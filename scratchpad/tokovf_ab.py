#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TOKOVF A/B: did the crunch bound turn fdcdi-acceptance (d8) and
geteject-acceptance (put) red? Both are disk probes with timed events, and both
were green in the D-BASICROM full battery 1.5 h earlier.

  A  the bound CUT (K-T1's edit: its `jp c,tk_end` -> three nops, so the test
     still RUNS and costs the same cycles but decides nothing), BEEP still in sub2
  B  the bound live (the tree as staged), clean rebuild
Each arm runs both probes.

Prediction: the cut arm keeps the same cycle cost, so if the reds are the bound's
TIMING they stay red in A too; if they are its DECISION they go green in A. My
bet: red in both arms (timing or the BEEP move, not the decision).
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "tokovf_ab")
PATH = "basic/tokenise.inc"
OLD = "                pop     hl\n                jp      c,tk_end\n                ld      a,(TKNAME)\n"
NEW = ("                pop     hl\n                nop                         ; A/B CUT\n"
       "                nop\n                nop\n                ld      a,(TKNAME)\n")
PROBES = ("probes/disk/disk_probe_fdcdi.py", "probes/disk/disk_probe_geteject.py")


def probes(tag):
    for p in PROBES:
        log = f"{TMP}/{tag}_{os.path.basename(p)}.log"
        with open(log, "w") as fh:
            rc = subprocess.call(["python3", "-u", p], cwd=REPO, stdout=fh,
                                 stderr=subprocess.STDOUT, timeout=1800)
        rows = [l.strip() for l in open(log) if l.startswith("ROW") or l.startswith("FAIL")]
        print(f"{tag} {os.path.basename(p)} rc={rc}")
        for r in rows:
            print("   " + r)


def main():
    os.makedirs(TMP, exist_ok=True)
    src = os.path.join(REPO, PATH)
    text = open(src).read()
    if text.count(OLD) != 1:
        print(f"REFUSED: anchor count {text.count(OLD)}")
        return 2
    before = knife_guard.hashes()
    try:
        open(src, "w").write(text.replace(OLD, NEW))
        ok, _, brc = knife_guard.build(f"{TMP}/mk_A.log", before)
        if brc or not ok:
            print(f"A: build rc={brc} reached-ROM={ok} -- NOT SCORED")
        else:
            probes("A-cut")
    finally:
        open(src, "w").write(text)
    ok, _, brc = knife_guard.build(f"{TMP}/mk_B.log", knife_guard.hashes(), clean=True)
    print(f"B: clean build rc={brc}")
    probes("B-live")
    return 0


if __name__ == "__main__":
    sys.exit(main())
