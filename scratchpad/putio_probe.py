#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-PUTIO — how many SECTORS does a `PUT` actually touch? Host-side, no emulator.

D-RUNGAP measured the cost and D-PUTIO asks where it could come from. The
emulated drive charges for physical accesses, so "the third write is slow" has
an obvious shape: the engine issues more of them as writes accumulate.

🎯 IT DOES NOT. Traps on `read_sector` / `write_sector` / `fat_dir_update`
over the sub image count every access `fat_rand_put` makes, with `frnd_locate`
trapped so the chain walk cannot contribute:

    same record x1     0 reads   1 write   1 dir_update
    same record x3     2 reads   3 writes  3 dir_updates
    same record x6     5 reads   6 writes  6 dir_updates
    spread 1,5,9       0 reads   3 writes  3 dir_updates

**Flat.** One write, one directory stamp and (after the first) one read-back per
`PUT`, whatever N is and wherever the records go. The first write of a given
sector reads nothing because the sector is past the old EOF and is filled with
spaces rather than read — which is also why `spread` reads zero.

🔴 SO THE RISING COST IS NOT THIS ENGINE ISSUING MORE I/O, and the candidate
that remains is per-access latency with zerobas simply doing MORE accesses per
write than the reference does. `fat_dir_update` on EVERY `PUT` is the specific
suspect: `frnd_update_size`'s own comment records that the CF-3300 moves `LOF`'s
field live but that *"the on-disk DIRECTORY entry still holds 0"* after
`PUT #1,1` — i.e. the reference does not stamp the directory per write.

⚠️ THAT IS A CANDIDATE, NOT A FINDING, AND THE ARITHMETIC DOES NOT YET FIT IT: a
constant per-write overhead predicts a constant cost, and what D-RUNGAP measured
is a STEP at the third write (<=0.5 s for one and two, 3.0 s for three). Naming
the cause needs a reading this file does not have.
"""
import collections
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# ⚠️ THE TESTS DIRECTORY GOES ON THE PATH BEFORE ITS MODULES ARE IMPORTED, and
# `_tmp` is one of them -- this file lives in scratchpad/ and is run from the
# repo root, so neither is importable until the path is set.
sys.path.insert(0, os.path.join(ROOT, "tests"))

from _tmp import tp        # noqa: E402
from msxtest import Machine  # noqa: E402

SECSIZE = 512
SUB_ROM, SUB_SYM = tp("putio_sub.rom"), tp("putio_sub.sym")


def build():
    subprocess.run(["pasmo", "-I", "sub", "--bin", "sub/sub.asm", SUB_ROM, SUB_SYM],
                   check=True, capture_output=True, cwd=ROOT)


def count(n, recs):
    disk, stats = {}, collections.Counter()
    m = Machine(SUB_ROM, SUB_SYM, rom_base=0)
    s = m.sym

    def loc(mm):
        sec = mm.mem[s["GP_SEC"]] | (mm.mem[s["GP_SEC"] + 1] << 8)
        mm.poke_w(s["GP_PHYS"], 100 + sec)
        mm.cpu.f &= ~0x01

    def rd(mm):
        stats["read"] += 1
        mm.poke(mm.cpu.hl, bytes(disk.get(mm.cpu.de, bytearray(b" " * SECSIZE))))
        mm.cpu.f &= ~0x01

    def wr(mm):
        stats["write"] += 1
        disk[mm.cpu.de] = bytearray(mm.peek(mm.cpu.hl, SECSIZE))
        mm.cpu.f &= ~0x01

    def dirupd(mm):
        stats["dir_update"] += 1
        mm.cpu.f &= ~0x01

    m.trap("frnd_locate", loc)
    m.trap("read_sector", rd)
    m.trap("write_sector", wr)
    m.trap("fat_dir_update", dirupd)
    m.poke(s["FCH_ACTIVE"], 1)
    m.poke_w(s["FCH_RECLENS"] + 2, 128)
    m.poke_w(s["FWR_BYTES"], 0)
    m.poke_w(s["FWR_BYTES"] + 2, 0)
    for i in range(n):
        m.poke_w(s["GP_RECNO"], recs[i] if isinstance(recs, list) else recs)
        m.poke(s["FSECTOR_BUF"], bytes([65 + i]) * 128)
        m.call("fat_rand_put")
    return stats


def main():
    build()
    print(f"\n{'case':20} {'reads':>6} {'writes':>7} {'dir':>5}   per-PUT")
    for n in (1, 2, 3, 4, 5, 6):
        st = count(n, 6)
        print(f"same record x{n:<7} {st['read']:6d} {st['write']:7d} "
              f"{st['dir_update']:5d}   r={st['read'] / n:.1f} w={st['write'] / n:.1f}")
    st = count(3, [1, 5, 9])
    print(f"{'spread 1,5,9':20} {st['read']:6d} {st['write']:7d} {st['dir_update']:5d}")
    print("\nflat per-PUT traffic: the rising emulated-time cost D-RUNGAP measured "
          "is NOT this engine issuing more I/O as writes accumulate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
