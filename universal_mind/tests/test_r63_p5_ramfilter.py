"""R63 P5 — «کدام پروسه‌ها بیشتر از ۱ گیگ رم می‌خورند؟» is a FILTER.

The old machine view answered a generic top-5-by-CPU no matter what
the operator asked — a question with a RAM floor got an answer about
something else. The RAM floor now selects the answer's kind:
- the real process list, filtered by the floor, sorted by RAM;
- a floor nothing passes is the honest «هیچ پردازشی … نمی‌خورد»
  (measured live: no process was above 1 GiB, and the answer said
  so instead of showing the top-5 anyway);
- the generic heavy-processes question keeps its own answer.
"""

from __future__ import annotations


class TestTheRamFilter:
    def test_a_gib_floor_answers_filtered(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("کدام پروسه‌ها بیشتر از ۱ گیگ رم می‌خورند؟")
        rep = p["agent_report"]
        # either the honest empty answer or the filtered list — NEVER
        # the generic CPU top-5
        assert ("هیچ پردازشی" in rep) or ("پردازش بیش از" in rep)
        assert "مرتب بر CPU" not in rep

    def test_a_low_floor_lists_real_processes(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("کدام پروسه‌ها بیشتر از ۱ مگ رم می‌خورند؟")
        rep = p["agent_report"]
        assert "پردازش بیش از" in rep  # something is above 1 MB, always
        assert "رم:" in rep

    def test_megabytes_work_too(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("کدام پروسه‌ها بیشتر از ۵۰۰ مگ رم می‌خورند؟")
        rep = p["agent_report"]
        assert ("هیچ پردازشی" in rep) or ("پردازش بیش از" in rep)

    def test_the_generic_question_unchanged(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("پروسه‌های پرمصرف را نشان بده")
        assert "مرتب بر CPU" in p["agent_report"]


class TestTheUnitMath:
    def test_gig_becomes_mib(self) -> None:
        from universal_mind.window_view import processes_by_ram

        res = processes_by_ram(min_mb=1024.0)
        assert res["ok"] is True
        assert all(p_["ram_mb"] >= 1024.0 for p_ in res["processes"])

    def test_the_floor_filters_for_real(self) -> None:
        from universal_mind.window_view import processes_by_ram

        res = processes_by_ram(min_mb=100000.0)  # nothing is this big
        assert res["processes"] == []
