"""R59 P3+P4 — the machine views: open windows and heavy processes.

Two measured dead sentences from the sweep, now answered from the REAL
machine through read-only PowerShell. A Persian window title must survive
the round trip (the OEM codepage turns it into ?????? — a view that renders
the operator's own tabs as question marks is a silent corruption).
"""

from __future__ import annotations

from unittest.mock import patch

from universal_mind.reflexive import answer_reflexive
from universal_mind import window_view as wv


class _FakeProc:
    returncode = 0

    def __init__(self, stdout: bytes) -> None:
        self.stdout = stdout
        self.stderr = b""


class TestOpenWindows:
    def test_the_sweep_question_answers_from_the_machine(self) -> None:
        with patch.object(wv.subprocess, "run",
                          return_value=_FakeProc(
                              b'[{"ProcessName":"firefox","MainWindowTitle":"\xd8\xaa\xd9\x85\xd8\xa7\xd8\xb4\xd8\xa7"}]')):
            res = wv.list_open_windows()
        assert res["ok"] is True
        assert res["windows"][0]["title"] == "تماشا"

    def test_a_persian_title_is_not_question_marks(self) -> None:
        # UTF-8 console encoding: the live witness caught «??????» for a
        # Persian Firefox title before the fix
        with patch.object(wv.subprocess, "run",
                          return_value=_FakeProc(
                              '[{"ProcessName":"f","MainWindowTitle":"سلام"}]'.encode("utf-8"))):
            rep = wv.windows_fa(wv.list_open_windows())
        assert "سلام" in rep and "????" not in rep

    def test_empty_is_said_honestly(self) -> None:
        with patch.object(wv.subprocess, "run", return_value=_FakeProc(b"")):
            rep = wv.windows_fa(wv.list_open_windows())
        assert "هیچ پنجره‌ای" in rep

    def test_a_powershell_failure_is_named_not_faked(self) -> None:
        class _Boom:
            returncode = 1
            stdout = b""
            stderr = "service stopped".encode()

        with patch.object(wv.subprocess, "run", return_value=_Boom()):
            res = wv.list_open_windows()
        assert res["ok"] is False
        assert "نشد" in res["error"]

    def test_a_single_row_json_dict_is_accepted(self) -> None:
        with patch.object(wv.subprocess, "run",
                          return_value=_FakeProc(
                              b'{"ProcessName":"x","MainWindowTitle":"y"}')):
            res = wv.list_open_windows()
        assert res["ok"] is True and len(res["windows"]) == 1


class TestTopProcesses:
    def test_sorted_by_cpu_with_real_fields(self) -> None:
        import json

        payload = json.dumps([
            {"ProcessName": "a", "CPU": 10.5, "WorkingSet64": 104857600},
            {"ProcessName": "b", "CPU": 99.1, "WorkingSet64": 20971520},
        ]).encode()
        with patch.object(wv.subprocess, "run", return_value=_FakeProc(payload)):
            res = wv.top_processes(5)
        assert res["ok"] is True
        assert res["processes"][0]["process"] == "b"      # the heavier first
        assert res["processes"][0]["ram_mb"] == 20.0

    def test_a_null_cpu_is_zero_not_a_crash(self) -> None:
        with patch.object(wv.subprocess, "run",
                          return_value=_FakeProc(
                              b'[{"ProcessName":"System","CPU":null,"WorkingSet64":null}]')):
            res = wv.top_processes()
        assert res["ok"] is True
        assert res["processes"][0]["cpu_seconds"] == 0.0

    def test_the_limit_is_clamped(self) -> None:
        with patch.object(wv.subprocess, "run",
                          return_value=_FakeProc(b'[{"ProcessName":"a","CPU":1,"WorkingSet64":1}]')):
            res = wv.top_processes(999)
        assert res["ok"] is True  # clamped to 20, no error

    def test_the_persian_report_names_cpu_and_ram(self) -> None:
        with patch.object(wv.subprocess, "run",
                          return_value=_FakeProc(
                              b'[{"ProcessName":"Hermes","CPU":123.4,"WorkingSet64":104857600}]')):
            rep = wv.processes_fa(wv.top_processes(1))
        assert "CPU" in rep and "رم" in rep and "مگابایت" in rep


class TestReflexWiring:
    def test_the_windows_question_is_a_reflex(self) -> None:
        with patch.object(wv.subprocess, "run",
                          return_value=_FakeProc(b"")):
            out = answer_reflexive("چه برنامه‌هایی الان باز است؟")
        assert out is not None and "پنجره" in out["agent_report"]

    def test_the_heavy_processes_question_is_a_reflex(self) -> None:
        with patch.object(wv.subprocess, "run",
                          return_value=_FakeProc(
                              b'[{"ProcessName":"x","CPU":5,"WorkingSet64":1}]')):
            out = answer_reflexive("پروسه‌های پرمصرف را نشان بده")
        assert out is not None and "پردازش" in out["agent_report"]

    def test_no_neighbour_sentence_is_stolen(self) -> None:
        from universal_mind.persian_router import route

        assert route("گزارش برنامه‌ام را بساز").capabilities == ("pdf",)
        assert route("نمودار مصرف را بکش").capabilities == ("chart",)
        assert route("سلام").capabilities == ()
