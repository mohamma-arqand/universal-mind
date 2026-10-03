"""R65 P1 — «اسمم چیه؟» answers from the operator's own memory first.

The sweep caught the question falling to the llm refusal while
«یادت باشد اسم من علی است» sat in named_memory — a question about the
OPERATOR's own facts must be answered from the operator's own store.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clean():
    from universal_mind.database_suite import DatabaseSuite

    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM named_memory WHERE fact LIKE '%اسم من گواه-r65%'")
    yield
    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM named_memory WHERE fact LIKE '%اسم من گواه-r65%'")


class TestThePersonalMemory:
    def test_a_stored_name_answers_from_memory(self) -> None:
        from universal_mind.persian_router import route_and_run

        route_and_run("یادت باشد اسم من گواه-r65 است")
        p = route_and_run("اسمم چیه؟")
        assert p["route"] == ["conversational"]  # never the llm refusal
        rep = p["agent_report"]
        assert "گواه-r65" in rep
        assert "مدل زبانی" not in rep

    def test_nothing_stored_teaches_the_enabling_sentence(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("من کیم؟")
        rep = p["agent_report"]
        assert ("یادم نیست" in rep) or ("اسمت را یادم نیست" in rep)
        assert "یادت باشد اسم من" in rep  # the exact enabling sentence

    def test_the_name_question_never_reaches_llm(self) -> None:
        from universal_mind.persian_router import route_and_run

        for cmd in ("اسمم چیه؟", "اسم من چیه؟", "نامم چیست؟"):
            p = route_and_run(cmd)
            assert p["route"] != ["llm"], cmd
