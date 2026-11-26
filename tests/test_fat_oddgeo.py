# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Host test for D-FATODDGEO: fat_mount's cluster count when the data sectors are NOT a multiple of the
sectors per cluster.

The count is FLOOR(data sectors / SPC) + 2, as the FAT specification counts clusters. The old loop stopped only on
an EXACT zero remainder: 5 sectors with SPC 2 went 5, 3, 1, $FFFF, ... and, with an even SPC, never reached 0 --
the mount HUNG. Only a BPB-geometry disk can have such a count (a media ID in the FAT fixes a standard format, see
test_mediaid.py), so the rows use FAT byte $00 and a BPB, read_sector served from memory as there.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import test_mediaid as T  # noqa: E402  -- its image builder, ROM build and geometry layout
from msxtest import Machine, carry  # noqa: E402


def bpb(spc, total):
    b = bytearray(T.BPB_720)
    b[2] = spc
    b[8:10] = total.to_bytes(2, "little")
    return bytes(b)


def run():
    T.build()
    m = Machine(T.ROM, T.SYM, rom_base=T.DISK_BASE)
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    # 720 KB layout: data starts at 1 + 2 * 3 + 112 * 32 / 512 = 14
    for spc, total in ((2, 1440), (2, 1439), (4, 1440), (4, 1439), (4, 1438), (4, 1437), (8, 1439)):
        sectors = T.image(0x00, bpb(spc, total))

        def read_sector(mach):
            mach.poke(mach.cpu.hl, sectors.get(mach.cpu.de, bytes(512)))
            mach.cpu.f &= ~0x01
        m.trap("read_sector", read_sector)
        data = total - 14
        want = data // spc + 2
        try:
            cpu = m.call("fat_mount")
        except Exception as e:                       # the old loop: the step budget runs out
            check(False, f"SPC {spc}, {data} data sectors: fat_mount did not return ({type(e).__name__})")
            continue
        a = m.addr("FAT_TOTCLUS")
        got = m.mem[a] | m.mem[a + 1] << 8
        check(not carry(cpu) and got == want,
              f"SPC {spc}, {data} data sectors (remainder {data % spc}): FAT_TOTCLUS {got} (want {want})")
    print()
    print("ALL PASS — the cluster count is floor(data / SPC) + 2" if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
