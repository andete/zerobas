#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-STICKSAMPLE -- was the flat `STICK` a SAMPLING window, not a dead rig?

D-HOLDROW proved the hold lands and row 8 is reached: with row 8 bit $20 held,
`INKEY$` reads **30** (up-arrow) and bit $01 reads **32** (space), on both
machines, with a silent negative control. Under the SAME hold `STICK(0)` read 0.

🎯 THE ASYMMETRY NOBODY LOOKED AT: the `INKEY$` case SAMPLES IN A LOOP for up to
a second, while `STICK(0)` was read ONCE, immediately after `RUN`. `ev_ff_stick`
(basic/expr.asm) calls the BIOS `GTSTCK` and returns whatever the matrix says AT
THAT INSTANT -- so a press that lands a few frames late is invisible to the
single read and obvious to the loop. That is a property of the PROBE, not of
`STICK`.

So this changes exactly one thing: `STICK(0)` sampled in the same loop shape.
  * `s0` -- `STICK(0)` polled until non-zero or ~1 s. UP held should give **1**
    (direction 1 is up, 1..8 clockwise).
  * `s1` -- the same poll with NOTHING held: must stay 0, or the loop is reading
    noise and `s0` means nothing.
  * `s2` -- `STRIG(0)` polled with SPACE (row 8 bit $01) held: -1 if seen.
  * `s3` -- `STRIG(0)` polled with nothing held: must stay 0.
🔴 BOTH MACHINES, and the negative controls are half the rows on purpose.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("C-BIOS_MSX1_EU_REPACK_DISK", "Philips_VG_8020")

# ⚠️ The poll spins on ITS OWN line, never back onto `T=TIME` -- a settle loop
# pointed at the clock read re-reads its own start and never exits.
POLL_STICK = ["T=TIME", "S=STICK(0)",
              "IF S=0 AND TIME-T<60 THEN 20",
              'PRINT"<J";S;">"']
POLL_STRIG = ["T=TIME", "S=STRIG(0)",
              "IF S=0 AND TIME-T<60 THEN 20",
              'PRINT"<J";S;">"']

CASES = [
    ("s0_stick_up",   POLL_STICK, (8, 0x20)),
    ("s1_stick_none", POLL_STICK, None),
    ("s2_strig_spc",  POLL_STRIG, (8, 0x01)),
    ("s3_strig_none", POLL_STRIG, None),
]


def main() -> int:
    for mach in MACHINES:
        print("===", mach, flush=True)
        specs = [("stored", body) for _, body, _ in CASES]
        holds = [h for _, _, h in CASES]
        try:
            raws = omsx_repl.run_cases(mach, specs, batch=False, cap_gap=10.0,
                                       holds=holds)
        except Exception as exc:                       # noqa: BLE001
            print(f"  🔴 APPARATUS FAILURE on {mach}: "
                  f"{str(exc).splitlines()[0][:160]}", flush=True)
            continue
        for (name, _, _), raw in zip(CASES, raws):
            txt = " ".join("".join(raw or "").split())
            i = txt.rfind("<J")
            j = txt.find(">", i + 1)
            cell = txt[i:j + 1] if i >= 0 and j > i else "<no reading>"
            print(f"  {name:14} {cell!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
