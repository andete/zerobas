#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Build the throwaway disk for the BDOSX.COM exerciser (see
disk/docs/tier2-bdos-exerciser-spec.md). Assembles bdosx.asm with pasmo, then
injects BDOSX.COM + its 384-byte test file BDOSX.BIN into a copy of a DOS
disk image via the FAT12 file-injector already written for the Tier-1 BDOS
oracle probe (disk_probe_bdos.fat12_add -- reused, not duplicated).

Prints the assembled `done` label address (the disk_probe_diff.py `capture
--at` anchor) so it never has to be hand-guessed.

Usage:
  python3 probes/disk/build_bdosx_disk.py --dos-disk ~/Documents/msx/msx/disks/test.dsk \
      --out /tmp/zerobas_bdosx.dsk
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
ASM = os.path.join(HERE, "bdosx.asm")


def bdosx_bin(size: int = 384) -> bytes:
    """Deterministic, position-varying content: byte i = (i*5 + 7) & 0xFF."""
    return bytes([(i * 5 + 7) & 0xFF for i in range(size)])


def assemble(tmp_dir: str) -> tuple[bytes, int]:
    com = os.path.join(tmp_dir, "bdosx.com")
    sym = os.path.join(tmp_dir, "bdosx.sym")
    subprocess.run(["pasmo", "--bin", ASM, com, sym], check=True)
    done = None
    for line in open(sym):
        name, _, rest = line.strip().partition("\t")
        if name.strip() == "done":
            done = int(rest.strip().split()[-1].rstrip("H"), 16)
    if done is None:
        sys.exit("could not find `done` symbol in bdosx.sym")
    return open(com, "rb").read(), done


def build(dos_src: str, out: str, tmp_dir: str) -> tuple[int, int]:
    com_bytes, done_addr = assemble(tmp_dir)
    shutil.copyfile(dos_src, out)
    img = bytearray(open(out, "rb").read())
    fat12_add(img, "BDOSX", "BIN", bdosx_bin())
    fat12_add(img, "BDOSX", "COM", com_bytes)
    open(out, "wb").write(img)
    return done_addr, com_bytes[2]      # sig = byte at $0102 (resident-program arm signature)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True, help="source MSX-DOS 1 disk (e.g. test.dsk)")
    ap.add_argument("--out", default="/tmp/zerobas_bdosx.dsk")
    ap.add_argument("--tmp-dir", default="/tmp")
    args = ap.parse_args()

    done_addr, sig = build(args.dos_disk, args.out, args.tmp_dir)
    print(f"built {args.out}")
    print(f"done = {done_addr:#06x}")
    print()
    # --arm-check-val gates the anchor on the resident program (byte at $0102 == sig),
    # so occurrence #1 of the `done` self-loop is the REAL program run, not a boot-time
    # address collision (the vacuous-anchor bug found 2026-07-04). See tier2-remediation-spec.md.
    print("next: python3 probes/disk/disk_probe_diff.py capture "
          f"--at {done_addr:#06x} --arm-check-val {sig:#04x} --keys '\\rBDOSX\\r' --keys-at 20 --settle 40 "
          f"--machine both --mem 0x0300:0x180 --diska {args.out}")
    print("      python3 probes/disk/disk_probe_diff.py capture "
          f"--at {done_addr:#06x} --arm-check-val {sig:#04x} --keys '\\rBDOSX\\r' --keys-at 20 --settle 40 "
          f"--machine both --mem 0x0400:0x180 --diska {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
