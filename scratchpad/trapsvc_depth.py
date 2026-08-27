#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""How many LEAKED trap dispatches does each machine survive?

The open half of the deferred-error item names `TRAPSVC` as the untested
construct: incremented on trap dispatch, decremented only by `ex_return`'s hook,
so a handler that never RETURNs leaves its record stacked -- and `TRAPSTK_MAX`
is **6**. `check_traps` guards on that and jumps to `gosub_stk_over`, i.e.
**ERR 7**.

🎯 THE REFERENCES HAVE NO `TRAPSTK`. They leak GOSUB frames instead, and the
GOSUB stack is far deeper than six -- so if the filed reading is right, zerobas
should give out MUCH earlier than either reference. That is the divergence, and
it is stated in behaviour (how many, and which error) rather than in internals.

⚠️ THE ITEM CALLS THE TRIGGER "RESUME out of a trap handler". The tree already
knows that is narrower than the class -- a plain `GOTO` out of the handler leaks
it with no error anywhere -- so this drives the GOTO form, which needs no fault
at all and is therefore the cleanest possible instance.

READOUT IS POKE-BASED: $D000 counts dispatches, $D002 takes ERR from the
handler, $D003 is the done sentinel. A run that ends without an error is a
reading too -- it means the machine outlasted the window.
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
# 🔴 CF-3300 IS NOT DRIVEN HERE, AND THAT IS A LIMIT OF THE HARNESS, NOT A
# CHOICE. `basic_probe_interval_trap` has only ever run `REF_MACHINE =
# Philips_VG_8020`; pointing its `run()` at the CF-3300 returned an all-$FF
# block on EVERY row -- the $D000 window never written -- which my first cut
# printed as `fires=255 err=255 done=255`, i.e. read garbage as data. One
# reference, said out loud.
SIDES = [("vg8020", "Philips_VG_8020"), ("zb", ZB)]


def program(leak: bool):
    """`leak=False` is the CONTROL: the handler RETURNs, so nothing accumulates
    and the same number of dispatches must NOT raise anything."""
    tail = ["802 GOTO30"] if leak else ["802 RETURN"]
    return ([T.ONERR] + T.CLR + [
        "10 ONINTERVAL=10GOSUB800",
        "20 INTERVALON",
        f"30 H=PEEK(&H{J+1:X}):W=PEEK(&H{J:X})+256*H"
        f":IFH<>PEEK(&H{J+1:X})THEN30",
        f"32 H=PEEK(&H{J+1:X}):V=PEEK(&H{J:X})+256*H"
        f":IFH<>PEEK(&H{J+1:X})THEN32",
        "34 IFV-W<300THEN32",
        "40 POKE&HD001,1",
        "790 POKE&HD003,1:END",
        "800 A=PEEK(&HD000):IFA<250THENPOKE&HD000,A+1",
        "801 INTERVALON",                 # clear SERVICING so it can fire again
    ] + tail + [
        "900 POKE&HD002,ERR:POKE&HD001,PEEK(&HD000):POKE&HD003,1:END",
    ])


def main():
    rows = []
    for label, leak in (("handler LEAKS (GOTO)", True),
                        ("handler RETURNs (control)", False)):
        for side, machine in SIDES:
            boot, step = (14.0, 4.5) if side == "cf3300" else (8.0, 3.0)
            r = T.run(machine, program(leak), boot=boot, step=step)
            rows.append((label, side, r))
    print(f"{'case':26s} {'side':8s} {'fires':>5s} {'ERR':>4s} {'done':>4s}")
    for label, side, r in rows:
        if not r:
            print(f"{label:26s} {side:8s} {'-':>5s}  <NO CAPTURE>"); continue
        print(f"{label:26s} {side:8s} {r['cnt']:>5d} {r['err']:>4d} "
              f"{r['done']:>4d}")
    if any(not r for _, _, r in rows):
        print("\nINSTRUMENT FAULT: a side produced no capture at all.")
        return 2
    # an all-$FF window is a block that was NEVER WRITTEN, not a reading of 255
    ff = [(l, s) for l, s, r in rows
          if r["cnt"] == 255 and r["err"] == 255 and r["done"] == 255]
    if ff:
        print(f"\nINSTRUMENT FAULT: {ff} returned an all-$FF $D000 window -- "
              f"the probe's memory was never written, so 255 is 'not measured', "
              f"not a count.")
        return 2
    if all(r["cnt"] == 0 for _, _, r in rows):
        print("\nINSTRUMENT FAULT: NOTHING fired anywhere -- the trap never "
              "dispatched, so no row says anything about TRAPSVC.")
        return 2
    ctl = {s: r for l, s, r in rows if l.startswith("handler RETURNs")}
    leak = {s: r for l, s, r in rows if l.startswith("handler LEAKS")}
    print()
    for side, _ in SIDES:
        c, k = ctl[side], leak[side]
        print(f"  {side:8s} control fires={c['cnt']:>3d} err={c['err']}   "
              f"leaking fires={k['cnt']:>3d} err={k['err']}")
    errs = {s: leak[s]["err"] for s, _ in SIDES}
    cnts = {s: leak[s]["cnt"] for s, _ in SIDES}
    diff = errs["zb"] != errs["vg8020"] or cnts["zb"] != cnts["vg8020"]
    print(f"\n=== {'DIVERGENCE' if diff else 'AGREE'} on the leaking case ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
