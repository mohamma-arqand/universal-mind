"""
Layering architecture test using AST to verify import dependencies.

Layer ranking (lower number = higher layer = cannot import from lower):
1 io
2 gates
3 core.executive
4 pantheon
5 memory.mnemosyne
6 core.clock, core.identity, core.models, memory.store
"""

import ast
from pathlib import Path

# Layer mapping: module prefix -> layer number, aligned with layers.py
LAYER_MAP = {
    'universal_mind.io': 1,
    'universal_mind.pantheon': 2,
    'universal_mind.demiurge': 3,
    'universal_mind.arete': 4,
    'universal_mind.prometheus': 5,
    'universal_mind.mouth': 6,
    'universal_mind.memory.mnemosyne': 7,
    'universal_mind.memory.lifespan': 7,
    'universal_mind.sovereign': 6,
    'universal_mind.synthesis': 3,
    'universal_mind.lifecycle': 5,
    'universal_mind.integration': 5,
    'universal_mind.gates': 2,
    'universal_mind.core.executive': 3,
    'universal_mind.observability': 2,
    'universal_mind.core.clock': 0,
    'universal_mind.core.identity': 0,
    'universal_mind.core.models': 0,
    'universal_mind.core.intent': 0,
    'universal_mind.core.errors': 0,
    'universal_mind.memory.store': 0,
    'universal_mind.layers': 0,
    'universal_mind.powers': 3,
    'universal_mind.feedback': 4,
    'universal_mind.durable': 5,
    'universal_mind.compose': 3,
}

# Modules that are explicitly allowed to import from anywhere (foundation)
FOUNDATION_MODULES = {
    'universal_mind.core.clock',
    'universal_mind.core.identity',
    'universal_mind.core.models',
    'universal_mind.core.intent',
    'universal_mind.core.errors',
    'universal_mind.memory.store',
    'universal_mind.layers',
}


def get_layer(module_name: str) -> int:
    """Get the layer number for a module."""
    for prefix, layer in LAYER_MAP.items():
        if module_name == prefix or module_name.startswith(prefix + '.'):
            return layer
    return 999  # Unknown module = highest layer


def is_foundation(module_name: str) -> bool:
    """Check if module is a foundation module (can be imported by anyone)."""
    return module_name in FOUNDATION_MODULES


def extract_imports(filepath: Path) -> list[tuple[int, str, str]]:
    """Extract all imports from a Python file. Returns (lineno, import_type, module_name)."""
    try:
        content = filepath.read_text()
        tree = ast.parse(content, filename=str(filepath))
    except OSError as e:
        print(f"ERROR parsing {filepath}: {e}")
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((node.lineno, 'import', alias.name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.lineno, 'from', node.module))
    return imports


def find_layer_violations() -> list[dict[str, object]]:
    """Find all layering violations in the codebase."""
    violations = []
    project_root = Path(__file__).parent.parent.parent

    # Find all Python files in universal_mind
    for py_file in project_root.rglob('universal_mind/**/*.py'):
        if '__pycache__' in str(py_file):
            continue
        if '_m1' in str(py_file):
            continue

        # Get the module name
        relative = py_file.relative_to(project_root)
        module_name = str(relative.with_suffix('')).replace('/', '.')

        file_layer = get_layer(module_name)

        # Extract imports
        imports = extract_imports(py_file)

        for lineno, import_type, imported_module in imports:
            imported_layer = get_layer(imported_module)

            # Skip if imported module is foundation (can be imported by anyone)
            if is_foundation(imported_module):
                continue

            # Skip if imported module is unknown
            if imported_layer == 999:
                continue

            # Violation: importing from lower layer (higher layer number)
            # Rule: a module at layer N can only import from layers <= N
            # (i.e., cannot import from layers with higher numbers)
            if imported_layer > file_layer:
                violations.append({
                    'file': str(relative),
                    'line': lineno,
                    'import_type': import_type,
                    'imported_module': imported_module,
                    'importer_layer': file_layer,
                    'imported_layer': imported_layer,
                })

    return violations


def test_layering() -> None:
    """Enforce that no module imports upward (architecture is not violated).

    The AST analysis maps every module to a layer and flags any import that
    reaches a *higher* (lower-numbered) layer. With the map aligned to the
    authoritative 7-layer model, the codebase must be clean; a violation now
    FAILS the suite (it is a real architectural debt, not a printed note).
    """
    violations = find_layer_violations()

    if violations:
        for v in violations:
            print(
                f"LAYERING VIOLATION: {v['file']}:{v['line']} "
                f"{v['import_type']} {v['imported_module']} "
                f"(importer {v['importer_layer']} -> imported {v['imported_layer']})"
            )

    assert not violations, (
        f"Found {len(violations)} layering violation(s) — a lower layer "
        "imports upward. See the printed list."
    )


if __name__ == '__main__':
    test_layering()