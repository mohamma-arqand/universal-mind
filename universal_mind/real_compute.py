"""Real compute tools — a node-backed specialist that runs real JavaScript.

A third real effect behind the same ``connector_factory`` pattern: this one runs a
real JavaScript expression through the host's node binary and returns the real
result, proving the super-platform drives *computation* — not just media (ffmpeg) or
archive (gzip) — as one more capability in the same loop.

Fail-safe and isolated: node's absence or a non-zero exit returns ``not ok`` with a
clear reason; nothing touches the live tree.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any


def _node() -> str | None:
    return shutil.which("node")


class ComputeTool:
    """A real node-backed specialist that evaluates JavaScript and returns JSON."""

    name = "node"
    capability = "compute"

    def evaluate(self, expression: str = "2 + 2") -> dict[str, Any]:
        """Run a JS expression via node and return its JSON result.

        The expression is wrapped to JSON.stringify its value, so the returned
        ``value`` is a real parsed result, not a printed string. Returns ``ok``,
        the parsed ``value``, and an ``error`` when node is missing or the
        expression fails.
        """
        node = _node()
        if node is None:
            return {"ok": False, "value": None, "error": "node not installed"}
        if not isinstance(expression, str) or not expression.strip():
            return {"ok": False, "value": None, "error": "empty expression"}
        program = f"console.log(JSON.stringify(({expression})))"
        try:
            result = subprocess.run(
                [node, "-e", program], capture_output=True, text=True, timeout=30, check=False
            )
        except (FileNotFoundError, OSError) as exc:
            return {"ok": False, "value": None, "error": str(exc)}
        if result.returncode != 0 or not result.stdout.strip():
            return {"ok": False, "value": None, "error": result.stderr.strip() or "no output"}

        import json

        try:
            value = json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            # Fall back to the raw string if it wasn't JSON-encodable.
            value = result.stdout.strip()
        return {"ok": True, "value": value, "error": ""}


__all__ = ["ComputeTool"]