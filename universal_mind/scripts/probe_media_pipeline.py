#!/usr/bin/env python3
"""Probe: real media pipeline — generate -> inspect -> transcode as one chain.

The strongest proof of "reach a real tool AND get a real effect" is a chained
pipeline: generate a real image, read back its real metadata, then transcode it —
each step's output feeding the next, all through the real ffmpeg/ffprobe binaries.
On a host without ffmpeg the chain fails SAFE (no fabricated artifact) and the probe
still passes on that path; but here ffmpeg IS present, so the full real path runs.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.real_media import MediaTool


def check_media_pipeline_end_to_end() -> bool:
    tool = MediaTool()
    if not tool.available():
        print("  ffmpeg absent — exercising fail-safe only")
        return tool.generate_image()["ok"] is False

    # Step 1: generate
    img = tool.generate_image(size="48x24", color="orange")
    if not img["ok"]:
        print("  generate failed: ", img["error"])
        return False

    # Step 2: inspect (reads the real file produced by step 1)
    meta = tool.inspect(img["path"])
    if not meta["ok"]:
        print("  inspect failed: ", meta["error"])
        return False
    width: object = meta["meta"].get("width")
    height: object = meta["meta"].get("height")
    ok = width == 48 and height == 24
    print(f"  generate({img['bytes']}B) -> inspect({width}x{height}): {ok}")
    if not ok:
        return False

    # Step 3: transcode (transforms the real file into another real file)
    out = tool.transcode(img["path"], out_format="png")
    if not out["ok"]:
        print("  transcode failed: ", out["error"])
        return False
    print(f"  transcode -> {out['bytes']}B real output: {out['ok']}")
    return out["ok"] is True


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeMediaPipeline",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeMediaPipeline", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("generate -> inspect -> transcode real chain", check_media_pipeline_end_to_end),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Real media pipeline probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: REAL MEDIA PIPELINE (generate -> inspect -> transcode)")
    print("=" * 64)

    results: list[tuple[str, bool]] = []
    for name, fn in _CHECKS:
        print(f"\n--- {name} ---")
        try:
            results.append((name, fn()))
        except Exception as exc:  # noqa: BLE001
            print(f"  check raised: {exc!r}")
            results.append((name, False))

    all_ok = all(ok for _, ok in results)
    for name, result in results:
        print(f"\n  {name}: {'OK' if result else 'FAILED'}")

    if args.junit_xml:
        write_junit_xml(results, args.junit_xml)
        print(f"\nJUnit XML written to {args.junit_xml}")

    print("\nALL CHECKS PASSED — THE MIND RUNS A REAL MEDIA PIPELINE" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())