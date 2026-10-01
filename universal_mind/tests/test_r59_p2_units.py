"""R59 P2 — the unit-convert capability, pinned.

Measured gaps (the 17-command sweep): «۱۰ کیلومتر چند مایل است؟» and
«۱۰۰ فارنهایت چند سانتیگراد است؟» both died in «نشناختم». A real capability
now converts them — with every factor an EXPLICIT table entry and temperature
as a FORMULA, never a guessed constant.
"""

from __future__ import annotations

import re

import pytest

from universal_mind.persian_router import route, route_and_run
from universal_mind.unit_convert_tool import (
    UnitConvertToolConnector,
    convert,
    parse_convert_request,
)


class TestConversionsAreCorrect:
    """Every family, checked against independently known values."""

    @pytest.mark.parametrize("value,src,tgt,want", [
        (10, "کیلومتر", "مایل", 6.2137),
        (1, "مایل", "کیلومتر", 1.609344),
        (100, "فارنهایت", "سانتیگراد", 37.7778),
        (0, "فارنهایت", "سانتیگراد", -17.7778),
        (100, "سانتیگراد", "فارنهایت", 212.0),
        (0, "سانتیگراد", "فارنهایت", 32.0),
        (0, "سانتیگراد", "کلوین", 273.15),
        (5, "کیلوگرم", "پوند", 11.0231),
        (2, "گیگابایت", "مگابایت", 2048.0),
        (90, "دقیقه", "ساعت", 1.5),
        (1, "اینچ", "سانتی‌متر", 2.54),
    ])
    def test_value(self, value: float, src: str, tgt: str, want: float) -> None:
        out = convert(value, src, tgt)
        assert out["ok"] is True, out
        assert abs(out["value"] - want) < 0.01


class TestHonestRefusals:
    def test_an_unknown_unit_is_refused_by_name(self) -> None:
        out = convert(5, "کیلوگرم", "زلوتي")
        assert out["ok"] is False
        assert "زلوتي" in out["error"]
        assert "شناخته" in out["error"]

    def test_cross_family_is_refused_with_both_families_named(self) -> None:
        out = convert(5, "کیلوگرم", "متر")
        assert out["ok"] is False
        assert "وزن" in out["error"] and "طول" in out["error"]

    def test_temperature_refuses_a_non_temperature_target(self) -> None:
        out = convert(30, "سانتیگراد", "متر")
        assert out["ok"] is False


class TestParsing:
    def test_the_sweep_sentence_parses(self) -> None:
        p = parse_convert_request("۱۰ کیلومتر چند مایل است؟")
        assert p == {"value": 10.0, "source": "کیلومتر", "target": "مایل"}

    def test_a_non_conversion_sentence_is_none(self) -> None:
        assert parse_convert_request("نمودار از ۲ و ۳ بکش") is None
        assert parse_convert_request("سلام") is None

    def test_colloquial_kilo_still_parses(self) -> None:
        p = parse_convert_request("۸۰ کیلو چند پوند است؟")
        assert p is not None and p["source"] == "کیلو"


class TestRouter:
    def test_the_two_sweep_sentences_route_to_unitconvert(self) -> None:
        assert route("۱۰ کیلومتر چند مایل است؟").capabilities == ("unitconvert",)
        assert route("۱۰۰ فارنهایت چند سانتیگراد است؟").capabilities == ("unitconvert",)

    def test_the_substring_trap_is_gated(self) -> None:
        # «کیلومتراژ» CONTAINS «کیلومتر» — a report about mileage is NOT a
        # conversion (the live witness caught this regression)
        assert "unitconvert" not in route("گزارش کیلومتراژ را بساز").capabilities

    def test_a_chart_command_is_untouched(self) -> None:
        assert route("نمودار از ۲ و ۳ بکش").capabilities == ("chart",)


class TestLiveAnswers:
    def test_the_sweep_question_answers_in_persian(self) -> None:
        p = route_and_run("۱۰۰ فارنهایت چند سانتیگراد است؟")
        assert p["ok"] is True
        assert "۳۷" in p["agent_report"]          # the real converted value
        assert "فارنهایت" in p["agent_report"]     # both units named
        assert "سانتیگراد" in p["agent_report"]

    def test_no_latin_digit_leaks_in_the_answer(self) -> None:
        p = route_and_run("۱۰ کیلومتر چند مایل است؟")
        line = [ln for ln in p["agent_report"].splitlines() if "برابر" in ln][0]
        assert not re.search(r"[0-9]", line)

    def test_the_connector_asks_when_units_are_missing(self) -> None:
        res = UnitConvertToolConnector().connect({}, {"operation": "convert"})
        assert res.ok is False
        assert "مثلا" in str(res.error)
