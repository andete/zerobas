#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of kif_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control is
a rival rule the probe separates, run over the same reference cases; it must be FALSE on some of them.

    python3 probes/basic/spec/kif_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kif_model as M  # noqa: E402


def alt(*a):
    return lambda c: M.ok(c, frozenset(a))


CONTROLS = {
    "IF": [("R-IF-TRUTH", "a fraction is false (cut to its whole part)", alt("fraction-false")),
           ("R-IF-TRUTH", "a string comparison is always true", alt("string-compare-true")),
           ("R-IF-TRUTH", "any non-zero byte makes a number true", alt("any-byte")),
           ("R-IF-LINE", "a false IF skips only THEN's statement", alt("false-skips-then-only")),
           ("R-IF-JUMP", "a missing line is error 8 even when not taken", alt("missing-line-always-8")),
           ("R-IF-JUMP", "IF ... GOTO needs a line number", alt("goto-needs-number")),
           ("R-IF-ELSE", "an ELSE reached by a true IF runs its part too", alt("else-as-stmt-runs")),
           ("R-IF-ELSE", "only an IF directly after THEN / ELSE opens a level", alt("nest-after-then-only")),
           ("R-IF-ELSE", "a constant's byte can be taken for IF / ELSE", alt("byte-scan")),
           ("R-IF-EMPTY", "THEN followed by nothing is a Syntax error", alt("empty-then-syntax")),
           ("R-IF-ERRORS", "RESUME NEXT goes on only at the next `:`", alt("resume-colon-only")),
           ("R-IF-ERRORS", "a condition that failed counts as false", alt("error-counts-false"))],
}


def main():
    rc = 0
    for kw, ctl in CONTROLS.items():
        cs = M.load(kw)["ref"]
        rules = {r.id: r for r in M.rules(kw)}
        for rid, what, check in ctl:
            sel = [c for c in cs if rules[rid].select(c)]
            false = [c.id for c in sel if not check(c)]
            print(f"{rid:16s} {what[:62]:62s} FALSE on {len(false):3d} of {len(sel):<3d}"
                  f"{'  e.g. ' + false[0] if false else '  <-- NO CASE AGAINST IT'}")
            rc |= not false
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
