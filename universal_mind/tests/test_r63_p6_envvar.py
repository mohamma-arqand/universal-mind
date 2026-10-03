"""R63 P6 — «متغیر محیطی TEMP را نشان بده»: the operator's own env.

A measured dead sentence. The env is the operator's data; one NAMED
variable is a view with three honest outcomes:
- defined → the real value;
- secret-LOOKING name (KEY/TOKEN/SECRET/PASSWORD/…) → masked, never
  printed (live-proved with a planted token);
- undefined → a named refusal, never «نشناختم».
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _planted(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("UM_R63_SECRET_TOKEN", "never-print-me")
    monkeypatch.setenv("UM_R63_PLAIN_VAR", "hello-63")


class TestTheView:
    def test_temp_shows_the_real_value(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("متغیر محیطی TEMP را نشان بده")
        assert p["ok"] is True
        assert "متغیر محیطی TEMP = " in p["agent_report"]
        assert "Temp" in p["agent_report"] or "TMP" in p["agent_report"]

    def test_a_secret_looking_name_is_masked(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("متغیر محیطی UM_R63_SECRET_TOKEN را نشان بده")
        rep = p["agent_report"]
        assert "never-print-me" not in rep  # the value NEVER prints
        assert "مخفی" in rep  # the mask is named

    def test_a_plain_var_shows(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("متغیر محیطی UM_R63_PLAIN_VAR را نشان بده")
        assert "hello-63" in p["agent_report"]

    def test_an_undefined_var_is_a_named_refusal(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("متغیر محیطی UM_R63_NO_SUCH_VAR را نشان بده")
        assert p["ok"] is False
        assert "تعریف نشده" in p["agent_report"]
        assert "نشناختم" not in p["agent_report"]

    def test_the_connector_path_works(self) -> None:
        from universal_mind.connectors import ConnectorResult
        from universal_mind.system_status_tool import (
            SystemStatusTool,
            SystemStatusToolConnector,
        )

        conn = SystemStatusToolConnector(tool=SystemStatusTool())
        out = conn.connect(None, {"operation": "env_var", "name": "UM_R63_PLAIN_VAR"})
        assert isinstance(out, ConnectorResult)
        assert out.ok is True
        assert out.output["value"] == "hello-63"
