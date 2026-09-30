"""A single registry that maps a capability to its real-tool connector.

The three real effects (media via ffmpeg, archive via gzip, compute via node) each
have a connector. This module gathers them into ONE factory so the whole real-tool
set is reachable through the super-platform's ``orchestrate`` without a caller
writing a bespoke factory per tool. Add a new real tool = add one line here.

It is deliberately a plain capability->connector table: the brain asks for a
capability, gets the connector that produces that real effect.
"""

from __future__ import annotations

from universal_mind.ai_suite import AISuiteConnector
from universal_mind.archive_adapter import ArchiveToolConnector
from universal_mind.chart_suite import ChartSuiteConnector
from universal_mind.clipboard_adapter import ClipboardToolConnector
from universal_mind.compute_adapter import ComputeToolConnector
from universal_mind.connectors import Connector
from universal_mind.data_suite import DataSuiteConnector
from universal_mind.database_suite import DatabaseSuiteConnector
from universal_mind.image_suite import ImageSuiteConnector
from universal_mind.llm_connector import LLMToolConnector
from universal_mind.media_adapter import MediaToolConnector
from universal_mind.notify_adapter import NotifyToolConnector
from universal_mind.csv_suite import CsvSuiteConnector
from universal_mind.zip_suite import ZipSuiteConnector
from universal_mind.excel_suite import ExcelSuiteConnector
from universal_mind.file_search_tool import FileSearchToolConnector
from universal_mind.file_dedupe_tool import FileDedupeToolConnector
from universal_mind.pdfreader_tool import PdfReaderToolConnector
from universal_mind.screenshot_tool import ScreenshotToolConnector
from universal_mind.webfetch_tool import WebFetchToolConnector
from universal_mind.ocr_tool import OcrToolConnector
from universal_mind.speech_tool import SpeechToolConnector
from universal_mind.email_outbox import EmailToolConnector
from universal_mind.pdf_suite import PdfSuiteConnector
from universal_mind.tool_registry import (
    ToolEntry,
    ToolRegistry,
)
from universal_mind.vision_suite import VisionSuiteConnector

# capability -> connector constructor (no-arg), kept in one place.
# The *_Suite entries are integrated PROGRAMS (whole toolboxes), not single ops.
_REAL_CONNECTORS: dict[str, type[Connector]] = {
    "media": MediaToolConnector,
    "archive": ArchiveToolConnector,
    "compute": ComputeToolConnector,
    "notify": NotifyToolConnector,
    "clipboard": ClipboardToolConnector,
    "speech": SpeechToolConnector,         # real Windows SAPI voice (fa-preferred, honest)
    "email": EmailToolConnector,           # real RFC-822 outbox (.eml) + optional SMTP (R44-11)
    "ocr": OcrToolConnector,              # real Windows.Media.Ocr — the platform READS images
    "excel": ExcelSuiteConnector,         # real openpyxl workbooks (the 15th program)
    "webfetch": WebFetchToolConnector,    # real urllib fetch — the 16th program
    "pdfreader": PdfReaderToolConnector, # real pypdf — the 17th: reads PDFs
    "screenshot": ScreenshotToolConnector,  # real ImageGrab — the 18th: sees the screen
    "filesearch": FileSearchToolConnector,  # R53 wave-4 — real disk search (read-only)
    "filededupe": FileDedupeToolConnector,  # R53 wave-5 — SHA-256 duplicates, preview-first
    "csv": CsvSuiteConnector,             # real csv stdlib — the 19th: universal interchange
    "zip": ZipSuiteConnector,             # real zipfile — the 20th: the world's archive format
    "image": ImageSuiteConnector,      # full Pillow surface (convert/resize/crop/rotate/filters/...)
    "pdf": PdfSuiteConnector,          # full reportlab surface (documents/tables/images)
    "chart": ChartSuiteConnector,      # full matplotlib surface (line/bar/pie/hist/scatter)
    "data": DataSuiteConnector,        # full numpy surface (stats/solve/eigen/normalize/correlate)
    "database": DatabaseSuiteConnector,  # full sqlite3 surface (DDL/inserts/queries/tables)
    "ai": AISuiteConnector,            # real ML + signal (sklearn train/fit + scipy fft/peaks)
    "vision": VisionSuiteConnector,    # real computer vision (OpenCV: edges/contours/threshold)
    "llm": LLMToolConnector,           # real OpenAI-compatible chat (R45-15, env-wired)
}


def real_tool_registry() -> ToolRegistry:
    """The registry of every REAL capability the platform ships.

    One entry per integrated program/effect, all absorbable, so the Persian
    layer, the desktop app, the CLI, and the probes all share ONE source of
    truth about what the platform can actually do.
    """
    from universal_mind.tool_registry import (
        ConnectionMechanism,
        ToolConnectionSpec,
        ToolEntry,
        ToolRegistry,
    )

    reg = ToolRegistry()
    for capability in sorted(_REAL_CONNECTORS):
        reg.register(
            ToolEntry(
                name=f"real::{capability}",
                capability=capability,
                connection=ToolConnectionSpec(
                    mechanism=ConnectionMechanism.SUBPROCESS,
                    command=f"python -m universal_mind.cli run {capability}",
                ),
                absorbable=True,
            )
        )
    return reg


def real_connector_factory(tool: ToolEntry) -> Connector:
    """Return the real-tool connector for a tool's capability.

    Falls back to the mechanism-derived connector for any capability not backed by
    a real tool, so the factory is safe to use as a universal ``connector_factory``
    in ``orchestrate``.
    """
    constructor = _REAL_CONNECTORS.get(tool.capability)
    if constructor is not None:
        return constructor()
    from universal_mind.connectors import connector_for

    return connector_for(tool.connection_mechanism)


__all__ = ["real_connector_factory", "real_tool_registry"]