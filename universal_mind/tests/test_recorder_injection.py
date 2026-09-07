"""Tests for observability Recorder injection into ExecutiveMind.

Verifies the recorder is a pure side-channel: gate decisions, throttle blocks,
validations, and blocked paths emit ``gate.decision`` / ``executive.cycle``
events, and a broken (raising) recorder never changes cycle semantics.
"""

from __future__ import annotations

import ast
import unittest
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from universal_mind.core.clock import FrozenClock
from universal_mind.core.executive import (
    Decision,
    ExecutionThrottle,
    ExecutiveMind,
    StrategicDecision,
    StrategicGate,
)
from universal_mind.core.identity import DEFAULT_OWNER
from universal_mind.core.intent import Determinism, Intent
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import InMemoryStore
from universal_mind.observability.recorder import (
    MemoryRecorder,
    NullRecorder,
    RecordedEvent,
)
from universal_mind.pantheon.contracts import (
    EchoCapability,
)
from universal_mind.pantheon.registry import CapabilityDossier, PantheonRegistry


class RaisingRecorder:
    """Recorder double that always raises — must never break the cycle."""

    def record(self, event: str, /, **fields: object) -> None:
        raise RuntimeError('broken recorder')


class LocalUniversalMindTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FrozenClock(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
        self.store = InMemoryStore()
        self.memory = Mnemosyne(self.store, self.clock)
        self.registry = PantheonRegistry(self.store)
        self.recorder = MemoryRecorder(clock=self.clock)

    def dossier(self, name: str = 'echo', purpose: str = 'echo requests') -> CapabilityDossier:
        return CapabilityDossier(
            name=name,
            version='1.0.0',
            signature=f'{name}(intent, params)',
            purpose=purpose,
            cost_model='flat',
            latency_profile='instant',
            reliability='high',
            side_effects='none',
            reversible=True,
            required_secrets=[],
            failure_modes='none',
            dependencies=[],
            determinism=Determinism.STRICT,
            provenance={'producer': 'test', 'created_at': self.clock.now().isoformat(), 'owner_id': DEFAULT_OWNER.owner_id, 'explicit_fields': ['idempotent']},
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


class RecorderInjectionTests(LocalUniversalMindTests):
    def test_success_path_records_all_gates_and_cycle(self) -> None:
        """Every executed gate plus the final cycle is recorded."""
        self.registry.register(self.dossier(), EchoCapability())
        executive = ExecutiveMind(
            self.registry, self.memory, self.clock, DEFAULT_OWNER,
            recorder=self.recorder,
        )
        outcome = executive.handle(self.intent('echo me', 'echo'))
        self.assertEqual(outcome.status, 'ok')

        gates = self.gate_events()
        # PowerZero, Layering, Policy (composite), Risk are all evaluated for an
        # allowed intent. HumanFeedback is absent (no feedback gate configured).
        self.assertGreaterEqual(len(gates), 4)
        self.assertTrue(all(g.fields['allowed'] is True for g in gates))
        self.assertEqual(len({g.fields['gate'] for g in gates}), len(gates))

        cycles = self.cycle_events()
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0].fields['outcome'], 'ok')
        self.assertIsNone(cycles[0].fields['terminal_gate'])

    def test_blocked_intent_records_terminal_gate_not_skipped_ones(self) -> None:
        """When a gate denies, the cycle records that gate, and later gates emit nothing."""

        class BlockingGate(StrategicGate):
            def evaluate(self, intent: Intent, context: dict[str, Any]) -> StrategicDecision:
                if 'block' in intent.raw_text:
                    return StrategicDecision(decision=Decision.BLOCK, reason='policy blocked')
                return StrategicDecision(decision=Decision.PROCEED)

        self.registry.register(self.dossier(), EchoCapability())
        executive = ExecutiveMind(
            self.registry, self.memory, self.clock, DEFAULT_OWNER,
            strategic_gate=BlockingGate(),
            recorder=self.recorder,
        )
        outcome = executive.handle(self.intent('block please', 'echo'))
        self.assertEqual(outcome.status, 'blocked')

        gates = self.gate_events()
        # Only gates that actually ran are recorded. The Policy gate denies, so
        # Risk is skipped and must NOT appear.
        self.assertNotIn('Risk', {g.fields['gate'] for g in gates})
        policy_gate = [g for g in gates if g.fields['gate'] == 'Policy']
        self.assertEqual(len(policy_gate), 1)
        self.assertFalse(policy_gate[0].fields['allowed'])

        cycles = self.cycle_events()
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0].fields['outcome'], 'blocked')
        self.assertEqual(cycles[0].fields['terminal_gate'], 'Policy')

    def test_throttle_block_records_traffic_and_terminal_throttle(self) -> None:
        """Raising the throttle to its limit records an executive.cycle with terminal 'Throttle'."""
        self.registry.register(self.dossier(), EchoCapability())
        throttle = ExecutionThrottle(max_concurrent=1, error_rate_threshold=1.0)
        executive = ExecutiveMind(
            self.registry, self.memory, self.clock, DEFAULT_OWNER,
            throttle=throttle, recorder=self.recorder,
        )
        executive.handle(self.intent('first', 'echo'))
        self.recorder._events.clear()  # reset recorder between cycles
        outcome = executive.handle(self.intent('second', 'echo'))
        self.assertEqual(outcome.status, 'blocked')

        cycle = self.cycle_events()
        self.assertEqual(len(cycle), 1)
        self.assertEqual(cycle[0].fields['terminal_gate'], 'Throttle')

    def test_recorder_failure_does_not_change_cycle_semantics(self) -> None:
        """A raising recorder must be swallowed; the intent still executes fine."""
        self.registry.register(self.dossier(), EchoCapability())
        executive = ExecutiveMind(
            self.registry, self.memory, self.clock, DEFAULT_OWNER,
            recorder=RaisingRecorder(),
        )
        outcome = executive.handle(self.intent('echo me', 'echo'))
        self.assertEqual(outcome.status, 'ok')

    def test_null_recorder_by_default(self) -> None:
        """A default ExecutiveMind records nothing observable (NullRecorder)."""
        self.registry.register(self.dossier(), EchoCapability())
        executive = ExecutiveMind(
            self.registry, self.memory, self.clock, DEFAULT_OWNER,
        )
        executive.handle(self.intent('echo me', 'echo'))
        self.assertIsInstance(executive._recorder, NullRecorder)


class MemoryRecorderBoundsAndFailureVisibility(LocalUniversalMindTests):
    """Pins Mission 3.4-R §A (bounded ring) and §B (fail-open is audible)."""

    def test_bounded_recorder_keeps_newest_and_counts_drops(self) -> None:
        """With maxlen=N the recorder keeps the N newest and counts the evicted."""
        rec = MemoryRecorder(clock=self.clock, maxlen=3)
        for i in range(5):
            rec.record(f'e{i}', n=i)
        events = rec.events
        # Only the newest 3 survived.
        self.assertEqual([e.event for e in events], ['e2', 'e3', 'e4'])
        # Two events (e0, e1) were evicted by the fixed-size ring buffer.
        self.assertEqual(rec.dropped_events, 2)

    def test_unbounded_recorder_by_default_counts_no_drops(self) -> None:
        """maxlen=None (the default) keeps everything and never drops."""
        rec = MemoryRecorder(clock=self.clock)
        for i in range(50):
            rec.record(f'e{i}')
        self.assertEqual(len(rec.events), 50)
        self.assertEqual(rec.dropped_events, 0)

    def test_events_is_a_readonly_snapshot(self) -> None:
        """Mutating the returned tuple cannot corrupt the underlying recorder."""
        rec = MemoryRecorder(clock=self.clock)
        rec.record('a')
        snapshot = rec.events
        # The tuple is immutable; a list view of it must not leak into the holder.
        self.assertEqual(rec.events, snapshot)
        # Record after snapshot: the old snapshot is unaffected.
        rec.record('b')
        self.assertEqual(len(snapshot), 1)
        self.assertEqual(len(rec.events), 2)

    def test_recorder_failure_is_counted_and_logged(self) -> None:
        """A raising recorder stays fail-open but the failure is visible, not silent."""
        import logging

        from universal_mind.core import executive as exec_module

        self.registry.register(self.dossier(), EchoCapability())
        executive = ExecutiveMind(
            self.registry, self.memory, self.clock, DEFAULT_OWNER,
            recorder=RaisingRecorder(),
        )
        # Cycle must still complete (fail-open), exactly as before.
        outcome = executive.handle(self.intent('echo me', 'echo'))
        self.assertEqual(outcome.status, 'ok')
        # ...but the breakdown is now observable instead of silent.
        self.assertGreater(executive.recorder_failures, 0)
        with self.assertLogs(exec_module.logger, level=logging.WARNING) as ctx:
            # Trigger at least one more recorder call.
            executive.handle(self.intent('echo again', 'echo'))
        self.assertTrue(
            any('Recorder raised' in line for line in ctx.output),
            msg=f'no warning logged; got {ctx.output}',
        )


class RecorderFactoryStructuralGate(unittest.TestCase):
    """Mission 3.6-R §B: the recorder bound is ENFORCED, not just documented.

    This is an AST-based structural gate. It walks every non-test ``.py`` file
    under the package and fails if a ``MemoryRecorder(...)`` call site omits an
    explicit ``maxlen=`` argument. Rationale: a documentation comment alone does
    not stop an unbounded ``MemoryRecorder()`` from shipping; a test that
    greps/regexes source is brittle and easier to slip past, so we parse the
    AST instead (standard library only, no regex, no new dependency).

    Today every production site that needs a recorder goes through
    :func:`make_bounded_recorder`, so this test must pass. Its value is
    *tomorrow*: a future unbounded construction site flips it red.
    """

    PKG = Path(__file__).resolve().parents[1]  # universal_mind/package root

    def _non_test_py_files(self) -> Iterator[Path]:
        # Only the shipped package, excluding tests and the venv.
        for path in sorted(self.PKG.rglob("*.py")):
            if "tests" in path.parts:
                continue
            if any(part.startswith(".") for part in path.parts):
                continue
            yield path

    def _calls_memory_recorder_without_maxlen(self, path: Path) -> list[int]:
        """Return line numbers of MemoryRecorder( call sites lacking maxlen=."""
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            raise AssertionError(f"failed to parse {path}") from None
        offending: list[int] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id != "MemoryRecorder":
                    continue
                keywords = {kw.arg for kw in node.keywords}
                if "maxlen" not in keywords:
                    offending.append(node.lineno)
        return offending

    def test_no_production_memory_recorder_without_explicit_maxlen(self) -> None:
        """Every non-test MemoryRecorder construction passes an explicit maxlen."""
        seen = [p for p in self._non_test_py_files() if (
            "MemoryRecorder" in p.read_text(encoding="utf-8")
        )]
        violations: dict[str, list[int]] = {}
        for path in seen:
            bad = self._calls_memory_recorder_without_maxlen(path)
            if bad:
                violations[str(path)] = bad
        self.assertEqual(
            violations, {},
            msg="production MemoryRecorder() without explicit maxlen=: "
                f"{violations}. Use make_bounded_recorder(clock=...) instead.",
        )

    def test_factory_produces_bounded_recorder(self) -> None:
        """make_bounded_recorder forces a non-None maxlen by construction."""
        from universal_mind.observability.recorder import (
            DEFAULT_RECORDER_MAXLEN,
            make_bounded_recorder,
        )
        rec = make_bounded_recorder(clock=self.frozen_clock())
        self.assertIsNotNone(rec.maxlen)
        if rec.maxlen is not None:
            self.assertEqual(rec.maxlen, DEFAULT_RECORDER_MAXLEN)

    @staticmethod
    def frozen_clock() -> FrozenClock:
        from universal_mind.core.clock import FrozenClock
        return FrozenClock(datetime(2024, 1, 1, tzinfo=timezone.utc))


if __name__ == '__main__':
    unittest.main()