"""Reporte de análisis de un archivo RBH/VRAM. Separa lo confirmado de las hipótesis."""
from __future__ import annotations

import json
from pathlib import Path

from .binfile import BinFile, hexdump

MAX_HITS_PER_TAG = 50


def build_report(path: str | Path) -> dict:
    """Nunca lanza excepciones: los errores quedan en report['errors']."""
    p = Path(path)
    report: dict = {
        "file": p.name,
        "path": str(p),
        "size": None,
        "head_hexdump": "",
        "tags": {},
        "strings": [],
        "entropy_4k": [],
        # Solo se llena con estructuras verificadas contra archivos reales.
        "confirmed": [],
        # Observaciones sin verificar (p. ej. valores u32 tras un tag).
        "hypotheses": [],
        "warnings": [],
        "errors": [],
    }
    try:
        bf = BinFile.open(p)
    except (OSError, ValueError) as e:
        report["errors"].append(str(e))
        return report

    report["size"] = len(bf)
    if len(bf) == 0:
        report["warnings"].append("archivo vacío")
        return report

    report["head_hexdump"] = hexdump(bf.data[:256])
    for tag, offsets in bf.find_tags().items():
        hits = []
        for off in offsets[:MAX_HITS_PER_TAG]:
            after = bf.data[off + 4:off + 20]
            u32 = [int.from_bytes(after[i:i + 4], "little") for i in range(0, len(after) - 3, 4)]
            hits.append({"offset": off, "next16_hex": after.hex(" "), "u32le_after": u32})
        report["tags"][tag] = {"count": len(offsets), "hits": hits}
        if len(offsets) > MAX_HITS_PER_TAG:
            report["warnings"].append(f"{tag}: se muestran {MAX_HITS_PER_TAG} de {len(offsets)}")

    report["strings"] = [{"offset": o, "text": s} for o, s in bf.strings()]
    report["entropy_4k"] = bf.entropy_blocks()

    found = [t for t, v in report["tags"].items() if v["count"]]
    if found:
        report["hypotheses"].append(
            "Se hallaron identificadores candidatos: " + ", ".join(found)
            + ". Su aparición no prueba que exista la estructura esperada.")
    else:
        report["warnings"].append("no se encontró ningún identificador candidato")
    if bf.entropy_blocks() and max(report["entropy_4k"]) > 7.5:
        report["hypotheses"].append("Hay bloques de entropía alta (>7.5): posible compresión.")
    return report


def save_report(report: dict, out_path: str | Path) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
