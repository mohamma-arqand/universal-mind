"""R61-S6 — the report a stranger can use: paths, Persian digits, no leaks.

Review findings 12-13: the artifact's location was NEVER stated (a stranger
cannot find their chart), and Latin digits leaked into the Persian report
(the ML coefficient count, the A/B margin, the PDF page count).
"""

from __future__ import annotations

from universal_mind.persian_report import persian_report


class TestArtifactPaths:
    def test_a_chart_report_names_its_file_location(self) -> None:
        payload = {
            "ok": True, "route": ["chart"],
            "result": {"chart": {"bytes": 25600, "path": "D:/out/line.png"}},
            "errors": {}, "extracted_params": {"chart": {"operation": "line"}},
        }
        rep = persian_report(payload)
        assert "D:/out/line.png" in rep

    def test_a_pdf_report_names_its_file_location(self) -> None:
        payload = {
            "ok": True, "route": ["pdf"],
            "result": {"pdf": {"bytes": 33900, "path": "D:/out/report.pdf"}},
            "errors": {},
        }
        rep = persian_report(payload)
        assert "D:/out/report.pdf" in rep

    def test_a_result_without_a_path_still_answers(self) -> None:
        payload = {
            "ok": True, "route": ["chart"],
            "result": {"chart": {"bytes": 25600}},
            "errors": {}, "extracted_params": {"chart": {"operation": "line"}},
        }
        rep = persian_report(payload)
        assert "ساخته شد" in rep and "در «" not in rep


class TestNoLatinDigitLeaks:
    def _no_latin(self, text: str) -> bool:
        return not any(ch in "0123456789" for ch in text.replace("D:/", "")
                       .replace("C:\\", "").replace("um-", "").replace(".png", "")
                       .replace(".pdf", "").replace("2.0", "").replace("1.22", ""))

    def test_the_ml_coefficient_count_is_persian(self) -> None:
        payload = {
            "ok": True, "route": ["ai"],
            "result": {"ai": {"coefficients": [1.5, 2.5]}},
            "errors": {},
        }
        rep = persian_report(payload)
        assert "۲ ضریب" in rep and "2 ضریب" not in rep

    def test_the_ab_margin_is_persian(self) -> None:
        # the A/B reasoning line rides the payload as gate/ab text
        from universal_mind.ab_contest import kind_ambiguity  # noqa: F401

        payload = {
            "ok": True, "route": ["chart"],
            "result": {"chart": {"bytes": 25600, "path": "D:/o/line.png"}},
            "errors": {}, "extracted_params": {"chart": {"operation": "line"}},
            "gate_reasoning": "مسابقهی A/B: «line» با برتری ۰.۷۵ برنده شد",
        }
        rep = persian_report(payload)
        assert "۰.۷۵" in rep

    def test_the_validator_page_count_is_persian(self) -> None:
        from universal_mind.artifact_validator import validate_artifact

        import tempfile

        # build a tiny real PDF via the suite (reportlab available)
        from universal_mind.pdf_suite import PdfSuite

        with tempfile.TemporaryDirectory() as d:
            out = PdfSuite().persian_rtl(title="ت", paragraphs=["x"], out_dir=d)
            v = validate_artifact(out["path"])
            assert v["ok"] is True
            assert "۱ صفحه" in v["detail"] and "1 صفحه" not in v["detail"]


class TestEndToEndPathStated:
    def test_a_live_chart_names_where_it_landed(self) -> None:
        from universal_mind.persian_router import route_and_run

        rep = str(route_and_run("نمودار بکش").get("agent_report", ""))
        assert "در «" in rep and ".png" in rep
