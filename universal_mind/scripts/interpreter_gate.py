"""R48-9/9b — THE INTERPRETER GATE: verify refuses to bless a wrong-python run.

The outage lesson: `python` on PATH is whatever survived the last install
spree. verify.py now (a) resolves the REAL interpreter the way scripts/
py.sh does, (b) runs everything through it, and (c) FAILS LOUDLY with the
versions printed when the active interpreter cannot import the platform's
own dependencies. A green VERIFY on a dead interpreter is a lie.
"""

from __future__ import annotations

import shutil
import subprocess
import sys


def resolve_interpreter() -> tuple[str, str]:
    """The platform's real interpreter + a one-line proof of identity."""
    # explicit override first
    import os

    override = os.environ.get("UM_PYTHON", "")
    homep = os.environ.get("LOCALAPPDATA") or ""
    candidates = [
        override,
        f"{homep}/hermes/hermes-agent/venv/Scripts/python.exe"
        if homep else "",
        "C:/Users/EliteBook/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe",
    ]
    for exe in candidates:
        if not exe:
            continue
        if shutil.which(exe) is None and not exe.lower().endswith(".exe"):
            exe = shutil.which(exe) or ""
            if not exe:
                continue
        try:
            probe = subprocess.run(
                [exe, "-c", "import numpy, pytest, sklearn"],
                capture_output=True, timeout=60)
            if probe.returncode == 0:
                ver_p = subprocess.run(
                    [exe, "-c", "import sys; print(sys.version.split()[0])"],
                    capture_output=True, text=True, timeout=30)
                return exe, (ver_p.stdout.strip() or "?")
        except (OSError, subprocess.SubprocessError):
            continue
    # py launcher
    launcher = shutil.which("py")
    if launcher:
        for minor in (11, 12, 13):
            try:
                probe = subprocess.run(
                    ["py", f"-3.{minor}", "-c", "import numpy, pytest, sklearn"],
                    capture_output=True, timeout=60)
                if probe.returncode == 0:
                    ver_p = subprocess.run(
                        ["py", f"-3.{minor}", "-c",
                         "import sys; print(sys.version.split()[0])"],
                        capture_output=True, text=True, timeout=30)
                    exe_p = subprocess.run(
                        ["py", f"-3.{minor}", "-c", "import sys; print(sys.executable)"],
                        capture_output=True, text=True, timeout=30)
                    return exe_p.stdout.strip(), ver_p.stdout.strip()
            except (OSError, subprocess.SubprocessError):
                continue
    return "", ""


def interpreter_gate() -> tuple[bool, str]:
    """GREEN when the CURRENT interpreter carries the platform's deps."""
    can = subprocess.run(
        [sys.executable, "-c", "import numpy, pytest, sklearn"],
        capture_output=True, timeout=60)
    ver = ".".join(map(str, sys.version_info[:3]))
    if can.returncode == 0:
        return True, f"interpreter {ver} carries the platform's dependencies"
    real, real_ver = resolve_interpreter()
    if real:
        return False, (
            f"این مفسر ({ver}) وابستگیهای پلتفرم را ندارد. "
            f"مفسر درست: {real} ({real_ver}) — با scripts/py.sh یا UM_PYTHON بیایید."
        )
    return False, (
        f"هیچ مفسر مجازی با numpy/pytest/sklearn پیدا نشد (فعلی: {ver}). "
        "UM_PYTHON را ست کنید."
    )


if __name__ == "__main__":
    ok, msg = interpreter_gate()
    print(("PASS " if ok else "FAIL ") + msg)
    raise SystemExit(0 if ok else 3)
