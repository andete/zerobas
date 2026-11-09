#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Build the throwaway disk for one D-DOSLADDER rung (TODO.md): assemble
probes/disk/dosl/<prog>.asm with pasmo, inject <PROG>.COM + an AUTOEXEC.BAT that
runs it into a copy of an MSX-DOS 1 disk image (disk_probe_bdos.fat12_add), and
print the disk_probe_diff.py capture command -- `done` the anchor, the 16-byte
`cap` block (or the program's own `cap` .. `cap_end`) the compared region.

Usage:
  python3 probes/disk/build_dosl_disk.py --prog d2type --dos-disk test.dsk [--out X]
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


def assemble(prog: str, tmp_dir: str) -> tuple[bytes, dict]:
    asm = os.path.join(HERE, "dosl", prog + ".asm")
    com = os.path.join(tmp_dir, prog + ".com")
    sym = os.path.join(tmp_dir, prog + ".sym")
    subprocess.run(["pasmo", "--bin", asm, com, sym], check=True)
    syms = {}
    for line in open(sym):
        name, _, rest = line.strip().partition("\t")
        if rest.strip():
            syms[name.strip()] = int(rest.strip().split()[-1].rstrip("H"), 16)
    for need in ("done", "cap"):
        if need not in syms:
            sys.exit(f"could not find `{need}` in {prog}.sym")
    return open(com, "rb").read(), syms


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prog", required=True, help="the rung: probes/disk/dosl/<prog>.asm")
    ap.add_argument("--dos-disk", required=True, help="source MSX-DOS 1 disk (e.g. test.dsk)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--tmp-dir", default=probe_tmp.ROOT)
    ap.add_argument("--settle", default="60")
    args = ap.parse_args()
    out = args.out or probe_tmp.tmp(f"dosl_{args.prog}.dsk")
    com, syms = assemble(args.prog, args.tmp_dir)
    shutil.copyfile(args.dos_disk, out)
    img = bytearray(open(out, "rb").read())
    name = args.prog.upper()[:8]
    fat12_add(img, name, "COM", com)
    fat12_add(img, "AUTOEXEC", "BAT", (name + "\r\n").encode())
    open(out, "wb").write(img)
    size = syms.get("cap_end", syms["cap"] + 16) - syms["cap"]
    print(f"built {out}")
    print(f"done = {syms['done']:#06x}")
    print()
    print("next: python3 probes/disk/disk_probe_diff.py capture "
          f"--at {syms['done']:#06x} --arm-check-val {com[2]:#04x} "
          f"--settle {args.settle} --machine both "
          f"--mem {syms['cap']:#06x}:{size:#x} --diska {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
