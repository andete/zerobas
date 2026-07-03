#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Build the throwaway disk for the BDOSX3.COM exerciser (M24: mutation +
random + absolute-I/O block, see disk/docs/tier2-bdos-remaining-spec.md
SS5.3). Assembles bdosx3.asm with pasmo, then injects BDOSX3.COM + the
Phase-1 384-byte BDOSX.BIN data file (reused byte-for-byte -- same generator
as build_bdosx_disk.py, not duplicated content) into a copy of a DOS disk
image via the FAT12 file-injector already written for the Tier-1 BDOS oracle
probe (disk_probe_bdos.fat12_add).

The scratch files BDOSXW.TMP / BDOSXR.TMP are NOT pre-seeded -- BDOSX3.COM
creates, writes, closes, renames and deletes them itself; that lifecycle is
exactly what this milestone is testing.

Prints the assembled `done` label address (the disk_probe_diff.py `capture
--at` anchor) so it never has to be hand-guessed.

Usage:
  python3 probes/disk/build_bdosx3_disk.py --dos-disk ~/Documents/msx/msx/disks/test.dsk \
      --out /tmp/zerobas_bdosx3.dsk
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
ASM = os.path.join(HERE, "bdosx3.asm")


def bdosx_bin(size: int = 384) -> bytes:
    """Deterministic, position-varying content: byte i = (i*5 + 7) & 0xFF.
    Byte-identical to build_bdosx_disk.py's generator (same file, same
    content) -- BDOSX3.COM's record 17-20 relies on this exact pattern."""
    return bytes([(i * 5 + 7) & 0xFF for i in range(size)])


SYM_NAMES = ("done", "fcb", "regs", "wrpat", "rdbuf", "rdbuf2", "absbuf")


def assemble(tmp_dir: str) -> tuple[bytes, dict[str, int]]:
    com = os.path.join(tmp_dir, "bdosx3.com")
    sym = os.path.join(tmp_dir, "bdosx3.sym")
    subprocess.run(["pasmo", "--bin", ASM, com, sym], check=True)
    addrs: dict[str, int] = {}
    for line in open(sym):
        name, _, rest = line.strip().partition("\t")
        name = name.strip()
        if name in SYM_NAMES:
            addrs[name] = int(rest.strip().split()[-1].rstrip("H"), 16)
    missing = [n for n in SYM_NAMES if n not in addrs]
    if missing:
        sys.exit(f"could not find symbol(s) {missing} in bdosx3.sym")
    return open(com, "rb").read(), addrs


def build(dos_src: str, out: str, tmp_dir: str) -> dict[str, int]:
    com_bytes, addrs = assemble(tmp_dir)
    shutil.copyfile(dos_src, out)
    img = bytearray(open(out, "rb").read())
    fat12_add(img, "BDOSX", "BIN", bdosx_bin())
    fat12_add(img, "BDOSX3", "COM", com_bytes)
    open(out, "wb").write(img)
    return addrs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True, help="source MSX-DOS 1 disk (e.g. test.dsk)")
    ap.add_argument("--out", default="/tmp/zerobas_bdosx3.dsk")
    ap.add_argument("--tmp-dir", default="/tmp")
    args = ap.parse_args()

    addrs = build(args.dos_disk, args.out, args.tmp_dir)
    print(f"built {args.out}")
    for name in SYM_NAMES:
        print(f"{name} = {addrs[name]:#06x}")
    print()
    # fcb..regs end (32*8=256 B after regs) covers the FCB+regs region;
    # wrpat..absbuf end (128+128+128+512=896 B after wrpat) covers the buffers.
    fcb_len = (addrs["regs"] - addrs["fcb"]) + 32 * 8
    buf_len = (addrs["absbuf"] - addrs["wrpat"]) + 512
    print("next: python3 probes/disk/disk_probe_diff.py capture "
          f"--at {addrs['done']:#06x} --keys '\\rBDOSX3\\r' --keys-at 20 --settle 60 "
          f"--machine both --mem {addrs['fcb']:#06x}:{fcb_len:#x} --diska {args.out}")
    print("      python3 probes/disk/disk_probe_diff.py capture "
          f"--at {addrs['done']:#06x} --keys '\\rBDOSX3\\r' --keys-at 20 --settle 60 "
          f"--machine both --mem {addrs['wrpat']:#06x}:{buf_len:#x} --diska {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
