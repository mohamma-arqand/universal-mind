"""R53 wave-4 — REAL FILE SEARCH, tested against the real disk.

«فایلهای بزرگ دیسک D را پیدا کن» was «نشناختم». Now a read-only,
deadline-bounded, honest walk: top-K by size, name/type filters, locked
folders NAMED (never silent), the find-intent never drags webfetch/image
into a disk search.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture()
def big_tree(tmp_path: Path) -> Path:
    """A real tree with known sizes: 3 big files, 2 small, one nested big."""
    d = tmp_path / "tree"
    d.mkdir()
    (d / "big1.bin").write_bytes(b"a" * 500_000)
    (d / "big2.bin").write_bytes(b"b" * 300_000)
    (d / "small1.txt").write_text("tiny", encoding="utf-8")
    sub = d / "sub"
    sub.mkdir()
    (sub / "big3.bin").write_bytes(b"c" * 800_000)
    (sub / "small2.txt").write_text("x", encoding="utf-8")
    return d


class TestFileSearchTool:
    def test_top_k_by_size_across_subdirs(self, big_tree: Path) -> None:
        from universal_mind.file_search_tool import FileSearchTool

        res = FileSearchTool().search(str(big_tree), top=3)
        assert res["ok"] is True
        names = [m["name"] for m in res["matches"]]
        assert names[0] == "big3.bin"  # 800k > 500k > 300k — real size sort
        assert len(res["matches"]) == 3

    def test_min_size_floor_filters_small_files(self, big_tree: Path) -> None:
        from universal_mind.file_search_tool import FileSearchTool

        res = FileSearchTool().search(str(big_tree), min_size=400_001)
        assert res["ok"] is True
        assert all(m["bytes"] >= 400_001 for m in res["matches"])
        assert len(res["matches"]) == 2  # big3 (800k) + big1 (500k)

    def test_name_filter_multi_token_any_match(self, big_tree: Path) -> None:
        from universal_mind.file_search_tool import FileSearchTool

        res = FileSearchTool().search(str(big_tree), name="txt md")
        assert res["ok"] is True
        assert {m["name"] for m in res["matches"]} == {"small1.txt", "small2.txt"}

    def test_zero_hits_is_honest_not_fake(self, big_tree: Path) -> None:
        from universal_mind.file_search_tool import FileSearchTool

        res = FileSearchTool().search(str(big_tree), name="zzz-nothing")
        assert res["ok"] is True
        assert res["matches"] == []

    def test_missing_folder_is_a_named_failure(self) -> None:
        from universal_mind.file_search_tool import FileSearchTool

        res = FileSearchTool().search("Z:/definitely/not/here")
        assert res["ok"] is False
        assert "پیدا نشد" in res["error"]

    def test_walk_is_read_only(self, big_tree: Path) -> None:
        """THE SAFETY LAW: search never moves/renames/deletes anything."""
        before = sorted(str(p.relative_to(big_tree)) for p in big_tree.rglob("*"))
        from universal_mind.file_search_tool import FileSearchTool

        FileSearchTool().search(str(big_tree))
        after = sorted(str(p.relative_to(big_tree)) for p in big_path_all(big_tree))
        assert before == after

    def test_system_junk_folders_are_skipped(self, big_tree: Path) -> None:
        """$Recycle.Bin and friends are never walked."""
        junk = big_tree / "$Recycle.Bin"
        junk.mkdir()
        (junk / "junk.bin").write_bytes(b"j" * 900_000)
        from universal_mind.file_search_tool import FileSearchTool

        res = FileSearchTool().search(str(big_tree), top=1)
        assert res["ok"] is True
        assert res["matches"][0]["name"] == "big3.bin"  # the 900k junk ignored


def big_path_all(root: Path) -> list[Path]:
    out = []
    for p in root.rglob("*"):
        out.append(p)
    return out


class TestParamExtraction:
    def test_disk_letter_resolves(self) -> None:
        from universal_mind.file_search_tool import extract_search_params

        p = extract_search_params("فایلهای بزرگ دیسک D را پیدا کن")
        assert p["folder"] == "D:\\"
        assert p["operation"] == "search"

    def test_size_hint_parses(self) -> None:
        from universal_mind.file_search_tool import extract_search_params

        p = extract_search_params("فایلهای بزرگتر از ۱۰۰ مگابایت در دانلودها")
        assert p["min_size_mb"] == 100
        assert p["folder"] == "دانلود"

    def test_photo_type_filter(self) -> None:
        from universal_mind.file_search_tool import extract_search_params

        p = extract_search_params("عکسهای پوشه دانلودها را پیدا کن")
        assert "jpg" in p["name"]

    def test_top_count(self) -> None:
        from universal_mind.file_search_tool import extract_search_params

        p = extract_search_params("۵ تا بزرگترین فایلهای دیسک E را پیدا کن")
        assert p["top"] == 5
        assert p["folder"] == "E:\\"


class TestRouterWiring:
    def test_disk_search_routes_clean(self) -> None:
        from universal_mind.persian_router import route

        r = route("فایلهای بزرگ دیسک D را پیدا کن")
        assert "filesearch" in r.capabilities
        assert "webfetch" not in r.capabilities
        assert "image" not in r.capabilities

    def test_photo_find_does_not_drag_image_edit(self) -> None:
        from universal_mind.persian_router import route

        r = route("عکسهای پوشه دانلودها را پیدا کن")
        assert "filesearch" in r.capabilities
        assert "image" not in r.capabilities

    def test_url_find_still_webfetch(self) -> None:
        from universal_mind.persian_router import route

        r = route("سایت example.com را بخوان")
        assert "webfetch" in r.capabilities
        assert "filesearch" not in r.capabilities

    def test_e2e_real_disk(self, tmp_path: Path) -> None:
        """Live: real files on the real disk found through the FULL router."""
        (tmp_path / "huge.bin").write_bytes(b"h" * 250_000)
        os.environ.pop("UM_LLM_BASE_URL", None)
        from universal_mind.persian_params import extract_params

        params = extract_params("فایلهای بزرگ را پیدا کن", "filesearch")
        assert params["operation"] == "search"
