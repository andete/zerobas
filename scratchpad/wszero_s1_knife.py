#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO slice 1 knife: does wszero-acceptance SEE the moves?

K-WS1  basic/sysvars.inc: CURPTR / ENDPTR / EXECPTR back at $EC20 / $EC22 / $EC24.
       Predicted: `bl` DIVERGES (the load rewrites its own loop cells).
K-WS2  basic/sysvars.inc: CAS_WANT back at $F00A (the names' first cell).
       Predicted: `cas` stays SAME -- the search fills those cells BEFORE the
       data block and refills them for the next file, so this row is expected to
       be BLIND to the move (an honest negative, recorded as such).
Built through knife_guard (ROM must MOVE), restored, rebuilt CLEAN, re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s1_knife")
CUTS = [
    ("K-WS1", "basic/sysvars.inc",
     "CURPTR          equ     $F7BC",
     "CURPTR          equ     $EC20 ; KNIFE K-WS1",
     ["bl"]),
    ("K-WS1b", "basic/sysvars.inc",
     "ENDPTR          equ     $F7BE",
     "ENDPTR          equ     $EC22 ; KNIFE K-WS1",
     None),
    ("K-WS1c", "basic/sysvars.inc",
     "EXECPTR         equ     $F7C0",
     "EXECPTR         equ     $EC24 ; KNIFE K-WS1",
     None),
    ("K-WS2", "basic/sysvars.inc",
     "CAS_WANT        equ     $F866",
     "CAS_WANT        equ     $F00A ; KNIFE K-WS2",
     []),
]
GROUPS = [("K-WS1", ["K-WS1", "K-WS1b", "K-WS1c"], ["bl"], ["bl"]),
          ("K-WS2", ["K-WS2"], [], ["cas"])]


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
    rc, red = suite("restore", ["bl", "cas"])
    print(f"restored: build rc={brc}; bl/cas {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
