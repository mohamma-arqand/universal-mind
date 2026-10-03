"""R68 P1+P2 — system stats are the machine's vitals; a contact count
counts the contact book.

Two LIVE wrong answers from the self-awareness sweep:
- «آمار کل سیستم را نشان بده» pulled data:stats and averaged the
  extracted_data table's EXPERIMENTAL rows («میانگین ۸ عدد برابر ۵»)
  as if they were the system's statistics. When the sentence names the
  machine (سیستم/دستگاه/…), sysstatus owns it alone.
- «چند تا مخاطب داری؟» answered with the RUN count («۴۷۶۰۳ اجرا
  ثبت شده») — the R64-P1 noun-owns-its-table law, contact edition.
"""

from __future__ import annotations



class TestSystemStatsOwnership:
    def test_system_stats_route_to_sysstatus_alone(self) -> None:
        from universal_mind.persian_router import route

        caps = route("آمار کل سیستم را نشان بده").capabilities
        assert "sysstatus" in caps
        assert "data" not in caps

    def test_live_answer_is_the_machines_vitals(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("آمار کل سیستم را نشان بده")
        assert p["ok"] is True
        assert p["route"] == ["sysstatus"]
        rep = p["agent_report"]
        assert "روشن است" in rep        # uptime
        assert "رم" in rep               # RAM
        assert "میانگین" not in rep      # never the experimental average

    def test_a_plain_stats_ask_still_goes_to_data(self) -> None:
        from universal_mind.persian_router import route

        caps = route("آمار این اعداد را بده: ۲ و ۸ و ۴").capabilities
        assert "data" in caps


class TestTheContactCountLaw:
    def test_the_count_is_the_real_book_not_runs(self) -> None:
        from universal_mind.contacts import list_contacts, save
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.persian_router import route_and_run

        DatabaseSuite(persistent=True).execute(
            "DELETE FROM contacts WHERE name LIKE '%گواه-r68%'")
        save("گواه-r68", "r68@example.com")
        try:
            real_n = len(list_contacts())
            p = route_and_run("چند تا مخاطب داری؟")
            fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
            assert f"{real_n} مخاطب داری".translate(fa) in p["agent_report"]
            assert "اجرا ثبت شده" not in p["agent_report"]
        finally:
            DatabaseSuite(persistent=True).execute(
                "DELETE FROM contacts WHERE name LIKE '%گواه-r68%'")

    def test_the_answer_names_a_recipe_both_ways(self) -> None:
        from universal_mind.contacts import list_contacts
        from universal_mind.persian_router import route_and_run

        p = route_and_run("چند تا مخاطب داری؟")
        assert p["ok"] is True
        if list_contacts():
            assert "مخاطبهام را نشان بده" in p["agent_report"]
        else:
            # the empty book names the recipe that creates one
            assert "یادت باشد" in p["agent_report"]
