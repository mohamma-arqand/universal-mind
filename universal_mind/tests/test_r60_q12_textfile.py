"""R60 Q1+Q2 — the text-file capability: read and write, honestly.

Two measured gaps: «محتوای فایل X را نشان بده» → «نشناختم», and «یک فایل
متنی بنویس…» was STOLEN by the clipboard (the file was never created). A
real text file is first-class data now — with the delete-law spirit (no
silent overwrite) and a secrets guard (.env is not content).
"""

from __future__ import annotations

from pathlib import Path

from universal_mind.persian_router import route, route_and_run
from universal_mind.textfile_tool import TextFileTool, TextFileToolConnector


class TestToolLaws:
    def test_read_roundtrip(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("سلام دنیا", encoding="utf-8")
        out = TextFileTool().read(str(f))
        assert out["ok"] is True and out["text"] == "سلام دنیا"

    def test_a_missing_file_is_refused_by_name(self) -> None:
        out = TextFileTool().read("D:/no/such/x.txt")
        assert out["ok"] is False and "پیدا نکردم" in out["error"]

    def test_a_directory_is_refused_as_a_directory(self, tmp_path: Path) -> None:
        out = TextFileTool().read(str(tmp_path))
        assert out["ok"] is False and "پوشه" in out["error"]

    def test_a_secret_file_is_never_read(self, tmp_path: Path) -> None:
        for name in (".env", "app.key", "my_secret.txt", "credentials.json"):
            f = tmp_path / name
            f.write_text("KEY=1", encoding="utf-8")
            out = TextFileTool().read(str(f))
            assert out["ok"] is False, name
            assert "راز" in out["error"] or "نمی‌خوانم" in out["error"], name

    def test_truncation_is_reported_not_hidden(self, tmp_path: Path) -> None:
        f = tmp_path / "big.txt"
        f.write_text("x" * 70_000, encoding="utf-8")
        out = TextFileTool().read(str(f), max_chars=1000)
        assert out["ok"] is True and out["truncated"] is True
        assert len(out["text"]) == 1000

    def test_write_creates_the_parent_and_refuses_overwrite(self, tmp_path: Path) -> None:
        target = tmp_path / "sub" / "new.txt"
        out = TextFileTool().write(str(target), "hello")
        assert out["ok"] is True and target.read_text(encoding="utf-8") == "hello"
        again = TextFileTool().write(str(target), "other")
        assert again["ok"] is False and "دورنویسی" in again["error"]

    def test_list_names_only_text_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("1", encoding="utf-8")
        (tmp_path / "b.md").write_text("2", encoding="utf-8")
        (tmp_path / "c.exe").write_bytes(b"3")
        out = TextFileTool().list_texts(str(tmp_path))
        assert out["ok"] is True
        assert "a.txt" in out["files"] and "b.md" in out["files"]
        assert "c.exe" not in out["files"]


class TestConnectorAsks:
    def test_read_without_path_asks_by_name(self) -> None:
        res = TextFileToolConnector().connect({}, {"operation": "read"})
        assert res.ok is False and "کدام فایل" in str(res.error)

    def test_write_without_path_asks_by_name(self) -> None:
        res = TextFileToolConnector().connect({}, {"operation": "write", "content": "x"})
        assert res.ok is False and "کجا بنویسم" in str(res.error)

    def test_an_unknown_operation_is_refused(self) -> None:
        res = TextFileToolConnector().connect({}, {"operation": "burn"})
        assert res.ok is False and "unknown operation" in str(res.error)


class TestRouting:
    def test_the_read_shape_routes_to_textfile(self) -> None:
        assert "textfile" in route("محتوای فایل D:/x.txt را نشان بده").capabilities

    def test_a_file_write_never_goes_to_clipboard(self, tmp_path: Path) -> None:
        # NOTE: route() is the raw keyword map — the WRITE shape is carried by
        # route_and_run's dedicated block (which re-enters with forced_route),
        # so the operator-level behaviour is what must not see clipboard.
        w = route_and_run(f"فایل متنی {tmp_path}/x.txt را با محتوای سلام بنویس")
        assert w["route"] == ["textfile"]
        assert f"{tmp_path}/x.txt".replace("/", "\\") in str(w) or "x.txt" in str(w) \
            or (tmp_path / "x.txt").exists()

    def test_plain_text_write_keeps_its_old_contract(self) -> None:
        # «متن بنویس» is the document shape — not the file shape
        assert "textfile" not in route("متن بنویس سلام دنیا").capabilities

    def test_a_chart_command_is_untouched(self) -> None:
        assert route("نمودار از ۲ و ۳ بکش").capabilities == ("chart",)


class TestEndToEnd:
    def test_write_then_read_through_the_router(self, tmp_path: Path) -> None:
        f = tmp_path / "note.txt"
        w = route_and_run(f"فایل متنی {f} را با محتوای گواه ر۶۰ بنویس")
        assert w["ok"] is True, w.get("agent_report")
        assert f.read_text(encoding="utf-8").startswith("گواه")
        r = route_and_run(f"محتوای فایل {f} را نشان بده")
        assert r["ok"] is True
        assert "گواه ر۶۰" in r["agent_report"]

    def test_overwrite_refusal_reaches_the_operator(self, tmp_path: Path) -> None:
        f = tmp_path / "note.txt"
        f.write_text("original", encoding="utf-8")
        w = route_and_run(f"فایل متنی {f} را با محتوای دیگر بنویس")
        assert w["ok"] is False
        assert "دورنویسی" in w["agent_report"]
        assert f.read_text(encoding="utf-8") == "original"  # nothing destroyed
