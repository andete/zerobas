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

    # --- slice 3a: the table at bdos_more2 ----------------------------------
    for fn, target in ((0x0B, "const_body"), (0x0E, "seldsk_drv_body"), (0x18, "login_body"),
                       (0x19, "curdrv_body"), (0x1B, "getalloc_body"), (0x2A, "gdate_body"),
                       (0x2E, "verify_body")):
        m = Machine(ROM, SYM, rom_base=DISK_BASE)
        seen = []
        m.trap(target, lambda mach: seen.append(mach.cpu.e))
        m.call("bdos_entry", c=fn, de=0x0005)
        check(seen == [5], f"BDOS ${fn:02X} -> {target} {seen} (want one call, E = 5)")
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    cpu = m.call("bdos_entry", c=0x0C)
    check(cpu.a == 0x22 and cpu.hl == 0x0022 and cpu.b == 0,
          f"BDOS $0C VERSION: A ${cpu.a:02X} HL ${cpu.hl:04X} B ${cpu.b:02X} (want 22 / 0022 / 00)")
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    cpu = m.call("bdos_entry", c=0x2C, de=0x1234, hl=0x5678, bc=0x9A2C)
    check((cpu.a, cpu.bc, cpu.de, cpu.hl) == (0, 0, 0, 0),
          f"BDOS $2C GTIME: A {cpu.a:02X} BC {cpu.bc:04X} DE {cpu.de:04X} HL {cpu.hl:04X} "
          "(want all 0: no clock)")
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    out = []
    m.trap("conout_body", lambda mach: out.append(mach.cpu.e))
    cpu = m.call("bdos_entry", c=0x02, de=0x0041)
    check(out == [0x41] and cpu.a == 0x41, f"BDOS $02 CONOUT 'A': {out}, A ${cpu.a:02X} (want "
                                            "[65], A = $41)")
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    m.poke(0xF247, b"\x01")
    cpu = m.call("bdos_entry", c=0x0D)
    check(cpu.a == 0 and m.mem[0xF247] == 0 and m.mem[m.addr("BASENT_REQ")] != ord("S"),
          f"BDOS $0D DSKRST: A ${cpu.a:02X}, drive {m.mem[0xF247]} (want 0, A:, no DOS mark)")

    # --- slice 3b: DELETE / RENAME ------------------------------------------
    def fcb(m, at, old, new=None):
        m.poke(at, bytes(37))
        m.poke(at + 1, old.encode())
        if new:
            m.poke(at + 17, new.encode())
    for cfs, want in (([0, 0, 1], 0x00), ([1], 0xFF)):
        m = Machine(ROM, SYM, rom_base=DISK_BASE)
        fcb(m, 0xC020, "PROBE?  TMP")
        seq = list(cfs)
        names = []

        def fdel(mach):
            names.append(bytes(mach.mem[mach.addr("DISK_FCB_NAME"):mach.addr("DISK_FCB_NAME") + 11]))
            mach.cpu.f = (mach.cpu.f & ~1) | seq.pop(0)
        m.trap("fat_delete", fdel)
        cpu = m.call("bdos_entry", c=0x13, de=0xC020)
        check(cpu.a == want and len(names) == len(cfs) and names[0] == b"PROBE?  TMP",
              f"BDOS $13 DELETE, fat_delete CF {cfs}: A ${cpu.a:02X}, {len(names)} call(s), "
              f"name {names[:1]} (want ${want:02X})")
    for taken, want, stamped in ((False, 0x00, 1), (True, 0xFF, 0)):
        m = Machine(ROM, SYM, rom_base=DISK_BASE)
        fcb(m, 0xC100, "PROBE   TMP", "PROBE2  TMP")
        finds = []
        stamps = []
        m.trap("fat_mount", lambda mach: setattr(mach.cpu, "f", mach.cpu.f & ~1))

        def ffind(mach, taken=taken):
            name = bytes(mach.mem[mach.cpu.hl:mach.cpu.hl + 11])
            finds.append(name)
            found = name == b"PROBE   TMP" or taken
            mach.cpu.f = (mach.cpu.f & ~1) | (0 if found else 1)
        m.trap("fat_find", ffind)
        m.trap("hkn_stamp", lambda mach: (stamps.append(bytes(
            mach.mem[mach.addr("DISK_FCB_NAME"):mach.addr("DISK_FCB_NAME") + 11])),
            setattr(mach.cpu, "f", mach.cpu.f & ~1)))
        cpu = m.call("bdos_entry", c=0x17, de=0xC100)
        check(cpu.a == want and len(stamps) == stamped
              and (not stamped or stamps[0] == b"PROBE2  TMP")
              and finds == [b"PROBE   TMP", b"PROBE2  TMP"],
              f"BDOS $17 RENAME, new name {'taken' if taken else 'free'}: A ${cpu.a:02X}, "
              f"finds {finds}, stamps {stamps} (want ${want:02X})")

    for fn in (0x00, 0x21, 0x26, 0x30):
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
