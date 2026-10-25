from spr_viewer.report import build_report


def test_report_finds_tag(tmp_path):
    p = tmp_path / "x.rbh"
    p.write_bytes(b"PIFF" + (0x1234).to_bytes(4, "little") + bytes(32))
    rep = build_report(p)
    assert rep["size"] == 40
    assert rep["tags"]["PIFF"]["count"] == 1
    assert rep["tags"]["PIFF"]["hits"][0]["u32le_after"][0] == 0x1234
    assert rep["errors"] == []


def test_report_never_claims_confirmed_structure(tmp_path):
    p = tmp_path / "x.rbh"
    p.write_bytes(b"PIFFRBHHBODY" + bytes(64))
    assert build_report(p)["confirmed"] == []


def test_report_missing_file_does_not_raise(tmp_path):
    rep = build_report(tmp_path / "nada.rbh")
    assert rep["errors"] and rep["size"] is None


def test_report_empty_file(tmp_path):
    p = tmp_path / "vacio.vram"
    p.write_bytes(b"")
    rep = build_report(p)
    assert rep["size"] == 0 and "archivo vacío" in rep["warnings"]


def test_report_tag_at_end_of_file(tmp_path):
    p = tmp_path / "corto.rbh"
    p.write_bytes(bytes(10) + b"PACK")  # truncado justo tras el tag
    rep = build_report(p)
    assert rep["tags"]["PACK"]["hits"][0]["next16_hex"] == ""
    assert rep["tags"]["PACK"]["hits"][0]["u32le_after"] == []
