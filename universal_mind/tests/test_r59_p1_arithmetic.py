"""R59 P1 — arithmetic QUESTIONS answered by the real compute path.

Measured gaps (the 17-command sweep): «جمع ۲ و ۵ چنده؟» returned «نشناختم»
while compute (a real node evaluator) sat unused — AND, worse, the params
layer built `5.0 + 3.0` for «۵ منهای ۳»: the numbers were right and the
OPERATOR was a lie. Both fixed: the question routes to compute, and the verb
in the sentence picks the operator.
"""

from __future__ import annotations

from universal_mind.persian_params import extract_params
from universal_mind.persian_router import route


class TestOperatorFromTheSentence:
    def test_minus(self) -> None:
        assert extract_params("۵ منهای ۳ چنده؟", "compute")["expression"] == "5.0 - 3.0"

    def test_multiply(self) -> None:
        assert extract_params("۴ ضرب‌در ۶ چنده؟", "compute")["expression"] == "4.0 * 6.0"

    def test_divide(self) -> None:
        assert extract_params("۲۰ تقسیم بر ۴ چند است؟", "compute")["expression"] == "20.0 / 4.0"

    def test_power(self) -> None:
        assert extract_params("۲ به توان ۱۰ چنده؟", "compute")["expression"] == "2.0 ** 10.0"

    def test_plus_stays_the_default(self) -> None:
        # an unknown verb keeps the pre-existing honest behaviour
        assert extract_params("جمع ۲ و ۵ چنده؟", "compute")["expression"] == "2.0 + 5.0"

    def test_a_single_number_yields_no_expression(self) -> None:
        assert "expression" not in extract_params("۵ چنده؟", "compute")


class TestTheQuestionRoutes:
    def test_arithmetic_questions_reach_compute(self) -> None:
        for cmd in ("جمع ۲ و ۵ چنده؟", "۵ منهای ۳ چنده؟", "۲ به توان ۱۰ چنده؟"):
            assert "compute" in route(cmd).capabilities, cmd


class TestLiveAnswers:
    """End to end through the REAL router+node: the answers are Persian."""

    def test_minus_answers_two(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("۵ منهای ۳ چنده؟")
        assert p["ok"] is True
        assert "نتیجه ۲" in p["agent_report"]

    def test_power_answers_1024(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("۲ به توان ۱۰ چنده؟")
        assert p["ok"] is True
        # ۱۰۲۴ with Persian digits
        assert "۱۰۲۴" in p["agent_report"] or "1024" in str(p["result"])

    def test_divide_answers_five(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("۲۰ تقسیم بر ۴ چند است؟")
        assert p["ok"] is True
        assert "نتیجه ۵" in p["agent_report"]
