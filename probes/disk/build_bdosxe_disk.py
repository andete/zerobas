#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause

"""Build the WRITE-PROTECTED disk for the BDOSXE.COM exerciser (D-DISKCONTRACT gap 2: a
disk error as an MSX-DOS program sees it through the BDOS and DISKVE).

Assembles bdosxe.asm, injects BDOSXE.COM and an AUTOEXEC.BAT that runs it into a copy
of a DOS disk, then makes the image file READ-ONLY. disk_probe_diff.py copies the image
with shutil.copy2, which keeps the mode, so openMSX mounts it write-protected on both
machines: MSX-DOS boots (reads only) and BDOSXE's FMAKE / WRABS meet the error.

Prints the `done` anchor and the capture block (regs + hrec + hcount, 65 B), read from
the .sym -- never hand-guessed.

Usage:
  python3 probes/disk/build_bdosxe_disk.py --dos-disk ~/Documents/msx/msx/disks/test.dsk \\
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
ASM = os.path.join(HERE, "bdosxe.asm")
SYM_NAMES = ("done", "regs", "hcount", "answers", "dv0")


def assemble(tmp_dir: str) -> tuple[bytes, dict]:
    com = os.path.join(tmp_dir, "bdosxe.com")
    sym = os.path.join(tmp_dir, "bdosxe.sym")
    subprocess.run(["pasmo", "--bin", ASM, com, sym], check=True)
    addrs: dict = {}
    for line in open(sym):
        name, _, rest = line.strip().partition("\t")
        name = name.strip()
        if name in SYM_NAMES:
            addrs[name] = int(rest.strip().split()[-1].rstrip("H"), 16)
    missing = [n for n in SYM_NAMES if n not in addrs]
    if missing:
        sys.exit(f"could not find symbol(s) {missing} in bdosxe.sym")
    return open(com, "rb").read(), addrs


def build(dos_src: str, out: str, tmp_dir: str, answers=()) -> dict:
    com_bytes, addrs = assemble(tmp_dir)
    com = bytearray(com_bytes)
    for i, a in enumerate(answers):             # the handler's answer per call (0 / 1)
        com[addrs["answers"] - 0x100 + i] = a
    com_bytes = bytes(com)
    if os.path.exists(out):                       # a previous run left it read-only
        os.chmod(out, stat.S_IRUSR | stat.S_IWUSR)
    shutil.copyfile(dos_src, out)
    img = bytearray(open(out, "rb").read())
    fat12_add(img, "BDOSXE", "COM", com_bytes)
    fat12_add(img, "AUTOEXEC", "BAT", b"BDOSXE\r\n")
    open(out, "wb").write(img)
    os.chmod(out, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)   # write-protected mount
    addrs["sig"] = com_bytes[2]                   # byte at $0102 (resident-program arm)
    addrs["len"] = addrs["dv0"] + 4 + 5 - addrs["regs"]
    if addrs["len"] != 3 * 8 + 6 * 8 + 1 + 4 + 5:
        sys.exit(f"regs / hrec / hcount are not contiguous ({addrs['len']} B)")
    return addrs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True, help="source MSX-DOS 1 disk (e.g. test.dsk)")
    # under the temp ROOT, not probe_tmp.tmp(): this process's own directory is removed at
    # exit, and the printed command uses the image from ANOTHER process
    os.makedirs(probe_tmp.BASE, exist_ok=True)
    ap.add_argument("--out", default=os.path.join(probe_tmp.BASE, "zerobas_bdosxe.dsk"))
    ap.add_argument("--tmp-dir", default=probe_tmp.BASE)
    ap.add_argument("--answers", default="", help="the handler's answer per call, e.g. 1,0")
    args = ap.parse_args()
    addrs = build(args.dos_disk, args.out, args.tmp_dir,
                  [int(x) for x in args.answers.split(",") if x != ""])
    print(f"built {args.out} (read-only)")
    print(f"done = {addrs['done']:#06x}")
    print(f"regs = {addrs['regs']:#06x} ({addrs['len']} B: 3 BDOS returns, 6 handler slots, the count)")
    print()
    print("next: python3 probes/disk/disk_probe_diff.py capture "
          f"--at {addrs['done']:#06x} --arm-check-val {addrs['sig']:#04x} --settle 90 "
          f"--machine both --mem {addrs['regs']:#06x}:{addrs['len']:#04x} --diska {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
