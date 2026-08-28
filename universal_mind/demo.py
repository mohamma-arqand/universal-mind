"""Runnable end-to-end demonstration for the Universal Mind seed core."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from universal_mind.core.clock import SystemClock
from universal_mind.core.identity import DEFAULT_OWNER
from universal_mind.core.intent import Determinism, Intent
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import LocalJSONLStore
from universal_mind.pantheon.contracts import EchoCapability
from universal_mind.pantheon.registry import CapabilityDossier, PantheonRegistry
from universal_mind.core.executive import ExecutiveMind


def main() -> None:
    """Run the demo using a local JSONL store in a temp directory."""
    with TemporaryDirectory() as temp_dir:
        store = LocalJSONLStore(directory=Path(temp_dir))
        clock = SystemClock()
        memory = Mnemosyne(store, clock)
        registry = PantheonRegistry(store)
        dossier = CapabilityDossier(
            name='echo',
            version='1.0.0',
            signature='echo(intent, params)',
            purpose='Echo back the request for end-to-end validation.',
            cost_model='flat',
            latency_profile='instant',
            reliability='high',
            side_effects='none',
            reversible=True,
            required_secrets=[],
            failure_modes='none',
            dependencies=[],
            determinism=Determinism.STRICT,
            provenance={'producer': 'demo', 'created_at': clock.now().isoformat(), 'owner_id': DEFAULT_OWNER.owner_id},
        )
        registry.register(dossier, EchoCapability())
        executive = ExecutiveMind(registry=registry, memory=memory, clock=clock, owner=DEFAULT_OWNER)
        intent = Intent.from_raw(
            raw_text='Please echo this back.',
            goal='echo',
            success_criteria=['output contains the request'],
            constraints=['keep it simple'],
            owner_id=DEFAULT_OWNER.owner_id,
            determinism=Determinism.STRICT,
        )
        outcome = executive.handle(intent)
        for record in store.read_all():
            print(record)
        print('outcome:', outcome)


if __name__ == '__main__':
    main()
