"""Hearing — the platform listens to the operator's VOICE and then acts.

R44 item 9: «گوش کن» is not a capability run, it is an OPERATOR GESTURE: the
platform opens its ears, dictates real speech-to-text (Windows
System.Speech), and routes what it HEARD through the same Persian router
every other command uses. The heard text is echoed FIRST (the operator must
see what the platform thinks it heard — a misheard command must never
execute silently).

STANDARDS:
- The echo always precedes the run: «شنیدم: «...»» then the real answer.
- Heard-nothing is honest: the platform says so and does not invent work.
- A missing engine names the exact remedy (never a silent no-op).
- The routed command is recorded as the heard text, so history and the
  advisor learn from what the operator actually said.
"""

from __future__ import annotations

from typing import Any


def hear_and_run(seconds: int = 5, lang: str = "en-US", *, registry: Any = None) -> dict[str, Any]:
    """Listen, echo what was heard, then route it — one honest gesture.

    Returns a payload shaped like route_and_run's, with `heard` added and a
    `hearing_report` that names the echo and the outcome.
    """
    from universal_mind.persian_router import route_and_run
    from universal_mind.speech_tool import SpeechTool

    heard = SpeechTool().listen(seconds=seconds, lang_hint=lang)
    if heard.get("ok") is not True:
        reason = str(heard.get("error") or "گوش دادن ممکن نشد")
        return {
            "ok": False,
            "command": "گوش کن",
            "route": ["speech"],
            "matched_words": ["گوش"],
            "unknown": [],
            "extracted_params": {"speech": {"operation": "listen"}},
            "result": {"speech": {"listen": heard}},
            "errors": {"speech": reason},
            "durations_ms": {},
            "flows": [],
            "judgment": {},
            "heard": "",
            "agent_report": f"❌ نشنیدم: {reason}",
            "_registry": registry,
        }

    text = str(heard.get("recognized") or "").strip()
    if not text:
        note = str(heard.get("note") or "صدایی شنیده نشد")
        return {
            "ok": False,
            "command": "گوش کن",
            "route": ["speech"],
            "matched_words": ["گوش"],
            "unknown": [],
            "extracted_params": {"speech": {"operation": "listen"}},
            "result": {"speech": {"listen": heard}},
            "errors": {"speech": note},
            "durations_ms": {},
            "flows": [],
            "judgment": {},
            "heard": "",
            "agent_report": f"❌ {note}",
            "_registry": registry,
        }

    # Route what was HEARD — the same real engine, the same Persian report.
    payload = route_and_run(text)
    inner = str(payload.get("agent_report") or "").strip()
    report = f"👂 شنیدم: «{text}»\n{inner}"
    return {
        **payload,
        "heard": text,
        "command": f"گوش کن → {text}",
        "agent_report": report,
    }


def is_hearing_phrase(command: str) -> bool:
    """«گوش کن» / «گوش بده» / «به من گوش کن» — the operator is SPEAKING."""
    c = command.strip()
    return c in (
        "گوش کن", "گوش بده", "به من گوش کن", "به حرفم گوش کن",
        "گوش کن و انجام بده", "بشنو", "گوش کن ببین چی میگم",
    ) or c.startswith(("گوش کن ", "گوش بده ", "بشنو "))


__all__ = ["hear_and_run", "is_hearing_phrase"]
