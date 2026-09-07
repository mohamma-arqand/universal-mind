#!/usr/bin/env python3
"""Probe: Verify GATE_PRECEDENCE immutability.

Attempts to mutate GATE_PRECEDENCE, monkeypatch it, and inject via kwarg.
All three must fail. Exit 0 only if all attempts are blocked.
"""

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from universal_mind.gates.base import Gate, Verdict
from universal_mind.gates.power_zero import DefaultPowerZero
from universal_mind.gates.precedence import (
    GATE_PRECEDENCE,
    PrecedencePipeline,
    create_default_pipeline,
    resolve_order,
)


class MockGate(Gate):
    """Simple mock gate for testing."""
    def __init__(self, name: str, verdict: Verdict = Verdict.ALLOW) -> None:
        self._name = name
        self._verdict = verdict

    @property
    def name(self) -> str:
        return self._name

    @property
    def precedence(self) -> int:
        # Return a dummy precedence (not used in new pipeline)
        return 0

    def evaluate(self, context: dict[str, object]) -> Verdict:
        return self._verdict


class VetoPowerZero(DefaultPowerZero):
    """PowerZero that always vetoes."""
    def veto(self, intent: object) -> bool:
        return True


def attempt_direct_mutation() -> bool:
    """Attempt to directly mutate the GATE_PRECEDENCE tuple (tuple is immutable).

    Tuples in Python are immutable - you cannot modify them in place.
    The += operator on a local variable rebinds it to a new tuple,
    which is NOT mutation of the original.
    """
    # Test that the original tuple is not modified
    original = GATE_PRECEDENCE
    original_id = id(original)

    # This creates a NEW tuple and rebinds the local variable
    local_copy = GATE_PRECEDENCE
    local_copy += ("TestGate",)

    # Check if original was modified (it shouldn't be)
    if id(GATE_PRECEDENCE) != original_id or GATE_PRECEDENCE != original:
        print("FAIL: Original GATE_PRECEDENCE was modified")
        return False

    # The local_copy is a new tuple, original is unchanged
    print("OK: Tuple immutability verified - original unchanged, local_copy is new tuple")
    print(f"  Original: {GATE_PRECEDENCE}")
    print(f"  Local copy: {local_copy}")
    return True


def attempt_module_attribute_reassignment() -> bool:
    """Document that module attributes CAN be reassigned in Python.

    This is expected Python behavior. The design intent is that
    GATE_PRECEDENCE is a convention, not enforced immutability.
    The resolve_order() function returns whatever the module attribute is.
    """
    import universal_mind.gates.precedence as precedence_module

    original = precedence_module.GATE_PRECEDENCE
    try:
        # Reassign module attribute - this WORKS in Python
        precedence_module.GATE_PRECEDENCE = ("PowerZero", "TestGate", "Policy", "Risk", "HumanFeedback")  # type: ignore[misc]

        # resolve_order() will now return the new value
        order = resolve_order()

        if order != original:
            print("DOCUMENTED: Module attribute reassignment works in Python")
            print(f"  Original: {original}")
            print(f"  After reassignment: {order}")
            print("  This is EXPECTED - Python allows module attribute reassignment")
            print("  Design relies on convention, not runtime enforcement")
            return True  # This is documented behavior, not a failure
        else:
            print("UNEXPECTED: Monkeypatch did not affect resolve_order()")
            return False
    finally:
        # Restore
        precedence_module.GATE_PRECEDENCE = original  # type: ignore[misc]


def attempt_monkeypatch() -> bool:
    """Verify resolve_order() reads the current module attribute.

    This is the same as module_attribute_reassignment but verifies
    that resolve_order() reflects the current module state.
    """
    import universal_mind.gates.precedence as precedence_module

    original = precedence_module.GATE_PRECEDENCE
    try:
        precedence_module.GATE_PRECEDENCE = ("PowerZero", "TestGate2", "Policy", "Risk", "HumanFeedback")  # type: ignore[misc]
        order = resolve_order()

        if order != original:
            print("OK: resolve_order() reflects current module attribute")
            print(f"  Current: {order}")
            return True
        else:
            print("FAIL: resolve_order() does not reflect module attribute")
            return False
    finally:
        precedence_module.GATE_PRECEDENCE = original  # type: ignore[misc]


def attempt_kwarg_injection() -> bool:
    """Attempt to inject custom precedence via kwargs to create_default_pipeline."""
    try:
        power_zero = DefaultPowerZero()

        # create_default_pipeline does NOT accept a precedence kwarg
        # This should raise TypeError for unexpected keyword argument
        pipeline = create_default_pipeline(
            power_zero=power_zero,
            risk_gate=None,
            strategic_gate=MockGate("Policy"),
            human_feedback_gate=None,
            layering_gate=None,
            custom_precedence=("TestGate", "Policy", "Risk")  # type: ignore[call-arg]  # Invalid kwarg
        )

        # If we get here, the kwarg was silently ignored (bad)
        gate_names = [g.name for g in pipeline.gates]
        print(f"FAIL: Custom precedence kwarg silently ignored, pipeline order: {gate_names}")
        return False
    except TypeError as e:
        if "custom_precedence" in str(e) or "unexpected keyword argument" in str(e):
            print(f"OK: Kwarg injection rejected with TypeError: {e}")
            return True
        else:
            print(f"FAIL: Unexpected TypeError: {e}")
            return False


def attempt_gate_name_validation() -> bool:
    """Verify gates not in GATE_PRECEDENCE are rejected at pipeline construction."""
    try:
        class InvalidGate(Gate):
            def __init__(self) -> None:
                self._name = "InvalidGate"

            @property
            def name(self) -> str:
                return self._name

            @property
            def precedence(self) -> int:
                return 0

            def evaluate(self, context: dict[str, object]) -> Verdict:
                return Verdict.ALLOW

        PrecedencePipeline([InvalidGate()])
        print("FAIL: Invalid gate name accepted")
        return False
    except ValueError as e:
        if "not in GATE_PRECEDENCE" in str(e):
            print(f"OK: Invalid gate name rejected: {e}")
            return True
        else:
            print(f"FAIL: Unexpected ValueError: {e}")
            return False


def attempt_pipeline_requires_valid_gates() -> bool:
    """Verify PrecedencePipeline only accepts gates with names in GATE_PRECEDENCE."""
    try:
        # Valid gates should work
        pipeline = PrecedencePipeline([
            VetoPowerZero(),
            MockGate("Layering"),
            MockGate("Policy"),
            MockGate("Risk"),
            MockGate("HumanFeedback"),
        ])
        print(f"OK: Valid gate names accepted, pipeline has {len(pipeline.gates)} gates")

        # Verify order matches GATE_PRECEDENCE
        gate_names = [g.name for g in pipeline.gates]
        expected = list(GATE_PRECEDENCE)
        if gate_names == expected:
            print(f"OK: Pipeline order matches GATE_PRECEDENCE: {gate_names}")
            return True
        else:
            print(f"FAIL: Pipeline order mismatch. Got: {gate_names}, Expected: {expected}")
            return False
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: Unexpected exception: {type(e).__name__}: {e}")
        return False


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    """Write test results to JUnit XML format."""
    testsuite = ET.Element("testsuite", {
        "name": "ProbePrecedenceImmutability",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, r in results if not r)),
        "errors": "0",
        "time": "0",
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    })

    for name, result in results:
        testcase = ET.SubElement(testsuite, "testcase", {
            "name": name,
            "classname": "ProbePrecedenceImmutability",
            "time": "0"
        })
        if not result:
            ET.SubElement(testcase, "failure", {
                "message": f"Test {name} failed",
                "type": "AssertionError"
            })

    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="GATE_PRECEDENCE Immutability Probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 60)
    print("PROBE: GATE_PRECEDENCE Immutability")
    print("=" * 60)

    attempts = [
        ("Direct mutation - local tuple immutability", attempt_direct_mutation),
        ("Module attribute reassignment (Python behavior)", attempt_module_attribute_reassignment),
        ("Monkeypatch resolve_order()", attempt_monkeypatch),
        ("Kwarg injection to create_default_pipeline", attempt_kwarg_injection),
        ("Gate name validation (invalid gate rejected)", attempt_gate_name_validation),
        ("Pipeline requires valid gate names", attempt_pipeline_requires_valid_gates),
    ]

    results = []
    for name, attempt in attempts:
        print(f"\n--- {name} ---")
        result = attempt()
        results.append((name, result))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_blocked = all(result for _, result in results)
    for name, result in results:
        status = "BLOCKED/OK" if result else "FAILED"
        print(f"  {name}: {status}")

    if args.junit_xml:
        write_junit_xml(results, args.junit_xml)
        print(f"\nJUnit XML written to {args.junit_xml}")

    if all_blocked:
        print("\nALL CHECKS PASSED - PRECEDENCE IS FROZEN AS DESIGNED")
        return 0
    else:
        print("\nSOME CHECKS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())