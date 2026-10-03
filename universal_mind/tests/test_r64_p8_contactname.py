"""R64 P8 — the contact name stops at its own verb.

«به زهرا ایمیل بزن» extracted «زهرا ایمیل بزن» — the bare-verb shape
(the R61 fix covered only the «با موضوع» shape). The name is cut at
the channel's action words; the refusal names the OPERATOR'S OWN WORD
(«زهرا»), not the sentence's tail.
"""

from __future__ import annotations


class TestTheCleanContactName:
    def test_the_bare_verb_shape_names_only_the_person(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("به زهرا ایمیل بزن")
        rep = str(p.get("agent_report", ""))
        assert "«زهرا»" in rep
        assert "زهرا ایمیل" not in rep  # the tail never rides in

    def test_the_subject_shape_still_works(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("به مدیر ایمیل بزن با موضوع گزارش")
        assert p["route"] and "email" in p["route"]

    def test_a_saved_contact_resolves(self) -> None:
        from universal_mind.contacts import save
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.persian_router import route_and_run

        db = DatabaseSuite.shared_persistent()
        db.execute("DELETE FROM contacts WHERE name LIKE '%گواه-r64%'")
        save("گواه-r64", "witness64@example.com")
        try:
            p = route_and_run("به گواه-r64 ایمیل بزن")
            params = p.get("extracted_params", {}).get("email", {})
            assert params.get("to") == "witness64@example.com"
            assert params.get("resolved_from") == "گواه-r64"
        finally:
            db.execute("DELETE FROM contacts WHERE name LIKE '%گواه-r64%'")
