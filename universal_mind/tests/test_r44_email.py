"""Tests: R44 item 11 — the email outbox (a real message leaves the platform).

Live laws:
1. A real RFC-822 .eml lands on disk with To/Subject/MIME — verifiable bytes.
2. An attachment really rides inside the message (the chain's own artifact).
3. SMTP is OPTIONAL: without env credentials the tool says the file was made
   but not sent (never a fake send); a real SMTP failure keeps the .eml and
   names the error. Credentials never appear in the result.
4. The production chain («... و به آدرس x@y ایمیل کن») ships the .eml with
   the report attached.
"""

from __future__ import annotations

from typing import Any


class TestTheOutbox:
    """compose — a real message file."""

    def test_a_real_eml_lands_on_disk(self, tmp_path: Any) -> None:
        from universal_mind.email_outbox import compose

        out = compose(to="ali@example.com", subject="گزارش", body="سلام", out_dir=str(tmp_path))
        assert out["ok"] is True
        raw = open(out["path"], "rb").read()
        assert b"To: ali@example.com" in raw
        assert b"MIME-Version: 1.0" in raw
        assert b"Subject:" in raw

    def test_the_attachment_really_rides(self, tmp_path: Any) -> None:
        from universal_mind.email_outbox import compose

        payload = tmp_path / "report.txt"
        payload.write_text("real content", encoding="utf-8")
        out = compose(to="a@b.com", body="پیوست", attachment=str(payload), out_dir=str(tmp_path))
        assert out["attachment_bytes"] == len("real content")
        raw = open(out["path"], "rb").read()
        assert b"application" in raw  # the part exists in the message

    def test_no_recipient_is_an_honest_refusal(self, tmp_path: Any) -> None:
        from universal_mind.email_outbox import compose

        out = compose(to="", body="x", out_dir=str(tmp_path))
        assert out["ok"] is False
        assert "گیرنده" in out["error"]

    def test_a_missing_attachment_is_named(self, tmp_path: Any) -> None:
        from universal_mind.email_outbox import compose

        out = compose(to="a@b.com", attachment=str(tmp_path / "nope.pdf"), out_dir=str(tmp_path))
        assert out["ok"] is False
        assert "پیوست" in out["error"]


class TestTheOptionalSend:
    """send — env-gated, never a fake send, never a leaked credential."""

    def test_without_env_it_says_so(self, tmp_path: Any, monkeypatch: Any) -> None:
        from universal_mind.email_outbox import compose, send

        for var in ("UM_SMTP_HOST", "UM_SMTP_USER", "UM_SMTP_PASS"):
            monkeypatch.delenv(var, raising=False)
        out = compose(to="a@b.com", body="x", out_dir=str(tmp_path))
        sent = send(out["path"])
        assert sent["sent"] is False
        assert "SMTP" in sent["error"]
        assert "UM_SMTP_HOST" in sent["error"]  # the remedy is named
        assert out["path"] and __import__("pathlib").Path(out["path"]).exists()

    def test_a_failed_send_keeps_the_file_and_hides_the_secret(
        self, tmp_path: Any, monkeypatch: Any
    ) -> None:
        from universal_mind.email_outbox import compose, send

        monkeypatch.setenv("UM_SMTP_HOST", "127.0.0.1")
        monkeypatch.setenv("UM_SMTP_PORT", "1")  # nothing listens there
        monkeypatch.setenv("UM_SMTP_USER", "user@x.com")
        monkeypatch.setenv("UM_SMTP_PASS", "SUPER-SECRET-VALUE")
        out = compose(to="a@b.com", body="x", out_dir=str(tmp_path))
        sent = send(out["path"])
        assert sent["sent"] is False
        assert "SUPER-SECRET-VALUE" not in str(sent)  # never echoed
        assert __import__("pathlib").Path(out["path"]).exists()  # work kept


class TestTheProductionChain:
    """The real route: numbers → pdf → email."""

    def test_the_chain_ships_the_message(self, tmp_path: Any, monkeypatch: Any) -> None:
        import tempfile
        from pathlib import Path
        from unittest.mock import patch as mock_patch

        from universal_mind.database_suite import DatabaseSuite

        monkeypatch.setenv("UM_OUTBOX_DIR", str(tmp_path))
        iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r44-11.db"))
        with mock_patch.object(DatabaseSuite, "shared_persistent",
                               classmethod(lambda cls: iso)):
            with mock_patch("universal_mind.email_outbox._outbox_dir", lambda *_a, **_k: tmp_path):
                from universal_mind.persian_router import route_and_run

                p: Any = route_and_run(
                    "میانگین ۱۰ و ۲۰ را حساب کن و گزارشش کن و به آدرس ali@example.com ایمیل کن"
                )
        assert p["route"] == ["data", "pdf", "email"]
        assert p["ok"] is True
        em = p["result"]["email"]
        assert em["to"] == "ali@example.com"
        assert em["bytes"] > 1000
        assert any("ایمیل" in f for f in p["flows"])
