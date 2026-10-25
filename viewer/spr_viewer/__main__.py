"""Línea de comandos: python -m spr_viewer <report|hexdump|vram|gui> ..."""
from __future__ import annotations

import argparse
import sys

from .binfile import BinFile, RangeError, hexdump
from .report import build_report, save_report
from .vram import FORMATS, PALETTE_FORMATS, decode_preview


def _int(s: str) -> int:
    return int(s, 0)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="spr_viewer")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("report", help="analiza un .rbh/.vram y escribe un reporte")
    r.add_argument("file")
    r.add_argument("--json", help="guardar el reporte completo en este archivo")

    h = sub.add_parser("hexdump", help="volcado hexadecimal")
    h.add_argument("file")
    h.add_argument("--offset", type=_int, default=0)
    h.add_argument("--length", type=_int, default=256)

    v = sub.add_parser("vram", help="vista previa EXPERIMENTAL de una textura")
    v.add_argument("file")
    v.add_argument("--width", type=_int, required=True)
    v.add_argument("--height", type=_int, required=True)
    v.add_argument("--offset", type=_int, default=0)
    v.add_argument("--format", choices=sorted(FORMATS), default="rgb565")
    v.add_argument("--palette-offset", type=_int)
    v.add_argument("--palette-format", choices=PALETTE_FORMATS, default="rgb565")
    v.add_argument("--out", required=True, help="PNG de salida")

    sub.add_parser("gui", help="abre la interfaz gráfica")

    a = ap.parse_args(argv)

    if a.cmd == "gui":
        from .gui import run
        return run()

    if a.cmd == "report":
        rep = build_report(a.file)
        print(f"{rep['file']}: {rep['size']} bytes")
        for t, info in rep["tags"].items():
            if info["count"]:
                print(f"  {t}: {info['count']} aparición(es), primera en 0x{info['hits'][0]['offset']:X}")
        for w in rep["warnings"]:
            print("  aviso:", w)
        for e in rep["errors"]:
            print("  ERROR:", e, file=sys.stderr)
        if a.json:
            save_report(rep, a.json)
            print("Reporte guardado en", a.json)
        return 1 if rep["errors"] else 0

    try:
        bf = BinFile.open(a.file)
        if a.cmd == "hexdump":
            print(hexdump(bf.slice(a.offset, min(a.length, max(0, len(bf) - a.offset))), a.offset))
        else:
            img = decode_preview(bf, a.offset, a.width, a.height, a.format,
                                 a.palette_offset, a.palette_format)
            img.save(a.out)
            print(f"Guardado {a.out} (EXPERIMENTAL: interpretación sin verificar)")
    except (OSError, ValueError, RangeError) as e:
        print("ERROR:", e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
