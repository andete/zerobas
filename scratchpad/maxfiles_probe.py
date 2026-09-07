#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-MAXFRE — does the per-channel reservation move when MAXFILES moves?

D-RESERVE showed the reference reserves UP FRONT rather than at OPEN. Joost's
follow-up: does that reservation then track MAXFILES? D-HIMEMRES fitted
`R = 293 + 267*MAXFILES` across SEPARATE runs at MAXFILES 1 and 2, which is a fit
over two points from different boots. This asks one machine, in one program,
stepping MAXFILES up and reading FRE(0) after each step.

⚠️ MAXFILES CLEARS VARIABLES, so a reading cannot be held in a variable across
the next MAXFILES. Each FRE(0) is PRINTED immediately, before the next change,
and the fences are read in order.

    predicted, reference   step of -267 per extra channel
    predicted, zerobas     step of  -50 (FCH_CTXSZ)

A FLAT line on either machine would mean the reservation does NOT track
MAXFILES, and would refute the formula that has been quoted for both.
"""
from __future__ import annotations

import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_tmp                                                  # noqa: E402

FIXTURE = os.path.join(ROOT, "disk", "test720.dsk")
STEPS = [0, 1, 2, 3, 4]
SIDES = {
    "vg8020": ("Philips_VG_8020", 8.0, ("NEW",)),
    "cf3300": ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW")),
    "zb": (os.environ.get("ZEROBAS_BASIC_MACHINE",
                          "C-BIOS_MSX1_EU_REPACK_DISK"), 8.0, ("NEW",)),
}

PROG = ['10 ON ERROR GOTO 900']
for i, n in enumerate(STEPS):
    PROG += [f'{20+i*10} MAXFILES={n}', f'{25+i*10} PRINT"ZM";FRE(0);"MZ"']
PROG += ['800 END', '900 PRINT"ZM";-1;"MZ":RESUME NEXT']


def run(side):
    """🔴 NO DISK FOR THE VG-8020. It is DISKLESS, and mounting an image made
    openMSX refuse to boot at all ("No disk drive A present"). The harness said
    so plainly, but the probe then printed 0 in every cell -- which reads as a
    measurement of zero rather than as an apparatus failure
    [[an-unnamed-outcome-reads-as-no-outcome]]. MAXFILES needs no disk to
    reserve, so the row is real once the mount is dropped."""
    machine, boot, reset = SIDES[side]
    kw = {}
    if side != "vg8020":
        dsk = probe_tmp.tmp(f"maxfre_{side}.dsk")
        shutil.copyfile(FIXTURE, dsk)
        kw["diska"] = dsk
    raw = "".join(omsx_repl.run_cases(
        machine, [("direct", list(reset) + PROG + ["RUN"])], batch=False,
        reset=(), boot=boot, step=8.0, cap_gap=45.0, timeout=400.0,
        **kw)[0] or "")
    # EVERY fence here is also in the source (two PRINT lines carry it), so keep
    # only matches with no source punctuation, in order [[trapsvc-echo-fence]]
    vals = [int(g) for g in re.findall(r"ZM\s*(-?\d+)\s*MZ", raw)]
    return vals[-len(STEPS):] if len(vals) >= len(STEPS) else vals


def main() -> int:
    got = {s: run(s) for s in SIDES}
    print(f"\n{'MAXFILES':>8s} " + "".join(f"{s:>10s}" for s in SIDES))
    for i, n in enumerate(STEPS):
        row = "".join(
            (f"{got[s][i]:>10d}" if i < len(got[s]) else f"{'<none>':>10s}")
            for s in SIDES)
        print(f"{n:>8d} {row}")
    print(f"\n{'step':>8s} " + "".join(f"{s:>10s}" for s in SIDES))
    for i in range(1, len(STEPS)):
        row = ""
        for s in SIDES:
            v = got[s]
            row += (f"{v[i]-v[i-1]:>10d}" if i < len(v) else f"{'-':>10s}")
        print(f"{STEPS[i-1]}->{STEPS[i]:<5d} {row}")
    print("\n(-1 in a cell is a trapped error, not a size.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
