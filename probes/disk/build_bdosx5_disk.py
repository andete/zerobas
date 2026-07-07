#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Build the DIR-FULL throwaway disk for the BDOSX5.COM exerciser (Tier-C case
3: the dir-full corner of Create, see disk/docs/tier2-tierC-spec.md "Candidate
cases" #3).

Assembles bdosx5.asm, injects BDOSX5.COM into a copy of a DOS disk, then fills
the ROOT DIRECTORY to its BPB entry count by injecting tiny 1-byte dummy files
under distinct 8.3 names ("DIRFIL00.TMP", "DIRFIL01.TMP", ...) via the SAME
fat12_add injector the other BDOSX builders use, until it raises
SystemExit("root directory full") -- at which point every root-dir slot is
occupied by a live entry. We catch that exception to know the fixture is
ready, then ASSERT free DATA CLUSTERS remain > 0 (each dummy is 1 byte -> 1
cluster, so filling ~a few hundred root entries with 1024-B clusters never
comes close to exhausting a 720 KB volume's ~700 data clusters) -- this keeps
the corner unambiguously DIR-FULL, not disk-full, which BDOSX4 already covers.

On the next boot BDOSX5.COM's FMAKE finds no free root-dir slot and returns
whatever stock's dir-full code is; we do not posit that code, we let the
differential capture it.

Prints the `done` anchor + the `fcb`/`regs` buffer addresses (the capture
--mem region), read from the .sym -- never hand-guessed (M15 lesson).

Usage:
  python3 probes/disk/build_bdosx5_disk.py --dos-disk ~/Documents/msx/msx/disks/test.dsk \
      --out /tmp/zerobas_bdosx5.dsk
"""
from __future__ import annotations

import argparse
import os
import shutil
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # sibling probes
from disk_probe_bdos import fat12_add  # noqa: E402  (reuse, don't duplicate)

HERE = os.path.dirname(os.path.abspath(__file__))
ASM = os.path.join(HERE, "bdosx5.asm")

SYM_NAMES = ("done", "fcb", "regs")


def assemble(tmp_dir: str) -> tuple[bytes, dict]:
    com = os.path.join(tmp_dir, "bdosx5.com")
    sym = os.path.join(tmp_dir, "bdosx5.sym")
    subprocess.run(["pasmo", "--bin", ASM, com, sym], check=True)
    addrs: dict = {}
    for line in open(sym):
        name, _, rest = line.strip().partition("\t")
        name = name.strip()
        if name in SYM_NAMES:
            addrs[name] = int(rest.strip().split()[-1].rstrip("H"), 16)
    missing = [n for n in SYM_NAMES if n not in addrs]
    if missing:
        sys.exit(f"could not find symbol(s) {missing} in bdosx5.sym")
    return open(com, "rb").read(), addrs


def fat12_geometry(img: bytearray) -> tuple[int, int, int, int]:
    """Return (clus_bytes, free_clusters, total_clusters, rootent) from the
    BPB + FAT-0. Same geometry math as fat12_add -- read-only, so kept small
    here."""
    bps = struct.unpack_from("<H", img, 11)[0]
    spc = img[13]
    resv = struct.unpack_from("<H", img, 14)[0]
    nfat = img[16]
    rootent = struct.unpack_from("<H", img, 17)[0]
    spf = struct.unpack_from("<H", img, 22)[0]
    first_root = resv + nfat * spf
    root_secs = (rootent * 32 + bps - 1) // bps
    first_data = first_root + root_secs
    fat_off = resv * bps
    total_clusters = (len(img) // bps - first_data) // spc + 2

    def get(c):
        idx = c * 3 // 2
        b = img[fat_off + idx] | (img[fat_off + idx + 1] << 8)
        return (b >> 4) if (c & 1) else (b & 0xFFF)

    free = sum(1 for c in range(2, total_clusters) if get(c) == 0)
    return bps * spc, free, total_clusters, rootent


def fill_root_dir(img: bytearray) -> int:
    """Inject tiny distinct-named dummy files until the root directory has no
    free slot left. Returns the number of dummies actually added."""
    added = 0
    while True:
        # 8-char numbered scheme: "DIRFILnn" (nn = 00..99), ext "TMP".
        name8 = f"DIRFIL{added:02d}"
        if len(name8) > 8:
            sys.exit(f"dummy-name counter overflowed 8.3 (added={added})")
        try:
            fat12_add(img, name8, "TMP", b"\x00")
        except SystemExit as e:
            if "root directory full" in str(e):
                return added
            raise
        added += 1


def build(dos_src: str, out: str, tmp_dir: str) -> dict:
    com_bytes, addrs = assemble(tmp_dir)
    shutil.copyfile(dos_src, out)
    img = bytearray(open(out, "rb").read())

    fat12_add(img, "BDOSX5", "COM", com_bytes)      # the exerciser first...
    # AUTOEXEC.BAT auto-runs BDOSX5 with zero typed keys (verify-first: see
    # tier2-autoexec-bat-harness-spec.md). Added BEFORE the root dir is saturated below,
    # so it occupies one of the slots the fixture fills anyway -- the dir still ends up
    # exactly saturated (fill_root_dir loops until SystemExit regardless of the count).
    fat12_add(img, "AUTOEXEC", "BAT", b"BDOSX5\r\n")
    dummies = fill_root_dir(img)                    # ...then saturate the root dir
    clus_bytes, free, total, rootent = fat12_geometry(img)
    if free < 1:
        sys.exit(f"fixture is disk-full too (free={free}); dir-full corner is ambiguous")

    open(out, "wb").write(img)
    addrs.update(clus_bytes=clus_bytes, free=free, total=total, rootent=rootent,
                 dummies=dummies, sig=com_bytes[2])  # byte at $0102 (arm signature)
    return addrs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True, help="source MSX-DOS 1 disk (e.g. test.dsk)")
    ap.add_argument("--out", default="/tmp/zerobas_bdosx5.dsk")
    ap.add_argument("--tmp-dir", default="/tmp")
    args = ap.parse_args()

    addrs = build(args.dos_disk, args.out, args.tmp_dir)
    print(f"built {args.out}")
    print(f"geometry: {addrs['clus_bytes']}-byte clusters, {addrs['total']} total, "
          f"{addrs['rootent']} root-dir entries, {addrs['dummies']} dummy files added "
          f"to saturate the root dir, {addrs['free']} free clusters left (dir-full, disk NOT full)")
    print(f"done = {addrs['done']:#06x}")
    print(f"fcb  = {addrs['fcb']:#06x}")
    print(f"regs = {addrs['regs']:#06x}")
    print()
    # fcb..regs end (8*8=64 B after regs) covers the FCB + all 3 used records
    # (37 B FCB not byte-aligned to regs, so the region spans fcb..regs+64).
    mem_len = (addrs["regs"] - addrs["fcb"]) + 8 * 8
    # --arm-check-val gates the anchor on the resident program (byte at $0102 == sig), so
    # occurrence #1 of `done` is the REAL program run, not a boot-time address collision
    # (the vacuous-anchor bug found 2026-07-04). See tier2-remediation-spec.md.
    print("next: python3 probes/disk/disk_probe_diff.py capture "
          f"--at {addrs['done']:#06x} --arm-check-val {addrs['sig']:#04x} --settle 90 "
          f"--machine both --mem {addrs['fcb']:#06x}:{mem_len:#x} --diska {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
