#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO slice 2 knife: does wszero-acceptance SEE the trap block's move?

K-WS3  basic/sysvars.inc: ZTRAP / ZINTVAL / ZINTCNT / TRAPENA / TRAPSVC / TRAPPEND /
       STOPHOLD all back at their old addresses ($EDD1 .. $EE1F, $F027).
       Predicted: `trap` DIVERGES (a load over $EDD1-$EE1F arms garbage traps).
Built through knife_guard (ROM must MOVE), restored, rebuilt CLEAN, re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s2_knife")
CUTS = [
    ("K-WS3a", "basic/sysvars.inc", "ZTRAP           equ     $FC4C", "ZTRAP           equ     $EDD1", None),
    ("K-WS3b", "basic/sysvars.inc", "ZINTVAL         equ     $FC82", "ZINTVAL         equ     $EE07", None),
    ("K-WS3c", "basic/sysvars.inc", "ZINTCNT         equ     $FC84", "ZINTCNT         equ     $EE09", None),
    ("K-WS3d", "basic/sysvars.inc", "TRAPENA         equ     $FC86", "TRAPENA         equ     $EE0B", None),
    ("K-WS3e", "basic/sysvars.inc", "TRAPPEND        equ     $FC88", "TRAPPEND        equ     $EE1F", None),
    ("K-WS3f", "basic/sysvars.inc", "TRAPSVC         equ     $FC87", "TRAPSVC         equ     $EE0C", None),
    ("K-WS3g", "basic/sysvars.inc", "STOPHOLD        equ     $FC89", "STOPHOLD        equ     $F027", None),
]
GROUPS = [("K-WS3", ["K-WS3a", "K-WS3b", "K-WS3c", "K-WS3d", "K-WS3e", "K-WS3f", "K-WS3g"], ["trap"], ["trap"])]


def suite(tag, rows):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call([sys.executable, "-u", "probes/basic/basic_probe_wszero.py", *rows],
                             stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    red = [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]
    return rc, red


def main():
    os.makedirs(TMP, exist_ok=True)
    by = {c[0]: c for c in CUTS}
    for _t, src, old, new, _p in CUTS:
        if open(src).read().count(old) != 1:
            print(f"{_t}: REFUSED, anchor count {open(src).read().count(old)}", flush=True)
            return 2
    for tag, members, pred, rows in GROUPS:
        src = by[members[0]][1]
        text = open(src).read()
        cut = text
        for m in members:
            cut = cut.replace(by[m][2], by[m][3])
        before = knife_guard.hashes()
        try:
            open(src, "w").write(cut)
            moved, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            if brc or not moved:
                print(f"{tag}: build rc={brc} ROM moved={moved} -- NOT SCORED", flush=True)
                continue
            subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            rc, red = suite(tag, rows)
            print(f"{tag}: rows {rows} diverging {red}; predicted {pred} -> "
                  f"{'HIT' if sorted(red) == sorted(pred) else 'MISS'}", flush=True)
        finally:
            open(src, "w").write(text)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rc, red = suite("restore", ["trap"])
    print(f"restored: build rc={brc}; trap {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
