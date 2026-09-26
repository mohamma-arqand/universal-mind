"""R47 wave 2 — prediction from MEANING, not just counting.

Item 4: the semantic anchor — the nearest past command by TF-IDF joins
the prediction when close enough; distant or tiny history = untouched.
Item 5: «آیا ... کار میکند؟» answers with the real prediction, no run.
Item 6: a weak chain with a proven semantic twin earns a semantic rival
in the gate, named in the reasoning — never silent.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from universal_mind.database_suite import DatabaseSuite
from universal_mind.run_history import RunHistory


def _db(rows: list[dict[str, Any]]) -> DatabaseSuite:
    suite = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r47w2.db"))
    RunHistory(suite)
    suite.insert_many("run_history", rows)
    return suite


_TWIN_HISTORY = [
    {"command": "خلاصه کن و نمودارش را بکش", "route": "summary,chart",
     "succeeded": 1, "excellence": 0.92},
    {"command": "خلاصه کن و نمودارش را بکش", "route": "summary,chart",
     "succeeded": 1, "excellence": 0.90},
]


class TestSemanticPredictor:
    def test_unseen_chain_borrows_the_anchor_story(self) -> None:
        db = _db(_TWIN_HISTORY)
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.semantic_predictor import predict_semantic

            pred = predict_semantic(
                "خلاصه کن و نمودارش را رسم کن", ("never_ran",))
            assert pred.semantic_anchor is not None
            assert pred.semantic_anchor["command"] == "خلاصه کن و نمودارش را بکش"
            assert pred.semantic_anchor["similarity"] >= 0.5
            # the unseen chain borrows the anchor's 100% success wholesale
            assert pred.success_probability == 1.0
            assert pred.tier == "strong"

    def test_seen_chain_blends_60_40(self) -> None:
        rows = _TWIN_HISTORY + [
            {"command": "خلاصه کن و نمودارش را رسم کن", "route": "chart",
             "succeeded": 1, "excellence": 0.8},
            {"command": "خلاصه کن و نمودارش را رسم کن", "route": "chart",
             "succeeded": 0, "excellence": 0.3},
        ]
        db = _db(rows)
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.semantic_predictor import predict_semantic
            from universal_mind.success_predictor import predict_success

            base = predict_success(("chart",))
            pred = predict_semantic(
                "خلاصه کن و نمودارش را رسم کن", ("chart",))
            # base p = (1+1)/(2+2) = 0.5; anchor = 1.0 → 0.6*0.5 + 0.4*1.0
            expected = round(0.6 * base.success_probability + 0.4 * 1.0, 4)
            assert abs(pred.success_probability - expected) < 1e-4

    def test_distant_command_is_untouched(self) -> None:
        db = _db(_TWIN_HISTORY)
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.semantic_predictor import predict_semantic

            pred = predict_semantic("فایل بکاپ را پاک کن", ("never_ran",))
            assert pred.semantic_anchor is None
            assert pred.anchor_similarity == 0.0
            # the base prediction (global fallback) came back untouched
            from universal_mind.success_predictor import predict_success

            base = predict_success(("never_ran",))
            assert pred.success_probability == base.success_probability


class TestPreRunQuestion:
    def test_the_question_is_answered_without_running(self) -> None:
        db = _db(_TWIN_HISTORY)
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.reflexive import answer_reflexive

            res = answer_reflexive("آیا خلاصه کن و نمودارش را رسم کار میکند؟")
            assert res is not None and res.get("ok") is True
            report = str(res["agent_report"])
            assert "پیشبینی" in report          # the real prediction
            assert "ریسکِ" in report            # the tier is spoken
            # nothing was RUN for the question itself
            n = db.query("SELECT COUNT(*) AS n FROM run_history")["rows"][0]["n"]
            assert n == 2                        # only the seed rows

    def test_anchor_line_names_the_twin(self) -> None:
        db = _db(_TWIN_HISTORY)
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.reflexive import answer_reflexive

            res = answer_reflexive("آیا خلاصه کن و نمودارش را رسم کار میکند؟")
            assert res is not None
            report = str(res["agent_report"])
            assert "مثل" in report and "خلاصه کن و نمودارش را بکش" in report


class TestSemanticRival:
    def test_weak_chain_earns_a_named_semantic_rival(self) -> None:
        rows = _TWIN_HISTORY + [
            {"command": "خلاصه کن و نمودارش را رسم کن", "route": "weak_chain",
             "succeeded": 0, "excellence": 0.1},
            {"command": "خلاصه کن و نمودارش را رسم کن", "route": "weak_chain",
             "succeeded": 0, "excellence": 0.1},
            {"command": "خلاصه کن و نمودارش را رسم کن", "route": "weak_chain",
             "succeeded": 0, "excellence": 0.1},
        ]
        db = _db(rows)
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.quality_gate import run_with_quality_gate

            ran: list[tuple[str, ...]] = []

            def runner(route: tuple[str, ...]) -> dict[str, Any]:
                ran.append(route)
                if "weak_chain" in route:
                    return {"ok": False, "error": "شکست"}
                return {"ok": True, "result": {"route": list(route)},
                        "agent_report": "ساخته شد"}

            outcome = run_with_quality_gate(
                "خلاصه کن و نمودارش را رسم کن", ("weak_chain",),
                runner, bar=0.75)
            # the semantic rival really ran
            assert ("summary", "chart") in ran
            # and it is named in the reasoning — never silent
            assert "رقیبِ معنایی" in outcome.reasoning
            assert "summary → chart" in outcome.reasoning

    def test_strong_chain_never_pays_for_a_rival(self) -> None:
        rows = _TWIN_HISTORY + [
            {"command": "مسیر قوی", "route": "strong_chain",
             "succeeded": 1, "excellence": 0.95},
            {"command": "مسیر قوی", "route": "strong_chain",
             "succeeded": 1, "excellence": 0.94},
        ]
        db = _db(rows)
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.quality_gate import run_with_quality_gate

            ran: list[tuple[str, ...]] = []

            def runner(route: tuple[str, ...]) -> dict[str, Any]:
                ran.append(route)
                return {"ok": True, "result": {}, "agent_report": "ساخته شد"}

            outcome = run_with_quality_gate(
                "مسیر قوی", ("strong_chain",), runner, bar=0.75)
            assert ("summary", "chart") not in ran  # no semantic rival
            assert "رقیبِ معنایی" not in outcome.reasoning
