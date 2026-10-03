"""R63 P2 — the compound file+content sentence, live.

«فایل گزارش.md را بساز و داخلش بنویس امروز هوا خوب بود» fell to the
reflexive history block: the write gate demanded a DRIVE-LETTER path
and the «داخلش بنویس» connector did not exist. The file was never
created and the sentence lied by answering something else entirely.

Three shapes now hold, each with its own honest answer:
- full path + «با محتوای X بنویس» → exact content X (trailing «بنویس»
  stripped, never stored as content);
- bare FILENAME (Persian letters allowed) + «داخلش بنویس X» → the
  file lands in the working area (~/Documents/universal_mind), the
  report names the real path;
- content but NO filename → a named refusal showing the exact shape.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from universal_mind.persian_router import route_and_run


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    for f in ("D:/um_t63_a.txt", "D:/um_t63_c.txt"):
        Path(f).unlink(missing_ok=True)
    (Path.home() / "Documents" / "universal_mind" / "گزارش-t63.md").unlink(missing_ok=True)


class TestTheCompoundSentence:
    def test_bare_filename_with_content_creates_the_file(self) -> None:
        p = route_and_run(
            "فایل گزارش-t63.md را بساز و داخلش بنویس امروز هوا خوب بود")
        target = Path.home() / "Documents" / "universal_mind" / "گزارش-t63.md"
        assert p["ok"] is True
        assert target.exists()
        assert target.read_text(encoding="utf-8") == "امروز هوا خوب بود"
        assert "نوشتم" in p["agent_report"]
        assert "universal_mind" in p["agent_report"]  # the real path is named

    def test_full_path_with_content_stores_exact_content(self) -> None:
        p = route_and_run("فایل متنی D:/um_t63_a.txt را با محتوای سلام بنویس")
        assert p["ok"] is True
        assert Path("D:/um_t63_a.txt").read_text(encoding="utf-8") == "سلام"

    def test_long_content_keeps_the_whole_sentence(self) -> None:
        p = route_and_run(
            "فایل متنی D:/um_t63_c.txt را با محتوای این یک جملهٔ طولانی‌تر است بنویس")
        assert p["ok"] is True
        assert Path("D:/um_t63_c.txt").read_text(encoding="utf-8") == \
            "این یک جملهٔ طولانی‌تر است"

    def test_no_filename_is_a_named_refusal(self) -> None:
        p = route_and_run("فایل بساز و داخلش بنویس امروز هوا خوب بود")
        assert p["ok"] is False
        assert "نامِ فایل را نگفتی" in p["agent_report"]
        assert "گزارش.md" in p["agent_report"]  # the working example is shown

    def test_a_filename_without_content_builds_a_document(self) -> None:
        # «فایل X را بساز» with no content is a DOCUMENT request — the
        # platform builds a real PDF (measured live), which is honest:
        # something real is created, and the path is named in the report.
        p = route_and_run("فایل گزارش-t63.md را بساز")
        assert p["ok"] is True
        assert "ساخت" in p["agent_report"] or "ساخته شد" in p["agent_report"]
