"""R65 P7+P8 — the scalar question owns its engine; spoken folders resolve.

- «جذر ۱۶ چنده؟» pulled compute into the chain (its «چنده؟» word) but
  compute has NO sqrt — its empty expression refused and the whole run
  went red while the data suite's scalar_op had the answer. The scalar
  intent (جذر/توان/ضرب/تقسیم) now owns its question alone.
- «دانلودها را نشان بده» searched a literal «دانلود» folder (and
  routed to webfetch). The spoken folder names resolve to the REAL user
  folders (Downloads/Desktop/Documents/Pictures/…).
"""

from __future__ import annotations



class TestTheScalarIntentOwnsItsQuestion:
    def test_sqrt_answers_from_data_alone(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("جذر ۱۶ چنده؟")
        assert p["ok"] is True
        assert p["route"] == ["data"]  # compute stepped aside
        assert "نتیجه ۴" in p["agent_report"]

    def test_power_answers_from_data_alone(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("۳ به توان ۴ چنده؟")
        assert p["ok"] is True
        assert p["route"] == ["data"]
        assert "نتیجه" in p["agent_report"]


class TestTheSpokenFolders:
    def test_downloads_resolves_to_the_real_folder(self) -> None:
        from pathlib import Path

        from universal_mind.persian_params import extract_params

        out = extract_params("دانلودها را نشان بده", "filesearch")
        assert out.get("folder") == str(Path.home() / "Downloads")

    def test_the_sentence_searches_the_real_folder(self) -> None:
        from pathlib import Path

        from universal_mind.persian_router import route_and_run

        p = route_and_run("دانلودها را نشان بده")
        assert p["ok"] is True
        assert p["route"] == ["filesearch"]
        assert str(Path.home() / "Downloads") in p["agent_report"]
