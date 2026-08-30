#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Does a LIVE, ARMED `ON INTERVAL` trap survive `CLEAR`?

🎯 THIS IS THE QUESTION IN FRONT OF A FIX, NOT THE FIX. TODO's CLEAR/TRAPSTK item
proposes `clear_vars` calling `trap_init` -- and `clear_vars` has exactly four
call sites (cold boot, RUN, NEW, CLEAR), so that hook would wipe the whole trap
block on `CLEAR` as well. That is only correct if the REFERENCE also stops an
armed trap there. Nobody has asked.

The measured defect (scratchpad/clrtrapstk_probe.py) is a trap the program
KILLED coming back after `CLEAR`. This probe asks the opposite half: a trap the
program never killed. If the reference keeps firing across `CLEAR`, then
`trap_init` is too broad and the fix has to be narrower -- reset only the
SERVICE stack, not the arm state.

🔴 THE CONTROL IS NOT OPTIONAL. A zero count in the second window has two
sufficient causes -- the trap was disarmed, or the program never got that far --
so `$D001` (who) records that the second wait COMPLETED, and the no-CLEAR row says the
fixture can count at all. [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
⚠️ THE CONTROL ROW'S TOTAL JITTERS BY ONE, AND THAT IS THE APPARATUS. A 160-frame
window at a 10-tick interval yields 16 or 17 fires depending on where the window
opens relative to the tick, so the no-CLEAR row reads 32 on one machine and 33 on
the other and has always done so. THE ROW UNDER TEST DOES NOT JITTER: it is
0-versus-nonzero, which is why the second window's count is reported separately
from the total rather than inferred by subtraction after the fact.
⚠️ `CLEAR` also resets `ON ERROR`, so an error after line 50 is untrapped and
kills the run silently; the done sentinel at $D003 is what separates that from a
real zero.
"""
from __future__ import annotations
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import basic_probe_interval_trap as T                             # noqa: E402

J = T.JIFFY
ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
# ⚠️ ONE REFERENCE, AND THE REASON IS THE HARNESS, NOT THE QUESTION. The
# CF-3300 needs a longer boot and its own reset sequence, and
# basic_probe_interval_trap.run does not carry them -- both CF-3300 runs reached
# no done sentinel, so the probe REFUSED rather than reporting their zeros as
# disarmed traps. The sibling probe scratchpad/clrtrapstk_probe.py drops it for
# the same reason. `ON INTERVAL` is core MSX1 BASIC, so a VG-8020 is a
# legitimate oracle on its own here.
SIDES = [("vg8020", "Philips_VG_8020"), ("zb", ZB)]


def wait(line, n):
    return [f"{line} H=PEEK(&H{J+1:X}):W=PEEK(&H{J:X})+256*H"
            f":IFH<>PEEK(&H{J+1:X})THEN{line}",
            f"{line+2} H=PEEK(&H{J+1:X}):V=PEEK(&H{J:X})+256*H"
            f":IFH<>PEEK(&H{J+1:X})THEN{line+2}",
            f"{line+4} IFV-W<{n}THEN{line+2}"]


def program(do_clear: bool):
    """The trap is armed and NEVER killed. $D000 counts fires in BOTH windows;
    $D008 (aux) latches the count at the moment of the CLEAR, so the second window's
    fires are (final - latched) and a trap that stopped is visible as a
    difference of zero rather than inferred from a total."""
    return ([T.ONERR] + T.CLR + [
        "10 ONINTERVAL=10GOSUB800",
        "20 INTERVALON",
    ] + wait(30, 160) + [
        "48 POKE&HD008,PEEK(&HD000)",      # latch the first window's count (aux)
        ("50 CLEAR" if do_clear else "50 REM no clear -- the CONTROL"),
    ] + wait(70, 160) + [
        "76 POKE&HD001,1",
        "790 POKE&HD003,1:END",
        "800 A=PEEK(&HD000):IFA<250THENPOKE&HD000,A+1",
        "802 RETURN",
        T.ERRH,
    ])


def main():
    rows = []
    for label, do_clear in (("CLEAR, trap still armed", True),
                            ("no CLEAR (control)", False)):
        for side, machine in SIDES:
            r = T.run(machine, program(do_clear), boot=8.0, step=3.0)
            rows.append((label, side, r))
    print(f"{'case':24s} {'side':8s} {'total':>6s} {'@CLEAR':>7s} {'2nd win':>8s} "
          f"{'2nd done':>9s} {'ERR':>4s} {'done':>5s}")
    bad = []
    for label, side, r in rows:
        if not r or r.get("done") != 1:
            print(f"{label:24s} {side:8s} {'-':>6s} — INSTRUMENT FAULT (no done sentinel)")
            bad.append((label, side)); continue
        tot = r["cnt"]
        at = r["aux"]
        print(f"{label:24s} {side:8s} {tot:>6} {str(at):>7} "
              f"{str(tot - at) if at is not None else '?':>8} "
              f"{str(r['who']):>9} {str(r['err']):>4} {str(r['done']):>5}")
    if bad:
        print(f"\n🔴 REFUSING TO CONCLUDE: {len(bad)} run(s) never reached the "
              f"done sentinel — a zero count there is a dead run, not a disarmed "
              f"trap: {bad}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
