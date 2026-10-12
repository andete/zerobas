#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BASICROM knives on `make basicrom-acceptance` (basic_probe_basicrom.py).

K-B1  basic/basicrom.asm brom_run returns at once (no cartridge program runs):
      predicted `boot` red, `lptr` red too (nothing runs there either).
K-B2  basic/interp.asm is_lref accepts $0E only (the `cp LINEADDR_TOKEN` gone):
      predicted `lptr` red (Syntax error at its first GOSUB), `boot` green.
Built through knife_guard; restored on a CLEAN build and re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "basicrom_knife")
CUTS = [
    ("K-B1", "basic/basicrom.asm",
     "brom_run:\n                ld      a,(BROM_TEXT+1)\n",
     "brom_run:\n                ret                         ; KNIFE K-B1\n                ld      a,(BROM_TEXT+1)\n",
     {"boot", "lptr"}),
    ("K-B2", "basic/interp.asm",
     "                cp      LINENO_TOKEN\n                ret     z\n                cp      LINEADDR_TOKEN\n                ret\n",
     "                cp      LINENO_TOKEN\n                ret                         ; KNIFE K-B2\n",
     {"lptr"}),
]


def gate(tag):
    log = f"{TMP}/gate_{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call(["python3", "-u", "probes/basic/basic_probe_basicrom.py"], cwd=REPO,
                             stdout=fh, stderr=subprocess.STDOUT, timeout=2400)
    return rc, {l.split()[0] for l in open(log) if "DIVERGES" in l}


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
