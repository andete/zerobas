#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S8 knife: does wszero-acceptance's `persist` row SEE S8's moves?

K-WS12 basic/sysvars.inc: GFX_DSCALE / GFX_DANGLE back at $ED97 / $ED98 (inside the
       window). Predicted: `persist` DIVERGES (DRAW"S8A1" set before the load, the
       load writes $A5 over both, the DRAW after it draws something else), `ctl` SAME.
K-WS13 DISKSLOT / DISKSLOT_OK back at $EF54 / $EF55. Predicted: `persist` DIVERGES
       (OPEN"A:X" after the load sees a "disk ROM present" flag of $A5 and
       takes the disk arm instead of raising 56). First cut used FILES: MISS --
       FILES never reads the flag.
Built through knife_guard (ROM must MOVE), restored, rebuilt CLEAN, re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s8_knife")
SRC = "basic/sysvars.inc"
KNIVES = [
    ("K-WS12", [("GFX_DSCALE      equ     $FCBC", "GFX_DSCALE      equ     $ED97"),
                ("GFX_DANGLE      equ     $FCBD", "GFX_DANGLE      equ     $ED98")],
     ["ctl", "persist"], ["persist"]),
    ("K-WS13", [("DISKSLOT        equ     $FB22", "DISKSLOT        equ     $EF54"),
                ("DISKSLOT_OK     equ     $FB21", "DISKSLOT_OK     equ     $EF55")],
     ["ctl", "persist"], ["persist"]),
]


def suite(tag, rows):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call([sys.executable, "-u", "probes/basic/basic_probe_wszero.py", *rows],
                             stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    red = [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]
    return rc, red


def main():
    os.makedirs(TMP, exist_ok=True)
    text = open(SRC).read()
    for tag, pairs, _r, _p in KNIVES:
        for old, new in pairs:
            if text.count(old) != 1:
                print(f"{tag}: REFUSED, anchor count {text.count(old)} for {old!r}", flush=True)
                return 2
    for tag, pairs, rows, pred in KNIVES:
        before = knife_guard.hashes()
        try:
            cut = text
            for old, new in pairs:
                cut = cut.replace(old, new)
            open(SRC, "w").write(cut)
            moved, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            if brc or not moved:
                print(f"{tag}: build rc={brc} ROM moved={moved} -- NOT SCORED", flush=True)
                continue
            subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            rc, red = suite(tag, rows)
            print(f"{tag}: rows {rows} diverging {red}; predicted {pred} -> "
                  f"{'HIT' if sorted(red) == sorted(pred) else 'MISS'}", flush=True)
        finally:
            open(SRC, "w").write(text)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rc, red = suite("restore", ["ctl", "persist"])
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
