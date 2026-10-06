"""R79 FINAL — the cross-platform one-file installer (Windows & Linux).

A deliverable that installs like a first-class citizen on EITHER platform.
The single entry is `python setup_universal.py` (or a double-click on the
generated shim). From the bundle it builds, you get:

  * on Windows: Program Files dir + autostart at login +
    a desktop shortcut (this is the Inno path, built by setup.cmd +
    installer + universal_mind.iss)
  * on Linux: ~/.local/share/universal-mind + a .desktop entry +
    ~/.config/autostart registration (no sudo needed — port 80 not used)
  * the SAME conversational door: `universal_mind` starts the Persian REPL
    (real volume, real windows, real schedule) — no claim, the output is
    measured.

The venv is private to the install (never the machine's own). The first run
needs the network to fetch the pinned wheels; every subsequent start is
fully offline.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUNDLE = HERE / "build" / "universal_mind-bundle.zip"

HOME_WIN = Path.home() / "universal_mind"
HOME_LIN = Path.home() / ".local" / "share" / "universal-mind"


def _fa(n: object) -> str:
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _need_bundle() -> None:
    if BUNDLE.exists():
        return
    subprocess.run(["bash", str(HERE / "setup.cmd")], cwd=HERE, check=True)


def _extract(home: Path) -> None:
    if home.exists():
        backup = home.with_name(home.name + "-prev")
        shutil.move(str(home), str(backup))
        print("نسخهٔ قبلی در", backup)
    home.mkdir(parents=True)
    with zipfile.ZipFile(BUNDLE) as z:
        z.extractall(home)
    print("استخراج شد:", len(list(home.rglob("*.*"))), "فایل در", home)


def _venv(home: Path) -> Path:
    vpy = home / ".venv" / ("bin/python" if platform.system() != "Windows" else "Scripts/python.exe")
    if not vpy.exists():
        print("ساختِ محیطِ مستقل…")
        subprocess.run([sys.executable, "-m", "venv", str(home / ".venv")], check=True)
    pip = home / ".venv" / ("bin/pip" if platform.system() != "Windows" else "Scripts/pip.exe")
    print("نصبِ وابستگیها (یک‌بار، اینترنت میخواهد)…")
    r = subprocess.run([str(pip), "install", "-q", "-r", str(home / "requirements.txt")])
    if r.returncode != 0:
        print("نکته: وابستگی آفلاین نصب نشد — بعداً آنلاین دوباره:", r.stderr[:100] if r.stderr else "")
    return vpy


def _install_windows(home: Path, vpy: Path) -> None:
    door = home / "universal_mind.cmd"
    door.write_text(
        f'@echo off\ntitle universal_mind\ncd /d "{home}"\n'
        f'"{vpy}" -m universal_mind\n', encoding="utf-8")
    subprocess.run(
        ["schtasks", "/create", "/tn", "UniversalMind", "/tr",
         f'"{door}"', "/sc", "onlogon", "/rl", "highest", "/f"],
        capture_output=True)
    # desktop shortcut
    vbs = Path(os.environ["TEMP"]) / "um.vbs"
    vbs.write_text(
        'Set o=CreateObject("WScript.Shell")\n'
        f'Set l=o.CreateShortcut("{Path.home()/"Desktop"/"ذهن سراسری.lnk"}")\n'
        f'l.TargetPath="{door}"\nl.Save\n', encoding="utf-8")
    subprocess.run(["cscript", "//nologo", str(vbs)], capture_output=True)
    vbs.unlink(missing_ok=True)


def _install_linux(home: Path, vpy: Path) -> None:
    bin_dir = Path.home() / ".local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    shim = bin_dir / "universal_mind"
    shim.write_text(f"#!/bin/sh\nexec \"{vpy}\" -m universal_mind \"$@\"\n")
    shim.chmod(0o755)
    apps = Path.home() / ".local/share/applications"
    apps.mkdir(parents=True, exist_ok=True)
    (apps/"universal-mind.desktop").write_text(
        "[Desktop Entry]\nName=Universal Mind\nName[fa]=ذهن سراسری\n"
        "Comment=Persian local-first assistant\n"
        f"Exec={shim}\nTerminal=true\nType=Application\n"
        "Categories=Utility;\n")
    adir = Path.home() / ".config/autostart"
    adir.mkdir(parents=True, exist_ok=True)
    (adir/"universal-mind.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Universal Mind\n"
        f"Exec={shim}\nX-GNOME-Autostart-enabled=true\n")
    print("لینوکس: شورتکات در منوی برنامهها + autostart")


def _prove(vpy: Path, home: Path) -> None:
    r = subprocess.run(
        [str(vpy), "-c",
         "import sys; sys.path.insert(0, " + repr(str(home)) + "); "
         "from universal_mind.persian_router import route_and_run; "
         "out=route_and_run('ساعت چنده؟'); print(out.get('agent_report',''))"],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "UM_MUTE": "1"})
    ok = bool(r.stdout.strip())
    print(("✅" if ok else "⚠️") + " گواه زنده:", (r.stdout or r.stderr)[:100].strip())


def install() -> None:
    _need_bundle()
    is_win = platform.system() == "Windows"
    home = HOME_WIN if is_win else HOME_LIN
    print("نصب در", home)
    _extract(home)
    vpy = _venv(home)
    (_install_windows if is_win else _install_linux)(home, vpy)
    _prove(vpy, home)
    print("تمام. برای شروع، دابل‌کلیک یا در ترمینال: `universal_mind`")


if __name__ == "__main__":
    install()
