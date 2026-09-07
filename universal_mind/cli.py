"""Command-line entrypoint for Universal Mind — the deployment face.

A thin, non-interactive CLI exposing the package as a runnable artifact:

- ``universal-mind health`` — exercise the whole stack (registry, memory,
  executive, an end-to-end echo) and print a JSON status; exit 0 only when the
  stack is healthy.
- ``universal-mind demo`` — run the reference end-to-end demo.
- ``universal-mind -V / --version`` — print the package version.

Registered as the ``universal-mind`` console script in ``pyproject.toml``.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import Any

from universal_mind.version import __version__


def build_health_status() -> dict[str, Any]:
    """Run a full in-memory echo through the ExecutiveMind and report status.

    Never raises: on any failure it returns a ``stack_ok=False`` status so a
    caller can decide. Imports are lazy to keep the CLI entry
    cheap for non-health commands.
    """
    from universal_mind.core.clock import SystemClock
    from universal_mind.core.executive import ExecutiveMind
    from universal_mind.core.identity import DEFAULT_OWNER
    from universal_mind.core.intent import Determinism, Intent
    from universal_mind.layers import LAYER_CONTRACTS
    from universal_mind.memory.mnemosyne import Mnemosyne
    from universal_mind.memory.store import LocalJSONLStore
    from universal_mind.pantheon.contracts import EchoCapability
    from universal_mind.pantheon.registry import CapabilityDossier, PantheonRegistry

    try:
        from pathlib import Path
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temp_dir:
            store = LocalJSONLStore(directory=Path(temp_dir))
            clock = SystemClock()
            memory = Mnemosyne(store, clock)
            registry = PantheonRegistry(store)
            registry.register(
                CapabilityDossier(
                    name="echo",
                    version="1.0.0",
                    signature="echo(intent, params)",
                    purpose="End-to-end health echo.",
                    cost_model="flat",
                    latency_profile="instant",
                    reliability="high",
                    side_effects="none",
                    reversible=True,
                    required_secrets=[],
                    failure_modes="none",
                    dependencies=[],
                    determinism=Determinism.STRICT,
                    idempotent=True,  # echo is safe to retry; avoids the S2 warning
                    provenance={
                        "producer": "cli:health",
                        "created_at": clock.now().isoformat(),
                        "owner_id": DEFAULT_OWNER.owner_id,
                        "explicit_fields": ["idempotent"],
                    },
                ),
                EchoCapability(),
            )
            executive = ExecutiveMind(registry=registry, memory=memory, clock=clock, owner=DEFAULT_OWNER)
            intent = Intent.from_raw(
                raw_text="Echo health probe.",
                goal="echo",
                success_criteria=["output contains the request"],
                constraints=[],
                owner_id=DEFAULT_OWNER.owner_id,
                determinism=Determinism.STRICT,
            )
            outcome = executive.handle(intent)
            records = sum(1 for _ in store.read_all())
        return {
            "version": __version__,
            "layers": len(LAYER_CONTRACTS),
            "stack_ok": True,
            "outcome_status": outcome.status,
            "records": records,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "version": __version__,
            "layers": 0,
            "stack_ok": False,
            "outcome_status": None,
            "records": 0,
            "error": str(exc),
        }


def _cmd_health(args: argparse.Namespace) -> int:
    status = build_health_status()
    print(json.dumps(status, indent=None if args.compact else 2, sort_keys=True))
    return 0 if status.get("stack_ok") else 1


def _cmd_demo(_args: argparse.Namespace) -> int:
    from universal_mind import demo

    demo.main()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments and dispatch; returns the process exit code."""
    parser = argparse.ArgumentParser(
        prog="universal-mind",
        description="Universal Mind seed-core orchestration (deployment face).",
    )
    parser.add_argument("-V", "--version", action="version", version=f"universal-mind {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    health = sub.add_parser("health", help="exercise the stack and print JSON status")
    health.add_argument("--compact", action="store_true", help="single-line JSON output")
    sub.add_parser("demo", help="run the reference end-to-end demo")
    sub.add_parser("interactive", help="REPL driving the composed integration harness")
    sub.add_parser("chat", help="REPL wired to a real OpenAI-compatible provider (env-configured)")

    args = parser.parse_args(argv)

    if args.command == "health":
        return _cmd_health(args)
    if args.command == "demo":
        return _cmd_demo(args)
    if args.command == "interactive":
        return _cmd_interactive(args)
    if args.command == "chat":
        return _cmd_chat(args)
    return 2


def _repl(harness: object) -> int:
    """Run the shared REPL loop over any UniversalMindRuntime harness."""
    from universal_mind.integration import IntegrationError, UniversalMindRuntime

    runtime = harness if isinstance(harness, UniversalMindRuntime) else None
    assert runtime is not None, "harness must conform to UniversalMindRuntime"
    print("Universal Mind REPL (Ctrl-D to exit)")
    while True:
        try:
            line = input("you> ")
        except EOFError:
            print()
            return 0
        if not line.strip():
            continue
        try:
            report = runtime.run("reply", line.strip())
        except IntegrationError as exc:
            print(f"error: {exc}")
            continue
        print(f"result: {report.result_content}")
        print(f"  arbitrated winner: {report.arbitration.winner_strategy_id} ({report.arbitration.decision.value})")
        print(f"  evolution: {', '.join(report.proposals) if report.proposals else 'no proposals'}")


def _cmd_interactive(_args: argparse.Namespace) -> int:
    from universal_mind.integration import InMemoryIntegrationHarness
    from universal_mind.io.gateway import EchoProvider, Gateway

    harness = InMemoryIntegrationHarness(Gateway([EchoProvider(cost=1.0)]))
    return _repl(harness)


def _cmd_chat(_args: argparse.Namespace) -> int:
    """REPL wired to a real OpenAI-compatible provider via the Gateway.

    Reads ``UM_OPENAI_BASE_URL``, ``UM_OPENAI_MODEL``, and (lazily, at the
    request point) ``UM_OPENAI_API_KEY`` from the environment. With no key the
    call fails safe with a clear message — nothing is attempted unauthenticated.
    """
    import os

    from universal_mind.integration import InMemoryIntegrationHarness
    from universal_mind.io.gateway import Gateway, HttpChatProvider

    base = os.environ.get("UM_OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("UM_OPENAI_MODEL", "gpt-4o-mini")
    provider = HttpChatProvider(base, model)
    harness = InMemoryIntegrationHarness(Gateway([provider]))
    return _repl(harness)


if __name__ == "__main__":
    sys.exit(main())
