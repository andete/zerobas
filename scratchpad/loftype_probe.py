#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-LOFTYPE — is the reference's LOF single or double precision?

A copy of scratchpad/putdomain_probe.py with ONE change: line 300 prints
LOF(1)/7 instead of LOF(1). 76800/7 = 10971.428571428571...; a SINGLE prints
7 significant digits (10971.43), a DOUBLE prints 14 (10971.428571429). That
decides which pack ev_ff_lof's u32->float path uses (arga_pack_single vs
arga_pack_fac) -- measured on the CF-3300, the only side with a drive AND a
correct LOF. Nothing else in the copy is touched, so its fixture, timing and
readout are exactly the ones that measured the -256.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_sides                                                # noqa: E402

probe_sides.require_disk("cf3300", "zb")
SIDES = probe_sides.sides("cf3300", "zb")
FIXTURE = os.path.join(ROOT, "disk", "test720.dsk")

# (tag, LEN= clause, record number, expected offset, note, run_gap)
# \U0001f534 THE GAP IS PER-ROW, AND IT HAD TO BECOME SO. A row this tree
# REFUSES answers in milliseconds; a row it PERFORMS has to extend the file one
# sector at a time, and `r.255` -- 255 records of 256 bytes, the last one inside
# today's cap -- is the only zerobas row that does the long version. At a flat
# 45 s it read `<none>`, which is indistinguishable from a hang and made the
# probe refuse the whole table. A timing parameter that is uniform across rows
# doing wildly different amounts of work is an apparatus defect, not a setting
# [[apparatus-is-part-of-the-measurement]].
CASES = [
    ("r.ctl",    "",        "1",     0,     "CONTROL: default reclen 256 -> LOF 256", 45.0),
    ("r.255",    "",        "255",   65024, "the last record inside today's cap", 240.0),
    ("r.256",    "",        "256",   65280, "past the cap; offset STILL fits 16 bits", 45.0),
    ("r.257",    "",        "257",   65536, "\U0001f3af the 16-bit offset BOUNDARY", 45.0),
    ("r.300",    "",        "300",   76544, "well past the boundary", 45.0),
    ("l1.ctl",   " LEN=1",  "1",     0,     "CONTROL: reclen 1 -> LOF 1", 45.0),
    ("l1.256",   " LEN=1",  "256",   255,   "past the cap, offset only 255", 45.0),
    ("l1.32767", " LEN=1",  "32767", 32766, "the largest MSX integer", 45.0),
    ("l1.32768", " LEN=1",  "32768", 32767, "past the SIGNED range -- a different rule", 45.0),
    ("l1.65535", " LEN=1",  "65535", 65534, "offset fits 16 bits; the number does not", 45.0),
]


# --- D-FACEPIN: the FACE, not just the row label ----------------------------
# 🔴 A FILED FACE ROTS WITHOUT THE ROW CEASING TO DIVERGE. `filed_row_sweep`
# calls a row that still diverges -- but to a DIFFERENT face -- `known`, and it
# reads green. Same shape as `basic_probe_nodisk.PINNED`: pin the VALUES, RED on
# drift in EITHER direction. ⚠️ Keyed by SIDE NAME, never by column position.
# 🎯 THE FACE HERE IS `E L` -- the trapped ERR and LOF TOGETHER -- because the
# whole point of this probe is that ERR alone cannot separate "did it" from
# "declined quietly". Pinning only the ERR would pin the blind half.
# ⚠️ `r.255`'s zb face is **0 -256**, and that is the FINDING, not a typo: 65280
# read back through a signed 16-bit LOF. If it ever becomes 65280 the defect is
# fixed, and this pin going RED is how somebody finds out.
PINNED = {
    # measured 2026-09-10, RE-MEASURED at pin time rather than carried from the
    # run that filed the entry. CONTROLS r.ctl / l1.ctl are deliberately NOT
    # pinned: they are the fixture check, and the probe already refuses the whole
    # table when either fails.
    "r.255":     {"cf3300": "0 65280", "zb": "0 -256"},
    "r.256":     {"cf3300": "0 65536", "zb": "0 256"},
    "r.257":     {"cf3300": "0 65792", "zb": "0 256"},
    "r.300":     {"cf3300": "0 76800", "zb": "0 256"},
    "l1.256":    {"cf3300": "0 256",   "zb": "0 1"},
    "l1.32767":  {"cf3300": "0 32767", "zb": "0 1"},
    "l1.32768":  {"cf3300": "0 32768", "zb": "0 1"},
    "l1.65535":  {"cf3300": "0 65535", "zb": "0 1"},
}


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="putdomain-")
    out = {}
    for tag, lenc, rec, off, note, gap in CASES:
        row = {}
        for side, c in SIDES.items():
            img = os.path.join(tmp, f"{tag}-{side}.dsk")
            shutil.copyfile(FIXTURE, img)
            p = ["10 ON ERROR GOTO 900", f'20 OPEN "A:Q.DAT" AS #1{lenc}',
                 "30 FIELD #1,1 AS A$", '40 LSET A$ = "H"', "50 PUT #1,1",
                 "60 E = 0",
                 f"70 PUT #1,{rec}",
                 "80 GOTO 300",
                 "900 E = ERR : RESUME 300",
                 # LOF BEFORE CLOSE -- asking a closed channel is a different
                 # question, and D-PUTEXTEND already paid for that lesson.
                 '300 L = LOF(1)/7 : CLOSE #1 : PRINT "ZQ";E;L;"QZ" : END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=gap,
                cap_gap=4.0, timeout=gap + 420.0, diska=img)[0] or "")
            v = [g for g in re.findall(r'ZQ\s*([-0-9 .E+]+?)\s*QZ', raw)
                 if '"' not in g and ';' not in g]
            row[side] = " ".join(v[-1].split()) if v else None
        out[tag] = row
        f = {s: (row[s] if row[s] else "<none>") for s in SIDES}
        mark = "" if f["cf3300"] == f["zb"] else "   \U0001f534 DIFF"
        print(f"  {tag:9s} PUT#1,{rec:6s}{lenc:8s} off={off:6d}  "
              f"cf=[E L]={f['cf3300']:14s} zb=[E L]={f['zb']:14s}{mark}\n"
              f"            {note}", flush=True)

    if any(v is None for r in out.values() for v in r.values()):
        print("\n  \U0001f534 A ROW HAS NO READING -- nothing is concluded.")
        return 2

    def lof(tag, side):
        try:
            return float(out[tag][side].split()[1])
        except (ValueError, IndexError):
            return None

    # Two controls, and they check DIFFERENT things: the default record length
    # (which caught the D-PUTEXTEND author expecting 10) and the LEN= clause
    # actually taking effect. A run where LEN=1 silently did nothing would make
    # every `l1.` row a duplicate of an `r.` row at reclen 256.
    bad = []
    if lof("r.ctl", "cf3300") != 256 or lof("r.ctl", "zb") != 256:
        bad.append(f"r.ctl LOF is not 256 (cf={lof('r.ctl','cf3300')}, "
                   f"zb={lof('r.ctl','zb')}) -- the default reclen moved")
    if lof("l1.ctl", "cf3300") != 1 or lof("l1.ctl", "zb") != 1:
        bad.append(f"l1.ctl LOF is not 1 (cf={lof('l1.ctl','cf3300')}, "
                   f"zb={lof('l1.ctl','zb')}) -- LEN=1 did not take, so every "
                   f"l1. row is secretly a reclen-256 row")
    if bad:
        print("\n  \U0001f534 CONTROL FAILED -- no row below is readable:")
        for b in bad:
            print(f"     {b}")
        return 2

    drift = []
    for lbl, want in PINNED.items():
        for side, face in want.items():
            if lbl not in out or side not in out[lbl]:
                continue                  # row or side not run; not a drift
            got = str(out[lbl][side])
            if got != face:
                drift.append(f"{lbl}[{side}]: pinned {face!r}, measured {got!r}")
    if drift:
        print("\n\U0001f534 PINNED FACE DRIFT -- the row may still diverge, but "
              "NOT to the face this tree has filed:")
        for d in drift:
            print(f"     {d}")
        print("  Re-read the owning entry: either the behaviour moved, or the "
              "filing was wrong when it was written.")
        return 2

    dis = [t for t, *_ in CASES if out[t]["cf3300"] != out[t]["zb"]]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    print("  reference LOF by row: " + ", ".join(
        f"{t}={lof(t,'cf3300')}" for t, *_ in CASES))
    print("\n\U0001f3af READ `r.257` FIRST. If the reference grew the file past "
          "65536 there, its record offsets are wider than 16 bits and lifting "
          "this tree's cap to the 16-bit limit would be a NEW divergence at a "
          "new place, not a fix. If it declined, the 16-bit offset IS the "
          "contract and the cap can move to exactly that line.")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
