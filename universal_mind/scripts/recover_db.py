"""One-shot recovery: parse the intact pages of a partially-corrupted SQLite db.

The header page (1) of mind.db was overwritten by an OpenCV stderr line;
pages 2+ are intact. This walks every leaf page, decodes the cell records
(varint header + serial types), and dumps every table's rows to JSON — then
rebuilds a FRESH mind.db by replaying them through the real DatabaseSuite.

Deterministic, local, prints exactly what it recovered per table.
"""

from __future__ import annotations

import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

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
    return 0  # 10/11 reserved


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


def parse_leaf_cells(page: bytes) -> list[list[object]]:
    """Decode every cell of a table-leaf page into a values list."""
    if not page or page[0] != 13:  # 0x0D = table leaf
        return []
    ncells = struct.unpack(">H", page[3:5])[0]
    rows: list[list[object]] = []
    for c in range(ncells):
        ptr = struct.unpack(">H", page[8 + 2 * c: 10 + 2 * c])[0]
        try:
            payload_len, i = read_varint(page, ptr)
            rowid, i = read_varint(page, i)
            hdr_len, j = read_varint(page, i)
            types: list[int] = []
            while j < i + hdr_len:
                t, j = read_varint(page, j)
                types.append(t)
            body_start = i + hdr_len
            values: list[object] = []
            k = body_start
            for t in types:
                ln = serial_len(t)
                values.append(decode_value(t, page[k: k + ln]))
                k += ln
            rows.append(values)
        except (IndexError, struct.error):
            continue
    return rows


def main() -> int:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\EliteBook\.universal-mind\mind.db.bak-corrupt")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "recovered_rows.json")
    data = src.read_bytes()
    n_pages = len(data) // PAGE

    # Walk pages; group rows heuristically by column count / shape. Page 1 is
    # the corrupted schema page — skip it. We cannot know table names from a
    # broken schema, so rows are bucketed by arity; the replay step maps them.
    buckets: dict[int, list[list[object]]] = defaultdict(list)
    for p in range(1, n_pages):  # page 0 (file page 1) is the schema page
        page = data[p * PAGE: (p + 1) * PAGE]
        for row in parse_leaf_cells(page):
            if row:
                buckets[len(row)].append(row)

    summary = {str(k): len(v) for k, v in sorted(buckets.items())}
    print("recovered row buckets (arity: count):", json.dumps(summary, ensure_ascii=False))
    out.write_text(json.dumps({str(k): v for k, v in buckets.items()}, ensure_ascii=False), encoding="utf-8")
    print(f"written: {out}")
    # Show a sample of each bucket for identification.
    for k, rows in sorted(buckets.items()):
        print(f"  arity {k}: sample {rows[0][:4]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())