#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Build the throwaway disk for the BDOSX8.COM exerciser (Item 5,
spec-diskbasic-option-closure.md: the WRSEQ $15 FCB position write-back
differential).

Assembles bdosx8.asm, then injects BDOSX8.COM + an AUTOEXEC.BAT auto-run into a
copy of a DOS disk via the SAME fat12_add injector the other BDOSX builders
use. No fixture file is needed: BDOSX8 FMAKEs its own scratch file
("WSEQPOS.DAT") and WRSEQs 10 records into it, so the disk just needs free
space (any normal DOS disk).

BDOSX8 exercises the write branch of $15 WRSEQ, then freezes the post-WRSEQ FCB
position (fcbsnap) before FCLOSE. The differential captures whatever stock
writes into the FCB position fields (+12/+28,29/+30/+32) and requires ours to
match byte-for-byte -- the write-side twin of the M33 read-branch fix.

Prints the `done` anchor + the single contiguous capture region (fcb..fcbsnap+37)
read from the .sym -- never hand-guessed (M15 lesson).

Usage:
  python3 probes/disk/build_bdosx8_disk.py --dos-disk ~/Documents/msx/msx/disks/test.dsk \
      --out /tmp/zerobas_bdosx8.dsk
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # sibling probes
from disk_probe_bdos import fat12_add  # noqa: E402  (reuse, don't duplicate)

HERE = os.path.dirname(os.path.abspath(__file__))
ASM = os.path.join(HERE, "bdosx8.asm")

SYM_NAMES = ("done", "fcb", "regs", "fcbsnap", "wrpat")


def assemble(tmp_dir: str) -> tuple[bytes, dict]:
    com = os.path.join(tmp_dir, "bdosx8.com")
    sym = os.path.join(tmp_dir, "bdosx8.sym")
    subprocess.run(["pasmo", "--bin", ASM, com, sym], check=True)
    addrs: dict = {}
    for line in open(sym):
        name, _, rest = line.strip().partition("\t")
        name = name.strip()
        if name in SYM_NAMES:
            addrs[name] = int(rest.strip().split()[-1].rstrip("H"), 16)
    missing = [n for n in SYM_NAMES if n not in addrs]
    if missing:
        sys.exit(f"could not find symbol(s) {missing} in bdosx8.sym")
    return open(com, "rb").read(), addrs


def build(dos_src: str, out: str, tmp_dir: str) -> dict:
    com_bytes, addrs = assemble(tmp_dir)
    shutil.copyfile(dos_src, out)
    img = bytearray(open(out, "rb").read())

    fat12_add(img, "BDOSX8", "COM", com_bytes)
    # AUTOEXEC.BAT auto-runs BDOSX8 with zero typed keys (verify-first: see
    # tier2-autoexec-bat-harness-spec.md). Replaces any typed launch.
    fat12_add(img, "AUTOEXEC", "BAT", b"BDOSX8\r\n")

    open(out, "wb").write(img)
    addrs["sig"] = com_bytes[2]         # byte at $0102 (resident-program arm signature)
    return addrs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True, help="source MSX-DOS 1 disk (e.g. test.dsk)")
    ap.add_argument("--out", default="/tmp/zerobas_bdosx8.dsk")
    ap.add_argument("--tmp-dir", default="/tmp")
    args = ap.parse_args()

    addrs = build(args.dos_disk, args.out, args.tmp_dir)
    print(f"built {args.out}")
    for name in SYM_NAMES:
        print(f"{name} = {addrs[name]:#06x}")
    print()
    # fcb..fcbsnap+37: one contiguous region covering the live post-FCLOSE FCB,
    # all 12 used records in regs, AND the frozen post-WRSEQ FCB position
    # snapshot (fcb, regs, fcbsnap are back-to-back in bdosx8.asm).
    fcb_len = (addrs["fcbsnap"] - addrs["fcb"]) + 37
    # --arm-check-val gates the anchor on the resident program (byte at $0102 == sig),
    # so occurrence #1 of `done` is the REAL program run, not a boot-time collision
    # (the vacuous-anchor bug found 2026-07-04). See tier2-remediation-spec.md.
    print("next: python3 probes/disk/disk_probe_diff.py capture "
          f"--at {addrs['done']:#06x} --arm-check-val {addrs['sig']:#04x} --settle 90 "
          f"--machine both --mem {addrs['fcb']:#06x}:{fcb_len:#x} --diska {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
