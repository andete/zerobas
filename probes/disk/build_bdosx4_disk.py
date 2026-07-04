#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Build the NEAR-FULL throwaway disk for the BDOSX4.COM exerciser (Tier-C case
2: the disk-full corner of Sequential Write, see disk/docs/tier2-tierC-spec.md).

Assembles bdosx4.asm, injects BDOSX4.COM into a copy of a DOS disk, then injects
a FILLER.DAT sized to consume ALL remaining free clusters -- leaving a 100%-FULL
volume. On the next boot BDOSX4.COM's first WRSEQ that needs to allocate a data
cluster finds NONE and returns the disk-full code; the differential asserts our
return code + register + FCB state match the National CF-3300's byte-for-byte.

A completely-full fixture (rather than one-free-cluster) is deliberate: it makes
the corner fire on the FIRST cluster allocation with NO successful physical data
flush beforehand. A near-full disk would force two slow emulated-FDC sector writes
before disk-full at record 9, and those writes desync the differential's trace
snapshot without adding coverage the happy-path BDOSX3 WRSEQ hasn't already proven.
Zero-free is fast, deterministic, and isolates exactly the disk-full return.

The filler is injected via the SAME fat12_add injector the other BDOSX builders
use (reuse, not duplicated FAT surgery): a file of `free` clusters' worth of zero
bytes consumes every free cluster. We assert the post-injection free count is
exactly 0 and print the geometry, so any disk whose cluster size or free space
differs from the CF-3300 720 KB target (spc=2, 1024-byte clusters) is caught at
build time rather than silently mis-targeting the corner.

Prints the `done` anchor + the `regs` buffer address (the capture --mem region),
read from the .sym -- never hand-guessed (M15 lesson).

Usage:
  python3 probes/disk/build_bdosx4_disk.py --dos-disk ~/Documents/msx/msx/disks/test.dsk \
      --out /tmp/zerobas_bdosx4.dsk
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
ASM = os.path.join(HERE, "bdosx4.asm")

SYM_NAMES = ("done", "regs")


def assemble(tmp_dir: str) -> tuple[bytes, dict]:
    com = os.path.join(tmp_dir, "bdosx4.com")
    sym = os.path.join(tmp_dir, "bdosx4.sym")
    subprocess.run(["pasmo", "--bin", ASM, com, sym], check=True)
    addrs: dict = {}
    for line in open(sym):
        name, _, rest = line.strip().partition("\t")
        name = name.strip()
        if name in SYM_NAMES:
            addrs[name] = int(rest.strip().split()[-1].rstrip("H"), 16)
    missing = [n for n in SYM_NAMES if n not in addrs]
    if missing:
        sys.exit(f"could not find symbol(s) {missing} in bdosx4.sym")
    return open(com, "rb").read(), addrs


def fat12_geometry(img: bytearray) -> tuple[int, int, int]:
    """Return (clus_bytes, free_clusters, total_clusters) from the BPB + FAT-0.
    Same geometry math as fat12_add -- read-only, so kept small here."""
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
    return bps * spc, free, total_clusters


def build(dos_src: str, out: str, tmp_dir: str) -> dict:
    com_bytes, addrs = assemble(tmp_dir)
    shutil.copyfile(dos_src, out)
    img = bytearray(open(out, "rb").read())

    fat12_add(img, "BDOSX4", "COM", com_bytes)      # the exerciser first...
    clus_bytes, free, total = fat12_geometry(img)
    if free < 1:
        sys.exit(f"source disk has no free clusters after injecting BDOSX4.COM")
    fat12_add(img, "FILLER", "DAT", bytes(free * clus_bytes))  # ...then fill to 0
    _, free_after, _ = fat12_geometry(img)
    if free_after != 0:
        sys.exit(f"post-fill free clusters = {free_after}, expected exactly 0")

    open(out, "wb").write(img)
    addrs.update(clus_bytes=clus_bytes, total=total, free_after=free_after,
                 sig=com_bytes[2])          # byte at $0102 (resident-program arm signature)
    return addrs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True, help="source MSX-DOS 1 disk (e.g. test.dsk)")
    ap.add_argument("--out", default="/tmp/zerobas_bdosx4.dsk")
    ap.add_argument("--tmp-dir", default="/tmp")
    args = ap.parse_args()

    addrs = build(args.dos_disk, args.out, args.tmp_dir)
    print(f"built {args.out}")
    print(f"geometry: {addrs['clus_bytes']}-byte clusters, {addrs['total']} total, "
          f"{addrs['free_after']} free clusters left (100%-full fixture)")
    print(f"done = {addrs['done']:#06x}")
    print(f"regs = {addrs['regs']:#06x}")
    print()
    # 16 records x 8 B = 0x80; captures FMAKE + 12 WRSEQ (crossing disk-full) + FCLOSE.
    # --arm-check-val gates on the resident program (byte at $0102 == sig) so the anchor is the
    # REAL program run, not a boot-time collision (vacuous-anchor bug, 2026-07-04).
    print("next: python3 probes/disk/disk_probe_diff.py capture "
          f"--at {addrs['done']:#06x} --arm-check-val {addrs['sig']:#04x} --keys '\\rBDOSX4\\r' --keys-at 20 --settle 60 "
          f"--machine both --mem {addrs['regs']:#06x}:0x80 --diska {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
