"""R60 Q4 — «فضای درایو C»: one drive, not a five-drive wall.

sysstatus already measured every drive; the sentence just never routed and
the report had no way to highlight THE drive the operator named.
"""

from __future__ import annotations

from typing import Any

from universal_mind.persian_params import extract_params
from universal_mind.persian_router import route
from universal_mind.persian_report import persian_report


class TestRouting:
    def test_the_drive_space_question_routes_to_sysstatus(self) -> None:
        assert route("فضای درایو C را نشان بده").capabilities == ("sysstatus",)

    def test_the_disk_word_routes_too(self) -> None:
        assert "sysstatus" in route("فضای دیسک D چند است؟").capabilities


class TestParams:
    def test_the_named_drive_letter_is_extracted_without_a_colon(self) -> None:
        # «درایو C را» — the colon is optional in speech; requiring one
        # measured empty-handed (the first live witness came back blank).
        p = extract_params("فضای درایو C را نشان بده", "sysstatus")
        assert p["drive_letter"] == "C"

    def test_a_coloned_drive_still_extracts(self) -> None:
        p = extract_params("فضای درایو D: را نشان بده", "sysstatus")
        assert p["drive_letter"] == "D"

    def test_no_drive_means_no_letter(self) -> None:
        p = extract_params("وضعیت سیستم را بگو", "sysstatus")
        assert p["drive_letter"] == ""


class TestReport:
    def _fake_result(self, drives: list[dict]) -> dict[str, Any]:
        return {
            "ok": True, "route": ["sysstatus"], "result": {"sysstatus": {
                "uptime": {"days": 1, "hours": 2, "minutes": 0},
                "ram": {"used_pct": 50, "free_gb": 8, "total_gb": 16},
                "disks": drives,
                "battery_pct": 90,
                "notes": [],
            }},
        }

    def test_the_named_drive_is_the_only_disk_line(self) -> None:
        payload = self._fake_result([
            {"drive": "C:", "free_gb": 100, "total_gb": 200, "free_pct": 50},
            {"drive": "D:", "free_gb": 50, "total_gb": 100, "free_pct": 50},
        ])
        payload["extracted_params"] = {"sysstatus": {"operation": "status",
                                                     "drive_letter": "C"}}
        rep = persian_report(payload)
        assert "دیسک C" in rep and "دیسک D" not in rep

    def test_an_unknown_drive_is_named_with_the_seen_ones(self) -> None:
        payload = self._fake_result([
            {"drive": "C:", "free_gb": 100, "total_gb": 200, "free_pct": 50},
        ])
        payload["extracted_params"] = {"sysstatus": {"operation": "status",
                                                     "drive_letter": "Z"}}
        rep = persian_report(payload)
        assert "Z را پیدا نکردم" in rep and "C:" in rep

    def test_without_a_letter_all_drives_show(self) -> None:
        payload = self._fake_result([
            {"drive": "C:", "free_gb": 100, "total_gb": 200, "free_pct": 50},
            {"drive": "D:", "free_gb": 50, "total_gb": 100, "free_pct": 50},
        ])
        payload["extracted_params"] = {"sysstatus": {"operation": "status",
                                                     "drive_letter": ""}}
        rep = persian_report(payload)
        assert "دیسک C" in rep and "دیسک D" in rep

