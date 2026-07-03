#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Build the throwaway disk for the BDOSX0.COM exerciser (M23: BDOS $00
TERM0 micro-test, see disk/docs/tier2-bdos-remaining-spec.md SS5.2).
Assembles bdosx0.asm with pasmo, then injects BDOSX0.COM into a copy of a DOS
disk image via the FAT12 file-injector already written for the Tier-1 BDOS
oracle probe (disk_probe_bdos.fat12_add -- reused, not duplicated). No `done`
anchor is printed: TERM0 never returns, so there is nothing to capture --
evidence is a `callseq --log 0x0005` alignment check + a `screen` arbiter
showing both machines back at a live A> prompt (see the spec section above).

Usage:
  python3 probes/disk/build_bdosx0_disk.py --dos-disk ~/Documents/msx/msx/disks/test.dsk \
      --out /tmp/zerobas_bdosx0.dsk
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
ASM = os.path.join(HERE, "bdosx0.asm")


def assemble(tmp_dir: str) -> bytes:
    com = os.path.join(tmp_dir, "bdosx0.com")
    sym = os.path.join(tmp_dir, "bdosx0.sym")
    subprocess.run(["pasmo", "--bin", ASM, com, sym], check=True)
    return open(com, "rb").read()


def build(dos_src: str, out: str, tmp_dir: str) -> None:
    com_bytes = assemble(tmp_dir)
    shutil.copyfile(dos_src, out)
    img = bytearray(open(out, "rb").read())
    fat12_add(img, "BDOSX0", "COM", com_bytes)
    open(out, "wb").write(img)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True, help="source MSX-DOS 1 disk (e.g. test.dsk)")
    ap.add_argument("--out", default="/tmp/zerobas_bdosx0.dsk")
    ap.add_argument("--tmp-dir", default="/tmp")
    args = ap.parse_args()

    build(args.dos_disk, args.out, args.tmp_dir)
    print(f"built {args.out}")
    print()
    print("next: python3 probes/disk/disk_probe_diff.py callseq --log 0x0005 --maxhits 30 "
          f"--keys '\\rBDOSX0\\r' --keys-at 20 --settle 30 --diska {args.out}")
    print("      python3 probes/disk/disk_probe_diff.py screen --machine both "
          f"--keys '\\rBDOSX0\\r' --keys-at 20 --settle 30 --diska {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
