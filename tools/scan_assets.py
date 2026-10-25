#!/usr/bin/env python3
"""Escanea la carpeta del juego (PC) y resume extensiones, tamaños y formatos.

Uso:
    python3 tools/scan_assets.py <carpeta_del_juego> [--json reporte.json]

Sirve para decidir por dónde empezar: qué contenedores hay, qué archivos
no se reconocen y si hay nombres que solo difieren en mayúsculas.
"""
import argparse
import collections
import json
import os
import sys

MAGICS = [
    (b"\x89PNG", "PNG"),
    (b"BM", "BMP"),
    (b"RIFF", "RIFF (WAV/AVI)"),
    (b"OggS", "OGG"),
    (b"ID3", "MP3 (ID3)"),
    (b"\xff\xfb", "MP3"),
    (b"PK\x03\x04", "ZIP"),
    (b"MZ", "EXE/DLL (PE)"),
    (b"\xff\xd8\xff", "JPEG"),
    (b"GIF8", "GIF"),
    (b"DDS ", "DDS"),
    (b"BIK", "Bink"),
    (b"\x1f\x8b", "GZIP"),
    (b"MThd", "MIDI"),
]


def sniff(path):
    """Devuelve (formato, primeros 16 bytes en hex)."""
    try:
        with open(path, "rb") as f:
            head = f.read(32)
    except OSError:
        return "ilegible", ""
    hexhead = head[:16].hex(" ")
    for magic, name in MAGICS:
        if head.startswith(magic):
            return name, hexhead
    return "desconocido", hexhead


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", help="carpeta del juego")
    ap.add_argument("--json", help="guardar el reporte completo en este archivo")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        sys.exit(f"No existe la carpeta: {args.root}")

    files = []
    by_ext = collections.defaultdict(lambda: {"count": 0, "bytes": 0, "kinds": collections.Counter()})
    lower_names = collections.defaultdict(list)

    for dirpath, _, names in os.walk(args.root):
        for name in names:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, args.root).replace("\\", "/")
            size = os.path.getsize(path)
            kind, head = sniff(path)
            ext = os.path.splitext(name)[1].lower() or "(sin extension)"
            files.append({"path": rel, "size": size, "ext": ext, "kind": kind, "head": head})
            e = by_ext[ext]
            e["count"] += 1
            e["bytes"] += size
            e["kinds"][kind] += 1
            lower_names[rel.lower()].append(rel)

    if not files:
        sys.exit("La carpeta está vacía.")

    total = sum(f["size"] for f in files)
    print(f"{len(files)} archivos, {human(total)} en total\n")

    print(f"{'ext':<18}{'cant':>6}{'tamaño':>12}  formatos detectados")
    for ext, e in sorted(by_ext.items(), key=lambda kv: -kv[1]["bytes"]):
        kinds = ", ".join(f"{k} x{n}" for k, n in e["kinds"].most_common())
        print(f"{ext:<18}{e['count']:>6}{human(e['bytes']):>12}  {kinds}")

    unknown = sorted((f for f in files if f["kind"] == "desconocido"), key=lambda f: -f["size"])
    if unknown:
        print("\nMás grandes sin formato reconocido (candidatos a contenedor propio):")
        for f in unknown[:20]:
            print(f"  {human(f['size']):>10}  {f['path']}\n{'':14}{f['head']}")

    clashes = [v for v in lower_names.values() if len(v) > 1]
    if clashes:
        print("\nNombres que solo difieren en mayúsculas (problema en Android):")
        for group in clashes:
            print("  " + "  |  ".join(group))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(files, f, indent=2, ensure_ascii=False)
        print(f"\nReporte completo guardado en {args.json}")


if __name__ == "__main__":
    main()
