#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Build the disk for the BDOSXS.COM exerciser (D-DISKCONTRACT gap 7: a disk SWAP seen through
DSKCHG and the BDOS).

Assembles bdosxs.asm and injects BDOSXS.COM and an AUTOEXEC.BAT that runs it into a copy of
a DOS disk; writes a SECOND image -- the same plus SWAPPED.TXT -- that the harness puts in
drive A at --swap-at (disk_probe_diff.py --swap-image), before typing the key the program
waits for. Prints the `done` anchor and the capture block (regs, the DPB, the DTA: 81 B).

Usage:
  python3 probes/disk/build_bdosxs_disk.py --dos-disk ~/Documents/msx/msx/disks/test.dsk \\
      [--out PATH]
"""
from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # sibling probes
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
from disk_probe_bdos import fat12_add  # noqa: E402  (reuse, don't duplicate)
import probe_tmp  # noqa: E402  (every scratch file under the project's temp root)

HERE = os.path.dirname(os.path.abspath(__file__))
ASM = os.path.join(HERE, "bdosxs.asm")
SYM_NAMES = ("done", "regs", "dta")


def assemble(tmp_dir: str) -> tuple[bytes, dict]:
    com = os.path.join(tmp_dir, "bdosxs.com")
    sym = os.path.join(tmp_dir, "bdosxs.sym")
    subprocess.run(["pasmo", "--bin", ASM, com, sym], check=True)
    addrs: dict = {}
    for line in open(sym):
        name, _, rest = line.strip().partition("\t")
        name = name.strip()
        if name in SYM_NAMES:
            addrs[name] = int(rest.strip().split()[-1].rstrip("H"), 16)
    missing = [n for n in SYM_NAMES if n not in addrs]
    if missing:
        sys.exit(f"could not find symbol(s) {missing} in bdosxs.sym")
    return open(com, "rb").read(), addrs


def build(dos_src: str, out: str, tmp_dir: str) -> dict:
    com_bytes, addrs = assemble(tmp_dir)
    if os.path.exists(out):
        os.chmod(out, stat.S_IRUSR | stat.S_IWUSR)
    shutil.copyfile(dos_src, out)
    img = bytearray(open(out, "rb").read())
    fat12_add(img, "BDOSXS", "COM", com_bytes)
    fat12_add(img, "AUTOEXEC", "BAT", b"BDOSXS\r\n")
    open(out, "wb").write(img)
    swap = bytearray(img)
    fat12_add(swap, "SWAPPED", "TXT", b"THE SECOND DISK\r\n")
    open(out + ".swap.dsk", "wb").write(swap)
    addrs["sig"] = com_bytes[2]                   # byte at $0102 (resident-program arm)
    addrs["len"] = addrs["dta"] + 33 - addrs["regs"]
    return addrs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True, help="source MSX-DOS 1 disk (e.g. test.dsk)")
    # under the temp ROOT, not probe_tmp.tmp(): this process's own directory is removed at
    # exit, and the printed command uses the image from ANOTHER process
    os.makedirs(probe_tmp.BASE, exist_ok=True)
    ap.add_argument("--out", default=os.path.join(probe_tmp.BASE, "zerobas_bdosxs.dsk"))
    ap.add_argument("--tmp-dir", default=probe_tmp.BASE)
    args = ap.parse_args()
    addrs = build(args.dos_disk, args.out, args.tmp_dir)
    print(f"built {args.out}")
    print(f"done = {addrs['done']:#06x}")
    print(f"regs = {addrs['regs']:#06x} ({addrs['len']} B: the records, the DPB, the DTA)")
    print()
    print("next: python3 probes/disk/disk_probe_diff.py capture "
          f"--at {addrs['done']:#06x} --arm-check-val {addrs['sig']:#04x} --settle 90 "
          f"--swap-image {args.out}.swap.dsk --swap-at 30 --keys2 'k' --keys2-at 33 "
          f"--machine both --mem {addrs['regs']:#06x}:{addrs['len']:#04x} --diska {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
