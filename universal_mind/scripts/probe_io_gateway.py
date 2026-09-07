#!/usr/bin/env python3
"""Probe: GATEWAY layer retries with backoff and fails over across providers.

Runs the Gateway against deterministic reference providers to confirm the
ordering contract holds from outside the test suite: primary success is fast,
transient failures back off and recover, permanent failures fail over, and a
total outage yields a clean failed outcome (not a hang or a crash). Exit 0 only
if every check passes.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.core.errors import RetryPolicy
from universal_mind.io import EchoProvider, Gateway, Message, ScriptedProvider
from universal_mind.io.errors import (
    ProviderConfig,
    ProviderPermanent,
    ProviderTransient,
)


def no_delay(max_retries: int = 2) -> RetryPolicy:
    """Deterministic zero-delay policy."""
    return RetryPolicy(max_retries=max_retries, base_delay_seconds=0.0, jitter=False)


def attempt_primary_success() -> bool:
    """A healthy primary answers on the first attempt."""
    outcome = Gateway([EchoProvider()]).generate([Message("user", "hello")])
    ok = outcome.ok and outcome.provider_name == "echo" and outcome.attempts == 1
    print(f"  provider={outcome.provider_name} attempts={outcome.attempts} ok={outcome.ok}")
    return ok


def attempt_retry_recovers() -> bool:
    """Transient failures are retried with backoff and then succeed."""
    primary = ScriptedProvider([ProviderTransient("boom"), ProviderTransient("boom"), "recovered"])
    gateway = Gateway([primary], retry_policy=no_delay())
    outcome = gateway.generate([Message("user", "ping")])
    ok = outcome.ok and outcome.content == "recovered" and outcome.attempts == 3
    print(f"  content={outcome.content!r} attempts={outcome.attempts} ok={outcome.ok}")
    return ok


def attempt_backoff_applied() -> bool:
    """Backoff delays are actually scheduled between retries."""
    delays: list[float] = []

    def sleep(delay: float) -> None:
        delays.append(delay)

    policy = RetryPolicy(max_retries=2, base_delay_seconds=1.0, jitter=False)
    gateway = Gateway(
        [ScriptedProvider([ProviderTransient("1"), ProviderTransient("2"), "ok"])],
        retry_policy=policy, sleep=sleep,
    )
    outcome = gateway.generate([Message("user", "x")])
    ok = outcome.ok and delays == [1.0, 2.0]
    print(f"  delays={delays} ok={outcome.ok}")
    return ok


def attempt_failover_on_permanent() -> bool:
    """A permanent primary failure fails over to the fallback immediately."""
    primary = ScriptedProvider([ProviderPermanent("collapsed")])
    outcome = Gateway([primary, EchoProvider()], retry_policy=no_delay()).generate(
        [Message("user", "fallback")]
    )
    ok = outcome.ok and outcome.provider_name == "echo" and outcome.attempts == 2
    print(f"  provider={outcome.provider_name} attempts={outcome.attempts} ok={outcome.ok}")
    return ok


def attempt_failover_after_exhaustion() -> bool:
    """Retries spent on the primary then fail over to the fallback."""
    primary = ScriptedProvider([ProviderTransient("always down")])
    outcome = Gateway([primary, EchoProvider()], retry_policy=no_delay(max_retries=2)).generate(
        [Message("user", "eventually")]
    )
    ok = outcome.ok and outcome.provider_name == "echo" and outcome.attempts == 4
    print(f"  provider={outcome.provider_name} attempts={outcome.attempts} ok={outcome.ok}")
    return ok


def attempt_total_outage() -> bool:
    """Every provider failing returns a clean failed outcome."""
    gateway = Gateway(
        [ScriptedProvider([ProviderPermanent("p1 down")], name="p1"),
         ScriptedProvider([ProviderTransient("p2 down")], name="p2")],
        retry_policy=no_delay(max_retries=1),
    )
    outcome = gateway.generate([Message("user", "x")])
    ok = (not outcome.ok) and outcome.content is None and outcome.last_error is not None
    print(f"  ok={outcome.ok} last_error={outcome.last_error!r}")
    return ok


def attempt_deterministic() -> bool:
    """Identical inputs produce identical attempts/cost/provider."""
    one = Gateway([EchoProvider(cost=3.0)]).generate([Message("user", "d")])
    two = Gateway([EchoProvider(cost=3.0)]).generate([Message("user", "d")])
    ok = (one.attempts, one.cost, one.provider_name) == (two.attempts, two.cost, two.provider_name)
    print(f"  attempts={one.attempts} cost={one.cost} provider={one.provider_name}")
    return ok


def attempt_http_fail_safe() -> bool:
    """HttpChatProvider fails safe (config error) when no key is present."""
    from universal_mind.io import HttpChatProvider

    provider = HttpChatProvider("https://example.test/v1", "demo", resolver=lambda _n: None)
    try:
        provider.call([Message("user", "x")])
        print("  FAIL: unauthenticated call attempted without a key")
        return False
    except ProviderConfig:
        print("  OK: fail-safe ProviderConfig raised without a key")
        return True


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    """Write probe results to JUnit XML."""
    testsuite = ET.Element(
        "testsuite",
        {
            "name": "ProbeIoGateway",
            "tests": str(len(results)),
            "failures": str(sum(1 for _, r in results if not r)),
            "errors": "0",
            "time": "0",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeIoGateway", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Primary provider answers fast (1 attempt)", attempt_primary_success),
    ("Transient failures retried, then recover", attempt_retry_recovers),
    ("Backoff delays are scheduled between retries", attempt_backoff_applied),
    ("Permanent primary failure fails over immediately", attempt_failover_on_permanent),
    ("Retries exhausted, then fail over to fallback", attempt_failover_after_exhaustion),
    ("Total outage yields a clean failed outcome", attempt_total_outage),
    ("Gateway is deterministic across identical inputs", attempt_deterministic),
    ("HttpChatProvider is fail-safe without a key", attempt_http_fail_safe),
]


def main() -> int:
    """Run every probe check and exit non-zero if any fails."""
    parser = argparse.ArgumentParser(description="GATEWAY layer Probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 60)
    print("PROBE: GATEWAY — Deterministic providers, Retry & Failover")
    print("=" * 60)

    results: list[tuple[str, bool]] = []
    for name, fn in _CHECKS:
        print(f"\n--- {name} ---")
        results.append((name, fn()))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_ok = True
    for name, result in results:
        status = "OK" if result else "FAILED"
        print(f"  {name}: {status}")
        all_ok = all_ok and result

    if args.junit_xml:
        write_junit_xml(results, args.junit_xml)
        print(f"\nJUnit XML written to {args.junit_xml}")

    if all_ok:
        print("\nALL CHECKS PASSED - GATEWAY RETRIES WITH BACKOFF AND FAILS OVER ACROSS PROVIDERS")
        return 0
    print("\nSOME CHECKS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())