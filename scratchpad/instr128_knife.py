#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-INSTR128 knife on `make instr128-acceptance`.

K-I2  sub/strheap.asm sis_next: the wrap guard (`jr z,sis_zero` after
      start++) dropped. Predicted: the 255-long no-match row never returns on
      zerobas (start wraps 255 -> 0 and the search restarts below the body),
      reads None, and the gate goes RED on `none255` only.
(The sign test's knife is the "before" run itself: scratchpad/
instr128_before.out, 7 rows red on the unfixed source.)
MEASURED: GREEN -- a MISS. Reproduced by hand on the cut build: INSTR of
"F", CHR$(0) and "#" in a 255-long string of "6"s all answer 0, in 2 ticks:
no hang. INFERENCE, not measured: the needle's temp snapshot sits just
below the haystack's body, so the wrapped start 0 compares body-1 -- the
needle with itself -- "matches" there, and a match at 0 prints 0, which is
also the right answer. The guard is kept (2 B of sub page 0): without it the
answer is right only by that layout. The gate cannot see it.
Built through knife_guard; restored on a CLEAN build and re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "instr128_knife")
SRC = os.path.join(REPO, "sub/strheap.asm")
OLD = "                jr      z,sis_zero          ; D-INSTR128: past 255 -- the last start\n"
NEW = "                                            ; D-INSTR128: past 255 -- the last start\n"


def gate(tag):
    log = f"{TMP}/gate_{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call(["python3", "-u", "probes/basic/basic_probe_instr128.py"], cwd=REPO,
                             stdout=fh, stderr=subprocess.STDOUT, timeout=2400)
    return rc, [l.split()[0] for l in open(log) if "DIVERGES" in l]


def main():
    os.makedirs(TMP, exist_ok=True)
    text = open(SRC).read()
    if text.count(OLD) != 1:
        sys.exit(f"REFUSED: anchor count {text.count(OLD)}")
    before = knife_guard.hashes()
    try:
        open(SRC, "w").write(text.replace(OLD, NEW))
        ok, _, brc = knife_guard.build(f"{TMP}/mk_k.log", before)
        if brc or not ok:
            print(f"K-I2: build rc={brc} reached-ROM={ok} -- NOT SCORED")
        else:
            rc, red = gate("k")
            hit = rc != 0 and red == ["none255"]
            print(f"K-I2 (wrap guard dropped): gate {'RED' if rc else 'GREEN'}, red {red}; "
                  f"predicted ['none255']: {'HIT' if hit else 'MISS'}")
    finally:
        open(SRC, "w").write(text)
    ok, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    rc, red = gate("restore")
    print(f"restored: build rc={brc}; gate {'GREEN' if not rc else 'RED -- RESTORE BROKEN ' + str(red)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
