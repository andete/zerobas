#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FILESNL: where does the cursor stand after FILES? Found by the DSKO$
keyword page's example (2026-10-09): a PRINT after FILES started on a new row
on the CF-3300 and continued the last listing row on zerobas.

  full  6 files (two full rows of three at WIDTH 40), then PRINT "X"
  part  7 files (a last row of one), then PRINT "X"
  w37   6 files at WIDTH 37, then PRINT "X"

Clean-room: typed BASIC in, the text screen out. CF-3300 vs zerobas DISK, each
on a private copy of disk/test720.dsk (6 files).
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

CASES = {
    "full": ("SCREEN 0:WIDTH 40", ['10 FILES:PRINT "X"', "RUN"]),
    "part": ("SCREEN 0:WIDTH 40", ['10 COPY "HI.TXT" TO "H2.TXT"', '20 FILES:PRINT "X"', "RUN"]),
    "w37": ("SCREEN 0:WIDTH 37", ['10 FILES:PRINT "X"', "RUN"]),
}


def rows(scr):
    if scr is None:
        return "<NO CAPTURE>"
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    if "RUN" in r:
        r = r[r.index("RUN") + 1:]
    return " | ".join(x for x in r if x and x not in ("Ok", "ZB"))


def main():
    bad = 0
    for name, (reset, lines) in CASES.items():
        got = {}
        for side, m in (("CF-3300", "National_CF-3300"), ("zerobas", "C-BIOS_MSX1_EU_REPACK_DISK")):
            dsk = probe_tmp.tmp(f"filesnl_{name}_{m}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            scr = omsx_repl.run_cases(m, [("direct", lines)], batch=False, diska=dsk, boot=14.0,
                                      reset=("", reset), step=4.5, run_gap=20.0)[0]
            got[side] = rows(scr)
        same = got["CF-3300"] == got["zerobas"]
        bad += not same
        print(f"{'==' if same else '✗ '} {name:4s}\n   CF-3300 [{got['CF-3300']}]\n   zerobas [{got['zerobas']}]", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
