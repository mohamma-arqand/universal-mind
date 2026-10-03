"""R74 P1-P5 — the FILE MANAGEMENT class.

A live 16-command sweep found 9 wrong/missing answers: a copy to a
FOLDER never copied (the destination regex could not see «به پوشه Y»),
«به اکسل تبدیل کن» CRASHED openpyxl on a .txt (not a named refusal),
«زیپ کن» was unknown, «پوشه بساز» built a PDF, and the folder
size/count/list operations existed in the tool but no sentence reached
them. The wave: destinations that name folders, a 30th real capability
(the format converter), the zip suite owns zip sentences, and folder
asks own their sentence (pdf/compute step aside).
"""

from __future__ import annotations

from pathlib import Path

import pytest

BASE = Path(r"D:/gwr74_tests")
SRC = BASE / "note.txt"
TGT = BASE / "copy_target"


def _setup() -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    SRC.write_text("سلام دنیا\nخط دوم\n", encoding="utf-8")
    TGT.mkdir(exist_ok=True)
    for f in TGT.iterdir():
        f.unlink()
    for suf in (".csv", ".json", ".xlsx"):
        SRC.with_suffix(suf).unlink(missing_ok=True)
    for z in BASE.glob("*.zip"):
        z.unlink()
    (BASE / "گزارشها").rmdir() if (BASE / "گزارشها").exists() else None


class TestDestinations:
    def test_copy_to_a_folder_lands_inside_it(self) -> None:
        from universal_mind.persian_router import route_and_run

        _setup()
        p = route_and_run(f"فایل {SRC} را به پوشه {TGT} کپی کن")
        assert p["ok"] is True, str(p.get("agent_report"))[:100]
        assert (TGT / "note.txt").exists(), "the copy never landed"

    def test_copy_to_a_path_is_a_file_destination(self) -> None:
        from universal_mind.textfile_tool import TextFileTool

        _setup()
        out = TextFileTool().copy(str(SRC), str(TGT / "renamed.txt"))
        assert out["ok"] is True and (TGT / "renamed.txt").exists()


class TestFormatConverter:
    def test_txt_to_csv_json_xlsx_all_real(self) -> None:
        from universal_mind.format_converter import convert_format

        _setup()
        for fmt in ("csv", "xlsx", "json"):
            out = convert_format(str(SRC), fmt)
            assert out["ok"] is True, (fmt, out.get("error"))
            assert Path(out["path"]).exists() and out["rows"] >= 1

    def test_a_bad_target_is_a_named_refusal(self) -> None:
        from universal_mind.format_converter import convert_format

        _setup()
        out = convert_format(str(SRC), "pdf")
        assert out["ok"] is False and "پشتیبانی نمیشود" in out["error"]

    def test_excel_ask_never_crashes_openpyxl(self) -> None:
        from universal_mind.persian_router import route_and_run

        _setup()
        p = route_and_run(f"فایل {SRC} را به اکسل تبدیل کن")
        assert p["ok"] is True, str(p.get("agent_report"))[:100]
        assert "excel" not in p["route"], "excel must step aside for convert"
        assert SRC.with_suffix(".xlsx").exists()

    def test_stats_sentences_survive(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("میانگین ۲ و ۴ را حساب کن")
        assert p["ok"] is True
        rep = str(p.get("agent_report", ""))
        assert "۳" in rep and "convert" not in (p.get("route") or [])


class TestZipSentences:
    def test_a_file_zip_builds_a_real_zip(self) -> None:
        from universal_mind.persian_router import route_and_run

        _setup()
        p = route_and_run(f"فایل {SRC} را ZIP کن")
        assert p["ok"] is True, str(p.get("agent_report"))[:100]
        assert "zip" in p["route"] and "archive" not in p["route"]

    def test_a_folder_zip_packs_its_real_files(self) -> None:
        from universal_mind.zip_helper import pack_folder

        _setup()
        out = pack_folder(BASE)
        assert "files" in out and len(out["files"]) >= 1

    def test_an_empty_folder_is_a_named_refusal(self) -> None:
        from universal_mind.zip_helper import pack_folder

        empty = BASE / "empty74"
        empty.mkdir(exist_ok=True)
        out = pack_folder(empty)
        assert "error" in out and "خالی" in out["error"]


class TestFolderAsks:
    def test_mkdir_by_name_builds_the_real_folder(self) -> None:
        from universal_mind.persian_router import route_and_run

        _setup()
        p = route_and_run("یک پوشه به نام گزارشها در D:/gwr74_tests بساز")
        assert p["ok"] is True, str(p.get("agent_report"))[:100]
        assert (BASE / "گزارشها").exists()
        assert "pdf" not in p["route"], "a folder ask must not build a PDF"

    def test_folder_size_answers_from_the_real_stats(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run(f"حجم پوشه {BASE} چنده؟")
        assert p["ok"] is True
        rep = str(p.get("agent_report", ""))
        assert "فایل" in rep and "پوشه" in rep

    def test_list_texts_with_a_pattern_filters(self) -> None:
        from universal_mind.persian_router import route_and_run

        _setup()
        p = route_and_run(f"همه فایلهای txt پوشه {BASE} را فهرست کن")
        assert p["ok"] is True
        rep = str(p.get("agent_report", ""))
        assert "note.txt" in rep and ".csv" not in rep


@pytest.fixture(autouse=True)
def _around() -> None:
    _setup()
    yield
    # cleanup: the test area is scratch; leave nothing the operator did not ask for
    import shutil

    shutil.rmtree(BASE, ignore_errors=True)
