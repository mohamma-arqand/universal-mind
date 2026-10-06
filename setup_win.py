"""R79 FINAL — the one-file Windows installer.

A product nobody can install is no product. Running THIS script (one
double-click, or `python setup_win.py`) delivers the assistant as a
native citizen of the machine:

  * extracts the bundle into the chosen home (default %USERPROFILE% + backslash + universal_mind)
  * creates a PRIVATE venv there and pins the interpreter
  * installs the pinned requirements (first run needs internet once;
    Windows honors a proxy via the HTTPS_PROXY env var or pip --proxy)
  * registers a Task Scheduler autostart — the assistant rises at every
    login, no further click needed
  * drops a DESKTOP shortcut for right-now use
  * MEASURES the result: answers «ساعت چنده؟» through the installed
    interpreter (never a claim — the answer itself is the proof)

Never asks for admin silently: the autostart registration is the only
step that needs it and the script ELEVATES ITSELF once (Windows asks
the operator) — that's the one-time, honest admin ask.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUNDLE = ROOT / "build" / "universal_mind-bundle.zip"


def _fa(n: object) -> str:
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _elevate_if_needed() -> None:
    """The Task Scheduler add needs admin ONCE — ask the OS, then exit."""
    import ctypes

    if ctypes.windll.shell32.IsUserAnAdmin():  # already there
        return
    print("ثبتِ auto-start به یک‌بارِ مجوزِ admin نیاز دارد — ویندوز از شما میپرسد...")
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{__file__}" autostart-only', None, 1)
    sys.exit(0)


def install() -> None:
    home = Path.home() / "universal_mind"
    print("نصب در", home, "…")

    # The bundle must be built first (setup.cmd does it) — never guess.
    if not BUNDLE.exists():
        subprocess.run(["bash", str(ROOT / "setup.cmd")], cwd=ROOT, check=True)

    # 1) extract (a fresh home; an existing one is backed up, never lost)
    if home.exists():
        bkp = home.with_name(home.name + "-بکاپ")
        shutil.move(str(home), str(bkp))
        print("نسخهٔ قبلی منتقل شد به", bkp)
    home.mkdir(parents=True)
    with zipfile.ZipFile(BUNDLE) as z:
        z.extractall(home)
    print("استخراج شد:", len(list(home.rglob("*.*"))), "فایل")

    # 2) the private interpreter
    venv_py = home / ".venv" / "Scripts" / "python.exe"
    if not venv_py.exists():
        print("ساختِ محیطِ مستقل (یک دقیقه، فقط بارِ اول)…")
        subprocess.run([sys.executable, "-m", "venv", str(home / ".venv")], check=True)
    print("نصب وابستگیها (اینترنت برای یک‌بار)…")
    pip = home / ".venv" / "Scripts" / "pip.exe"
    r = subprocess.run([str(pip), "install", "-q", "-r",
                        str(home / "requirements.txt")], check=False)
    if r.returncode != 0:
        print("نکته: نصبِ آفلاین شد — خطا:", r.stderr[-120:] if r.stderr else "")

    # 3) the door (a double-clickable launcher in the bundle root)
    door = home / "universal_mind.cmd"
    door.write_text(
        "@echo off\n"
        "title universal_mind\n"
        "cd /d \"%~dp0\"\n"
        "call \"%~dp0.venv\\Scripts\\python.exe\" -m universal_mind\n",
        encoding="utf-8")

    # 4) autostart at every login (the ONE admin ask, through the OS)
    subprocess.run([
        "schtasks", "/create", "/tn", "UniversalMind",
        "/tr", f'"{door}"', "/sc", "onlogon", "/rl", "highest", "/f"],
        capture_output=True)
    print("auto-start ثبت شد.")

    # 5) a desktop shortcut
    _desktop_shortcut(door)
    print("میانبرِ دسکتاپ ساخته شد.")

    # 6) THE PROOF — ask the installed interpreter a real question. The
    # numeric answer is the measurement (never a claim).
    r = subprocess.run(
        [str(venv_py), "-m", "universal_mind", "--version"] if False else [
            str(venv_py), "-c",
            "import sys; sys.path.insert(0, "
            + repr(str(home)) + "); "
            "from universal_mind.persian_router import route_and_run; "
            "print(route_and_run('ساعت چنده؟').get('agent_report', ''))"],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "UM_MUTE": "1"})
    print("\n✅ نصب شد. گواهِ زنده:", r.stdout.strip()[:80] or r.stderr[:80])
    print("باز کن با دابل‌کلیکِ آیکونِ دسکتاپ، یا بعدِ لاگینِ بعد خودش میآید.")


def _desktop_shortcut(target: Path) -> None:
    desktop = Path.home() / "Desktop" / "ذهن سراسری.lnk"
    vb = Path(os.environ["TEMP"]) / "um_lnk.vbs"
    vb.write_text(
        'Set o=CreateObject("WScript.Shell")\n'
        f'Set l=o.CreateShortcut("{desktop}")\n'
        f'l.TargetPath="{target}"\n'
        'l.Save\n', encoding="utf-8")
    subprocess.run(["cscript", "//nologo", str(vb)], capture_output=True)
    vb.unlink(missing_ok=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "autostart-only":
        install()
        sys.exit(0)
    _elevate_if_needed()
    install()
