"""Tests for orchestrated synthesis (super-platform Phase D)."""

from __future__ import annotations

from universal_mind.orchestration import SubOutput, orchestrate
from universal_mind.tool_registry import (
    ConnectionMechanism,
    ToolConnectionSpec,
    ToolEntry,
    ToolRegistry,
)


def _entry(name: str, capability: str, command: str = "echo hello") -> ToolEntry:
    return ToolEntry(
        name=name,
        capability=capability,
        connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command=command),
        absorbable=True,
    )


def _registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(_entry("a", "transcode", "echo transcode_out"))
    reg.register(_entry("b", "send_email", "echo email_out"))
    return reg


def test_orchestrate_fuses_multiple_tools_into_one_artifact() -> None:
    reg = _registry()
    syn = orchestrate(reg, ["transcode", "send_email"])
    assert syn.ok is True
    # D is a single fused artifact keyed by capability, produced by NO single tool.
    assert syn.output["synthesized_from"]["transcode"] == "transcode_out"
    assert syn.output["synthesized_from"]["send_email"] == "email_out"
    assert len(syn.sub_outputs) == 2


def test_missing_capability_fails_the_whole_synthesis() -> None:
    reg = _registry()
    syn = orchestrate(reg, ["transcode", "nonexistent_capability"])
    assert syn.ok is False
    # The missing capability is an explicit failed sub-output, not a fake result.
    missing = [s for s in syn.sub_outputs if s.ok is False]
    assert len(missing) == 1
    assert missing[0].capability == "nonexistent_capability"
    assert "no tool" in missing[0].error


def test_injectable_composer_controls_the_fusion() -> None:
    reg = _registry()

    def join(sub_outputs: list[SubOutput]) -> str:
        return " + ".join(str(s.output) for s in sub_outputs if s.ok)

    syn = orchestrate(reg, ["transcode", "send_email"], composer=join)
    assert syn.output == "transcode_out + email_out"


def test_single_capability_is_still_a_synthesis() -> None:
    reg = _registry()
    syn = orchestrate(reg, ["transcode"])
    assert syn.ok is True
    assert syn.output["synthesized_from"]["transcode"] == "transcode_out"


def test_best_tool_is_chosen_by_evidence() -> None:
    reg = ToolRegistry()
    rookie = _entry("rookie", "transcode", "echo rookie_out")
    proven = _entry("proven", "transcode", "echo proven_out")
    proven.record_evidence(True, 1.0)
    reg.register(rookie)
    reg.register(proven)
    syn = orchestrate(reg, ["transcode"])
    # The proven tool (higher evidence) is the one reached.
    assert syn.sub_outputs[0].tool_name == "proven"
    assert syn.output["synthesized_from"]["transcode"] == "proven_out"


def _real_registry() -> ToolRegistry:
    """The REAL registered capabilities (the shipped super-platform surface)."""
    from universal_mind.real_tool_registry import real_tool_registry

    return real_tool_registry()


class TestDataflowSynthesis:
    """flow=True: one program's real output becomes the next program's input."""

    def test_chart_feeds_pdf_for_real(self) -> None:
        """chart → pdf: the PDF genuinely embeds the chart that was just made."""
        from universal_mind.real_tool_registry import real_connector_factory

        syn = orchestrate(_real_registry(), ["chart", "pdf"],
                          connector_factory=real_connector_factory, flow=True)
        assert syn.ok is True
        # The flow is recorded honestly in the bundle.
        assert syn.output["flows"] == ["chart → pdf (گزارش فارسی با نمودار درونش)"]
        # And the PDF really is an image-bearing PDF (bytes grew by the image).
        assert syn.output["synthesized_from"]["pdf"]["bytes"] > 1000

    def test_explicit_params_win_over_flow(self) -> None:
        """The caller's explicit operation is never overridden by inference."""
        from universal_mind.real_tool_registry import real_connector_factory

        syn = orchestrate(
            _real_registry(), ["chart", "pdf"],
            connector_factory=real_connector_factory, flow=True,
            capability_params={"pdf": {"operation": "document", "title": "گزارش"}},
        )
        assert syn.ok is True
        assert syn.output.get("flows", []) == []  # no flow: explicit intent wins

    def test_flow_off_by_default(self) -> None:
        """Without flow=True, programs stay independent (backward compatible)."""
        from universal_mind.real_tool_registry import real_connector_factory

        syn = orchestrate(_real_registry(), ["chart", "pdf"],
                          connector_factory=real_connector_factory)
        assert syn.ok is True
        assert "flows" not in syn.output

    def test_persian_rtl_is_upgraded_to_report_when_image_flows(self) -> None:
        """The ONE sanctioned upgrade: a Persian rtl report embeds the just-made
        chart; any other explicit operation is untouched."""
        from universal_mind.real_tool_registry import real_connector_factory

        syn = orchestrate(
            _real_registry(), ["chart", "pdf"],
            connector_factory=real_connector_factory, flow=True,
            capability_params={"pdf": {"operation": "persian_rtl", "title": "گزارش"}},
        )
        assert syn.ok is True
        assert syn.output["flows"] == ["chart → pdf (گزارش فارسی با نمودار درونش)"]
        # bigger than a text-only RTL pdf because the chart image is inside.
        assert syn.output["synthesized_from"]["pdf"]["bytes"] > 20000

    def test_data_feeds_pdf_stats_table_for_real(self) -> None:
        """data → pdf: the computed statistics become a REAL table inside the
        Persian report (bytes grow by the rendered table)."""
        from universal_mind.real_tool_registry import real_connector_factory

        syn = orchestrate(
            _real_registry(), ["data", "pdf"],
            connector_factory=real_connector_factory, flow=True,
            capability_params={
                "data": {"operation": "stats", "data": [10.0, 20.0, 30.0]},
                "pdf": {"operation": "persian_rtl"},
            },
        )
        assert syn.ok is True
        assert syn.output["flows"] == ["data → pdf (جدول آمار واقعی درون گزارش)"]
        # the report with a real stats table is bigger than the text-only one
        assert syn.output["synthesized_from"]["pdf"]["bytes"] > 35500

    def test_failed_producer_never_flows(self) -> None:
        """A failed producer's (non-)output never becomes the next input."""
        from universal_mind.real_tool_registry import real_connector_factory

        syn = orchestrate(_registry(), ["nonexistent", "pdf"],
                          connector_factory=real_connector_factory, flow=True)
        assert syn.ok is False
        assert syn.output.get("flows", []) == []


def test_orchestration_records_evidence_on_tools() -> None:
    reg = _registry()
    orchestrate(reg, ["transcode", "send_email"])
    # Each tool now carries one evidence point from this run (feeds Phase E).
    for tool in reg.tools_for("transcode") + reg.tools_for("send_email"):
        assert len(tool.evidence) == 1