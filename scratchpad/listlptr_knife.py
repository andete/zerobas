#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LISTLPTR knife: does listflt-acceptance's `lptr` row SEE the fix?

K-LP1  basic/detok.inc: `$0D` dispatched to dt_lineno again (the pointer printed
       as a number). Predicted: `lptr` DIVERGES, every float row stays SAME.
Built through knife_guard; restored on a CLEAN build and the suite re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "listlptr_knife")
SRC = "basic/detok.inc"
OLD = "                jp      z,dt_laddr\n"
NEW = "                jp      z,dt_lineno         ; KNIFE K-LP1\n"


def suite(tag):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call(["make", "listflt-acceptance"], stdout=fh,
                             stderr=subprocess.STDOUT, timeout=2400)
    red = [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]
    return rc, red


def main():
    os.makedirs(TMP, exist_ok=True)
    text = open(SRC).read()
    if text.count(OLD) != 1:
        print(f"K-LP1: REFUSED, anchor count {text.count(OLD)}")
        return 2
    before = knife_guard.hashes()
    try:
        open(SRC, "w").write(text.replace(OLD, NEW))
        moved, _, brc = knife_guard.build(f"{TMP}/mk_K-LP1.log", before)
        if brc or not moved:
            print(f"K-LP1: build rc={brc} ROM moved={moved} -- NOT SCORED")
        else:
            rc, red = suite("K-LP1")
            print(f"K-LP1: listflt {'RED' if rc else 'green'}, diverging rows {red}; "
                  f"predicted ['lptr'] only", flush=True)
    finally:
        open(SRC, "w").write(text)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    rc, red = suite("restore")
    print(f"restored: build rc={brc}; listflt {'RED -- RESTORE BROKEN ' + str(red) if rc else 'green'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
