"""The Latin-digit lock: NO ASCII digits in the SYSTEM's Persian narration.

The operator's Persian experience is total: every digit the PLATFORM renders
in its own narration lines is a Persian digit. Content quoted from data (OCR
text, the operator's raw command echoes) is exempt BY DESIGN — we render what
was read; we do not rewrite reality.
"""

from __future__ import annotations

import re


class TestNoLatinDigitsInSystemNarration:
    def test_the_standard_reports_are_all_persian_digits(self) -> None:
        from universal_mind.persian_report import persian_report
        from universal_mind.persian_router import route_and_run

        commands = [
            "میانگین ۳ و ۷ را حساب کن",
            "نمودار خطی بساز و گزارشش کن",
            "میانگین ۱۰ و ۲۰ را حساب کن و در اکسل بریز",
            "گزارش کامل فروش با ۱۰ و ۲۰ بساز",
        ]
        for command in commands:
            payload = route_and_run(command)
            report = persian_report(payload)
            # quoted OCR/goal content is exempt; the system's lines are not
            system_lines = [
                ln for ln in report.splitlines()
                if not ln.startswith("• متنِ") and "«" not in ln
            ]
            latin = re.findall(r"[0-9]", "\n".join(system_lines))
            assert not latin, (
                f"latin digits leaked into the system narration for {command!r}: {latin}"
            )

    def test_the_status_report_renders_persian_digits(self) -> None:
        """The goal texts themselves carry operator digits — the RENDERING
        Persianizes them (the stored text stays verbatim)."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("وضعیت")
        report = payload["agent_report"]
        # whatever the store holds, the rendered board must be Persian-clean
        latin = re.findall(r"[0-9]", report)
        assert not latin, f"latin digits in the status board: {latin}"
