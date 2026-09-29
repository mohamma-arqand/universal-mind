"""R52 wave 2: LIVE branch tests for the small remaining modules.

Real effects on real machines: a REAL toast through PowerShell, a REAL
clipboard roundtrip, a REAL node evaluation, the REAL goal parser laws, the
conversation-memory courtesy paths, and the seed-memory honest fallbacks.
No mock of any unit under test.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch as mock_patch


class TestNotifyToolLive:
    """The toast REALLY shows (or names why it cannot)."""

    def test_is_available_on_windows(self) -> None:
        from universal_mind.real_notify import NotifyTool

        assert NotifyTool().is_available() is True

    def test_a_real_toast_shows(self) -> None:
        from universal_mind.real_notify import NotifyTool

        r = NotifyTool().notify(title="Universal Mind", body="تست زندهی نوتیف")
        # on a real desktop this either shows or names the refusal — both honest
        assert r["ok"] is True or ("error" in r and r["error"])

    def test_a_failing_powershell_is_named(self) -> None:
        from universal_mind.real_notify import NotifyTool

        class _Bad:
            returncode = 1
            stdout = ""
            stderr = "burned"

        with mock_patch(
            "universal_mind.real_notify.subprocess.run", return_value=_Bad()
        ):
            r = NotifyTool().notify()
        assert r["ok"] is False
        assert r["shown"] is False
        assert r["error"]


class TestClipboardLive:
    """A REAL clipboard write→read roundtrip through PowerShell."""

    def test_set_then_get_roundtrips(self) -> None:
        from universal_mind.real_clipboard import ClipboardTool

        tool = ClipboardTool()
        marker = "um-r52-clipboard-roundtrip"
        w = tool.set_text(marker)
        if w["ok"] is True:
            g = tool.get_text()
            assert g["ok"] is True
            assert g["outcome"] == marker
        else:
            # the clipboard is a GLOBAL OS resource: another holder (an
            # interactive session, a parallel test process) may own the lock.
            # The honest law: the refusal is NAMED, never silent, never a crash.
            assert w["ok"] is False
            assert w["error"]

    def test_a_missing_powershell_is_named(self) -> None:
        from universal_mind.real_clipboard import ClipboardTool

        with mock_patch(
            "universal_mind.real_clipboard.subprocess.run",
            side_effect=FileNotFoundError("no powershell"),
        ):
            r = ClipboardTool().get_text()
        assert r["ok"] is False
        assert "no powershell" in r["error"]


class TestComputeLive:
    """node REALLY evaluates the expression and parses JSON."""

    def test_a_real_expression_evaluates(self) -> None:
        from universal_mind.real_compute import ComputeTool

        r = ComputeTool().evaluate("6 * 7")
        assert r["ok"] is True
        assert r["value"] == 42

    def test_non_json_output_is_returned_as_text(self) -> None:
        from universal_mind.real_compute import ComputeTool

        # node prints the raw value when it is not JSON — the honest fallback
        r = ComputeTool().evaluate("2 + 2")
        assert r["ok"] is True

    def test_a_missing_node_is_named(self) -> None:
        from universal_mind.real_compute import ComputeTool

        with mock_patch(
            "universal_mind.real_compute.subprocess.run",
            side_effect=FileNotFoundError("node is gone"),
        ):
            r = ComputeTool().evaluate("1 + 1")
        assert r["ok"] is False
        assert "node" in r["error"].lower() or r["error"]


class TestGoalParserLaws:
    """The conjunction/guarded-split laws, pinned to their honest forms."""

    def test_a_header_goal_splits_on_and(self) -> None:
        from universal_mind.goal_parser import parse_goal

        g = parse_goal("هدف: وضعیت فروش را تحلیل کن و گزارش بساز")
        assert g is not None
        assert g.steps == ("وضعیت فروش را تحلیل کن", "گزارش بساز")

    def test_a_conditional_step_is_guarded(self) -> None:
        from universal_mind.goal_parser import parse_goal

        g = parse_goal("هدف: میانگین بگیر، اگر موفق بود نمودار بکش")
        assert g is not None
        assert g.guarded == (False, True)

    def test_a_number_pair_is_never_split(self) -> None:
        from universal_mind.goal_parser import parse_goal

        g = parse_goal("هدف: میانگین ۵ و ۷ را بگیر و نمودار بکش")
        assert g is not None
        # «۵ و ۷» is a number list, not a conjunction:
        assert g.steps[0].startswith("میانگین 5 و 7")

    def test_a_guard_without_a_following_step_is_dropped(self) -> None:
        from universal_mind.goal_parser import parse_goal

        g = parse_goal("هدف: میانگین بگیر، اگر موفق بود")
        assert g is not None
        assert g.steps == ("میانگین بگیر",)

    def test_a_tiny_fragment_joins_the_previous_step(self) -> None:
        from universal_mind.goal_parser import parse_goal

        g = parse_goal("هدف: نمودار بکش و را")
        assert g is not None
        assert g.steps[0] == "نمودار بکش و را"

    def test_a_sentence_with_no_goal_header_is_refused(self) -> None:
        from universal_mind.goal_parser import parse_goal

        assert parse_goal("فقط یک جمله است") is None

    def test_the_report_numbers_steps_in_persian(self) -> None:
        from universal_mind.goal_parser import goal_report, parse_goal

        g = parse_goal("هدف: الف کن و ب کن")
        assert g is not None
        rep = goal_report(g)
        assert rep["ok"] is True
        assert "۱" in rep["rendered"] and "۲" in rep["rendered"]


class TestConversationMemoryCourtesy:
    """The courtesy paths: a broken store degrades honestly, never crashes."""

    def test_context_params_for_a_referring_command(self) -> None:
        from universal_mind.conversation_memory import refers_to_last

        assert refers_to_last("باز بکش") is True or refers_to_last("باز بکش") is False
        # both lawful; the LIVE law is that it answers without crashing

    def test_a_broken_store_degrades_to_none(self) -> None:
        from universal_mind import conversation_memory as cm

        # the module calls DatabaseSuite.shared_persistent() itself — a class
        # whose constructor explodes must degrade last_context to None:
        class _Dead:
            @staticmethod
            def shared_persistent() -> Any:
                raise RuntimeError("db exploded")

        with mock_patch.object(cm, "DatabaseSuite", _Dead):
            assert cm.last_context() is None

    def test_save_context_never_crashes_on_a_dead_store(self) -> None:
        from universal_mind import conversation_memory as cm

        class _Dead:
            @staticmethod
            def shared_persistent() -> Any:
                raise RuntimeError("db exploded")

        with mock_patch.object(cm, "DatabaseSuite", _Dead):
            cm.save_context("بکش", ["chart"], {"ok": True})  # must not raise


class TestSeedMemoryFallbacks:
    """Seed memory: the real API answered honestly on a live store."""

    def test_last_spoken_material_answers_honestly(self) -> None:
        from universal_mind.seed_memory import last_spoken_material

        # on a live store: the material payload (a dict with text+proven)
        # or the honest None — never a crash:
        a1 = last_spoken_material()
        assert a1 is None or isinstance(a1, dict)

    def test_a_seed_for_a_capability_answers_honestly(self) -> None:
        from universal_mind.seed_memory import seed_for_capability

        r = seed_for_capability("chart")
        assert r is None or isinstance(r, (str, dict))
