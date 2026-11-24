#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause

"""Build the disk for the BDOSXK.COM exerciser (D-DISKCONTRACT gap 5: what CONIN's and BUFIN's echo
put on the screen).

Assembles bdosxk.asm and injects BDOSXK.COM and an AUTOEXEC.BAT that runs it into a copy of
a DOS disk. Prints the `done` anchor and the capture block (cells + the 960-byte screen copy,
986 B), read from the .sym -- never hand-guessed. The keys (--keys2) are typed after the
program has loaded.

Usage:
  python3 probes/disk/build_bdosxk_disk.py --dos-disk ~/Documents/msx/msx/disks/test.dsk \\
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
ASM = os.path.join(HERE, "bdosxk.asm")
SYM_NAMES = ("done", "cells", "screen")


def assemble(tmp_dir: str) -> tuple[bytes, dict]:
    com = os.path.join(tmp_dir, "bdosxk.com")
    sym = os.path.join(tmp_dir, "bdosxk.sym")
    subprocess.run(["pasmo", "--bin", ASM, com, sym], check=True)
    addrs: dict = {}
    for line in open(sym):
        name, _, rest = line.strip().partition("\t")
        name = name.strip()
        if name in SYM_NAMES:
            addrs[name] = int(rest.strip().split()[-1].rstrip("H"), 16)
    missing = [n for n in SYM_NAMES if n not in addrs]
    if missing:
        sys.exit(f"could not find symbol(s) {missing} in bdosxk.sym")
    return open(com, "rb").read(), addrs


def build(dos_src: str, out: str, tmp_dir: str) -> dict:
    com_bytes, addrs = assemble(tmp_dir)
    if os.path.exists(out):
        os.chmod(out, stat.S_IRUSR | stat.S_IWUSR)
    shutil.copyfile(dos_src, out)
    img = bytearray(open(out, "rb").read())
    fat12_add(img, "BDOSXK", "COM", com_bytes)
    # MODE 32 first (D-DISKROMHOST step 2b, 2026-11-24): MSX-DOS now starts in the host's
    # start-up screen ($7D2F: JP SCREEN 1 / 29 on the CF-3300, EU TEXT1 / 37 on zerobas, a
    # style split the VG-8020 decides -- dosmode-acceptance measures it). This exerciser's
    # subject is the BDOS console, so it fixes its own screen; dosmode-acceptance's mode32
    # row shows MODE 32 leaves identical cells on both machines.
    fat12_add(img, "AUTOEXEC", "BAT", b"MODE 32\r\nBDOSXK\r\n")
    open(out, "wb").write(img)
    addrs["sig"] = com_bytes[2]                   # byte at $0102 (resident-program arm)
    addrs["len"] = addrs["screen"] + 960 - addrs["cells"]
    return addrs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True, help="source MSX-DOS 1 disk (e.g. test.dsk)")
    # under the temp ROOT, not probe_tmp.tmp(): this process's own directory is removed at
    # exit, and the printed command uses the image from ANOTHER process
    os.makedirs(probe_tmp.BASE, exist_ok=True)
    ap.add_argument("--out", default=os.path.join(probe_tmp.BASE, "zerobas_bdosxk.dsk"))
    ap.add_argument("--tmp-dir", default=probe_tmp.BASE)
    args = ap.parse_args()
    addrs = build(args.dos_disk, args.out, args.tmp_dir)
    print(f"built {args.out}")
    print(f"done = {addrs['done']:#06x}")
    print(f"cells = {addrs['cells']:#06x} ({addrs['len']} B: $A5, CONIN's A, the BUFIN buffer, the screen)")
    print()
    print("next: python3 probes/disk/disk_probe_diff.py capture "
          f"--at {addrs['done']:#06x} --arm-check-val {addrs['sig']:#04x} --settle 90 "
          "--keys2 'xHelz\\blo\\r' --keys2-at 30 "
          f"--machine both --mem {addrs['cells']:#06x}:{addrs['len']:#05x} --diska {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
