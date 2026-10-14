#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO slice 6 knife: does wszero-acceptance SEE slice 6's ceiling raise?

K-WS8  basic/sysvars.inc: TXTMAX_NODISK back at $EBCD (slice 5's ceiling), the cells
       left where slice 6 put them -- boot's stack back at ~$E8E9. Predicted:
       `noclear2` ($E800-$E97F, no CLEAR) DIVERGES, `ctl` SAME.
Built through knife_guard (ROM must MOVE), restored, rebuilt CLEAN, re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s6_knife")
SRC = "basic/sysvars.inc"
KNIVES = [
    ("K-WS8", "TXTMAX_NODISK   equ     $ECF8", "TXTMAX_NODISK   equ     $EBCD",
     ["ctl", "noclear2"], ["noclear2"]),
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
    rc, red = suite("restore", ["ctl", "noclear2"])
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
