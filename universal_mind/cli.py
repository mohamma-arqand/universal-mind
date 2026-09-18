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
    sub = parser.add_subparsers(dest="verb", required=True)

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

    run = sub.add_parser("run", help="run one real capability through the super-platform (JSON output)")
    run.add_argument("capability", nargs="?", default="", help="capability to invoke (data/database/image/chart/pdf/media/archive/compute/notify/clipboard/vision/ai) — omit with --list to see all")
    run.add_argument("--params", default="{}", help="JSON params for the operation (e.g. '{\"operation\":\"stats\",\"data\":[1,2,3]}')")
    run.add_argument("--capabilities", help="comma-separated multi-capability synthesis (overrides single capability)")
    run.add_argument("--list", action="store_true", help="list every registered capability with its real operations")

    sub.add_parser("health-tick", help="آیا حلقهی خودکار زنده است؟ (task + heartbeat)")

    sub.add_parser("install-tick", help="نصب tick در Task Scheduler ویندوز — پلتفرم هر ساعت خودش را بیدار میکند")
    sub.add_parser("tick-health", help="ضربان پیشرو: آیا tick زنده است؟ سه سیگنال واقعی")

    sub.add_parser("uninstall-tick", help="حذف tick از Task Scheduler")

    goal = sub.add_parser("goal", help="هدف: «...» — اجرای هدف چندگامی با داوری ARETĒ و قابلیت ادامه")
    goal.add_argument("sentence", nargs="+", help="the goal sentence (quote it)")

    sch = sub.add_parser("schedule", help="زمانبندی: «هر روز ساعت ۸ گزارش کامل بده» را ثبت میکند")
    sch.add_argument("command", nargs="+", help="the Persian sentence WITH the schedule clause (quote it)")
    sub.add_parser("schedule-list", help="لیست زمانبندیهای ثبتشده")
    sub.add_parser("schedule-run", help="اجرا هر چه سررسید شده — the proactive loop tick")

    dsp = sub.add_parser("dashboard-sp", help="the super-platform dashboard — real usage, one self-contained Persian HTML")
    dsp.add_argument("--out", default="", help="output HTML path (default: artifacts/superplatform_dashboard.html)")

    fa = sub.add_parser("fa", help="اجرای فرمان فارسی (Persian command → real chain, Persian report)")
    fa.add_argument("command", help="the Persian command (quote it)")
    fa.add_argument("--json", action="store_true", help="print the raw JSON payload instead of the Persian report")

    fac = sub.add_parser("fa-contest", help="دو زنجیره رقابت میکنند و ARETĒ برنده را انتخاب میکند")
    fac.add_argument("command", help="the Persian command (quote it)")

    args = parser.parse_args(argv)

    if args.verb == "health":
        return _cmd_health(args)
    if args.verb == "demo":
        return _cmd_demo(args)
    if args.verb == "interactive":
        return _cmd_interactive(args)
    if args.verb == "chat":
        return _cmd_chat(args)
    if args.verb == "replay":
        return _cmd_replay(args)
    if args.verb == "evolve":
        return _cmd_evolve(args)
    if args.verb == "dashboard":
        return _cmd_dashboard(args)
    if args.verb == "cycle":
        return _cmd_cycle(args)
    if args.verb == "tick-health":
        return _cmd_tick_health(args)
    if args.verb == "health-tick":
        return _cmd_health_tick(args)
    if args.verb == "install-tick":
        return _cmd_install_tick(args)
    if args.verb == "uninstall-tick":
        return _cmd_uninstall_tick(args)
    if args.verb == "goal":
        return _cmd_goal(args)
    if args.verb == "schedule":
        return _cmd_schedule(args)
    if args.verb == "schedule-list":
        return _cmd_schedule_list(args)
    if args.verb == "schedule-run":
        return _cmd_schedule_run(args)
    if args.verb == "dashboard-sp":
        return _cmd_dashboard_sp(args)
    if args.verb == "fa":
        return _cmd_fa(args)
    if args.verb == "fa-contest":
        return _cmd_fa_contest(args)
    if args.verb == "run":
        return _cmd_run(args)
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
    try:
        from universal_mind.sovereign import build_sovereign_context

        ctx = build_sovereign_context(harness.store)
        print(f"[self] {ctx.summary}")
    except Exception as exc:  # noqa: BLE001 — the preamble is best-effort, never fatal
        print(f"[self] (context unavailable: {exc})", file=sys.stderr)
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


def _cmd_tick_health(args: argparse.Namespace) -> int:
    """The proactive heartbeat, honestly classified."""
    from universal_mind.task_install import tick_health

    result = tick_health()
    verdict_fa = {
        "alive": "زنده ✅", "silent": "نصب است اما ساکت ⏸", "dead": "نصب نیست ❌",
    }
    result["verdict_fa"] = verdict_fa.get(result["verdict"], result["verdict"])
    print(json.dumps(result, ensure_ascii=False))
    return 0


def _cmd_health_tick(args: argparse.Namespace) -> int:
    """Is the proactive loop alive? Task + heartbeat, each verbatim."""
    from universal_mind.task_install import tick_health

    print(json.dumps(tick_health(), indent=2, ensure_ascii=False))
    return 0


def _cmd_install_tick(args: argparse.Namespace) -> int:
    """Register the hourly tick in Windows Task Scheduler (read back)."""
    from universal_mind.task_install import install

    result = install()
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


def _cmd_uninstall_tick(args: argparse.Namespace) -> int:
    """Remove the tick task (idempotent)."""
    from universal_mind.task_install import uninstall

    result = uninstall()
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


def _cmd_goal(args: argparse.Namespace) -> int:
    """Parse a goal, persist it, run it step by step under ARETĒ judgment."""
    from universal_mind.agent_loop import goal_run_report, run_goal, start_goal
    from universal_mind.goal_parser import parse_goal

    sentence = " ".join(args.sentence)
    parsed = parse_goal(sentence)
    if parsed is None:
        print(json.dumps({"ok": False, "error": "قالب هدف: هدف: گام اول و گام دوم ..."}, ensure_ascii=False))
        return 1
    started = start_goal(parsed.text, parsed.steps, getattr(parsed, "guarded", None))
    result = run_goal(started["goal_id"])
    print(goal_run_report(result))
    return 0 if result.finished else 1


def _cmd_schedule(args: argparse.Namespace) -> int:
    """Register a scheduled task from a Persian sentence."""
    from universal_mind.scheduler import register

    sentence = " ".join(args.command)
    result = register(sentence)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


def _cmd_schedule_list(args: argparse.Namespace) -> int:
    from universal_mind.scheduler import list_schedules

    schedules = [
        {"id": s.schedule_id, "command": s.command, "every_minutes": s.every_minutes,
         "hour_of_day": s.hour_of_day, "last_run": s.last_run, "active": s.active}
        for s in list_schedules()
    ]
    print(json.dumps(schedules, indent=2, ensure_ascii=False))
    return 0


def _cmd_schedule_run(args: argparse.Namespace) -> int:
    """Fire every due schedule through the real engine (the proactive tick)."""
    from universal_mind.scheduler import run_due

    result = run_due()
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0 if result.get("ok") else 1


def _cmd_dashboard_sp(args: argparse.Namespace) -> int:
    """Build the super-platform dashboard from the REAL persistent history."""
    from universal_mind.superplatform_dashboard import build_dashboard

    result = build_dashboard(args.out or None)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


def _cmd_fa(args: argparse.Namespace) -> int:
    """Run a Persian command through the real engine; print the Persian report."""
    import json as _json

    from universal_mind.persian_report import persian_report
    from universal_mind.persian_router import route_and_run

    payload = route_and_run(args.command)
    if args.json:
        payload.pop("_registry", None)
        print(_json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        return 0 if payload.get("ok") else 1
    print(persian_report(payload))
    return 0 if payload.get("ok") else 1


def _cmd_fa_contest(args: argparse.Namespace) -> int:
    """Two candidate chains race on a real command; ARETĒ picks the winner."""
    from universal_mind.contested_execution import run_contested
    from universal_mind.persian_router import route_and_run
    from universal_mind.persian_report import persian_report

    route_payload = route_and_run(args.command)
    route = tuple(route_payload.get("route", []))
    if not route:
        print("هیچ قابلیتی شناخته نشد")
        return 1

    def _run(candidate: tuple[str, ...]) -> dict[str, object]:
        return route_and_run(args.command, forced_route=list(candidate))

    verdict = run_contested(args.command, route, _run)
    if not verdict.contested:
        print("(تنها یک نامزد — مسابقهای در کار نیست)")
        print(persian_report(verdict.winner.payload if verdict.winner else {}))
        return 0
    print(f"🏆 مسابقه: {' vs '.join(' → '.join(e.route) for e in verdict.all_entries)}")
    print(verdict.reasoning)
    if verdict.winner is not None:
        print()
        print(persian_report(verdict.winner.payload))
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    """Run one (or several) real capabilities through the super-platform.

    This is the single command-line door to every integrated suite and real tool:
    data/database/image/chart/pdf suites, media/archive/compute real effects, and
    notify/clipboard. Prints a JSON result; exit 0 on success, 1 on failure.
    """
    import json as _json

    from universal_mind.orchestration import orchestrate
    from universal_mind.real_tool_registry import real_connector_factory
    from universal_mind.tool_registry import (
        ConnectionMechanism,
        ToolConnectionSpec,
        ToolEntry,
        ToolRegistry,
    )

    if args.list:
        from universal_mind.real_tool_registry import _REAL_CONNECTORS

        listing: dict[str, Any] = {}
        for cap in sorted(_REAL_CONNECTORS):
            connector = _REAL_CONNECTORS[cap]()
            suite = getattr(connector, "_suite", None)  # every *SuiteConnector holds its suite
            ops = getattr(suite, "OPERATIONS", None) if suite is not None else None
            if not ops:
                # The five real-effect tools report their concrete operations.
                ops = {
                    "media": ("generate", "inspect", "transcode"),
                    "archive": ("compress",),
                    "compute": ("evaluate",),
                    "notify": ("notify",),
                    "clipboard": ("read", "write"),
                }.get(cap, ("(real effect)",))
            listing[cap] = list(ops)
        print(_json.dumps(listing, indent=2, ensure_ascii=False))
        return 0

    if not args.capability and not args.capabilities:
        print(_json.dumps({"ok": False, "error": "یک قابلیت بده یا --list بزن"}))
        return 1

    try:
        params = _json.loads(args.params)
        if not isinstance(params, dict):
            raise TypeError("params must be a JSON object")
    except (_json.JSONDecodeError, TypeError, ValueError) as exc:
        print(_json.dumps({"ok": False, "error": f"invalid --params: {exc}"}))
        return 1

    registry = ToolRegistry()
    if args.capabilities:
        capabilities = [c.strip() for c in args.capabilities.split(",") if c.strip()]
    else:
        capabilities = [args.capability.strip()]

    # Known real capabilities get routed to their suite; anything else falls back
    # to the mechanism connector (subprocess), so an unknown name is honestly
    # reported by the connector rather than silently misrouted.
    from universal_mind.real_tool_registry import _REAL_CONNECTORS

    known = set(_REAL_CONNECTORS)
    for cap in capabilities:
        registry.register(
            ToolEntry(
                name=f"cli-{cap}",
                capability=cap,
                connection=ToolConnectionSpec(
                    mechanism=ConnectionMechanism.SUBPROCESS,
                    command=(f"universal-mind-internal:{cap}" if cap in known else "unused"),
                ),
                absorbable=True,
            )
        )

    syn = orchestrate(registry, capabilities, connector_factory=real_connector_factory)
    output = {
        "ok": syn.ok,
        "capabilities": capabilities,
        "result": syn.output["synthesized_from"],
        "errors": {s.capability: s.error for s in syn.sub_outputs if not s.ok},
        "durations_ms": {s.capability: s.duration_ms for s in syn.sub_outputs},
    }
    print(_json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if syn.ok else 1


if __name__ == "__main__":
    sys.exit(main())
