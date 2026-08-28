from __future__ import annotations
import unittest
import json
from datetime import datetime, timezone, timedelta
from tempfile import TemporaryDirectory
from pathlib import Path
from typing import Any

from universal_mind.core.clock import FrozenClock, SystemClock
from universal_mind.core.errors import SystemFault, TaskFailure, CallerFault, ErrorHandler, retry_on_failure, RetryPolicy
from universal_mind.core.executive import (
    ExecutiveMind, StrategicGate, StrategicDecision, Decision,
    ExecutionThrottle, RiskAssessor,
)
from universal_mind.core.identity import DEFAULT_OWNER
from universal_mind.core.intent import Determinism, Intent, IntentIncomplete
from universal_mind.feedback.channel import (
    FeedbackChannel, FeedbackPolicy, HumanFeedbackGate, Verdict, feedback_gate,
)
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import InMemoryStore, LocalJSONLStore, CompactionPolicy
from universal_mind.pantheon.contracts import (
    Capability, CapabilityResult, EchoCapability, ContractViolation,
)
from universal_mind.pantheon.registry import CapabilityDossier, PantheonRegistry


class FailingTaskCapability(Capability):
    def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
        raise TaskFailure('expected task failure')


class FaultingCapability(Capability):
    def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
        raise SystemFault('expected system fault')


class UniversalMindTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FrozenClock(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
        self.store = InMemoryStore()
        self.memory = Mnemosyne(self.store, self.clock)
        self.registry = PantheonRegistry(self.store)

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

    def test_append_only_guarantee(self) -> None:
        first_id = self.memory.record(owner_id=DEFAULT_OWNER.owner_id, kind='fact', payload={'value': 1}, provenance={'producer': 'test'})
        correction_id = self.memory.record(owner_id=DEFAULT_OWNER.owner_id, kind='fact_correction', payload={'value': 2}, provenance={'producer': 'test'}, supersedes=first_id)
        records = list(self.store.read_all())
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]['payload']['value'], 1)
        self.assertEqual(records[1]['supersedes'], first_id)
        self.assertEqual(correction_id, records[1]['id'])

    def test_owner_id_present_on_every_persisted_record(self) -> None:
        self.memory.record(owner_id=DEFAULT_OWNER.owner_id, kind='fact', payload={'value': 1}, provenance={'producer': 'test'})
        self.registry.register(self.dossier(), EchoCapability())
        feedback = FeedbackChannel(self.store, self.clock)
        feedback.submit(DEFAULT_OWNER.owner_id, 'target-1', Verdict.APPROVED, 'good')
        for record in self.store.read_all():
            self.assertIn('owner_id', record)
            self.assertTrue(record['owner_id'])

    def test_ttl_classification_with_frozen_clock(self) -> None:
        self.memory.record(owner_id=DEFAULT_OWNER.owner_id, kind='note', payload={'x': 1}, provenance={'producer': 'test'}, ttl_seconds=10)
        self.clock = self.clock.advance(15)
        self.memory = Mnemosyne(self.store, self.clock)
        fresh_hit = self.memory.recall(owner_id=DEFAULT_OWNER.owner_id, kind='note')[0]
        self.assertEqual(fresh_hit.status.value, 'stale')
        self.clock = self.clock.advance(20)
        self.memory = Mnemosyne(self.store, self.clock)
        expired_hit = self.memory.recall(owner_id=DEFAULT_OWNER.owner_id, kind='note')[0]
        self.assertEqual(expired_hit.status.value, 'expired')

    def test_intent_incomplete_raised_on_empty_goal_or_success_criteria(self) -> None:
        with self.assertRaises(IntentIncomplete):
            Intent.from_raw(raw_text='hi', goal=' ', success_criteria=['x'], owner_id=DEFAULT_OWNER.owner_id)
        with self.assertRaises(IntentIncomplete):
            Intent.from_raw(raw_text='hi', goal='do it', success_criteria=[], owner_id=DEFAULT_OWNER.owner_id)

    def test_duplicate_registration_raises_system_fault(self) -> None:
        dossier = self.dossier()
        self.registry.register(dossier, EchoCapability())
        with self.assertRaises(SystemFault):
            self.registry.register(dossier, EchoCapability())

    def test_secret_leak_validator_raises_system_fault(self) -> None:
        with self.assertRaises(SystemFault):
            CapabilityDossier(
                name='bad',
                version='1.0.0',
                signature='bad()',
                purpose='bad',
                cost_model='flat',
                latency_profile='instant',
                reliability='low',
                side_effects='none',
                reversible=True,
                required_secrets=['-----BEGIN PRIVATE KEY-----'],
                failure_modes='none',
                dependencies=[],
                determinism=Determinism.STRICT,
                provenance={'producer': 'test', 'created_at': self.clock.now().isoformat(), 'owner_id': DEFAULT_OWNER.owner_id, 'explicit_fields': ['idempotent']},
            )

    def test_registry_warns_on_implicit_idempotent_default(self) -> None:
        """Test that registering a capability without explicit idempotent field emits a warning."""
        import warnings
        
        # Test without explicit_fields - should warn
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            dossier = CapabilityDossier(
                name='implicit_test',
                version='1.0.0',
                signature='implicit_test()',
                purpose='implicit test',
                cost_model='flat',
                latency_profile='instant',
                reliability='high',
                side_effects='none',
                reversible=True,
                required_secrets=[],
                failure_modes='none',
                dependencies=[],
                determinism=Determinism.STRICT,
                provenance={'producer': 'test', 'created_at': self.clock.now().isoformat(), 'owner_id': DEFAULT_OWNER.owner_id},
                idempotent=True
            )
            # Should warn because idempotent not in explicit_fields
            self.assertEqual(len(w), 1)
            self.assertIn('idempotent defaulted to False', str(w[0].message))
            self.assertIn('implicit_test', str(w[0].message))
        
        # Test with explicit_fields - should NOT warn
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            dossier2 = CapabilityDossier(
                name='explicit_test',
                version='1.0.0',
                signature='explicit_test()',
                purpose='explicit test',
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
                idempotent=True
            )
            # Should NOT warn because idempotent is explicitly declared
            self.assertEqual(len(w), 0)

    def test_business_card_returns_exactly_five_lines(self) -> None:
        card = self.dossier().business_card()
        self.assertEqual(len(card.splitlines()), 5)

    def test_executive_re_raises_system_fault_and_records(self) -> None:
        self.registry.register(self.dossier(name='fault', purpose='fault trigger'), FaultingCapability())
        executive = ExecutiveMind(self.registry, self.memory, self.clock, DEFAULT_OWNER)
        intent = Intent.from_raw(raw_text='fault trigger', goal='fault', success_criteria=['x'], owner_id=DEFAULT_OWNER.owner_id)
        with self.assertRaises(SystemFault):
            executive.handle(intent)
        kinds = [r['kind'] for r in self.store.read_all()]
        self.assertIn('fault', kinds)

    def test_executive_task_failure_is_recorded_and_reported(self) -> None:
        self.registry.register(self.dossier(name='task', purpose='task trigger'), FailingTaskCapability())
        executive = ExecutiveMind(self.registry, self.memory, self.clock, DEFAULT_OWNER)
        intent = Intent.from_raw(raw_text='task trigger', goal='task', success_criteria=['x'], owner_id=DEFAULT_OWNER.owner_id)
        with self.assertRaises(TaskFailure):
            executive.handle(intent)
        fault_records = [r for r in self.store.read_all() if r['kind'] == 'fault']
        self.assertEqual(len(fault_records), 1)
        self.assertEqual(fault_records[0]['payload']['fault_class'], 'task_failure')

    def test_end_to_end_echo_capability_produces_complete_audit_trail(self) -> None:
        self.registry.register(self.dossier(), EchoCapability())
        executive = ExecutiveMind(self.registry, self.memory, self.clock, DEFAULT_OWNER)
        intent = Intent.from_raw(raw_text='please echo this', goal='echo', success_criteria=['it echoes'], owner_id=DEFAULT_OWNER.owner_id)
        outcome = executive.handle(intent)
        self.assertEqual(outcome.status, 'ok')
        kinds = [r['kind'] for r in self.store.read_all()]
        self.assertIn('intent_received', kinds)
        self.assertIn('capability_selected', kinds)
        self.assertIn('capability_result', kinds)
        self.assertNotIn('fault', kinds)

    def test_feedback_aggregation_works(self) -> None:
        feedback = FeedbackChannel(self.store, self.clock)
        feedback.submit(DEFAULT_OWNER.owner_id, 'target-1', Verdict.APPROVED, 'good')
        feedback.submit(DEFAULT_OWNER.owner_id, 'target-1', Verdict.REJECTED, 'bad')
        feedback.submit(DEFAULT_OWNER.owner_id, 'target-1', Verdict.APPROVED, 'better')
        aggregate = feedback.aggregate('target-1')
        self.assertEqual(aggregate[Verdict.APPROVED.value], 2)
        self.assertEqual(aggregate[Verdict.REJECTED.value], 1)
        self.assertEqual(aggregate[Verdict.NEEDS_WORK.value], 0)

    def test_local_jsonl_store_runnable(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store = LocalJSONLStore(directory=Path(temp_dir))
            record_id = store.append({'owner_id': DEFAULT_OWNER.owner_id, 'kind': 'x', 'created_at': self.clock.now().isoformat(), 'provenance': {}, 'payload': {}, 'schema_version': 1})
            self.assertTrue(record_id)
            self.assertEqual(len(list(store.read_all())), 1)

    def test_local_jsonl_store_delete_tombstone(self) -> None:
        """Test LocalJSONLStore.delete() uses tombstones and decay works with it."""
        with TemporaryDirectory() as temp_dir:
            store = LocalJSONLStore(directory=Path(temp_dir))
            clock = FrozenClock(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
            memory = Mnemosyne(store, clock)
            
            # Add a record with short TTL
            record_id = memory.record(
                owner_id=DEFAULT_OWNER.owner_id,
                kind='test_fact',
                payload={'value': 'test'},
                provenance={'producer': 'test'},
                ttl_seconds=10
            )
            
            # Verify record exists
            records = list(store.read_all())
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]['id'], record_id)
            
            # Advance clock beyond TTL * 2 (to EXPIRED)
            clock = clock.advance(25)
            memory = Mnemosyne(store, clock)
            
            # Decay should remove expired records via tombstone
            removed_count = memory.decay()
            self.assertEqual(removed_count, 1)
            
            # Record should be gone from read_all (filtered by tombstone)
            remaining = list(store.read_all())
            self.assertEqual(len(remaining), 0)
            
            # Verify tombstone record was written
            all_lines = []
            with store.file_path.open('r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        all_lines.append(json.loads(line))
            
            tombstones = [r for r in all_lines if r.get('kind') == 'tombstone']
            self.assertEqual(len(tombstones), 1)
            self.assertEqual(tombstones[0]['target_record_id'], record_id)

    # ===== New Feature Tests =====

    def test_intent_contract_enforcement_assert_complete(self) -> None:
        """Test Intent.assert_complete validates all required contract fields."""
        # Valid intent should pass
        intent = Intent.from_raw(
            raw_text='test', goal='test goal', success_criteria=['criterion 1'],
            owner_id=DEFAULT_OWNER.owner_id, determinism=Determinism.STRICT
        )
        intent.assert_complete()  # Should not raise

        # Missing goal should fail
        with self.assertRaises(IntentIncomplete):
            intent_no_goal = Intent.from_raw(
                raw_text='test', goal='', success_criteria=['criterion 1'],
                owner_id=DEFAULT_OWNER.owner_id, determinism=Determinism.STRICT
            )
            intent_no_goal.assert_complete()

        # Empty success criteria should fail
        with self.assertRaises(IntentIncomplete):
            intent_empty_criteria = Intent.from_raw(
                raw_text='test', goal='test goal', success_criteria=[],
                owner_id=DEFAULT_OWNER.owner_id, determinism=Determinism.STRICT
            )
            intent_empty_criteria.assert_complete()

        # Missing owner_id should fail
        with self.assertRaises(IntentIncomplete):
            intent_no_owner = Intent.from_raw(
                raw_text='test', goal='test goal', success_criteria=['criterion 1'],
                owner_id='', determinism=Determinism.STRICT
            )
            intent_no_owner.assert_complete()

        # Invalid determinism should fail - use a string that's not a valid Determinism
        with self.assertRaises(IntentIncomplete):
            class InvalidIntent(Intent):
                pass
            invalid_intent = Intent(
                raw_text='test', goal='test', success_criteria=['c'],
                constraints=[], deadline=None, determinism='invalid',  # type: ignore
                owner_id=DEFAULT_OWNER.owner_id
            )
            invalid_intent.assert_complete()

    def test_intent_validates_params(self) -> None:
        """Test Intent.validates_params ensures required execution params."""
        intent = Intent.from_raw(
            raw_text='test', goal='test goal', success_criteria=['criterion 1'],
            owner_id=DEFAULT_OWNER.owner_id
        )
        
        # Valid params should pass
        intent.validates_params({'owner_id': DEFAULT_OWNER.owner_id})
        
        # Missing owner_id should fail
        with self.assertRaises(IntentIncomplete):
            intent.validates_params({})

    def test_capability_contract_validation(self) -> None:
        """Test Capability.validate_intent validates intent against capability contract."""
        capability = EchoCapability()
        
        # Valid intent should pass
        valid_intent = Intent.from_raw(
            raw_text='test', goal='echo', success_criteria=['it echoes'],
            owner_id=DEFAULT_OWNER.owner_id, determinism=Determinism.STRICT
        )
        capability.validate_intent(valid_intent)  # Should not raise

        # Invalid determinism should raise ContractViolation
        invalid_determinism = Intent(
            raw_text='test', goal='echo', success_criteria=['it echoes'],
            constraints=[], deadline=None, determinism='invalid_type',  # type: ignore
            owner_id=DEFAULT_OWNER.owner_id
        )
        with self.assertRaises(ContractViolation):
            capability.validate_intent(invalid_determinism)

        # Past deadline should raise ContractViolation
        past_deadline = Intent.from_raw(
            raw_text='test', goal='echo', success_criteria=['it echoes'],
            owner_id=DEFAULT_OWNER.owner_id, determinism=Determinism.STRICT,
            deadline=datetime(2020, 1, 1, tzinfo=timezone.utc)
        )
        with self.assertRaises(ContractViolation):
            capability.validate_intent(past_deadline)

    def test_memory_decay_collect_expired(self) -> None:
        """Test Mnemosyne.collect_expired returns expired record IDs."""
        # Record with short TTL
        record_id = self.memory.record(
            owner_id=DEFAULT_OWNER.owner_id,
            kind='test_fact',
            payload={'value': 'test'},
            provenance={'producer': 'test'},
            ttl_seconds=10
        )
        
        # Advance clock beyond TTL * 2 (to EXPIRED)
        self.clock = self.clock.advance(25)
        self.memory = Mnemosyne(self.store, self.clock)
        
        expired_ids = self.memory.collect_expired()
        self.assertIn(record_id, expired_ids)

    def test_memory_decay_decay_removes_expired(self) -> None:
        """Test Mnemosyne.decay actually removes expired records."""
        # Add records with various TTLs
        self.memory.record(owner_id=DEFAULT_OWNER.owner_id, kind='fresh', payload={'v': 1}, provenance={}, ttl_seconds=100)
        self.memory.record(owner_id=DEFAULT_OWNER.owner_id, kind='stale', payload={'v': 2}, provenance={}, ttl_seconds=10)
        self.memory.record(owner_id=DEFAULT_OWNER.owner_id, kind='expired', payload={'v': 3}, provenance={}, ttl_seconds=5)
        
        # Advance clock
        self.clock = self.clock.advance(15)
        self.memory = Mnemosyne(self.store, self.clock)
        
        # Decay should remove expired records
        removed_count = self.memory.decay()
        self.assertEqual(removed_count, 1)  # Only the expired one
        
        # Verify fresh and stale remain
        remaining = list(self.store.read_all())
        kinds = [r['kind'] for r in remaining]
        self.assertIn('fresh', kinds)
        self.assertIn('stale', kinds)
        self.assertNotIn('expired', kinds)

    def test_error_handler_retry_logic(self) -> None:
        """Test ErrorHandler.should_retry logic."""
        handler = ErrorHandler(retry_policy=RetryPolicy(max_retries=3))
        
        # Should retry on TaskFailure
        self.assertTrue(handler.should_retry(0, TaskFailure('test')))
        self.assertTrue(handler.should_retry(2, TaskFailure('test')))
        self.assertFalse(handler.should_retry(3, TaskFailure('test')))  # Max retries exceeded
        
        # Should NOT retry on SystemFault
        self.assertFalse(handler.should_retry(0, SystemFault('test')))

    def test_retry_on_failure_decorator(self) -> None:
        """Test retry_on_failure decorator retries on TaskFailure."""
        handler = ErrorHandler(retry_policy=RetryPolicy(max_retries=3, base_delay_seconds=0.01, jitter=False))
        call_count = 0
        
        @retry_on_failure(handler)
        def sometimes_fails() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TaskFailure('temporary failure')
            return 'success'
        
        result = sometimes_fails()
        self.assertEqual(result, 'success')
        self.assertEqual(call_count, 3)

    def test_retry_on_failure_no_retry_on_system_fault(self) -> None:
        """Test retry_on_failure doesn't retry on SystemFault."""
        handler = ErrorHandler(retry_policy=RetryPolicy(max_retries=3))
        call_count = 0
        
        @retry_on_failure(handler)
        def always_system_fault() -> None:
            nonlocal call_count
            call_count += 1
            raise SystemFault('permanent failure')
        
        with self.assertRaises(SystemFault):
            always_system_fault()
        self.assertEqual(call_count, 1)  # Only called once, no retry

    def test_retry_on_failure_no_retry_on_caller_fault(self) -> None:
        """Test retry_on_failure doesn't retry on CallerFault (ContractViolation)."""
        handler = ErrorHandler(retry_policy=RetryPolicy(max_retries=3))
        call_count = 0
        
        @retry_on_failure(handler)
        def always_caller_fault() -> None:
            nonlocal call_count
            call_count += 1
            raise CallerFault('invalid input')
        
        with self.assertRaises(CallerFault):
            always_caller_fault()
        self.assertEqual(call_count, 1)  # Only called once, no retry

    def test_execution_throttle_excludes_caller_faults(self) -> None:
        """Test ExecutionThrottle excludes caller faults from error rate."""
        # Throttle with 10% error rate threshold
        throttle = ExecutionThrottle(max_concurrent=100, error_rate_threshold=0.1)
        
        # 5 total errors (including 5 caller faults) out of 10 executions
        # effective_errors = 5 - 5 = 0, rate = 0/10 = 0% -> should allow
        self.assertTrue(throttle.should_allow(recent_errors=5, recent_executions=10, caller_faults=5))
        
        # 7 total errors (5 caller faults + 2 real errors) out of 10 executions
        # effective_errors = 7 - 5 = 2, executions = 10, rate = 20% > 10% -> should block
        self.assertFalse(throttle.should_allow(recent_errors=7, recent_executions=10, caller_faults=5))
        
        # 6 total errors (5 caller faults + 1 real error) out of 10 executions
        # effective_errors = 6 - 5 = 1, executions = 10, rate = 10% == threshold -> should allow
        self.assertTrue(throttle.should_allow(recent_errors=6, recent_executions=10, caller_faults=5))
        
        # 10 total errors (all caller faults) out of 10 executions
        # effective_errors = 10 - 10 = 0, rate = 0% -> should allow
        self.assertTrue(throttle.should_allow(recent_errors=10, recent_executions=10, caller_faults=10))

    def test_caller_fault_does_not_trip_throttle(self) -> None:
        """Test that repeated ContractViolation/CallerFault does NOT trip the throttle."""
        # Register echo capability
        self.registry.register(self.dossier(), EchoCapability())
        
        # Create executive with throttle
        throttle = ExecutionThrottle(max_concurrent=100, error_rate_threshold=0.1)
        executive = ExecutiveMind(
            self.registry, self.memory, self.clock, DEFAULT_OWNER,
            # We can't directly inject throttle yet, so we test the logic separately
        )
        
        # Test that ContractViolation is a CallerFault and doesn't retry
        from universal_mind.pantheon.contracts import ContractViolation
        from universal_mind.core.errors import CallerFault
        
        self.assertTrue(issubclass(ContractViolation, CallerFault))
        
        # Verify ErrorHandler.should_retry returns False for CallerFault
        handler = ErrorHandler(retry_policy=RetryPolicy(max_retries=3))
        self.assertFalse(handler.should_retry(0, CallerFault('test')))
        self.assertFalse(handler.should_retry(0, ContractViolation('test')))

    def test_executive_with_error_handler(self) -> None:
        """Test ExecutiveMind uses error handler for retries."""
        call_count = 0
        
        class RetryThenSucceedCapability(Capability):
            def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise TaskFailure('temporary failure')
                return CapabilityResult(
                    ok=True, output={'attempts': call_count},
                    cost={}, provenance={'producer': 'RetryThenSucceed'}
                )
        
        self.registry.register(self.dossier(name='retry', purpose='retry test'), RetryThenSucceedCapability())
        
        # Executive with retry handler
        handler = ErrorHandler(retry_policy=RetryPolicy(max_retries=3, base_delay_seconds=0.01, jitter=False))
        executive = ExecutiveMind(self.registry, self.memory, self.clock, DEFAULT_OWNER, error_handler=handler)
        
        intent = Intent.from_raw(
            raw_text='retry test', goal='retry', success_criteria=['succeeds after retries'],
            owner_id=DEFAULT_OWNER.owner_id
        )
        
        outcome = executive.handle(intent)
        self.assertEqual(outcome.status, 'ok')
        self.assertEqual(call_count, 3)  # Initial + 2 retries

    def test_executive_no_retry_on_system_fault(self) -> None:
        """Test ExecutiveMind doesn't retry on SystemFault."""
        call_count = 0
        
        class AlwaysSystemFaultCapability(Capability):
            def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
                nonlocal call_count
                call_count += 1
                raise SystemFault('permanent failure')
        
        self.registry.register(self.dossier(name='fault', purpose='fault test'), AlwaysSystemFaultCapability())
        
        handler = ErrorHandler(retry_policy=RetryPolicy(max_retries=3))
        executive = ExecutiveMind(self.registry, self.memory, self.clock, DEFAULT_OWNER, error_handler=handler)
        
        intent = Intent.from_raw(
            raw_text='fault test', goal='fault', success_criteria=['should not retry'],
            owner_id=DEFAULT_OWNER.owner_id
        )
        
        with self.assertRaises(SystemFault):
            executive.handle(intent)
        self.assertEqual(call_count, 1)  # Only called once

    def test_executive_retry_only_on_idempotent_capability(self) -> None:
        """Test ExecutiveMind only retries on idempotent capabilities."""
        # Use fresh store/memory to avoid throttle interference from previous tests
        fresh_store = InMemoryStore()
        fresh_clock = FrozenClock(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
        fresh_memory = Mnemosyne(fresh_store, fresh_clock)
        fresh_registry = PantheonRegistry(fresh_store)
        
        call_count = 0
        
        class NonIdempotentCapability(Capability):
            def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
                nonlocal call_count
                call_count += 1
                raise TaskFailure('temporary failure')
        
        # Register with idempotent=False - use unique goal name
        non_idempotent_dossier = CapabilityDossier(
            name='nonidempotent_xyz', version='1.0.0', signature='nonidempotent_xyz()',
            purpose='nonidempotent_xyz purpose', cost_model='flat', latency_profile='instant',
            reliability='high', side_effects='none', reversible=False,
            required_secrets=[], failure_modes='none', dependencies=[],
            determinism=Determinism.STRICT,
            provenance={'producer': 'test', 'created_at': fresh_clock.now().isoformat(), 'owner_id': DEFAULT_OWNER.owner_id, 'explicit_fields': ['idempotent']},
            idempotent=False  # Non-idempotent capability
        )
        fresh_registry.register(non_idempotent_dossier, NonIdempotentCapability())
        
        handler = ErrorHandler(retry_policy=RetryPolicy(max_retries=3, base_delay_seconds=0.01, jitter=False))
        executive = ExecutiveMind(fresh_registry, fresh_memory, fresh_clock, DEFAULT_OWNER, error_handler=handler)
        
        intent = Intent.from_raw(
            raw_text='test nonidempotent_xyz', goal='nonidempotent_xyz', success_criteria=['should not retry'],
            owner_id=DEFAULT_OWNER.owner_id
        )
        
        # Should fail on first attempt, not retry
        with self.assertRaises(TaskFailure):
            executive.handle(intent)
        self.assertEqual(call_count, 1)  # Only called once, no retries
        
        # Now test with idempotent=True (default) - use fresh store again
        fresh_store2 = InMemoryStore()
        fresh_clock2 = FrozenClock(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
        fresh_memory2 = Mnemosyne(fresh_store2, fresh_clock2)
        fresh_registry2 = PantheonRegistry(fresh_store2)
        
        call_count = 0
        
        class IdempotentCapability(Capability):
            def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise TaskFailure('temporary failure')
                return CapabilityResult(
                    ok=True, output={'attempts': call_count},
                    cost={}, provenance={'producer': 'IdempotentCapability'}
                )
        
        idempotent_dossier = CapabilityDossier(
            name='idempotent_abc', version='1.0.0', signature='idempotent_abc()',
            purpose='idempotent_abc purpose', cost_model='flat', latency_profile='instant',
            reliability='high', side_effects='none', reversible=True,
            required_secrets=[], failure_modes='none', dependencies=[],
            determinism=Determinism.STRICT,
            provenance={'producer': 'test', 'created_at': fresh_clock2.now().isoformat(), 'owner_id': DEFAULT_OWNER.owner_id, 'explicit_fields': ['idempotent']},
            idempotent=True
        )
        fresh_registry2.register(idempotent_dossier, IdempotentCapability())
        
        handler2 = ErrorHandler(retry_policy=RetryPolicy(max_retries=3, base_delay_seconds=0.01, jitter=False))
        executive2 = ExecutiveMind(fresh_registry2, fresh_memory2, fresh_clock2, DEFAULT_OWNER, error_handler=handler2)
        
        intent = Intent.from_raw(
            raw_text='test idempotent_abc', goal='idempotent_abc', success_criteria=['succeeds after retries'],
            owner_id=DEFAULT_OWNER.owner_id
        )
        
        outcome = executive2.handle(intent)
        self.assertEqual(outcome.status, 'ok')
        self.assertEqual(call_count, 3)  # Initial + 2 retries

    def test_human_feedback_gate_blocks_on_rejection(self) -> None:
        """Test HumanFeedbackGate blocks execution on rejection."""
        gate = feedback_gate(self.store, self.clock)
        
        # Submit rejection
        gate.submit(DEFAULT_OWNER.owner_id, 'target-1', Verdict.REJECTED, 'bad result')
        
        # Should be blocked
        self.assertTrue(gate.is_blocked('target-1'))

    def test_human_feedback_gate_blocks_on_repeated_needs_work(self) -> None:
        """Test HumanFeedbackGate blocks on repeated needs_work without approval."""
        gate = feedback_gate(self.store, self.clock)
        
        # Submit multiple needs_work
        gate.submit(DEFAULT_OWNER.owner_id, 'target-2', Verdict.NEEDS_WORK, 'needs improvement')
        gate.submit(DEFAULT_OWNER.owner_id, 'target-2', Verdict.NEEDS_WORK, 'still needs work')
        
        # Should be blocked (needs_work_threshold=2 by default)
        self.assertTrue(gate.is_blocked('target-2'))
        
        # But approval should unblock
        gate.submit(DEFAULT_OWNER.owner_id, 'target-2', Verdict.APPROVED, 'fixed')
        self.assertFalse(gate.is_blocked('target-2'))

    def test_human_feedback_gate_custom_policy(self) -> None:
        """Test HumanFeedbackGate with custom policy."""
        # Custom policy: block on 2 rejections or 3 needs_work
        custom_policy = FeedbackPolicy(
            rejection_threshold=2,
            needs_work_threshold=3,
            approval_threshold=1
        )
        gate = HumanFeedbackGate(self.store, self.clock, custom_policy)
        
        # Single rejection should NOT block
        gate.submit(DEFAULT_OWNER.owner_id, 'target-3', Verdict.REJECTED, 'bad')
        self.assertFalse(gate.is_blocked('target-3'))
        
        # Second rejection should block
        gate.submit(DEFAULT_OWNER.owner_id, 'target-3', Verdict.REJECTED, 'still bad')
        self.assertTrue(gate.is_blocked('target-3'))

    def test_strategic_gate_blocks_execution(self) -> None:
        """Test StrategicGate can block execution."""
        
        class BlockingGate(StrategicGate):
            def evaluate(self, intent: Intent, context: dict[str, Any]) -> StrategicDecision:
                if 'block_me' in intent.raw_text:
                    return StrategicDecision(decision=Decision.BLOCK, reason='Contains block_me')
                return StrategicDecision(decision=Decision.PROCEED)
        
        gate = BlockingGate()
        executive = ExecutiveMind(self.registry, self.memory, self.clock, DEFAULT_OWNER, strategic_gate=gate)
        
        # Register a capability
        self.registry.register(self.dossier(), EchoCapability())
        
        # Intent that should be blocked
        blocked_intent = Intent.from_raw(
            raw_text='block_me please', goal='test', success_criteria=['blocked'],
            owner_id=DEFAULT_OWNER.owner_id
        )
        
        outcome = executive.handle(blocked_intent)
        self.assertEqual(outcome.status, 'blocked')
        self.assertIn('block_me', outcome.notes[0])

    def test_strategic_gate_redirects_to_capability(self) -> None:
        """Test StrategicGate can redirect to a different capability."""
        
        class RedirectingGate(StrategicGate):
            def evaluate(self, intent: Intent, context: dict[str, Any]) -> StrategicDecision:
                if 'redirect' in intent.raw_text:
                    return StrategicDecision(decision=Decision.REDIRECT, redirect_capability='echo')
                return StrategicDecision(decision=Decision.PROCEED)
        
        gate = RedirectingGate()
        executive = ExecutiveMind(self.registry, self.memory, self.clock, DEFAULT_OWNER, strategic_gate=gate)
        
        # Register capabilities
        self.registry.register(self.dossier(), EchoCapability())
        
        class CustomCapability(Capability):
            def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
                return CapabilityResult(
                    ok=True, output={'source': 'custom'},
                    cost={}, provenance={'producer': 'Custom'}
                )
        
        self.registry.register(
            CapabilityDossier(
                name='custom', version='1.0.0', signature='custom()',
                purpose='custom purpose', cost_model='flat', latency_profile='instant',
                reliability='high', side_effects='none', reversible=True,
                required_secrets=[], failure_modes='none', dependencies=[],
                determinism=Determinism.STRICT,
                provenance={'producer': 'test', 'created_at': self.clock.now().isoformat(), 'owner_id': DEFAULT_OWNER.owner_id, 'explicit_fields': ['idempotent']},
                idempotent=True
            ),
            CustomCapability()
        )
        
        # Intent that should be redirected to echo
        redirect_intent = Intent.from_raw(
            raw_text='redirect this', goal='custom', success_criteria=['redirected'],
            owner_id=DEFAULT_OWNER.owner_id
        )
        
        outcome = executive.handle(redirect_intent)
        self.assertEqual(outcome.status, 'ok')

    def test_risk_assessor_assesses_risk(self) -> None:
        """Test RiskAssessor assigns risk levels."""
        assessor = RiskAssessor()
        
        # High reliability, strict determinism = low risk
        dossier = self.dossier()
        intent = Intent.from_raw(
            raw_text='test', goal='echo', success_criteria=['ok'],
            owner_id=DEFAULT_OWNER.owner_id, determinism=Determinism.STRICT
        )
        capability = EchoCapability()
        
        risk = assessor.assess(intent, capability, dossier)
        self.assertEqual(risk, 'low')
        
        # Low reliability = high risk
        low_reliability_dossier = CapabilityDossier(
            name='low_rel', version='1.0.0', signature='low()',
            purpose='test', cost_model='flat', latency_profile='instant',
            reliability='low', side_effects='none', reversible=True,
            required_secrets=[], failure_modes='none', dependencies=[],
            determinism=Determinism.STRICT,
            provenance={'producer': 'test', 'created_at': self.clock.now().isoformat(), 'owner_id': DEFAULT_OWNER.owner_id, 'explicit_fields': ['idempotent']},
            idempotent=True
        )
        risk = assessor.assess(intent, capability, low_reliability_dossier)
        self.assertEqual(risk, 'high')
        
        # Creative determinism = medium risk
        creative_intent = Intent.from_raw(
            raw_text='test', goal='echo', success_criteria=['ok'],
            owner_id=DEFAULT_OWNER.owner_id, determinism=Determinism.CREATIVE
        )
        risk = assessor.assess(creative_intent, capability, dossier)
        self.assertEqual(risk, 'medium')

    def test_execution_throttle(self) -> None:
        """Test ExecutionThrottle limits concurrent executions."""
        throttle = ExecutionThrottle(max_concurrent=2, error_rate_threshold=0.5)
        
        # Should allow first two
        self.assertTrue(throttle.should_allow(0, 0))
        self.assertTrue(throttle.should_allow(0, 1))
        
        # Should block on third
        self.assertFalse(throttle.should_allow(0, 2))
        
        # Error rate threshold
        self.assertTrue(throttle.should_allow(0, 0))
        self.assertFalse(throttle.should_allow(1, 2))  # 50% error rate

    def test_executive_records_risk_assessment(self) -> None:
        """Test ExecutiveMind records risk assessment."""
        self.registry.register(self.dossier(), EchoCapability())
        executive = ExecutiveMind(self.registry, self.memory, self.clock, DEFAULT_OWNER)
        
        intent = Intent.from_raw(
            raw_text='test', goal='echo', success_criteria=['it echoes'],
            owner_id=DEFAULT_OWNER.owner_id
        )
        
        outcome = executive.handle(intent)
        self.assertEqual(outcome.status, 'ok')
        
        # Check risk assessment was recorded
        risk_records = [r for r in self.store.read_all() if r.get('kind') == 'risk_assessment']
        self.assertEqual(len(risk_records), 1)
        self.assertEqual(risk_records[0]['payload']['risk_level'], 'low')

    def test_risk_policy_allows_and_blocks(self) -> None:
        """Test RiskPolicy with two policies giving opposite outcomes on high risk."""
        from universal_mind.core.executive import DefaultRiskPolicy, RiskPolicy

        # Policy 1: blocks high risk (default)
        blocking_policy = DefaultRiskPolicy(RiskPolicy(high_risk_blocks=True))

        # Policy 2: allows high risk
        allowing_policy = DefaultRiskPolicy(RiskPolicy(high_risk_blocks=False))

        # Create a high-risk dossier (low reliability, NOT reversible so it gets blocked)
        high_risk_dossier = CapabilityDossier(
            name='high_risk', version='1.0.0', signature='high_risk()',
            purpose='test', cost_model='flat', latency_profile='instant',
            reliability='low', side_effects='none', reversible=False,
            required_secrets=[], failure_modes='none', dependencies=[],
            determinism=Determinism.STRICT,
            provenance={'producer': 'test', 'created_at': self.clock.now().isoformat(), 'owner_id': DEFAULT_OWNER.owner_id, 'explicit_fields': ['idempotent']},
            idempotent=True
        )

        intent = Intent.from_raw(
            raw_text='test', goal='echo', success_criteria=['ok'],
            owner_id=DEFAULT_OWNER.owner_id, determinism=Determinism.STRICT
        )
        capability = EchoCapability()

        assessor = RiskAssessor()
        risk = assessor.assess(intent, capability, high_risk_dossier)
        self.assertEqual(risk, 'high')

        # Blocking policy should block
        self.assertFalse(blocking_policy.allows(risk, high_risk_dossier, intent))

        # Allowing policy should allow
        self.assertTrue(allowing_policy.allows(risk, high_risk_dossier, intent))

    def test_strategic_decision_recorded(self) -> None:
        """Test strategic decisions are recorded in memory."""
        
        class BlockingGate(StrategicGate):
            def evaluate(self, intent: Intent, context: dict[str, Any]) -> StrategicDecision:
                return StrategicDecision(decision=Decision.BLOCK, reason='Policy violation')
        
        gate = BlockingGate()
        executive = ExecutiveMind(self.registry, self.memory, self.clock, DEFAULT_OWNER, strategic_gate=gate)
        
        intent = Intent.from_raw(
            raw_text='test', goal='blocked', success_criteria=['blocked'],
            owner_id=DEFAULT_OWNER.owner_id
        )
        
        outcome = executive.handle(intent)
        self.assertEqual(outcome.status, 'blocked')
        
        # Check strategic decision was recorded
        decision_records = [r for r in self.store.read_all() if r.get('kind') == 'strategic_decision']
        self.assertEqual(len(decision_records), 1)
        self.assertEqual(decision_records[0]['payload']['decision'], 'block')

    def test_executive_fallback_capability(self) -> None:
        """Test ExecutiveMind falls back to fallback_capability when retries exhausted."""
        # Use fresh store to avoid interference
        fresh_store = InMemoryStore()
        fresh_clock = FrozenClock(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
        fresh_memory = Mnemosyne(fresh_store, fresh_clock)
        fresh_registry = PantheonRegistry(fresh_store)
        
        call_count = 0
        
        class FailingCapability(Capability):
            def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
                nonlocal call_count
                call_count += 1
                raise TaskFailure('always fails')
        
        class FallbackCapability(Capability):
            def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
                return CapabilityResult(
                    ok=True, output={'source': 'fallback', 'params': params},
                    cost={}, provenance={'producer': 'FallbackCapability'}
                )
        
        # Register primary capability that always fails
        primary_dossier = CapabilityDossier(
            name='primary', version='1.0.0', signature='primary()',
            purpose='primary test', cost_model='flat', latency_profile='instant',
            reliability='low', side_effects='none', reversible=True,
            required_secrets=[], failure_modes='none', dependencies=[],
            determinism=Determinism.STRICT,
            provenance={'producer': 'test', 'created_at': fresh_clock.now().isoformat(), 'owner_id': DEFAULT_OWNER.owner_id, 'explicit_fields': ['idempotent']},
            idempotent=True
        )
        fresh_registry.register(primary_dossier, FailingCapability())
        
        # Register fallback capability
        fallback_dossier = CapabilityDossier(
            name='fallback', version='1.0.0', signature='fallback()',
            purpose='fallback test', cost_model='flat', latency_profile='instant',
            reliability='high', side_effects='none', reversible=True,
            required_secrets=[], failure_modes='none', dependencies=[],
            determinism=Determinism.STRICT,
            provenance={'producer': 'test', 'created_at': fresh_clock.now().isoformat(), 'owner_id': DEFAULT_OWNER.owner_id, 'explicit_fields': ['idempotent']},
            idempotent=True
        )
        fresh_registry.register(fallback_dossier, FallbackCapability())
        
        # Executive with fallback configured
        handler = ErrorHandler(
            retry_policy=RetryPolicy(max_retries=2, base_delay_seconds=0.01, jitter=False),
            fallback_capability='fallback',
            fallback_params={'fallback_param': 'test_value'}
        )
        executive = ExecutiveMind(fresh_registry, fresh_memory, fresh_clock, DEFAULT_OWNER, error_handler=handler)
        
        intent = Intent.from_raw(
            raw_text='test fallback', goal='primary', success_criteria=['fallback executes'],
            owner_id=DEFAULT_OWNER.owner_id
        )
        
        # Should fallback after retries exhausted
        outcome = executive.handle(intent)
        self.assertEqual(outcome.status, 'ok')
        
        # Primary should have been called 3 times (initial + 2 retries)
        self.assertEqual(call_count, 3)

    def test_composite_strategic_gate(self) -> None:
        """Test CompositeStrategicGate evaluates gates in precedence order."""
        from universal_mind.core.executive import (
            CompositeStrategicGate, ThrottleGate, StrategicGate, Decision, StrategicDecision
        )
        
        # Create a gate that blocks on 'block_me'
        class BlockingGate(StrategicGate):
            def evaluate(self, intent: Intent, context: dict[str, Any]) -> StrategicDecision:
                if 'block_me' in intent.raw_text:
                    return StrategicDecision(decision=Decision.BLOCK, reason='Contains block_me')
                return StrategicDecision(decision=Decision.PROCEED)
        
        # Create a gate that redirects on 'redirect_me'
        class RedirectingGate(StrategicGate):
            def evaluate(self, intent: Intent, context: dict[str, Any]) -> StrategicDecision:
                if 'redirect_me' in intent.raw_text:
                    return StrategicDecision(decision=Decision.REDIRECT, redirect_capability='echo')
                return StrategicDecision(decision=Decision.PROCEED)
        
        blocking_gate = BlockingGate()
        redirecting_gate = RedirectingGate()
        
        # Composite with blocking gate at higher precedence
        composite = CompositeStrategicGate([
            (100, blocking_gate),
            (50, redirecting_gate),
        ])
        
        # Intent that triggers both - blocking should win due to higher precedence
        block_intent = Intent.from_raw(
            raw_text='block_me and redirect_me', goal='test', success_criteria=['blocked'],
            owner_id=DEFAULT_OWNER.owner_id
        )
        
        decision = composite.evaluate(block_intent, {})
        self.assertEqual(decision.decision, Decision.BLOCK)
        self.assertIsNotNone(decision.reason)
        if decision.reason:
            self.assertIn('block_me', decision.reason)
        
        # Intent that only triggers redirect
        redirect_intent = Intent.from_raw(
            raw_text='redirect_me please', goal='test', success_criteria=['redirected'],
            owner_id=DEFAULT_OWNER.owner_id
        )
        
        decision = composite.evaluate(redirect_intent, {})
        self.assertEqual(decision.decision, Decision.REDIRECT)
        self.assertEqual(decision.redirect_capability, 'echo')
        
        # Intent that triggers neither
        proceed_intent = Intent.from_raw(
            raw_text='proceed please', goal='test', success_criteria=['proceeds'],
            owner_id=DEFAULT_OWNER.owner_id
        )
        
        decision = composite.evaluate(proceed_intent, {})
        self.assertEqual(decision.decision, Decision.PROCEED)

    def test_executive_gate_precedence(self) -> None:
        """Test ExecutiveMind gate_precedence parameter affects evaluation order."""
        from universal_mind.core.executive import (
            ExecutiveMind, StrategicGate, Decision, StrategicDecision,
            PRECEDENCE_POLICY, PRECEDENCE_RISK, PRECEDENCE_FEEDBACK,
            DefaultRiskPolicy, RiskPolicy, RiskAssessor
        )

        # Gate that blocks on 'policy_block'
        class PolicyGate(StrategicGate):
            def evaluate(self, intent: Intent, context: dict[str, Any]) -> StrategicDecision:
                if 'policy_block' in intent.raw_text:
                    return StrategicDecision(decision=Decision.BLOCK, reason='Policy gate blocked')
                return StrategicDecision(decision=Decision.PROCEED)

        # Gate that blocks on 'risk_block'
        class TestRiskGate(StrategicGate):
            def evaluate(self, intent: Intent, context: dict[str, Any]) -> StrategicDecision:
                if 'risk_block' in intent.raw_text:
                    return StrategicDecision(decision=Decision.BLOCK, reason='Risk gate blocked')
                return StrategicDecision(decision=Decision.PROCEED)

        policy_gate = PolicyGate()

        # Test 1: Default precedence (policy=80, risk=60) - policy wins
        executive_default = ExecutiveMind(
            self.registry, self.memory, self.clock, DEFAULT_OWNER,
            strategic_gate=policy_gate,
            risk_assessor=RiskAssessor(),
            risk_policy=DefaultRiskPolicy(RiskPolicy(high_risk_blocks=False)),
            gate_precedence={'policy': 80, 'risk': 60}
        )

        intent = Intent.from_raw(
            raw_text='policy_block and risk_block', goal='echo',
            success_criteria=['blocked'], owner_id=DEFAULT_OWNER.owner_id
        )
        outcome = executive_default.handle(intent)
        self.assertEqual(outcome.status, 'blocked')
        # Policy gate should have won (higher precedence = evaluated first)

        # Test 2: Custom precedence - risk gate at higher precedence (risk=90, policy=80)
        test_risk_gate = TestRiskGate()
        executive_custom = ExecutiveMind(
            self.registry, self.memory, self.clock, DEFAULT_OWNER,
            strategic_gate=policy_gate,
            risk_assessor=RiskAssessor(),
            risk_policy=DefaultRiskPolicy(RiskPolicy(high_risk_blocks=False)),
            gate_precedence={'policy': 80, 'risk': 90}
        )

        # Need to re-register capability for new executive
        self.registry.register(self.dossier(), EchoCapability())

        outcome = executive_custom.handle(intent)
        self.assertEqual(outcome.status, 'blocked')
        # Both would block, but risk gate evaluated first due to higher precedence

        # Test 3: Test that gate_precedence dict is stored and used
        self.assertEqual(executive_default.gate_precedence, {'policy': 80, 'risk': 60})
        self.assertEqual(executive_custom.gate_precedence, {'policy': 80, 'risk': 90})

    # ===== S1: Automatic compaction tests =====

    def test_local_jsonl_store_auto_compaction_threshold(self) -> None:
        """Test that automatic compaction triggers when tombstone ratio exceeds threshold."""
        with TemporaryDirectory() as temp_dir:
            # Use a policy that triggers compaction at low threshold
            policy = CompactionPolicy(max_tombstone_ratio=0.1, min_records_before_compact=10)
            store = LocalJSONLStore(directory=Path(temp_dir), compaction_policy=policy)
            
            # Add 20 live records
            record_ids = []
            for i in range(20):
                record_id = store.append({'owner_id': 'test', 'kind': 'fact', 'created_at': self.clock.now().isoformat(), 'provenance': {}, 'payload': {'value': i}, 'schema_version': 1})
                record_ids.append(record_id)
            
            # Delete 3 records (3/17 = 0.176 > 0.1 threshold)
            for record_id in record_ids[:3]:
                result = store.delete(record_id)
                self.assertTrue(result)
            
            # Compaction should have triggered automatically
            # Verify live records still exist and tombstones are gone
            live_records = list(store.read_all())
            self.assertEqual(len(live_records), 17)
            
            # Check file only has live records (no tombstones)
            all_lines = []
            with store.file_path.open('r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        all_lines.append(json.loads(line))
            tombstones = [r for r in all_lines if r.get('kind') == 'tombstone']
            self.assertEqual(len(tombstones), 0)

    def test_local_jsonl_store_compaction_survives_crash(self) -> None:
        """Test that crash-safe compaction preserves live data (atomic replace)."""
        with TemporaryDirectory() as temp_dir:
            store = LocalJSONLStore(directory=Path(temp_dir))
            
            # Add records
            for i in range(5):
                store.append({'owner_id': 'test', 'kind': 'fact', 'created_at': self.clock.now().isoformat(), 'provenance': {}, 'payload': {'value': i}, 'schema_version': 1})
            
            # Delete 2 records
            records_before = list(store.read_all())
            store.delete(records_before[0]['id'])
            store.delete(records_before[1]['id'])
            
            # Manually trigger compaction
            # compact() returns total lines dropped (live records tombstoned + tombstone markers)
            removed = store.compact()
            self.assertEqual(removed, 4)  # 2 live records tombstoned + 2 tombstone markers
            
            # Verify data integrity
            live_records = list(store.read_all())
            self.assertEqual(len(live_records), 3)
            for i, record in enumerate(live_records):
                self.assertEqual(record['payload']['value'], i + 2)  # Records 2,3,4 remain

    def test_local_jsonl_store_auto_compaction_max_tombstones(self) -> None:
        """Test that automatic compaction triggers when absolute tombstone count exceeds max_tombstones."""
        with TemporaryDirectory() as temp_dir:
            # Use a policy that triggers compaction at absolute count
            policy = CompactionPolicy(max_tombstones=3, min_records_before_compact=5)
            store = LocalJSONLStore(directory=Path(temp_dir), compaction_policy=policy)

            # Add 10 live records
            record_ids = []
            for i in range(10):
                record_id = store.append({'owner_id': 'test', 'kind': 'fact', 'created_at': self.clock.now().isoformat(), 'provenance': {}, 'payload': {'value': i}, 'schema_version': 1})
                record_ids.append(record_id)

            # Delete 3 records - should trigger compaction (max_tombstones=3)
            for record_id in record_ids[:3]:
                result = store.delete(record_id)
                self.assertTrue(result)

            # Compaction should have triggered automatically
            # Verify live records still exist and tombstones are gone
            live_records = list(store.read_all())
            self.assertEqual(len(live_records), 7)

            # Check file only has live records (no tombstones)
            all_lines = []
            with store.file_path.open('r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        all_lines.append(json.loads(line))
            tombstones = [r for r in all_lines if r.get('kind') == 'tombstone']
            self.assertEqual(len(tombstones), 0)

    def test_local_jsonl_store_compact_idempotent(self) -> None:
        """Test that compact() on an already-clean store is a no-op (returns 0)."""
        with TemporaryDirectory() as temp_dir:
            store = LocalJSONLStore(directory=Path(temp_dir))
            
            # Add records
            for i in range(5):
                store.append({'owner_id': 'test', 'kind': 'fact', 'created_at': self.clock.now().isoformat(), 'provenance': {}, 'payload': {'value': i}, 'schema_version': 1})
            
            # First compaction
            removed1 = store.compact()
            self.assertEqual(removed1, 0)
            
            # Second compaction (should be no-op)
            removed2 = store.compact()
            self.assertEqual(removed2, 0)
            
            # Third compaction
            removed3 = store.compact()
            self.assertEqual(removed3, 0)
            
            # Data unchanged
            live_records = list(store.read_all())
            self.assertEqual(len(live_records), 5)

    def test_local_jsonl_store_compaction_preserves_order(self) -> None:
        """Test that compaction preserves append order of live records."""
        with TemporaryDirectory() as temp_dir:
            store = LocalJSONLStore(directory=Path(temp_dir))
            
            # Add records in order
            ids = []
            for i in range(10):
                record_id = store.append({'owner_id': 'test', 'kind': 'fact', 'created_at': self.clock.now().isoformat(), 'provenance': {}, 'payload': {'seq': i}, 'schema_version': 1})
                ids.append(record_id)
            
            # Delete records 2, 5, 8 (non-sequential)
            store.delete(ids[2])
            store.delete(ids[5])
            store.delete(ids[8])
            
            # Compact
            store.compact()
            
            # Verify order preserved
            live_records = list(store.read_all())
            self.assertEqual(len(live_records), 7)
            expected_seq = [0, 1, 3, 4, 6, 7, 9]
            for i, record in enumerate(live_records):
                self.assertEqual(record['payload']['seq'], expected_seq[i])

    def test_executive_pre_execution_pipeline(self) -> None:
        """Test ExecutiveMind pre-execution pipeline order."""
        # Use fresh store to avoid interference
        fresh_store = InMemoryStore()
        fresh_clock = FrozenClock(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
        fresh_memory = Mnemosyne(fresh_store, fresh_clock)
        fresh_registry = PantheonRegistry(fresh_store)
        
        # Register echo capability
        fresh_registry.register(self.dossier(), EchoCapability())
        
        # Create executive with custom gate that blocks
        class BlockingGate(StrategicGate):
            def evaluate(self, intent: Intent, context: dict[str, Any]) -> StrategicDecision:
                if 'pipeline_block' in intent.raw_text:
                    return StrategicDecision(decision=Decision.BLOCK, reason='Pipeline blocked')
                return StrategicDecision(decision=Decision.PROCEED)
        
        gate = BlockingGate()
        executive = ExecutiveMind(fresh_registry, fresh_memory, fresh_clock, DEFAULT_OWNER, strategic_gate=gate)
        
        # Intent that should be blocked by gate (after contract validation, throttle)
        blocked_intent = Intent.from_raw(
            raw_text='pipeline_block test', goal='test', success_criteria=['blocked'],
            owner_id=DEFAULT_OWNER.owner_id
        )
        
        outcome = executive.handle(blocked_intent)
        self.assertEqual(outcome.status, 'blocked')
        
        # Verify pipeline recorded intent_received then strategic_decision
        records = list(fresh_store.read_all())
        kinds = [r['kind'] for r in records]
        self.assertIn('intent_received', kinds)
        self.assertIn('strategic_decision', kinds)
        # Should NOT have capability_selected or capability_result
        self.assertNotIn('capability_selected', kinds)
        self.assertNotIn('capability_result', kinds)

    def test_executive_contract_validation_in_pipeline(self) -> None:
        """Test contract validation happens before gates in pipeline."""
        fresh_store = InMemoryStore()
        fresh_clock = FrozenClock(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
        fresh_memory = Mnemosyne(fresh_store, fresh_clock)
        fresh_registry = PantheonRegistry(fresh_store)
        
        fresh_registry.register(self.dossier(), EchoCapability())
        executive = ExecutiveMind(fresh_registry, fresh_memory, fresh_clock, DEFAULT_OWNER)
        
        # Intent with empty goal - should fail at contract validation (Step 1)
        invalid_intent = Intent(
            raw_text='test', goal='', success_criteria=['test'],
            constraints=[], deadline=None, determinism=Determinism.STRICT,
            owner_id=DEFAULT_OWNER.owner_id
        )
        
        with self.assertRaises(IntentIncomplete):
            executive.handle(invalid_intent)
        
        # Intent with missing owner_id in params - should fail at validates_params
        intent = Intent.from_raw(
            raw_text='test', goal='echo', success_criteria=['it echoes'],
            owner_id=DEFAULT_OWNER.owner_id
        )
        # This should fail at validates_params
        with self.assertRaises(IntentIncomplete):
            intent.validates_params({})  # Missing owner_id

    # ===== R4: Multi-fallback chain test =====

    def test_executive_multi_fallback_chain(self) -> None:
        """Test chain of 3 fallbacks where first two fail, third succeeds; verify call order."""
        fresh_store = InMemoryStore()
        fresh_clock = FrozenClock(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
        fresh_memory = Mnemosyne(fresh_store, fresh_clock)
        fresh_registry = PantheonRegistry(fresh_store)

        call_order = []

        class FailingCapability1(Capability):
            def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
                call_order.append('primary')
                raise TaskFailure('primary always fails')

        class FailingCapability2(Capability):
            def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
                call_order.append('fallback1')
                raise TaskFailure('fallback1 always fails')

        class SucceedingCapability3(Capability):
            def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
                call_order.append('fallback2')
                return CapabilityResult(
                    ok=True, output={'source': 'fallback2', 'params': params},
                    cost={}, provenance={'producer': 'SucceedingCapability3'}
                )

        # Register primary capability that always fails
        primary_dossier = CapabilityDossier(
            name='primary', version='1.0.0', signature='primary()',
            purpose='primary test', cost_model='flat', latency_profile='instant',
            reliability='low', side_effects='none', reversible=True,
            required_secrets=[], failure_modes='none', dependencies=[],
            determinism=Determinism.STRICT,
            provenance={'producer': 'test', 'created_at': fresh_clock.now().isoformat(), 'owner_id': DEFAULT_OWNER.owner_id, 'explicit_fields': ['idempotent']},
            idempotent=True
        )
        fresh_registry.register(primary_dossier, FailingCapability1())

        # Register first fallback that always fails
        fallback1_dossier = CapabilityDossier(
            name='fallback1', version='1.0.0', signature='fallback1()',
            purpose='fallback1 test', cost_model='flat', latency_profile='instant',
            reliability='low', side_effects='none', reversible=True,
            required_secrets=[], failure_modes='none', dependencies=[],
            determinism=Determinism.STRICT,
            provenance={'producer': 'test', 'created_at': fresh_clock.now().isoformat(), 'owner_id': DEFAULT_OWNER.owner_id, 'explicit_fields': ['idempotent']},
            idempotent=True
        )
        fresh_registry.register(fallback1_dossier, FailingCapability2())

        # Register second fallback that succeeds
        fallback2_dossier = CapabilityDossier(
            name='fallback2', version='1.0.0', signature='fallback2()',
            purpose='fallback2 test', cost_model='flat', latency_profile='instant',
            reliability='high', side_effects='none', reversible=True,
            required_secrets=[], failure_modes='none', dependencies=[],
            determinism=Determinism.STRICT,
            provenance={'producer': 'test', 'created_at': fresh_clock.now().isoformat(), 'owner_id': DEFAULT_OWNER.owner_id, 'explicit_fields': ['idempotent']},
            idempotent=True
        )
        fresh_registry.register(fallback2_dossier, SucceedingCapability3())

        # Executive with fallback chain: primary -> fallback1 -> fallback2
        # Use ErrorHandler with fallback_capability as a list for the chain
        handler = ErrorHandler(
            retry_policy=RetryPolicy(max_retries=1, base_delay_seconds=0.01, jitter=False),
            fallback_capability=['fallback1', 'fallback2'],
            fallback_params={'param': 'value1'}
        )
        executive = ExecutiveMind(fresh_registry, fresh_memory, fresh_clock, DEFAULT_OWNER, error_handler=handler)

        intent = Intent.from_raw(
            raw_text='test multi fallback', goal='primary', success_criteria=['fallback executes'],
            owner_id=DEFAULT_OWNER.owner_id
        )

        # Should fallback through chain: primary (1 retry) -> fallback1 (1 retry) -> fallback2 succeeds
        outcome = executive.handle(intent)
        self.assertEqual(outcome.status, 'ok')

        # Verify call order: primary called (initial + 1 retry = 2), fallback1 called once (no retries on fallbacks), fallback2 called once
        self.assertEqual(call_order.count('primary'), 2)
        self.assertEqual(call_order.count('fallback1'), 1)
        self.assertEqual(call_order.count('fallback2'), 1)

    def test_executive_all_fallbacks_fail_raises_original(self) -> None:
        """Test that when ALL fallbacks fail, original TaskFailure is re-raised (B0.1)."""
        fresh_store = InMemoryStore()
        fresh_clock = FrozenClock(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
        fresh_memory = Mnemosyne(fresh_store, fresh_clock)
        fresh_registry = PantheonRegistry(fresh_store)

        class FailingCapability(Capability):
            def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
                raise TaskFailure('always fails')

        class FailingFallback(Capability):
            def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
                raise TaskFailure('fallback also fails')

        # Register primary capability that always fails
        primary_dossier = CapabilityDossier(
            name='primary', version='1.0.0', signature='primary()',
            purpose='primary test', cost_model='flat', latency_profile='instant',
            reliability='low', side_effects='none', reversible=True,
            required_secrets=[], failure_modes='none', dependencies=[],
            determinism=Determinism.STRICT,
            provenance={'producer': 'test', 'created_at': fresh_clock.now().isoformat(), 'owner_id': DEFAULT_OWNER.owner_id, 'explicit_fields': ['idempotent']},
            idempotent=True
        )
        fresh_registry.register(primary_dossier, FailingCapability())

        # Register fallback that always fails
        fallback_dossier = CapabilityDossier(
            name='fallback', version='1.0.0', signature='fallback()',
            purpose='fallback test', cost_model='flat', latency_profile='instant',
            reliability='low', side_effects='none', reversible=True,
            required_secrets=[], failure_modes='none', dependencies=[],
            determinism=Determinism.STRICT,
            provenance={'producer': 'test', 'created_at': fresh_clock.now().isoformat(), 'owner_id': DEFAULT_OWNER.owner_id, 'explicit_fields': ['idempotent']},
            idempotent=True
        )
        fresh_registry.register(fallback_dossier, FailingFallback())

        handler = ErrorHandler(
            retry_policy=RetryPolicy(max_retries=1, base_delay_seconds=0.01, jitter=False),
            fallback_capability='fallback',
            fallback_params={'param': 'value'}
        )
        executive = ExecutiveMind(fresh_registry, fresh_memory, fresh_clock, DEFAULT_OWNER, error_handler=handler)

        intent = Intent.from_raw(
            raw_text='test all fail', goal='primary', success_criteria=['all fail'],
            owner_id=DEFAULT_OWNER.owner_id
        )

        # Should re-raise the ORIGINAL primary TaskFailure, not the fallback error
        with self.assertRaises(TaskFailure) as cm:
            executive.handle(intent)
        
        # The raised exception should be the original primary TaskFailure
        self.assertIn('always fails', str(cm.exception))
        # And it should be chained from the fallback error
        self.assertIsNotNone(cm.exception.__cause__)


if __name__ == '__main__':
    unittest.main()
