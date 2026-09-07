"""Mission 3.3-R: observability injection into ExecutiveMind.

These tests pin the Recorder as a pure side-channel:

* ``gate.decision`` events are emitted in the same gate order as the frozen
  ``resolve_order()`` source of truth (compared against the actual function,
  never a hard-coded list).
* With a ``FrozenClock`` every recorded ``at`` is deterministic and identical;
  with a step clock the ``at`` timestamps advance exactly when the clock does.
* Three gates allow and PowerZero denies — the terminal ``gate.decision`` is
  PowerZero with ``allowed=False`` and the cycle records ``blocked``.
* When an earlier gate denies, no ``gate.decision`` is emitted for the skipped
  gates that never ran (proven purely from the recorded events).
* With no Recorder injected, ``handle()`` behaves byte-for-byte identically to
  an instance carrying a ``NullRecorder`` (regression).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from universal_mind.core.clock import Clock, FrozenClock
from universal_mind.core.executive import (
    Decision,
    ExecutiveMind,
    StrategicDecision,
    StrategicGate,
)
from universal_mind.core.identity import DEFAULT_OWNER
from universal_mind.core.intent import Determinism, Intent
from universal_mind.gates.power_zero import PowerZero
from universal_mind.gates.precedence import resolve_order
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import InMemoryStore
from universal_mind.observability.recorder import (
    MemoryRecorder,
    NullRecorder,
    RecordedEvent,
)
from universal_mind.pantheon.contracts import EchoCapability
from universal_mind.pantheon.registry import CapabilityDossier, PantheonRegistry


class StepClock(Clock):
    """Mutable clock whose ``now()`` advances in place — proves timestamp source."""

    def __init__(self, start: datetime) -> None:
        self._now = start
        if self._now.tzinfo is None:
            self._now = self._now.replace(tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: int) -> None:
        self._now += timedelta(seconds=seconds)


class DenyGoalPowerZero(PowerZero):
    """PowerZero that vetoes a single goal (three other gates still allow)."""

    def veto(self, intent: Intent) -> bool:
        return intent.goal == 'forbidden'


class ObservableBase(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FrozenClock(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
        self.store = InMemoryStore()
        self.memory = Mnemosyne(self.store, self.clock)
        self.registry = PantheonRegistry(self.store)
        self.recorder = MemoryRecorder(clock=self.clock)

    def dossier(self, name: str = 'echo') -> CapabilityDossier:
        return CapabilityDossier(
            name=name,
            version='1.0.0',
            signature=f'{name}(intent, params)',
            purpose='echo requests',
            cost_model='flat',
            latency_profile='instant',
            reliability='high',
            side_effects='none',
            reversible=True,
            required_secrets=[],
            failure_modes='none',
            dependencies=[],
            determinism=Determinism.STRICT,
            provenance={
                'producer': 'test',
                'created_at': self.clock.now().isoformat(),
                'owner_id': DEFAULT_OWNER.owner_id,
                'explicit_fields': ['idempotent'],
            },
            idempotent=True,
        )

    def intent(self, raw_text: str, goal: str) -> Intent:
        return Intent.from_raw(
            raw_text=raw_text, goal=goal, success_criteria=['done'],
            owner_id=DEFAULT_OWNER.owner_id,
        )

    def gate_events(self) -> list[RecordedEvent]:
        return [e for e in self.recorder.events if e.event == 'gate.decision']

    def cycle_events(self) -> list[RecordedEvent]:
        return [e for e in self.recorder.events if e.event == 'executive.cycle']


class GateOrderAndDeterminism(ObservableBase):
    def test_gate_decision_order_matches_resolve_order(self) -> None:
        """gate.decision event order equals the live resolve_order() output."""
        self.registry.register(self.dossier(), EchoCapability())
        executive = ExecutiveMind(
            self.registry, self.memory, self.clock, DEFAULT_OWNER,
            recorder=self.recorder,
        )
        outcome = executive.handle(self.intent('echo me', 'echo'))
        self.assertEqual(outcome.status, 'ok')

        gates = self.gate_events()
        # Every non-skipped gate that actually ran is recorded; their relative
        # order must match the frozen source of truth exactly.
        expected = [g for g in resolve_order() if g in {e.fields['gate'] for e in gates}]
        self.assertEqual([g.fields['gate'] for g in gates], expected)

    def test_at_deterministic_with_frozen_clock_and_advances(self) -> None:
        """FrozenClock pins every `at`; a step clock advances it in lockstep."""
        self.registry.register(self.dossier(), EchoCapability())
        executive = ExecutiveMind(
            self.registry, self.memory, self.clock, DEFAULT_OWNER,
            recorder=self.recorder, power_zero=DenyGoalPowerZero(),
        )
        # Run two cycles; both at the frozen instant.
        executive.handle(self.intent('forbidden', 'forbidden'))
        executive.handle(self.intent('also forbidden', 'forbidden'))

        ats = {e.at for e in self.recorder.events}
        self.assertEqual(ats, {self.clock.now()})

        # With a step clock, `at` is taken from the injected clock and changes.
        t0 = datetime(2025, 5, 5, 5, 5, tzinfo=timezone.utc)
        step = StepClock(t0)
        rec = MemoryRecorder(clock=step)
        rec.record('a')
        step.advance(10)
        rec.record('b')
        # Event a was stamped at the clock's value when recorded (= t0).
        self.assertEqual(rec.events[0].at, t0)
        # Event b was stamped after the clock advanced by 10s.
        self.assertEqual(rec.events[1].at, t0 + timedelta(seconds=10))
        self.assertNotEqual(rec.events[0].at, rec.events[1].at)
        # Neither came from the host clock: they exactly match step.now() at each point.
        self.assertEqual(rec.events[1].at, step.now())


class VetoAndShortCircuit(ObservableBase):
    def test_power_zero_deny_terminates_with_terminal_event(self) -> None:
        """Three gates allow; PowerZero denies — terminal event is PowerZero(blocked)."""
        self.registry.register(self.dossier(), EchoCapability())
        executive = ExecutiveMind(
            self.registry, self.memory, self.clock, DEFAULT_OWNER,
            recorder=self.recorder, power_zero=DenyGoalPowerZero(),
        )
        outcome = executive.handle(self.intent('forbidden thing', 'forbidden'))
        self.assertEqual(outcome.status, 'blocked')

        gates = self.gate_events()
        # PowerZero is the deny -> it is the ONLY non-skipped gate decision, and
        # it is therefore also the LAST recorded gate.decision.
        self.assertEqual([g.fields['gate'] for g in gates], ['PowerZero'])
        self.assertFalse(gates[-1].fields['allowed'])

        cycles = self.cycle_events()
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0].fields['outcome'], 'blocked')
        self.assertEqual(cycles[0].fields['terminal_gate'], 'PowerZero')

    def test_earlier_deny_emits_no_decision_for_later_gates(self) -> None:
        """A denying policy gate short-circuits later gates out of the records."""

        class BlockingPolicy(StrategicGate):
            def evaluate(self, intent: Intent, context: dict[str, Any]) -> StrategicDecision:
                if 'nosir' in intent.raw_text:
                    return StrategicDecision(decision=Decision.BLOCK, reason='policy says no')
                return StrategicDecision(decision=Decision.PROCEED)

        self.registry.register(self.dossier(), EchoCapability())
        executive = ExecutiveMind(
            self.registry, self.memory, self.clock, DEFAULT_OWNER,
            strategic_gate=BlockingPolicy(), recorder=self.recorder,
        )
        outcome = executive.handle(self.intent('nosir please', 'echo'))
        self.assertEqual(outcome.status, 'blocked')

        ran = {g.fields['gate'] for g in self.gate_events()}
        # PowerZero and Layering ran and allowed; Policy denied. Risk is skipped.
        self.assertIn('PowerZero', ran)
        self.assertIn('Policy', ran)
        self.assertNotIn('Risk', ran)

        policy_event = [g for g in self.gate_events() if g.fields['gate'] == 'Policy']
        self.assertEqual(len(policy_event), 1)
        self.assertFalse(policy_event[0].fields['allowed'])


class Regression(ObservableBase):
    def test_no_recorder_is_byte_identical_to_null_recorder(self) -> None:
        """handle() without a recorder behaves identically to one with NullRecorder."""
        self.registry.register(self.dossier(), EchoCapability())

        def normalized(record: dict[str, Any]) -> tuple[Any, ...]:
            """Drop generated IDs; keep the deterministic outcome fields."""
            payload = record.get('payload') or {}
            return (
                record.get('kind'),
                record.get('created_at'),
                tuple(sorted((k, json.dumps(v, sort_keys=True, default=str))
                             for k, v in payload.items())),
            )

        def run_with(recorder: Any):
            store = InMemoryStore()
            memory = Mnemosyne(store, self.clock)
            reg = PantheonRegistry(store)
            reg.register(self.dossier(), EchoCapability())
            exec_ = ExecutiveMind(reg, memory, self.clock, DEFAULT_OWNER, recorder=recorder)
            out = exec_.handle(self.intent('echo me', 'echo'))
            return out, sorted(normalized(r) for r in store.read_all())

        out_no, records_no = run_with(None)
        out_null, records_null = run_with(NullRecorder())

        # Records carry randomly-generated IDs, so compare deterministic fields.
        self.assertEqual(out_no.status, out_null.status)
        self.assertEqual(records_no, records_null)
        # The default instance truly falls back to a NullRecorder.
        default_exec = ExecutiveMind(self.registry, self.memory, self.clock, DEFAULT_OWNER)
        self.assertIsInstance(default_exec._recorder, NullRecorder)


class ReceiptFailPathAndDeterminism(unittest.TestCase):
    """Mission 3.6-R §A: prove the receipt's negative path, not just pass.

    A gate that has never been seen to close is not a gate. This class runs the
    actual ``scripts/generate_receipt.py`` (the single source of truth — no
    duplicate, Step D) end-to-end in a subprocess against synthetic JUnit XML
    and asserts *real* exit codes and *absence* of receipts, never mocks.
    """

    SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_receipt.py"
    PYTHON = sys.executable

    def _run(self, junit: Path, output: Path | None = None) -> subprocess.CompletedProcess[str]:
        argv = [self.PYTHON, str(self.SCRIPT), str(junit)]
        if output is not None:
            argv += ["--output", str(output)]
        # Injected project root so git detection and default paths resolve.
        env = dict(os.environ)
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
        return subprocess.run(argv, capture_output=True, text=True, env=env, check=False)

    @staticmethod
    def _write(xml_text: str, path: Path) -> None:
        path.write_text(xml_text.strip(), encoding="utf-8")

    def _tmp(self, name: str) -> Path:
        d = tempfile.mkdtemp(prefix="receipt_test_")
        return Path(d) / name

    def test_failure_scenario_exit_nonzero_and_overall_fail(self) -> None:
        """A JUnit log with failures yields exit=1 and overall='fail'."""
        xml = self._tmp("fail.xml")
        out = self._tmp("fail.json")
        self._write(
            '<testsuite tests="2" failures="1" errors="0" skipped="0">'
            '<testcase name="a"/><testcase name="b"><failure/></testcase></testsuite>',
            xml,
        )
        proc = self._run(xml, out)
        self.assertNotEqual(proc.returncode, 0)
        receipt = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["overall"], "fail")
        self.assertEqual(receipt["tests"]["failures"], 1)

    def test_vacuous_zero_tests_exit_nonzero_and_overall_fail(self) -> None:
        """tests='0' is not a pass: overall must be 'fail', exit nonzero."""
        xml = self._tmp("zero.xml")
        out = self._tmp("zero.json")
        self._write('<testsuite tests="0" failures="0" errors="0" skipped="0"/>', xml)
        proc = self._run(xml, out)
        self.assertNotEqual(proc.returncode, 0)
        receipt = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["overall"], "fail")

    def test_missing_xml_exit_2_and_no_receipt_written(self) -> None:
        """A missing XML file exits 2 and writes NO receipt file."""
        missing = self._tmp("missing.xml")  # never created
        out = self._tmp("missing.json")
        self.assertFalse(missing.exists())
        proc = self._run(missing, out)
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(out.exists(), msg="must not write a receipt when XML is missing")

    def test_malformed_xml_exit_2_and_no_receipt_written(self) -> None:
        """Broken (unparseable) XML exits 2 and writes NO receipt file."""
        malformed = self._tmp("bad.xml")
        out = self._tmp("bad.json")
        self._write("<testsuite><testcase", malformed)  # intentionally truncated tag
        proc = self._run(malformed, out)
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(out.exists(), msg="must not write a receipt when XML is malformed")

    def test_deterministic_output_differs_only_by_generated_at(self) -> None:
        """Two runs over identical input produce receipts differing only in timestamp."""
        xml = self._tmp("ok.xml")
        out1 = self._tmp("run1.json")
        out2 = self._tmp("run2.json")
        self._write(
            '<testsuite tests="3" failures="0" errors="0" skipped="0">'
            '<testcase name="a"/><testcase name="b"/><testcase name="c"/></testsuite>',
            xml,
        )
        r1, r2 = self._run(xml, out1), self._run(xml, out2)
        self.assertEqual(r1.returncode, 0)
        self.assertEqual(r2.returncode, 0)
        a = json.loads(out1.read_text(encoding="utf-8"))
        b = json.loads(out2.read_text(encoding="utf-8"))
        self.assertEqual(a["overall"], "pass")
        self.assertEqual(a["tests"], b["tests"])
        self.assertEqual(a["checks"], b["checks"])
        self.assertEqual(a["schema_version"], b["schema_version"])
        self.assertNotEqual(a["generated_at"], b["generated_at"])
        # remove the volatile field; the remainder must be identical
        del a["generated_at"]
        del b["generated_at"]
        self.assertEqual(a, b, msg="non-timestamp fields must be deterministic")


if __name__ == '__main__':
    unittest.main()