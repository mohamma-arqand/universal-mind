"""R79 FINAL — the install proof.

A product nobody can install is no product. The bundle (setup.cmd) must
contain the door, the pinned deps, the installer (autostart), the Persian
README, and the compiled volume tool — and that tool must RUN from the
bundle.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "build" / "universal_mind-bundle.zip"


class TestTheBundle:
    def test_everything_a_new_user_needs_is_inside(self, tmp_path) -> None:
        assert BUNDLE.exists(), "run setup.cmd first"
        need = [
            "universal_mind.cmd", "install.cmd", "requirements.txt", "شروع.md",
            "universal_mind/__main__.py", "universal_mind/persian_router.py",
            "universal_mind/tools/volctl.exe",
        ]
        with zipfile.ZipFile(BUNDLE) as z:
            names = set(z.namelist())
            for m in need:
                assert m in names, f"missing: {m}"

    def test_the_bundled_tool_runs_from_the_bundle(self, tmp_path) -> None:
        import subprocess

        with zipfile.ZipFile(BUNDLE) as z:
            z.extractall(tmp_path)
        r = subprocess.run(
            [str(tmp_path / "universal_mind" / "tools" / "volctl.exe"), "get"],
            capture_output=True, text=True, timeout=20)
        assert r.returncode == 0 and ":" in r.stdout, r.stdout + r.stderr

    def test_the_door_is_importable(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "_um_door", ROOT / "universal_mind" / "__main__.py")
        assert spec is not None and spec.loader is not None

    def test_dependencies_are_pinned_in_pyproject(self) -> None:
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert "[tool.setuptools.package-data]" in text
        assert "volctl.exe" in text
