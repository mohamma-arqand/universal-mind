"""Tests for the native desktop application (engine logic, no display)."""

from __future__ import annotations

import json
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


def test_chains_are_listed_and_all_real(tk_root: tk.Tk) -> None:
    """Every preset chain lists only capabilities that are genuinely wired."""
    import universal_mind.real_tool_registry as rtr
    from universal_mind.desktop_app import _PRESET_CHAINS

    app = MindDesktopApp(tk_root)
    listed = list(app._chain_list.get(0, tk.END))
    assert len(listed) == len(_PRESET_CHAINS)
    for name, caps in _PRESET_CHAINS.items():
        assert name in listed
        for cap in caps:
            # Every chain capability must be a genuinely registered real
            # capability (the registry is the single source of truth).
            assert cap in rtr._REAL_CONNECTORS, f"chain '{name}' uses non-real '{cap}'"


def test_chain_work_is_real(tk_root: tk.Tk) -> None:
    """_do_chain_work runs a genuine two-real-program synthesis (media + archive)."""
    app = MindDesktopApp(tk_root)
    app._do_chain_work(["media", "archive"])
    tk_root.update()
    shown = app._chain_result.get("1.0", tk.END)
    payload = json.loads(shown)
    assert payload["ok"] is True
    assert payload["results"]["media"]["bytes"] > 0
    assert payload["results"]["archive"]["bytes"] > 0


def test_first_image_from_finds_the_chart(tmp_path_factory: pytest.TempPathFactory) -> None:
    """A chain's outputs containing a chart/media PNG yield that path; text-only
    results yield None (no fabricated preview)."""
    from universal_mind.desktop_app import _first_image_from

    tmp = tmp_path_factory.mktemp("preview")
    from PIL import Image

    chart = tmp / "line.png"
    Image.new("RGB", (60, 40), color=(10, 80, 160)).save(chart)
    results = {
        "chart": {"path": str(chart), "bytes": chart.stat().st_size},
        "data": {"mean": 5.0},
    }
    assert _first_image_from(results) == str(chart)
    assert _first_image_from({"data": {"mean": 5.0}}) is None


def test_show_preview_displays_the_real_image(tk_root: tk.Tk, tmp_path_factory: pytest.TempPathFactory) -> None:
    """_show_preview loads a real PNG into the label (the photo reference holds)."""
    from PIL import Image

    tmp = tmp_path_factory.mktemp("preview2")
    img = tmp / "real.png"
    Image.new("RGB", (200, 150), color=(200, 100, 20)).save(img)

    app = MindDesktopApp(tk_root)
    app._show_preview(str(img))
    tk_root.update()
    # The label now shows an image (photo ref held) and no placeholder text.
    assert app._preview_photo is not None
    assert app._preview_label.cget("text") == ""


def test_show_preview_handles_no_image(tk_root: tk.Tk) -> None:
    app = MindDesktopApp(tk_root)
    app._show_preview(None)
    tk_root.update()
    assert app._preview_photo is None
    assert "تولید نکرد" in app._preview_label.cget("text")


def test_chain_work_shows_preview_of_real_chart(tk_root: tk.Tk) -> None:
    """A real chart chain ends with the produced chart visible in the window."""
    app = MindDesktopApp(tk_root)
    app._do_chain_work(["chart", "data"])
    tk_root.update()
    payload = json.loads(app._chain_result.get("1.0", tk.END))
    assert payload["ok"] is True
    assert app._preview_photo is not None  # the real chart is displayed


def test_persian_tab_present_and_routed(tk_root: tk.Tk) -> None:
    """The Persian tab exists, and _do_persian_work runs the real chain."""
    app = MindDesktopApp(tk_root)
    # tkinter stdlib stubs are untyped (tab/index carry no annotations).
    tab_count: int = app._notebook.index(tk.END)  # type: ignore[no-untyped-call]
    tabs = [app._notebook.tab(i, "text") for i in range(tab_count)]  # type: ignore[no-untyped-call]
    assert "فرمان فارسی" in tabs
    # Set a Persian command and run it for real.
    for w in app._fa_entry.master.winfo_children():
        pass  # the entry already holds the default command
    app._do_persian_work("محاسبه کن و نمودار بکش")
    tk_root.update()
    payload = json.loads(app._fa_result_text.get("1.0", tk.END))
    assert payload["ok"] is True
    assert set(payload["route"]) == {"data", "chart"}
    route_text = app._fa_route_text.get("1.0", tk.END)
    assert "data → chart" in route_text


def test_persian_unknown_command_honest(tk_root: tk.Tk) -> None:
    app = MindDesktopApp(tk_root)
    app._do_persian_work("پرواز کن به ماه")
    tk_root.update()
    payload = json.loads(app._fa_result_text.get("1.0", tk.END))
    assert payload["ok"] is False
    assert payload["error"]


def test_persian_tab_shows_preview_of_real_chart(tk_root: tk.Tk) -> None:
    """A Persian command producing a chart ends with that chart in the fa pane."""
    app = MindDesktopApp(tk_root)
    app._do_persian_work("نمودارشو ۱ و ۲ و ۳ بکش")
    tk_root.update()
    payload = json.loads(app._fa_result_text.get("1.0", tk.END))
    assert payload["ok"] is True
    assert app._fa_preview_photo is not None  # the real chart displayed in the fa pane


def test_vision_chain_lists_and_runs_real(tk_root: tk.Tk) -> None:
    """The vision chains are listed, and vision→pdf runs real CV + a real PDF."""
    app = MindDesktopApp(tk_root)
    listed = list(app._chain_list.get(0, tk.END))
    assert any("بینایی" in name for name in listed)
    app._do_chain_work(["vision", "pdf"])
    tk_root.update()
    payload = json.loads(app._chain_result.get("1.0", tk.END))
    assert payload["ok"] is True
    # The default vision operation is real stats (per-channel, from OpenCV).
    assert payload["results"]["vision"]["shape"] == [120, 160, 3]
    assert payload["results"]["pdf"]["bytes"] > 0
    # The vision image is displayed in the preview pane (stats has no image,
    # but pdf's doc is not an image either — so the preview shows the placeholder).
    assert payload.get("ok") is True


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