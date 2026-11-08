# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: D-RECSLOW (2026-11-05) -- a random PUT that extends the chain holds
the FAT sector across every mark and link, and writes it once.

fat_rand_put on the host Z80 with NOTHING trapped but the sector I/O (and the
directory stamp): a fresh 720 KB FAT, an empty LEN=1 file, one PUT at record N.
The chain is decoded from the IMAGE afterwards by this file's own FAT12 reader,
never the ROM's. Cases:

  far     record 32767: a 32-cluster chain, both FAT copies equal, the record in
          the right data sector, and few sector commands (it was ~6 per cluster;
          the bound is what makes the test fail if the hold stops holding).
  cross   clusters 2..335 already used: the new chain crosses FAT sectors 1/2 and
          the entry that straddles them (341).
  full    12 clusters on the volume: the chain takes all 12, Disk full (66)
          pending, everything claimed on both copies.

The first build of this slice linked to a garbage cluster and wrote the "FAT
sector" over data sectors; an emulator command count only looked odd. This rig
saw a 1-cluster chain at once (scratchpad/recslow_host.py, its origin).
Clean-room: our own routines (disk/kernel.asm, disk/fat.asm, basic/fat-prim-body.inc),
public FAT12 layout.
"""
import os
import subprocess
import sys

from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

ROM, SYM = tp("rand_extend_disk.rom"), tp("rand_extend_disk.sym")
ROW, BLK, CHAN = 0xD000, 0xC000, 1


def build():
    subprocess.run(["pasmo", "-I", "disk", "--bin", "disk/disk.asm", ROM, SYM],
                   check=True, capture_output=True, cwd=ROOT)


def fresh_fat(preused):
    fat = bytearray(b"\xF9\xFF\xFF" + bytes(1533))
    for c in range(2, 2 + preused):
        o = c * 3 // 2
        v = fat[o] | fat[o + 1] << 8
        v = (v & 0x000F) | (0xFF7 << 4) if c & 1 else (v & 0xF000) | 0xFF7
        fat[o], fat[o + 1] = v & 0xFF, v >> 8
    disk = {}
    for i in range(3):
        disk[1 + i] = bytearray(fat[i * 512:(i + 1) * 512])
        disk[4 + i] = bytearray(fat[i * 512:(i + 1) * 512])
    return disk


def put(recno, preused=0, tot=2 + 713):
    disk, log = fresh_fat(preused), []
    m = Machine(ROM, SYM, rom_base=0x4000)
    s = m.sym

    def rd(mm):
        log.append(("R", mm.cpu.de))
        mm.poke(mm.cpu.hl, bytes(disk.get(mm.cpu.de, bytearray(512))))
        mm.cpu.f &= ~1

    def wr(mm):
        log.append(("W", mm.cpu.de))
        disk[mm.cpu.de] = bytearray(mm.peek(mm.cpu.hl, 512))
        mm.cpu.f &= ~1

    # D-PUTCACHE: trap BELOW read_sector / fatprim_write_sector, at the DSKIO both
    # end in (the direction is the carry), so read_sector's held-sector check runs.
    def dskio(mm):
        (wr if mm.cpu.f & 1 else rd)(mm)
    m.trap("dskio_calslt", dskio)
    m.trap("fat_dir_update", lambda mm: mm.cpu.__setattr__("f", mm.cpu.f & ~1))
    m.poke(s["FAT_SECPERCLUS"], 2)
    m.poke_w(s["FAT_FATSTART"], 1)
    m.poke(s["FAT_NUMFATS"], 2)
    m.poke_w(s["FAT_SECPERFAT"], 3)
    m.poke_w(s["FAT_FIRSTDATA"], 14)
    m.poke_w(s["FAT_TOTCLUS"], tot)
    m.poke_w(s["FAT_ALLOCHINT"], 2)
    m.poke(s["DISKOP_ERR"], 0)
    m.poke(s["FAT_DEFER"], 0)
    m.poke_w(s["FAT_FATSEC"], 0xFFFF)
    m.poke(ROW, bytes(64))
    m.poke_w(ROW + s["DOUT_BLK"], BLK)
    m.poke(s["FCH_ACTIVE"], CHAN)
    m.poke_w(s["FCH_RECLENS"] + CHAN * 2, 1)
    m.poke(ROW + 33, (recno - 1).to_bytes(4, "little"))
    m.poke(BLK + 9, b"Z")
    m.poke(s["GP_FLAGS"], 1)
    cpu = m.call("fat_rand_put", ix=ROW, max_steps=50_000_000)
    cf = carry(cpu)             # (m.call hands back the LIVE cpu: read it before the flush)
    m.call("rh_flush")          # D-PUTCACHE: the held record sector out, as CLOSE does
    fat = disk[1] + disk[2] + disk[3]

    def ent(c):
        o = c * 3 // 2
        v = fat[o] | fat[o + 1] << 8
        return v >> 4 if c & 1 else v & 0xFFF

    first = m.mem[ROW + s["DOUT_FIRST"]] | m.mem[ROW + s["DOUT_FIRST"] + 1] << 8
    chain, c = [], first
    while 2 <= c < 0xFF8 and len(chain) < 800:
        chain.append(c)
        c = ent(c)
    return dict(cf=cf, err=m.mem[s["DISKOP_ERR"]], defer=m.mem[s["FAT_DEFER"]],
                chain=chain, end=c, copies=all(disk[i] == disk[i + 3] for i in (1, 2, 3)),
                log=log, disk=disk)


def run():
    build()
    fails = 0

    def check(label, ok, detail):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}: {detail}")

    r = put(32767)
    want_sec = 14 + (r["chain"][-1] - 2) * 2 + 1 if r["chain"] else None
    check("far: record 32767 at LEN=1",
          not r["cf"] and len(r["chain"]) == 32 and r["end"] >= 0xFF8 and r["copies"]
          and r["defer"] == 0 and len(r["log"]) <= 10
          and r["disk"].get(want_sec, b" ")[510] == ord("Z"),
          f"chain {len(r['chain'])} (want 32), copies equal {r['copies']}, "
          f"{len(r['log'])} sector commands (<= 10), FAT_DEFER {r['defer']}")
    r = put(16000, preused=334)
    check("cross: the chain crosses FAT sectors 1/2 (entry 341 straddles)",
          not r["cf"] and len(r["chain"]) == 16 and r["chain"][0] == 336
          and r["chain"][-1] == 351 and r["copies"] and r["defer"] == 0,
          f"chain {r['chain'][:1]}..{r['chain'][-1:]} x{len(r['chain'])}, copies equal {r['copies']}")
    r = put(32767, tot=14)
    check("full: the volume fills mid-extension",
          r["cf"] and r["err"] == 66 and len(r["chain"]) == 12 and r["end"] >= 0xFF8
          and r["copies"] and r["defer"] == 0,
          f"CF {r['cf']}, DISKOP_ERR {r['err']}, chain {len(r['chain'])} (want 12), "
          f"copies equal {r['copies']}")
    print()
    print("ALL PASS -- a random PUT's chain extension holds the FAT sector and writes it once"
          if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
