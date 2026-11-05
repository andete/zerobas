#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RECSLOW (2026-11-05): fat_rand_put's chain extension on the host Z80, with
NOTHING trapped but the sector I/O -- a fresh 720 KB FAT, an empty file, one PUT
at record N, LEN=1. Prints every sector read / written and checks the FAT chain
in the image afterwards (its own decode, never the ROM's).

    python3 -u scratchpad/recslow_host.py [RECNO]
"""
import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from _tmp import tp  # noqa: E402
from msxtest import Machine  # noqa: E402

ROM, SYM = tp("recslow_disk.rom"), tp("recslow_disk.sym")
subprocess.run(["pasmo", "-I", "disk", "--bin", "disk/disk.asm", ROM, SYM],
               check=True, capture_output=True, cwd=ROOT)
RECNO = int(sys.argv[1]) if len(sys.argv) > 1 else 32767
ROW, BLK, CHAN = 0xD000, 0xC000, 1
disk = {}
for f in (1, 4):                                   # both FAT copies' first sector
    disk[f] = bytearray(b"\xF9\xFF\xFF" + bytes(509))
PREUSED = int(os.environ.get("PREUSED", "0"))      # clusters 2..PREUSED+1 already used
TOT = int(os.environ.get("TOT", str(2 + 713)))     # FAT_TOTCLUS (a small one fills)
fat0 = bytearray(disk[1] + bytes(1024))
for c in range(2, 2 + PREUSED):
    o = c * 3 // 2
    v = fat0[o] | fat0[o + 1] << 8
    v = (v & 0x000F) | (0xFF7 << 4) if c & 1 else (v & 0xF000) | 0xFF7
    fat0[o], fat0[o + 1] = v & 0xFF, v >> 8
for i in range(3):
    disk[1 + i] = bytearray(fat0[i * 512:(i + 1) * 512])
    disk[4 + i] = bytearray(fat0[i * 512:(i + 1) * 512])
log = []
m = Machine(ROM, SYM, rom_base=0x4000)
s = m.sym


def rd(mm):
    log.append(f"R{mm.cpu.de}")
    mm.poke(mm.cpu.hl, bytes(disk.get(mm.cpu.de, bytearray(512))))
    mm.cpu.f &= ~1


def wr(mm):
    log.append(f"W{mm.cpu.de}")
    disk[mm.cpu.de] = bytearray(mm.peek(mm.cpu.hl, 512))
    mm.cpu.f &= ~1


m.trap("read_sector", rd)
m.trap("fatprim_write_sector", wr)
m.trap("fat_dir_update", lambda mm: mm.cpu.__setattr__("f", mm.cpu.f & ~1))
m.poke(s["FAT_SECPERCLUS"], 2)
m.poke_w(s["FAT_FATSTART"], 1)
m.poke(s["FAT_NUMFATS"], 2)
m.poke_w(s["FAT_SECPERFAT"], 3)
m.poke_w(s["FAT_FIRSTDATA"], 14)
m.poke_w(s["FAT_TOTCLUS"], TOT)
m.poke_w(s["FAT_ALLOCHINT"], 2)
m.poke(s["DISKOP_ERR"], 0)
m.poke(s["FAT_DEFER"], 0)
m.poke_w(s["FAT_FATSEC"], 0xFFFF)
m.poke(ROW, bytes(64))
m.poke_w(ROW + s["DOUT_BLK"], BLK)
m.poke(s["FCH_ACTIVE"], CHAN)
m.poke_w(s["FCH_RECLENS"] + CHAN * 2, 1)
m.poke(ROW + 33, (RECNO - 1).to_bytes(4, "little"))
m.poke(BLK + 9, b"Z")
m.poke(s["GP_FLAGS"], 1)
cpu = m.call("fat_rand_put", ix=ROW, max_steps=50_000_000)
print("CF", cpu.f & 1, "FAT_DEFER", m.mem[s["FAT_DEFER"]], "DISKOP_ERR", m.mem[s["DISKOP_ERR"]])
print(len(log), "sector commands:", " ".join(log[:60]), "..." if len(log) > 60 else "")
fat = disk[1] + disk.get(2, bytearray(512)) + disk.get(3, bytearray(512))


def ent(c):
    o = c * 3 // 2
    v = fat[o] | fat[o + 1] << 8
    return v >> 4 if c & 1 else v & 0xFFF


first = m.mem[ROW + s["DOUT_FIRST"]] | m.mem[ROW + s["DOUT_FIRST"] + 1] << 8
chain, c = [], first
while 2 <= c < 0xFF8 and len(chain) < 800:
    chain.append(c)
    c = ent(c)
need = (RECNO - 1) // 1024 + 1
print("first", first, "chain length", len(chain), "end", hex(c), "need", need)
print("FAT copies equal:", [disk.get(i) == disk.get(i + 3) for i in (1, 2, 3)])
data_writes = [x for x in log if x[0] == "W" and int(x[1:]) >= 14]
print("data writes", data_writes)
