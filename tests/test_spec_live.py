#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""tools/spec_live.py's parsing, which decides what the gate compares (docs/spec-method.md §8 step 2).

A mis-read of a page's Differences table would make the gate AGREE for the wrong reason; a run file it
cannot re-run row by row must be refused, not guessed at."""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "lib"))
import probe_tmp  # noqa: E402,F401  -- tempfile under the project's temp root
import spec_live as L  # noqa: E402

PAGE = """# `X` ($0000)

## Differences from the reference

| TODO item | rules zerobas fails |
|---|---|
| **D-ONE** (the first, R-FAKE-0 in the description) | R-K-AF, R-K-ERA-A |
| ruled font (D-BIOSINT) | R4-LT / R-T-VRAM2 (its two cases) |

## Open (not measured)

- **[A]** R-NOT-A-DIFF named in an open item.
"""


class _Mod:
    def __init__(self, page):
        self.PAGE = page


class TestSpecLive(unittest.TestCase):
    def page(self, text):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "X.md")
        open(p, "w").write(text)
        return _Mod(p)

    def test_listed_reads_only_the_rule_column_of_the_differences_table(self):
        # the description column's R-FAKE-0 and the Open section's R-NOT-A-DIFF are NOT listed
        self.assertEqual(L.page_listed(self.page(PAGE)), {"R-K-AF", "R-K-ERA-A", "R4-LT", "R-T-VRAM2"})

    def test_a_page_with_no_differences_lists_nothing(self):
        text = "## Differences from the reference\n\nNone measured: every rule holds on zerobas.\n\n## Open\n"
        self.assertEqual(L.page_listed(self.page(text)), set())

    def test_a_run_file_without_one_cap_line_per_row_is_refused(self):
        d = tempfile.mkdtemp()
        bad = os.path.join(d, "BAD.out")
        open(bad, "w").write("===== probes/bios/spec/x.asm nodisk: A vs B =====\n"
                             "  CAP ref : 00\n")          # a header, no `CAP ours` line
        with self.assertRaises(SystemExit):
            L.live_run(bad, d)


if __name__ == "__main__":
    unittest.main()
