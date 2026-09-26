"""R47 wave 4 — the breathing vocabulary.

Item 10: the harvest SUGGESTS — a frequent unknown that is a plausible
typo of a real trigger word gets a proposal with the teach command.
Item 11: «چقدر یاد گرفتی؟» answers with the real ratio; teaching grows it.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from universal_mind.database_suite import DatabaseSuite
from universal_mind.run_history import RunHistory


def _db(rows: list[dict[str, Any]]) -> DatabaseSuite:
    suite = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r47w4.db"))
    RunHistory(suite)
    suite.insert_many("unknown_terms", rows)
    return suite


class TestVocabularySuggestions:
    def test_a_typo_suggests_its_real_capability(self) -> None:
        db = _db([{"term": "نمادار", "hits": 4}])
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.reflexive import answer_reflexive

            res = answer_reflexive("واژههای ناشناخته را پیشنهاد بده")
            assert res is not None
            report = str(res["agent_report"])
            assert "نمادار" in report          # the harvested word
            assert "شاید منظورت «chart» بود" in report  # the real capability
            assert "واژهی نمادار یعنی chart" in report    # the teach command

    def test_a_distant_word_is_never_guessed(self) -> None:
        db = _db([{"term": "زوکوپرین", "hits": 6}])
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.reflexive import answer_reflexive

            res = answer_reflexive("واژههای ناشناخته را پیشنهاد بده")
            assert res is not None
            report = str(res["agent_report"])
            assert "زوکوپرین" not in report  # too far — never a wild guess
            assert "شکار تمیز است" in report

    def test_junk_never_becomes_vocabulary(self) -> None:
        db = _db([{"term": "xyzq", "hits": 9}])
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.vocab_breathing import suggestions

            assert suggestions(db=db) == []  # test junk is invisible


class TestLearningRatio:
    def test_the_ratio_is_answered_honestly(self) -> None:
        db = _db([{"term": "نمادار", "hits": 4},
                  {"term": "زوکوپرین", "hits": 6}])
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.reflexive import answer_reflexive

            res = answer_reflexive("چقدر یاد گرفتی؟")
            assert res is not None
            report = str(res["agent_report"])
            assert "درصدِ یادگیریِ واژگان" in report
            # 1 of 2 resolvable (نمادار is a typo; زوکوپرین is not)
            assert "۵۰٪" in report
            assert "۲ واژهی ناشناختهی واقعی" in report

    def test_teaching_grows_the_ratio(self) -> None:
        db = _db([{"term": "نمادار", "hits": 4},
                  {"term": "زوکوپرین", "hits": 6}])
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.learned_vocab import teach
            from universal_mind.reflexive import answer_reflexive

            teach("زوکوپرین", "summary", db=db)
            res = answer_reflexive("چقدر یاد گرفتی؟")
            report = str(res["agent_report"]) if res else ""
            assert "۱۰۰٪" in report  # both resolved now

    def test_an_empty_harvest_is_stated_not_faked(self) -> None:
        db = _db([])
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.vocab_breathing import learning_ratio

            info = learning_ratio(db=db)
            assert info["total"] == 0 and info["ratio"] == 0.0
