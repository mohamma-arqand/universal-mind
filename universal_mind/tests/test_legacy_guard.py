"""Guard: no production module may import the orphaned legacy packages.

``telemetry/`` and ``synergy.py`` are legacy duplicates (``telemetry/errors.py``
shadows ``core/errors.py``; ``synergy.py`` is unreferenced). No *production*
module may depend on them — that would fork the single source of truth for
errors and layering. This test fails the suite if any non-test module imports
them, turning a silent drift risk into a hard architectural rule.

The references in ``gates/layering.py`` and ``tests/test_layering.py`` are
layer-map entries only (they name the packages, they do not import them).
"""

from __future__ import annotations

import ast
from pathlib import Path

_ORPHANED = {"universal_mind.telemetry", "universal_mind.synergy"}


def _import_targets(filepath: Path) -> list[str]:
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
    except (OSError, SyntaxError):
        return []
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.append(node.module)
    return targets


def test_no_production_import_of_legacy_packages() -> None:
    """Enforce that orphaned legacy packages are not imported by production code."""
    root = Path(__file__).resolve().parent.parent
    violations: list[str] = []
    for py in root.rglob("*.py"):
        rel = py.relative_to(root)
        parts = rel.parts
        # Skip tests, scripts, the orphaned packages themselves, and __pycache__.
        if "tests" in parts or "scripts" in parts or "__pycache__" in parts:
            continue
        modname = str(rel.with_suffix("")).replace("\\", ".").replace("/", ".")
        if modname.startswith("universal_mind.telemetry") or modname == "universal_mind.synergy":
            continue
        for target in _import_targets(py):
            if target in _ORPHANED or target.startswith("universal_mind.telemetry."):
                violations.append(f"{rel}: imports {target}")

    assert not violations, (
        "Production code imports an orphaned legacy package "
        "(telemetry/ or synergy.py): " + "; ".join(violations)
    )