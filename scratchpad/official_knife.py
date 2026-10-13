#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-OFFICIAL knives on `make officialcell-acceptance`.

K-O1  TRACEFLAG back at its private $ED26: predicted trcflg RED only (its
      control reads 0 either way).
K-O2  MAXF back at its private $EB11: predicted maxfil AND maxfil-ctl RED
      (MAXFIL then reads 0 even at boot).
Built through knife_guard; restored on a CLEAN build and re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "official_knife")
CUTS = [
    ("K-O1", "basic/sysvars.inc",
     "TRACEFLAG       equ     $F7C4   ;", "TRACEFLAG       equ     $ED26   ; KNIFE K-O1", {"trcflg"}),
    ("K-O2", "basic/sysvars.inc",
     "MAXF            equ     $F85F   ;", "MAXF            equ     $EB11   ; KNIFE K-O2", {"maxfil", "maxfil-ctl"}),
]


def gate(tag):
    log = f"{TMP}/gate_{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call(["make", "officialcell-acceptance"], cwd=REPO, stdout=fh,
                             stderr=subprocess.STDOUT, timeout=1800)
    red = {l.split()[0] for l in open(log) if " DIVERGES " in l}
    return rc, red


def main():
    os.makedirs(TMP, exist_ok=True)
    for tag, path, old, new, want in CUTS:
        src = os.path.join(REPO, path)
        text = open(src).read()
        if text.count(old) != 1:
            print(f"{tag}: REFUSED, anchor count {text.count(old)}")
            continue
        before = knife_guard.hashes()
        try:
            open(src, "w").write(text.replace(old, new))
            ok, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            if brc or not ok:
                print(f"{tag}: build rc={brc} reached-ROM={ok} -- NOT SCORED")
                continue
            rc, red = gate(tag)
            print(f"{tag}: gate {'RED' if rc else 'GREEN'}, red {sorted(red)}; predicted "
                  f"{sorted(want)}: {'HIT' if rc and red == want else 'MISS'}", flush=True)
        finally:
            open(src, "w").write(text)
    ok, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    rc, red = gate("restore")
    print(f"restored: build rc={brc}; gate {'GREEN' if not rc else 'RED -- RESTORE BROKEN'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
