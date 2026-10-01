"""R58 M5 — an OCR call with no file asks IN PERSIAN, with the remedy.

Measured gap (the 18-command sweep): «متن تصویر را بخوان و در دیتابیس ذخیره
کن» surfaced a bare English «no image path given». The house law: every
refusal names what is missing and the exact sentence that fixes it.
"""

from __future__ import annotations

from universal_mind.ocr_tool import OcrToolConnector


class TestOcrNoPathAsksInPersian:
    def test_no_path_is_refused_with_the_persian_remedy(self) -> None:
        res = OcrToolConnector().connect({}, {"operation": "read"})
        assert res.ok is False
        assert "کدام تصویر" in str(res.error)
        assert "مثلا" in str(res.error)  # the recipe is named

    def test_no_english_leak_in_the_refusal(self) -> None:
        res = OcrToolConnector().connect({}, {})
        assert "no image path" not in str(res.error)

    def test_the_remedy_names_the_operation(self) -> None:
        res = OcrToolConnector().connect({}, {"operation": "read"})
        assert "متن تصویر" in str(res.error)  # the sentence shape to copy

    def test_an_unknown_operation_is_still_refused(self) -> None:
        res = OcrToolConnector().connect({}, {"operation": "تسلط"})
        assert res.ok is False and res.error

    def test_a_real_missing_file_failure_keeps_its_own_named_error(self) -> None:
        res = OcrToolConnector().connect({}, {"operation": "read",
                                              "path": "Z:/no/such.png"})
        assert res.ok is False
        # the file's own honest failure (image not found), not the no-path ask
        assert "کدام تصویر" not in str(res.error)
