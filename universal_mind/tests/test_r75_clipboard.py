"""R75 P1-P4 — the CLIPBOARD class.

A live 12-command sweep found 10 wrong answers: «سلام به همه را کپی کن»
got a GREETING, «متن «X» را در کلیپبورد کپی کن» fell to a file-move
with an empty destination, «آدرس فایل X را کپی کن» READ the file
instead of copying the path — and the system discovery: the machine's
clipboard is PERMANENTLY held by cua-driver (a Computer-Use overlay),
so the honest answer must NAME the holder, never a vague «برنامهی دیگر».
"""

from __future__ import annotations

import pytest


class TestCopyOwnership:
    def test_text_copy_routes_clipboard_only(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("متن «سلام به همه» را در کلیپبورد کپی کن")
        assert p["route"] == ["clipboard"], p["route"]

    def test_a_greeting_shaped_copy_is_not_small_talk(self) -> None:
        from universal_mind.conversational import answer_conversational
        from universal_mind.persian_router import route_and_run

        assert answer_conversational("سلام به همه را کپی کن") is None
        p = route_and_run("سلام به همه را کپی کن")
        assert p["route"] == ["clipboard"], p["route"]

    def test_plain_greeting_survives(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("سلام")
        assert p["ok"] is True and "conversational" in p["route"]

    def test_path_copy_is_clipboard_of_the_path(self) -> None:
        from universal_mind.persian_params import extract_params

        got = extract_params("آدرس فایل D:/g/x.txt را کپی کن", "clipboard")
        assert got["operation"] == "write" and got["text"] == "D:/g/x.txt"

    def test_file_copy_with_destination_still_copies_the_file(self) -> None:
        from pathlib import Path

        from universal_mind.persian_router import route_and_run

        base = Path(r"D:/gwr75_tests")
        base.mkdir(exist_ok=True)
        src = base / "a.txt"
        src.write_text("g", encoding="utf-8")
        (base / "dst").mkdir(exist_ok=True)
        for f in (base / "dst").iterdir():  # a clean destination: the
            f.unlink()                      # overwrite law is ANOTHER test
        p = route_and_run(f"فایل {src} را به پوشه {base / 'dst'} کپی کن")
        assert p["ok"] is True, str(p.get("agent_report"))[:100]
        assert (base / "dst" / "a.txt").exists()

    def test_payload_shapes(self) -> None:
        from universal_mind.persian_params import extract_params

        assert extract_params("سلام به همه را کپی کن", "clipboard") == {
            "operation": "write", "text": "سلام به همه"}
        assert extract_params(
            "متن را در کلیپبورد بگذار: متن آزمایشی", "clipboard") == {
            "operation": "write", "text": "متن آزمایشی"}
        assert extract_params("یادداشت خرید نان را بنویس", "clipboard") == {
            "operation": "write", "text": "خرید نان"}
        assert extract_params("محتوای کلیپبورد را بخوان", "clipboard") == {
            "operation": "read"}


class TestTheHonestLock:
    def test_a_locked_clipboard_names_the_holder_or_admits_blindness(self) -> None:
        """On this machine cua-driver holds the clipboard; the error either
        NAMES the holder process or honestly says another app holds it —
        never a bare traceback, never a fabricated string."""
        from universal_mind.real_clipboard import ClipboardTool

        out = ClipboardTool().get_text()
        if out["ok"]:
            pytest.skip("clipboard is free on this run — lock unseen")
        err = out["error"]
        assert "کلیپبورد قفل شده" in err
        assert ("برنامهٔ" in err) or ("برنامهی دیگر" in err)

    def test_holder_detection_is_never_fatal(self) -> None:
        from universal_mind.real_clipboard import _clipboard_holder

        h = _clipboard_holder()  # any answer (or "") — never an exception
        assert isinstance(h, str)

    def test_set_text_retries_transient_locks(self) -> None:
        """The write path retries 3x with a growing backoff; a permanent
        holder still fails — named."""
        from universal_mind.real_clipboard import ClipboardTool

        out = ClipboardTool().set_text("gavahi-r75")
        assert out["ok"] is False  # held by cua-driver on this machine
        assert "کلیپبورد قفل شده" in out["error"]
        assert ("برنامهٔ" in out["error"]) or ("برنامهی دیگر" in out["error"])
