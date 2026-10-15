#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DSKLOCAL knife: does dskio-acceptance SEE disk.rom's hk_dsk do the read?

K-DL1  disk/kernel.asm: hk_dsk's `call read_sector` -> 3 B of no-ops (byte-neutral):
       DSKI$ claims success and moves nothing. Predicted: `dir` and `boot` DIFF;
       `len`, `dsko`, `o1` ok.
Built through knife_guard (ROM must MOVE), restored, rebuilt CLEAN, re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "dsklocal_knife")
SRC = "disk/kernel.asm"
KNIVES = [
    ("K-DL1", "hkd_read:\n                call    read_sector\n",
     "hkd_read:\n                or      a\n                nop\n                nop\n", None, None),
]


def suite(tag, rows):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call(["make", "dskio-acceptance"], stdout=fh, stderr=subprocess.STDOUT,
                             timeout=3600)
    red = [ln.split()[1] for ln in open(log) if ln.strip().startswith("DIFF")]
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
            rc, red = suite(tag, rows)
            print(f"{tag}: rows {rows} diverging {red}", flush=True)
        finally:
            open(SRC, "w").write(text)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    rc, red = suite("restore", None)
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
