"""The remote face — a tiny localhost HTTP API over the Persian router.

The platform had faces only inside the machine (desktop tab, CLI). This
module serves ONE endpoint on localhost so a browser/phone on the same
machine (or via tunnel) can TALK to the platform:

    GET  /ask?text=...   -> the full route_and_run payload (JSON, UTF-8)
    GET  /health         -> ok + counts
    GET  /               -> a minimal Persian chat page (no build step)

STANDARDS:
- Binds 127.0.0.1 ONLY (localhost face, never a public one by accident).
- No secrets, no auth — a localhost personal tool, same trust as the CLI.
- Never dies on a bad command: the router's honest failure IS the answer.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

_HOST = "127.0.0.1"

_PAGE = """<!DOCTYPE html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<title>ذهن جهانی</title>
<style>
 body{font-family:Tahoma,Segoe UI;background:#14161f;color:#d6d9e3;margin:0;display:flex;flex-direction:column;height:100vh}
 #log{flex:1;overflow-y:auto;padding:16px}
 .m{margin:6px 0;padding:8px 12px;border-radius:10px;max-width:80%;white-space:pre-wrap}
 .me{background:#23304d;align-self:flex-start}
 .sys{background:#1d2a22;align-self:flex-end}
 .vbar{display:flex;gap:8px;padding:2px 16px}
form{display:flex;padding:10px;background:#101219}
 input{flex:1;font-size:16px;padding:10px;border-radius:8px;border:1px solid #333;background:#1b1e2b;color:#eee}
 button{margin-right:8px;font-size:16px;padding:10px 18px;border-radius:8px;border:0;background:#3d5af1;color:#fff;cursor:pointer}
</style></head><body>
<div id="log"></div>
<form onsubmit="return send()"><input id="t" autofocus placeholder="بنویس..."><button>بفرست</button></form>
<script>
let lastOkCommand=null;
async function send(){
 const t=document.getElementById('t');const v=t.value.trim();if(!v)return false;
 t.value='';add(v,'me');
 const r=await fetch('/ask?text='+encodeURIComponent(v));
 const j=await r.json();
 add(j.agent_report||(j.ok?'انجام شد':'ناموفق'),'sys');
 if(j.ok===true&&j.planned!==true){lastOkCommand=v;verdictRow()}
 return false}
function verdictRow(){
 const bar=document.createElement('div');bar.className='vbar';
 const g=document.createElement('button');g.textContent='👍 عالی بود';g.onclick=()=>vote('good',bar);
 const b=document.createElement('button');b.textContent='👎 بد بود';b.onclick=()=>vote('bad',bar);
 bar.appendChild(g);bar.appendChild(b);
 document.getElementById('log').appendChild(bar)}
async function vote(v,bar){
 if(!lastOkCommand)return;
 const r=await fetch('/verdict?text='+encodeURIComponent(lastOkCommand)+'&v='+v);
 const j=await r.json();
 add(j.answer||'رأیت ثبت شد.','sys');
 bar.remove()}
function add(t,c){const d=document.createElement('div');d.className='m '+c;d.textContent=t;
 document.getElementById('log').appendChild(d)}
</script></body></html>"""


def make_handler() -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 — http.server API
            url = urlparse(self.path)
            if url.path == "/":
                self._send(200, _PAGE.encode("utf-8"), "text/html; charset=utf-8")
                return
            if url.path == "/health":
                body = json.dumps({"ok": True}, ensure_ascii=False).encode("utf-8")
                self._send(200, body, "application/json; charset=utf-8")
                return
            if url.path == "/verdict":
                # R44-4: the operator's one-click verdict — the SAME store-bound
                # record as «عالی بود»/«بد بود» in the chat, from the web face.
                q = parse_qs(url.query)
                cmd = unquote((q.get("text") or [""])[0]).strip()
                v = (q.get("v") or ["good"])[0]
                from universal_mind.operator_verdicts import record_verdict

                out: dict[str, Any] = record_verdict(cmd, v)
                body = json.dumps(out, ensure_ascii=False, default=str).encode("utf-8")
                self._send(200, body, "application/json; charset=utf-8")
                return
            if url.path == "/ask":
                text = (parse_qs(url.query).get("text") or [""])[0]
                text = unquote(text).strip()
                from universal_mind.persian_router import route_and_run

                payload: dict[str, Any] = route_and_run(text)
                payload.pop("_registry", None)  # not JSON-serializable
                body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
                self._send(200, body, "application/json; charset=utf-8")
                return
            self._send(404, b'{"ok":false,"error":"not found"}', "application/json")

        def log_message(self, fmt: str, *args: Any) -> None:  # quiet
            return

    return Handler


def serve(port: int = 8765) -> ThreadingHTTPServer:
    """Bind the localhost face (blocks the caller — run in a thread)."""
    server = ThreadingHTTPServer((_HOST, port), make_handler())
    return server


def serve_forever(port: int = 8765) -> None:
    """Run the localhost face until killed (the CLI entrypoint)."""
    srv = serve(port)
    print(f"چهرهی محلی روی http://{_HOST}:{port} — Ctrl+C برای توقف")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.server_close()


if __name__ == "__main__":
    serve_forever()


__all__ = ["make_handler", "serve", "serve_forever"]