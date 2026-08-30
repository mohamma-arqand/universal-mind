#!/usr/bin/env python3
"""Probe: Verify PowerZero is terminal veto.

Run veto scenario and prove no downstream gates and no fallback execute.
Counts actual calls, not just log text.
"""

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from universal_mind.core.identity import DEFAULT_OWNER
from universal_mind.core.intent import Intent
from universal_mind.gates.base import Verdict
from universal_mind.gates.power_zero import PowerZero
from universal_mind.gates.precedence import PrecedencePipeline, create_default_pipeline


class CountingGate:
    """Gate that counts how many times evaluate() is called.

    Implements the Gate protocol properly.
    """

    def __init__(self, name: str, should_deny: bool = False):
        self._name = name
        self.should_deny = should_deny
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def precedence(self) -> int:
        return 0  # Not used in new pipeline

    def evaluate(self, context) -> Verdict:
        self.call_count += 1
        if self.should_deny:
            return Verdict.DENY
        return Verdict.ALLOW


class CountingPowerZero(PowerZero):
    """PowerZero that counts calls."""

    def __init__(self):
        super().__init__()
        self.call_count = 0
        self.veto_count = 0

    def evaluate(self, context) -> Verdict:
        self.call_count += 1
        verdict = super().evaluate(context)
        if verdict == Verdict.DENY:
            self.veto_count += 1
        return verdict


def test_powerzero_veto_stops_downstream() -> tuple[bool, dict]:
    """Test that PowerZero veto stops all downstream gates."""
    power_zero = CountingPowerZero()

    # Create downstream gates that count calls
    layering_gate = CountingGate("Layering")
    policy_gate = CountingGate("Policy")
    risk_gate = CountingGate("Risk")
    feedback_gate = CountingGate("HumanFeedback")

    # Make PowerZero return DENY
    class VetoPowerZero(CountingPowerZero):
        def evaluate(self, context) -> Verdict:
            self.call_count += 1
            self.veto_count += 1
            return Verdict.DENY

    power_zero = VetoPowerZero()

    # Create pipeline with all gates
    pipeline = PrecedencePipeline([
        power_zero,
        layering_gate,
        policy_gate,
        risk_gate,
        feedback_gate,
    ])

    # Evaluate with a context that triggers veto
    context = {"intent": Intent.from_raw(
        raw_text="test", goal="test", success_criteria=["test"],
        owner_id=DEFAULT_OWNER.owner_id
    )}

    judgment = pipeline.evaluate(context)

    # Check results
    downstream_calls = (
        layering_gate.call_count +
        policy_gate.call_count +
        risk_gate.call_count +
        feedback_gate.call_count
    )

    result = {
        "power_zero_calls": power_zero.call_count,
        "power_zero_vetoes": power_zero.veto_count,
        "layering_calls": layering_gate.call_count,
        "policy_calls": policy_gate.call_count,
        "risk_calls": risk_gate.call_count,
        "feedback_calls": feedback_gate.call_count,
        "downstream_calls": downstream_calls,
        "final_decision": judgment.decision.value,
        "trace": [(r.gate_name, r.verdict.value, r.skipped) for r in judgment.trace],
    }

    # PowerZero should be called once and veto
    # All downstream gates should be skipped (not evaluated)
    success = (
        power_zero.call_count == 1 and
        power_zero.veto_count == 1 and
        downstream_calls == 0 and
        judgment.decision == Verdict.DENY
    )

    # Check trace: PowerZero evaluated, rest skipped
    trace_ok = (
        len(judgment.trace) == 5 and
        judgment.trace[0].gate_name == "PowerZero" and
        judgment.trace[0].verdict == Verdict.DENY and
        judgment.trace[0].skipped == False and
        all(r.skipped == True and r.verdict == Verdict.DENY for r in judgment.trace[1:])
    )

    return success and trace_ok, result


def test_powerzero_allow_allows_downstream() -> tuple[bool, dict]:
    """Test that PowerZero ALLOW allows downstream gates to run."""
    power_zero = CountingPowerZero()

    layering_gate = CountingGate("Layering")
    policy_gate = CountingGate("Policy")
    risk_gate = CountingGate("Risk")
    feedback_gate = CountingGate("HumanFeedback")

    pipeline = PrecedencePipeline([
        power_zero,
        layering_gate,
        policy_gate,
        risk_gate,
        feedback_gate,
    ])

    context = {"intent": Intent.from_raw(
        raw_text="test", goal="test", success_criteria=["test"],
        owner_id=DEFAULT_OWNER.owner_id
    )}

    judgment = pipeline.evaluate(context)

    downstream_calls = (
        layering_gate.call_count +
        policy_gate.call_count +
        risk_gate.call_count +
        feedback_gate.call_count
    )

    result = {
        "power_zero_calls": power_zero.call_count,
        "downstream_calls": downstream_calls,
        "final_decision": judgment.decision.value,
    }

    success = (
        power_zero.call_count == 1 and
        power_zero.veto_count == 0 and
        downstream_calls == 4 and  # All 4 downstream gates should run
        judgment.decision == Verdict.ALLOW
    )

    return success, result


def test_create_default_pipeline_powerzero_terminal() -> tuple[bool, dict]:
    """Test create_default_pipeline with PowerZero veto."""
    power_zero = CountingPowerZero()

    class VetoPowerZero(CountingPowerZero):
        def evaluate(self, context) -> Verdict:
            self.call_count += 1
            self.veto_count += 1
            return Verdict.DENY

    power_zero = VetoPowerZero()

    pipeline = create_default_pipeline(
        power_zero=power_zero,
        risk_gate=None,
        strategic_gate=CountingGate("Policy"),
        human_feedback_gate=None,
        layering_gate=CountingGate("Layering"),
    )

    context = {"intent": Intent.from_raw(
        raw_text="test", goal="test", success_criteria=["test"],
        owner_id=DEFAULT_OWNER.owner_id
    )}

    judgment = pipeline.evaluate(context)

    # Count downstream calls
    downstream_calls = 0
    for gate in pipeline.gates:
        if gate.name != "PowerZero" and hasattr(gate, 'call_count'):
            downstream_calls += gate.call_count

    result = {
        "power_zero_calls": power_zero.call_count,
        "power_zero_vetoes": power_zero.veto_count,
        "downstream_calls": downstream_calls,
        "final_decision": judgment.decision.value,
    }

    success = (
        power_zero.call_count == 1 and
        power_zero.veto_count == 1 and
        downstream_calls == 0 and
        judgment.decision == Verdict.DENY
    )

    return success, result


def write_junit_xml(results, output_file):
    """Write test results to JUnit XML format."""
    testsuite = ET.Element("testsuite", {
        "name": "ProbePowerZeroTerminal",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, r in results if not r)),
        "errors": "0",
        "time": "0",
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    })

    for name, result in results:
        testcase = ET.SubElement(testsuite, "testcase", {
            "name": name,
            "classname": "ProbePowerZeroTerminal",
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
    parser = argparse.ArgumentParser(description="PowerZero Terminal Veto Probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 60)
    print("PROBE: PowerZero Terminal Veto")
    print("=" * 60)

    tests = [
        ("PowerZero veto stops downstream gates", test_powerzero_veto_stops_downstream),
        ("PowerZero allow allows downstream", test_powerzero_allow_allows_downstream),
        ("create_default_pipeline PowerZero terminal", test_create_default_pipeline_powerzero_terminal),
    ]

    all_passed = True
    test_results = []

    for name, test_func in tests:
        print(f"\n--- {name} ---")
        passed, result = test_func()
        test_results.append((name, passed))
        status = "PASS" if passed else "FAIL"
        print(f"  Result: {status}")
        for k, v in result.items():
            print(f"    {k}: {v}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)

    if args.junit_xml:
        write_junit_xml(test_results, args.junit_xml)
        print(f"\nJUnit XML written to {args.junit_xml}")

    if all_passed:
        print("ALL TESTS PASSED - POWERZERO IS TERMINAL")
        return 0
    else:
        print("SOME TESTS FAILED - POWERZERO NOT TERMINAL")
        return 1


if __name__ == "__main__":
    sys.exit(main())