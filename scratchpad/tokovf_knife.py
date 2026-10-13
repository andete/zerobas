#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TOKOVF knife on `make linemax-acceptance ONLY=corrupt-ovf`.

K-T1  basic/tokenise.inc: the bound at tk_loop's head is cut (its `jp c,tk_end`
      becomes three `nop`s, so the test runs and decides nothing): predicted
      corrupt-ovf RED (zerobas reads back an overrun byte, not 7), corrupt-ovfctl
      green. HIT while TOKBUF was $EC00 (scratchpad/tokovf_knife.out).
      🔴 INERT SINCE D-RAMKBUF (TOKBUF = KBUF, 2026-10-12): the unbounded crunch
      now overruns into BUF, its own source, ahead of the read cursor, and the
      `0#` literals' $00 bytes end the line early -- nothing past BUF is touched
      (scratchpad/ramkbuf_knife.out: green with the cut). The bound's witness
      moved to the host: tests/test_tokenise.py measures the crunch's reach
      (321 live, 831 cut: scratchpad/ramkbuf_hostknife.out).
Built through knife_guard; restored on a CLEAN build and re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "tokovf_knife")
CUTS = [
    ("K-T1", "basic/tokenise.inc",
     "                pop     hl\n                jp      c,tk_end\n                ld      a,(TKNAME)\n",
     "                pop     hl\n                nop                         ; KNIFE K-T1\n"
     "                nop\n                nop\n                ld      a,(TKNAME)\n",
     {"corrupt-ovf"}),
]


def gate(tag):
    log = f"{TMP}/gate_{tag}.log"
    env = dict(os.environ, ZEROBAS_REFCACHE="0")
    with open(log, "w") as fh:
        rc = subprocess.call(["make", "linemax-acceptance", "ONLY=corrupt-ovf"], cwd=REPO,
                             stdout=fh, stderr=subprocess.STDOUT, timeout=2400, env=env)
    red = {l.split()[2] for l in open(log) if l.startswith("FAIL")}
    print(open(log).read().split("\n\n")[-1].strip()[-200:])
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
