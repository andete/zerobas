#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of kerr_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control flips
ONE law of the shared small BASIC (kstop_model's `alt` switches) and runs over the reference's cases; it must be FALSE
on some of them.

    python3 probes/basic/spec/kerr_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kerr_model as M  # noqa: E402


def alt(*a):
    return lambda c: M.ok(c, frozenset(a))


CONTROLS = {
    "ERROR": [("R-ERROR-RAISE", "an error typed at the prompt never reaches a handler", alt("typed-errors-untrapped")),
              ("R-ERROR-RAISE", "code 22 itself is never trapped", alt("code22-untrapped")),
              ("R-ERROR-CODE", "the code is rounded, not cut", alt("error-code-rounds")),
              ("R-ERROR-CODE", "Overflow only past 65535", alt("error-bound-65535")),
              ("R-ERROR-CODE", "a comma after the code is error 2 at once", alt("error-comma-first"))],
    "ERR": [("R-ERR-VALUE", "RESUME keeps ERR", alt("resume-keeps-err")),
            ("R-ERR-KEPT", "RUN, CLEAR, NEW and an edit clear ERR and ERL", alt("reset-clears-err")),
            ("R-ERR-SYNTAX", "ERR takes a number after it", alt("err-tail-ok"))],
    "ERL": [("R-ERL-LINE", "an error typed at the prompt leaves ERL 0", alt("typed-erl-zero"))],
    "RESUME": [("R-RESUME-FORMS", "RESUME NEXT always goes to the next line", alt("resume-next-next-line")),
               ("R-RESUME-FORMS", "RESUME to a missing line stops -- zerobas's, which hung", alt("resume-missing-silent")),
               ("R-RESUME-HANDLER", "RESUME's own error is trapped too", alt("resume-error-trapped")),
               ("R-RESUME-HANDLER", "END inside a handler disarms ON ERROR", alt("end-disarms-handler")),
               ("R-RESUME-HANDLER", "an error typed at the prompt never reaches a handler", alt("typed-errors-untrapped")),
               ("R-RESUME-HANDLER", "an error inside the handler enters it again", alt("handler-traps-own")),
               ("R-RESUME-HANDLER", "an untrapped stop leaves the handler active", alt("untrapped-keeps-handler")),
               ("R-RESUME-FRAMES", "RESUME drops the frames opened since the error", alt("resume-drops-frames")),
               ("R-RESUME-ONERROR", "GOTO 0 inside a handler only disarms", alt("onerr0-just-disarms")),
               ("R-RESUME-ONERROR", "a missing handler line is found only at the error", alt("onerr-missing-late")),
               ("R-RESUME-ONERROR", "a non-number after GOTO is error 2 at once -- zerobas's", alt("onerr-var-syntax"))],
}


def main():
    rc = 0
    for kw, ctl in CONTROLS.items():
        cs = M.load(kw)["ref"]
        rules = {r.id: r for r in M.rules(kw)}
        for rid, what, check in ctl:
            sel = [c for c in cs if rules[rid].select(c)]
            false = [c.id for c in sel if not check(c)]
            print(f"{rid:18s} {what[:62]:62s} FALSE on {len(false):3d} of {len(sel):<3d}"
                  f"{'  e.g. ' + false[0] if false else '  <-- NO CASE AGAINST IT'}")
            rc |= not false
        bare = sorted(set(rules) - {rid for rid, _, _ in ctl})    # every rule pinned by a control of its own
        for rid in bare:
            print(f"{rid:18s} 🔴 NO CONTROL OF ITS OWN")
        rc |= bool(bare)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
