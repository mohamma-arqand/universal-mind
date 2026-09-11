"""Direct coverage for PantheonRegistry's uncovered branches.

The registry is live and central, but organ handling, key-error paths, restore
guards, and search filters were only partially exercised. These tests target
exactly those lines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from universal_mind.core.errors import SystemFault
from universal_mind.core.identity import DEFAULT_OWNER
from universal_mind.core.intent import Determinism
from universal_mind.layers import Layer
from universal_mind.memory.store import InMemoryStore
from universal_mind.pantheon.contracts import (
    Capability,
    CapabilityResult,
)
from universal_mind.pantheon.registry import (
    CapabilityDossier,
    OrganDescriptor,
    PantheonRegistry,
)


class _Stub(Capability):
    def execute(self, intent: Any, params: dict[str, Any]) -> CapabilityResult:
        return CapabilityResult(ok=True, output={}, cost={}, provenance={})


def _dossier(name: str, **over: Any) -> CapabilityDossier:
    fields: dict[str, Any] = {
        "name": name,
        "version": "1.0.0",
        "signature": f"{name}()",
        "purpose": f"serve {name}",
        "cost_model": "flat",
        "latency_profile": "instant",
        "reliability": "high",
        "side_effects": "none",
        "reversible": True,
        "required_secrets": [],
        "failure_modes": "none",
        "dependencies": [],
        "determinism": Determinism.STRICT,
        "provenance": {"producer": "test", "created_at": datetime.now(timezone.utc).isoformat(),
                       "owner_id": DEFAULT_OWNER.owner_id, "explicit_fields": ["idempotent"]},
        "idempotent": True,
    }
    fields.update(over)
    return CapabilityDossier(**fields)


def _organ(name: str, dossier: CapabilityDossier, **over: Any) -> OrganDescriptor:
    fields: dict[str, Any] = {
        "name": name,
        "signature": dossier.signature,
        "cost": 1.0,
        "latency_ms": 10.0,
        "credibility": 0.9,
        "domains": ("greeting",),
        "layer": Layer.GATEWAY,
        "dossier": dossier,
    }
    fields.update(over)
    return OrganDescriptor(**fields)


def _reg() -> tuple[PantheonRegistry, InMemoryStore]:
    store = InMemoryStore()
    return PantheonRegistry(store), store


def test_get_and_get_dossier_key_error() -> None:
    reg, _ = _reg()
    with pytest.raises(SystemFault):
        reg.get("missing", "1.0.0")
    with pytest.raises(SystemFault):
        reg.get_dossier("missing", "1.0.0")


def test_register_organ_and_duplicate() -> None:
    reg, _ = _reg()
    d = _dossier("greet")
    reg.register_organ(_organ("greet", d), _Stub())
    # duplicate organ name raises
    with pytest.raises(SystemFault):
        reg.register_organ(_organ("greet", d), _Stub())


def test_get_organ_key_error() -> None:
    reg, _ = _reg()
    with pytest.raises(SystemFault):
        reg.get_organ("missing")


def test_attach_organ_is_idempotent() -> None:
    reg, _ = _reg()
    d = _dossier("greet")
    reg.register(d, _Stub())
    organ = _organ("greet", d)
    assert reg.attach_organ(organ) == "greet"
    assert reg.attach_organ(organ) == "greet"  # idempotent


def test_restore_capability_new_and_existing_and_missing() -> None:
    reg, store = _reg()
    d = _dossier("greet")
    reg.register(d, _Stub())
    # capability already live -> restore returns False
    assert reg.restore_capability("greet", "1.0.0", _Stub()) is False

    # a fresh registry (dossier restored from store but no live capability)
    reg2 = PantheonRegistry(store)  # restores dossier from store
    assert reg2.restore_capability("greet", "1.0.0", _Stub()) is True
    assert reg2.restore_capability("greet", "1.0.0", _Stub()) is False

    # missing dossier -> raises
    reg3, _ = _reg()
    with pytest.raises(SystemFault):
        reg3.restore_capability("nope", "1.0.0", _Stub())


def test_search_filters() -> None:
    reg, _ = _reg()
    reg.register(_dossier("alpha", purpose="do the greeting", reversible=True, determinism=Determinism.STRICT), _Stub())
    reg.register(_dossier("beta", purpose="run analysis", reversible=False, determinism=Determinism.CREATIVE), _Stub())

    # purpose_contains matching (name or purpose)
    assert {d.name for d in reg.search(purpose_contains="greeting")} == {"alpha"}
    assert {d.name for d in reg.search(purpose_contains="analysis")} == {"beta"}
    # reversible filter
    assert {d.name for d in reg.search(reversible=True)} == {"alpha"}
    assert {d.name for d in reg.search(reversible=False)} == {"beta"}
    # determinism filter
    assert {d.name for d in reg.search(determinism=Determinism.CREATIVE)} == {"beta"}
    # no filters -> all
    assert len(reg.search()) == 2


def test_search_organs_filters() -> None:
    reg, _ = _reg()
    a = _dossier("alpha")
    b = _dossier("beta")
    reg.register(a, _Stub())
    reg.register(b, _Stub())
    reg.attach_organ(_organ("alpha-organ", a, credibility=0.9, layer=Layer.GATEWAY, domains=("greeting",), cost=1.0, latency_ms=10.0))
    reg.attach_organ(_organ("beta-organ", b, credibility=0.3, layer=Layer.DEMIURGE, domains=("analysis",), cost=50.0, latency_ms=500.0))

    # domain filter
    assert [o.name for o in reg.search_organs(domain="greeting")] == ["alpha-organ"]
    # layer filter
    assert [o.name for o in reg.search_organs(layer=Layer.DEMIURGE)] == ["beta-organ"]
    # min credibility
    assert [o.name for o in reg.search_organs(min_credibility=0.5)] == ["alpha-organ"]
    # max cost
    assert [o.name for o in reg.search_organs(max_cost=10.0)] == ["alpha-organ"]
    # max latency
    assert [o.name for o in reg.search_organs(max_latency_ms=100.0)] == ["alpha-organ"]
    # no filters
    assert len(reg.search_organs()) == 2
    assert len(reg.list_organs()) == 2