#!/usr/bin/env python3
"""Probe: R44 item 12 — the absorption recipe, itself measured.

The recipe (ABSORPTION_RECIPE.md) claims a new tool is absorbed in five
steps with a wiring footprint under 30 adapter lines. This probe MEASURES
that claim against the real source instead of trusting the prose:

1. Every registered real connector is reachable through
   real_connector_factory (no dangling registration).
2. The newest absorbed tool's adapter is <= 30 lines.
3. All FOUR wires exist for it (registry, vocabulary, params, [flow]).
4. The platform's real-program count is reported (measurable growth).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, "..")

ROOT = Path(__file__).resolve().parent.parent  # the universal_mind package dir

sys.stderr.write("PROBE R44-12 (the absorption recipe, measured):\n")

_ADAPTER_BAR = 30
# The newest absorbed tool — the recipe's own reference sample (R44-11 email).
_NEWEST: dict[str, Any] = {
    "capability": "email",
    "module": "email_outbox.py",
    "adapter": "EmailToolConnector",
    "vocab_file": "persian_router.py",
    "vocab_count": 7,
    "params_file": "persian_params.py",
    "flow_file": "orchestration.py",
}


def _ok(name: str, cond: bool, extra: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    sys.stderr.write(f"  [{mark}] {name}" + (f" — {extra}" if extra else "") + "\n")
    if not cond:
        raise SystemExit(1)


def main() -> int:
    # H1 — every registered connector is REACHABLE (no dangling registration).
    from universal_mind.real_tool_registry import _REAL_CONNECTORS, real_connector_factory
    from universal_mind.tool_registry import (
        ConnectionMechanism,
        ToolConnectionSpec,
        ToolEntry,
    )

    dangling: list[str] = []
    for capability, _constructor in _REAL_CONNECTORS.items():
        entry = ToolEntry(
            name=f"probe::{capability}",
            capability=capability,
            connection=ToolConnectionSpec(
                mechanism=ConnectionMechanism.SUBPROCESS, command="unused"
            ),
            absorbable=True,
        )
        try:
            conn = real_connector_factory(entry)
        except Exception as exc:  # noqa: BLE001 — a dangling registration IS the finding
            dangling.append(f"{capability}: {exc}")
            continue
        if conn is None:
            dangling.append(f"{capability}: factory returned None")
    _ok("no dangling registration", not dangling,
        f"{len(_REAL_CONNECTORS)} real programs, {len(dangling)} dangling")
    if dangling:
        for d in dangling:
            sys.stderr.write(f"      {d}\n")

    # H2 — the newest adapter stays under the bar (wiring, not logic).
    module_src = (ROOT / _NEWEST["module"]).read_text(encoding="utf-8")
    m = re.search(
        rf"class {_NEWEST['adapter']}:.*?(?=\n__all__|\Z)", module_src, re.S
    )
    _ok("the adapter class exists", m is not None)
    adapter_lines = len([ln for ln in (m.group(0) if m else "").splitlines() if ln.strip()])
    _ok(
        f"adapter <= {_ADAPTER_BAR} lines",
        adapter_lines <= _ADAPTER_BAR,
        f"{adapter_lines} lines",
    )

    # H3 — all FOUR wires are live for the newest tool.
    reg_src = (ROOT / "real_tool_registry.py").read_text(encoding="utf-8")
    wire_registry = reg_src.count(_NEWEST["adapter"]) >= 2  # import + dict entry
    _ok("wire 1/4: registry (import + entry)", wire_registry)

    vocab_src = (ROOT / _NEWEST["vocab_file"]).read_text(encoding="utf-8")
    vocab_hits = vocab_src.count(f'"{_NEWEST["capability"]}"')
    _ok("wire 2/4: Persian vocabulary", vocab_hits >= _NEWEST["vocab_count"],
        f"{vocab_hits} entries")

    params_src = (ROOT / _NEWEST["params_file"]).read_text(encoding="utf-8")
    _ok(
        "wire 3/4: param extraction branch",
        f'if capability == "{_NEWEST["capability"]}"' in params_src,
    )

    flow_src = (ROOT / _NEWEST["flow_file"]).read_text(encoding="utf-8")
    _ok(
        "wire 4/4: dataflow branch",
        f'if consumer == "{_NEWEST["capability"]}"' in flow_src,
    )

    # H4 — the recipe document exists and the growth is reported.
    doc = ROOT / "ABSORPTION_RECIPE.md"
    _ok("the recipe is a real document", doc.exists() and doc.stat().st_size > 1000,
        f"{doc.stat().st_size if doc.exists() else 0} bytes")
    sys.stderr.write(f"  (platform real programs: {len(_REAL_CONNECTORS)})\n")

    sys.stderr.write("R44-12: ALL HOLDS GREEN\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
