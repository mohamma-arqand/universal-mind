"""Coverage for real_tools.py's remaining branches (health/404/unknown-op/url)."""

from __future__ import annotations

import json
import urllib.request

import pytest

from universal_mind.io.real_tools import RealToolProvider, ToolService


def test_url_property_raises_before_start() -> None:
    service = ToolService()
    with pytest.raises(RuntimeError):
        _ = service.url


def test_url_property_after_start() -> None:
    service = ToolService()
    url = service.start()
    try:
        assert service.url == url
    finally:
        service.stop()


def test_tool_service_health_endpoint() -> None:
    service = ToolService()
    url = service.start()
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        assert body == {"status": "ok"}
    finally:
        service.stop()


def test_tool_service_unknown_path_returns_404() -> None:
    service = ToolService()
    url = service.start()
    try:
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"{url}/nope", timeout=5)
        assert exc_info.value.code == 404
    finally:
        service.stop()


def test_unknown_op_returns_zero() -> None:
    service = ToolService()
    url = service.start()
    try:
        provider = RealToolProvider(url)
        result = provider.compute("sqrt", [4.0])
        assert result.output == 0.0
        assert result.via_fallback is False
    finally:
        service.stop()


def test_product_with_no_args_returns_zero() -> None:
    service = ToolService()
    url = service.start()
    try:
        provider = RealToolProvider(url)
        # product requires args; empty -> falls to else branch -> 0.0
        result = provider.compute("product", [])
        assert result.output == 0.0
    finally:
        service.stop()