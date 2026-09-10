#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""Does the CLEAR/TRAPSTK defect reproduce on STOP? The shared-code argument, 2 of 4.

TODO.md's "`KEY / STRIG / SPRITE / STOP` were NOT run against the D-TRAPSVC rows"
records the four non-INTERVAL traps as covered by a CODE argument -- *"they share
`check_traps`, `ct_find`, `set_state` and `trap_return_check` verbatim; the index
is a parameter"* -- and not by a measurement. `SPRITE` was converted 2026-08-26
(`scratchpad/clrtrapstk_sprite_probe.py`) because a sprite collision needs no device.
This is `STOP`, which does: it needs Ctrl-STOP on the real key matrix.

🎯 THE APPARATUS ALREADY EXISTS AND IS IMPORTED, NOT COPIED.
`probes/basic/basic_probe_stop_trap.py` drives Ctrl-STOP through openMSX
`keymatrixdown`/`keymatrixup`, injects the program through KEYBUF, and captures
FLAG/RAN/DONE through a `done` sentinel. Its `run()` is used verbatim here --
a second copy would sit outside `make latch-check` and re-open the delivery race
that gate exists for.

⚠️ THE TAP LENGTH AND THE `run_gap` ARE THAT PROBE'S, FOR ITS REASONS. 100 ms is
5 PAL frames because 30 ms fired at only 3 of 6 sub-frame phases; `run_gap=2.0`
puts the press zero where the FOR delay is. Changing either would move the press
out of the only regime that discriminates, so they are inherited rather than
re-chosen.

🔴 THE DISCRIMINATOR IS THE SAME 2x2 THE INTERVAL AND SPRITE RUNS USED:

    (CLEAR / no-CLEAR) x (trap killed / still SERVICING)

"Still SERVICING" is produced by leaving the handler with a `GOTO` instead of a
`RETURN` on the first fire -- exactly as the SPRITE replay does -- so
`trap_return_check` never runs and the trap stays in its serviced state. If the
shared-code argument holds, the `CLEAR, still SERVICING` cell must be the one
that moves, and the other three must agree.

⚠️ WHAT THIS CANNOT DO THAT THE SPRITE RUN COULD: SPRITE re-fires once per FRAME,
so a re-enabled trap SATURATES a counter and starves the program -- a very loud
signature. Ctrl-STOP fires once per PRESS, so the second fire needs a second
press and the reading is a COUNT of 1 vs 2, not a saturation. That makes the
second press part of the instrument: without it, every cell reads 1 and the run
would agree for the wrong reason
[[a-case-that-agrees-can-agree-for-the-wrong-reason]].
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import basic_probe_stop_trap as S                                 # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = [("vg8020", "Philips_VG_8020"), ("zb", ZB)]

# Two taps: the first drives the handler (which GOTOs out, leaving SERVICING or
# not), the second asks whether the trap is still live afterwards.
TAPS = [(0.3, 0.40), (3.0, 3.10)]


def program(do_clear: bool, kill: bool, always_return: bool = False):
    return [
        S.CLR,
        "10 ON STOP GOSUB 100",
        "20 STOP ON",
        S.RANOK,
        "30 FORI=1TO4000:NEXT",          # first tap lands in here
        ("40 STOP OFF" if kill else "40 REM state left SERVICING"),
        ("50 CLEAR" if do_clear else "50 REM no clear -- the CONTROL"),
        "60 GOSUB 810",                  # exercise the stack after the CLEAR
        "70 FORI=1TO12000:NEXT",         # second tap lands in here
        "80 POKE&HD003,1:END",
        "810 RETURN",
        # The handler COUNTS. On the FIRST fire it leaves by GOTO, never reaching
        # RETURN -- that is what holds the trap in SERVICING.
        "100 POKE&HD000,PEEK(&HD000)+1",
    ] + ([] if always_return else ["105 IFPEEK(&HD000)=1THEN40"]) + [
        "108 RETURN",
    ]


# \U0001f534 THE FIFTH ROW IS THE ONE THE FIRST RUN LACKED, AND WITHOUT IT THE RUN SAID
# NOTHING. Every cell read 1 -- which is what the REFERENCE correctly reads in all
# four (a trap left SERVICING does not re-fire until RETURN, so 1 is right there),
# and also exactly what a SECOND TAP THAT NEVER LANDED reads. Two causes, one
# number [[a-case-that-agrees-can-agree-for-the-wrong-reason]]. The SPRITE replay
# never needed this: SPRITE re-fires per FRAME, so its live cell SATURATED at 250
# and could not be confused with a missed event.
# `c.twofire` uses a handler that always RETURNs, so the trap is armed again when
# the second tap arrives: it MUST read 2 on both machines, and if it does not,
# the taps are the instrument and every other row is void.
CASES = (("CLEAR, still SERVICING", True, False, False),
         ("CLEAR, trap killed", True, True, False),
         ("no-CLEAR, still SERVICING", False, False, False),
         ("no-CLEAR (control)", False, True, False),
         ("c.twofire POSITIVE CONTROL", False, False, True))


def main() -> int:
    rows = []
    for label, do_clear, kill, always_ret in CASES:
        for side, machine in SIDES:
            r = S.run(machine, program(do_clear, kill, always_ret), TAPS,
                      boot=6.0, step=3.0, done_gap=4.0)
            rows.append((label, side, r))

    print(f"\n{'case':26s} {'side':8s} {'fires':>5s} {'ran':>4s} {'done':>5s}")
    for label, side, r in rows:
        if not r:
            print(f"{label:26s} {side:8s} {'-':>5s}   <NO CAPTURE>")
            continue
        print(f"{label:26s} {side:8s} {r['flag']:>5d} {r['ran']:>4d} "
              f"{r['done']:>5d}")

    broken = [(l, s) for l, s, r in rows if not r or r["done"] != 1
              or r["ran"] != 1]
    if broken:
        print(f"\n\U0001f534 INSTRUMENT FAULT: {broken} did not reach the done "
              f"sentinel with ran==1 -- no reading. Unlike the SPRITE replay "
              f"there is no starvation regime here, so a missing done is always "
              f"the apparatus.")
        return 2
    get = {(l, s): r["flag"] for l, s, r in rows if r}
    if all(v == 0 for v in get.values()):
        print("\n\U0001f534 INSTRUMENT FAULT: NOTHING fired anywhere -- the taps "
              "missed, or ON STOP GOSUB is inert on both machines. A 0-vs-0 row "
              "is not evidence about the trap.")
        return 2
    # \U0001f534 THE POSITIVE CONTROL IS CHECKED BEFORE ANY VERDICT IS PRINTED.
    ctl = "c.twofire POSITIVE CONTROL"
    bad_ctl = [s_ for s_ in ("vg8020", "zb") if get.get((ctl, s_)) != 2]
    if bad_ctl:
        print(f"\n\U0001f534 INSTRUMENT FAULT: the positive control read "
              f"{ {s_: get.get((ctl, s_)) for s_ in ('vg8020','zb')} } where BOTH "
              f"sides must read 2. The SECOND TAP DID NOT LAND, so every other "
              f"row's `1` is the instrument and not the machine. Refused.")
        return 2
    print()
    diffs = []
    for label, _c, _k, _r in CASES:
        v, z = get[(label, "vg8020")], get[(label, "zb")]
        if v != z:
            diffs.append(label)
        print(f"  {label:26s} vg8020={v:>3}  zb={z:>3}"
              + ("   <-- DIVERGENCE" if v != z else ""))
    print(f"\n=== {len(diffs)} divergence(s): {sorted(diffs) or 'none'} ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
