import pytest

from spr_viewer.binfile import BinFile, RangeError, hexdump


def test_slice_valid():
    bf = BinFile(b"0123456789")
    assert bf.slice(2, 3) == b"234"
    assert bf.slice(10, 0) == b""


@pytest.mark.parametrize("offset,size", [(-1, 2), (0, -1), (8, 3), (11, 0), (100, 1)])
def test_slice_invalid_ranges(offset, size):
    with pytest.raises(RangeError):
        BinFile(b"0123456789").slice(offset, size)


def test_unpack_truncated():
    bf = BinFile(b"\x01\x02\x03")
    assert bf.unpack("<H", 0) == (0x0201,)
    with pytest.raises(RangeError):
        bf.unpack("<I", 0)


def test_find_tags_offsets():
    bf = BinFile(b"xxPIFFyyRBHHzzPIFF")
    tags = bf.find_tags()
    assert tags["PIFF"] == [2, 14]
    assert tags["RBHH"] == [8]
    assert tags["BODY"] == []


def test_hexdump_format():
    out = hexdump(b"PIFF\x00\x01", base=0x10)
    assert out.startswith("00000010  50 49 46 46 00 01")
    assert out.endswith("|PIFF..|")


def test_open_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        BinFile.open(tmp_path / "no_existe.rbh")


def test_open_does_not_modify_file(tmp_path):
    p = tmp_path / "a.rbh"
    p.write_bytes(b"PIFF" + bytes(100))
    before = (p.read_bytes(), p.stat().st_mtime_ns)
    BinFile.open(p)
    assert (p.read_bytes(), p.stat().st_mtime_ns) == before


def test_strings_and_entropy():
    bf = BinFile(b"\x00\x00hello world\x00\xff" + bytes(range(256)))
    assert (2, "hello world") in bf.strings()
    ent = bf.entropy_blocks(block=64)
    assert len(ent) >= 1 and all(0 <= e <= 8 for e in ent)
