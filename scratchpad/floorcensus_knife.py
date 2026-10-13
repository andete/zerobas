#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FLOORCENSUS negative control: does floorcensus-acceptance NAME the D-FLOORREC writer?

K-FC1  sub/fatprim.asm: device channels take BOTH record copies again (load:
       record -> FSECTOR_BUF; save: FSECTOR_BUF -> record), i.e. the pre-fix code.
       Predicted: floorcensus FAILS naming tfl_rec (the load copy) and nothing else
       outside the program-RAM managers.
Built through knife_guard; restored on a CLEAN build and the suite re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "floorcensus_knife")
# 🔴 RUNS 1-2 CUT THE WRONG FILE: this runner was derived from listlptr_knife.py
# and the SRC/OLD/NEW substitution did not match, so both cut basic/detok.inc
# (the LIST fix) and read floorcensus green -- meaningless, NOT SCORED. The cut is
# written out here and the anchors are checked below.
SRC = "sub/fatprim.asm"
CUTS = [("                jr      c,tfl_dev           ; a device channel: no engine state, no record\n",
         "                jr      c,tfl_rec           ; KNIFE K-FC1 (load side)\n"),
        ("                jr      c,tfs_dout          ; D-FLOORREC: a device channel keeps no record here\n",
         "                jr      c,tfs_rec           ; KNIFE K-FC1 (save side)\n")]
OLD = None


def suite(tag):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call(["make", "floorcensus-acceptance"], stdout=fh,
                             stderr=subprocess.STDOUT, timeout=2400)
    red = [ln.split()[2] for ln in open(log) if ln.startswith("UNLISTED WRITER")]
    return rc, red


def main():
    os.makedirs(TMP, exist_ok=True)
    text = open(SRC).read()
    cut = text
    for o, n in CUTS:
        if cut.count(o) != 1:
            print(f"K-FC1: REFUSED, anchor count {cut.count(o)} for {o.strip()[:40]}")
            return 2
        cut = cut.replace(o, n)
    before = knife_guard.hashes()
    try:
        open(SRC, "w").write(cut)
        moved, _, brc = knife_guard.build(f"{TMP}/mk_K-FC1.log", before)
        if brc or not moved:
            print(f"K-FC1: build rc={brc} ROM moved={moved} -- NOT SCORED")
        else:
            rc, red = suite("K-FC1")
            print(f"K-FC1: floorcensus {'RED' if rc else 'green'}, diverging rows {red}; "
                  f"predicted tfl_rec only", flush=True)
    finally:
        open(SRC, "w").write(text)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    rc, red = suite("restore")
    print(f"restored: build rc={brc}; floorcensus {'RED -- RESTORE BROKEN ' + str(red) if rc else 'green'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
