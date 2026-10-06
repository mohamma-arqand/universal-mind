"""R79 — the tray citizen + the global hotkey (Win32 pure, no new deps).

The audit's quality gap: after install, Universal Mind was a window you
must LOOK for. A first-class desktop citizen sits in the tray, is one
keystroke away on ANY window (Ctrl+Alt+M), and speaks Persian.

Both are built with ctypes over Win32 only — no pystray, no keyboard
package (the bundle stays 14 pins; the Lite build stays small).

  * TrayIcon  — a real notification-area icon (Shell_NotifyIcon) whose
    menu offers: گفت‌وگو / وضعیت سیستم / بستن.
  * GlobalHotkey — RegisterHotKey(Ctrl+Alt+M): pressing it anywhere
    raises the conversational door.
  * serve() — one call that runs both on a dedicated thread; the door
    itself is the existing __main__ REPL (a console window on purpose:
    Persian text in a GUI textbox needs shaping; the console already
    shapes it right).
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
import threading
from pathlib import Path

WM_APP = 0x8000
WM_TRAYICON = WM_APP + 1
WM_HOTKEY_DOOR = 0x0400 + 0xB00  # app-private id
_ID_TRAY = 1
_MOD_ALT, _MOD_CONTROL = 0x0001, 0x0002
_VK_M = 0x4D

_NIM_ADD, _NIM_MODIFY, _NIM_DELETE = 0, 1, 2
_NIF_MESSAGE, _NIF_ICON, _NIF_TIP = 1, 2, 4
_NIF_ICON_VERSION_4 = 0x00000010  # NOTIFYICON_VERSION_4


class _WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wt.UINT), ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
        ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON),
        ("hCursor", ctypes.c_void_p), ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", wt.LPCWSTR), ("lpszClassName", wt.LPCWSTR),
    ]


class _NOTIFYICONDATA(ctypes.Structure):
    _fields_ = [
        ("hWnd", wt.HWND), ("uID", wt.UINT), ("uFlags", wt.UINT),
        ("uCallbackMessage", wt.UINT), ("hIcon", wt.HICON),
        ("szTip", wt.WCHAR * 128), ("dwState", wt.DWORD),
        ("dwStateMask", wt.DWORD), ("szInfo", wt.WCHAR * 256),
        ("uVersion", wt.UINT), ("szInfoTitle", wt.WCHAR * 64),
        ("dwInfoFlags", wt.DWORD), ("guidItem", wt.CHAR * 16),
    ]


def _door_command() -> list[str]:
    """Open the conversational door as a NEW console window."""
    exe = sys.executable
    root = Path(__file__).resolve().parents[1]
    inner = (
        "import sys; sys.path.insert(0, r'" + str(root.parent) + "'); "
        "from universal_mind.__main__ import main; main()"
    )
    return [exe, "-c", inner]


def open_door() -> None:
    """A NEW console window with the Persian REPL (never block the tray)."""
    subprocess.Popen(
        _door_command(),
        creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        cwd=str(Path(__file__).resolve().parents[1]),
        env={**__import__("os").environ, "UM_MUTE": "1"},
    )


def _run_tray(ready: threading.Event) -> None:  # noqa: ANN001 - std threading
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    shell32 = ctypes.windll.shell32

    wc = _WNDCLASSW()
    # a message-only window: no wndproc needed (DefWindowProc by the OS);
    # our loop reads messages directly with GetMessage/DispatchMessage.
    _dwp = ctypes.windll.user32.DefWindowProcW
    _dwp.restype = ctypes.c_longlong
    _dwp.argtypes = [ctypes.c_void_p, wt.UINT,
                     ctypes.c_size_t, ctypes.c_size_t]
    wc.lpfnWndProc = ctypes.cast(
        ctypes.WINFUNCTYPE(ctypes.c_longlong, ctypes.c_void_p, wt.UINT,
                           ctypes.c_size_t, ctypes.c_size_t)(
            lambda h, m, w, l: _dwp(h, m, w, l)),
        ctypes.c_void_p)
    wc.lpszClassName = "UMTray79"
    wc.hInstance = kernel32.GetModuleHandleW(None)
    user32.RegisterClassW(ctypes.byref(wc))
    user32.CreateWindowExW.restype = wt.HWND
    user32.CreateWindowExW.argtypes = [
        wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        wt.HWND, wt.HMENU, wt.HINSTANCE, ctypes.c_void_p]
    hwnd = user32.CreateWindowExW(
        0, "UMTray79", "UMTray", 0,
        0, 0, 0, 0, None, None, wc.hInstance, None)

    # icon: the system shell icon (index 2 — no external file needed)
    icon = shell32.ExtractIconW(None, "shell32.dll", 2)
    nid = _NOTIFYICONDATA()
    nid.cbSize = ctypes.sizeof(nid)
    nid.hWnd = hwnd
    nid.uID = _ID_TRAY
    nid.uFlags = _NIF_MESSAGE | _NIF_ICON | _NIF_TIP
    nid.uCallbackMessage = WM_TRAYICON
    nid.hIcon = icon
    nid.szTip = "ذهنِ سراسری — Ctrl+Alt+M برای گفت‌وگو"
    shell32.Shell_NotifyIconW(_NIM_ADD, ctypes.byref(nid))

    # the GLOBAL hotkey: Ctrl+Alt+M — works over ANY window
    user32.RegisterHotKey(hwnd, WM_HOTKEY_DOOR, _MOD_CONTROL | _MOD_ALT, _VK_M)

    ready.set()
    msg = wt.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message == WM_HOTKEY_DOOR:
            open_door()
        elif msg.message == WM_TRAYICON:
            if msg.lParam == 0x0202:  # WM_LBUTTONDBLCLK
                open_door()
            elif msg.lParam in (0x0204,):  # WM_RBUTTONUP → menu
                menu = user32.CreatePopupMenu()
                user32.AppendMenuW(menu, 0, 1, "گفت‌وگو (Ctrl+Alt+M)")
                user32.AppendMenuW(menu, 0, 2, "وضعیت سیستم")
                user32.AppendMenuW(menu, 0x800, 0, None)  # separator
                user32.AppendMenuW(menu, 0, 3, "بستن")
                pt = wt.POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                user32.SetForegroundWindow(hwnd)
                cmd = user32.TrackPopupMenu(
                    menu, 0x0180, pt.x, pt.y, 0, hwnd, None)
                user32.DestroyMenu(menu)
                if cmd == 1:
                    open_door()
                elif cmd == 2:
                    subprocess.Popen(
                        [*_door_command()[:2],
                         "import sys; sys.path.insert(0, r'" +
                         str(Path(__file__).resolve().parents[1].parent) +
                         "'); from universal_mind.persian_router import "
                         "route_and_run; print(route_and_run("
                         "'وضعیت سیستم را بگو')['agent_report']); input()"],
                        creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
                elif cmd == 3:
                    user32.PostMessageW(hwnd, 0x0012, 0, 0)  # WM_QUIT
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

    shell32.Shell_NotifyIconW(_NIM_DELETE, ctypes.byref(nid))
    user32.UnregisterHotKey(hwnd, WM_HOTKEY_DOOR)


def serve(start_door: bool = False) -> None:
    """Sit in the tray + own Ctrl+Alt+M; returns when the user exits."""
    ready = threading.Event()
    t = threading.Thread(target=_run_tray, args=(ready,), daemon=True)
    t.start()
    ready.wait(timeout=5)
    if start_door:
        open_door()
    try:
        while t.is_alive():
            t.join(timeout=3600)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    print("ذهنِ سراسری در سینی نشست — Ctrl+Alt+M = گفت‌وگو؛ راست‌کلیک = منو")
    serve(start_door=("--open" in sys.argv))
