import json

from spr_viewer.__main__ import main


def test_cli_report_and_json(tmp_path, capsys):
    f = tmp_path / "a.rbh"
    f.write_bytes(b"RBHH" + bytes(60))
    out = tmp_path / "r.json"
    assert main(["report", str(f), "--json", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["tags"]["RBHH"]["count"] == 1
    assert "RBHH" in capsys.readouterr().out


def test_cli_report_missing_file_returns_error(tmp_path):
    assert main(["report", str(tmp_path / "nada.rbh")]) == 1


def test_cli_vram_writes_png(tmp_path):
    f = tmp_path / "a.vram"
    f.write_bytes(bytes(64))
    out = tmp_path / "t.png"
    assert main(["vram", str(f), "--width", "4", "--height", "4", "--format", "gray8",
                 "--out", str(out)]) == 0
    assert out.read_bytes()[:4] == b"\x89PNG"


def test_cli_vram_truncated_fails_cleanly(tmp_path):
    f = tmp_path / "a.vram"
    f.write_bytes(bytes(4))
    assert main(["vram", str(f), "--width", "64", "--height", "64", "--out",
                 str(tmp_path / "t.png")]) == 1
