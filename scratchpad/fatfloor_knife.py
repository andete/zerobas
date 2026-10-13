#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FATFLOOR knife: is a wrong diskless ceiling SEEN?

K-FF1  basic/sysvars.inc: TXTMAX_NODISK $E76A -> $E86A, i.e. 256 B past the
       DISK-ONLY buffers into live interpreter cells (the PAINT / DRAW block).
       On a diskless machine a program would then overwrite them.
       Predicted: `make ram-map-check` RED, naming untagged basic cells in
       [$E76A, $E86A); `make ceiling-acceptance` GREEN -- it reads its
       expectation from the same sym, so it agrees with ANY ceiling (that is
       why the static gate exists; FRE(0) is never gated as an absolute).
(Run 1 was NOT SCORED: its restore went red on a drifted docs/ram-map.md.)
Built through knife_guard; restored on a CLEAN build, both re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "fatfloor_knife")
SRC = "basic/sysvars.inc"
OLD = "TXTMAX_NODISK   equ     $E76A  ; NOT-A-CELL"
NEW = "TXTMAX_NODISK   equ     $E86A  ; NOT-A-CELL"


def gate(tag, target):
    log = f"{TMP}/{tag}_{target}.log"
    with open(log, "w") as fh:
        rc = subprocess.call(["make", target], cwd=REPO, stdout=fh,
                             stderr=subprocess.STDOUT, timeout=2400)
    floor = [l.strip() for l in open(log)
             if "DISKLESS FLOOR" in l or "untagged on the diskless floor" in l]
    return rc, floor


def main():
    os.makedirs(TMP, exist_ok=True)
    src = os.path.join(REPO, SRC)
    text = open(src).read()
    if text.count(OLD) != 1:
        print(f"K-FF1: REFUSED, anchor count {text.count(OLD)}")
        return 2
    before = knife_guard.hashes()
    try:
        open(src, "w").write(text.replace(OLD, NEW))
        moved, _, brc = knife_guard.build(f"{TMP}/mk_K-FF1.log", before)
        if brc or not moved:
            print(f"K-FF1: build rc={brc} ROM moved={moved} -- NOT SCORED")
        else:
            rc, floor = gate("K-FF1", "ram-map-check")
            print(f"K-FF1: ram-map-check {'RED' if rc else 'green'}; "
                  + (f"{len(floor)} line(s): " + " | ".join(x[:60] for x in floor[:6])
                     if floor else "no DISKLESS FLOOR line"), flush=True)
            rc2, _ = gate("K-FF1", "ceiling-acceptance")
            print(f"K-FF1: ceiling-acceptance {'RED' if rc2 else 'green'}", flush=True)
            print("K-FF1: predicted ram-map-check RED, ceiling-acceptance green")
    finally:
        open(src, "w").write(text)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    r1, _ = gate("restore", "ram-map-check")
    r2, _ = gate("restore", "ceiling-acceptance")
    print(f"restored: build rc={brc}; ram-map-check {'RED -- RESTORE BROKEN' if r1 else 'green'}; "
          f"ceiling-acceptance {'RED -- RESTORE BROKEN' if r2 else 'green'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
