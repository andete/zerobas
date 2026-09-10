#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-PARENNEST — how deep can an ORDINARY nested expression go before the Z80
stack floor stops it, on all three machines?

Joost, 2026-09-10, reading the tier table: *"some of the tier 5 ones seem
fundamental/urgent, like 'THE Z80 STACK IS IN THE WRONG PLACE, AND THE DEF FN
CAP IS THE SYMPTOM'"*. He is right that the TIER is not settled by the one
symptom that has been measured. That block records `SP` at `$F2EA` with **234 B**
of headroom to `FN_STK_FLOOR`, and that zerobas never sets `SP` at all -- and the
same stack carries the expression evaluator's recursion, which every program
uses. Its own last line says what to measure first: *"how much of the ~78
B/level is evaluator recursion vs FN machinery"*.

\U0001f3af THIS RAMP ANSWERS THE TIER, NOT THE FIX. If a nested-parentheses
formula dies here at a depth a magazine listing plausibly uses (say < 16) while
both references survive it, the stack item is **TIER 1** -- a happy-path wrong
answer -- and SP relocation is tier-1 work. If zerobas matches the references to
a depth no ordinary program reaches, the item's only real symptom is the `FN`
cap and TIER 5 stands. Either way the tag is then a MEASUREMENT.

Three ladders, because "nested expression" is not one thing on the stack:
  p..  parentheses      PRINT ((((1+1)+1)+1)...)      -- pure evaluator recursion
  f..  function nesting PRINT ABS(ABS(ABS(...1...)))  -- function-call frames
  s..  string functions PRINT LEN(CHR$(ASC(CHR$(...)) -- the string engine's temps

Fenced with the row's own name, anchored after the last RUN, control row last:
`p08r` re-runs a passing depth after the failing ones with their error still on
the glass, and the run refuses to adjudicate if that row does not read its
value (D-FNNEST's readout lesson, twice in one day).
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                              # noqa: E402
import probe_sides                                            # noqa: E402


def prog(tag, expr):
    return ["10 ON ERROR GOTO 900",
            f'20 CLS:PRINT"[{tag} ";{expr};"]":END',
            f'900 CLS:PRINT"[{tag} ERR";ERR;"AT";ERL;"]":END',
            "RUN"]


def parens(n):     # ((((1+1)+1)+1)...)  -> value n+1
    return "(" * n + "1" + "+1)" * n


def absnest(n):    # ABS(ABS(...(1)...))  -> 1
    return "ABS(" * n + "1" + ")" * n


def strnest(n):    # LEN(CHR$(ASC(CHR$(...65...)))) -> 1 ; each level snapshots a temp
    return "LEN(" + "CHR$(ASC(" * n + "CHR$(65)" + "))" * n + ")"


DEPTHS = [8, 12, 16, 20, 24, 28, 32]
CASES = []
for n in DEPTHS:
    CASES.append((f"p{n:02d}", prog(f"p{n:02d}", parens(n))))
for n in DEPTHS:
    CASES.append((f"f{n:02d}", prog(f"f{n:02d}", absnest(n))))
for n in [4, 8, 12, 16, 18]:        # 20 would be a 261-char line; 18 is 239
    CASES.append((f"s{n:02d}", prog(f"s{n:02d}", strnest(n))))
CASES.append(("p08r", prog("p08r", parens(8))))          # the readout's control


def fence(tag, cap):
    c = cap or ""
    key = "[" + tag + " "
    i = c.rfind(key)
    if i < 0:
        return "<NO OWN FENCE>"
    j = c.find("]", i)
    return " ".join(c[i + len(key):j].split()) if j > 0 else "<UNTERMINATED>"


def main() -> int:
    for _, lines in CASES:
        assert all(len(l) <= 250 for l in lines), "a line is over the 255-char limit"
    SIDES = probe_sides.sides("vg8020", "cf3300", "zb")
    out = {}
    for name, m in SIDES.items():
        # \U0001f534 batch=False, MEASURED NECESSARY: the first run (batch=True)
        # lost every zb row from p16 on -- INCLUDING the p08r control that had
        # passed as p08 -- which is the signature of a machine that HUNG at p16
        # and never saw the next case's NEW. A fresh boot per case makes each
        # row its own machine, so a hang is a reading about ONE depth.
        out[name] = omsx_repl.run_cases(m["machine"], CASES, batch=False,
                                        boot=m["boot"], reset=m["reset"])
    got = {s: [fence(tag, out[s][i]) for i, (tag, _) in enumerate(CASES)] for s in SIDES}
    print("D-PARENNEST: nested-expression depth, three ladders, fenced by row name\n")
    for i, (tag, _) in enumerate(CASES):
        cells = "  ".join(f"{s}=[{got[s][i]:16}]" for s in SIDES)
        print(f"  {tag:5} {cells}")
        for s_ in SIDES:                       # the raw glass for any silent row
            if got[s_][i].startswith("<"):
                c = (out[s_][i] or "<NO DUMP>")
                rows = [c[k:k + 40].rstrip() for k in range(0, len(c), 40)]
                rows = [r for r in rows if r.strip() and "color" not in r]
                print(f"        {s_} glass: " + " / ".join(rows[-4:]))
    ctl = len(CASES) - 1
    print()
    if any(got[s][ctl] != "9" for s in SIDES):
        print("\U0001f534 THE READOUT'S CONTROL FAILED -- p08r must read 9 on every side. "
              "Nothing above is adjudicated.")
        return 2
    print("✅ readout control passes (p08r = 9 on all three sides)")
    diff = [tag for i, (tag, _) in enumerate(CASES)
            if got["zb"][i] != got["vg8020"][i] or got["zb"][i] != got["cf3300"][i]]
    print(f"=== {len(diff)} row(s) where zerobas differs from BOTH or either reference: "
          f"{diff or 'none'} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
