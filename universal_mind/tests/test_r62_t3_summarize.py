"""R62 T3 — capability 28: extractive Persian summarization, no LLM.

«خلاصه کن این متن را: …» was dead. The summary is a SELECTION of the
text's OWN sentences (word-overlap centrality + first-sentence bonus) —
never a generated sentence, never «این خلاصه است».
"""

from __future__ import annotations

from universal_mind.persian_router import route, route_and_run
from universal_mind.text_summary_tool import summarize


TEXT = (
    "هوش مصنوعی در سالهای اخیر تغییر بزرگی کرده است. ماشینها حالا میتوانند متن را بخوانند و بفهمند. "
    "در ایران هم شرکتهای زیادی روی پردازش زبان فارسی کار میکنند. ابزارهای فارسی هنوز کم هستند. "
    "پردازش زبان فارسی چالشهای خاص خودش را دارد. مثلا نیمفاصله و املای محاوره‌ای. "
    "آیندهٔ هوش مصنوعی فارسی روشن به نظر میرسد."
)


class TestTheTool:
    def test_the_summary_picks_the_texts_own_sentences(self) -> None:
        out = summarize(TEXT, max_sentences=3)
        assert out["ok"] is True
        for s in out["summary"]:
            assert s in TEXT  # a summary sentence MUST come from the text

    def test_the_first_sentence_rises(self) -> None:
        out = summarize(TEXT, max_sentences=3)
        assert TEXT.split(".")[0].strip() in out["summary"]

    def test_no_text_is_a_named_refusal(self) -> None:
        out = summarize("")
        assert out["ok"] is False and "متنی" in str(out["error"])

    def test_a_short_text_is_returned_whole(self) -> None:
        out = summarize("یک جمله. دو جمله.")
        assert out["ok"] is True and out["kind"] == "whole"
        assert len(out["summary"]) == 2


class TestRouting:
    def test_the_summary_sentence_routes_to_the_new_capability(self) -> None:
        r = route(f"خلاصه کن این متن را: {TEXT}")
        assert "textsummarize" in r.capabilities

    def test_the_summary_intent_owns_the_route(self) -> None:
        # «متن» drags data and «هوش» drags llm — both must step aside
        r = route(f"خلاصه کن این متن را: {TEXT}")
        assert "data" not in r.capabilities and "llm" not in r.capabilities


class TestEndToEnd:
    def test_the_report_counts_honestly(self) -> None:
        rep = str(route_and_run(f"خلاصه کن این متن را: {TEXT}").get("agent_report", ""))
        assert "۳ جمله از ۷" in rep

    def test_the_report_names_the_capability_in_persian(self) -> None:
        rep = str(route_and_run(f"خلاصه کن این متن را: {TEXT}").get("agent_report", ""))
        assert "خلاصه‌سازی متن" in rep

    def test_without_text_the_refusal_reaches_the_operator(self) -> None:
        p = route_and_run("خلاصه کن این متن را")
        assert p.get("ok") is False
        assert "متنی برای خلاصه‌کردن" in p["agent_report"]
