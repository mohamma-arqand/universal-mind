"""R66 P3 — «فایل X را بساز و محتواش را نشان بده»: BOTH halves of the sentence.

The sweep caught the sentence unrecognized (an «این فرمان را نشناختم»
over a plain everyday ask). Two shapes now work in ONE run:
- no spoken content → the file is created EMPTY, the emptiness is NAMED
  (خالی — متنش را نگفتی), and the (empty) content shows back;
- with content («با محتوای …») → the write runs, then the content
  shows back (answering only the write is a half-truth).
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def tmp_file(tmp_path: Path) -> Path:
    return tmp_path / "gwr66.txt"


class TestCreateAndShow:
    def test_create_empty_then_show(self, tmp_file: Path) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run(f"فایل {tmp_file} را بساز و محتواش را به من نشان بده")
        assert p["ok"] is True
        assert p["route"] == ["textfile"]
        assert tmp_file.exists()
        assert tmp_file.stat().st_size == 0
        assert "خالی" in p["agent_report"]  # the emptiness is named
        assert "محتوای فعلی" in p["agent_report"]

    def test_create_with_content_shows_it_back(self, tmp_file: Path) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run(
            f"فایل {tmp_file} را با محتوای سلام از گواه بساز و محتواش را نشان بده"
        )
        assert p["ok"] is True
        assert tmp_file.read_text(encoding="utf-8") == "سلام از گواه"
        # BOTH halves answered: the write AND the show
        assert "نوشتم" in p["agent_report"]
        assert "محتوای فایل" in p["agent_report"]
        assert "سلام از گواه" in p["agent_report"]

    def test_an_existing_file_is_not_replaced(self, tmp_file: Path) -> None:
        from universal_mind.persian_router import route_and_run

        tmp_file.write_text("موجود", encoding="utf-8")
        p = route_and_run(f"فایل {tmp_file} را بساز و محتواش را به من نشان بده")
        # the file keeps its real content (create does not clobber)
        assert tmp_file.read_text(encoding="utf-8") == "موجود"
        assert "موجود" in p["agent_report"]
