#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of kgosub_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control is
a rival rule the probe separates, run over the same reference cases; it must be FALSE on some of them.

    python3 probes/basic/spec/kgosub_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kgosub_model as M  # noqa: E402


def alt(*a):
    return lambda c: M.ok(c, frozenset(a))


CONTROLS = {
    "GOTO": [("R-GOTO-JUMP", "a GOTO inside a subroutine drops the GOSUB", alt("goto-drops-gosub")),
             ("R-GOTO-GOTO", "GO TO is not a synonym -- zerobas's before D-GOTOSPACE", alt("no-goto-space")),
             ("R-GOTO-NUMBER", "the number stops at a space", alt("no-join")),
             ("R-GOTO-NUMBER", "a number past 65529 is read whole (and is undefined)", alt("big-undefined")),
             ("R-GOTO-NUMBER", "anything after the number is error 2", alt("tail-syntax"))],
    "GOSUB": [("R-GOSUB-CALL", "a RETURN unwinds every GOSUB", alt("return-unwinds-all")),
              ("R-GOSUB-CALL", "the number stops at a space", alt("no-join")),
              ("R-GOSUB-ERRORS", "the frame is pushed before the line is looked up -- zerobas's",
               alt("gosub-frame-first"))],
    "RETURN": [("R-RETURN-BACK", "RETURN n keeps the subroutine open", alt("return-n-keeps-frame")),
               ("R-RETURN-FRAMES", "RETURN drops only its GOSUB, the FOR frames stay", alt("return-keeps-for")),
               ("R-RETURN-FRAMES", "NEXT reaches a FOR below the GOSUB", alt("next-crosses-gosub")),
               ("R-RETURN-ERRORS", "RETURN reads its line number before checking for a GOSUB", alt("return-line-first")),
               ("R-RETURN-ERRORS", "RETURN n looks the line up before closing", alt("return-missing-keeps"))],
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
