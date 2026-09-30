"""R56 — THE CONTACT BOOK: «به مدیر ایمیل بزن» where مدیر is a saved name.

The measured gap: the operator speaks NAMES, machines need ADDRESSES.
Before this, «ایمیل بزن به مدیر» could only refuse. Now: save a contact
by voice, resolve it by name (exact then substring), email through the
FULL router, and get a remedy that NAMES the operator's own unknown word.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def book(tmp_path: Path):  # type: ignore[no-untyped-def]
    """An isolated contact book (never the live store)."""
    from universal_mind.database_suite import DatabaseSuite

    return DatabaseSuite(str(tmp_path / "contacts.db"))


class TestContactStore:
    def test_save_and_resolve_roundtrip(self, book) -> None:  # type: ignore[no-untyped-def]
        from universal_mind.contacts import resolve, save

        res = save("مدیر", "boss@example.com", db=book)
        assert res["ok"] is True and res["saved"] is True
        assert resolve("مدیر", db=book) == "boss@example.com"

    def test_a_bad_address_is_refused_with_the_recipe(self, book) -> None:  # type: ignore[no-untyped-def]
        from universal_mind.contacts import resolve, save

        res = save("مدیر", "not-an-address", db=book)
        assert res["ok"] is False
        assert "معتبر نیست" in res["error"] and "name@domain.com" in res["error"]
        assert resolve("مدیر", db=book) is None  # nothing stored

    def test_resolve_falls_back_to_substring(self, book) -> None:  # type: ignore[no-untyped-def]
        """«مدیر» stored; «مدیر پروژه» still resolves (the longer form wins)."""
        from universal_mind.contacts import resolve, save

        save("مدیر", "boss@example.com", db=book)
        save("مدیر پروژه", "pm@example.com", db=book)
        assert resolve("مدیر پروژه", db=book) == "pm@example.com"
        assert resolve("مدیر", db=book) == "boss@example.com"

    def test_unknown_name_returns_none_not_a_guess(self, book) -> None:  # type: ignore[no-untyped-def]
        from universal_mind.contacts import resolve

        assert resolve("رئیسکل", db=book) is None

    def test_forget_removes_by_name(self, book) -> None:  # type: ignore[no-untyped-def]
        from universal_mind.contacts import forget, resolve, save

        save("مدیر", "boss@example.com", db=book)
        assert forget("مدیر", db=book)["ok"] is True
        assert resolve("مدیر", db=book) is None

    def test_forget_unknown_names_it(self, book) -> None:  # type: ignore[no-untyped-def]
        from universal_mind.contacts import forget

        res = forget("ناموجود", db=book)
        assert res["ok"] is False and "ندارم" in res["error"]

    def test_list_is_alphabetical(self, book) -> None:  # type: ignore[no-untyped-def]
        from universal_mind.contacts import list_contacts, save

        save("ب", "b@x.com", db=book)
        save("ا", "a@x.com", db=book)
        names = [c["name"] for c in list_contacts(db=book)]
        assert names == sorted(names)


class TestContactParsing:
    def test_forms_all_extract_name_and_address(self) -> None:
        from universal_mind.contacts import parse_contact_request

        forms = [
            "آدرس ایمیل مدیر را یادت باشد: boss@example.com",
            "مخاطب مدیر را ذخیره کن: boss@example.com",
            "ایمیل مدیر را ثبت کن boss@example.com",
        ]
        for form in forms:
            got = parse_contact_request(form)
            assert got is not None, form
            assert got["address"] == "boss@example.com"
            assert "مدیر" in got["name"]

    def test_an_ordinary_command_is_not_a_contact_request(self) -> None:
        from universal_mind.contacts import parse_contact_request

        # a report that merely mentions an address is NOT a save request
        assert parse_contact_request("نمودار بکش") is None
        assert parse_contact_request("ایمیل بزن به ali@example.com") is None

    def test_named_memory_without_an_address_is_not_a_contact(self) -> None:
        """«یادت باشد مدیر آقای رضایی است» is NAMED MEMORY, not a contact."""
        from universal_mind.contacts import parse_contact_request

        assert parse_contact_request("یادت باشد که مدیر پروژه آقای رضایی است") is None


class TestRouterIntegration:
    def test_save_then_email_by_name_through_the_full_router(self) -> None:
        from universal_mind.contacts import forget, list_contacts
        from universal_mind.persian_router import route_and_run

        forget("تستمدیر")
        try:
            save_res = route_and_run(
                "آدرس ایمیل تستمدیر را یادت باشد: testboss@example.com")
            assert save_res["route"] == ["contacts"]
            assert save_res["ok"] is True

            listed = route_and_run("مخاطبین من")
            assert "testboss@example.com" in listed["agent_report"]

            emailed = route_and_run("ایمیل بزن به تستمدیر با موضوع گزارش تست")
            # the address resolved: the email step no longer refuses for lack of a recipient
            assert "گیرنده مشخص نیست" not in str(emailed.get("errors"))
        finally:
            forget("تستمدیر")
            assert not [c for c in list_contacts() if c["name"] == "تستمدیر"]

    def test_unknown_name_gives_a_remedy_naming_the_word(self) -> None:
        from universal_mind.contacts import forget
        from universal_mind.persian_router import route_and_run

        forget("رئیسکل")
        res = route_and_run("ایمیل بزن به رئیسکل با موضوع گزارش")
        assert res["ok"] is False
        err = str(res.get("errors", {}).get("email", ""))
        # the operator's OWN word is named, with the exact sentence that fixes it
        assert "رئیسکل" in err
        assert "یادت باشد" in err
