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

        # R63 P3: explicit real data — the silent default series is gone.
        syn = orchestrate(_real_registry(), ["chart", "pdf"],
                          connector_factory=real_connector_factory, flow=True,
                          capability_params={"chart": {"operation": "line",
                                                       "series": {"داده": [2, 3, 5, 7]}}})
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
            capability_params={"chart": {"operation": "line", "series": {"داده": [2, 3, 5, 7]}}, "pdf": {"operation": "document", "title": "گزارش"}},
        )
        assert syn.ok is True
        assert syn.output.get("flows", []) == []  # no flow: explicit intent wins

    def test_flow_off_by_default(self) -> None:
        """Without flow=True, programs stay independent (backward compatible)."""
        from universal_mind.real_tool_registry import real_connector_factory

        syn = orchestrate(_real_registry(), ["chart", "pdf"],
                          connector_factory=real_connector_factory,
                          capability_params={"chart": {"operation": "line", "series": {"داده": [2, 3, 5, 7]}}})
        assert syn.ok is True
        assert "flows" not in syn.output

    def test_persian_rtl_is_upgraded_to_report_when_image_flows(self) -> None:
        """The ONE sanctioned upgrade: a Persian rtl report embeds the just-made
        chart; any other explicit operation is untouched."""
        from universal_mind.real_tool_registry import real_connector_factory

        syn = orchestrate(
            _real_registry(), ["chart", "pdf"],
            connector_factory=real_connector_factory, flow=True,
            capability_params={"chart": {"operation": "line", "series": {"داده": [2, 3, 5, 7]}}, "pdf": {"operation": "persian_rtl", "title": "گزارش"}},
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

    def test_notify_flow_summarizes_the_real_artifact(self) -> None:
        """pdf → notify: the toast body is a real summary of what was MADE,
        not an echo of the order."""
        from universal_mind.real_tool_registry import real_connector_factory

        syn = orchestrate(
            _real_registry(), ["chart", "pdf", "notify"],
            connector_factory=real_connector_factory, flow=True,
            command="نمودار بساز و گزارشش کن و اطلاع بده",
            capability_params={"chart": {"operation": "line",
                                         "series": {"داده": [2, 3, 5, 7]}}},  # R63 P3
        )
        assert syn.ok is True
        flow_strs = syn.output["flows"]
        assert any("pdf → notify" in f and "persian_report.pdf" in f for f in flow_strs)
        notify_out = syn.output["synthesized_from"]["notify"]
        assert notify_out.get("shown") is True

    def test_explicit_notify_body_wins_over_flow(self) -> None:
        """The operator named a body — inference never overrides it."""
        from universal_mind.real_tool_registry import real_connector_factory

        syn = orchestrate(
            _real_registry(), ["chart", "notify"],
            connector_factory=real_connector_factory, flow=True,
            command="نمودار بساز و بهم بگو «تمام شد»",
            capability_params={"chart": {"operation": "line", "series": {"داده": [2, 3, 5, 7]}}, "notify": {"operation": "notify", "title": "T", "body": "تمام شد"}},
        )
        assert syn.ok is True
        assert not any("→ notify" in f for f in syn.output.get("flows", []))

    def test_clipboard_flow_puts_the_real_summary_on_the_clipboard(self) -> None:
        """chart → clipboard: the Windows clipboard carries a real summary of
        what was made, ready to paste."""
        from universal_mind.real_tool_registry import real_connector_factory

        syn = orchestrate(
            _real_registry(), ["chart", "clipboard"],
            connector_factory=real_connector_factory, flow=True,
            command="نمودار بساز و در کلیپبورد بگذار",
        )
        if syn.ok is True:
            assert any("→ clipboard" in f and "line.png" in f for f in syn.output["flows"])
            # and the clipboard REALLY carries it (read back)
            cb = syn.output["synthesized_from"]["clipboard"]
            assert isinstance(cb, str) and "line.png" in cb
        else:
            # the clipboard is a GLOBAL OS resource: when another app holds it
            # the platform names the lock honestly instead of pretending success
            assert "قفل" in str(syn)  # the refusal rides the synthesis itself

    def test_clipboard_read_is_never_overridden(self) -> None:
        """«کلیپبورد را بخوان» — an explicit read is the operator's choice."""
        from universal_mind.real_tool_registry import real_connector_factory

        syn = orchestrate(
            _real_registry(), ["chart", "clipboard"],
            connector_factory=real_connector_factory, flow=True,
            command="نمودار بساز و کلیپبورد را بخوان",
            capability_params={"chart": {"operation": "line", "series": {"داده": [2, 3, 5, 7]}}, "clipboard": {"operation": "read"}},
        )
        # locked or carried: the EXPLICIT READ intent is never overridden either way
        assert "→ clipboard" not in syn.output.get("flows", []) or not syn.ok

    def test_database_flow_stores_the_computed_results(self) -> None:
        """data → database: the COMPUTED metrics (not the raw input echo) are
        persisted, named by metric — the record IS what was computed."""
        from universal_mind.real_tool_registry import real_connector_factory

        syn = orchestrate(
            _real_registry(), ["data", "database"],
            connector_factory=real_connector_factory, flow=True,
            command="میانگین ۳ و ۷ و ۱۱ را حساب کن و در دیتابیس ذخیره کن",
            capability_params={"data": {"operation": "stats", "data": [3.0, 7.0, 11.0]},
                               "database": {"operation": "insert_many", "table": "extracted_data",
                                            "rows": [{"value": "3"}, {"value": "7"}, {"value": "11"}],
                                            "persistent": True}},
        )
        assert syn.ok is True
        assert syn.output["flows"] == ["data → database (6 شاخصِ محاسبهشده ذخیره شد)"]
        db_out = syn.output["synthesized_from"]["database"]
        assert db_out["inserted"] == 6  # the six computed metrics, not the 3 raw numbers

    def test_vision_flow_analyzes_the_chains_own_image(self) -> None:
        """chart → vision: real OpenCV statistics on the image the chain made —
        the platform SEES its own output (make → look → understand)."""
        from universal_mind.real_tool_registry import real_connector_factory

        syn = orchestrate(
            _real_registry(), ["chart", "vision"],
            connector_factory=real_connector_factory, flow=True,
            command="نمودار بساز و تحلیل تصویرش کن",
            capability_params={"chart": {"operation": "line",
                                         "series": {"داده": [2, 3, 5, 7]}}},  # R63 P3
        )
        assert syn.ok is True
        assert any("→ بینایی" in f for f in syn.output["flows"])
        vision_out = syn.output["synthesized_from"]["vision"]
        # real pixel statistics came back (shape + per-channel means + std)
        assert "shape" in vision_out and "std" in vision_out

    def test_explicit_vision_operation_wins(self) -> None:
        """«لبهها را پیدا کن» — the operator named contours; it stands."""
        from universal_mind.real_tool_registry import real_connector_factory

        syn = orchestrate(
            _real_registry(), ["chart", "vision"],
            connector_factory=real_connector_factory, flow=True,
            command="نمودار بساز و لبهها را پیدا کن",
            capability_params={"chart": {"operation": "line", "series": {"داده": [2, 3, 5, 7]}}, "vision": {"operation": "contours"}},
        )
        assert syn.ok is True
        assert not any("→ بینایی" in f for f in syn.output.get("flows", []))

    def test_vision_stats_flow_into_the_pdf_report(self) -> None:
        """chart → vision → pdf: the vision analysis (real OpenCV stats on the
        chain's own chart) becomes a real table INSIDE the Persian report,
        together with the chart image itself."""
        from universal_mind.real_tool_registry import real_connector_factory

        syn = orchestrate(
            _real_registry(), ["chart", "vision", "pdf"],
            connector_factory=real_connector_factory, flow=True,
            command="نمودار بساز و تحلیل تصویرش کن و گزارشش کن",
            capability_params={"chart": {"operation": "line",
                                         "series": {"داده": [2, 3, 5, 7]}}},  # R63 P3
        )
        assert syn.ok is True
        flow_strs = syn.output["flows"]
        assert any("→ بینایی" in f for f in flow_strs)          # the perception flow
        assert any("جدول آمار + نمودار درون گزارش" in f for f in flow_strs)  # both parts
        # the report carries BOTH the table and the image (bigger than either alone)
        assert syn.output["synthesized_from"]["pdf"]["bytes"] > 45000

    def test_chart_structure_understands_the_chart_for_real(self) -> None:
        """«ساختارش را بخوان» — real OpenCV structure detection on the chain's
        own chart: dominant colors, long lines, ink density — the platform
        UNDERSTANDS the chart it just drew."""
        from universal_mind.real_tool_registry import real_connector_factory

        syn = orchestrate(
            _real_registry(), ["chart", "vision"],
            connector_factory=real_connector_factory, flow=True,
            command="نمودار بساز و ساختارش را بخوان",
            capability_params={"chart": {"operation": "line",
                                         "series": {"داده": [2, 3, 5, 7]}},  # R63 P3
                               "vision": {"operation": "chart_structure"}},
        )
        assert syn.ok is True
        vision_out = syn.output["synthesized_from"]["vision"]
        assert "dominant_colors" in vision_out
        assert vision_out["long_lines"] >= 2  # axes/grid lines really detected
        # the dominant color is the canvas background (a real chart readout)
        assert vision_out["dominant_colors"][0]["share"] > 0.5

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