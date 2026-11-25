#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of kstop_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control is
a rival rule the probe separates, run over the same reference cases; it must be FALSE on some of them.

    python3 probes/basic/spec/kgosub_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kstop_model as M  # noqa: E402


def alt(*a):
    return lambda c: M.ok(c, frozenset(a))


CONTROLS = {
    "END": [("R-END-STOP", "CONT after END cannot continue", alt("cont-after-end-cant"))],
    "STOP": [("R-STOP-BREAK", "STOP in direct mode prints nothing", alt("stop-direct-silent")),
             ("R-STOP-CONT", "CONT repeats the statement before the STOP", alt("cont-from-stmt-start"))],
    "CONT": [("R-CONT-WHEN", "CONT after an error cannot continue", alt("cont-after-error-cant")),
             ("R-CONT-WHEN", "a direct statement in between blocks CONT", alt("direct-blocks-cont")),
             ("R-CONT-WHEN", "an added line keeps CONT possible", alt("edit-keeps-cont"))],
    "RUN": [("R-RUN-CLEAR", "RUN keeps the variables", alt("run-keeps-vars"))],
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
