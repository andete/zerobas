#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-STRSCRBUF knife: does input-acceptance SEE the one-byte shift?

K-SB1  basic/input.asm: the console answer at LINEBUF+0 again (no shift) while
       STRSCR is LINEBUF -- the splitter's [len] byte lands on the first character.
       Predicted: input-acceptance RED on console INPUT rows.
Built through knife_guard; restored on a CLEAN build and the suite re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "strscrbuf_knife")
# 🔴 RUNS 1-2 CUT THE WRONG FILE: this runner was derived from listlptr_knife.py
# and the SRC/OLD/NEW substitution did not match, so both cut basic/detok.inc
# (the LIST fix) and read input green -- meaningless, NOT SCORED. The cut is
# written out here and the anchors are checked below.
SRC = "basic/input.asm"
CUTS = [("""                ld      hl,LINEBUF+255
                ld      de,LINEBUF+256
                ld      bc,256
                lddr                        ; -> LINEBUF+1 .. LINEBUF+256
                ld      hl,LINEBUF+1
""", """                ld      hl,LINEBUF          ; KNIFE K-SB1: the old layout, no shift
"""),
        ("                cp      low (LINEBUF+1)     ; D-STRSCRBUF: the line starts one byte up\n",
         "                cp      low LINEBUF         ; KNIFE K-SB1\n")]
OLD = None


def suite(tag):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call(["make", "input-acceptance"], stdout=fh,
                             stderr=subprocess.STDOUT, timeout=2400)
    red = [ln.strip()[:60] for ln in open(log) if "FAIL" in ln or "DIVERGES" in ln][:6]
    return rc, red


def main():
    os.makedirs(TMP, exist_ok=True)
    text = open(SRC).read()
    cut = text
    for o, n in CUTS:
        if cut.count(o) != 1:
            print(f"K-SB1: REFUSED, anchor count {cut.count(o)} for {o.strip()[:40]}")
            return 2
        cut = cut.replace(o, n)
    before = knife_guard.hashes()
    try:
        open(SRC, "w").write(cut)
        moved, _, brc = knife_guard.build(f"{TMP}/mk_K-SB1.log", before)
        if brc or not moved:
            print(f"K-SB1: build rc={brc} ROM moved={moved} -- NOT SCORED")
        else:
            rc, red = suite("K-SB1")
            print(f"K-SB1: input {'RED' if rc else 'green'}, diverging rows {red}; "
                  f"predicted console INPUT rows", flush=True)
    finally:
        open(SRC, "w").write(text)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    rc, red = suite("restore")
    print(f"restored: build rc={brc}; input {'RED -- RESTORE BROKEN ' + str(red) if rc else 'green'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
