"""Coverage for the Summon power (InMemorySummon.summon)."""

from __future__ import annotations

import asyncio

from universal_mind.powers.summon import InMemorySummon, SummonInput


def test_summon_spawns_with_incrementing_ids() -> None:
    s = InMemorySummon()
    out1 = asyncio.run(s.summon(SummonInput(organ_name="greeter", config={"a": 1}, owner_id="o")))
    out2 = asyncio.run(s.summon(SummonInput(organ_name="greeter", config={"b": 2}, owner_id="o")))

    assert out1.organ_id == "greeter-1"
    assert out2.organ_id == "greeter-2"
    assert out1.status == "spawned"


def test_summon_records_organ_metadata() -> None:
    s = InMemorySummon()
    out = asyncio.run(s.summon(SummonInput(organ_name="greeter", config={"x": 1, "y": 2}, owner_id="o")))
    assert out.metadata == {"config_keys": ["x", "y"]}
    # internal store tracks the organ with owner + config + spawned status
    assert "greeter-1" in s._organs
    assert s._organs["greeter-1"]["owner_id"] == "o"
    assert s._organs["greeter-1"]["status"] == "spawned"