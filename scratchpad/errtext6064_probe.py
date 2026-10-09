#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Two questions the keyword-page rollout raised (2026-10-09):

  1. `ERROR 60`..`ERROR 64` on the DISKLESS target: the VG-8020 has no disk
     messages; does zerobas NODISK print the CF-3300's texts instead?
  2. `DSKI$(2,0)` (drive B: on a one-drive machine): Bad drive name, or the
     CF-3300's drive-swap prompt?

Clean-room: typed BASIC in, the text screen out.
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402


def rows(scr, start):
    if scr is None:
        return "<NO CAPTURE>"
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    if start in r:
        r = r[r.index(start) + 1:]
    return " | ".join(x for x in r if x and x not in ("Ok", "ZB"))


def main():
    bad = 0
    for code in range(60, 65):
        got = {}
        for side, m in (("VG-8020", "Philips_VG_8020"), ("zerobas", "C-BIOS_MSX1_EU_REPACK_NODISK")):
            scr = omsx_repl.run_cases(m, [("direct", ["NEW", f"10 ERROR {code}", "RUN"])], batch=False,
                                      reset=("", "SCREEN 0:WIDTH 40"), step=3.0)[0]
            got[side] = rows(scr, "RUN")
        same = got["VG-8020"] == got["zerobas"]
        bad += not same
        print(f"{'==' if same else '✗ '} ERROR {code}  VG-8020 [{got['VG-8020']}]  zerobas [{got['zerobas']}]", flush=True)
    got = {}
    for side, m in (("CF-3300", "National_CF-3300"), ("zerobas", "C-BIOS_MSX1_EU_REPACK_DISK")):
        dsk = probe_tmp.tmp(f"dski2_{m}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        line = 'A$=DSKI$(2,0):PRINT "[DONE]"'
        scr = omsx_repl.run_cases(m, [("direct", [line])], batch=False, diska=dsk, boot=14.0,
                                  reset=("", "SCREEN 0:WIDTH 40"), step=8.0)[0]
        got[side] = rows(scr, line)
    same = got["CF-3300"] == got["zerobas"]
    bad += not same
    print(f"{'==' if same else '✗ '} DSKI$(2,0)  CF-3300 [{got['CF-3300']}]  zerobas [{got['zerobas']}]", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
