#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DATARESET knife on `make readerl-acceptance`.

K-D1  basic/readdata-body.inc rov_none: the rewind store (`ld (DATASTATE),a`)
      cut -- `Out of DATA` leaves zerobas exhausted again. Predicted: exactly
      oodrewind, oodcount and oodrestore RED; the seven older rows green.
Built through knife_guard; restored on a CLEAN build and re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "datareset_knife")
PATH = "basic/readdata-body.inc"
OLD = "                ld      (DATASTATE),a\n                ret\n\n; --- rov_str"
NEW = "                ret                         ; KNIFE K-D1\n\n; --- rov_str"
WANT = {"oodrewind", "oodcount", "oodrestore"}


def gate(tag):
    log = f"{TMP}/gate_{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call(["make", "readerl-acceptance"], cwd=REPO, stdout=fh,
                             stderr=subprocess.STDOUT, timeout=2400)
    return rc, {l.split()[1] for l in open(log) if l.startswith("ROW") and l.rstrip().endswith("DIVERGES")}


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
        ok, _, brc = knife_guard.build(f"{TMP}/mk_K-D1.log", before)
        if brc or not ok:
            print(f"K-D1: build rc={brc} reached-ROM={ok} -- NOT SCORED")
        else:
            rc, red = gate("K-D1")
            print(f"K-D1: gate {'RED' if rc else 'GREEN'}, red {sorted(red)}; predicted "
                  f"{sorted(WANT)}: {'HIT' if rc and red == WANT else 'MISS'}")
    finally:
        open(src, "w").write(text)
    ok, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    rc, red = gate("restore")
    print(f"restored: build rc={brc}; gate {'GREEN' if not rc else 'RED -- RESTORE BROKEN'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
