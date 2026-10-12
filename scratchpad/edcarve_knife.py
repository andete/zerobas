#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EDCARVE knife on `make screditor-acceptance`: is the moved tenant what
makes the CTRL editing keys work?

K-E1  sub2/edctrl.asm edctrl_tenant answers "not ours" WITHOUT calling
      ek_ctrl. Predicted: e.ctrle, e.ctrlu, e.ctrlb, e.ctrlf DIVERGE (the keys
      reach the readline tenant, which does not edit with them); every other
      row stays ok.
      FIRST CUT (a MISS, the knife's fault): it only forced the VERDICT to "not
      ours" after ek_ctrl had already made the edit -- the key then went on to
      the readline tenant, which ignores these codes, and every row read right.
      It showed the "handled" flag is not load-bearing for these five keys;
      the edit is.
(The `cp 22` filter in rl_get only spares printable keys the crossing: no
behaviour depends on it, so no knife can see it -- stated, not tested.)
Built through knife_guard; restored on a CLEAN build and re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "edcarve_knife")
SRC = os.path.join(REPO, "sub2/edctrl.asm")
OLD = ("                call    ek_ctrl\n                ld      a,0\n"
       "                ret     z                   ; handled\n")
NEW = "                ld      a,1\n                ret                         ; KNIFE: never edits\n"
WANT = {"e.ctrle", "e.ctrlu", "e.ctrlb", "e.ctrlf"}


def gate(tag):
    log = f"{TMP}/gate_{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call(["make", "screditor-acceptance"], cwd=REPO, stdout=fh,
                             stderr=subprocess.STDOUT, timeout=2400)
    red = {l.split()[1] for l in open(log) if l.strip().startswith(("DIFF", "XX", "!!"))
           or (l.strip().split()[:1] and l.strip().split()[0] not in ("ok",) and
               len(l.split()) > 1 and l.split()[1].startswith("e."))}
    return rc, red


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
            print(f"K-E1: build rc={brc} reached-ROM={ok} -- NOT SCORED")
        else:
            rc, red = gate("k")
            hit = rc != 0 and WANT <= red
            print(f"K-E1 (tenant never handles): gate {'RED' if rc else 'GREEN'}, "
                  f"red {sorted(red)}; predicted {sorted(WANT)}: {'HIT' if hit else 'MISS'}")
    finally:
        open(SRC, "w").write(text)
    ok, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    rc, red = gate("restore")
    print(f"restored: build rc={brc}; gate {'GREEN' if not rc else 'RED -- RESTORE BROKEN'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
