"""R63 P1 — the teach path can no longer poison the route overlay.

The live sweep caught a serious routing bug: a LONG colon-clause
sentence («قابلیت جدید یاد بگیر: وقتی گفتم برق رفت یعنی …») was
swallowed by the small-word-definition parser, which grabbed its last
«X یعنی Y» clause and taught word='رفت' → cap='برق'. Every later
sentence containing «رفت» mis-routed, and the run died on
«command 'unused' is not allowlisted».

Two laws now hold:
- a definition must BE the sentence (pattern spans the whole command);
- teach() only accepts REAL capabilities — anything else is a NAMED
  refusal listing the known ones.
"""

from __future__ import annotations

import pytest

from universal_mind.database_suite import DatabaseSuite
from universal_mind.learned_vocab import parse_definition, teach


@pytest.fixture(autouse=True)
def _clean_vocab():
    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM learned_vocab WHERE word IN ('زرشک', 'برق', 'رفت')")
    yield
    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM learned_vocab WHERE word IN ('زرشک', 'برق', 'رفت')")


class TestTheDefinitionMustBeTheSentence:
    def test_a_colon_clause_sentence_is_not_a_definition(self) -> None:
        assert parse_definition(
            "یک قابلیت جدید یاد بگیر: وقتی گفتم برق رفت یعنی برق وایرلس قطع شد"
        ) is None

    def test_a_small_definition_still_parses(self) -> None:
        d = parse_definition("واژهی زرشک یعنی داده")
        assert d == {"word": "زرشک", "cap": "داده"}

    def test_a_bare_definition_without_marker_parses(self) -> None:
        d = parse_definition("زرشک یعنی داده")
        assert d == {"word": "زرشک", "cap": "داده"}

    def test_punctuation_around_the_definition_is_allowed(self) -> None:
        d = parse_definition("زرشک یعنی داده.")
        assert d is not None and d["cap"] == "داده"


class TestTeachOnlyAcceptsRealCapabilities:
    def test_a_known_operator_word_maps_and_stores(self) -> None:
        r = teach("زرشک", "داده")
        assert r["ok"] is True
        assert r["capability"] == "data"

    def test_an_unknown_capability_is_a_named_refusal(self) -> None:
        r = teach("برق", "وایرلس قطع شد")
        assert r["ok"] is False
        assert "قابلیتی که بشناسم نیست" in r["error"]
        assert "data" in r["error"]  # the known list is named

    def test_a_real_registry_capability_is_accepted(self) -> None:
        r = teach("نمودارچه", "chart")
        assert r["ok"] is True
        assert r["capability"] == "chart"

    def test_nothing_is_stored_on_refusal(self) -> None:
        teach("برق", "وایرلس قطع شد")
        rows = DatabaseSuite.shared_persistent().query(
            "SELECT word FROM learned_vocab WHERE word = 'برق'").get("rows", [])
        assert rows == []


class TestTheRouterIsNoLongerPoisoned:
    def test_the_big_sentence_no_longer_teaches(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run(
            "یک قابلیت جدید یاد بگیر: وقتی گفتم برق رفت یعنی برق وایرلس قطع شد")
        rows = DatabaseSuite.shared_persistent().query(
            "SELECT word, capability FROM learned_vocab").get("rows", [])
        assert all(r["word"] != "رفت" for r in rows)
        # and the sentence itself is honestly unknown, not a broken run
        assert p.get("route") != ["برق"]
