"""R53 wave-5 — SHA-256 DUPLICATES, preview-first, no silent deletes.

«فایلهای تکراری را پاک کن» — the DELETE LAW of this house: nothing is
deleted without the operator's explicit confirm; same-size is only a
candidate, SHA-256 is the only evidence; the original (earliest modified)
of each group is kept; every deletion is listed for rollback.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest


@pytest.fixture()
def dup_tree(tmp_path: Path) -> Path:
    """A tree with 2 real duplicate pairs and 2 same-size-but-different files."""
    d = tmp_path / "dups"
    d.mkdir()
    payload = os.urandom(4096)  # real content
    (d / "a1.bin").write_bytes(payload)
    (d / "a2.bin").write_bytes(payload)          # TRUE duplicate of a1
    other = os.urandom(4096)
    (d / "b1.bin").write_bytes(other)
    (d / "b2.bin").write_bytes(other)             # TRUE duplicate of b1
    (d / "c1.bin").write_bytes(os.urandom(4096))  # same size, DIFFERENT bytes
    (d / "small.txt").write_text("s", encoding="utf-8")
    return d


class TestFind:
    def test_only_true_duplicates_group(self, dup_tree: Path) -> None:
        from universal_mind.file_dedupe_tool import FileDedupeTool

        res = FileDedupeTool().find(str(dup_tree), min_size=1024)
        assert res["ok"] is True
        assert res["n_groups"] == 2  # c1 is same-size but NOT a duplicate
        names = {Path(f).name for g in res["groups"] for f in g["files"]}
        assert "c1.bin" not in names

    def test_wasted_bytes_are_real(self, dup_tree: Path) -> None:
        from universal_mind.file_dedupe_tool import FileDedupeTool

        res = FileDedupeTool().find(str(dup_tree), min_size=1024)
        # 2 groups × 4096 bytes wasted each = 8192 — computed, not estimated
        assert res["wasted_bytes"] == 8192

    def test_find_never_deletes(self, dup_tree: Path) -> None:
        before = sorted(p.name for p in dup_tree.iterdir())
        from universal_mind.file_dedupe_tool import FileDedupeTool

        FileDedupeTool().find(str(dup_tree), min_size=1024)
        after = sorted(p.name for p in dup_tree.iterdir())
        assert before == after  # THE READ-ONLY LAW


class TestClean:
    def test_preview_is_the_default(self, dup_tree: Path) -> None:
        from universal_mind.file_dedupe_tool import FileDedupeTool

        res = FileDedupeTool().clean(str(dup_tree), min_size=1024)
        assert res["deleted"] == []  # nothing deleted without confirm
        assert res["preview_only"] is True
        assert (dup_tree / "a2.bin").exists()

    def test_confirm_deletes_copies_keeps_originals(self, dup_tree: Path) -> None:
        """«تأیید کن» deletes the LATER copies, keeps the earliest (original)."""
        old = time.time() - 10000
        os.utime(dup_tree / "a1.bin", (old, old))  # a1 = the original
        from universal_mind.file_dedupe_tool import FileDedupeTool

        res = FileDedupeTool().clean(str(dup_tree), confirm=True, min_size=1024)
        assert res["ok"] is True
        assert res["n_deleted"] == 2
        assert (dup_tree / "a1.bin").exists()   # the original KEPT
        assert not (dup_tree / "a2.bin").exists()  # the copy GONE
        assert (dup_tree / "b1.bin").exists()
        assert not (dup_tree / "b2.bin").exists()
        # the same-size-different-content file survived (never was a duplicate)
        assert (dup_tree / "c1.bin").exists()

    def test_deleted_paths_are_listed_for_rollback(self, dup_tree: Path) -> None:
        from universal_mind.file_dedupe_tool import FileDedupeTool

        res = FileDedupeTool().clean(str(dup_tree), confirm=True, min_size=1024)
        assert len(res["deleted"]) == 2
        assert all(Path(p).is_absolute() or p for p in res["deleted"])


class TestParamsAndRouter:
    def test_pak_without_taeid_is_preview(self) -> None:
        from universal_mind.persian_params import extract_params

        p = extract_params("فایلهای تکراری در دانلودها را پاک کن", "filededupe")
        assert p["operation"] == "clean"
        assert p["confirm"] is False  # «پاک» arms it; only «تأیید» fires it

    def test_pak_with_taeid_confirms(self) -> None:
        from universal_mind.persian_params import extract_params

        p = extract_params("فایلهای تکراری در دانلودها را پاک کن — تأیید کن", "filededupe")
        assert p["operation"] == "clean"
        assert p["confirm"] is True

    def test_bare_find_is_preview_operation(self) -> None:
        from universal_mind.persian_params import extract_params

        p = extract_params("فایلهای تکراری در دیسک D را نشان بده", "filededupe")
        assert p["operation"] == "find"

    def test_router_routes_dedupe(self) -> None:
        from universal_mind.persian_router import route

        r = route("فایلهای تکراری را پاک کن")
        assert "filededupe" in r.capabilities
