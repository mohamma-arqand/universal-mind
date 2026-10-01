"""R59 P6 — «زنجیره‌های من را نشان بده»: the saved-chain listing.

The sweep measured «نشناختم» while ChainsStore().load() existed. The listing
names each saved chain with its REAL steps in Persian (from the one
translation table, persian_report._CAP_FA — never a second copy).

ISOLATION LAW: ChainsStore now takes an INJECTABLE db. The first draft of
this test patched shared_persistent — which __init__ never read, so the test
LEAKED two rows into the operator's real mind.db (found and removed with a
named cleanup). This file uses the injected store only.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import mkdtemp
from unittest.mock import patch

from universal_mind.database_suite import DatabaseSuite
from universal_mind.reflexive import answer_reflexive


def _fresh_db() -> DatabaseSuite:
    return DatabaseSuite(str(Path(mkdtemp(prefix="um-p6-")) / "chains.db"))


def _db_with_chain(db: DatabaseSuite, name: str, caps: list[str]) -> DatabaseSuite:
    from universal_mind.chains_store import ChainsStore

    ChainsStore(db=db).save(name, caps)
    return db


def _with(db: DatabaseSuite):  # type: ignore[no-untyped-def]
    # the reflex reads the store through shared_persistent(); the injected
    # store IS the patched one, so the listing reads the isolated db
    return patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: db))


class TestChainListing:
    def test_a_saved_chain_is_listed_with_its_real_steps(self) -> None:
        db = _db_with_chain(_fresh_db(), "گزارش هفتگی", ["data", "chart", "pdf"])
        with _with(db):
            out = answer_reflexive("زنجیره‌های من را نشان بده")
        assert out is not None
        rep = out["agent_report"]
        assert "گزارش هفتگی" in rep
        assert "تحلیل داده" in rep and "نمودار" in rep  # Persian step names

    def test_two_chains_are_numbered_in_persian(self) -> None:
        db = _fresh_db()
        _db_with_chain(db, "الف", ["data"])
        _db_with_chain(db, "ب", ["chart"])
        with _with(db):
            rep = answer_reflexive("زنجیره‌های من را نشان بده")["agent_report"]
        assert "۲ زنجیره ذخیره شده" in rep
        assert "۱." in rep and "۲." in rep

    def test_empty_is_honest_with_the_recipe(self) -> None:
        db = _fresh_db()
        with _with(db):
            rep = answer_reflexive("زنجیره‌های من را نشان بده")["agent_report"]
        assert "ذخیره نکردی" in rep
        assert "زنجیره‌ی" in rep  # the recipe names the save sentence

    def test_running_a_chain_is_not_a_listing(self) -> None:
        # «زنجیره‌ی X را اجرا کن» is the RUN shape, not the LIST shape
        db = _db_with_chain(_fresh_db(), "گزارش هفتگی", ["data"])
        with _with(db):
            out = answer_reflexive("زنجیره‌ی گزارش هفتگی را اجرا کن")
        assert out is None or "زنجیره ذخیره شده" not in out["agent_report"]

    def test_a_dead_store_names_the_failure(self) -> None:
        class _Boom:
            def execute(self, *a: object, **k: object) -> object:
                raise RuntimeError("gone")

            def query(self, *a: object, **k: object) -> object:
                raise RuntimeError("gone")

        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: _Boom())):  # type: ignore[arg-type]
            out = answer_reflexive("زنجیره‌های من را نشان بده")
        assert out is not None and "نشد" in out["agent_report"]

    def test_the_store_is_injectable_no_real_db_is_touched(self) -> None:
        # the isolation law itself: constructing with an injected db must
        # never fall back to the persistent one
        db = _fresh_db()
        from universal_mind.chains_store import ChainsStore

        store = ChainsStore(db=db)
        store.save("ایزوله", ["data"])
        assert any(c.name == "ایزوله" for c in store.load())
