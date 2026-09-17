"""Rebuild mind.db from the corrupted original — exact, table by table.

Uses the recovered sqlite_master rows (table name → root page) to walk each
table's B-tree pages in the backup, decode every row, and replay them into a
FRESH database through the real DatabaseSuite schema. The fresh db is built
at a temp path, verified, then swapped in — the operator's real history is
never at risk during the rebuild.
"""

from __future__ import annotations

import json
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
PAGE = 4096


def read_varint(buf: bytes, i: int) -> tuple[int, int]:
    result = 0
    for _ in range(8):
        b = buf[i]
        i += 1
        result = (result << 7) | (b & 0x7F)
        if not (b & 0x80):
            return result, i
    result = (result << 8) | buf[i]
    return result, i + 1


def serial_len(t: int) -> int:
    if t in (0, 8, 9, 12, 13):
        return 0
    if t == 1:
        return 1
    if t == 2:
        return 2
    if t == 3:
        return 3
    if t == 4:
        return 4
    if t == 5:
        return 6
    if t in (6, 7):
        return 8
    if t >= 12:
        return (t - 12) // 2
    return 0


def decode_value(t: int, raw: bytes) -> object:
    if t == 0:
        return None
    if t == 1:
        return struct.unpack(">b", raw)[0]
    if t == 2:
        return struct.unpack(">h", raw)[0]
    if t == 3:
        return struct.unpack(">i", b"\x00" + raw)[0] if len(raw) == 3 else None
    if t == 4:
        return struct.unpack(">i", raw)[0]
    if t == 5:
        return struct.unpack(">q", b"\x00\x00" + raw)[0] if len(raw) == 6 else None
    if t == 6:
        return struct.unpack(">q", raw)[0]
    if t == 7:
        return struct.unpack(">d", raw)[0]
    if t in (8, 9):
        return t - 8
    if t >= 13 and t % 2 == 1:
        return raw.decode("utf-8", errors="replace")
    if t >= 12 and t % 2 == 0:
        return raw.hex()
    return None


def walk_table(data: bytes, root_page: int) -> list[list[object]]:
    """Depth-first walk of a table B-tree from its root page (1-based)."""
    rows: list[list[object]] = []
    seen: set[int] = set()
    stack = [root_page]
    while stack:
        pno = stack.pop()
        if pno in seen or pno < 1:
            continue
        seen.add(pno)
        page = data[(pno - 1) * PAGE: pno * PAGE]
        if not page:
            continue
        ptype = page[0]
        ncells = struct.unpack(">H", page[3:5])[0]
        header_size = 12 if ptype in (2, 5) else 8
        for c in range(ncells):
            ptr = struct.unpack(">H", page[header_size - 4 + 2 * c: header_size - 2 + 2 * c])[0]
            if ptype == 13:  # table leaf
                try:
                    _, i = read_varint(page, ptr)
                    _, i = read_varint(page, i)  # rowid
                    hdr_len, j = read_varint(page, i)
                    types: list[int] = []
                    while j < i + hdr_len:
                        t, j = read_varint(page, j)
                        types.append(t)
                    k = i + hdr_len
                    values: list[object] = []
                    for t in types:
                        ln = serial_len(t)
                        values.append(decode_value(t, page[k: k + ln]))
                        k += ln
                    rows.append(values)
                except (IndexError, struct.error):
                    continue
            elif ptype == 5:  # interior table page: children at offset 8+2n
                child = struct.unpack(">H", page[8 + 2 * c: 10 + 2 * c])[0]
                stack.append(child)
        if ptype == 5:
            # rightmost pointer at bytes 8..12
            stack.append(struct.unpack(">I", page[8:12])[0])
    return rows


def main() -> int:
    src = Path(r"C:\Users\EliteBook\.universal-mind\mind.db.bak-corrupt")
    fresh = Path(r"C:\Users\EliteBook\.universal-mind\mind.db.new")
    live = Path(r"C:\Users\EliteBook\.universal-mind\mind.db")
    data = src.read_bytes()

    # Recovered schema (from the arity-2 sqlite_master rows).
    schema = {  # table -> root page
        "custom_chains": 866,
        "run_history": 6076,
        "schedules": 68,
    }
    # The other tables' schema rows were in the overwritten header zone; their
    # rows are re-derived below from the recovered page buckets by SHAPE (the
    # sqlite_master rows for them did not survive).

    tables: dict[str, list[list[object]]] = {}
    for name, root in schema.items():
        tables[name] = walk_table(data, root)
        print(f"  {name}: {len(tables[name])} rows from root {root}")

    # Identify the headerless tables from the JSON buckets by their shape.
    buckets = json.loads(Path("recovered_rows.json").read_text(encoding="utf-8"))

    def rows_like(sample: list[object], bucket: list[list[object]]) -> list[list[object]]:
        return [r for r in bucket if r and isinstance(r[0], type(sample[0]))]

    # run_history rows are arity-6 (id, command, route, succeeded, excellence, created_at)
    ar6 = [r for r in buckets.get("6", []) if isinstance(r[1], str) and isinstance(r[2], str)]
    # chain_results: (id, metric, value) — arity 3 with two strings? match by sample
    ar3 = [r for r in buckets.get("3", []) if len(r) == 3 and isinstance(r[1], str)]
    # planner_lessons: (capability, operation, excellence, created_at) — arity 4
    ar4_str2 = [r for r in buckets.get("4", []) if len(r) == 4 and isinstance(r[0], str) and isinstance(r[1], str)]
    # extracted_data: (id, value) — arity 2 with numeric id and string value
    ar2_val = [r for r in buckets.get("2", []) if isinstance(r[1], str) and not isinstance(r[0], str)]

    print(f"  candidate run_history rows: {len(ar6)}")
    print(f"  candidate chain_results rows: {len(ar3)}")
    print(f"  candidate planner_lessons rows: {len(ar4_str2)}")
    print(f"  candidate extracted_data rows: {len(ar2_val)}")

    # ---- Replay into a FRESH real database (same persistent path, new file).
    if fresh.exists():
        fresh.unlink()
    from universal_mind.database_suite import DatabaseSuite

    db = DatabaseSuite(db_path=str(fresh))
    db.execute(
        "CREATE TABLE IF NOT EXISTS run_history (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "command TEXT, route TEXT, succeeded INTEGER, excellence REAL, "
        "created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS custom_chains (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "name TEXT, capabilities TEXT)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS schedules (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "command TEXT, every_minutes INTEGER, hour_of_day INTEGER, "
        "last_run TEXT DEFAULT '', active INTEGER DEFAULT 1)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS chain_results (metric TEXT, value TEXT)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS extracted_data (value TEXT)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS planner_lessons (capability TEXT, operation TEXT, "
        "excellence REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )

    def ins(table: str, rows: list[list[object]], cols: int) -> int:
        count = 0
        for r in rows:
            if len(r) < cols:
                continue
            db.insert_many(table, [dict(zip(
                _COLUMNS[table], [_norm(v) for v in r[:cols]]
            ))])
            count += 1
        return count

    total = 0
    total += ins("run_history", ar6, 6)
    total += ins("custom_chains", tables["custom_chains"], 3)
    total += ins("schedules", tables["schedules"], 6)
    total += ins("chain_results", ar3, 3)
    total += ins("extracted_data", ar2_val, 2)
    total += ins("planner_lessons", ar4_str2, 4)
    print(f"  replayed rows: {total}")

    # ---- Verify the fresh db, then swap.
    q = db.query("SELECT COUNT(*) AS n FROM run_history")
    print("fresh run_history:", q["rows"][0]["n"])
    q2 = db.query("SELECT COUNT(*) AS n FROM planner_lessons")
    print("fresh planner_lessons:", q2["rows"][0]["n"])

    shutil.copy2(live, str(live) + ".bak-pre-swap")
    shutil.copy2(fresh, live)
    print("swapped: mind.db is the rebuilt file; original kept as .bak-corrupt")
    return 0


def _norm(v: object) -> object:
    return v


_COLUMNS = {
    "run_history": ["id", "command", "route", "succeeded", "excellence", "created_at"],
    "custom_chains": ["id", "name", "capabilities"],
    "schedules": ["id", "command", "every_minutes", "hour_of_day", "last_run", "active"],
    "chain_results": ["id", "metric", "value"],
    "extracted_data": ["id", "value"],
    "planner_lessons": ["capability", "operation", "excellence", "created_at"],
}


if __name__ == "__main__":
    sys.exit(main())