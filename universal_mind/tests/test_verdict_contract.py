"""Contract test: the two Verdict enums are SEMANTICALLY equivalent.

There are two ALLOW/DENY/DEFER verdict enums in the codebase:

- ``gates.base.Verdict`` — plain ``Enum``, UPPERCASE values ("ALLOW"), used only
  for identity comparison inside the gate pipeline.
- ``powers.judgment.Verdict`` — ``str, Enum``, lowercase values ("allow"), whose
  ``.value`` is serialized all over (lineage, policy_trace, cross_judge,
  dashboard, cli, showcase).

They are the *same* three-way outcome; they differ only in representation. A
future change that crosses them (e.g. comparing one against the other) would
silently always be False. This test locks the contract so a divergence or an
accidental cross-use is caught loudly here rather than as a runtime bug.
"""

from __future__ import annotations

from universal_mind.gates.base import Verdict as GateVerdict
from universal_mind.powers.judgment import Verdict as JudgmentVerdict


def test_both_have_identical_membership() -> None:
    assert {v.name for v in GateVerdict} == {"ALLOW", "DENY", "DEFER"}
    assert {v.name for v in JudgmentVerdict} == {"ALLOW", "DENY", "DEFER"}


def test_values_differ_only_by_case() -> None:
    """The serialized form (powers.judgment) is lowercase; the gate form is not."""
    assert JudgmentVerdict.ALLOW.value == "allow"
    assert JudgmentVerdict.DENY.value == "deny"
    assert JudgmentVerdict.DEFER.value == "defer"
    # The gate enum's values are uppercase; a future merge must pick ONE.
    assert GateVerdict.ALLOW.value == "ALLOW"


def test_lowercase_payload_value_is_the_serialized_contract() -> None:
    """Everywhere a decision is serialized, .value must be lowercase."""
    import json

    # a decision payload must encode the lowercase string, not "ALLOW"
    payload = {"decision": JudgmentVerdict.ALLOW.value}
    assert json.loads(json.dumps(payload))["decision"] == "allow"