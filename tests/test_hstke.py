# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Host test for D-HSTKE (basic/files.asm hstke and its sites): BASIC calls the
published hook H.STKE ($FEDA) where the CF-3300 does, with every register kept.

Measured on the CF-3300 with our own handler counting calls
(scratchpad/stke_when*.out): CLEAR, NEW, LOAD, RUN, a typed program line and an
untrapped error call it once each; the start of BASIC once, after the banner;
a direct statement, GOTO, STOP, CONT and END never. zerobas never called it, and
MemMan's `No free segment for MemMan` comes from it. The emulator rows on zerobas
are scratchpad/stke_when_zb.out; this file pins the helper's contract and the
two NEW entries.
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
MAIN_ROM, MAIN_SYM = tp("zb_hstke_main.rom"), tp("zb_hstke_main.sym")
H_STKE = 0xFEDA


def build():
    subprocess.run(["pasmo", "--bin", os.path.join(ROOT, "basic", "main.asm"), MAIN_ROM, MAIN_SYM],
                   check=True, capture_output=True, cwd=ROOT)


def run():
    build()
    m = Machine(MAIN_ROM, MAIN_SYM, rom_base=BASIC_BASE)
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    calls = []

    def hook(mach):
        c = mach.cpu
        calls.append(1)
        c.a, c.f, c.bc, c.de, c.hl, c.ix, c.iy = 0x11, 0x22, 0x3333, 0x4444, 0x5555, 0x6666, 0x7777

    m.trap(H_STKE, hook)

    regs = dict(a=0x9A, bc=0x1234, de=0x5678, hl=0x9ABC, ix=0xDEF0, iy=0x0FED)
    c = m.call("hstke", **regs)
    got = dict(a=c.a, bc=c.bc, de=c.de, hl=c.hl, ix=c.ix, iy=c.iy)
    check(calls == [1], f"hstke calls $FEDA once (got {len(calls)})")
    check(got == regs, f"every register comes back from a hook that clobbers all: {got}")

    for entry, want in (("new_prog", 1), ("new_prog_quiet", 0)):
        calls.clear()
        m.call(entry)
        check(len(calls) == want,
              f"{entry}: H.STKE x{len(calls)} (want {want}: NEW / LOAD call it, the cold "
              "boot's early reset does not -- its call comes after the banner)")
    return fails


if __name__ == "__main__":
    f = run()
    print(f"{'OK' if not f else 'FAILED'}: {f} failure(s)")
    sys.exit(1 if f else 0)
