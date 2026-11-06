# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: D-SAVEFAT (2026-11-06) -- a tokenised SAVE holds the FAT sector across
every cluster and writes it once.

The disk ROM's SAVE engine (hkds_run -> sav_disk_write: create, one putbyte per
program byte, close) on the host Z80 against a freshly generated empty 720 KB volume (tools/make_test_dsk.py
--empty, the Makefile's disk/empty720.dsk recipe), with NOTHING
trapped but the sector I/O. The image is then decoded by this file's own FAT12 and
directory reader, never the ROM's:

  plain   a 14 KB program on an empty disk: the entry, its size, the chain, every
          byte, both FAT copies equal -- and few sector commands (W3a wrote both
          FAT copies per cluster; the bound fails if the hold stops holding).
  cross   clusters 2..335 already used: the chain crosses FAT sectors 1 / 2 (341
          straddles), where the hold flushes and ends.
  full    a volume with too few free clusters: status 3, both copies equal.

Clean-room: our own routines and a public FAT12 / 8.3 layout.
"""
import os
import subprocess
import sys

from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

ROM, SYM = tp("save_fathold_disk.rom"), tp("save_fathold_disk.sym")
# The empty volume is GENERATED here, as the Makefile's $(DISK_EMPTY_DSK) rule makes
# it: disk/empty720.dsk is a build product, absent on a fresh checkout (CI went red
# on exactly that, 2026-11-06).
_EMPTY = tp("save_fathold_empty720.dsk")
subprocess.run([sys.executable, os.path.join(ROOT, "tools", "make_test_dsk.py"),
                "--empty", _EMPTY], check=True, capture_output=True)
IMG = open(_EMPTY, "rb").read()
SPC, FAT0, FATSECS, NFATS, ROOT0, ROOTSECS, DATA0 = 2, 1, 3, 2, 7, 7, 14
TXT = 0x8001


def fat_get(fat, c):
    o = c * 3 // 2
    v = fat[o] | fat[o + 1] << 8
    return v >> 4 if c & 1 else v & 0xFFF


def fat_set(fat, c, val):
    o = c * 3 // 2
    v = fat[o] | fat[o + 1] << 8
    v = (v & 0x000F) | (val << 4) if c & 1 else (v & 0xF000) | val
    fat[o], fat[o + 1] = v & 0xFF, v >> 8


def save(n, preused=0, freeleft=None):
    disk = bytearray(IMG)
    fat = bytearray(disk[FAT0 * 512:(FAT0 + FATSECS) * 512])
    for c in range(2, 2 + preused):
        fat_set(fat, c, 0xFF7)
    if freeleft is not None:
        for c in range(2 + freeleft, 714):
            fat_set(fat, c, 0xFF7)
    for k in range(NFATS):
        disk[(FAT0 + k * FATSECS) * 512:(FAT0 + (k + 1) * FATSECS) * 512] = fat
    log = []
    m = Machine(ROM, SYM, rom_base=0x4000)
    s = m.sym

    def rd(mm):
        log.append(("R", mm.cpu.de))
        mm.poke(mm.cpu.hl, bytes(disk[mm.cpu.de * 512:(mm.cpu.de + 1) * 512]))
        mm.cpu.f &= ~1

    def wr(mm):
        log.append(("W", mm.cpu.de))
        disk[mm.cpu.de * 512:(mm.cpu.de + 1) * 512] = mm.peek(mm.cpu.hl, 512)
        mm.cpu.f &= ~1

    m.trap("read_sector", rd)
    m.trap("fatprim_write_sector", wr)
    m.poke_w(s["DATE_DAYS"], 1461)
    m.poke(s["DISKSLOT_OK"], 1)
    m.poke(s["FAT_DEFER"], 0)
    m.poke(s["DISK_FCB_NAME"], b"BIG     BAS")
    prog = bytes((i * 7 + 3) & 0xFF for i in range(n))
    m.poke(TXT, prog)
    m.poke_w(s["TXTTAB"], TXT)
    m.poke_w(s["PRGEND"], TXT + n - 2)          # the last image byte is PRGEND+1
    m.poke(s["DISKOP_STATUS"], 0)
    m.call("hkds_run", hl=s["sav_disk_write"], max_steps=200_000_000)
    status = m.mem[s["DISKOP_STATUS"]]
    copies = all(disk[(FAT0 + k * FATSECS) * 512:(FAT0 + (k + 1) * FATSECS) * 512]
                 == disk[FAT0 * 512:(FAT0 + FATSECS) * 512] for k in range(NFATS))
    fat = disk[FAT0 * 512:(FAT0 + FATSECS) * 512]
    entry = None
    for sec in range(ROOT0, ROOT0 + ROOTSECS):
        for off in range(0, 512, 32):
            e = disk[sec * 512 + off:sec * 512 + off + 32]
            if e[:11] == b"BIG     BAS":
                entry = e
    got = b""
    chain = []
    if entry is not None:
        c = entry[26] | entry[27] << 8
        size = int.from_bytes(entry[28:32], "little")
        while 2 <= c < 0xFF8 and len(chain) < 800:
            chain.append(c)
            first = DATA0 + (c - 2) * SPC
            got += bytes(disk[first * 512:(first + SPC) * 512])
            c = fat_get(fat, c)
        got = got[:size]
    return dict(status=status, copies=copies, entry=entry, chain=chain,
                ok=got == b"\xFF" + prog, log=log, fat=fat)


def run():
    subprocess.run(["pasmo", "-I", "disk", "--bin", "disk/disk.asm", ROM, SYM],
                   check=True, capture_output=True, cwd=ROOT)
    fails = 0

    def check(label, ok, detail):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}: {detail}")

    r = save(14000)
    fatw = sum(1 for k, sec in r["log"] if k == "W" and FAT0 <= sec < FAT0 + NFATS * FATSECS)
    check("plain: a 14 KB SAVE", r["status"] == 0 and r["ok"] and r["copies"]
          and len(r["chain"]) == 14 and fatw <= 2,
          f"status {r['status']}, content {r['ok']}, chain {len(r['chain'])} (want 14), "
          f"copies equal {r['copies']}, FAT writes {fatw} (<= 2: one per copy), "
          f"{len(r['log'])} sector commands")
    r = save(14000, preused=334)
    check("cross: the chain crosses FAT sectors 1 / 2", r["status"] == 0 and r["ok"]
          and r["copies"] and r["chain"][:1] == [336] and len(r["chain"]) == 14,
          f"status {r['status']}, content {r['ok']}, chain {r['chain'][:1]}..{r['chain'][-1:]}, "
          f"copies equal {r['copies']}")
    r = save(14000, freeleft=3)
    check("full: too few free clusters", r["status"] == 3 and r["copies"],
          f"status {r['status']} (want 3), copies equal {r['copies']}")
    print()
    print("ALL PASS -- a SAVE holds the FAT sector and writes it once"
          if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
