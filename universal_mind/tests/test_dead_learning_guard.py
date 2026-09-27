"""AST guard: the production tree must stay free of dead learning modules.

`path_optimization` and `merit_learning` (R49) had ZERO production importers —
their evidence trail (record_evidence) was never fed by real runs and a live
replacement existed (planner_learning for chains, absorption benchmark for tools).
Testing dead code is circular self-coverage that proves nothing reachable. This
guard fails the suite if any module imports them again, so the deletion is an
enforced rule rather than a silent re-fork.
"""

from __future__ import annotations

import ast
from pathlib import Path

_DEAD_MODULES = frozenset({"path_optimization", "merit_learning"})


def _py_sources() -> list[Path]:
    root = Path(__file__).resolve().parent.parent
    return [
        p
        for p in root.rglob("*.py")
        if "__pycache__" not in p.parts and "tests" not in p.parts
    ]


def test_no_module_imports_the_dead_learning_modules() -> None:
    offenders: list[str] = []
    for src in _py_sources():
        try:
            tree = ast.parse(src.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[-1] in _DEAD_MODULES:
                        offenders.append(f"{src.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.split(".")[-1] in _DEAD_MODULES:
                    offenders.append(f"{src.name}: from {module}")
    assert not offenders, f"dead learning modules are imported: {offenders}"


def test_the_files_are_gone() -> None:
    root = Path(__file__).resolve().parent.parent
    for name in _DEAD_MODULES:
        assert not (root / f"{name}.py").exists(), f"{name}.py was resurrected"


__test__ = True
