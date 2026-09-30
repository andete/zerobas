#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""Boot HIMEM and FRE(0) on the four machines, one boot each.

Written down as a file by D-ENGROW0 (2026-09-30): D-FCBSHAPE S1+S2 measured the
same two numbers (scratchpad/fcbs12_bootfre.out) with an inline script that was
never kept. Same program: HIMEM as the unsigned word at $FC4A, and FRE(0), right
after boot with nothing typed but this line (and SCREEN 0: the CF-3300 boots in
SCREEN 1, which the scrape cannot read). FRE(0) reads 46 B above
fcbs12_bootfre.out on EVERY machine -- that script's program is lost, and the
offset is uniform, so the cross-machine differences are what compare.
"""
from __future__ import annotations
import os, re, shutil, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

SIDES = [("Philips_VG_8020", 14.0), ("National_CF-3300", 14.0),
         ("C-BIOS_MSX1_EU_REPACK_NODISK", 8.0), ("C-BIOS_MSX1_EU_REPACK_DISK", 8.0)]
LINE = 'PRINT"[";PEEK(-950)+256*PEEK(-949);FRE(0);"]"'   # -950 = $FC4A


def main() -> int:
    print("boot HIMEM and FRE(0), one boot each")
    for machine, boot in SIDES:
        kw = {}
        if machine in ("National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"):
            tmp = tempfile.mkstemp(suffix=".dsk")[1]
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), tmp)
            kw["diska"] = tmp
        caps = omsx_repl.run_cases(machine, [("boot", [LINE])], batch=False,
                                   boot=boot, reset=("", "SCREEN 0"),
                                   cap_gap=20.0, timeout=600.0, **kw)
        m = re.search(r"\[\s*(\d+)\s+(\d+)\s*\]", caps[0] or "")
        print(f"  {machine:32s} " + (f"{m.group(1)} {m.group(2)}" if m
                                     else "<NO OUTPUT>"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
