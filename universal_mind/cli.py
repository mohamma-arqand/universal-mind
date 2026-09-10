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


def _cmd_dashboard(args: argparse.Namespace) -> int:
    """Build a self-contained, real-data dashboard HTML to ``--out``."""
    from universal_mind.dashboard import build_and_write

    out = build_and_write(args.out)
    print(f"dashboard written to {out}")
    return 0


def _cmd_cycle(args: argparse.Namespace) -> int:
    """Run one full demo->dashboard cycle on a durable ledger directory.

    Opens ``--dir`` as a persistent store, runs the synthesis + ARETĒ scenario
    (via :func:`build_and_write`, which reuses an existing store without
    clearing it), then rewrites the dashboard HTML from that same canonical
    ledger. Duplicate capability registrations are idempotent, so repeated
    cycles grow only the synthesis/standard history — an audit trail — while the
    dashboard always reflects the latest committed state.
    """
    from pathlib import Path

    from universal_mind.core.clock import SystemClock
    from universal_mind.core.executive import ExecutionThrottle, ExecutiveMind
    from universal_mind.core.identity import DEFAULT_OWNER
    from universal_mind.dashboard import build_and_write
    from universal_mind.memory.mnemosyne import Mnemosyne
    from universal_mind.memory.store import LocalJSONLStore
    from universal_mind.pantheon.registry import PantheonRegistry
    from universal_mind.prometheus import evolve_and_apply

    directory = Path(args.dir)
    store = LocalJSONLStore(directory=directory, filename=args.filename)

    # Prometheus self-evolution pass on the durable ledger before rendering.
    executive = ExecutiveMind(
        registry=PantheonRegistry(store),
        memory=Mnemosyne(store, SystemClock()),
        clock=SystemClock(),
        owner=DEFAULT_OWNER,
        throttle=ExecutionThrottle(error_rate_threshold=args.throttle),
    )
    report, outcomes = evolve_and_apply(store, executive)

    out = build_and_write(Path(args.out), store=store)
    records = sum(1 for _ in store.read_all())
    print(
        f"cycle complete: evolution {[p.kind.value for p in report.proposals]} "
        f"| applied {[o.detail for o in outcomes if not o.detail.startswith('ignored')]} "
        f"| {records} ledger records -> {out}"
    )
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
    chatp = sub.add_parser("chat", help="REPL wired to an OpenAI-compatible provider (env or --local)")
    chatp.add_argument("--local", action="store_true", help="spin up the offline stub provider (no key/network)")
    replay = sub.add_parser("replay", help="recover + audit an on-disk ledger directory")
    replay.add_argument("--dir", required=True, help="ledger directory to recover")
    replay.add_argument("--filename", default="ledger.jsonl", help="ledger filename")
    replay.add_argument("--compact", action="store_true", help="single-line JSON output")
    evolve = sub.add_parser("evolve", help="run one Prometheus self-evolution pass on a ledger dir")
    evolve.add_argument("--dir", required=True, help="ledger directory to evolve over")
    evolve.add_argument("--filename", default="ledger.jsonl", help="ledger filename")
    evolve.add_argument("--throttle", type=float, default=0.5, help="starting error-rate threshold")
    evolve.add_argument("--compact", action="store_true", help="single-line JSON output")

    dash = sub.add_parser("dashboard", help="build a self-contained real-data dashboard HTML")
    dash.add_argument("--out", required=True, help="output .html path")

    cycle = sub.add_parser("cycle", help="run a demo->synthesis->evolve->dashboard cycle on a durable ledger")
    cycle.add_argument("--dir", required=True, help="ledger directory (persistent)")
    cycle.add_argument("--filename", default="ledger.jsonl", help="ledger filename")
    cycle.add_argument("--throttle", type=float, default=0.5, help="starting error-rate threshold")
    cycle.add_argument("--out", required=True, help="output .html path")

    args = parser.parse_args(argv)

    if args.command == "health":
        return _cmd_health(args)
    if args.command == "demo":
        return _cmd_demo(args)
    if args.command == "interactive":
        return _cmd_interactive(args)
    if args.command == "chat":
        return _cmd_chat(args)
    if args.command == "replay":
        return _cmd_replay(args)
    if args.command == "evolve":
        return _cmd_evolve(args)
    if args.command == "dashboard":
        return _cmd_dashboard(args)
    if args.command == "cycle":
        return _cmd_cycle(args)
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


def _cmd_chat(args: argparse.Namespace) -> int:
    """REPL wired to a real OpenAI-compatible provider via the Gateway.

    With ``--local`` the command spins up the offline stub server (no key, no
    network) and points the harness at it, so the full GATEWAY→provider wire path
    is exercised deterministically on the machine. Otherwise it reads
    ``UM_OPENAI_BASE_URL``, ``UM_OPENAI_MODEL``, and (lazily) ``UM_OPENAI_API_KEY``
    from the environment; with no key it fails safe with a clear message.
    """
    import os

    from universal_mind.integration import InMemoryIntegrationHarness
    from universal_mind.io.gateway import Gateway, HttpChatProvider
    from universal_mind.io.stub_server import StubChatServer

    if args.local:
        server = StubChatServer()
        base = server.start()
        model = "stub-1"
        print(f"[local] stub provider serving at {base} (model {model})")
        provider = HttpChatProvider(base, model, resolver=lambda _: "local-key")
    else:
        base = os.environ.get("UM_OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.environ.get("UM_OPENAI_MODEL", "gpt-4o-mini")
        provider = HttpChatProvider(base, model)
    harness = InMemoryIntegrationHarness(Gateway([provider]))
    try:
        return _repl(harness)
    finally:
        if args.local:
            server.stop()


def _cmd_replay(args: argparse.Namespace) -> int:
    """Recover + audit an on-disk ledger directory (local, no network)."""
    from universal_mind.runtime import recover_ledger

    records = recover_ledger(args.dir, filename=args.filename)
    kinds: dict[str, int] = {}
    for record in records:
        kind = str(record.get("kind", "unknown"))
        kinds[kind] = kinds.get(kind, 0) + 1

    summary = {
        "dir": str(args.dir),
        "filename": args.filename,
        "total_records": len(records),
        "kinds": kinds,
    }
    print(json.dumps(summary, indent=None if args.compact else 2, sort_keys=True))
    return 0


def _cmd_evolve(args: argparse.Namespace) -> int:
    """Run one Prometheus self-evolution pass over an on-disk ledger."""
    from universal_mind.core.clock import SystemClock
    from universal_mind.core.executive import ExecutionThrottle, ExecutiveMind
    from universal_mind.core.identity import DEFAULT_OWNER
    from universal_mind.memory.mnemosyne import Mnemosyne
    from universal_mind.memory.store import LocalJSONLStore
    from universal_mind.pantheon.registry import PantheonRegistry
    from universal_mind.prometheus import evolve_and_apply

    store = LocalJSONLStore(directory=args.dir, filename=args.filename)
    # A no-op harness provider is only used to satisfy construction; the pass
    # is driven purely by the ledger records already on disk.
    executive = ExecutiveMind(
        registry=PantheonRegistry(store),
        memory=Mnemosyne(store, SystemClock()),
        clock=SystemClock(),
        owner=DEFAULT_OWNER,
        throttle=ExecutionThrottle(error_rate_threshold=args.throttle),
    )
    report, outcomes = evolve_and_apply(store, executive)
    summary = {
        "dir": str(args.dir),
        "proposals": [p.kind.value for p in report.proposals],
        "applied": [o.detail for o in outcomes if not o.detail.startswith("ignored")],
        "ignored": [o.detail for o in outcomes if o.detail.startswith("ignored")],
        "throttle_threshold": executive.throttle.error_rate_threshold,
        "evolution_summary": report.summary,
    }
    print(json.dumps(summary, indent=None if args.compact else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
