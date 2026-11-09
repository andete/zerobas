#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Build the throwaway disk for DSKFMT.COM (D-DSKFMT): what the disk ROM's CHOICE offers
and what DSKFMT writes -- see probes/disk/dskfmt.asm (it FORMATS the copy).
Assembles it with pasmo and injects DSKFMT.COM + an AUTOEXEC.BAT that runs it into a
copy of a DOS disk image (disk_probe_bdos.fat12_add).

Prints the assembled `done` label address (the disk_probe_diff.py `capture
--at` anchor) so it never has to be hand-guessed.

Usage:
  python3 probes/disk/build_dskfmt_disk.py --dos-disk ~/Documents/msx/msx/disks/test.dsk \
      --out /tmp/zerobas_dskfmt.dsk
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # sibling probes
from disk_probe_bdos import fat12_add  # noqa: E402  (reuse, don't duplicate)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import probe_tmp  # noqa: E402  -- every scratch file under the project's temp root

HERE = os.path.dirname(os.path.abspath(__file__))
ASM = os.path.join(HERE, "dskfmt.asm")
CHOICE = 1


def assemble(tmp_dir: str) -> tuple[bytes, int]:
    com = os.path.join(tmp_dir, "dskfmt.com")
    sym = os.path.join(tmp_dir, "dskfmt.sym")
    subprocess.run(["pasmo", "--bin", ASM, com, sym], check=True)
    syms = {}
    for line in open(sym):
        name, _, rest = line.strip().partition("\t")
        if rest.strip():
            syms[name.strip()] = int(rest.strip().split()[-1].rstrip("H"), 16)
    if "done" not in syms or "fchoice" not in syms:
        sys.exit("could not find `done` / `fchoice` in dskfmt.sym")
    com_bytes = bytearray(open(com, "rb").read())
    com_bytes[syms["fchoice"] - 0x100] = CHOICE
    return bytes(com_bytes), syms["done"]


def build(dos_src: str, out: str, tmp_dir: str) -> tuple[int, int]:
    com_bytes, done_addr = assemble(tmp_dir)
    shutil.copyfile(dos_src, out)
    img = bytearray(open(out, "rb").read())
    fat12_add(img, "DSKFMT", "COM", com_bytes)
    # AUTOEXEC.BAT auto-runs DSKFMT with zero typed keys (tier2-autoexec-bat-harness-spec.md).
    fat12_add(img, "AUTOEXEC", "BAT", b"DSKFMT\r\n")
    open(out, "wb").write(img)
    return done_addr, com_bytes[2]      # sig = byte at $0102 (resident-program arm signature)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True, help="source MSX-DOS 1 disk (e.g. test.dsk)")
    ap.add_argument("--out", default=probe_tmp.tmp("dskfmt.dsk"))
    ap.add_argument("--tmp-dir", default=probe_tmp.ROOT)
    ap.add_argument("--choice", type=int, default=1, help="DSKFMT's A: the CHOICE item (1..4)")
    args = ap.parse_args()
    global CHOICE
    CHOICE = args.choice

    done_addr, sig = build(args.dos_disk, args.out, args.tmp_dir)
    print(f"built {args.out}")
    print(f"done = {done_addr:#06x}")
    print()
    # --arm-check-val gates the anchor on the resident program (byte at $0102 == sig),
    # so occurrence #1 of `done` is the REAL program run, not a boot-time address collision
    # (the vacuous-anchor bug found 2026-07-04). See tier2-remediation-spec.md.
    print("next: python3 probes/disk/disk_probe_diff.py capture "
          f"--at {done_addr:#06x} --arm-check-val {sig:#04x} "
          "--settle 300 --machine both "  # choice 4 (2DD) takes the CF-3300 181 s
          f"--mem 0x0400:0x10C0 --diska {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
