"""Tests for the native desktop application (engine logic, no display)."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Iterator

import pytest

from universal_mind.desktop_app import (
    _CAPABILITY_DESCRIPTIONS,
    _DEFAULT_PARAMS,
    MindDesktopApp,
    _factory_for,
)


@pytest.fixture(scope="module")  # type: ignore[untyped-decorator]
def tk_root() -> Iterator[tk.Tk]:
    """A hidden Tk root (no window shown, but the widget tree is real)."""
    try:
        root = tk.Tk()
        root.withdraw()  # never display during tests
    except tk.TclError:
        pytest.skip("no display available for tkinter")
    yield root
    root.destroy()


def test_all_listed_capabilities_are_real() -> None:
    """Every capability the window lists is genuinely wired in the registry."""
    import universal_mind.real_tool_registry as rtr

    for cap in _CAPABILITY_DESCRIPTIONS:
        assert cap in rtr._REAL_CONNECTORS, f"{cap} listed but not real"


def test_default_params_are_valid_json() -> None:
    for cap, raw in _DEFAULT_PARAMS.items():
        import json

        parsed = json.loads(raw)
        assert isinstance(parsed, dict), f"{cap} params are not a JSON object"


def test_app_populates_the_capability_list(tk_root: tk.Tk) -> None:
    app = MindDesktopApp(tk_root)
    listed = list(app._cap_list.get(0, tk.END))
    assert "data" in listed
    assert "database" in listed
    assert len(listed) == len(_CAPABILITY_DESCRIPTIONS)


def test_selecting_a_capability_fills_params(tk_root: tk.Tk) -> None:
    app = MindDesktopApp(tk_root)
    # Select 'compute' by finding its index.
    caps = list(app._cap_list.get(0, tk.END))
    idx = caps.index("compute")
    app._cap_list.selection_clear(0, tk.END)
    app._cap_list.selection_set(idx)
    app._on_select(None)
    params_text = app._params_text.get("1.0", tk.END).strip()
    import json

    assert json.loads(params_text)["operation"] == "evaluate"


def test_factory_resolves_to_the_real_connector() -> None:
    from universal_mind.data_suite import DataSuiteConnector
    from universal_mind.tool_registry import (
        ConnectionMechanism,
        ToolConnectionSpec,
        ToolEntry,
    )

    entry = ToolEntry(name="d", capability="data",
                      connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="unused"),
                      absorbable=True)
    conn = _factory_for("data")(entry)
    assert isinstance(conn, DataSuiteConnector)


def test_engine_work_is_real(tk_root: tk.Tk) -> None:
    """_do_work runs the genuine engine (numpy stats) and produces a payload."""
    app = MindDesktopApp(tk_root)
    app._do_work("data", {"operation": "stats", "data": [2, 4, 4, 4, 5, 5, 7, 9]})
    # _do_work posts via root.after(0, ...); process pending events instead of
    # mainloop, then read what the result pane holds.
    tk_root.update()
    shown = app._result_text.get("1.0", tk.END)
    import json

    payload = json.loads(shown)
    assert payload["ok"] is True
    assert payload["result"]["data"]["mean"] == 5.0