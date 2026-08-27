#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Does `CLEAR` let a later GOSUB/RETURN re-enable a trap the program killed?

The filed claim (docs/spec-basic-trapsvc.md §7): after a LEAKED trap dispatch
the abandoned GOSUB frame keeps the TRAPSTK record's gsp unreachable, so
`trap_return_check`'s match is sound BY CONSTRUCTION -- and `clear_vars`
(basic/vars.asm) resets `GSP` to the base WITHOUT calling `trap_init`, so after a
`CLEAR` an unrelated `GOSUB`/`RETURN` can land on the stale record's gsp and
re-enable a trap the program believes is dead.

🎯 IT IS A DIFFERENTIAL EVEN THOUGH `TRAPSTK` IS OURS ALONE. The references have
no such structure, so what they do IS the definition: after `INTERVAL OFF` the
trap must not fire again. A second fire on zerobas and not on the reference is
the defect, stated in behaviour rather than in internals.

READOUT IS POKE-BASED, WHICH THE ITEM ASKED FOR: `CLEAR` wipes the variables a
fenced `PRINT` row would carry its flags in, so the counters live at $D000 and
are read straight out of emulated RAM.

  $D000  total INTERVAL fires (the whole claim: 1 = sound, >=2 = re-enabled)
  $D001  1 iff the SECOND wait completed -- without it a count of 1 could just
         mean the program never got far enough to fire again
  $D003  done sentinel
  $D004  TRAPSVC        how many service records are still stacked
  $D005  TRAPENA        the enable byte the claim says gets set behind the program
  $D006/7 top record gsp, and $D008/9 GSP itself, both AFTER the GOSUB/RETURN

🔴 A FIRE COUNT OF 1 IS ONLY HALF A READING. "The trap did not come back" has
more than one sufficient cause: the stale record may already be popped, or the
gsp may simply never have matched at this depth, or the re-enable may set
TRAPENA while the trap's STATE stays OFF so it cannot fire anyway. The zerobas
side therefore reads the MECHANISM out of RAM as well, so a green row says
which of those it is [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
⚠️ Those four cells are zerobas-internal addresses and are read on the zb side
only -- the references have no such structure, which is the whole premise.

🔴 THE HANDLER LEAKS ONLY ONCE. `GOTO`ing out of it on every fire would spin
forever once the trap came back; leaking on the FIRST fire and returning
normally afterwards is what makes ">=2" observable at all.
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


def wait(line, n):
    """Frames-elapsed wait, INLINE (no GOSUB) so the only frame the leak
    abandons is the trap's own -- the construction under test."""
    return [f"{line} H=PEEK(&H{J+1:X}):W=PEEK(&H{J:X})+256*H"
            f":IFH<>PEEK(&H{J+1:X})THEN{line}",
            f"{line+2} H=PEEK(&H{J+1:X}):V=PEEK(&H{J:X})+256*H"
            f":IFH<>PEEK(&H{J+1:X})THEN{line+2}",
            f"{line+4} IFV-W<{n}THEN{line+2}"]


def program(do_clear: bool, kill: bool = True):
    """`kill=False` leaves the trap's ZTRAP state at SERVICING when the handler
    leaks. 🎯 THAT IS THE CASE THAT SEPARATES THE RULES. `trap_return_check`
    re-enables only `iff` the entry is still SERVICING (`cp ZTS_SERVICING /
    ret nz`), so an `INTERVAL OFF` in the handler's escape path POPS the stale
    record without re-enabling anything -- which is why the first two cases
    agreed. Leave the state alone and the same collision reaches the
    `or ZTS_ON` + `inc TRAPENA` path."""
    return ([T.ONERR] + T.CLR + [
        "10 ONINTERVAL=10GOSUB800",
        "20 INTERVALON",
    ] + wait(30, 160) + [
        ("40 INTERVALOFF" if kill else "40 REM state left SERVICING"),
        ("50 CLEAR" if do_clear else "50 REM no clear -- the CONTROL"),
        "60 GOSUB810",                     # unrelated GOSUB/RETURN pair
    ] + wait(70, 160) + [
        "76 POKE&HD001,1",
        # the mechanism, read straight out of RAM on the zb side (see docstring)
        "77 POKE&HD004,PEEK(&HE20C):POKE&HD005,PEEK(&HE20B)",
        "78 POKE&HD006,PEEK(&HE20D):POKE&HD007,PEEK(&HE20E)",
        "79 POKE&HD008,PEEK(&HE041):POKE&HD009,PEEK(&HE042)",
        "790 POKE&HD003,1:END",
        # 🔴 THE SUBROUTINE MUST SORT **AFTER** THE `END` LINE. At 700 it sat
        # between the last statement and `790 END`, so execution FELL INTO it
        # and its RETURN raised ERR 3 -- which the control rows showed as
        # `ERR=3` and the CLEAR rows as a dead run, because `CLEAR` had also
        # reset `ON ERROR`, so the untrapped ERR 3 stopped the program before
        # the done sentinel. The line NUMBER decides, not the order typed
        # (basic_probe_interval_trap says so in its own words).
        "810 RETURN",
        # leak on the FIRST fire only (see the docstring)
        "800 A=PEEK(&HD000):IFA<250THENPOKE&HD000,A+1",
        "801 IFA=0THEN40",
        "802 RETURN",
        T.ERRH,
    ])


def main():
    rows = []
    CASES = (("CLEAR, trap killed", True, True),
             ("no-CLEAR (control)", False, True),
             ("CLEAR, still SERVICING", True, False),
             ("no-CLEAR, still SERVICING", False, False))
    for label, do_clear, kill in CASES:
        for side, machine in SIDES:
            r = T.run(machine, program(do_clear, kill), boot=8.0, step=3.0)
            if not r:
                rows.append((label, side, None, None, None, None,
                             0, 0, 0, 0, 0, 0)); continue
            # run() already decodes $D000.. into named fields: cnt/who/err/done.
            rows.append((label, side, r["cnt"], r["who"], r["err"], r["done"],
                         r["j1"] & 0xFF, (r["j1"] >> 8) & 0xFF,
                         r["j2"] & 0xFF, (r["j2"] >> 8) & 0xFF, r["aux"], r["aux2"]))
    print(f"{'case':20s} {'side':8s} {'fires':>5s} {'2nd':>4s} {'ERR':>4s} "
          f"{'done':>4s} {'TRAPSVC':>7s} {'TRAPENA':>7s} {'rec.gsp':>8s} {'GSP':>6s}")
    # $D004=TRAPSVC $D005=TRAPENA $D006/7=record gsp $D008/9=GSP, in that order.
    # (The first cut named these `glo,ghi,rlo,rhi` and printed the record from
    # the GSP pair -- a mislabelled readout is indistinguishable from a wrong
    # answer, so the names now match the addresses.)
    for (label, side, fires, w2, err, done,
         svc, ena, reclo, rechi, gsplo, gsphi) in rows:
        f = "-" if fires is None else str(fires)
        rec = f"{rechi:02X}{reclo:02X}" if side == "zb" else "-"
        gsp = f"{gsphi:02X}{gsplo:02X}" if side == "zb" else "-"
        print(f"{label:20s} {side:8s} {f:>5s} {str(w2):>4s} {str(err):>4s} "
              f"{str(done):>4s} {svc if side=='zb' else '-':>7} "
              f"{ena if side=='zb' else '-':>7} {rec:>8s} {gsp:>6s}")

    bad = [r for r in rows if r[2] is None or r[5] != 1]
    if bad:
        print(f"\nINSTRUMENT FAULT: {len(bad)} run(s) did not reach the done "
              f"sentinel -- nothing above is a reading: "
              f"{[(r[0], r[1]) for r in bad]}")
        return 2
    if not all(r[3] == 1 for r in rows):
        print("\nINSTRUMENT FAULT: a run never completed its SECOND wait, so a "
              "fire count of 1 cannot be distinguished from 'never had the "
              "chance to fire again'.")
        return 2
    get = {(r[0], r[1]): r[2] for r in rows}
    diffs = sorted({lab for lab, _ in get
                    if get[(lab, "vg8020")] != get[(lab, "zb")]})
    for lab in sorted({l for l, _ in get}):
        print(f"  {lab:26s} vg8020={get[(lab,'vg8020')]}  zb={get[(lab,'zb')]}"
              + ("   <-- DIVERGENCE" if lab in diffs else ""))
    print(f"\n=== {len(diffs)} divergence(s): {diffs or 'none'} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
