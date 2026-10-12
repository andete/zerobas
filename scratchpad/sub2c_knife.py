#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-SUB2 stage (c) knife on `make sub2-acceptance`: is the discovery store
the reason main reaches ROM 2?

K-2C   try_sub_slot's "Z2" branch loads the slot but never stores it
       (`ld (SUBSLOT2),a` -> `nop` x3). Predicted: SUBSLOT2 reads $00, main's
       subrom2_call returns "absent" without calling (its row $00) -- RED on
       both machines -- while the six direct-CALSLT rows stay green.
Built through knife_guard; restored with a CLEAN build and re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import knife_guard                                 # noqa: E402

SRC = os.path.join(REPO, "basic/subrom-boot.asm")
OLD = "                ld      (SUBSLOT2),a        ; a slot id is never 0, so 0 stays \"absent\"\n"
NEW = "                nop\n                nop\n                nop\n"
TMP = os.path.join(tempfile.gettempdir(), "zerobas", "sub2c_knife")


def probe(tag):
    log = f"{TMP}/probe_{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call(["python3", "-u", "probes/basic/basic_probe_sub2_ping.py"],
                             cwd=REPO, stdout=fh, stderr=subprocess.STDOUT, timeout=600)
    return rc, [l.rstrip() for l in open(log) if "FAIL" in l]


def main():
    os.makedirs(TMP, exist_ok=True)
    text = open(SRC).read()
    if text.count(OLD) != 1:
        sys.exit(f"REFUSED: anchor count {text.count(OLD)}")
    before = knife_guard.hashes()
    try:
        open(SRC, "w").write(text.replace(OLD, NEW))
        ok, _, brc = knife_guard.build(f"{TMP}/mk_k2c.log", before)
        if brc or not ok:
            print(f"K-2C: build rc={brc} reached-ROM={ok} -- NOT SCORED")
        else:
            rc, fails = probe("k2c")
            print(f"K-2C (SUBSLOT2 never stored): gate {'RED' if rc else 'GREEN'} "
                  f"(predicted RED: {'HIT' if rc else 'MISS'})")
            for f in fails:
                print("   " + f)
    finally:
        open(SRC, "w").write(text)
    ok, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(),
                                   clean=True)
    rc, _ = probe("restore")
    print(f"restored: build rc={brc}; gate {'GREEN' if not rc else 'RED -- RESTORE BROKEN'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
