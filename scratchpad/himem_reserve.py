#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-TXTCEIL: what does the reference RESERVE below HIMEM? Measured, not modelled.

D-TXTCEIL round 4 built the whole line-store ceiling and found the VALUE wrong:
`strheap_varceil()` = `min(HIMEM,TXTMAX) − POOLSIZE − MAXF×FCH_CTXSZ` leaves
**642 B** of program headroom where both references leave **148**, on the same
`CLEAR 300,TXTTAB+1000` fixture. Roughly 500 B are reserved by the reference and
not by that formula. This measures WHAT.

🎯 THE QUESTION IS THE SHAPE OF THE RESERVE, NOT ONE NUMBER. One fixture cannot
tell a CONSTANT reserve from one that scales with the string pool or with the
distance HIMEM was moved — and picking either from a single reading is the error
this item has already made once. So the sweep varies both knobs independently:

    CLEAR <pool>, TXTTAB + <gap>

  * gap 1000 vs 1500 with pool fixed  -> does headroom track the GAP 1:1?
  * pool 100 / 300 / 500 with gap fixed -> does headroom track the POOL 1:1?

A reserve that is CONSTANT shows as `headroom = gap − pool − R` with the same `R`
in every row. Anything else says the formula needs a term neither knob is.

⚠️ `FRE(0)` IS THE READOUT AND IT IS NOT THE SAME QUESTION AS "will this line
store". `FRE(0)` reports free program/variable space; the store check is a
separate comparison. Both are printed per row rather than one being taken for the
other, because the whole defect here is a ceiling that disagrees with what the
machine will actually accept.

⚠️ zerobas is run alongside, unchanged, so the gap is visible per row rather than
inferred from the single filed fixture.
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
# (label, pool, gap, maxfiles)
# 🔴 MAXFILES IS THE THIRD KNOB AND LEAVING IT OUT WOULD HAVE SHIPPED A
# CONSTANT THAT IS REALLY A FORMULA. Round 1 of this sweep varied pool and gap
# only, found R constant at 560 on both references, and that is EXACTLY what
# `R = base + MAXFILES*buf` looks like when MAXFILES never moves. zerobas's own
# R of 62 already contains `MAXF*FCH_CTXSZ` = 50, so the term demonstrably exists
# on at least one of the three machines
# [[two-rules-that-coincide-on-every-row-you-have]].
CASES = [
    ("g1000.p300.f1", 300, 1000, 1),   # the filed fixture: refs read 140
    ("g1500.p300.f1", 300, 1500, 1),   # + 500 of gap
    ("g2000.p300.f1", 300, 2000, 1),   # + 1000 of gap
    ("g1500.p100.f1", 100, 1500, 1),   # - 200 of pool
    ("g1500.p500.f1", 500, 1500, 1),   # + 200 of pool
    ("g1500.p300.f2", 300, 1500, 2),   # 🎯 the separator: one more channel
    ("g1500.p300.f4", 300, 1500, 4),   # ...and three more, so the STEP is visible
]


def run(side, pool, gap, mf):
    machine, boot, reset = SIDES[side]
    # ⚠️ MAXFILES BEFORE CLEAR: it moves HIMEM's usable top itself, and the
    # `A=PEEK(TXTTAB)` read has to happen after any statement that could relocate
    # the text base.
    prog = [f"MAXFILES={mf}",
            "A=PEEK(&HF676)+256*PEEK(&HF677)",
            f"CLEAR {pool},A+{gap}",
            "99 REM Z",
            'PRINT"[F";FRE(0);"]"']
    raw = "".join(omsx_repl.run_cases(
        machine, [("direct", list(reset) + prog)], batch=False, reset=(),
        boot=boot, step=6.0, cap_gap=10.0, timeout=300.0)[0] or "")
    rows = [raw[i * 40:(i + 1) * 40].strip() for i in range(24)]
    # Only rows that BEGIN with the fence: an echo of the PRINT line contains it
    # too, and reading that would report the typed text as a value.
    m = [mm for r in rows if r.startswith("[F")
         for mm in re.findall(r"^\[F\s*(-?\d+)\s*\]", r)]
    return int(m[-1]) if m else None


def main() -> int:
    print(f"\n{'case':15s} {'pool':>5s} {'gap':>5s} {'mf':>3s} "
          f"{'vg8020':>8s} {'cf3300':>8s} {'zb':>8s}   reserve R = gap-pool-FRE")
    blind = 0
    rows = []
    for lab, pool, gap, mf in CASES:
        v = {s: run(s, pool, gap, mf) for s in SIDES}
        blind += sum(1 for x in v.values() if x is None)
        rows.append((lab, pool, gap, mf, v))
        r = {s: (gap - pool - x if x is not None else None) for s, x in v.items()}
        fmt = lambda x: "----" if x is None else f"{x}"
        print(f"{lab:15s} {pool:>5d} {gap:>5d} {mf:>3d} "
              f"{fmt(v['vg8020']):>8s} {fmt(v['cf3300']):>8s} {fmt(v['zb']):>8s}"
              f"   R: vg={fmt(r['vg8020'])} cf={fmt(r['cf3300'])} zb={fmt(r['zb'])}")
    # 🔴 A NEGATIVE RESERVE IS AN OUT-OF-DOMAIN ROW, NOT A SMALL ONE. On the
    # references `MAXFILES=4` needs more than a 1500-byte gap can hold, so the
    # CLEAR errors and FRE reports the UN-CLEARED machine -- 28006 on the
    # VG-8020, which computes to R = -26806. Printing that beside 560 and 827 as
    # if all three were readings is how a sweep launders a failure into a trend.
    oor = [(lab, s_, gap - pool - v[s_])
           for lab, pool, gap, _m, v in rows for s_ in SIDES
           if v[s_] is not None and gap - pool - v[s_] < 0]
    if oor:
        print("\n⚠️ OUT OF DOMAIN (reserve computes NEGATIVE -- the CLEAR did not "
              "take, so FRE is the un-CLEARed machine). Excluded from the model:")
        for lab, s_, r in oor:
            print(f"    {lab:15s} {s_:7s} R={r}")
        rows = [(lab, pool, gap, m, v) for lab, pool, gap, m, v in rows
                if all(gap - pool - v[s_] >= 0 for s_ in SIDES
                       if v[s_] is not None)]
    if blind:
        print(f"\n🔴 INSTRUMENT FAULT: {blind} cell(s) produced no reading. "
              f"Refused -- a missing FRE is not a small one.")
        return 2
    Rs = {s: {gap - pool - v[s] for _l, pool, gap, _m, v in rows} for s in SIDES}
    bymf = {s: {m: gap - pool - v[s] for _l, pool, gap, m, v in rows} for s in SIDES}
    print()
    for s in ("vg8020", "cf3300", "zb"):
        vals = sorted(Rs[s])
        verdict = ("CONSTANT" if len(vals) == 1 else f"VARIES over {vals}")
        print(f"  {s:7s} reserve {verdict}   per MAXFILES: "
              + ", ".join(f"{m}->{r}" for m, r in sorted(bymf[s].items())))
    print("\n🎯 Read the two references first: if R is constant on both, the "
          "\n   ceiling is `min(HIMEM,TXTMAX) - POOLSIZE - R` and R is a number to "
          "\n   hardcode. If it varies, the missing term is neither knob.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
