"""R79 LITE — the door must stay open without the heavy engines.

The 88MB Full installer ships cv2+scipy; a Lite build drops them (180MB
unpacked). The LAW this pins: a missing heavy library may never break the
conversational door, and the capability it powers must REFUSE BY NAME
(honest, actionable) — never a crash, never a fabricated image.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORTABLE = ROOT / "build" / "portable"
PY = PORTABLE / "python" / "python.exe"
SP = PORTABLE / "python" / "Lib" / "site-packages"


def test_no_cv2_scipy_on_this_machine_is_not_a_crash(monkeypatch) -> None:
    """If the heavy engines are present (Full build), rename them away for
    the moment of the test — the door must answer everything else."""
    import os

    disabled: list[Path] = []
    for name in ("cv2", "scipy", "scipy.libs"):
        d = SP / name
        if d.exists():
            d.rename(SP / (name + "_off"))
            disabled.append(d)
    try:
        env = {k: v for k, v in os.environ.items()
               if k not in ("PYTHONPATH", "PYTHONHOME")}
        env["UM_MUTE"] = "1"
        code = (
            "import sys; sys.path.insert(0, r'" + str(PORTABLE / "app") + "'); "
            "from universal_mind.persian_router import route_and_run; "
            "p = route_and_run('ساعت چنده؟'); "
            "print('OK' if p.get('ok') else 'DEAD')"
        )
        r = subprocess.run([str(PY), "-c", code], capture_output=True,
                           text=True, timeout=120, env=env)
        assert "OK" in r.stdout, r.stdout + r.stderr
    finally:
        for d in disabled:
            (SP / (d.name + "_off")).rename(d)


def test_the_vision_capability_refuses_by_name_without_cv2(tmp_path) -> None:
    """Direct connector check (no rename needed — we ask _have_cv2 to be
    honest on THIS machine): with cv2 present the vision path works; the
    refusal shape is what the Lite machine sees. Here we pin the refusal
    TEXT by calling the connector with cv2 import blocked in-process."""
    sys.path.insert(0, str(ROOT))
    import importlib
    import universal_mind.vision_suite as vs

    reload = importlib.reload(vs)
    # block cv2 inside this process, then reload the module fresh
    import builtins

    real_import = builtins.__import__

    def _no_cv2(name, *a, **k):
        if name == "cv2":
            raise ImportError("blocked for the Lite proof")
        return real_import(name, *a, **k)

    builtins.__import__ = _no_cv2
    try:
        vs2 = importlib.reload(vs)
        assert vs2._have_cv2() is False
        conn = vs2.VisionSuiteConnector()
        out = conn.connect(None, {"operation": "stats"})
        assert out.ok is False
        assert "OpenCV" in str(getattr(out, "error", "")) or "OpenCV" in str(out)
    finally:
        builtins.__import__ = real_import
        importlib.reload(vs)  # restore the real state
