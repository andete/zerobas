#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-RUNGAP — how much EMULATED time the three-PUT program actually needs, in
the harness's own units, without trusting the guest's clock.

Three causes have been eliminated for why those rows read `<NO OUTPUT>` at
`step=2.5`: execution (D-PUTCOST: the guest's `TIME` says 0.12 s), line entry
(D-LINEENTRY: the LISTING is 6/6 intact at that step), and the reader (the
screen shows `ZBRUN` and then nothing). What was left was "the wall time between
`RUN` and the first output character", and I said it needed a host-side timer.

🎯 IT DOES NOT — THE HARNESS ALREADY HAS THE RIGHT KNOB, AND ITS OWN COMMENT
SAYS SO: *"the window a case's budget actually buys between RUN and capture is
exactly `step`"*, and `run_gap` exists to separate that completion budget from
the inter-line typing spacing. So the question "how long does this program need
after RUN" is answered by finding the smallest `run_gap` at which the output
appears — a measurement in EMULATED seconds, directly comparable between
machines, and immune to whatever the guest's JIFFY counter does or does not
count.

🔴 WHICH MATTERS, BECAUSE `TIME` IS A SUSPECT. JIFFY is advanced by the VBlank
interrupt handler, and disk routines run stretches with interrupts DISABLED — so
a `TIME` delta can under-count exactly the interval this question is about.
D-PUTCOST's "1.71 ticks per PUT" may be true and blind at the same time. This
probe does not depend on it either way.

⚠️ `step` IS HELD AT 2.5 THROUGHOUT — the failing value. If a longer `run_gap`
alone fixes the row, the cost is in COMPLETION and typing was never the issue;
if it does not, `run_gap` is not the axis and that is a finding too.
"""
from __future__ import annotations

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import omsx_repl                                                  # noqa: E402
import probe_tmp                                                  # noqa: E402
import basic_probe_fldwidth as F                                  # noqa: E402

STEP = 2.5
GAPS = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 16.0)
RD = 'GET#1,6:PRINT"[";LEFT$(A$,1);MID$(A$,50,1);RIGHT$(A$,1);"]"'

PROG = ['CLEAR 1000',
        'OPEN"TS.DAT"AS #1 LEN=128',
        'FIELD#1,128 AS A$',
        'LSET A$=STRING$(128,"A"):PUT#1,5',
        'LSET A$=STRING$(128,"B"):PUT#1,6',
        'LSET A$=STRING$(128,"C"):PUT#1,7',
        RD]
# 🔴 THE LADDER, AND ITS CONTROL. One, two and three PUTs with everything else
# identical. Without the short rungs a rising run_gap says nothing about the
# WRITES -- it could be the OPEN, the FIELD or the CLEAR -- and with them the
# ladder answers the question the original filing asked and D-PUT3SLOW
# explicitly declined to claim: is the THIRD put individually slower, or do
# three ordinary writes simply add up?
# ⚠️ THE EXPECTED VALUE IS PER CASE. The first cut asked every rung for `BBB`,
# which is record 6's content -- so the one-PUT rung, which writes "A", was
# scored as NEVER COMPLETING at any gap while it was in fact reading `AAA` at
# the smallest one. A fixture fault presented as a machine bound
# [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
def ladder(n):
    head = ['CLEAR 1000', 'OPEN"TS.DAT"AS #1 LEN=128', 'FIELD#1,128 AS A$']
    body = [f'LSET A$=STRING$(128,"{c}"):PUT#1,{5 + i}'
            for i, c in enumerate("ABC"[:n])]
    return head + body + ['GET#1,%d:PRINT"[";LEFT$(A$,1);MID$(A$,50,1);'
                          'RIGHT$(A$,1);"]"' % (5 + n - 1)]


LADDER = [(f"{n} PUT{'s' if n > 1 else ' '}", ladder(n), "ABC"[n - 1] * 3)
          for n in (1, 2, 3)]


def run(side, lines, gap):
    cfg = F.SIDES[side]
    kw = {}
    if cfg["diska"]:
        dsk = probe_tmp.tmp(f"rungap_{side}_{len(lines)}_{gap}.dsk")
        shutil.copy(os.path.join(ROOT, "disk", "test720.dsk"), dsk)
        kw["diska"] = dsk
    body = [f"{10 * (k + 1)} {ln}" for k, ln in enumerate(lines)]
    caps = omsx_repl.run_cases(
        cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
        batch=False, reset=(), boot=cfg["boot"], step=STEP, run_gap=gap,
        timeout=900.0, **kw)
    return F.bracket(caps[0])


def sweep(side, lines, want):
    """The smallest run_gap at which the row READS. None = needs more than the
    largest tried, which is a bound and is reported as one."""
    for g in GAPS:
        got = run(side, lines, g)
        ok = got == want
        print(f"    run_gap={g:5.1f}  {str(got):>14}   {'ok' if ok else ''}")
        if ok:
            return g
    return None


def main():
    print(f"\nstep held at {STEP} (the FAILING value) throughout; only run_gap moves.\n")
    res = {}
    for tag, lines, want in LADDER:
        for side in ("cf3300", "zb"):
            print(f"  {tag} on {side} (want {want}):")
            res[(tag, side)] = sweep(side, lines, want)
            print()
    print("smallest run_gap that completes (emulated seconds):")
    print(f"    {'':18} {'cf3300':>10} {'zb':>10}")
    for tag, _, _ in LADDER:
        a, b = res[(tag, "cf3300")], res[(tag, "zb")]
        f = lambda v: f">{GAPS[-1]}" if v is None else f"{v}"    # noqa: E731
        print(f"    {tag:18} {f(a):>10} {f(b):>10}")
    # 🔴 A BOUND IS NOT A NUMBER. If either side never completed, say so
    # rather than letting the table imply a measured value.
    if any(v is None for v in res.values()):
        print(f"\n⚠️ at least one row never completed within {GAPS[-1]}s; those "
              f"cells are BOUNDS, not measurements.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
