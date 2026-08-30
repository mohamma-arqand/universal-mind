"""Tests for the hardened mypy ratchet (Mission 3.6-R).

The ratchet's job is to freeze *where* existing type debt lives, not just *how
much*. A lone integer baseline lets 1 error in a previously-clean file slide by
as long as 1 error is fixed somewhere else. These tests pin the two behaviours
that close that gap:

  * ``canonical_debt`` turns raw mypy output into a per-(file, code) breakdown;
  * ``is_prefix`` only accepts live debt that is a subset of the baseline.

Purely unit-level — no mypy is executed here — so the assertions are
deterministic and independent of how many pre-existing errors the repo has.
"""

from __future__ import annotations

import unittest

from scripts.check_mypy_ratchet import canonical_debt, is_prefix  # type: ignore[import-not-found]


class CanonicalDebtTests(unittest.TestCase):
    def test_parses_error_lines_into_file_code_groups(self) -> None:
        output = (
            "a.py:1: error: Call to untyped function \"f\" in typed context  [no-untyped-call]\n"
            "a.py:2: error: Missing type arguments for generic type \"G\"  [type-arg]\n"
            "b.py:10: error: Call to untyped function \"f\" in typed context  [no-untyped-call]\n"
            "Found 3 errors in 2 files (checked 5 source files)\n"
        )
        self.assertEqual(
            canonical_debt(output),
            {
                "a.py  no-untyped-call": 1,
                "a.py  type-arg": 1,
                "b.py  no-untyped-call": 1,
            },
        )

    def test_ignores_summary_and_note_lines(self) -> None:
        output = (
            "b.py:3: error: Something  [misc]\n"
            "Found 1 error in 1 file (checked 1 source file)\n"
            "note: https://mypy.readthedocs.io/...\n"
        )
        self.assertEqual(canonical_debt(output), {"b.py  misc": 1})

    def test_counts_multiple_errors_of_same_class(self) -> None:
        output = (
            "a.py:1: error: X  [misc]\n"
            "a.py:2: error: X  [misc]\n"
        )
        self.assertEqual(canonical_debt(output), {"a.py  misc": 2})


class IsPrefixTests(unittest.TestCase):
    def test_identical_is_prefix(self) -> None:
        base = {"a.py  misc": 2}
        self.assertTrue(is_prefix({"a.py  misc": 2}, base))

    def test_strict_subset_is_prefix(self) -> None:
        base = {"a.py  misc": 2, "b.py  type-arg": 1}
        self.assertTrue(is_prefix({"a.py  misc": 1}, base))

    def test_new_key_in_clean_file_fails(self) -> None:
        # A swap: same total, but debt appears in a file that had none.
        base = {"a.py  misc": 2}
        live = {"a.py  misc": 1, "b.py  no-untyped-call": 1}
        self.assertFalse(is_prefix(live, base))

    def test_count_rise_in_existing_slot_fails(self) -> None:
        base = {"a.py  misc": 2}
        self.assertFalse(is_prefix({"a.py  misc": 3}, base))

    def test_zero_live_is_always_prefix(self) -> None:
        self.assertTrue(is_prefix({}, {"a.py  misc": 2}))


if __name__ == "__main__":
    unittest.main()