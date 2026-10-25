import struct

import pytest

from spr_viewer.binfile import BinFile, RangeError
from spr_viewer.vram import decode_preview


def test_rgb565_known_colors():
    data = struct.pack("<4H", 0xF800, 0x07E0, 0x001F, 0xFFFF)
    img = decode_preview(BinFile(data), 0, 2, 2, "rgb565")
    assert img.size == (2, 2)
    assert img.getpixel((0, 0)) == (255, 0, 0, 255)
    assert img.getpixel((1, 0)) == (0, 255, 0, 255)
    assert img.getpixel((0, 1)) == (0, 0, 255, 255)
    assert img.getpixel((1, 1)) == (255, 255, 255, 255)


def test_argb1555_alpha_bit():
    data = struct.pack("<2H", 0x8000 | 0x7C00, 0x7C00)
    img = decode_preview(BinFile(data), 0, 2, 1, "argb1555")
    assert img.getpixel((0, 0)) == (255, 0, 0, 255)
    assert img.getpixel((1, 0)) == (255, 0, 0, 0)


def test_bgr888_channel_order():
    img = decode_preview(BinFile(bytes([1, 2, 3])), 0, 1, 1, "bgr888")
    assert img.getpixel((0, 0)) == (3, 2, 1, 255)


def test_pal8_uses_palette():
    palette = struct.pack("<256H", *([0xF800] + [0x07E0] * 255))
    data = bytes([0, 1, 1, 0]) + palette
    img = decode_preview(BinFile(data), 0, 2, 2, "pal8", palette_offset=4)
    assert img.getpixel((0, 0)) == (255, 0, 0, 255)
    assert img.getpixel((1, 0)) == (0, 255, 0, 255)


def test_offset_is_respected():
    data = bytes(8) + bytes([10, 20, 30, 40])
    img = decode_preview(BinFile(data), 8, 2, 2, "gray8")
    assert img.getpixel((1, 1))[0] == 40


@pytest.mark.parametrize("w,h", [(0, 4), (4, 0), (-1, 4), (9000, 4)])
def test_invalid_dimensions(w, h):
    with pytest.raises(ValueError):
        decode_preview(BinFile(bytes(64)), 0, w, h, "gray8")


def test_truncated_data_raises_range_error():
    with pytest.raises(RangeError):
        decode_preview(BinFile(bytes(10)), 0, 4, 4, "rgb565")


def test_invalid_offset_raises_range_error():
    with pytest.raises(RangeError):
        decode_preview(BinFile(bytes(16)), 100, 2, 2, "gray8")


def test_unknown_format_and_missing_palette():
    with pytest.raises(ValueError):
        decode_preview(BinFile(bytes(16)), 0, 2, 2, "xyz")
    with pytest.raises(ValueError):
        decode_preview(BinFile(bytes(16)), 0, 2, 2, "pal8")
