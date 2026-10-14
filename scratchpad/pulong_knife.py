#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PULONG / D-PUWIDE knife: does pulong-acceptance SEE each part of the fix?

K-PL1  basic/printusing.asm pu_hold_fmt: NEVER SNAPSHOT (the `jr nc,phf_snap`
       made a jump to the next instruction, 0 B) -- every format held by a
       descriptor copy, so a heap variable's body can move under it.
       Run 2 predicted `gc` DIVERGES and read GREEN -- MISS: the row was blind
       (F$ at the heap's top never moved). Run 3, with the `gcmove` row (the GC
       moves F$ and a 200 B string lands on its old bytes): predicted gcmove
       DIVERGES, nothing else. (Run 1 cut the 32 B cap back in;
       it cost 6 B against main page 1's 5 and did not build -- NOT SCORED.
       The truncation half is shown by the pre-fix run, pulong_probe.out.)
K-PL2  basic/pu-render.inc: the 24-wide check made unreachable (cp 25 -> cp 255).
       Predicted: w25 w30e d24 d25 s25 m25 c25 p25 DIVERGE. Run 1: those AND
       x25 -- MISS in the prediction, not the gate: x25's 25 `#` are over 24
       before its trailing `-` is even counted (pulong_knife_run1.out).
K-PL3  sub/printusing.asm pu_pchar: never stops (the window bound never met).
       Predicted: big, big2 DIVERGE.
Each cut: explicit file + anchor (count must be 1), built through knife_guard
(ROM must MOVE), the suite run, the file restored. Then a CLEAN build and the
suite re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "pulong_knife")
CUTS = [
    ("K-PL1", "basic/printusing.asm",
     "                jr      nc,phf_snap         ; in (or above) the heap: it can move\n",
     "                jr      nc,$+2              ; KNIFE K-PL1: never snapshot\n",
     ["gcmove"]),
    ("K-PL2", "basic/pu-render.inc",
     "                cp      25\n                jr      nc,ptf_wide\n",
     "                cp      255                 ; KNIFE K-PL2\n                jr      nc,ptf_wide\n",
     ["w25", "w30e", "d24", "d25", "s25", "m25", "c25", "p25"]),
    ("K-PL3", "sub/printusing.asm",
     "                cp      low(DB_WIN + DB_WINSZ - 1)\n                jr      nc,ppc_full         ; pchar would only flag it now\n",
     "                cp      255                 ; KNIFE K-PL3\n                jr      nc,ppc_full         ; pchar would only flag it now\n",
     ["big", "big2"]),
]


def suite(tag):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call(["make", "pulong-acceptance"], stdout=fh,
                             stderr=subprocess.STDOUT, timeout=3600)
    red = [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]
    return rc, red


def main():
    os.makedirs(TMP, exist_ok=True)
    for tag, src, old, new, pred in CUTS:
        text = open(src).read()
        if text.count(old) != 1:
            print(f"{tag}: REFUSED, anchor count {text.count(old)} in {src}", flush=True)
            return 2
    only = sys.argv[1:]
    for tag, src, old, new, pred in CUTS:
        if only and tag not in only:
            continue
        text = open(src).read()
        before = knife_guard.hashes()
        try:
            open(src, "w").write(text.replace(old, new))
            moved, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            if brc or not moved:
                print(f"{tag}: build rc={brc} ROM moved={moved} -- NOT SCORED", flush=True)
                continue
            rc, red = suite(tag)
            score = "HIT" if sorted(red) == sorted(pred) else "MISS"
            print(f"{tag}: pulong {'RED' if rc else 'green'}, diverging {red}; "
                  f"predicted {pred} -> {score}", flush=True)
        finally:
            open(src, "w").write(text)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    rc, red = suite("restore")
    print(f"restored: build rc={brc}; pulong {'RED -- RESTORE BROKEN ' + str(red) if rc else 'green'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
