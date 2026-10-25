"""Vista previa EXPERIMENTAL de datos de textura.

El formato real de .vram no está confirmado. Estas funciones solo interpretan
bytes con los parámetros que elija el usuario; el resultado debe tratarse como
una prueba, no como una decodificación verificada.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from .binfile import BinFile, RangeError

MAX_DIM = 8192

# nombre -> bytes por píxel (None = indexado, necesita paleta)
FORMATS: dict[str, int | None] = {
    "gray8": 1,
    "pal8": None,
    "rgb565": 2,
    "argb1555": 2,
    "rgb888": 3,
    "bgr888": 3,
    "rgba8888": 4,
    "bgra8888": 4,
}
PALETTE_FORMATS = ("rgb565", "argb1555", "rgb888", "rgba8888")


def _convert(raw: bytes, fmt: str, count: int) -> np.ndarray:
    """Devuelve un arreglo (count, 4) uint8 RGBA."""
    if fmt == "gray8":
        g = np.frombuffer(raw, np.uint8, count)
        return np.stack([g, g, g, np.full(count, 255, np.uint8)], axis=1)
    if fmt in ("rgb565", "argb1555"):
        v = np.frombuffer(raw, "<u2", count).astype(np.uint32)
        if fmt == "rgb565":
            r, g, b = (v >> 11) & 31, (v >> 5) & 63, v & 31
            r, g, b = r * 255 // 31, g * 255 // 63, b * 255 // 31
            a = np.full(count, 255)
        else:
            a = ((v >> 15) & 1) * 255
            r, g, b = ((v >> 10) & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31, (v & 31) * 255 // 31
        return np.stack([r, g, b, a], axis=1).astype(np.uint8)
    if fmt in ("rgb888", "bgr888"):
        a3 = np.frombuffer(raw, np.uint8, count * 3).reshape(count, 3)
        if fmt == "bgr888":
            a3 = a3[:, ::-1]
        return np.concatenate([a3, np.full((count, 1), 255, np.uint8)], axis=1)
    if fmt in ("rgba8888", "bgra8888"):
        a4 = np.frombuffer(raw, np.uint8, count * 4).reshape(count, 4)
        return a4[:, [2, 1, 0, 3]] if fmt == "bgra8888" else a4.copy()
    raise ValueError(f"formato desconocido: {fmt}")


def decode_preview(bf: BinFile, offset: int, width: int, height: int, fmt: str,
                   palette_offset: int | None = None, palette_fmt: str = "rgb565",
                   palette_size: int = 256) -> Image.Image:
    """Interpreta bytes crudos como imagen. Valida todos los rangos antes de leer."""
    if fmt not in FORMATS:
        raise ValueError(f"formato desconocido: {fmt}")
    if not (1 <= width <= MAX_DIM and 1 <= height <= MAX_DIM):
        raise ValueError(f"dimensiones fuera de rango (1..{MAX_DIM}): {width}x{height}")
    count = width * height

    bpp = FORMATS[fmt]
    if bpp is None:  # indexado
        if palette_offset is None:
            raise ValueError("pal8 requiere un offset de paleta")
        if palette_fmt not in PALETTE_FORMATS:
            raise ValueError(f"formato de paleta inválido: {palette_fmt}")
        pbpp = FORMATS[palette_fmt]
        palette = _convert(bf.slice(palette_offset, palette_size * pbpp), palette_fmt, palette_size)
        idx = np.frombuffer(bf.slice(offset, count), np.uint8)
        rgba = palette[np.minimum(idx, palette_size - 1)]
    else:
        rgba = _convert(bf.slice(offset, count * bpp), fmt, count)

    return Image.fromarray(rgba.reshape(height, width, 4), "RGBA")


__all__ = ["FORMATS", "PALETTE_FORMATS", "decode_preview", "RangeError"]
