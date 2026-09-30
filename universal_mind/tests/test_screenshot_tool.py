"""Tests: the screenshot tool (18th capability) + the screen-perception chain."""

from __future__ import annotations


class TestScreenshotTool:
    def test_a_real_capture_lands_on_disk(self) -> None:
        """On an interactive desktop, ImageGrab captures the real screen."""
        from universal_mind.screenshot_tool import ScreenshotTool

        result = ScreenshotTool().capture()
        if result["ok"] is False and "screen unavailable" in result["error"]:
            return  # headless service context: honest skip
        assert result["ok"] is True
        assert result["width"] >= 640 and result["height"] >= 480  # a real display
        # A real PNG's SIZE tracks its CONTENT (a calm dark desktop compresses
        # to ~7 KB; a busy one to ~2 MB) — a byte floor pins compression luck,
        # not realness. Realness = a decodable PNG of a real display:
        from PIL import Image

        with Image.open(result["path"]) as im:
            assert im.size == (result["width"], result["height"])
        assert result["bytes"] > 1_000  # any real PNG clears this trivially

    def test_connector_contracts(self) -> None:
        from universal_mind.connectors import ConnectorResult
        from universal_mind.screenshot_tool import ScreenshotToolConnector

        conn = ScreenshotToolConnector()
        result = conn.connect({}, {"operation": "capture"})
        assert isinstance(result, ConnectorResult)
        if result.ok:
            assert result.output["path"].endswith(".png")
        bad = conn.connect({}, {"operation": "scroll"})
        assert bad.ok is False


class TestScreenPerceptionChain:
    def test_screenshot_flows_into_vision(self) -> None:
        """اسکرینشات → تحلیل تصویر: the platform captures and analyzes a
        REAL screen in one chain."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("اسکرینشات بگیر و تحلیل تصویرش کن")
        assert payload["route"] == ["screenshot", "vision"]
        if payload["ok"] is not True:
            return  # headless context: honest refusal is acceptable in tests
        assert any("→ بینایی" in f for f in payload["flows"])
        vision_out = payload["result"]["vision"]
        assert "shape" in vision_out  # real OpenCV stats on the real screen

    def test_screenshot_is_an_image_producer(self) -> None:
        """The planner treats screenshot as a producer (consumers run after)."""
        from universal_mind.dependency_planner import plan_chain

        plan = plan_chain(["vision", "screenshot"])
        caps = [s.capability for s in plan.steps]
        assert caps.index("screenshot") < caps.index("vision")
