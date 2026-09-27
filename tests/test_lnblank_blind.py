# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: lnblank's SAY_ONLY reader keeps the span reader's reason, and a
row with no reading on ANY side is refused, not reported as agreement.

🔴 D-NAMBLANK found a `--say` payload with no brackets reading `<none>` on
EVERY side -- and sides that all failed compare EQUAL and report *agrees*.
D-SPANWHY gave `result_span` a `why` channel; nothing passed it. D-SAYBLIND
(2026-09-27) makes `basic_probe_lnblank.py` pass it, and while doing so found
the same shape through a SECOND sentinel: `<NO ECHO>`, described as "fatal" in
the TAIL_ONLY reader, was not in `BAD`.

The NEGATIVE arms are the point: a blind row must be REFUSED, and a row where
only ONE side lost its reading must NOT be (that is a divergence, a finding).
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))

import omsx_repl  # noqa: E402
import basic_probe_lnblank as lb  # noqa: E402

COLS = omsx_repl.COLS


def screen(*rows):
    return "".join(r.ljust(COLS)[:COLS] for r in rows)


def run():
    fails = 0

    def check(ok, label, detail=""):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label:60}" + ("" if ok else f"  {detail}"))

    cmd = 'PRINT"[";7;"]"'
    check(lb.say_span(screen("Ok", cmd, "[ 7 ]", "Ok"), cmd) == " 7 ",
          "a bracketed payload reads its value")
    nob = lb.say_span(screen("Ok", "PRINT 7", " 7", "Ok"), "PRINT 7")
    check(nob.startswith(lb.NO_READING) and "no bracket" in nob,
          "a bracketless payload is a NO-READING, and says why", repr(nob))
    ab = lb.say_span(screen("Ok", cmd, "[ 7", "Syntax error"), cmd)
    check(ab.startswith(lb.NO_READING) and "aborted" in ab,
          "an unterminated '[' is a NO-READING, and says aborted", repr(ab))
    check(nob != ab, "the two no-reading shapes stay DIFFERENT values")
    check(lb.say_span(None, cmd) == "NOCAPTURE", "no capture is NOCAPTURE")
    ne = lb.say_span(screen("Ok", "SOMETHING ELSE"), cmd)
    check(ne == "<NO ECHO>" and lb.is_bad(ne),
          "a missing echo row is <NO ECHO>, and is_bad refuses it", repr(ne))

    # --- the guard -------------------------------------------------------------
    check(lb.blind({nob}), "NEGATIVE: every side no-bracket -> BLIND (refused)")
    check(lb.blind({nob, ab}), "NEGATIVE: mixed no-reading shapes -> BLIND")
    check(not lb.blind({nob, " 7 "}),
          "one side lost its reading -> NOT blind (a divergence, a finding)")
    check(not lb.blind({" 7 "}), "a real agreeing reading is not blind")
    check(not lb.blind(set()), "no values at all is not blind (ungated, elsewhere)")

    print()
    print("ALL PASS — a say row with no reading anywhere is refused, not agreed"
          if not fails else f"{fails} CHECK(S) FAILED")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(run())
