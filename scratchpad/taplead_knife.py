#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TAPLEAD knife: does tapionlead-acceptance SEE the leader verify loop?

K-TL1  tape/tape.asm: the verify loop cut -- TAPION returns right after storing
       LOWLIM, as before D-TAPLEAD. Predicted: at least one of k190 / k200 / k204
       DIVERGES; `end` SAME; `mid` diverges (unpinned since 2026-10-15).
K-TL2  (2026-10-15) only the cycle verify's LOWER bound cut (`jr c` -> `jr $+2`,
       byte-neutral). Predicted: `mid` DIVERGES, the other four SAME.
Built through knife_guard (ROM must MOVE), restored, rebuilt CLEAN, re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "taplead_knife")
SRC = "tape/tape.asm"
KNIVES = [
    ("K-TL1", "                ld      c,CAS_VERIFY / 2\n", "                or      a\n                ret\n",   # byte-neutral: the loop goes dead
     ["mid", "k190", "k200", "k204", "end"], None),
    ("K-TL2", "                jr      c,tapion_relock ; cycle < 0.875 x avg: the lock averaged LONG halves\n",
     "                jr      $+2\n",                                              # byte-neutral: lower bound dead
     ["mid", "k190", "k200", "k204", "end"], None),
]


def suite(tag, rows):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call([sys.executable, "-u", "probes/basic/basic_probe_tapionlead.py", *rows],
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
            print(f"{tag}: rows {rows} diverging {red}", flush=True)
        finally:
            open(SRC, "w").write(text)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rc, red = suite("restore", ["mid", "k190", "k200", "k204", "end"])
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
