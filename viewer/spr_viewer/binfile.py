"""Acceso de solo lectura a archivos binarios, con validación de rangos."""
from __future__ import annotations

import math
import re
import struct
from pathlib import Path

# Identificadores candidatos: son pistas, no prueba de que exista una estructura.
CANDIDATE_TAGS = ("PIFF", "RBHH", "BODY", "PACK", "PKDB", "PKDW", "PKDL", "GLOB", "RELC")

MAX_FILE_SIZE = 512 * 1024 * 1024


class RangeError(ValueError):
    """Un offset, tamaño o cantidad queda fuera del archivo."""


class BinFile:
    """Contenido de un archivo en memoria. Nunca escribe en disco."""

    def __init__(self, data: bytes, name: str = "<memoria>"):
        self.data = bytes(data)
        self.name = name

    @classmethod
    def open(cls, path: str | Path) -> "BinFile":
        p = Path(path)
        size = p.stat().st_size
        if size > MAX_FILE_SIZE:
            raise ValueError(f"{p.name}: {size} bytes supera el límite de {MAX_FILE_SIZE}")
        with open(p, "rb") as f:  # solo lectura
            return cls(f.read(), p.name)

    def __len__(self) -> int:
        return len(self.data)

    def check_range(self, offset: int, size: int) -> None:
        if offset < 0 or size < 0:
            raise RangeError(f"offset/tamaño negativo ({offset}, {size})")
        if offset + size > len(self.data):
            raise RangeError(
                f"rango 0x{offset:X}+{size} excede el archivo ({len(self.data)} bytes)")

    def slice(self, offset: int, size: int) -> bytes:
        self.check_range(offset, size)
        return self.data[offset:offset + size]

    def unpack(self, fmt: str, offset: int) -> tuple:
        self.check_range(offset, struct.calcsize(fmt))
        return struct.unpack_from(fmt, self.data, offset)

    def find_all(self, needle: bytes, limit: int = 1000) -> list[int]:
        out: list[int] = []
        pos = self.data.find(needle)
        while pos != -1 and len(out) < limit:
            out.append(pos)
            pos = self.data.find(needle, pos + 1)
        return out

    def find_tags(self, tags=CANDIDATE_TAGS, limit: int = 1000) -> dict[str, list[int]]:
        return {t: self.find_all(t.encode("ascii"), limit) for t in tags}

    def strings(self, min_len: int = 4, limit: int = 500) -> list[tuple[int, str]]:
        out: list[tuple[int, str]] = []
        for m in re.finditer(rb"[\x20-\x7e]{%d,}" % min_len, self.data):
            out.append((m.start(), m.group().decode("ascii")))
            if len(out) >= limit:
                break
        return out

    def entropy_blocks(self, block: int = 4096) -> list[float]:
        """Entropía de Shannon (bits/byte) por bloque: sirve para ver zonas comprimidas."""
        result = []
        for start in range(0, len(self.data), block):
            chunk = self.data[start:start + block]
            counts = [0] * 256
            for b in chunk:
                counts[b] += 1
            n = len(chunk)
            result.append(round(-sum(c / n * math.log2(c / n) for c in counts if c), 3))
        return result


def hexdump(data: bytes, base: int = 0, width: int = 16) -> str:
    """Volcado hexadecimal + ASCII."""
    lines = []
    for i in range(0, len(data), width):
        row = data[i:i + width]
        hexpart = " ".join(f"{b:02x}" for b in row).ljust(width * 3 - 1)
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        lines.append(f"{base + i:08x}  {hexpart}  |{text}|")
    return "\n".join(lines)
