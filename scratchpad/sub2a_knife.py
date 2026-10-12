#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-SUB2 stage 2a knife: is the trampoline's restore of the LIVE secondary
register load-bearing for `make subrom-inttest`?

K-2A: after the ISR, the restored slot-3 secondary byte gets its page-0 field
forced to 3 (`or 3`) -- page 0 comes back as the EMPTY subslot 3-3 instead of
the interrupted tenant's 3-2, which is what the old boot-constant restore would
have done to a 3-3 tenant, mirrored. Predicted: subrom-inttest RED (the tenant
never returns to the stub; the 12 s safety net captures). Then the source is
restored, rebuilt and the gate re-run: predicted GREEN.

Uses knife_guard (a cut that did not reach the ROM must say so).
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import knife_guard                                 # noqa: E402

SRC = os.path.join(REPO, "basic/subromcall.asm")
OLD = "                ld      a,b\n                ld      ($FFFF),a\n"
NEW = "                ld      a,b\n                or      3\n                ld      ($FFFF),a\n"
TMP = os.path.join(tempfile.gettempdir(), "zerobas", "sub2a_knife")


def gate(tag):
    with open(f"{TMP}/inttest_{tag}.log", "w") as fh:
        rc = subprocess.call(["make", "subrom-inttest"], cwd=REPO, stdout=fh,
                             stderr=subprocess.STDOUT, timeout=600)
    tail = open(f"{TMP}/inttest_{tag}.log").read().strip().splitlines()[-4:]
    return rc, tail


def main():
    os.makedirs(TMP, exist_ok=True)
    text = open(SRC).read()
    if text.count(OLD) != 1:
        sys.exit(f"REFUSED: anchor count {text.count(OLD)}")
    before = knife_guard.hashes()
    try:
        open(SRC, "w").write(text.replace(OLD, NEW))
        ok, after, rc = knife_guard.build(f"{TMP}/mk_k2a.log", before)
        if rc or not ok:
            print(f"K-2A: build rc={rc} reached-ROM={ok} -- NOT SCORED")
            return 2
        rc, tail = gate("k2a")
        print(f"K-2A (restore page 0 to 3-3): subrom-inttest rc={rc}  "
              f"{'RED (predicted)' if rc else 'GREEN -- KNIFE MISSED'}")
        print("   " + "\n   ".join(tail))
    finally:
        open(SRC, "w").write(text)
    # clean: a restore built in the same second as the cut can be skipped by make
    # (sub2b_knife.py's first run read its restore RED for exactly that reason)
    ok, _, rc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(),
                                  clean=True)
    rc2, tail = gate("restore")
    print(f"restored: build rc={rc}; subrom-inttest rc={rc2}  "
          f"{'GREEN (predicted)' if not rc2 else 'RED -- RESTORE BROKEN'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
