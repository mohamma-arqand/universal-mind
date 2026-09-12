"""Spec introspection — the type-2 absorption pre-step (Phase 2b).

Phase 2c will re-implement an open tool's logic as internal code. Before that, the
system must *read* the tool's interface — its name, what it does (capability), its
inputs, and how it is reached. This module does that reading from a small,
structured tool spec (a JSON-ish dictionary), turning it into a
:class:`~universal_mind.tool_registry.ToolEntry` ready for the encyclopedia.

This is deliberately a *deterministic* reader over a declared spec, not a free-text
parser of arbitrary documentation — the honest boundary. A spec that is missing a
required field is refused with a clear error (never a guessed default): an
unparseable tool is not absorbed, only reported.

Deterministic and pure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from universal_mind.tool_registry import (
    ConnectionMechanism,
    ToolConnectionSpec,
    ToolEntry,
)

_REQUIRED = ("name", "capability", "mechanism")


@dataclass(frozen=True)
class SpecReading:
    """The parsed result of studying one tool spec."""

    entry: ToolEntry | None          # None when the spec is unparseable
    warnings: tuple[str, ...]        # non-fatal observations about the spec
    error: str                       # reason the spec was refused ("" if parsed)


def read_spec(spec: dict[str, Any]) -> SpecReading:
    """Parse a structured tool spec into a :class:`ToolEntry`.

    Expected shape:
        {
            "name": str,            # vendor/binary label
            "capability": str,      # stable capability slug (what it DOES)
            "mechanism": "subprocess" | "http" | "com",
            "command"?: str,        # subprocess command (mechanism=subprocess)
            "endpoint"?: str,       # base URL (mechanism=http)
            "prog_id"?: str,        # COM ProgID (mechanism=com)
            "absorbable"?: bool,    # default False (closed)
        }

    A spec missing a required key (name/capability/mechanism) or carrying an
    unknown mechanism is refused — we never fabricate a tool from a broken spec.
    """
    missing = [k for k in _REQUIRED if k not in spec or not str(spec.get(k, "")).strip()]
    if missing:
        return SpecReading(entry=None, warnings=(), error=f"missing required field(s): {', '.join(missing)}")

    name = str(spec["name"]).strip()
    capability = str(spec["capability"]).strip()
    mechanism_raw = str(spec["mechanism"]).strip().lower()
    try:
        mechanism = ConnectionMechanism(mechanism_raw)
    except ValueError:
        return SpecReading(entry=None, warnings=(), error=f"unknown mechanism: {mechanism_raw!r}")

    warnings: list[str] = []
    # Build the connection spec from the mechanism's one meaningful field.
    if mechanism is ConnectionMechanism.SUBPROCESS:
        command = str(spec.get("command", "")).strip()
        if not command:
            warnings.append("subprocess tool has no command; it will fail until one is supplied")
        conn = ToolConnectionSpec(mechanism=mechanism, command=command)
    elif mechanism is ConnectionMechanism.HTTP:
        endpoint = str(spec.get("endpoint", "")).strip()
        if not endpoint:
            warnings.append("http tool has no endpoint; it will fail until one is supplied")
        conn = ToolConnectionSpec(mechanism=mechanism, endpoint=endpoint)
    else:  # COM
        prog_id = str(spec.get("prog_id", "")).strip()
        if not prog_id:
            warnings.append("com tool has no prog_id; it will fail until one is supplied")
        conn = ToolConnectionSpec(mechanism=mechanism, prog_id=prog_id)

    absorbable = bool(spec.get("absorbable", False))
    entry = ToolEntry(name=name, capability=capability, connection=conn, absorbable=absorbable)
    return SpecReading(entry=entry, warnings=tuple(warnings), error="")


__all__ = ["SpecReading", "read_spec"]