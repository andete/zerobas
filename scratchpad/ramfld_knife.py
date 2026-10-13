#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RAMFLD knife on `make ceiling-acceptance` -- the knife D-RAMCEIL owed.

K-C1  basic/interp.asm: the boot's `jr nc,bh_store` cut to two `nop`s, so a
      diskless boot falls through to `ld hl,TXTMAX` -- the disk build's ceiling.
      Predicted: nodisk RED (TXTCEIL = TXTMAX), disk green.
Built through knife_guard; restored on a CLEAN build and re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "ramfld_knife")
PATH = "basic/interp.asm"
OLD = "                jr      nc,bh_store         ; HIMEM not lowered: the diskless ceiling\n"
NEW = "                nop                         ; KNIFE K-C1\n                nop\n"


def gate(tag):
    log = f"{TMP}/gate_{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call(["make", "ceiling-acceptance"], cwd=REPO, stdout=fh,
                             stderr=subprocess.STDOUT, timeout=1800)
    rows = [l.strip() for l in open(log) if l.startswith(("nodisk", "disk "))]
    return rc, rows


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
        ok, _, brc = knife_guard.build(f"{TMP}/mk_K-C1.log", before)
        if brc or not ok:
            print(f"K-C1: build rc={brc} reached-ROM={ok} -- NOT SCORED")
        else:
            rc, rows = gate("K-C1")
            red = [r.split()[0] for r in rows if " FAIL " in r]
            print(f"K-C1: gate {'RED' if rc else 'GREEN'}, red {red}; predicted ['nodisk']: "
                  f"{'HIT' if red == ['nodisk'] else 'MISS'}")
            for r in rows:
                print("   " + r)
    finally:
        open(src, "w").write(text)
    ok, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    rc, rows = gate("restore")
    print(f"restored: build rc={brc}; gate {'GREEN' if not rc else 'RED -- RESTORE BROKEN'}")
    for r in rows:
        print("   " + r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
