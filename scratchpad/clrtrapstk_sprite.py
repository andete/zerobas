#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Does the CLEAR/TRAPSTK defect reproduce on SPRITE? The shared-code argument, measured.

`KEY / STRIG / SPRITE / STOP were NOT run against the D-TRAPSVC rows` records
that the four non-INTERVAL traps are covered by a CODE argument -- *"they share
`check_traps`, `ct_find`, `set_state` and `trap_return_check` verbatim; the
index is a parameter"* -- and not by a measurement.

🎯 THE `CLEAR` DEFECT MEASURED TODAY IS A DISCRIMINATOR FOR THAT ARGUMENT. It
lives in `trap_return_check`, which is the shared routine. If the argument holds,
SPRITE must break in exactly the same cell of the same 2x2; if it does not, the
argument is falsified and the sharing is not what it claims.

⚠️ `basic_probe_sprite_trap.py` still says `ON SPRITE GOSUB` is unimplemented on
the zerobas side (D-G7-4 left `SPRITE ON/OFF/STOP` a no-op). That comment is
STALE by reading -- `basic/sprtrap-body.inc` is included via `subromcall.asm`
and `ZTI_SPRITE` is a live index -- and this run is what settles it either way.

🔴 THE SPRITES MUST BE SEPARATED AND RE-COLLIDED. A permanent overlap fires once
per FRAME, so both waits would fire regardless of any re-enable and the run
would measure nothing. Sprite 1 is parked off-target after the first fire and
brought back only for the second wait, so a second fire needs the trap to be
enabled AND a fresh collision.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import basic_probe_interval_trap as T                             # noqa: E402

J = T.JIFFY
ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = [("vg8020", "Philips_VG_8020"), ("zb", ZB)]
APART, TOGETHER = "(200,100)", "(104,100)"


def wait(line, n):
    return [f"{line} H=PEEK(&H{J+1:X}):W=PEEK(&H{J:X})+256*H"
            f":IFH<>PEEK(&H{J+1:X})THEN{line}",
            f"{line+2} H=PEEK(&H{J+1:X}):V=PEEK(&H{J:X})+256*H"
            f":IFH<>PEEK(&H{J+1:X})THEN{line+2}",
            f"{line+4} IFV-W<{n}THEN{line+2}"]


def program(do_clear: bool, kill: bool):
    return ([T.ONERR] + T.CLR + [
        "10 SCREEN2",
        "12 SPRITE$(0)=STRING$(8,255)",
        f"14 PUTSPRITE0,(100,100),15,0",
        f"16 PUTSPRITE1,{APART},15,0",
        "20 ONSPRITEGOSUB800",
        "22 SPRITEON",
        f"24 PUTSPRITE1,{TOGETHER},15,0",
    ] + wait(30, 60) + [
        ("40 SPRITEOFF" if kill else "40 REM state left SERVICING"),
        ("50 CLEAR" if do_clear else "50 REM no clear -- the CONTROL"),
        f"55 PUTSPRITE1,{APART},15,0",
        "60 GOSUB810",
        f"65 PUTSPRITE1,{TOGETHER},15,0",
    ] + wait(70, 60) + [
        "76 POKE&HD001,1",
        "77 POKE&HD004,PEEK(&HE20C):POKE&HD005,PEEK(&HE20B)",
        "78 POKE&HD006,PEEK(&HE20D):POKE&HD007,PEEK(&HE20E)",
        "79 POKE&HD008,PEEK(&HE041):POKE&HD009,PEEK(&HE042)",
        "790 POKE&HD003,1:END",
        "810 RETURN",
        "800 A=PEEK(&HD000):IFA<250THENPOKE&HD000,A+1",
        "801 IFA=0THEN40",
        "802 RETURN",
        T.ERRH,
    ])


def main():
    rows = []
    CASES = (("CLEAR, still SERVICING", True, False),
             ("CLEAR, trap killed", True, True),
             ("no-CLEAR, still SERVICING", False, False),
             ("no-CLEAR (control)", False, True))
    for label, do_clear, kill in CASES:
        for side, machine in SIDES:
            r = T.run(machine, program(do_clear, kill), boot=8.0, step=3.0)
            rows.append((label, side, r))
    print(f"{'case':26s} {'side':8s} {'fires':>5s} {'2nd':>4s} {'ERR':>4s} "
          f"{'done':>4s} {'TRAPSVC':>7s} {'TRAPENA':>7s}")
    for label, side, r in rows:
        if not r:
            print(f"{label:26s} {side:8s} {'-':>5s}  <NO CAPTURE>"); continue
        svc = r["j1"] & 0xFF if side == "zb" else "-"
        ena = (r["j1"] >> 8) & 0xFF if side == "zb" else "-"
        print(f"{label:26s} {side:8s} {r['cnt']:>5d} {r['who']:>4d} "
              f"{r['err']:>4d} {r['done']:>4d} {str(svc):>7s} {str(ena):>7s}")

    # 🔴 "DID NOT FINISH" HAS TWO CAUSES AND ONLY ONE IS A FAULT. A row that
    # SATURATED the counter (250) and never completed its second wait did not
    # fail to be measured -- it was STARVED by the defect under test, because
    # SPRITE re-fires once per FRAME once it is re-enabled. Classifying that as
    # an instrument fault would throw away the strongest row in the run.
    starved = [(l, s) for l, s, r in rows
               if r and r["done"] != 1 and r["cnt"] >= 250 and r["who"] == 0]
    broken = [(l, s) for l, s, r in rows
              if not r or (r["done"] != 1 and (l, s) not in starved)]
    if broken:
        print(f"\nINSTRUMENT FAULT: {broken} did not reach the done sentinel "
              f"and did not saturate -- no reading.")
        return 2
    for l, s in starved:
        print(f"\n  🔴 {l} / {s}: counter SATURATED at 250 and the second wait "
              f"never completed -- the re-enabled trap fired every frame and "
              f"starved the program. That is the defect, not a missing reading.")
    get = {(l, s): r["cnt"] for l, s, r in rows if r}
    if all(v == 0 for v in get.values()):
        print("\nINSTRUMENT FAULT: NOTHING fired anywhere -- the collision never "
              "happened, or ON SPRITE GOSUB is inert on both machines. A 0-vs-0 "
              "row is not evidence about the trap.")
        return 2
    diffs = [l for l in {a for a, _ in get} if get[(l, "vg8020")] != get[(l, "zb")]]
    print()
    for l in sorted({a for a, _ in get}):
        print(f"  {l:26s} vg8020={get[(l,'vg8020')]:>3}  zb={get[(l,'zb')]:>3}"
              + ("   <-- DIVERGENCE" if l in diffs else ""))
    print(f"\n=== {len(diffs)} divergence(s): {sorted(diffs) or 'none'} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
