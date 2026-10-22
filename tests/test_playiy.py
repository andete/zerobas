# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Host test for D-PLAYIY (basic/subromcall.asm sr_slot): a tenant call hands the
caller's IY back.

`sr_slot` loads IYh with the sub-ROM slot id for CALSLT, and IY used to come back
as that slot id ($8B00 for slot 3-2). PLAY's pl_voice holds its voice-block
pointer in IY across `str_eval`, whose string VARIABLE lookup is a tenant call,
so `PLAY "C",A$,B$` wrote B$'s descriptor to $8B02 -- into the program text of
any program past ~2.8 KB (the tape run's Blocker; scratchpad/blocker_watch.out,
scratchpad/iyclobber.out).

🔴 WHY NO OTHER TEST SAW IT: Machine's subrom bridge (tests/msxtest.py) traps
`subrom_call` itself and never touches IY, so on the host IY always survived.
This test takes the bridge OUT and runs the real sr_slot, with CALSLT replaced
by a stub that does what a CALSLT may do to IY: anything.
"""

import os
import subprocess
import sys
from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

BASIC_BASE = 0x2781
MAIN_ROM, MAIN_SYM = tp("zb_playiy_main.rom"), tp("zb_playiy_main.sym")


def build():
    subprocess.run(["pasmo", "--bin", os.path.join(ROOT, "basic", "main.asm"), MAIN_ROM, MAIN_SYM],
                   check=True, capture_output=True, cwd=ROOT)


def run():
    build()
    m = Machine(MAIN_ROM, MAIN_SYM, rom_base=BASIC_BASE)
    s = m.sym
    del m.traps[s["subrom_call"]]          # the REAL sr_slot, not the bridge
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    seen = {}

    def calslt(mach):
        c = mach.cpu
        seen.update(iy=c.iy, ix=c.ix, hl=c.hl, de=c.de)
        c.iy = 0x5A5A                       # a CALSLT may leave IY anything
        c.a = 0x42                          # the tenant's result

    m.trap("CALSLT", calslt)

    for iy in (0xFB41, 0xFB66, 0x0000):     # VCBA, VCBB, and a zero
        m.poke(s["SUBSLOT_OK"], b"\x01")
        m.poke(s["SUBSLOT"], b"\x8B")
        c = m.call("subrom_call", iy=iy, ix=0x0123, hl=0x1111, de=0x2222)
        check(c.iy == iy, f"IY {iy:#06x} comes back from a tenant call (got {c.iy:#06x})")
        check(seen.get("iy", 0) >> 8 == 0x8B,
              f"CALSLT saw IYh = the slot id $8B (got {seen.get('iy', 0):#06x})")
        check((seen.get("hl"), seen.get("de"), seen.get("ix")) == (0x1111, 0x2222, 0x0123),
              "HL, DE and IX reach CALSLT unchanged")
        check(c.a == 0x42 and not c.f & 1, "A = the tenant's result, CF = 0")

    # absent: no call, CF = 1, IY untouched as before
    seen.clear()
    m.poke(s["SUBSLOT_OK"], b"\x00")
    c = m.call("subrom_call", iy=0xFB41, ix=0x0123)
    check(not seen and c.f & 1 and c.iy == 0xFB41, "absent sub-ROM: no call, CF = 1, IY kept")
    return fails


if __name__ == "__main__":
    f = run()
    print(f"{'OK' if not f else 'FAILED'}: {f} failure(s)")
    sys.exit(1 if f else 0)
