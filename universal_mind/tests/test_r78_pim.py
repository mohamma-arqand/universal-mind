"""R78 P1-P4 — the PIM class (notes/contacts).

A live 12-command sweep found 5 wrong answers: «یادداشتهایم را نشان بده»
read the LOCKED clipboard (a word collision — the note class lives in
named_memory, not on the clipboard), «فراموش کن» did the same, a
contact-name filter listed everything, «ایمیل علی را نشان بده» was
unknown, and «مخاطب علی با ایمیل ali@x.com» stored the NAME as
«علی با ایمیل» (the connector glued into the name).
"""

from __future__ import annotations

import pytest


def _cleanup() -> None:
    from universal_mind.database_suite import DatabaseSuite

    db = DatabaseSuite(persistent=True)
    db.execute("DELETE FROM contacts WHERE address LIKE '%gw78%'")
    db.execute("DELETE FROM named_memory WHERE fact LIKE '%gw78note%'")


class TestNotes:
    def test_the_note_listing_reads_named_memory_not_clipboard(self) -> None:
        from universal_mind.named_memory import save_fact
        from universal_mind.persian_router import route_and_run

        _cleanup()
        save_fact("gw78note یادداشت موج")
        p = route_and_run("یادداشتهایم را نشان بده")
        assert p["route"] == ["reflexive"], p["route"]
        rep = str(p.get("agent_report", ""))
        assert "gw78note" in rep and "کلیپبورد" not in rep

    def test_forgetting_a_note_deletes_it_by_name(self) -> None:
        from universal_mind.named_memory import save_fact
        from universal_mind.persian_router import route_and_run

        _cleanup()
        save_fact("gw78note حذفشدنی")
        p = route_and_run("یادداشت gw78note را فراموش کن")
        assert p["route"] == ["reflexive"]
        rep = str(p.get("agent_report", ""))
        assert "فراموش شد" in rep and "gw78note" in rep

    def test_forgetting_an_unknown_note_is_honest(self) -> None:
        from universal_mind.persian_router import route_and_run

        _cleanup()
        p = route_and_run("یادداشت gw78noteناپیدا را فراموش کن")
        assert p["ok"] is True
        assert "چنین یادداشتی ندارم" in str(p.get("agent_report", ""))


class TestContacts:
    def test_the_contact_name_is_stored_clean(self) -> None:
        from universal_mind.persian_router import route_and_run

        _cleanup()
        p = route_and_run("مخاطب رضا با ایمیل r.gw78@x.com را اضافه کن")
        assert p["ok"] is True
        rep = str(p.get("agent_report", ""))
        assert "«رضا»" in rep and "با ایمیل»" not in rep

    def test_the_contacts_email_is_answered(self) -> None:
        from universal_mind.persian_router import route_and_run

        _cleanup()
        route_and_run("مخاطب رضا با ایمیل r.gw78@x.com را اضافه کن")
        p = route_and_run("ایمیل رضا را نشان بده")
        rep = str(p.get("agent_report", ""))
        assert "r.gw78@x.com" in rep

    def test_the_name_filter_filters(self) -> None:
        from universal_mind.persian_router import route_and_run

        _cleanup()
        route_and_run("مخاطب رضا با ایمیل r.gw78@x.com را اضافه کن")
        p = route_and_run("مخاطبهایی که اسمشان رضا است را پیدا کن")
        rep = str(p.get("agent_report", ""))
        assert "رضا" in rep and "زهرا" not in rep

    def test_an_unknown_contact_email_is_a_named_miss(self) -> None:
        from universal_mind.persian_router import route_and_run

        _cleanup()
        p = route_and_run("ایمیل nobodygw78 را نشان بده")
        assert "ندارم" in str(p.get("agent_report", ""))


@pytest.fixture(autouse=True)
def _around() -> None:
    _cleanup()
    yield
    _cleanup()
