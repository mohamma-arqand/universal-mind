"""Continuous self-code-audit — periodic, automatic hygiene for the mind's own code.

The G4 foundational audit was a one-shot human-driven pass. This module makes
that discipline *continuous*: a deterministic scanner walks the mind's own source
tree and flags well-understood anti-patterns — empty modules, orphaned imports of
removed packages, and files with no docstring — writing findings to the ledger as
an ``self_code_audit`` record. The mind keeps itself clean over time, not just
when a human happens to look.

It reads source, never mutates it; the audit itself is auditable.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from universal_mind.core.identity import DEFAULT_OWNER, Identity
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import MemoryStore


@dataclass(frozen=True)
class AuditFinding:
    """One code-hygiene issue with its location and severity."""

    path: str
    kind: str            # 'empty_module' | 'orphaned_import' | 'no_docstring'
    detail: str


@dataclass(frozen=True)
class CodeAuditReport:
    """The result of one self-code-audit pass."""

    findings: tuple[AuditFinding, ...]
    clean: bool
    files_scanned: int
    ledger_record_id: str | None = None


# Packages confirmed removed (G4); importing them is an orphaned reference.
_ORPHANED = {"universal_mind.telemetry", "universal_mind.synergy"}


def scan_source(root: Path) -> tuple[AuditFinding, ...]:
    """Scan ``root`` for known anti-patterns; return findings (empty == clean)."""
    findings: list[AuditFinding] = []
    for py in sorted(root.rglob("*.py")):
        if "__pycache__" in py.parts or "scripts" in py.parts or "tests" in py.parts:
            continue
        rel = str(py.relative_to(root)).replace("\\", "/")

        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=rel)
        except (OSError, SyntaxError):
            continue

        # 1. Empty module (no meaningful statements beyond the docstring).
        body = [n for n in tree.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str))]
        if not body:
            findings.append(AuditFinding(path=rel, kind="empty_module", detail="no statements beyond a docstring"))

        # 2. Orphaned imports of removed packages.
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and (node.module in _ORPHANED or node.module.startswith("universal_mind.telemetry."))
            ):
                findings.append(AuditFinding(path=rel, kind="orphaned_import", detail=f"imports {node.module}"))

        # 3. Missing module docstring.
        if not (ast.get_docstring(tree)):
            findings.append(AuditFinding(path=rel, kind="no_docstring", detail="module has no docstring"))

    return tuple(findings)


def run_self_audit(
    root: Path,
    store: MemoryStore | None = None,
    *,
    owner: Identity = DEFAULT_OWNER,
    clock: Any | None = None,
) -> CodeAuditReport:
    """Run one audit pass and (optionally) record it to the ledger as ``self_code_audit``."""
    findings = scan_source(root)
    files = sum(
        1 for py in sorted(root.rglob("*.py"))
        if "__pycache__" not in py.parts and "scripts" not in py.parts and "tests" not in py.parts
    )
    clean = not findings

    record_id: str | None = None
    if store is not None:
        from universal_mind.core.clock import SystemClock

        mnemosyne = Mnemosyne(store, clock if clock is not None else SystemClock())
        record_id = mnemosyne.record(
            owner_id=owner.owner_id,
            kind="self_code_audit",
            payload={
                "clean": clean,
                "files_scanned": files,
                "findings": [{"path": f.path, "kind": f.kind, "detail": f.detail} for f in findings],
            },
            provenance={"producer": "SelfCodeAudit", "owner_id": owner.owner_id},
        )

    return CodeAuditReport(findings=findings, clean=clean, files_scanned=files, ledger_record_id=record_id)