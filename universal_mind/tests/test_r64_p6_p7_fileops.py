"""R64 P6+P7 — search inside a file, replace inside a file.

Both were measured dead: «در فایل X دنبال کلمه Y بگرد» and «کلمه A را با
B عوض کن» returned «نشناختم». Both are REAL text operations now, with
the file-tool's laws intact:
- search: real matches with line numbers; a needle that is not there
  says so honestly; secret-looking files are never read;
- replace: rewrites the file, so it needs the operator's EXPLICIT
  continue («روی همان فایل …» — the delete-law spirit); the count and
  the pair are always named; a miss changes nothing and says so.

«روی همان فایل» is NOT an anaphora — excluding it from refers_to_last
keeps the confirmation phrase reachable (a live bug the sweep caught:
the replace-with-confirmation fell to «همان را دوباره بکن»).
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def witness(tmp_path: Path) -> Path:
    f = tmp_path / "um_r64.txt"
    f.write_text("سلام دنیا\nاین یک سلام است\nمتن آزمون\nسلام دوباره",
                 encoding="utf-8")
    return f


class TestSearch:
    def test_matches_with_line_numbers(self, witness: Path) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run(f"در فایل {witness} دنبال کلمه سلام بگرد")
        assert p["ok"] is True
        rep = p["agent_report"]
        assert "۳ مورد" in rep
        assert "خط ۱" in rep and "خط ۲" in rep and "خط ۴" in rep

    def test_a_miss_is_honest(self, witness: Path) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run(f"در فایل {witness} دنبال کلمه زرشک بگرد")
        assert p["ok"] is True
        assert "هیچ" in p["agent_report"]

    def test_a_missing_file_refuses_by_name(self, tmp_path: Path) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run(f"در فایل {tmp_path}/nofile-r64.txt دنبال کلمه سلام بگرد")
        assert p["ok"] is False
        assert "پیدا نکردم" in p["agent_report"]


class TestReplace:
    def test_without_confirmation_it_asks(self, witness: Path) -> None:
        from universal_mind.persian_router import route_and_run

        before = witness.read_text(encoding="utf-8")
        p = route_and_run(
            f"فایل {witness} را ویرایش کن و کلمه سلام را با درود عوض کن")
        assert p["ok"] is False
        assert "تأیید" in p["agent_report"]
        assert "روی همان فایل" in p["agent_report"]  # the remedy is named
        assert witness.read_text(encoding="utf-8") == before  # untouched

    def test_with_confirmation_it_replaces_for_real(self, witness: Path) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run(f"روی همان فایل {witness} کلمه سلام را با درود عوض کن")
        assert p["ok"] is True
        assert "۳ مورد عوض شد" in p["agent_report"]
        after = witness.read_text(encoding="utf-8")
        assert "درود دنیا" in after and "سلام" not in after

    def test_a_missed_needle_changes_nothing(self, witness: Path) -> None:
        from universal_mind.persian_router import route_and_run

        before = witness.read_text(encoding="utf-8")
        p = route_and_run(f"روی همان فایل {witness} کلمه زرشک را با انار عوض کن")
        assert p["ok"] is True
        assert "چیزی عوض نشد" in p["agent_report"]
        assert witness.read_text(encoding="utf-8") == before
