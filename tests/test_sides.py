# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Host test for D-SIDES: DSKIO seats a logical sector by the MEDIA BYTE, as both
references do (scratchpad/bpbrule_p8f.out: a valid single-sided 360 KB disk with
its program at sector 18 runs on the CF-3300 and the VG-8020 + NMS 1200, and did
not here -- zerobas seated every sector as 2 sides x 9).

lsec_chs (disk/fat.asm) is run directly for every media ID: bit 1 set = 8 sectors
a track (else 9), bit 0 set = two sides. Then dskio's entry: a C of $F8 or more is
adopted into DSK_MEDIA, a smaller C (our own FAT layer's 0) keeps the mounted one.
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
ROM = tp("zb_sides_ut.rom")
SYM = tp("zb_sides_ut.sym")


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


def chs(media, n):
    spt = 8 if media & 2 else 9
    q, r = divmod(n, spt)
    if media & 1:
        return r + 1, q // 2, q % 2
    return r + 1, q, 0


def run():
    build()
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    cell = m.addr("DSK_MEDIA")
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        if not ok or msg.startswith("*"):
            print(f"{'PASS' if ok else 'FAIL'}  {msg.lstrip('*')}")

    rows = 0
    for media in range(0xF8, 0x100):
        for n in (0, 1, 8, 9, 17, 18, 19, 26, 359, 719, 1439):
            m.poke(cell, bytes([media]))
            cpu = m.call("lsec_chs", hl=n)
            got = (cpu.c, cpu.de >> 8, cpu.de & 0xFF)
            want = chs(media, n)
            check(got == want, f"media {media:02X} sector {n}: (sector, track, side) "
                               f"{got} (want {want})")
            rows += 1
    check(True, f"*lsec_chs: {rows} (media, sector) rows")
    # the single-sided row that separated the machines: sector 18 of a $F8 disk
    m.poke(cell, b"\xF8")
    cpu = m.call("lsec_chs", hl=18)
    check((cpu.c, cpu.de) == (1, 0x0200),
          f"*$F8 sector 18 -> sector {cpu.c}, track {cpu.de >> 8}, side {cpu.de & 0xFF} "
          "(want 1, 2, 0 -- 2 sides x 9 gave track 1, side 0)")

    # dskio's entry: adopt a media ID, keep the mounted one for C < $F8
    m.trap("fdc_read_phys", lambda mach: setattr(mach.cpu, "f", mach.cpu.f & ~1))
    m.trap("fdc_write_phys", lambda mach: setattr(mach.cpu, "f", mach.cpu.f & ~1))
    for start, c, want in ((0xF9, 0xF8, 0xF8), (0xF8, 0x00, 0xF8), (0xF8, 0xFD, 0xFD),
                           (0xFD, 0xF7, 0xFD)):
        m.poke(cell, bytes([start]))
        m.call("dskio", a=0, b=0, c=c, de=0, hl=0xC000)
        got = m.mem[cell]
        check(got == want, f"*dskio C={c:02X} with DSK_MEDIA {start:02X}: {got:02X} "
                           f"(want {want:02X})")

    print()
    print("ALL PASS — sectors seated by the media byte, as on both references"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
