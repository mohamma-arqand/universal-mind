#!/usr/bin/env python3
"""R57 N1 — THE SSRF GUARD, live-proved: 8 proofs.

All of these run FOR REAL (a real socket for the redirect case, real
network classification for the public case). Nothing is mocked.

 1  A loopback target is refused BY DEFAULT and named blocked_target.
 2  The refusal carries the Persian remedy the operator can act on.
 3  Every private family is refused (loopback/private/link-local/metadata).
 4  The refusal happens BEFORE any connection is attempted.
 5  A REAL 302 to file:// is refused even with the local guard lifted.
 6  A REAL 302 to the cloud metadata address is refused.
 7  A local server is readable only when the operator says so explicitly.
 8  A public host is NOT mislabelled as private (offline != blocked).
"""

from __future__ import annotations

import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FAILURES: list[str] = []


def check(n: int, label: str, ok: bool) -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {n}. {label}")
    if not ok:
        FAILURES.append(label)


class _Redirector(BaseHTTPRequestHandler):
    """Serves 302s: one to file://, one to the cloud metadata address,
    one to a healthy local page."""

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/to-file":
            self.send_response(302)
            self.send_header("Location", "file:///C:/Windows/win.ini")
            self.end_headers()
            return
        if self.path == "/to-metadata":
            self.send_response(302)
            self.send_header("Location", "http://169.254.169.254/latest/meta-data/")
            self.end_headers()
            return
        body = b"<html><title>ok</title><body>local page</body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a: object) -> None:
        return


def main() -> int:
    import os

    os.environ["UM_MUTE"] = "1"

    from universal_mind.webfetch_tool import WebFetchTool

    tool = WebFetchTool()

    # 1 + 2 — the default refusal, with the operator's own remedy
    r = tool.fetch("http://127.0.0.1:9/x")
    print(f"    127.0.0.1:9 -> ok={r['ok']} kind={r['kind']}")
    check(1, "a loopback target is refused by default (blocked_target)",
          r["ok"] is False and r["kind"] == "blocked_target")
    check(2, "the refusal names the Persian remedy",
          "آدرس داخلی مجاز است" in r["error"])

    # 3 — the whole private family, each named honestly
    fam = {
        "loopback": "http://127.0.0.1/",
        "localhost": "http://localhost:8080/",
        "private-10": "http://10.1.2.3/",
        "private-192": "http://192.168.0.1/",
        "link-local": "http://169.254.169.254/latest/meta-data/",
        "ipv6-loopback": "http://[::1]/",
        "internal-name": "http://nas.internal/",
    }
    results = {k: tool.fetch(u)["kind"] for k, u in fam.items()}
    print(f"    family -> {results}")
    check(3, f"every private family is refused ({len(fam)} targets)",
          all(v == "blocked_target" for v in results.values()))

    # 4 — nothing was dialled: prove with a socket-level trap
    real_connect = socket.socket.connect

    def _trap(self, *a, **k):  # type: ignore[no-untyped-def]
        raise AssertionError("the tool tried to connect to a blocked target")

    socket.socket.connect = _trap  # type: ignore[method-assign]
    try:
        r4 = tool.fetch("http://169.254.169.254/latest/meta-data/")
    finally:
        socket.socket.connect = real_connect  # type: ignore[method-assign]
    check(4, "the refusal happens BEFORE any connection is attempted",
          r4["kind"] == "blocked_target")

    # ---- a REAL socket for the redirect proofs ----
    srv = HTTPServer(("127.0.0.1", 0), _Redirector)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    try:
        to_file = tool.fetch(f"{base}/to-file", allow_private=True)
        print(f"    302 -> file://  => kind={to_file['kind']}")
        check(5, "a REAL 302 to file:// is refused even with the local guard lifted",
              to_file["ok"] is False and to_file["kind"] == "blocked_target")

        to_meta = tool.fetch(f"{base}/to-metadata", allow_private=True)
        print(f"    302 -> metadata => kind={to_meta['kind']}")
        check(6, "a REAL 302 to the cloud metadata address is refused",
              to_meta["ok"] is False and to_meta["kind"] == "blocked_target")

        ok_page = tool.fetch(f"{base}/page", allow_private=True)
        check(7, "a local server is readable when the operator says so explicitly",
              ok_page["ok"] is True and ok_page["chars"] > 0)
    finally:
        srv.shutdown()
        srv.server_close()

    # 8 — a public host is never mislabelled
    public = tool.fetch("https://dead-host-zz9.example.invalid")
    print(f"    public dead host -> kind={public['kind']}")
    check(8, "a public host is NOT mislabelled as private (offline != blocked)",
          public["kind"] in ("offline", "timeout"))

    print()
    if FAILURES:
        print(f"R57-SSRF probe FAILED ({len(FAILURES)}):")
        for f in FAILURES:
            print(f"  ✗ {f}")
        return 1
    print("R57-SSRF probe: ALL 8 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
