"""Tool registry — one encyclopedia of every absorbed/connected tool.

The super-platform's foundation (Phase A): a single data structure that, for each
tool, records *what capability it has* (never its name), *which connection
mechanism reaches it* (subprocess / http / com), and *whether its capability can
be absorbed and re-implemented internally* (absorbable) — plus a contract and an
evidence trail so the same non-compensatory judgment used everywhere else can
rank tools against each other.

This does NOT replace :class:`~universal_mind.pantheon.registry.PantheonRegistry`;
it is the *absorb* view layered on top. ``PantheonRegistry`` already holds
``CapabilityDossier``/``OrganDescriptor`` (the "what I can do + how much I cost
+ how credible I am"). The registry here adds the two missing dimensions the
super-platform needs to actually reach the world:

    1. ``ConnectionMechanism`` — HOW a tool is reached (subprocess / http / com);
    2. ``absorbable`` — whether its capability is open and can be re-implemented
       internally (Phase C), versus closed and only connectable (like a licensed
       desktop app reached through COM).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConnectionMechanism(str, Enum):
    """The one way a tool is reached on a host.

    There are exactly three, and every external tool maps to one of them:
    subprocess (a CLI / agent you run), http (an API / service you call), and
    com (a Windows desktop app you drive through its object model).
    """

    SUBPROCESS = "subprocess"
    HTTP = "http"
    COM = "com"


@dataclass(frozen=True)
class ToolConnectionSpec:
    """How to reach a tool through a given mechanism.

    Exactly one of the fields is meaningful depending on ``mechanism``:
    - SUBPROCESS -> ``command`` (a shell command template);
    - HTTP       -> ``endpoint`` (a base URL);
    - COM        -> ``prog_id`` (the Windows COM ProgID, e.g. "Excel.Application").
    """

    mechanism: ConnectionMechanism
    command: str = ""
    endpoint: str = ""
    prog_id: str = ""


@dataclass(frozen=True)
class ToolEntry:
    """One tool in the encyclopedia: capability-first, connection + absorbability.

    ``capability`` is a stable slug of WHAT the tool does (e.g. "edit_image"),
    never the vendor name — so the brain asks for a capability and the registry
    returns the best tool that has it. ``absorbable`` marks whether the tool's
    capability is open (source available or a clear API spec) and therefore a
    candidate for internal re-implementation in Phase C.
    """

    name: str  # vendor/binary name (human-facing label only)
    capability: str  # the stable slug of what it can DO
    connection: ToolConnectionSpec  # how to reach it
    absorbable: bool  # can we re-implement its capability internally?
    evidence: list[dict[str, Any]] = field(default_factory=list)  # performance trail

    @property
    def connection_mechanism(self) -> ConnectionMechanism:
        return self.connection.mechanism

    def record_evidence(self, succeeded: bool, score: float, note: str = "") -> None:
        """Append one outcome to the evidence trail (the tool's show-of-work)."""
        self.evidence.append({"succeeded": succeeded, "score": score, "note": note})


class ToolRegistry:
    """The absorbed-tool encyclopedia: capability-indexed, mechanism-aware.

    Indexes tools by capability so the brain says "I need edit_image" and gets
    every tool (subprocess, http, or com) that can honor it, ranked by evidence.
    Deterministic and local — a plain in-memory index with no side effects.
    """

    def __init__(self) -> None:
        self._by_capability: dict[str, list[ToolEntry]] = {}
        self._by_name: dict[str, ToolEntry] = {}

    def register(self, entry: ToolEntry) -> str:
        """Add a tool to the encyclopedia (idempotent by name)."""
        if entry.name in self._by_name:
            return entry.name
        self._by_name[entry.name] = entry
        self._by_capability.setdefault(entry.capability, []).append(entry)
        return entry.name

    def tools_for(self, capability: str) -> list[ToolEntry]:
        """Every tool that can honor ``capability`` (possibly empty)."""
        return list(self._by_capability.get(capability, []))

    def capable(self, capability: str) -> bool:
        """True if at least one tool can honor the capability."""
        return bool(self._by_capability.get(capability))

    def absorbable_for(self, capability: str) -> list[ToolEntry]:
        """The subset of tools for a capability whose code/behavior we can absorb."""
        return [t for t in self.tools_for(capability) if t.absorbable]

    def best_for(self, capability: str) -> ToolEntry | None:
        """The highest-evidence tool for a capability, or None.

        Ranked by mean evidence score (descending); tools with no evidence trail
        rank below those with a proven record. Ties resolve by name for determinism.
        """
        tools = self.tools_for(capability)
        if not tools:
            return None
        return max(tools, key=lambda t: (_mean_score(t), -len(t.name), t.name))


def _mean_score(entry: ToolEntry) -> float:
    """Mean success score over the evidence trail; 0.0 with no trail."""
    if not entry.evidence:
        return 0.0
    scores = [
        e["score"] for e in entry.evidence if isinstance(e.get("score"), (int, float))
    ]
    return sum(scores) / len(scores) if scores else 0.0
