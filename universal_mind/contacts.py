"""The contact book — named recipients for «به مدیر ایمیل بزن» (R56).

The measured gap: the operator says «ایمیل بزن به مدیر با موضوع گزارش» and
the platform can only refuse («گیرنده مشخص نیست») because it knows no
addresses by NAME. Humans speak in names, machines need addresses — this
module is the bridge.

Laws (the house style):
  - An address is VALIDATED before it is stored (a typo must not become a
    silent dead end: «ali@@x» is refused with the remedy named).
  - Resolution is exact-then-substring, honest about misses — a name that
    matches nothing returns None and the caller names the remedy.
  - The book is the PERSISTENT store (contacts survive restarts).
  - Never a secret: only name → address, nothing else.
"""

from __future__ import annotations

import re
from typing import Any

from universal_mind.database_suite import DatabaseSuite

# TWO patterns, two jobs: EXACT anchors the whole string (validation at save
# time — a typo must be refused), FIND scans inside a sentence (extraction).
_ADDR_EXACT = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
_ADDR_FIND = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _db(db: DatabaseSuite | None = None) -> DatabaseSuite:
    store = db or DatabaseSuite.shared_persistent()
    store.execute(
        "CREATE TABLE IF NOT EXISTS contacts ("
        "name TEXT PRIMARY KEY, address TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    return store


def save(name: str, address: str, *, db: DatabaseSuite | None = None) -> dict[str, Any]:
    """Remember a contact. The address is validated — a bad one is refused."""
    clean_name = name.strip().strip("«»\"'")
    clean_addr = address.strip().strip("<>")
    if not clean_name:
        return {"ok": False, "error": "نام مخاطب خالی است", "saved": False}
    if not _ADDR_EXACT.match(clean_addr):
        return {
            "ok": False,
            "error": f"آدرس «{clean_addr}» معتبر نیست — قالب درست: name@domain.com",
            "saved": False,
        }
    store = _db(db)
    safe_name = clean_name.replace("'", "''")
    safe_addr = clean_addr.replace("'", "''")
    store.execute(
        f"INSERT INTO contacts (name, address, updated_at) VALUES "
        f"('{safe_name}', '{safe_addr}', CURRENT_TIMESTAMP) "
        f"ON CONFLICT(name) DO UPDATE SET address = excluded.address, "
        f"updated_at = excluded.updated_at"
    )
    return {"ok": True, "name": clean_name, "address": clean_addr, "saved": True, "error": ""}


def resolve(name: str, *, db: DatabaseSuite | None = None) -> str | None:
    """The address behind a spoken name — exact match first, then substring.

    None means the book does not know the name (the caller names the remedy).
    """
    needle = name.strip().strip("«»\"':؛,.")
    if not needle:
        return None
    store = _db(db)
    safe = needle.replace("'", "''")
    q = store.query(f"SELECT address FROM contacts WHERE name = '{safe}' LIMIT 1")
    rows = q.get("rows", []) if q.get("ok") else []
    if rows:
        return str(rows[0]["address"])
    # substring both ways («مدیر پروژه» matches a stored «مدیر»)
    q2 = store.query(
        f"SELECT name, address FROM contacts WHERE name LIKE '%{safe}%' "
        f"OR '{safe}' LIKE '%' || name || '%' "
        "ORDER BY LENGTH(name) DESC LIMIT 1"
    )
    rows2 = q2.get("rows", []) if q2.get("ok") else []
    return str(rows2[0]["address"]) if rows2 else None


def list_contacts(*, db: DatabaseSuite | None = None) -> list[dict[str, str]]:
    """Every known contact (name → address), alphabetical."""
    store = _db(db)
    q = store.query("SELECT name, address FROM contacts ORDER BY name")
    return [{"name": str(r["name"]), "address": str(r["address"])}
            for r in (q.get("rows", []) if q.get("ok") else [])]


def forget(name: str, *, db: DatabaseSuite | None = None) -> dict[str, Any]:
    """Remove a contact by name (exact, then substring)."""
    needle = name.strip().strip("«»\"'")
    if not needle:
        return {"ok": False, "error": "نامی برای حذف داده نشد"}
    store = _db(db)
    target = resolve(needle, db=db)
    if target is None:
        return {"ok": False, "error": f"مخاطبی با نام «{needle}» ندارم"}
    safe = needle.replace("'", "''")
    store.execute(
        f"DELETE FROM contacts WHERE name = '{safe}' OR '{safe}' LIKE '%' || name || '%'"
    )
    return {"ok": True, "removed": needle}


def parse_contact_request(command: str) -> dict[str, str] | None:
    """«آدرس ایمیل مدیر را یادت باشد: ali@x.com» → {name, address}, or None.

    Honest forms:
      «آدرس ایمیل مدیر را یادت باشد: ali@x.com»
      «مخاطب مدیر را ذخیره کن: ali@x.com»
      «ایمیل مدیر را ثبت کن ali@x.com»
    """
    addr = _ADDR_FIND.search(command)
    if not addr:
        return None
    if not any(w in command for w in ("یادت باشد", "ذخیره کن", "ثبت کن", "اضافه کن",
                                      "مخاطب", "آدرس ایمیل")):
        return None
    name = ""
    m = re.search(r"(?:آدرس ایمیل|ایمیل|مخاطب)\s+«?([^»:\n]+?)»?\s*(?:را)?\s*"
                  r"(?:یادت باشد|ذخیره کن|ثبت کن|اضافه کن)", command)
    if m:
        name = m.group(1).strip()
    if not name:
        m2 = re.search(r"(?:یادت باشد|ذخیره کن|ثبت کن|اضافه کن)\s*[:：]?\s*«?([^»\n]+?)»?\s*"
                       r"(?:با آدرس|آدرس)?", command)
        if m2:
            name = m2.group(1).strip()
    name = re.sub(_ADDR_FIND, "", name).strip(" :：،,")
    if not name or "@" in name:
        return None
    return {"name": name, "address": addr.group(0)}


__all__ = ["save", "resolve", "list_contacts", "forget", "parse_contact_request"]
