#!/usr/bin/env python3
"""Probe: R43 — the honest refusal classes + vocabulary truth, live.

Three laws from the live audit, each locked with a real round-trip:
1. «جستجو کن» (no URL) is a QUESTION, not a failure — the row carries
   outcome_class='needs_param' and the predictor ignores it (176 rows of
   fake pessimism were recorded before this class existed).
2. The err_text read is FIXED — sub_outputs carry the errors; the old
   syn.output['errors'] read was always empty, so NO refusal class ever
   fired (even blocked_env).
3. The vocabulary means what it says: «موسیقی پخش کن» is media (playing
   a file), «متن بنویس» is pdf (a durable document) — never speech/clipboard.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "..")

sys.stderr.write("PROBE R43 honest refusals:\n")


def _ok(name: str, cond: bool, extra: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    sys.stderr.write(f"  [{mark}] {name}" + (f" — {extra}" if extra else "") + "\n")
    if not cond:
        raise SystemExit(1)


def main() -> int:
    import tempfile
    from pathlib import Path
    from unittest.mock import patch as mock_patch

    from universal_mind.database_suite import DatabaseSuite

    iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "probe-r43.db"))
    with mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: iso)):
        from universal_mind.persian_router import route_and_run, route

        # H1 — the question is recorded as a question.
        route_and_run("جستجو کن")
        row = iso.query(
            "SELECT succeeded, outcome_class FROM run_history ORDER BY id DESC LIMIT 1"
        )["rows"][0]
        _ok("needs_param recorded", row["outcome_class"] == "needs_param",
            f"class={row['outcome_class']!r} ok={row['succeeded']}")

        # H2 — the predictor ignores the questions (no learned pessimism).
        from universal_mind.success_predictor import predict_success

        for _ in range(3):
            route_and_run("جستجو کن")
        p = predict_success(("webfetch",))
        _ok("predictor blind to questions", p.evidence_runs == 0,
            f"evidence={p.evidence_runs}")

        # H3 — the vocabulary means what it says.
        caps_music = route("موسیقی پخش کن").capabilities
        _ok("music is media", "media" in caps_music and "speech" not in caps_music,
            f"route={caps_music}")
        caps_text = route("متن بنویس که سلام دنیا").capabilities
        _ok("write-text is a document", caps_text == ("pdf",), f"route={caps_text}")
        caps_aloud = route("میانگین ۴ و ۶ را حساب کن و بلند بخوان").capabilities
        _ok("read-aloud stays speech", "speech" in caps_aloud, f"route={caps_aloud}")

    sys.stderr.write("R43 honest refusals: ALL HOLDS GREEN\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
