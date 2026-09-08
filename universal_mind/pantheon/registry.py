"""Capability registry and dossier persistence."""
from __future__ import annotations

import warnings
from dataclasses import asdict, dataclass
from typing import Any

from ..core.errors import SystemFault
from ..core.intent import Determinism
from ..layers import Layer
from ..memory.store import MemoryStore
from .contracts import Capability


@dataclass(frozen=True)
class OrganDescriptor:
    """Describes an organ (capability + metadata) in the pantheon.

    Frozen at creation - no mutation after registration.
    """

    name: str
    signature: str
    cost: float  # Estimated cost in arbitrary units
    latency_ms: float  # Expected latency in milliseconds
    credibility: float  # 0.0 to 1.0, trustworthiness score
    domains: tuple[str, ...]  # Domains this organ operates in
    layer: Layer  # Architectural layer
    dossier: CapabilityDossier  # Full dossier reference


@dataclass(frozen=True)
class CapabilityDossier:
    """Self-describing capability registry entry.

    Note: idempotent defaults to False for safety. Capabilities that are truly
    idempotent (read-only, deterministic, no side effects) must explicitly declare
    idempotent=True. A warning is emitted at registration if idempotent is not
    explicitly set, to catch accidental assumptions.
    """

    name: str
    version: str
    signature: str
    purpose: str
    cost_model: str
    latency_profile: str
    reliability: str
    side_effects: str
    reversible: bool
    required_secrets: list[str]
    failure_modes: str
    dependencies: list[str]
    determinism: Determinism
    provenance: dict[str, Any]
    idempotent: bool = False  # Default False for safety; must opt-in explicitly

    def __post_init__(self) -> None:
        for secret in self.required_secrets:
            if len(secret) > 64 or '-----BEGIN' in secret:
                raise SystemFault('required_secrets must contain names only, not actual secrets.')
        # Warn if idempotent not explicitly set (uses default False)
        if 'idempotent' not in self.provenance.get('explicit_fields', []):
            warnings.warn(
                f'Capability "{self.name}": idempotent defaulted to False. '
                'If this capability is truly idempotent (safe to retry), '
                'explicitly set idempotent=True in the dossier.',
                UserWarning,
                stacklevel=3,
            )

    def business_card(self) -> str:
        """Return a five-line summary for day-to-day use."""
        lines = [
            f'{self.name} v{self.version}',
            f'Purpose: {self.purpose}',
            f'Cost: {self.cost_model} | Latency: {self.latency_profile}',
            f'Reliability: {self.reliability} | Determinism: {self.determinism.value}',
            f'Reversible: {self.reversible} | Side effects: {self.side_effects}',
        ]
        return '\n'.join(lines)


class PantheonRegistry:
    """Append-only capability registry backed by a memory store."""

    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        self._capabilities: dict[tuple[str, str], Capability] = {}
        self._dossiers: dict[tuple[str, str], CapabilityDossier] = {}
        self._organs: dict[str, OrganDescriptor] = {}  # Keyed by name
        for record in self.store.read_all():
            if record.get('kind') == 'capability_registration':
                payload = record['payload']
                if isinstance(payload, dict) and 'dossier' in payload:
                    dossier = CapabilityDossier(**payload['dossier'])
                    self._dossiers[(dossier.name, dossier.version)] = dossier

    def register(self, dossier: CapabilityDossier, capability: Capability) -> str:
        """Register a capability and persist the dossier."""
        key = (dossier.name, dossier.version)
        if key in self._dossiers:
            raise SystemFault(f'Duplicate capability registration for {dossier.name} {dossier.version}.')
        record = {
            'owner_id': dossier.provenance.get('owner_id', 'system'),
            'kind': 'capability_registration',
            'created_at': dossier.provenance.get('created_at'),
            'provenance': dict(dossier.provenance),
            'payload': {'dossier': asdict(dossier)},
            'schema_version': 1,
            'dossier_name': dossier.name,
            'dossier_version': dossier.version,
        }
        if not record['created_at']:
            from ..core.clock import SystemClock
            record['created_at'] = SystemClock().now().isoformat()
        record_id = self.store.append(record)
        self._capabilities[key] = capability
        self._dossiers[key] = dossier
        return record_id

    def register_organ(self, organ: OrganDescriptor, capability: Capability) -> str:
        """Register an organ (capability with full descriptor) and persist."""
        if organ.name in self._organs:
            raise SystemFault(f'Organ already registered: {organ.name}')
        # Also register the underlying capability
        self.register(organ.dossier, capability)
        self._organs[organ.name] = organ
        return organ.name

    def get(self, name: str, version: str) -> Capability:
        """Return a previously registered capability."""
        try:
            return self._capabilities[(name, version)]
        except KeyError as exc:
            raise SystemFault(f'Capability not found: {name} {version}.') from exc

    def get_dossier(self, name: str, version: str) -> CapabilityDossier:
        """Return the stored dossier for a capability."""
        try:
            return self._dossiers[(name, version)]
        except KeyError as exc:
            raise SystemFault(f'Capability dossier not found: {name} {version}.') from exc

    def restore_capability(self, name: str, version: str, capability: Capability) -> bool:
        """Re-attach a live capability to an already-restored dossier.

        After reopening a durable ledger the dossiers are restored from the
        stored registration records, but capability objects (code) are not
        serializable and must be attached again. This attaches without appending
        another registration record (which would duplicate). Returns True if the
        capability was newly attached, False if it is already live. Raises
        ``SystemFault`` if no dossier exists for ``(name, version)``.
        """
        key = (name, version)
        if key in self._capabilities:
            return False
        if key not in self._dossiers:
            raise SystemFault(f'No restored dossier for {name} {version}.')
        self._capabilities[key] = capability
        return True

    def get_organ(self, name: str) -> OrganDescriptor:
        """Return an organ by name."""
        try:
            return self._organs[name]
        except KeyError as exc:
            raise SystemFault(f'Organ not found: {name}.') from exc

    def attach_organ(self, organ: OrganDescriptor) -> str:
        """Record an organ's metadata (name index) for selectable resolution.

        Unlike :meth:`register_organ`, this does NOT re-append the dossier record
        or re-register the capability — it makes an already-registered capability
        addressable by domain/credibility for :class:`CapabilityResolver`,
        idempotently.
        """
        self._organs[organ.name] = organ
        return organ.name

    def search(
        self,
        *,
        purpose_contains: str | None = None,
        reversible: bool | None = None,
        determinism: Determinism | None = None,
    ) -> list[CapabilityDossier]:
        """Search dossiers by policy attributes."""
        matches = []
        for dossier in self._dossiers.values():
            if purpose_contains is not None and purpose_contains.lower() not in dossier.purpose.lower() and purpose_contains.lower() not in dossier.name.lower():
                continue
            if reversible is not None and dossier.reversible != reversible:
                continue
            if determinism is not None and dossier.determinism != determinism:
                continue
            matches.append(dossier)
        return matches

    def search_organs(
        self,
        *,
        domain: str | None = None,
        layer: Layer | None = None,
        min_credibility: float | None = None,
        max_cost: float | None = None,
        max_latency_ms: float | None = None,
    ) -> list[OrganDescriptor]:
        """Search organs by architectural attributes."""
        matches = []
        for organ in self._organs.values():
            if domain is not None and domain not in organ.domains:
                continue
            if layer is not None and organ.layer != layer:
                continue
            if min_credibility is not None and organ.credibility < min_credibility:
                continue
            if max_cost is not None and organ.cost > max_cost:
                continue
            if max_latency_ms is not None and organ.latency_ms > max_latency_ms:
                continue
            matches.append(organ)
        return matches

    def list_organs(self) -> list[OrganDescriptor]:
        """List all registered organs."""
        return list(self._organs.values())
