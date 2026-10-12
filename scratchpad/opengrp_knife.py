#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-OPENGRP knives on `make opengrp-acceptance` (basic_probe_opengrp.py).
Each cut must turn a NAMED case red; predicted before the run:

K-G1  sub2/grpprt.asm: the header's 64..95 range check dropped (byte-64 for
      every byte after CHR$(1)) -> `header` and `sweepLo` red.
K-G2  basic/print.asm: the comma zone's GRP: column-0 rule dropped -> `zones` red.
      FIRST RUN: GREEN -- a MISS. With the text cursor at column 1 (as it is in
      SCREEN 2), "zone from CSRX" and "zone from column 0" coincide on every row
      the gate had. Measured with CSRX moved to 11 (`POKE &HF3DD,11`): the
      VG-8020 still pads 14, so column 0 IS the rule; the row is now in `zones`.
      Re-run alone (`opengrp_knife.py K-G2`): predicted red.
K-G3  basic/grpdev.asm: pch_grp's SCREEN 0/1 refusal dropped -> `errors` red.
K-G4  sub2/grpprt.asm: the y wrap at 192 dropped (y keeps counting) -> `core` red.

Built through knife_guard (a cut that did not reach the ROM says so); every
cut is restored and the gate re-run green on a CLEAN build at the end (a
restore built in the same second as the cut can be skipped by make).
"""
import os, re, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "opengrp_knife")
CUTS = [
    ("K-G1", "sub2/grpprt.asm",
     "                cp      64                  ; only 64..95 are graphic-glyph codes:\n"
     "                jr      c,gp_plain          ; below, the byte is itself (a control\n"
     "                cp      96                  ; acts, 32..63 draws itself) -- above,\n"
     "                jr      nc,gp_plain         ; it draws itself too (round 6)\n",
     "", {"header", "sweepLo"}),
    ("K-G2", "basic/print.asm",
     "                sub     4                   ; PRDEV 4 = GRP: -> A = 0 = the column\n"
     "                jr      z,pcz_col\n"
     "                add     a,3                 ; back to PRDEV - 1\n",
     "                dec     a\n", {"zones"}),
    ("K-G3", "basic/grpdev.asm",
     "                jp      c,gfx_err5          ; SCREEN 0/1 -> ERR 5\n",
     "", {"errors"}),
    ("K-G4", "sub2/grpprt.asm",
     "                cp      192\n"
     "                jr      c,gp_sty            ; y reaching 192 wraps to the top\n",
     "                jr      gp_sty\n", {"core"}),
]


def gate(tag):
    log = f"{TMP}/gate_{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call(["python3", "-u", "probes/basic/basic_probe_opengrp.py"],
                             cwd=REPO, stdout=fh, stderr=subprocess.STDOUT, timeout=3000)
    red = {l.split()[0] for l in open(log) if "DIVERGES" in l or "FAIL" in l.split()[-1:]}
    return rc, red - {"opengrp"}


def main():
    os.makedirs(TMP, exist_ok=True)
    only = set(sys.argv[1:])
    for tag, path, old, new, want in CUTS:
        if only and tag not in only:
            continue
        src = os.path.join(REPO, path)
        text = open(src).read()
        if text.count(old) != 1:
            print(f"{tag}: REFUSED, anchor count {text.count(old)} in {path}")
            continue
        before = knife_guard.hashes()
        try:
            open(src, "w").write(text.replace(old, new))
            ok, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            if brc or not ok:
                print(f"{tag}: build rc={brc} reached-ROM={ok} -- NOT SCORED")
                continue
            rc, red = gate(tag)
            hit = rc != 0 and want <= red
            print(f"{tag} ({path}): gate {'RED' if rc else 'GREEN'}, red cases "
                  f"{sorted(red)}; predicted {sorted(want)}: {'HIT' if hit else 'MISS'}",
                  flush=True)
        finally:
            open(src, "w").write(text)
    ok, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    rc, red = gate("restore")
    print(f"restored: build rc={brc}; gate {'GREEN' if not rc else 'RED -- RESTORE BROKEN ' + str(sorted(red))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
