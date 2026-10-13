#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DSCALEDISK knife: does diskalias-acceptance SEE the overlap?

K-DD1  disk/equates.inc: FAT_NUMFATS put back ON GFX_DSCALE's address (read from
       the sym), the
       overlap step 2b removed (from the disk side: a basic-side cut would trip
       sysvars.inc's own asserts and never build).
       Predicted: `scale` DIVERGES; `scale0` (no disk access) and `hook` SAME.
Built through knife_guard; restored on a CLEAN build, the suite re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "diskalias_knife")
SRC = "disk/equates.inc"
OLD = "FAT_NUMFATS     equ     $E824   ;"
# READ, never copied: run 1 hard-coded $E9A1 from a listing taken BEFORE the
# DB_WIN swap moved GFX_DSCALE to $E941 -- it cut a different cell, read green,
# and is NOT SCORED.
import re as _re
_DS = next(int(m.group(1), 16) for m in (_re.match(r"GFX_DSCALE\s+EQU\s+0?([0-9A-F]+)H", l)
                                          for l in open("build/basic-reloc.sym")) if m)
NEW = f"FAT_NUMFATS     equ     ${_DS:04X}   ; KNIFE K-DD1 (on GFX_DSCALE)"


def suite(tag):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call(["make", "diskalias-acceptance"], stdout=fh,
                             stderr=subprocess.STDOUT, timeout=2400)
    red = [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]
    return rc, red


def main():
    os.makedirs(TMP, exist_ok=True)
    text = open(SRC).read()
    if text.count(OLD) != 1:
        print(f"K-DD1: REFUSED, anchor count {text.count(OLD)}")
        return 2
    before = knife_guard.hashes()
    try:
        open(SRC, "w").write(text.replace(OLD, NEW))
        moved, _, brc = knife_guard.build(f"{TMP}/mk_K-DD1.log", before)
        if brc or not moved:
            print(f"K-DD1: build rc={brc} ROM moved={moved} -- NOT SCORED")
        else:
            rc, red = suite("K-DD1")
            print(f"K-DD1: diskalias {'RED' if rc else 'green'}, diverging {red}; "
                  "predicted ['scale'] only", flush=True)
    finally:
        open(SRC, "w").write(text)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    rc, red = suite("restore")
    print(f"restored: build rc={brc}; diskalias {'RED -- RESTORE BROKEN ' + str(red) if rc else 'green'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
