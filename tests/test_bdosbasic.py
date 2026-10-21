# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Host test for D-BDOSBASIC slice 1: bdos_entry (the $F37D BDOS door in the
boot code's environment) answers $09 STROUT, $11 SFIRST and $12 SNEXT, and $1A
SETDTA also writes the work-area DTA cell $F23D.

Measured first: ROBOCOP's boot loader calls $09, $1A, $11, $0F, $27 and runs on the
CF-3300 (scratchpad/bootpath_robocop_bdos.out); the CF-3300's SETDTA from BASIC
leaves the DTA in $F23D (scratchpad/bdos_dtacell.out). The bodies are trapped
here -- the dispatch and the cell are what this slice adds; the root walk
(sfirst_body / snext_body) and the '$'-string printer were already in use.
"""

import os
import subprocess
import sys
from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

DISK_BASE = 0x4000
ROM = tp("zb_bdosbasic_ut.rom")
SYM = tp("zb_bdosbasic_ut.sym")
RES_PRINT, DOS_DTAPTR = 0xF1C9, 0xF23D


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


def run():
    build()
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    for fn, target in ((0x09, RES_PRINT), (0x11, "sfirst_body"), (0x12, "snext_body")):
        m = Machine(ROM, SYM, rom_base=DISK_BASE)
        seen = []
        for name in (RES_PRINT, "sfirst_body", "snext_body"):
            m.trap(name, lambda mach, name=name: seen.append((name, mach.cpu.de)))
        m.call("bdos_entry", c=fn, de=0xC0DA)
        check(seen == [(target, 0xC0DA)],
              f"BDOS ${fn:02X} -> {seen} (want {target} with DE = $C0DA)")

    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    m.poke(DOS_DTAPTR, b"\0\0")
    m.call("bdos_entry", c=0x1A, de=0xD100)
    dta = m.mem[m.addr("BDOS_DTA")] | m.mem[m.addr("BDOS_DTA") + 1] << 8
    cell = m.mem[DOS_DTAPTR] | m.mem[DOS_DTAPTR + 1] << 8
    check(dta == 0xD100 and cell == 0xD100,
          f"BDOS $1A DE=$D100: BDOS_DTA ${dta:04X}, $F23D ${cell:04X} (want both $D100)")

    for fn in (0x00, 0x02, 0x13, 0x30):
        m = Machine(ROM, SYM, rom_base=DISK_BASE)
        cpu = m.call("bdos_entry", c=fn, de=0xC0DA)
        check(cpu.a == 0xFF, f"BDOS ${fn:02X} (not answered yet): A = ${cpu.a:02X} (want $FF)")

    # --- slice 2: the $F37D stub (install_f37d) -----------------------------
    for page0, label, want in ((0, "page 0 = the BIOS (a BASIC program)", "calslt"),
                               (3, "page 0 = RAM (a boot code, MSX-DOS)", "direct")):
        m = Machine(ROM, SYM, rom_base=DISK_BASE)
        m.poke(m.addr("HOOK_SLOT"), b"\x87")
        m.call("install_f37d")
        stub = m.addr("F37D_STUB")
        log = []
        m.trap(0x001C, lambda mach: log.append(("calslt", mach.cpu.iy >> 8, mach.cpu.ix,
                                                mach.cpu.c, mach.cpu.de)))
        m.trap("bdos_entry", lambda mach: log.append(("direct", mach.cpu.c, mach.cpu.de)))
        m.cpu.io_in = lambda port, p0=page0: (0xF0 | p0) if port & 0xFF == 0xA8 else 0xFF
        m.call(stub, c=0x11, de=0xD020, ix=0x1234, iy=0x5678)
        if want == "calslt":
            ok = log == [("calslt", 0x87, m.addr("bdos_entry"), 0x11, 0xD020)]
            ok = ok and m.cpu.ix == 0x1234 and m.cpu.iy == 0x5678
        else:
            ok = log == [("direct", 0x11, 0xD020)]
        check(ok, f"$F37D stub, {label}: {log} (want {want}; IX/IY kept "
                  f"{m.cpu.ix:04X}/{m.cpu.iy:04X})")

    print()
    print("ALL PASS — bdos_entry answers STROUT / SFIRST / SNEXT and sets $F23D"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
