"""Tests: R37 layer-1+2 — the living-memory flows + the spoken vocabulary."""

from __future__ import annotations


class TestLivingMemoryFlows:
    def test_stored_records_get_plotted(self) -> None:
        """database → chart: the operator's OWN stored numbers, plotted."""
        from universal_mind.orchestration import _flow_params

        params, desc = _flow_params(
            "chart", {}, "database",
            [{"metric": "میانگین", "value": "4.5"}, {"metric": "بیشینه", "value": "8"}],
            "چی ذخیره کردی را نمودارش کن", (),
        )
        assert desc is not None and "رکورد ذخیرهشده" in desc
        assert params["operation"] == "bar"
        assert params["values"] == [4.5, 8.0]
        assert "میانگین" in params["categories"]

    def test_string_values_are_coerced(self) -> None:
        """SQLite stores numbers as TEXT — the flow must still plot them."""
        from universal_mind.orchestration import _flow_params

        params, desc = _flow_params(
            "chart", {}, "database",
            [{"metric": "a", "value": "5"}, {"metric": "b", "value": "8"}],
            "cmd", (),
        )
        assert desc is not None
        assert params["values"] == [5.0, 8.0]

    def test_non_numeric_rows_are_skipped(self) -> None:
        from universal_mind.orchestration import _flow_params

        params, desc = _flow_params(
            "chart", {}, "database",
            [{"metric": "a", "value": "متن"}, {"metric": "b", "value": "8"}],
            "cmd", (),
        )
        assert desc is not None
        assert params["values"] == [8.0]

    def test_web_page_gets_stored(self) -> None:
        """webfetch → database: «صفحه وب رو ذخیره کن» actually stores."""
        from universal_mind.orchestration import _flow_params

        params, desc = _flow_params(
            "database", {}, "webfetch", {"preview": "محتوای صفحه برای ذخیره"},
            "صفحه وب رو ذخیره کن", (),
        )
        assert desc is not None and "خواندهشده ذخیره شد" in desc
        assert params["operation"] == "insert_many"
        assert params["persistent"] is True

    def test_document_gets_spoken(self) -> None:
        """pdfreader → speech: the Persian reader — the document, aloud."""
        from universal_mind.orchestration import _flow_params

        params, desc = _flow_params(
            "speech", {}, "pdfreader", {"text": "این متن سند است"},
            "سند را بلند بخوان", (),
        )
        assert desc is not None and "بلند گفته شد" in desc
        assert "این متن سند است" in params["text"]

    def test_explicit_speech_text_wins_over_flow(self) -> None:
        from universal_mind.orchestration import _flow_params

        params, desc = _flow_params(
            "speech", {"operation": "speak", "text": "جملهی صریح"},
            "pdfreader", {"text": "متن سند"}, "cmd", (),
        )
        assert desc is None  # the operator's own words win


class TestSpokenVocabulary:
    def test_write_routes_to_clipboard(self) -> None:
        from universal_mind.persian_router import route_and_run

        assert "clipboard" in route_and_run("متن بنویس که سلام دنیا")["route"]

    def test_send_routes_to_clipboard(self) -> None:
        from universal_mind.persian_router import route_and_run

        assert "clipboard" in route_and_run("این متن را برایم بفرست")["route"]

    def test_music_routes_to_speech(self) -> None:
        from universal_mind.persian_router import route_and_run

        assert "speech" in route_and_run("موسیقی پخش کن")["route"]

    def test_look_routes_to_vision(self) -> None:
        from universal_mind.persian_router import route_and_run

        assert "vision" in route_and_run("این صفحه را ببین و بگو چه میبینی")["route"]

    def test_film_routes_to_media(self) -> None:
        from universal_mind.persian_router import route_and_run

        assert "media" in route_and_run("یک فیلم کوتاه بساز")["route"]

    def test_previous_holes_stay_closed(self) -> None:
        from universal_mind.persian_router import route_and_run

        for c in ("سلام", "چند تا اجرا موفق داشتی؟", "ترندها رو نشون بده"):
            assert route_and_run(c).get("route"), c