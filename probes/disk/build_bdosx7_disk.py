#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Build the throwaway disk for the BDOSX7.COM exerciser (Tier-C case 5:
rename-collision, see disk/docs/tier2-tierC-spec.md "Candidate cases" #5).

Assembles bdosx7.asm, then injects BDOSX7.COM + TWO 1-byte fixture files
"RENSRC.TMP" and "RENDST.TMP" (both present) into a copy of a DOS disk via
the SAME fat12_add injector the other BDOSX builders use (reuse, not
duplicated FAT surgery).

BDOSX7.COM issues $17 FREN "RENSRC.TMP" -> "RENDST.TMP" -- a rename onto a
name that ALREADY EXISTS -- then reopens both names to observe whether the
failed rename left the source intact and whether the pre-existing
destination survived untouched. We do not posit the FREN return code; the
differential captures whatever stock does and requires ours to match
byte-for-byte.

Prints the `done` anchor + the `fcb`/`regs` buffer addresses (the capture
--mem region), read from the .sym -- never hand-guessed (M15 lesson).

Usage:
  python3 probes/disk/build_bdosx7_disk.py --dos-disk ~/Documents/msx/msx/disks/test.dsk \
      --out /tmp/zerobas_bdosx7.dsk
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # sibling probes
from disk_probe_bdos import fat12_add  # noqa: E402  (reuse, don't duplicated)

HERE = os.path.dirname(os.path.abspath(__file__))
ASM = os.path.join(HERE, "bdosx7.asm")

SYM_NAMES = ("done", "fcb", "regs")


def assemble(tmp_dir: str) -> tuple[bytes, dict]:
    com = os.path.join(tmp_dir, "bdosx7.com")
    sym = os.path.join(tmp_dir, "bdosx7.sym")
    subprocess.run(["pasmo", "--bin", ASM, com, sym], check=True)
    addrs: dict = {}
    for line in open(sym):
        name, _, rest = line.strip().partition("\t")
        name = name.strip()
        if name in SYM_NAMES:
            addrs[name] = int(rest.strip().split()[-1].rstrip("H"), 16)
    missing = [n for n in SYM_NAMES if n not in addrs]
    if missing:
        sys.exit(f"could not find symbol(s) {missing} in bdosx7.sym")
    return open(com, "rb").read(), addrs


def build(dos_src: str, out: str, tmp_dir: str) -> dict:
    com_bytes, addrs = assemble(tmp_dir)
    shutil.copyfile(dos_src, out)
    img = bytearray(open(out, "rb").read())

    fat12_add(img, "BDOSX7", "COM", com_bytes)
    fat12_add(img, "RENSRC", "TMP", b"\x2a")     # arbitrary 1-byte content
    fat12_add(img, "RENDST", "TMP", b"\x5c")     # distinct 1-byte content (the collision target)
    # AUTOEXEC.BAT auto-runs BDOSX7 with zero typed keys (verify-first: see
    # tier2-autoexec-bat-harness-spec.md). Replaces the typed '\rBDOSX7\r' launch.
    fat12_add(img, "AUTOEXEC", "BAT", b"BDOSX7\r\n")

    open(out, "wb").write(img)
    addrs["sig"] = com_bytes[2]         # byte at $0102 (resident-program arm signature)
    return addrs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True, help="source MSX-DOS 1 disk (e.g. test.dsk)")
    ap.add_argument("--out", default="/tmp/zerobas_bdosx7.dsk")
    ap.add_argument("--tmp-dir", default="/tmp")
    args = ap.parse_args()

    addrs = build(args.dos_disk, args.out, args.tmp_dir)
    print(f"built {args.out}")
    for name in SYM_NAMES:
        print(f"{name} = {addrs[name]:#06x}")
    print()
    # fcb..regs end (8*8=64 B after regs) covers the FCB + all 3 used records.
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
