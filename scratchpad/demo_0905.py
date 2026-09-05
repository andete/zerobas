#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""The 2026-09-05 closing demo — one MSX BASIC program over the day's BASIC work.

The standing rule is that a session ends in real MSX BASIC, run on BOTH
references and on zerobas. Today shipped three user-visible changes; this program
exercises the two that a running program can show:

    D-UNARYPLUS   `A=+1` and friends were ERR 2 here and legal on both refs
    D-CSAVEEXPR   `CSAVE 5` was a non-raising `load error` here, `Type mismatch`
                  there -- the last `cp '"'` filename gate in the tree

⚠️ THE THIRD (D-TXTCEIL, a line store growing past HIMEM into the string pool) is
NOT here and cannot be: it is about what happens while lines are TYPED, so no
program can print it. `make txtceil-acceptance` is its row.

⚠️ AND `+2^2` IS IN THE PROGRAM WITHOUT BEING A DISCRIMINATOR, which is worth
saying rather than leaving to be discovered: unary plus is the identity, so it
reads 4 whether `+` binds like unary minus (which takes the power first) or
looser. It is here because it was measured, not because it decides anything.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": ("Philips_VG_8020", 8.0, ("NEW",)),
    "cf3300": ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW")),
    "zb": (ZB, 8.0, ("NEW",)),
}
PROG = [
    "10 ON ERROR GOTO 90",
    '20 A=+1:PRINT"[A";A;"]"',
    '30 B=1:PRINT"[B";+B;"]"',
    '40 PRINT"[C";1++2;"]"',
    '50 PRINT"[D";+2^2;"]"',
    "60 CSAVE 5",
    '70 PRINT"[E";0;"]":END',
    '90 PRINT"[E";ERR;"]":END',
]
KEYS = "ABCDE"
# What the same five readings were BEFORE today, measured and committed:
#   scratchpad/uplus_before2.out  (A/B/C/D: ERR 2 on zb, values on both refs)
#   scratchpad/csaveexpr_now.out  (E: `load error`, non-raising, so ERR stayed 0)
BEFORE_ZB = {"A": "ERR 2", "B": "ERR 2", "C": "ERR 2", "D": "ERR 2",
             "E": "0 (a PRINTED `load error`, never raised)"}


def run(side):
    machine, boot, reset = SIDES[side]
    raw = "".join(omsx_repl.run_cases(
        machine, [("direct", list(reset) + PROG + ["RUN"])], batch=False,
        reset=(), boot=boot, step=6.0, cap_gap=12.0, timeout=400.0)[0] or "")
    rows = [raw[i * 40:(i + 1) * 40].strip() for i in range(24)]
    out = {}
    for k in KEYS:
        # only rows that BEGIN with the fence -- the echo of the PRINT line
        # carries it too, and reading that reports the typed text as a value.
        m = [mm for r in rows if r.startswith(f"[{k}")
             for mm in re.findall(rf"^\[{k}\s*(-?\d+)\s*\]", r)]
        out[k] = m[-1] if m else None
    return out


def main() -> int:
    print("\n" + "\n".join(PROG) + "\nRUN\n")
    got = {s: run(s) for s in SIDES}
    blind = sum(1 for s in SIDES for k in KEYS if got[s][k] is None)
    print(f"{'':4s} {'vg8020':>8s} {'cf3300':>8s} {'zb':>8s}   "
          f"{'zb BEFORE today':<38s} what it is")
    WHAT = {"A": "A=+1            unary plus, LET",
            "B": "+B              unary plus on a variable",
            "C": "1++2            binary + then unary +",
            "D": "+2^2            (identity: NOT a binding discriminator)",
            "E": "CSAVE 5         the filename is an EXPRESSION now"}
    for k in KEYS:
        v = [got[s][k] if got[s][k] is not None else "----" for s in
             ("vg8020", "cf3300", "zb")]
        print(f"{k:4s} {v[0]:>8s} {v[1]:>8s} {v[2]:>8s}   "
              f"{BEFORE_ZB[k]:<38s} {WHAT[k]}")
    if blind:
        print(f"\n\U0001f534 INSTRUMENT FAULT: {blind} cell(s) unread. A demo that "
              f"could not read itself is not a demo.")
        return 2
    agree = all(got["vg8020"][k] == got["cf3300"][k] == got["zb"][k]
                for k in KEYS)
    print(f"\n{'\U0001f7e2 all three machines agree on all five' if agree else '\U0001f534 NOT all three agree'}"
          f" — and every one of the five was a zerobas DIVERGENCE this morning.")
    return 0 if agree else 1


if __name__ == "__main__":
    raise SystemExit(main())
