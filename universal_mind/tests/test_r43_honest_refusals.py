"""Tests: R43 — the honest refusal classes + the vocabulary truth.

Live audit findings, locked:
1. «جستجو کن» (no URL) recorded 176 rows as FAILURES — a missing-parameter
   question poisoned the success predictor. Now: outcome_class='needs_param',
   filtered out of every learning read.
2. The err_text read was DEAD — syn.output has no 'errors' key (they live in
   sub_outputs), so even 'blocked_env' never fired from this path.
3. «موسیقی پخش کن» routed to SPEECH (reading text aloud!) — media is the
   real capability. «متن بنویس» routed to CLIPBOARD — writing a durable text
   is a pdf, and the explicit intent wins over the bare «بنویس».
"""

from __future__ import annotations

from contextlib import AbstractContextManager, contextmanager
from typing import Any, Iterator


def _isolated() -> AbstractContextManager[Any]:
    """One isolated store for a run + read-back."""
    import tempfile
    from pathlib import Path
    from unittest.mock import patch as mock_patch

    from universal_mind.database_suite import DatabaseSuite

    @contextmanager
    def _ctx() -> Iterator[Any]:
        suite = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r43.db"))
        with mock_patch.object(
            DatabaseSuite, "shared_persistent", classmethod(lambda cls: suite)
        ):
            yield suite

    return _ctx()


class TestNeedsParamClass:
    """A missing-parameter refusal is a QUESTION, not a chain failure."""

    def test_search_without_url_records_needs_param(self) -> None:
        from universal_mind.persian_router import route_and_run

        with _isolated() as suite:
            route_and_run("جستجو کن")
            rows = suite.query(
                "SELECT command, succeeded, outcome_class FROM run_history "
                "ORDER BY id DESC LIMIT 1"
            )["rows"]
            last = rows[0] if rows else {}
        assert last, "the run must be recorded"
        assert last["succeeded"] == 0  # honest: it did not run
        assert last["outcome_class"] == "needs_param"  # but it is not a failure

    def test_the_predictor_ignores_needs_param_rows(self) -> None:
        from universal_mind.persian_router import route_and_run
        from universal_mind.success_predictor import predict_success

        with _isolated():
            # 3 questions, 0 real runs — the predictor must see NOTHING.
            for _ in range(3):
                route_and_run("جستجو کن")
            p = predict_success(("webfetch",))
            assert p.evidence_runs == 0  # the questions taught no pessimism

    def test_persian_speech_still_blocks_env(self) -> None:
        """The blocked_env class still fires through the FIXED err_text read."""
        from universal_mind.persian_router import route_and_run

        with _isolated() as suite:
            route_and_run("میانگین ۴ و ۶ را حساب کن و بلند بخوان")
            rows = suite.query(
                "SELECT command, succeeded, outcome_class FROM run_history "
                "ORDER BY id DESC LIMIT 1"
            )["rows"]
            last = rows[0] if rows else {}
        # On this machine: no Persian SAPI voice → blocked_env (honest env
        # refusal). On a machine WITH the voice it succeeds. Either way it
        # must NEVER be an unclassed failure.
        assert last["outcome_class"] in ("blocked_env", "")


class TestVocabularyTruth:
    """The routed capability must MEAN what the operator said."""

    def test_music_play_is_media_not_speech(self) -> None:
        from universal_mind.persian_router import route

        r = route("موسیقی پخش کن")
        assert "media" in r.capabilities
        assert "speech" not in r.capabilities  # playing a file is not reading

    def test_write_text_is_a_document_not_the_clipboard(self) -> None:
        from universal_mind.persian_router import route

        r = route("متن بنویس که سلام دنیا")
        assert r.capabilities == ("pdf",)
        assert "clipboard" not in r.capabilities

    def test_read_aloud_is_still_speech(self) -> None:
        from universal_mind.persian_router import route

        r = route("میانگین ۴ و ۶ را حساب کن و بلند بخوان")
        assert "speech" in r.capabilities

    def test_clipboard_send_still_works(self) -> None:
        from universal_mind.persian_router import route

        r = route("این متن را برایم بفرست")
        assert "clipboard" in r.capabilities
        assert "pdf" not in r.capabilities
