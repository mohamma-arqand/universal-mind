"""Tests: folder watchers — the third proactive perception channel."""

from __future__ import annotations

import os
import tempfile
from contextlib import AbstractContextManager
from unittest.mock import patch as mock_patch

import universal_mind.scheduler as sched_mod
from universal_mind.scheduler import (
    list_watchers,
    parse_folder_watcher,
    register,
    scan_watchers,
)


def _isolated() -> AbstractContextManager[object]:
    """One fresh temp store per test — the operator's real watchers are never
    touched (the 68-schedule lesson, applied from the start this time)."""
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    return mock_patch.object(sched_mod, "_store", lambda: suite)


class TestParseFolderWatcher:
    def test_downloads_folder_by_persian_name(self) -> None:
        watcher = parse_folder_watcher(
            "هر وقت در پوشهی دانلود فایل جدید آمد، فایلش را تحلیل تصویر کن"
        )
        assert watcher is not None
        assert watcher["folder"].endswith("Downloads")
        assert "تحلیل تصویر" in watcher["action"]

    def test_absolute_folder(self) -> None:
        folder = tempfile.mkdtemp(prefix="um-watchparse-")
        watcher = parse_folder_watcher(
            f"هر وقت در پوشهی {folder} فایل جدید آمد، میانگین ۱ و ۲ را حساب کن"
        )
        assert watcher is not None
        assert watcher["folder"] == folder

    def test_not_a_watcher_is_none(self) -> None:
        assert parse_folder_watcher("هر روز ساعت ۸ گزارش بده") is None

    def test_a_watcher_is_not_a_time_schedule(self) -> None:
        """Register routes the sentence to the watcher path, not the clock."""
        with _isolated():
            folder = tempfile.mkdtemp(prefix="um-w-reg-")
            result = register(f"هر وقت در پوشهی {folder} فایل جدید آمد، نمودار بکش")
            assert result["ok"] is True
            assert result.get("watcher") is True
            assert list_watchers()[0]["folder"] == folder


class TestScanWatchers:
    def test_baseline_learns_without_firing(self) -> None:
        """The first scan only learns the folder — reacting to pre-existing
        files would be reacting to the past, not to a new event."""
        with _isolated():
            folder = tempfile.mkdtemp(prefix="um-w-base-")
            with open(os.path.join(folder, "old.txt"), "w", encoding="utf-8") as f:
                f.write("x")
            register(f"هر وقت در پوشهی {folder} فایل جدید آمد، میانگین ۱ و ۲ را حساب کن")
            first = scan_watchers()
            assert first["count"] == 0  # the pre-existing file fired nothing

    def test_new_file_fires_once(self) -> None:
        """A genuinely new file runs the action ONCE (idempotent after)."""
        with _isolated():
            folder = tempfile.mkdtemp(prefix="um-w-fire-")
            register(f"هر وقت در پوشهی {folder} فایل جدید آمد، میانگین ۱ و ۵ را حساب کن")
            scan_watchers()  # baseline
            with open(os.path.join(folder, "new.txt"), "w", encoding="utf-8") as f:
                f.write("hello")
            second = scan_watchers()
            assert second["count"] == 1
            assert second["fired"][0]["file"] == "new.txt"
            assert second["fired"][0]["ok"] is True  # the action REALLY ran
            third = scan_watchers()
            assert third["count"] == 0  # never re-fire a known file

    def test_empty_folder_baseline_is_not_forever(self) -> None:
        """An EMPTY folder must still count as learned (the __baseline__
        marker) — otherwise every later file would look pre-existing."""
        with _isolated():
            folder = tempfile.mkdtemp(prefix="um-w-empty-")
            register(f"هر وقت در پوشهی {folder} فایل جدید آمد، میانگین ۱ و ۲ را حساب کن")
            scan_watchers()  # baseline over an EMPTY folder
            with open(os.path.join(folder, "first.txt"), "w", encoding="utf-8") as f:
                f.write("x")
            second = scan_watchers()
            assert second["count"] == 1  # fires: the folder was learned empty

    def test_file_substitution_in_the_action(self) -> None:
        """«فایلش» in the action is replaced by the real absolute path."""
        with _isolated():
            folder = tempfile.mkdtemp(prefix="um-w-sub-")
            register(f"هر وقت در پوشهی {folder} فایل جدید آمد، فایلش را تحلیل تصویر کن")
            scan_watchers()  # baseline
            with open(os.path.join(folder, "img.png"), "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n")  # a PNG header — real bytes
            second = scan_watchers()
            assert second["count"] == 1
            fired_action = second["fired"][0]["action"]
            assert os.path.join(folder, "img.png") in fired_action


class TestWatcherInTick:
    def test_tick_scans_watchers_too(self) -> None:
        """The tick sweeps watchers as part of its proactive pass."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path("scripts").resolve()))
        from scheduler_tick import tick

        with _isolated():
            folder = tempfile.mkdtemp(prefix="um-w-tick-")
            register(f"هر وقت در پوشهی {folder} فایل جدید آمد، میانگین ۱ و ۲ را حساب کن")
            tick()  # baseline inside the tick
            with open(os.path.join(folder, "note.txt"), "w", encoding="utf-8") as f:
                f.write("x")
            with mock_patch("universal_mind.real_notify.NotifyTool.notify"):
                result = tick()
        assert result.get("watcher_fired", 0) >= 1  # the watcher swept in the tick
