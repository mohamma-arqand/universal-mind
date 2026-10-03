"""R65 P6 — «فایل X را به Y جابجا کن»: a REAL move, delete-law safe.

A move DELETES the source, so a destination that already exists needs
the operator's explicit continue («روی همان فایل …»); the source must
exist; both paths are named in the answer.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def pair(tmp_path: Path) -> tuple[Path, Path]:
    a = tmp_path / "um_a.txt"
    a.write_text("محتوای گواه", encoding="utf-8")
    return a, tmp_path / "um_b.txt"


class TestTheRealMove:
    def test_it_moves_for_real(self, pair: tuple[Path, Path]) -> None:
        from universal_mind.persian_router import route_and_run

        src, dst = pair
        p = route_and_run(f"فایل {src} را به {dst} جابجا کن")
        assert p["ok"] is True
        assert "جابجا شد" in p["agent_report"]
        assert str(src) in p["agent_report"] and str(dst) in p["agent_report"]
        assert not src.exists()          # the source is really gone
        assert dst.read_text(encoding="utf-8") == "محتوای گواه"

    def test_an_existing_destination_needs_confirmation(self, pair: tuple[Path, Path]) -> None:
        from universal_mind.persian_router import route_and_run

        src, dst = pair
        dst.write_text("موجود", encoding="utf-8")
        before = src.read_text(encoding="utf-8")
        p = route_and_run(f"فایل {src} را به {dst} جابجا کن")
        assert p["ok"] is False
        assert "از قبل هست" in p["agent_report"]
        assert "روی همان فایل" in p["agent_report"]  # the remedy named
        # nothing moved: source intact, destination intact
        assert src.read_text(encoding="utf-8") == before
        assert dst.read_text(encoding="utf-8") == "موجود"

    def test_confirmation_overwrites(self, pair: tuple[Path, Path]) -> None:
        from universal_mind.persian_router import route_and_run

        src, dst = pair
        dst.write_text("موجود", encoding="utf-8")
        p = route_and_run(f"روی همان فایل {src} را به {dst} جابجا کن")
        assert p["ok"] is True
        assert dst.read_text(encoding="utf-8") == "محتوای گواه"
        assert not src.exists()
