#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO slice 5 knife: does wszero-acceptance SEE the raised diskless ceiling?

K-WS6  basic/sysvars.inc: TXTMAX_NODISK back at $E98A, the cells left PACKED where
       slice 5 put them -- so the ONLY difference is where boot puts HIMEM, the
       string space and the stack. Predicted: `noclear` DIVERGES (the stack is back
       inside $E000-$E7FF), `ctl` stays SAME.
K-WS7  POOLSIZE back in the window at $EF9B (TXTCEIL left in CONLO): the pair is
       split again. Predicted: `q2` DIVERGES, `ctl` SAME.
Built through knife_guard (ROM must MOVE), restored, rebuilt CLEAN, re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s5_knife")
SRC = "basic/sysvars.inc"
KNIVES = [
    ("K-WS6", "TXTMAX_NODISK   equ     $EBCD", "TXTMAX_NODISK   equ     $E98A",
     ["ctl", "noclear"], ["noclear"]),
    ("K-WS7", "POOLSIZE        equ     $F66A", "POOLSIZE        equ     $EF9B",
     ["ctl", "q2"], ["q2"]),
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
    for tag, old, new, _r, _p in KNIVES:
        if text.count(old) != 1:
            print(f"{tag}: REFUSED, anchor count {text.count(old)}", flush=True)
            return 2
    for tag, old, new, rows, pred in KNIVES:
        before = knife_guard.hashes()
        try:
            open(SRC, "w").write(text.replace(old, new))
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
    rc, red = suite("restore", ["ctl", "q2", "noclear"])
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
