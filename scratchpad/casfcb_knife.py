#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CASFCB knives: is the tape-buffer pointer (CAS_BUFP) seen by the gates?

K-F1  basic/bload.asm: BLOAD's stub no longer sets it. Predicted: casbin's bty
      and bbare RED (the search's skip reads through an unset pointer).
K-F2  basic/cload.asm: cas_open_match's stub no longer sets it. Predicted:
      casbin's lbin RED and cas-ascii RED (LOAD's ASCII path).
Each cut is the `xor a` / `call cas_bufp_set` pair turned into nops; built
through knife_guard; restored on a CLEAN build and both suites re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "casfcb_knife")
SUITES = ("casbin-acceptance", "cas-ascii-acceptance")
CUTS = [
    ("K-F1", "basic/bload.asm",
     "                xor     a                   ; D-CASFCB: a tape BLOAD's search skips\n"
     "                call    cas_bufp_set        ;  other files through channel #0's buffer\n",
     "                nop                         ; KNIFE K-F1\n                nop\n                nop\n                nop\n",
     "casbin: bty, bbare"),
    ("K-F2", "basic/cload.asm",
     "                xor     a\n                call    cas_bufp_set\n                call    sc_inl1",
     "                nop                         ; KNIFE K-F2\n                nop\n                nop\n                nop\n                call    sc_inl1",
     "casbin: lbin (+ cas-ascii)"),
]


def run_suites(tag):
    out = {}
    for t in SUITES:
        log = f"{TMP}/{tag}_{t}.log"
        with open(log, "w") as fh:
            rc = subprocess.call(["make", t], cwd=REPO, stdout=fh, stderr=subprocess.STDOUT,
                                 timeout=2400)
        red = [l.split()[1].rstrip(":") for l in open(log) if l.startswith("DIVERGES")]
        out[t] = (rc, red)
    return out


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
            res = run_suites(tag)
            print(f"{tag}: predicted {want}; got " + "; ".join(
                f"{t.replace('-acceptance', '')} {'RED' if rc else 'green'} {red}"
                for t, (rc, red) in res.items()), flush=True)
        finally:
            open(src, "w").write(text)
    ok, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    res = run_suites("restore")
    print(f"restored: build rc={brc}; " + "; ".join(
        f"{t.replace('-acceptance', '')} {'RED -- RESTORE BROKEN' if rc else 'green'}"
        for t, (rc, red) in res.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
