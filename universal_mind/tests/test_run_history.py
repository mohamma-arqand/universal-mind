"""Tests for run history + the chain advisor (learn from real runs)."""

from __future__ import annotations

import uuid

from universal_mind.run_history import ChainAdvisor, RunHistory


def _isolated_history() -> RunHistory:
    """A fresh TEMP history per test — isolated from the real persistent one,
    so the advisor tests never see (or pollute) the operator's actual history."""
    from universal_mind.database_suite import DatabaseSuite

    return RunHistory(DatabaseSuite())  # default temp db: thrown away per test


def _unique_history() -> RunHistory:
    """The real persistent history (for the persistence tests only)."""
    return RunHistory()


class TestRunHistory:
    def test_record_and_query_roundtrip(self) -> None:
        history = _unique_history()
        history.record("میانگین ۲ و ۴", ["data"], True)
        history.record("فرمان شکستخورده", ["data"], False)
        runs = history.successful_runs()
        assert any(r.command == "میانگین ۲ و ۴" and r.route == ("data",) for r in runs)

    def test_failed_runs_are_never_recommended(self) -> None:
        history = _isolated_history()
        history.record("فقط شکست", ["data"], False)
        assert history.successful_runs() == []  # a failed run is not advice

    def test_history_survives_a_fresh_instance(self) -> None:
        history = _unique_history()
        marker = f"ماندگاری {uuid.uuid4().hex[:6]}"
        history.record(marker, ["media"], True)
        fresh = RunHistory()
        assert any(r.command == marker for r in fresh.successful_runs())


class TestChainAdvisor:
    def test_no_history_no_advice(self) -> None:
        """A fresh advisor with an empty honest store gives no advice."""
        advisor = ChainAdvisor(_isolated_history())
        assert advisor.advise("میانگین حساب کن") is None

    def test_advises_the_chain_that_succeeded_before(self) -> None:
        """After a successful data→chart run, a similar command is advised
        that same chain — evidence-based, not guessed."""
        history = _isolated_history()
        marker = uuid.uuid4().hex[:6]
        history.record(f"میانگین و نمودار {marker}", ["data", "chart"], True)
        advisor = ChainAdvisor(history)
        advice = advisor.advise(f"میانگین این اعداد و نمودارش {marker}")
        assert advice is not None
        assert advice.route == ("data", "chart")
        assert advice.similarity >= 2  # shared: میانگین + نمودار

    def test_unrelated_command_gets_no_advice(self) -> None:
        history = _isolated_history()
        history.record("فشردهسازی آرشیو", ["archive"], True)
        advisor = ChainAdvisor(history)
        # No vocabulary overlap with the stored run → honest None.
        assert advisor.advise("میانگین اعداد را حساب کن") is None

    def test_higher_overlap_wins(self) -> None:
        history = _isolated_history()
        history.record("آ", ["data"], True)  # weak match seed (no vocab)
        marker = uuid.uuid4().hex[:6]
        history.record(f"میانگین و خوشهبندی و نمودار {marker}", ["data", "ai", "chart"], True)
        advisor = ChainAdvisor(history)
        advice = advisor.advise(f"میانگین و خوشهبندی بکن {marker}")
        assert advice is not None
        assert "ai" in advice.route  # the richer match wins

    def test_winning_record_beats_single_similarity(self) -> None:
        """A chain that succeeded 3 times beats a chain seen once, even when
        both overlap the command (the learned winning record matters)."""
        history = _isolated_history()
        marker = uuid.uuid4().hex[:6]
        # One weakly-seen route...
        history.record(f"میانگین و خوشهبندی فقطیکبار {marker}", ["data", "ai"], True)
        # ...and a route that succeeded three times.
        for _ in range(3):
            history.record(f"میانگین و نمودار {marker}", ["data", "chart"], True)
        advisor = ChainAdvisor(history)
        advice = advisor.advise(f"میانگین و نمودار را بکش {marker}")
        assert advice is not None
        assert advice.route == ("data", "chart")
        assert advice.succeeded_runs == 3

    def test_advice_reports_how_many_times_it_won(self) -> None:
        history = _isolated_history()
        marker = uuid.uuid4().hex[:6]
        for _ in range(2):
            history.record(f"محاسبه {marker}", ["data"], True)
        advice = ChainAdvisor(history).advise(f"محاسبه کن {marker}")
        assert advice is not None
        assert advice.succeeded_runs == 2

    def test_saved_chain_is_a_candidate_too(self) -> None:
        """A saved chain whose NAME overlaps the command is advised — explicit
        operator trust, even with no run history for it."""
        import string
        import uuid

        from universal_mind.chains_store import ChainsStore

        letters = string.ascii_lowercase
        suffix = "".join(letters[b % 26] for b in uuid.uuid4().bytes[:6])
        store = ChainsStore()
        saved = store.save(f"میانگین و نمودار سفارشی {suffix}", ["data", "chart"])
        try:
            history = _isolated_history()  # empty run history
            advice = ChainAdvisor(history).advise(f"میانگین و نمودار بکش {suffix}")
            assert advice is not None
            assert advice.route == ("data", "chart")
        finally:
            store.delete(saved.chain_id)

    def test_end_to_end_route_and_run_records_history(self) -> None:
        """route_and_run writes the real run to the persistent history."""
        from universal_mind.persian_router import route_and_run

        marker = uuid.uuid4().hex[:6]
        route_and_run(f"محاسبه کن {marker}")
        history = RunHistory()
        assert any(marker in r.command and r.route == ("data",)
                   for r in history.successful_runs())


