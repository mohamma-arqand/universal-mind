"""R77 — the OPENER (the 31st real capability).

«باز کن» fell to webfetch (a word collision): a FILE, a FOLDER, the
calculator, notepad, and Windows settings all got «کدام سایت؟». The
opener runs the real Windows verb (Start-Process/ShellExecute) for each
object class — file, folder, program, URL — names what it opened, and
refuses an unknown object BY NAME. Reading a page keeps its own verb
(«سایت X را بخوان» → webfetch).
"""

from __future__ import annotations

from pathlib import Path

import pytest

BASE = Path(r"D:/gwr77_tests")


def _setup() -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / "note.txt").write_text("گواه R77\n", encoding="utf-8")
    (BASE / "subfolder").mkdir(exist_ok=True)


class TestRouting:
    def test_open_a_file_routes_opener_only(self) -> None:
        from universal_mind.persian_router import route_and_run

        _setup()
        p = route_and_run(f"فایل {BASE / 'note.txt'} را باز کن")
        assert p["route"] == ["opener"], p["route"]
        assert p["ok"] is True

    def test_open_a_folder_is_not_a_file_read(self) -> None:
        from universal_mind.persian_router import route_and_run

        _setup()
        p = route_and_run(f"پوشه {BASE / 'subfolder'} را باز کن")
        assert p["route"] == ["opener"], p["route"]
        assert p["ok"] is True

    def test_the_open_report_names_the_thing(self) -> None:
        from universal_mind.persian_router import route_and_run

        _setup()
        p = route_and_run(f"پوشه {BASE / 'subfolder'} را باز کن")
        rep = str(p.get("agent_report", ""))
        assert "پوشه" in rep and "باز شد" in rep and str(BASE / "subfolder") in rep

    def test_reading_a_page_keeps_webfetch(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("سایت example.com را بخوان")
        assert "webfetch" in p["route"] and "opener" not in p["route"]


class TestTargets:
    def test_a_missing_path_is_a_named_refusal(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run(f"فایل {BASE / 'nope.txt'} را باز کن")
        assert p["ok"] is False
        assert "نه مسیر موجود است" in str(p.get("agent_report", ""))

    def test_the_verb_rides_from_با(self) -> None:
        from universal_mind.persian_params import extract_params

        got = extract_params(f"فایل {BASE / 'note.txt'} را با notepad باز کن", "opener")
        assert got["target"].endswith("note.txt") and got["verb"] == "notepad"

    def test_the_program_table(self) -> None:
        from universal_mind.opener_tool import _PROGRAMS_FA

        assert _PROGRAMS_FA["ماشینحساب"] == "calc"
        assert _PROGRAMS_FA["تنظیمات ویندوز"] == "ms-settings:"

    def test_the_connector_protocol(self) -> None:
        from universal_mind.connectors import ConnectorResult
        from universal_mind.opener_tool import OpenerConnector

        _setup()
        out = OpenerConnector().connect(None, {"target": str(BASE / "subfolder")})
        assert isinstance(out, ConnectorResult) and out.ok is True
        bad = OpenerConnector().connect(None, {})
        assert bad.ok is False and "چه چیزی" in bad.error


@pytest.fixture(autouse=True)
def _around() -> None:
    _setup()
    yield
    import shutil

    shutil.rmtree(BASE, ignore_errors=True)
