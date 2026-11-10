# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Host test for D-P1RDBLK (disk ROM): a BDOS block read into a DTA in PAGE 1 lands
in the RAM under the disk ROM, and P1_BLIT is there to do it on every host.

starsh2's boot loader maps RAM into page 1, sets the DTA to $4000 and reads its
game with BDOS $27. The CF-3300 has the bytes at $4000 afterwards; zerobas had
$FF there (scratchpad/starsh2_p1.out): the block read stored each byte with a
plain `ld (hl),a`, which went to the disk ROM itself while it was mapped. Every
block read stores through dta_put now (D-BDOSFCB, 2026-11-10: the $F37D RDBLK is the
kernel's k47b2_body, whose transfer loop calls it; the old rdb_recloop_body is gone),
so these rows drive dta_put, one byte per call, as that loop does. And
P1_BLIT -- the page-3 routine that copies with page 1 switched to RAM -- was
installed only behind the $FF gate, so not on the C-BIOS target at all.

This harness is flat (no slots), so the RAM under page 1 is modelled by trapping
P1_BLIT: the trap copies the bytes into `page1_ram` instead of the ROM image.
Rows:
  * a 4-byte record to a page-1 DTA goes through P1_BLIT, byte by byte, and the
    ROM image there is untouched;
  * the same record to a page-2 DTA is plain stores, no P1_BLIT;
  * install_f37d installs P1_BLIT too, and the installed routine copies BC bytes
    HL -> DE and puts the slot-3 subslot register back.
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
ROM, SYM = tp("zb_p1rdblk.rom"), tp("zb_p1rdblk.sym")


def build():
    subprocess.run(["pasmo", "-I", "disk", "--bin", "disk/disk.asm", ROM, SYM],
                   check=True, capture_output=True, cwd=ROOT)


def run():
    build()
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    data = b"\x11\x00\x22\x33"

    def machine(dst):
        m = Machine(ROM, SYM, rom_base=DISK_BASE)
        m.poke_w(m.addr("RDBLK_DST"), dst)
        return m

    def record(m):
        for b in data:
            m.call("dta_put", a=b)

    # --- page 1: through P1_BLIT ------------------------------------------------
    dst = 0x4100
    m = machine(dst)
    rom_before = bytes(m.mem[dst:dst + 4])
    page1_ram, blits = {}, []

    def p1blit(mach):
        c = mach.cpu
        blits.append((c.hl, c.de, c.bc))
        for i in range(c.bc):
            page1_ram[c.de + i] = mach.mem[c.hl + i]
        c.hl, c.de, c.bc = c.hl + c.bc, c.de + c.bc, 0
    m.trap("P1_BLIT", p1blit)
    record(m)
    got = bytes(page1_ram.get(dst + i, 0xEE) for i in range(4))
    check(got == data and len(blits) == 4 and all(b[2] == 1 for b in blits),
          f"page-1 DTA ${dst:04X}: RAM gets {got.hex()} in {len(blits)} one-byte blits "
          f"(want {data.hex()}, 4)")
    check(bytes(m.mem[dst:dst + 4]) == rom_before,
          "page-1 DTA: the ROM image under it is untouched (no plain store)")
    ptr = int.from_bytes(m.peek(m.addr("RDBLK_DST"), 2), "little")
    check(ptr == dst + 4, f"page-1 DTA: the pointer moved to ${ptr:04X} (want past the record)")

    # --- page 2: plain stores ------------------------------------------------------
    dst = 0x8100
    m = machine(dst)
    blits = []
    m.trap("P1_BLIT", lambda mach: blits.append(1))
    record(m)
    check(m.peek(dst, 4) == data and not blits,
          f"page-2 DTA ${dst:04X}: {m.peek(dst, 4).hex()} stored directly, {len(blits)} blits "
          "(want the record, 0)")

    # --- the installed routine ------------------------------------------------------
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    p1 = m.addr("P1_BLIT")
    m.poke(p1, b"\x00" * 16)
    m.call("install_f37d")
    m.poke(0xD000, b"ABCDE")
    m.poke(0xFFFF, bytes([(~0x04) & 0xFF]))      # reads back inverted: page 1 = subslot 1
    seen = []
    c = m.call(p1, hl=0xD000, de=0xD100, bc=5)
    check(m.peek(0xD100, 5) == b"ABCDE" and c.de == 0xD105 and c.hl == 0xD005,
          f"P1_BLIT (installed by install_f37d): copied {m.peek(0xD100, 5)!r}, DE={c.de:04X} "
          "(want ABCDE, D105)")
    check(m.mem[0xFFFF] == 0x04,
          f"P1_BLIT: the subslot register written back as ${m.mem[0xFFFF]:02X} (want $04, "
          "page 1 = the disk ROM again)")
    # D-TPAPTAIL (b): the window is DI'd and the caller's interrupt state comes back
    for iff in (1, 0):
        m.poke(0xFFFF, bytes([(~0x04) & 0xFF]))
        m.cpu.iff = iff
        c = m.call(p1, hl=0xD000, de=0xD100, bc=5)
        check(c.iff == iff, f"P1_BLIT returns with interrupts {'on' if iff else 'off'} as they "
                            f"were (iff {c.iff}, want {iff})")
    return fails


if __name__ == "__main__":
    f = run()
    print(f"{'OK' if not f else 'FAILED'}: {f} failure(s)")
    sys.exit(1 if f else 0)
