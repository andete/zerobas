#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DRVCOUNT: DRVINF ($FB21, the drive count of the first disk interface) and $FB22 (its
slot) as a Disk BASIC program reads them -- the CF-3300 against zerobas.

D-DRVINT (2026-11-08) made our disk ROM's INIT copy the drive count / slot there, and was
measured under MSX-DOS only. Under Disk BASIC main's slot scan then `inc`ed the same cell
(it doubles as main's DISKSLOT_OK): 3 where the CF-3300 holds 2, and facdemo3.di2's drive
loop ran on past the CF-3300's end (scratchpad/facusr_run8.out). This row reads both
bytes with PEEK at the prompt after a boot from the repo's blank data disk.

Compared: $FB21 exactly, and $FB22 as "the disk ROM's slot" -- PEEK(&HFB22) must equal
the slot the machine's own DSKIO answers from, which is not a value the two machines share,
so it is checked per side as nonzero. Black box: work-area RAM only.

    ZEROBAS_BASIC_MACHINE=... python3 -u probes/disk/disk_probe_drvinf.py
"""
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402

IMAGE = os.path.join(REPO, "disk", "test720.dsk")   # the build's blank data disk (make: $(DISK_TEST_DSK))
PROG = ["NEW", '10 PRINT "[D";PEEK(&HFB21);PEEK(&HFB22);"]"', "RUN"]


def main():
    got = {}
    for side, mach in (("REF", RT.REF_MACHINE), ("ZB", RT.OUR_MACHINE)):
        dsk = probe_tmp.tmp(f"drvinf_{side}.dsk")
        shutil.copyfile(IMAGE, dsk)
        raw = omsx_repl.run_cases(mach, [("direct", PROG)], batch=False, diska=dsk,
                                  reset=("", "SCREEN 0", "NEW"), boot=14.0, step=3.0,
                                  run_gap=6.0)[0] or ""
        t = " ".join(raw.split())
        i = t.rfind("[D")
        f = t[i + 2:t.find("]", i)].split() if i >= 0 else []
        got[side] = f if len(f) == 2 else None
        print(f"ROW {side:3} PEEK($FB21) PEEK($FB22) = {got[side]}", flush=True)
    if not got["REF"] or not got["ZB"]:
        print("INSTRUMENT FAULT: a side gave no reading")
        return 2
    ok = got["REF"][0] == got["ZB"][0] and got["REF"][1] != "0" and got["ZB"][1] != "0"
    print(f"{'PASS' if ok else 'FAIL'}: DRVINF under Disk BASIC "
          f"(count REF {got['REF'][0]} / ZB {got['ZB'][0]}, slot nonzero on both)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
