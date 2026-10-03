"""R67 P2-P6 — real file operations: rename, copy, size, folder count, mkdir.

The sweep caught «نام فایل X را عوض کن به Y» answering with the file's
CONTENT (a read!), «فایل X را به Y کپی کن» going to the clipboard with
an «empty text» refusal, and size/count/mkdir unrecognized. All five
are REAL operations now, delete-law safe (rename removes the old NAME;
copy over an existing file needs «روی همان فایل»).
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def pair(tmp_path: Path) -> tuple[Path, Path]:
    a = tmp_path / "um_a.txt"
    a.write_text("محتوای گواه", encoding="utf-8")
    return a, tmp_path / "um_b.txt"


class TestRename:
    def test_a_real_rename_both_names_named(self, pair: tuple[Path, Path]) -> None:
        from universal_mind.persian_router import route_and_run

        src, dst = pair
        p = route_and_run(f"نام فایل {src} را عوض کن به {dst}")
        assert p["ok"] is True
        assert "نام عوض شد" in p["agent_report"]
        assert not src.exists() and dst.exists()
        assert dst.read_text(encoding="utf-8") == "محتوای گواه"

    def test_an_existing_destination_needs_confirmation(self, pair: tuple[Path, Path]) -> None:
        from universal_mind.persian_router import route_and_run

        src, dst = pair
        dst.write_text("موجود", encoding="utf-8")
        p = route_and_run(f"نام فایل {src} را عوض کن به {dst}")
        assert p["ok"] is False
        assert "از قبل هست" in p["agent_report"]
        assert src.exists() and dst.read_text(encoding="utf-8") == "موجود"


class TestCopy:
    def test_a_real_copy_the_source_survives(self, pair: tuple[Path, Path]) -> None:
        from universal_mind.persian_router import route_and_run

        src, dst = pair
        p = route_and_run(f"فایل {src} را به {dst} کپی کن")
        assert p["ok"] is True
        assert p["route"] == ["textfile"]  # NOT clipboard
        assert src.exists()  # the source SURVIVES a copy
        assert dst.read_text(encoding="utf-8") == "محتوای گواه"
        assert "سر جایش است" in p["agent_report"]

    def test_an_existing_destination_refuses(self, pair: tuple[Path, Path]) -> None:
        from universal_mind.persian_router import route_and_run

        src, dst = pair
        dst.write_text("موجود", encoding="utf-8")
        p = route_and_run(f"فایل {src} را به {dst} کپی کن")
        assert p["ok"] is False
        assert "روی همان فایل" in p["agent_report"]


class TestSize:
    def test_the_real_size_human_readable(self, pair: tuple[Path, Path]) -> None:
        from universal_mind.persian_router import route_and_run

        src, _ = pair
        p = route_and_run(f"حجم فایل {src} چقدر است؟")
        assert p["ok"] is True
        assert f"{len('محتوای گواه'.encode('utf-8'))} بایت".translate(
            str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")) in p["agent_report"]

    def test_a_missing_file_is_an_honest_refusal(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("حجم فایل D:/um_nonexistent_zz.txt چقدر است؟")
        assert p["ok"] is False
        assert "پیدا نکردم" in p["agent_report"]


class TestFolderCount:
    def test_the_real_count(self, tmp_path: Path) -> None:
        from universal_mind.persian_router import route_and_run

        (tmp_path / "f1.txt").write_text("x", encoding="utf-8")
        (tmp_path / "f2.txt").write_text("y", encoding="utf-8")
        (tmp_path / "sub").mkdir()
        p = route_and_run(f"در پوشه {tmp_path} چند فایل هست؟")
        assert p["ok"] is True
        assert "۲ فایل" in p["agent_report"]
        assert "۱ پوشه" in p["agent_report"]


class TestMkdir:
    def test_a_real_folder_with_parents(self, tmp_path: Path) -> None:
        from universal_mind.persian_router import route_and_run

        target = tmp_path / "deep" / "gwr67"
        p = route_and_run(f"پوشه {target} را بساز")
        assert p["ok"] is True
        assert target.is_dir()
        assert "ساخته شد" in p["agent_report"]

    def test_an_existing_folder_refuses(self, tmp_path: Path) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run(f"پوشه {tmp_path} را بساز")
        assert p["ok"] is False
        assert "از قبل هست" in p["agent_report"]
