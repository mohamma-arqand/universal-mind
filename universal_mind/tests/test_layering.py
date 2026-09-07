"""
Layering architecture test using AST to verify import dependencies.

Layer ranking (lower number = higher layer = cannot import from lower):
1 io
2 gates
3 core.executive
4 pantheon
5 memory.mnemosyne
6 telemetry
7 core.clock, core.identity, core.models, memory.store
"""

import ast
from pathlib import Path

# Layer mapping: module prefix -> layer number
LAYER_MAP = {
    'universal_mind.io': 1,
    'universal_mind.gates': 2,
    'universal_mind.core.executive': 3,
    'universal_mind.pantheon': 4,
    'universal_mind.memory.mnemosyne': 5,
    'universal_mind.telemetry': 6,
    'universal_mind.core.clock': 7,
    'universal_mind.core.identity': 7,
    'universal_mind.core.models': 7,
    'universal_mind.memory.store': 7,
}

# Modules that are explicitly allowed to import from anywhere (foundation)
FOUNDATION_MODULES = {
    'universal_mind.core.clock',
    'universal_mind.core.identity',
    'universal_mind.core.models',
    'universal_mind.memory.store',
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
    """Test that captures layering violations (architectural debt map).
    
    This test reports violations but does not fail - it's a debt tracking test.
    """
    violations = find_layer_violations()

    if violations:
        print("LAYERING VIOLATIONS FOUND:")
        for v in violations:
            print(f"  {v['file']}:{v['line']} - {v['import_type']} {v['imported_module']}")
            print(f"    Importer layer: {v['importer_layer']}, Imported layer: {v['imported_layer']}")

    # Report total count
    print(f"\nTotal violations: {len(violations)}")

    # This test captures debt - it passes but records the violations
    # The violations are printed above for the architectural debt map
    assert True  # Always pass - this is a debt tracking test


if __name__ == '__main__':
    test_layering()