"""Orchestrated synthesis — many tools, one artifact (super-platform Phase D).

Phases A–C made tools reachable and absorbable. Phase D is where "more than the
sum of its parts" becomes concrete: given a high-level request that names several
needed capabilities, the brain reaches each, collects their evidence-anchored
outputs, and *fuses* them into a single new artifact D that no single tool produced
alone — the same "synthesis, not integration" axiom the project already holds, now
generalized from two pre-selected specialists to any N tools in the encyclopedia.

Deterministic and local: it reads the registry, reaches tools through their
connectors, and fuses through an injectable composer (defaulting to a structured
join). Nothing here invents an output; a capability with no tool simply fails that
sub-request rather than fabricating a result.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from universal_mind.connectors import Connector, connector_for
from universal_mind.tool_registry import ToolEntry, ToolRegistry


def _perf() -> float:
    """A monotonic clock with a fixed unit (seconds)."""
    return time.perf_counter()

# Resolve the connector for a tool. Defaults to the built-in mechanism mapping,
# but a caller may inject a factory (e.g. to route a capability to a custom
# connector such as MediaToolConnector).
ConnectorFactory = Callable[[ToolEntry], Connector]


def _default_connector(tool: ToolEntry) -> Connector:
    return connector_for(tool.connection_mechanism)


class OrchestrationError(Exception):
    """Raised when a requested capability cannot be honored by any tool."""


@dataclass(frozen=True)
class SubOutput:
    """One tool's contribution to the synthesis."""

    capability: str
    tool_name: str
    output: Any
    ok: bool
    error: str = ""
    duration_ms: float = 0.0   # real wall-clock time the tool took (measured)


@dataclass(frozen=True)
class Synthesis:
    """The fused artifact D plus its provenance."""

    output: Any
    sub_outputs: tuple[SubOutput, ...]
    ok: bool                  # True only when every requested capability succeeded


# A composer fuses a list of per-capability results into one artifact D.
Composer = Callable[[list[SubOutput]], Any]


def _default_composer(sub_outputs: list[SubOutput]) -> Any:
    """Default fusion: a structured bundle keyed by capability (never a lossy concat)."""
    return {
        "synthesized_from": {s.capability: s.output for s in sub_outputs if s.ok},
    }


# ---------------------------------------------------------------------------
# Dataflow synthesis: one program's real output becomes the next program's input.
#
# The flow table is explicit and honest: image-producing capabilities (chart,
# media, image, vision) feed pdf's with_image; the flow only fills a GAP — it
# never overrides parameters the caller (e.g. the Persian layer) already chose.
# ---------------------------------------------------------------------------

_IMAGE_PRODUCERS: tuple[str, ...] = ("chart", "media", "image", "vision")
_IMAGE_EXTENSIONS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".bmp", ".webp")


def _flow_params(
    consumer: str,
    params: dict[str, Any],
    last_producer: str | None,
    last_output: Any,
    command: str = "",
    produced_paths: tuple[str, ...] = (),
    produced_stats: dict[str, float] | None = None,
) -> tuple[dict[str, Any], str | None]:
    """Enrich the consumer's params with the previous producer's real output.

    Returns (enriched_params, flow_description) — flow_description is None when
    nothing flowed (the common, honest case). Two real flows exist:
    - IMAGE flow: chart/media/image/vision → pdf/image (the artifact is embedded);
    - STATS flow: data → pdf (the computed statistics become a real table row).
    """
    if last_producer is None or not isinstance(last_output, (dict, list)):
        return params, None  # non-structured outputs cannot flow

    # IMAGE flow — the previous program produced a real image file; only an
    # image consumer (pdf/image) can embed it. Other consumers (clipboard/
    # archive/notify) fall through to their own flows below. A LIST output
    # (a database read-back) has no image — it flows to the memory flow below.
    path = last_output.get("path") if isinstance(last_output, dict) else None
    if (
        isinstance(path, str)
        and path.lower().endswith(_IMAGE_EXTENSIONS)
        and consumer in ("pdf", "image")
    ):
        # The one sanctioned UPGRADE: a Persian report gets the just-made image
        # embedded (persian_rtl → persian_report). Any other explicit intent wins.
        if params.get("operation") and params["operation"] != "persian_rtl":
            return params, None
        if consumer == "pdf":
            enriched = {
                **params,
                "operation": "persian_report",
                "image_path": path,
                "caption": params.get("title") or f"{last_producer} output",
            }
            return enriched, f"{last_producer} → pdf (گزارش فارسی با نمودار درونش)"
        return params, None

    # STATS flow — the previous program computed real numbers; a pdf report
    # renders them as a real table (the numbers ARE the content). Both shapes
    # are honored: the suite's raw flat result (mean/std/... directly) and the
    # wrapped shape ({"stats": {...}}).
    stats = last_output.get("stats") if isinstance(last_output, dict) else None
    if not isinstance(stats, dict) or not stats:
        flat = (
            {
                k: v
                for k, v in last_output.items()
                if isinstance(v, (int, float)) and not isinstance(v, bool) and k != "ok"
            }
            if isinstance(last_output, dict)
            else {}
        )
        if flat:
            stats = flat
    # A vision read-back carries its own stats wrapper (shape/means/std of the
    # image the chain made) — the pdf report can tabulate it too.
    if isinstance(stats, dict) and stats and consumer == "pdf":
        if params.get("operation") and params["operation"] not in ("persian_rtl", "persian_report"):
            return params, None  # explicit intent (invoice/table/...) wins
        headers = ["شاخص", "مقدار"]
        rows = [[str(k), _fmt_num(v)] for k, v in stats.items()]
        # A report with a chart in the chain gets BOTH: the table AND the image
        # (persian_report renders each part it is given).
        image_in_chain = next(
            (p2 for p2 in reversed(produced_paths) if p2.lower().endswith(_IMAGE_EXTENSIONS)),
            "",
        )
        enriched = {
            **params,
            "operation": "persian_report",
            "image_path": image_in_chain,
            "stats_headers": headers,
            "stats_rows": rows,
        }
        if image_in_chain:
            return enriched, f"{last_producer} → pdf (جدول آمار + نمودار درون گزارش)"
        return enriched, f"{last_producer} → pdf (جدول آمار واقعی درون گزارش)"

    # CLIPBOARD flow — the chain's real output summarized INTO the Windows
    # clipboard, ready to paste. An explicit text always wins.
    if consumer == "clipboard":
        if params.get("operation") == "read":
            return params, None  # the operator asked to READ, never override
        if not params.get("text"):
            summary = _artifact_summary(last_output)
            if summary:
                return (
                    {**params, "operation": "write", "text": summary},
                    f"{last_producer} → clipboard ({summary})",
                )
        return params, None

    # EXCEL flow — the chain's computed numbers become a REAL .xlsx table:
    # the stats/metrics the chain produced, styled headers, typed cells.
    # Explicit headers/rows in the params always win.
    if consumer == "excel":
        if params.get("operation") == "read_table":
            return params, None  # the operator asked to READ a workbook
        if params.get("headers") or params.get("rows"):
            return params, None  # explicit table content wins
        stats = last_output.get("stats") if isinstance(last_output, dict) else None
        if not isinstance(stats, dict) or not stats:
            stats = dict(produced_stats) if produced_stats else {}
        if stats:
            headers = ["شاخص", "مقدار"]
            rows = [[str(k), _fmt_num(v)] for k, v in stats.items()]
            return (
                {**params, "operation": "write_table", "headers": headers, "rows": rows},
                f"{last_producer} → excel ({len(rows)} شاخص در اکسل)",
            )
        return params, None

    # OCR flow — the chain's own image READ: real text extraction from what
    # the platform just made. The deepest read loop: make → look → READ.
    if consumer == "ocr" and produced_paths:
        if params.get("path"):
            return params, None  # an explicit target wins
        image_paths = [p for p in produced_paths if p.lower().endswith(_IMAGE_EXTENSIONS)]
        if image_paths:
            target = image_paths[-1]
            name = target.rsplit("/", 1)[-1].rsplit(chr(92), 1)[-1]
            return (
                {**params, "operation": "read", "path": target},
                f"آخرین تصویر زنجیره → متنخوان (خواندن {name})",
            )
        return params, None

    # VISION flow — the chain's produced image UNDERSTOOD by real computer
    # vision (OpenCV): the platform sees its own output. The perception loop
    # at the deepest level: make → look → understand.
    if consumer == "vision" and produced_paths:
        if params.get("operation"):
            return params, None  # an explicit analysis choice wins
        image_paths = [p for p in produced_paths if p.lower().endswith(_IMAGE_EXTENSIONS)]
        if image_paths:
            target = image_paths[-1]  # the most recent image the chain made
            return (
                {**params, "operation": "stats", "path": target},
                f"آخرین تصویر زنجیره → بینایی (تحلیل {target.rsplit('/', 1)[-1].rsplit(chr(92), 1)[-1]})",
            )
        return params, None

    # DATABASE flow — the chain's computed results persisted into a REAL table
    # so the operator can query them later («چی ذخیره کردی؟»). The one sanctioned
    # UPGRADE (the pdf/persian_report pattern): when the sentence's raw-number
    # insert coincides with a real computing producer, the COMPUTED results
    # replace the raw echo — storing what was computed beats re-stating the
    # input. Any other explicit shape wins untouched.
    if consumer == "database":
        op = params.get("operation")
        raw_insert = (
            op == "insert_many" and params.get("table") == "extracted_data"
            and all(set(r) == {"value"} for r in params.get("rows") or [])
        )
        if op and op != "query" and not raw_insert:
            return params, None  # an explicit insert/query choice wins
        # The whole chain's computed metrics (every producer), not just the
        # last one — «حساب کن ... ذخیره کن» stores ALL the numbers made.
        chain_metrics: dict[str, Any] = dict(produced_stats) if produced_stats else {}
        if not chain_metrics:
            last_stats = last_output.get("stats") if isinstance(last_output, dict) else None
            if isinstance(last_stats, dict) and last_stats:
                chain_metrics = dict(last_stats)
        if chain_metrics:
            result_rows: list[dict[str, str]] = [
                {"metric": str(k), "value": _fmt_num(v)} for k, v in chain_metrics.items()
            ]
            return (
                {**{k: v for k, v in params.items() if k != "rows"},
                 "operation": "insert_many", "table": "chain_results",
                 "rows": result_rows, "persistent": True},
                f"{last_producer} → database ({len(result_rows)} شاخصِ محاسبهشده ذخیره شد)",
            )
        return params, None

    # ARCHIVE flow — the run's produced FILES packed into one real .tar.gz.
    # The whole chain's output, preserved as a single portable bundle.
    # A generic "compress" (the vocabulary default) is upgradeable: archiving
    # the chain's real files is the superior interpretation of the same intent.
    if consumer == "archive" and produced_paths:
        op = params.get("operation")
        if op and op not in ("compress", "compress_files"):
            return params, None  # an explicit other operation wins
        enriched = {
            **params,
            "operation": "compress_files",
            "files": list(produced_paths),
        }
        return enriched, f"{len(produced_paths)} فایلِ این اجرا → archive (بایگانی یکجا)"

    # MEMORY→REPORT flow — a database read-back (a LIST of real stored rows)
    # becomes a genuine table inside the Persian report: the platform renders
    # ITS OWN MEMORY. Only fires when the producer's output IS a row list.
    if consumer == "pdf" and isinstance(last_output, list) and last_output:
        if params.get("operation") and params["operation"] not in ("persian_rtl", "persian_report"):
            return params, None  # explicit intent wins
        sample = last_output[0]
        if isinstance(sample, dict):
            headers = list(sample.keys())
            rows = [[_fmt_num(v) if isinstance(v, (int, float)) else str(v)
                     for v in r.values()] for r in last_output[:15]]
            return (
                {**params, "operation": "persian_report",
                 "image_path": "", "stats_headers": headers, "stats_rows": rows},
                f"حافظه → گزارش ({len(rows)} ردیفِ واقعی از دیتابیس درون گزارش)",
            )
    # SPEECH flow — the chain's summary spoken ALOUD through the real SAPI
    # voice (fa-preferred, honest when no Persian voice is installed).
    # Explicit text always wins; the command echo is treated as empty.
    if consumer == "speech":
        if not params.get("text") or params.get("text") == command:
            summary = _artifact_summary(last_output)
            if summary:
                spoken_text = (
                    f"{summary}. میانگین برابر {_fmt_num(last_output.get('mean'))}"
                    if isinstance(last_output, dict) and isinstance(last_output.get("mean"), (int, float))
                    else summary
                )
                return (
                    {**params, "operation": "speak", "text": spoken_text},
                    f"{last_producer} → speech ({summary})",
                )
        return params, None

    # NOTIFY flow — the chain's final artifact summarized as a real Windows
    # toast. The perception loop closes: the platform not only MAKES, it SAYS
    # what it made. Explicit title/body in the params always win.
    if consumer == "notify":
        title = params.get("title") or "ذهن یکپارچه"
        body = params.get("body")
        # A body that merely echoes the command carries no information — the
        # real summary of what the chain MADE is worthier than the order echo.
        if not body or body == command:
            summary = _artifact_summary(last_output)
            if summary:
                return (
                    {**params, "operation": "notify", "title": title, "body": summary},
                    f"{last_producer} → notify ({summary})",
                )
    return params, None


def _artifact_summary(output: Any) -> str:
    """A short honest Persian summary of one program's real output."""
    if not isinstance(output, dict):
        return ""
    path = output.get("path")
    if isinstance(path, str) and path:
        name = path.replace("\\", "/").rsplit("/", 1)[-1]
        return f"ساخته شد: {name}"
    bytes_value = output.get("bytes")
    if isinstance(bytes_value, (int, float)) and bytes_value > 0:
        return f"خروجی {_fmt_num(bytes_value / 1024)} کیلوبایتی ساخته شد"
    stats = output.get("stats")
    if isinstance(stats, dict) and stats:
        return "آمار محاسبه شد"
    # A flat computed result (data's mean/std/... directly) is real work too.
    flat = {
        k: v
        for k, v in output.items()
        if isinstance(v, (int, float)) and not isinstance(v, bool) and k != "ok"
    }
    if flat:
        return f"{_fmt_num(len(flat))} شاخص محاسبه شد"
    return ""


def _fmt_num(value: Any) -> str:
    """A number rendered compactly for a table cell (no fake precision)."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if f == int(f) and abs(f) < 1e15:
        return str(int(f))
    return f"{f:.4f}".rstrip("0").rstrip(".")


def orchestrate(
    registry: ToolRegistry,
    capabilities: list[str],
    *,
    composer: Composer | None = None,
    connector_factory: ConnectorFactory | None = None,
    capability_params: dict[str, dict[str, Any]] | None = None,
    flow: bool = False,
    command: str = "",
) -> Synthesis:
    """Reach a tool for each needed capability and fuse their outputs into one D.

    ``capabilities`` is the list of WHAT the request needs (in order); for each,
    the registry's best tool (highest evidence) is reached through its connector.
    If any capability has no tool, that sub-output is ``ok=False`` and the whole
    synthesis is ``ok=False`` — a missing capability is never papered over.

    The ``composer`` fuses the sub-outputs; the default produces a structured
    bundle so D carries exactly which tool satisfied which capability (auditable).
    ``connector_factory`` overrides the mechanism-derived connector (e.g. to route
    a capability to a custom connector such as ``MediaToolConnector``).
    ``capability_params`` feeds each capability the parameters the caller (or the
    Persian router) specified: {"data": {"operation": "stats", "data": [2, 4]}} —
    so «میانگین ۲ و ۴» computes [2, 4], not a default series.
    """
    fuse = composer if composer is not None else _default_composer
    factory = connector_factory if connector_factory is not None else _default_connector
    sub_outputs: list[SubOutput] = []
    flows: list[str] = []
    last_producer: str | None = None
    last_output: Any = None
    produced_paths: list[str] = []  # every real file this run produced so far
    produced_stats: dict[str, float] = {}  # every computed metric so far (all producers)
    for capability in capabilities:
        tool = registry.best_for(capability)
        call_params = dict((capability_params or {}).get(capability, {}))
        if flow:
            call_params, flow_desc = _flow_params(
                capability, call_params, last_producer, last_output, command,
                tuple(produced_paths), dict(produced_stats),
            )
            if flow_desc:
                flows.append(flow_desc)
        if tool is None:
            sub_outputs.append(
                SubOutput(capability=capability, tool_name="", output=None, ok=False,
                          error=f"no tool can honor '{capability}'")
            )
            last_producer, last_output = None, None
            continue
        start = _perf()
        result = factory(tool).connect(tool.connection, call_params)
        duration_ms = (_perf() - start) * 1000.0
        sub_outputs.append(
            SubOutput(
                capability=capability,
                tool_name=tool.name,
                output=result.output,
                ok=result.ok,
                error=result.error,
                duration_ms=round(duration_ms, 4),
            )
        )
        # Track the last SUCCESSFUL producer so the next consumer can feed on it.
        if result.ok and result.output is not None:
            last_producer, last_output = capability, result.output
            if isinstance(result.output, dict):
                if isinstance(result.output.get("path"), str):
                    produced_paths.append(result.output["path"])
                # Every numeric metric this producer computed — ALL producers
                # accumulate (a consumer like database deserves the whole chain's
                # results, not just the last program's). Only COMPUTING
                # capabilities contribute metrics: an artifact producer's
                # bytes/size is evidence ABOUT the artifact, not content.
                if capability in ("data", "ai", "compute", "vision"):
                    for k, v in result.output.items():
                        if (
                            isinstance(v, (int, float))
                            and not isinstance(v, bool)
                            and k != "ok"
                        ):
                            metric_name = f"{capability}.{k}" if k in produced_stats else k
                            produced_stats[metric_name] = float(v)
        else:
            last_producer, last_output = None, None
        # Record the outcome on the tool's evidence trail so the next synthesis
        # ranks tools by what actually worked (feeds Phase E).
        tool.evidence.append({"succeeded": result.ok, "score": 1.0 if result.ok else 0.0, "note": capability})


    fused = fuse(sub_outputs)
    if isinstance(fused, dict) and flows:
        fused = {**fused, "flows": flows}  # auditable: exactly what flowed
    all_ok = all(s.ok for s in sub_outputs)
    return Synthesis(output=fused, sub_outputs=tuple(sub_outputs), ok=all_ok)


__all__ = ["ConnectorFactory", "OrchestrationError", "SubOutput", "Synthesis", "orchestrate"]