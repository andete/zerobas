#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BLOADRTAIL knife: does bloadrtail-acceptance SEE the call-and-return?

K-BT1  basic/bload.asm load_handoff: `call nz,lh_jphl` -> `jp nz,lh_jphl` (the
       old jump, same size): the program's `ret` goes back past the statement.
       Predicted: all five rows (ret clob prog ran chain) DIVERGE.
Built through knife_guard (ROM must MOVE), restored, rebuilt CLEAN, re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "bloadrtail_knife")
CUTS = [
    ("K-BT1", "basic/bload.asm",
     "                call    nz,lh_jphl          ; ,R: run it; it RETURNS here\n",
     "                jp      nz,lh_jphl          ; KNIFE K-BT1: the old jump\n",
     ["ret", "clob", "prog", "ran", "chain"]),
]


def suite(tag):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call(["make", "bloadrtail-acceptance"], stdout=fh,
                             stderr=subprocess.STDOUT, timeout=3600)
    red = [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]
    return rc, red


def main():
    os.makedirs(TMP, exist_ok=True)
    for tag, src, old, new, pred in CUTS:
        text = open(src).read()
        if text.count(old) != 1:
            print(f"{tag}: REFUSED, anchor count {text.count(old)} in {src}", flush=True)
            return 2
    only = sys.argv[1:]
    for tag, src, old, new, pred in CUTS:
        if only and tag not in only:
            continue
        text = open(src).read()
        before = knife_guard.hashes()
        try:
            open(src, "w").write(text.replace(old, new))
            moved, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            if brc or not moved:
                print(f"{tag}: build rc={brc} ROM moved={moved} -- NOT SCORED", flush=True)
                continue
            rc, red = suite(tag)
            score = "HIT" if sorted(red) == sorted(pred) else "MISS"
            print(f"{tag}: bloadrtail {'RED' if rc else 'green'}, diverging {red}; "
                  f"predicted {pred} -> {score}", flush=True)
        finally:
            open(src, "w").write(text)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    rc, red = suite("restore")
    print(f"restored: build rc={brc}; bloadrtail {'RED -- RESTORE BROKEN ' + str(red) if rc else 'green'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
