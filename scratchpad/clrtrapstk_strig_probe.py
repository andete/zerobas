#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""Does the CLEAR/TRAPSTK defect reproduce on STRIG? The shared-code argument, 3 of 4.

TODO.md's "`KEY / STRIG / SPRITE / STOP` were NOT run against the D-TRAPSVC rows"
covers four traps by a CODE argument -- *"they share `check_traps`, `ct_find`,
`set_state` and `trap_return_check` verbatim; the index is a parameter"*.
`SPRITE` was converted 2026-08-26 and **diverged** (1 vs 250 in
`CLEAR, still SERVICING`); `STOP` was converted 2026-09-05 and **did not**. Two
verbs through the one routine already gave different answers, so the third is not
a formality -- it is the tie-breaker on how far the sharing actually reaches.

🎯 THE APPARATUS IS IMPORTED, NOT COPIED. `basic_probe_strig_trap.py` presses
trigger 0 -- which IS the SPACE key, keyboard matrix row 8 bit 0 -- through
openMSX `keymatrixdown`/`keymatrixup`, injects through KEYBUF and gates every
reading on a `done` sentinel. Its `run()`, `kdown()`/`kup()` and `TWO_TAPS`
schedule are used verbatim; a second copy would sit outside `make latch-check`.

🔴 THE POSITIVE CONTROL IS NOT OPTIONAL, AND THE STOP RUN IS WHY. Its first
attempt read 1 in all four cells -- which is what the REFERENCE correctly reads
(a trap left SERVICING does not re-fire until `RETURN`) and ALSO exactly what a
second tap that never landed reads. One number, two causes. STRIG fires once per
EDGE, like STOP and unlike SPRITE (which re-fires per frame and saturates), so
the same guard is needed here: `c.twofire` uses a handler that always `RETURN`s,
must read 2 on both machines, and the whole run is refused otherwise
[[a-case-that-agrees-can-agree-for-the-wrong-reason]].

⚠️ THE PROBE'S OWN GATE ALREADY ASSERTS THAT SHAPE (`C_two_taps`, cnt==2 on both
machines), so the control is not a new claim -- it is that claim, re-read inside
THIS program, where the `CLEAR` and the GOSUB have had their chance to disturb it.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import basic_probe_strig_trap as G                                # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = [("vg8020", "Philips_VG_8020"), ("zb", ZB)]


def program(do_clear: bool, kill: bool, always_return: bool = False):
    return [
        G.ONERR,
        # HIMEM below the sentinels, exactly as the STOP replay does: line 50's
        # bare CLEAR resets HIMEM to the default and $D000.. must stay ours.
        "5 CLEAR200,&HCFFF:POKE&HD000,0:POKE&HD001,0",
        "6 POKE&HD002,0:POKE&HD003,0",
        "10 ON STRIG GOSUB 100",
        "20 STRIG(0) ON",
        "30 FORI=1TO9000:NEXT",           # the first tap (1.0 s) lands in here
        ("40 STRIG(0) OFF" if kill else "40 REM state left SERVICING"),
        ("50 CLEAR" if do_clear else "50 REM no clear -- the CONTROL"),
        "60 GOSUB 810",                   # exercise the stack after the CLEAR
        "70 FORI=1TO20000:NEXT",          # the second tap (3.0 s) lands in here
        "80 POKE&HD003,1:END",
        "810 RETURN",
        # The handler COUNTS. Unless this is the positive control it leaves by
        # GOTO on the FIRST fire, never reaching RETURN -- which is what holds
        # the trap in SERVICING.
        "100 POKE&HD000,PEEK(&HD000)+1:POKE&HD001,1",
    ] + ([] if always_return else ["105 IFPEEK(&HD000)=1THEN40"]) + [
        "108 RETURN",
        G.ERRH,
    ]


CASES = (("CLEAR, still SERVICING", True, False, False),
         ("CLEAR, trap killed", True, True, False),
         ("no-CLEAR, still SERVICING", False, False, False),
         ("no-CLEAR (control)", False, True, False),
         ("c.twofire POSITIVE CONTROL", False, False, True))
CTL = "c.twofire POSITIVE CONTROL"


def main() -> int:
    rows = []
    for label, do_clear, kill, always_ret in CASES:
        for side, machine in SIDES:
            r = G.run(machine, program(do_clear, kill, always_ret), G.TWO_TAPS,
                      boot=8.0, step=3.0)
            rows.append((label, side, r))

    print(f"\n{'case':28s} {'side':8s} {'fires':>5s} {'who':>4s} {'ERR':>4s} "
          f"{'done':>5s}")
    for label, side, r in rows:
        if not r:
            print(f"{label:28s} {side:8s} {'-':>5s}   <NO CAPTURE>")
            continue
        print(f"{label:28s} {side:8s} {r['cnt']:>5d} {r['who']:>4d} "
              f"{r['err']:>4d} {r['done']:>5d}")

    broken = [(l, s) for l, s, r in rows
              if not r or r["done"] != 1 or r["err"] != 0]
    if broken:
        print(f"\n\U0001f534 INSTRUMENT FAULT: {broken} did not reach the done "
              f"sentinel with err==0 -- no reading. STRIG fires per EDGE, so "
              f"unlike the SPRITE replay there is no starvation regime that "
              f"could explain a missing done.")
        return 2
    get = {(l, s): r["cnt"] for l, s, r in rows if r}
    bad = {s: get.get((CTL, s)) for s in ("vg8020", "zb")
           if get.get((CTL, s)) != 2}
    if bad:
        print(f"\n\U0001f534 INSTRUMENT FAULT: the positive control read {bad} where "
              f"BOTH sides must read 2. THE SECOND TAP DID NOT LAND, so every "
              f"other row's `1` is the instrument and not the machine. Refused.")
        return 2
    print()
    diffs = []
    for label, _c, _k, _r in CASES:
        v, z = get[(label, "vg8020")], get[(label, "zb")]
        if v != z:
            diffs.append(label)
        print(f"  {label:28s} vg8020={v:>3}  zb={z:>3}"
              + ("   <-- DIVERGENCE" if v != z else ""))
    print(f"\n=== {len(diffs)} divergence(s): {sorted(diffs) or 'none'} ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
