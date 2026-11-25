#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of kstop_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control is
a rival rule the probe separates, run over the same reference cases; it must be FALSE on some of them.

    python3 probes/basic/spec/kstop_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kstop_model as M  # noqa: E402


def alt(*a):
    return lambda c: M.ok(c, frozenset(a))


CONTROLS = {
    "END": [("R-END-STOP", "CONT after END cannot continue", alt("cont-after-end-cant")),
            ("R-END-STOP", "CONT after END goes on at the next LINE", alt("cont-after-end-next-line")),
            ("R-END-STOP", "END drops a pending GOSUB", alt("end-drops-gosub")),
            ("R-END-CLOSE", "END leaves files open -- zerobas's (and the CF-3300 page claim's)", alt("end-keeps-files"))],
    "STOP": [("R-STOP-BREAK", "STOP in direct mode prints nothing", alt("stop-direct-silent")),
             ("R-STOP-BREAK", "Break in names the program's first line", alt("break-first-line")),
             ("R-STOP-CONT", "CONT repeats the STOP itself", alt("cont-from-stmt-start")),
             ("R-STOP-CONT", "STOP finishes an error handler", alt("stop-ends-handler"))],
    "CONT": [("R-CONT-WHEN", "an edit keeps CONT possible", alt("edit-keeps-cont")),
             ("R-CONT-WHEN", "an edit keeps the variables", alt("edit-keeps-vars")),
             ("R-CONT-WHEN", "CLEAR keeps the resume point", alt("clear-keeps-cont")),
             ("R-CONT-WHEN", "RUN drops the resume point only once its line is found -- zerobas's",
              alt("run-drops-cont-late")),
             ("R-CONT-WHEN", "a direct statement in between blocks CONT", alt("direct-blocks-cont")),
             ("R-CONT-WHEN", "a typed error drops the resume point", alt("direct-error-drops-cont")),
             ("R-CONT-WHEN", "a failed delete drops the resume point", alt("delete-missing-drops-cont")),
             ("R-CONT-WHERE", "CONT after an error cannot continue", alt("cont-after-error-cant")),
             ("R-CONT-WHERE", "CONT after an error prints the stored error again", alt("cont-after-error-reprint")),
             ("R-CONT-WHERE", "CONT after the end of the program cannot continue", alt("run-end-cant"))],
    "RUN": [("R-RUN-START", "RUN n inside a program is GOTO n (no clearing)", alt("run-n-goto")),
            ("R-RUN-CLEAR", "RUN keeps the variables", alt("run-keeps-vars")),
            ("R-RUN-CLEAR", "RUN keeps the DATA pointer", alt("run-keeps-data")),
            ("R-RUN-CLEAR", "RUN keeps ON ERROR", alt("run-keeps-onerror")),
            ("R-RUN-CLEAR", "RUN keeps open files", alt("run-keeps-files")),
            ("R-RUN-CLEAR", "the end of a run clears the variables", alt("run-end-clears"))],
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
        bare = sorted(set(rules) - {rid for rid, _, _ in ctl})    # every rule pinned by a control of its own
        for rid in bare:
            print(f"{rid:16s} 🔴 NO CONTROL OF ITS OWN")
        rc |= bool(bare)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
