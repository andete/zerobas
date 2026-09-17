#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-LONGRUN -- the question `pair_carve_scout.py` structurally cannot ask.

That tool sweeps runs of 2..5 instructions and DISCARDS every run seen at fewer
than 8 sites (`if n < 8: continue`). Both bounds hide the same shape, and it is
the shape that pays most per site:

    net = n * (cost - 3) - (cost + 1)

is linear in n but ALSO linear in cost, so a 12-byte run at 4 sites (net 27)
beats a 4-byte run at 10 sites (net 5) five times over. Long runs are RARER by
construction -- a 12-gram repeats less often than a pair -- so a fixed 8-site
floor is exactly the filter that removes them. 2026-09-17: with every route in
[[carve-routes-measured-shut]] re-run and the best pair worth 5 B, this is the
only unasked question left in the mechanical family.

It reuses pair_carve_scout's own `runs()`, `isize()`, `relative()` and
sub-included exclusion, so the two tools agree on every shared judgement and
this file adds ONLY the thresholds. 🎯 That is deliberate: a second normaliser
would be a second set of bugs, and the 2026-09-09 IX/IY under-count shows the
sizer is the part that goes wrong.

⚠️ EVERY CAVEAT ON THE PARENT STILL APPLIES AND IS NOT REPEATED IN THE OUTPUT:
runs OVERLAP (a 12-gram contains two 11-grams; savings are NOT additive), `net`
is a CEILING that assumes a helper which cannot fall through, `sites` counts
SOURCE lines so a site inside an `IF` that is off costs and saves nothing, and
the three hazards in the parent's docstring are unpriced. Read it first.

🔴 AND A LONG RUN IS LESS LIKELY TO BE FOLDABLE THAN A SHORT ONE, for a reason
the arithmetic does not show: the longer the run, the more likely it spans a
point some OTHER code jumps into, and the more likely one of its instructions is
position-dependent. This tool ranks CANDIDATES; every row still has to be read.

--selftest plants a long run at 3 sites and asserts it is ranked above a short
run at 9 -- i.e. that the bound this file exists to remove is actually removed.
"""
from __future__ import annotations

import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
_spec = importlib.util.spec_from_file_location("pcs", "scratchpad/pair_carve_scout.py")
pcs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pcs)


def score(files, upto, minsites):
    out = []
    for run, n in pcs.runs(files, upto).items():
        if n < minsites:
            continue
        cost = sum(pcs.isize(i) for i in run)
        out.append((n * (cost - 3) - (cost + 1), n, cost, run))
    out.sort(reverse=True)
    return out


def selftest() -> int:
    long_run = ["ld hl,(a1)", "ld de,(a2)", "call sub16", "ld (a3),hl",
                "ld a,(a4)", "or a", "ld hl,(a5)", "call emit"]
    files = {}
    for i in range(3):
        files[f"L{i}.asm"] = [f"lab{i}:"] + ["                " + x for x in long_run]
    for i in range(9):
        files[f"S{i}.asm"] = [f"sab{i}:", "                inc hl",
                             "                ld a,(hl)", "                ret"]
    fails = []
    top = score(files, 12, 3)
    if not top:
        fails.append("nothing ranked at all -- runs() or the thresholds are broken")
    else:
        best = top[0]
        if len(best[3]) < 8:
            fails.append("the 8-instruction run at 3 sites did not rank first -- "
                         "the site floor this file exists to remove is still there")
        if best[0] <= 0:
            fails.append("a long run at 3 sites priced <= 0; the net formula is wrong")
    # the parent's own bound must still exclude it, or there is nothing new here
    if score(files, 5, 8) and len(score(files, 5, 8)[0][3]) >= 8:
        fails.append("the parent's bounds would have found it -- this tool is redundant")
    if fails:
        print("\U0001f534 SELFTEST FAILED")
        for f in fails:
            print("   ", f)
        return 2
    print("selftest: a long run at 3 sites outranks a short run at 9, and the "
          "parent's own bounds miss it ✅")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    upto, minsites, top = 12, 3, 30
    for a in sys.argv[1:]:
        if a.startswith("--upto="):
            upto = int(a.split("=", 1)[1])
        elif a.startswith("--min-sites="):
            minsites = int(a.split("=", 1)[1])
        elif a.startswith("--top="):
            top = int(a.split("=", 1)[1])
    SUB = pcs.sub_included()
    files = {}
    for f in sorted(os.listdir("basic")):
        if f.endswith((".asm", ".inc")) and f not in SUB:
            files[f] = open(os.path.join("basic", f), encoding="utf-8").read().splitlines()
    scored = score(files, upto, minsites)
    print(f"basic/ files swept: {len(files)}   (excluded as sub-included: {len(SUB)})")
    print(f"runs of 2..{upto} instructions at {minsites}+ sites: {len(scored)}")
    print(f"\n{'net':>5} {'sites':>5} {'B':>3} {'k':>2}  run")
    live = 0
    for net, n, cost, run in scored[:top]:
        note = ""
        if pcs.relative(run):
            note = "   \U0001f534 RELATIVE JUMP INSIDE -- cannot fold"
        elif net > 0:
            live += 1
        print(f"{net:5d} {n:5d} {cost:3d} {len(run):2d}  " + "  |  ".join(run) + note)
    if not scored:
        print("   (nothing at those thresholds)")
    print(f"\n{live} of the top {min(top, len(scored))} can pay for themselves.")
    print("\U0001f534 READ scratchpad/pair_carve_scout.py's DOCSTRING FIRST -- overlap, "
          "the net ceiling, the source-line site count and the three hazards all "
          "apply here unchanged and are not restated per row.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
