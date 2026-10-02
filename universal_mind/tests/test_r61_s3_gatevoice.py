"""R61-S3 — the shrunken-route confession and the gate that speaks.

«گزارش بساز و برایم ایمیل کن» ran only the PDF half: the quality gate's
semantic rival shipped the smaller successful route and the report said
NOTHING about the dropped half. Two laws now hold:

1. gate_reasoning is always rendered in the Persian report (a repair the
   operator cannot see is a silent mutation of their own sentence).
2. When a repair ships a route SMALLER than planned, the dropped
   capabilities are named with the remedy.
"""

from __future__ import annotations

from universal_mind.persian_report import persian_report


class TestTheGateSpeaks:
    def test_gate_reasoning_is_rendered_in_the_report(self) -> None:
        payload = {
            "ok": True, "route": ["pdf"],
            "result": {"pdf": {"bytes": 33900, "pages": 1, "path": "x.pdf"}},
            "errors": {},
            "gate_reasoning": "داوری مسیر اصلی ۰.۷۵ بود — ترمیم خودکار انجام شد",
        }
        rep = persian_report(payload)
        assert "⚖" in rep and "ترمیم خودکار" in rep

    def test_a_report_without_the_gate_is_unchanged(self) -> None:
        payload = {
            "ok": True, "route": ["pdf"],
            "result": {"pdf": {"bytes": 33900, "pages": 1, "path": "x.pdf"}},
            "errors": {},
        }
        rep = persian_report(payload)
        assert "⚖" not in rep


class TestTheShrunkenRouteConfession:
    def _payload_with_dropped(self, dropped_fa: str) -> dict[str, object]:
        return {
            "ok": True, "route": ["pdf"],
            "result": {"pdf": {"bytes": 33900, "pages": 1, "path": "x.pdf"}},
            "errors": {},
            "gate_reasoning": (
                f"داوری مسیر اصلی ۰.۷۵ بود — ترمیم خودکار انجام شد "
                f"⚠ نکتهٔ صادقانه: بخشِ «{dropped_fa}» از جملهٔ تو در این اجرا "
                "اجرا نشد (رانِ ترمیمی مسیر کوچک‌تری برد) — اگر همان بخش را "
                "می‌خواهی، جداگانه بگو تا اجرا کنم."
            ),
        }

    def test_the_dropped_capability_is_named_with_the_remedy(self) -> None:
        rep = persian_report(self._payload_with_dropped("ایمیل"))
        assert "اجرا نشد" in rep
        assert "ایمیل" in rep
        assert "جداگانه بگو" in rep

    def test_the_confession_is_persian(self) -> None:
        rep = persian_report(self._payload_with_dropped("ایمیل"))
        assert "صادقانه" in rep


class TestEndToEnd:
    def test_the_two_verb_sentence_names_its_dropped_half(self) -> None:
        # live: BOTH outcomes are honest — (a) the gate ships the smaller
        # route and the report confesses the dropped half, or (b) the whole
        # chain runs and email's missing-recipient failure is NAMED in the
        # report. Either way, no half of the sentence dies silently.
        from universal_mind.persian_router import route_and_run

        rep = str(route_and_run("گزارش بساز و برایم ایمیل کن").get("agent_report", ""))
        dropped_confessed = "اجرا نشد" in rep and "ایمیل" in rep
        whole_chain_named_failure = "ایمیل" in rep and "ناموفق" in rep
        assert dropped_confessed or whole_chain_named_failure
