"""R67 P7+P8 — the named-hour distance; the contact delete law.

- «چند دقیقه تا ساعت ۲۰ مانده؟» was unrecognized. The answer is the
  real distance on the 24h clock (a past hour today = tomorrow's
  occurrence), Persian digits, cross-checked against an independent
  computation.
- «مخاطب X را حذف کن» was unrecognized while contacts.forget existed.
  The DELETE LAW applies: the bare ask names the contact (name +
  address) and refuses; only «تأیید کن» removes the row. An unknown
  name is an honest refusal.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest


class TestTheNamedHourDistance:
    def test_matches_the_independent_computation(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("چند دقیقه تا ساعت ۲۰ مانده؟")
        now = datetime.now()
        tgt = now.replace(hour=20, minute=0, second=0, microsecond=0)
        if tgt <= now:
            tgt += timedelta(days=1)
        mins = int((tgt - now).total_seconds() // 60)
        h, m = divmod(mins, 60)
        _fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        expect = (f"{h} ساعت و {m} دقیقه" if h else f"{mins} دقیقه")
        assert p["ok"] is True
        assert expect.translate(_fa) in p["agent_report"]

    def test_a_past_hour_means_tomorrow(self) -> None:
        from universal_mind.persian_router import route_and_run

        now = datetime.now()
        past = (now.hour - 1) % 24
        p = route_and_run(f"چند دقیقه تا ساعت {past} مانده؟")
        # always a real positive distance — time only moves forward
        assert p["ok"] is True
        assert "مانده" in p["agent_report"]


@pytest.fixture()
def probe_contact():
    from universal_mind.contacts import save
    from universal_mind.database_suite import DatabaseSuite

    DatabaseSuite(persistent=True).execute(
        "DELETE FROM contacts WHERE name LIKE '%گواه-r67-p8%'")
    save("گواه-r67-p8", "p8@example.com")
    yield "گواه-r67-p8"
    DatabaseSuite(persistent=True).execute(
        "DELETE FROM contacts WHERE name LIKE '%گواه-r67-p8%'")


def _has(name: str) -> bool:
    from universal_mind.contacts import list_contacts

    return any(r["name"] == name for r in list_contacts())


class TestTheContactDeleteLaw:
    def test_the_bare_ask_refuses_and_names_the_contact(self, probe_contact) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run(f"مخاطب {probe_contact} را حذف کن")
        assert p["ok"] is False
        assert "تأیید" in p["agent_report"]
        assert probe_contact in p["agent_report"]          # the NAME is shown
        assert "p8@example.com" in p["agent_report"]       # the ADDRESS too
        assert _has(probe_contact)                          # the row survives

    def test_the_confirmation_removes_the_row(self, probe_contact) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run(f"مخاطب {probe_contact} را حذف کن — تأیید کن")
        assert p["ok"] is True
        assert "حذف شد" in p["agent_report"]
        assert not _has(probe_contact)

    def test_an_unknown_name_is_an_honest_refusal(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("مخاطب گواه-ناموجود-zz را حذف کن — تأیید کن")
        assert p["ok"] is False
        assert "ندارم" in p["agent_report"]
