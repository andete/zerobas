#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Build the throwaway disk for the BDOSX6.COM exerciser (Tier-C case 4:
past-EOF random-record I/O, see disk/docs/tier2-tierC-spec.md "Candidate
cases" #4).

Assembles bdosx6.asm, then injects BDOSX6.COM + a short fixture file
"SHORT.DAT" (exactly 256 bytes = 2x 128-byte records, 1 data cluster) into a
copy of a DOS disk via the SAME fat12_add injector the other BDOSX builders
use (reuse, not duplicated FAT surgery).

BDOSX6.COM opens SHORT.DAT, sets record size 128, then points the FCB's
random-record field (+33..35) at record 5 -- past the file's actual end
(only records 0 and 1 exist) -- and issues RDRND (expect some EOF/unwritten-
record code, no valid data) followed by WRRND at the same position
(expected to extend the file; record 5 = byte offset 640, still inside the
fixture's single 1024-byte cluster, so no second-cluster allocation is
forced). We do not posit what the return codes are; the differential
captures whatever stock does and requires ours to match byte-for-byte.

Prints the `done` anchor + BOTH capture regions (fcb..regs, the corner's
register/FCB state; and rdbuf, what RDRND past EOF delivered) read from the
.sym -- never hand-guessed (M15 lesson).

Usage:
  python3 probes/disk/build_bdosx6_disk.py --dos-disk ~/Documents/msx/msx/disks/test.dsk \
      --out /tmp/zerobas_bdosx6.dsk
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
ASM = os.path.join(HERE, "bdosx6.asm")


def short_dat(size: int = 256) -> bytes:
    """Deterministic, position-varying content: byte i = (i*7 + 3) & 0xFF
    (same generator idiom as disk_probe_bdos.py's ORACLE2.BIN)."""
    return bytes([(i * 7 + 3) & 0xFF for i in range(size)])


SYM_NAMES = ("done", "fcb", "regs", "wrsize", "rdbuf", "wrpat")


def assemble(tmp_dir: str) -> tuple[bytes, dict]:
    com = os.path.join(tmp_dir, "bdosx6.com")
    sym = os.path.join(tmp_dir, "bdosx6.sym")
    subprocess.run(["pasmo", "--bin", ASM, com, sym], check=True)
    addrs: dict = {}
    for line in open(sym):
        name, _, rest = line.strip().partition("\t")
        name = name.strip()
        if name in SYM_NAMES:
            addrs[name] = int(rest.strip().split()[-1].rstrip("H"), 16)
    missing = [n for n in SYM_NAMES if n not in addrs]
    if missing:
        sys.exit(f"could not find symbol(s) {missing} in bdosx6.sym")
    return open(com, "rb").read(), addrs


def build(dos_src: str, out: str, tmp_dir: str) -> dict:
    com_bytes, addrs = assemble(tmp_dir)
    shutil.copyfile(dos_src, out)
    img = bytearray(open(out, "rb").read())

    fat12_add(img, "BDOSX6", "COM", com_bytes)
    fat12_add(img, "SHORT", "DAT", short_dat())
    # AUTOEXEC.BAT auto-runs BDOSX6 with zero typed keys (verify-first: see
    # tier2-autoexec-bat-harness-spec.md). Replaces the typed '\rBDOSX6\r' launch.
    fat12_add(img, "AUTOEXEC", "BAT", b"BDOSX6\r\n")

    open(out, "wb").write(img)
    addrs["sig"] = com_bytes[2]         # byte at $0102 (resident-program arm signature)
    return addrs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True, help="source MSX-DOS 1 disk (e.g. test.dsk)")
    ap.add_argument("--out", default="/tmp/zerobas_bdosx6.dsk")
    ap.add_argument("--tmp-dir", default="/tmp")
    args = ap.parse_args()

    addrs = build(args.dos_disk, args.out, args.tmp_dir)
    print(f"built {args.out}")
    for name in SYM_NAMES:
        print(f"{name} = {addrs[name]:#06x}")
    print()
    # fcb..wrsize+4 covers the FCB (record 4's re-FOPEN reloads +16..19 from the
    # on-disk dirent -- the M36 non-vacuity check), all 5 used records in regs,
    # AND the saved post-WRRND size snapshot (wrsize) -- one contiguous region
    # (fcb, regs, wrsize are laid out back-to-back in bdosx6.asm).
    fcb_len = (addrs["wrsize"] - addrs["fcb"]) + 4
    # --arm-check-val gates the anchor on the resident program (byte at $0102 == sig),
    # so occurrence #1 of `done` is the REAL program run, not a boot-time address
    # collision (the vacuous-anchor bug found 2026-07-04). See tier2-remediation-spec.md.
    print("next: python3 probes/disk/disk_probe_diff.py capture "
          f"--at {addrs['done']:#06x} --arm-check-val {addrs['sig']:#04x} --settle 90 "
          f"--machine both --mem {addrs['fcb']:#06x}:{fcb_len:#x} --diska {args.out}")
    print("      python3 probes/disk/disk_probe_diff.py capture "
          f"--at {addrs['done']:#06x} --arm-check-val {addrs['sig']:#04x} --settle 90 "
          f"--machine both --mem {addrs['rdbuf']:#06x}:0x80 --diska {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
