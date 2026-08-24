# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: the HARNESS's own stack-band invariant (msxtest.StackLost).

The subject here is tests/msxtest.py, not the ROM. It exists because an
invariant whose green state is "found nothing" rots: if someone weakens or
deletes the band check in Machine.call, every other test in this directory stays
green and the defect class it guards against silently comes back.

The class (D-CONTR, docs/spec-basic-cont-record.md §5.5): the error-abort funnel
does `ld sp,(SAVSTK)`, SAVSTK is 0 in this harness's zeroed RAM, so the funnel's
tail `ret` pops from $0000 and the CPU runs away through memory until the
2,000,000-step guard fires. test_poke.py's ERRMARK row swallowed that guard with
`except: pass` and asserted on a byte read AFTERWARDS -- it was measuring where
2M steps happened to land, and it agreed for the wrong reason for its whole life.

Swept 2026-07-31 (docs/spec-tests-runaway-sweep.md): instrumenting every one of
the suite's 5606 Machine.call() invocations found 0 surviving members -- the
whole suite lives in SP $F326..$F380 and every call returns with SP=$F380
exactly. The class is empty; this file is what keeps it empty.

Three rows, and all three are load-bearing:
  R1  THE KNIFE     -- hand-poked `ld sp,($F000)` with $F000 holding 0 must raise
                       StackLost, EARLY (not via the 2M guard). ROM-independent:
                       it tests the harness, which is the subject.
  R2  GREEN CONTROL -- a poked `ret`, and a real do_poke success case, must pass
                       cleanly with SP back at $F380. Without R2, R1 is also
                       satisfied by a guard that fires on everything.
  R3  IN SITU       -- the actual D-CONTR case: do_poke with a comma-less token
                       stream and the funnel NOT trapped must now raise instead
                       of running away. Knowingly coupled to poke.asm's error
                       path; that is what makes it able to catch the removal of
                       test_poke.py's fre_abort_low trap.
"""

import os
from _tmp import tp
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, StackLost  # noqa: E402

# The shipped image at its ORG, named here rather than defaulted -- msxtest's old
# default was $4000, the retired lean cart's org (docs/spec-lean-retire-s3-gates.md §5).
BASIC_BASE = 0x2812
ROM = tp("zb_hguard.rom")
SYM = tp("zb_hguard.sym")
CODE = 0xC000    # scratch: hand-assembled Z80 for the synthetic rows
SPWORD = 0xF000  # holds the bogus SP the synthetic row loads (left 0 = zeroed RAM)
BUF = 0xC100     # token buffer for the in-situ row

HARNESS_SP = 0xF380   # msxtest.Machine.call's own stack base


def build():
    subprocess.run(["pasmo", "--bin", os.path.join(ROOT, "basic", "main.asm"),
                    ROM, SYM], check=True, capture_output=True)


def machine():
    return Machine(ROM, SYM, rom_base=BASIC_BASE)


def report(ok, label, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {detail}")
    return 0 if ok else 1


def r1_knife():
    """`ld sp,($F000)` with $F000 = $0000, then ret -> StackLost, immediately."""
    m = machine()
    m.poke(CODE, bytes([0xED, 0x7B, SPWORD & 0xFF, SPWORD >> 8, 0xC9]))
    m.poke_w(SPWORD, 0x0000)          # explicit: the harness zeroes RAM anyway
    try:
        m.call(CODE)
    except StackLost as e:
        # EARLY is half the claim: if this arrived at ~2,000,000 steps it came
        # from the old runaway guard, i.e. the band check did nothing.
        ok = e.sp == 0x0000 and e.steps <= 8
        return report(ok, "R1 knife  ld sp,($F000)=0 -> StackLost",
                      f"SP={e.sp:#06x} after {e.steps} step(s)"
                      + ("" if ok else "   want SP=$0000 within 8 steps"))
    except RuntimeError as e:
        return report(False, "R1 knife  ld sp,($F000)=0 -> StackLost",
                      f"got plain RuntimeError instead: {str(e)[:60]}")
    return report(False, "R1 knife  ld sp,($F000)=0 -> StackLost",
                  "call() RETURNED -- the band check is not firing")


def r2_control():
    """The green control: a bare `ret`, and a real routine, both clean."""
    fails = 0
    m = machine()
    m.poke(CODE, bytes([0xC9]))                  # ret
    cpu = m.call(CODE)
    fails += report(cpu.sp == HARNESS_SP, "R2 control  poked `ret` returns clean",
                    f"SP={cpu.sp:#06x} (want {HARNESS_SP:#06x})")

    # ...and a real ROM routine, so the control is not purely synthetic:
    # POKE &HC600,5 -- HEX_TOKEN addr, comma, digit token, EOL (see test_poke.py).
    m2 = machine()
    m2.poke(BUF, bytes([0x0C, 0x00, 0xC6]) + b',' + bytes([0x11 + 5, 0x00]))
    cpu = m2.call("do_poke", hl=BUF)
    ok = m2.mem[0xC600] == 5 and cpu.sp == HARNESS_SP
    fails += report(ok, "R2 control  do_poke success path unaffected",
                    f"mem[$C600]={m2.mem[0xC600]:#04x}, SP={cpu.sp:#06x}"
                    + ("" if ok else f"   want $05 / {HARNESS_SP:#06x}"))
    return fails


def r3_in_situ():
    """The D-CONTR case: the funnel reached for real, NOT trapped."""
    m = machine()
    m.capture_chput()                            # absorb the error string
    m.poke(BUF, bytes([0x0C, 0x00, 0xC6, 0x00]))  # &HC600 then EOL: no comma
    try:
        m.call("do_poke", hl=BUF)
    except StackLost as e:
        ok = e.sp == 0x0000 and e.steps < 100_000
        return report(ok, "R3 in situ  untrapped POKE abort funnel is LOUD",
                      f"StackLost SP={e.sp:#06x} at PC={e.pc:#06x}, "
                      f"{e.steps} steps"
                      + ("" if ok else "   want SP=$0000 well before the 2M guard"))
    except RuntimeError as e:
        return report(False, "R3 in situ  untrapped POKE abort funnel is LOUD",
                      f"only the 2M runaway guard fired: {str(e)[:60]}")
    return report(False, "R3 in situ  untrapped POKE abort funnel is LOUD",
                  "call() RETURNED after the abort -- a row reading RAM here "
                  "would be measuring a runaway")


def run():
    build()
    fails = r1_knife() + r2_control() + r3_in_situ()
    print()
    print("FAIL: harness stack-band invariant" if fails
          else "PASS: harness stack-band invariant (knife + control + in situ)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
