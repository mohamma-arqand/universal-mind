"""R79 TRAY — the tray citizen + the global hotkey (Win32 pure).

The audit's quality gap was "after install you must LOOK for the app".
The tray service makes it a desktop citizen: an icon in the notification
area, a right-click Persian menu (گفت‌وگو / وضعیت سیستم / بستن), a
double-click door, and the GLOBAL Ctrl+Alt+M hotkey that raises the door
over any window — all with ctypes over Win32, zero new dependencies.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
IS_WIN = sys.platform == "win32"


@pytest.mark.skipif(not IS_WIN, reason="Win32 tray")
class TestTheTrayCitizen:
    def _probe(self) -> dict[str, bool]:
        code = (
            "import sys; sys.path.insert(0, r'" + str(ROOT) + "')\n"
            "import threading, time, ctypes\n"
            "from universal_mind.tray_service import serve\n"
            "t = threading.Thread(target=serve, daemon=True)\n"
            "t.start()\n"
            "time.sleep(4)\n"
            "user32 = ctypes.windll.user32\n"
            "hwnd = user32.FindWindowW('UMTray79', 'UMTray')\n"
            # a SECOND RegisterHotKey with the same combo fails while ours
            # holds it — that failure IS the proof the hotkey is ours.
            "second = user32.RegisterHotKey(None, 0xB01, 0x0002|0x0001, 0x4D)\n"
            "print('WINDOW=' + str(bool(hwnd)))\n"
            "print('HOTKEY=' + str(second == 0))\n"
            "print('ALIVE=' + str(t.is_alive()))\n"
        )
        env = {**__import__("os").environ, "UM_MUTE": "1",
               "PYTHONPATH": str(ROOT)}
        r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                           text=True, timeout=90, env=env)
        out = dict(line.split("=", 1) for line in r.stdout.splitlines()
                   if "=" in line)
        return {k: v == "True" for k, v in out.items()}

    def test_the_tray_window_and_hotkey_exist(self) -> None:
        got = self._probe()
        assert got.get("WINDOW") is True, got
        assert got.get("HOTKEY") is True, got
        assert got.get("ALIVE") is True, got

    def test_the_door_command_points_at_the_real_repl(self) -> None:
        sys.path.insert(0, str(ROOT))
        from universal_mind.tray_service import _door_command

        cmd = _door_command()
        assert "universal_mind.__main__" in " ".join(cmd)
        assert Path(cmd[0]).exists()

    def test_open_door_never_raises_in_the_tray(self) -> None:
        sys.path.insert(0, str(ROOT))
        from universal_mind.tray_service import open_door

        try:
            open_door()  # a console flashes open; the tray must survive
        except OSError as exc:  # pragma: no cover - only on broken hosts
            pytest.skip(f"console spawn unavailable: {exc}")
