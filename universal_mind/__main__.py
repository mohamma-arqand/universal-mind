"""universal_mind — conversational door (python -m universal_mind)."""
from __future__ import annotations
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_BANNER = "ذهنِ سراسری — دستیارِ فارسی شما | «راهنما» = تواناییها | «خروج» = بستن"

def main() -> None:
    os.environ.setdefault("UM_MUTE", "1")
    from universal_mind.persian_router import route_and_run
    print(_BANNER, flush=True)
    while True:
        try:
            text = input("شما » ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not text or text in ("خروج", "exit", "quit"):
            print("فعلاً.")
            return
        try:
            out = route_and_run(text)
            print(str(out.get("agent_report", "…")), flush=True)
        except KeyboardInterrupt:
            print()
        except Exception as exc:
            print(f"خطای داخلی: {str(exc)[:150]}", flush=True)

if __name__ == "__main__":
    main()
