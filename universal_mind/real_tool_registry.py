"""A single registry that maps a capability to its real-tool connector.

The three real effects (media via ffmpeg, archive via gzip, compute via node) each
have a connector. This module gathers them into ONE factory so the whole real-tool
set is reachable through the super-platform's ``orchestrate`` without a caller
writing a bespoke factory per tool. Add a new real tool = add one line here.

It is deliberately a plain capability->connector table: the brain asks for a
capability, gets the connector that produces that real effect.
"""

from __future__ import annotations

from universal_mind.archive_adapter import ArchiveToolConnector
from universal_mind.compute_adapter import ComputeToolConnector
from universal_mind.connectors import Connector
from universal_mind.media_adapter import MediaToolConnector
from universal_mind.tool_registry import ToolEntry

# capability -> connector constructor (no-arg), kept in one place.
_REAL_CONNECTORS: dict[str, type[Connector]] = {
    "media": MediaToolConnector,
    "archive": ArchiveToolConnector,
    "compute": ComputeToolConnector,
}


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


__all__ = ["real_connector_factory"]