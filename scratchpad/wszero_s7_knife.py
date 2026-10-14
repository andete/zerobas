#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO slice 7 knife: does wszero-acceptance SEE FNSP's move out of the window?

K-WS9  basic/sysvars.inc: FNSP back at $EF07 (inside the window), FN_FST left in PRMLEN.
       Predicted: `abort` and `onerr` DIVERGE (an error after the load follows a
       garbage FN chain), `ctl` SAME.
K-WS10 DATAPTR back at $EF27. Predicted: `rich` DIVERGES (its READ after the load).
K-WS11 SUB_INT_RAM back at $F125 (the stub copied there again). Predicted: `rich`
       DIVERGES (an interrupt inside PAINT / CIRCLE runs the loaded bytes).
Built through knife_guard (ROM must MOVE), restored, rebuilt CLEAN, re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s7_knife")
SRC = "basic/sysvars.inc"
KNIVES = [
    ("K-WS9", "FNSP            equ     $F6E4", "FNSP            equ     $EF07",
     ["ctl", "abort", "onerr"], ["abort", "onerr"]),
    ("K-WS10", "DATAPTR         equ     $F6C8", "DATAPTR         equ     $EF27",
     ["ctl", "rich"], ["rich"]),
    ("K-WS11", "SUB_INT_RAM     equ     $F92D", "SUB_INT_RAM     equ     $F125",
     ["ctl", "rich"], ["rich"]),
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
    rc, red = suite("restore", ["ctl", "abort", "onerr", "rich"])
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
