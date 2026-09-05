#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""K-FE1..4 — are the `*-alive` verb controls actually VERB-specific?

TODO gap (1), filed by the fat-error 8-of-8 closure (spec-fat-error-verb-control
§8.6): *"no knife separates `bload-alive`, `open-alive` or `append-alive` from
the shared `fat_io_getbyte` layer, so each is shown to see its READ PATH die but
not proven verb-specific"*. This is that knife set.

    arm                                        rows that must move
    K-FE1  fat_io_getbyte -- the SHARED layer   every control that READS BYTES
    K-FE2  BLOAD's own $FE header check         bload-alive ONLY
    K-FE3  OPEN FOR INPUT's own mode byte       open-alive ONLY
    K-FE4  fat_io_append's own chain pickup     append-alive ONLY

🎯 K-FE1 IS NOT A CONTROL, IT IS THE OTHER HALF OF THE CLAIM. The filing says
these rows are coupled through one layer; nobody had run the cut that shows it.
Its green rows carry the information: `fat-alive` (FILES), `kill-alive` and
`name-alive` are DIRECTORY operations that read no file bytes, so they must hold
even when every reader dies. If they moved too, the cut would be breaking the
disk rather than the read layer.

⚠️ AND THE THREE VERB ARMS ARE THE ANSWER TO THE FILING. Each cuts code only its
own verb executes -- BLOAD's BSAVE-marker compare, OPEN's `mode = INPUT` store,
APPEND's re-use of the existing chain -- so a row moving under one of them is
moving for ITS VERB, which is exactly what "shown to see its read path die but
not proven verb-specific" says is missing.

🔴 ROM-HASHED ROUND EVERY PLANT (D-KNIFEROM2); sources restored byte-identically.

    python3 scratchpad/fatverb_knives.py [--only K-FE3]
"""
from __future__ import annotations

import argparse
import atexit
import hashlib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.chdir(ROOT)
sys.path.insert(0, HERE)
import knife_guard                                                # noqa: E402

TMP = "scratchpad/fatverb_knives"
GATE = ["make", "fat-error-acceptance"]

FATIO = "basic/fatio-body.inc"
BLOAD = "basic/bload-body.inc"
FILES = "basic/files.asm"
FAT = "basic/fat.asm"

KNIVES = [
    ("K-FE1", FATIO,
     "fat_io_getbyte:\n",
     "fat_io_getbyte:\n                scf                 ; K-FE1 CUT: every read fails\n                ret\n",
     {"load-alive", "run-alive", "bload-alive", "open-alive", "append-alive",
      "merge-alive"},
     "the SHARED read layer -- every byte-reading control must move, and the "
     "DIRECTORY ones (fat/kill/name) must not"),
    ("K-FE2", BLOAD,
     "                cp      BSAVE_DISK_ID\n",
     "                cp      $00                    ; K-FE2 CUT: BLOAD's own marker\n",
     {"bload-alive"},
     "BLOAD's own BSAVE-marker compare -- no other verb executes it"),
    ("K-FE3", FILES,
     "                ld      a,1                 ; mode = INPUT\n",
     "                ld      a,4                 ; K-FE3 CUT: INPUT opens RANDOM\n",
     # 🎯 `append-alive` MOVES TOO, AND THAT IS THE FILING'S GAP (2), NOT A
     # KNIFE ERROR. Its program is `OUTPUT "AA" : APPEND "BB" : read both back`
     # -- and the read-back is an `OPEN FOR INPUT`. So breaking OPEN breaks it,
     # which is exactly *"merge-alive, append-alive and kill-alive lean on a
     # SECOND verb, so a break elsewhere can mark their row NOT MEASURED --
     # loud, but not their own verb"*. Predicted here rather than discovered,
     # because a prediction that omits it would score this arm as a miss.
     {"open-alive", "append-alive"},
     "OPEN FOR INPUT's own mode byte -- only this verb STORES it, but "
     "append-alive READS BACK through it (the filing's gap 2)"),
    ("K-FE4", FAT,
     "                ld      hl,(FAT_FIRSTCLUS)\n                ld      (FWR_FIRST),hl\n",
     "                ld      hl,0                ; K-FE4 CUT: APPEND loses the chain\n                ld      (FWR_FIRST),hl\n",
     {"append-alive"},
     "fat_io_append's own re-use of the existing chain"),
]

ROW = re.compile(r"^\s*(PASS|FAIL)\s+(\S+)", re.M)


# 🔴 A ROW NAME APPEARS MORE THAN ONCE, AND A name->verdict DICT KEEPS THE LAST.
# `append-alive` is printed twice -- `FAIL append-alive ...` and then
# `PASS append-alive (directory) ...`, a second check under the same leading
# name -- so a dict comprehension recorded it as PASS and this matrix reported
# K-FE1 and K-FE4 as MISSES when both knives had worked. The knife was right and
# the READOUT was wrong [[readout-blind-to-its-own-subject]]. A row is FAILing if
# ANY of its lines says FAIL, so the failures are collected as a set.
def run_gate(tag):
    log = f"{TMP}/{tag}.out"
    with open(log, "w") as fh:
        rc = subprocess.call(GATE, stdout=fh, stderr=subprocess.STDOUT)
    txt = open(log, encoding="utf-8", errors="replace").read()
    seen = ROW.findall(txt)
    fails = {n for v, n in seen if v == "FAIL"}
    names = {n for _v, n in seen}
    return rc, fails, names, log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    args = ap.parse_args()
    os.makedirs(TMP, exist_ok=True)
    sel = [k for k in KNIVES if not args.only or k[0] == args.only]
    if not sel:
        print(f"no knife matches {args.only!r}")
        return 2

    originals = {}
    for tag, path, anchor, _r, _w, _y in sel:
        originals.setdefault(path, open(path).read())
        if originals[path].count(anchor) != 1:
            print(f"INSTRUMENT FAULT: {tag}'s anchor occurs "
                  f"{originals[path].count(anchor)} time(s) in {path}, not once "
                  f"-- it would cut nothing and its red arm would pass by never "
                  f"firing.")
            return 2
    digests = {p: hashlib.sha256(s.encode()).hexdigest()
               for p, s in originals.items()}

    def restore():
        for p, s in originals.items():
            open(p, "w").write(s)
            assert hashlib.sha256(open(p).read().encode()).hexdigest() == digests[p]
        print(f"  restored {', '.join(originals)} byte-identically")
    atexit.register(restore)

    print("=== baseline")
    _m, _a, brc = knife_guard.build(f"{TMP}/base_build.log", None)
    if brc:
        print(f"INSTRUMENT FAULT: clean tree does not build ({TMP}/base_build.log)")
        return 2
    print(f"  ROM {knife_guard.hashes()}")
    rc0, bad0set, names0, log0 = run_gate("base")
    bad0 = sorted(bad0set)
    print(f"  fat-error rc={rc0}, {len(names0)} row(s), FAIL {bad0 or 'none'}   {log0}")
    if rc0 or bad0:
        print("INSTRUMENT FAULT: the gate is red BEFORE any cut.")
        return 2

    results, faults = [], []
    for tag, path, anchor, repl, want, why in sel:
        print(f"\n=== {tag}: {why}")
        for p, s in originals.items():
            open(p, "w").write(s)
        open(path, "w").write(originals[path].replace(anchor, repl, 1))
        h0 = knife_guard.hashes()
        moved, h1, brc = knife_guard.build(f"{TMP}/{tag}_build.log", h0)
        if brc:
            print(f"INSTRUMENT FAULT: knifed tree does not build "
                  f"({TMP}/{tag}_build.log)")
            faults.append(tag)
            continue
        print(knife_guard.report(tag, moved, h0, h1))
        if not moved:
            faults.append(tag)
            continue
        rc, fails, _names, log = run_gate(tag)
        # only the *-alive controls are this matrix's subject
        got = {k for k in fails if k.endswith("-alive")}
        ok = got == want
        results.append((tag, want, got, ok))
        extra, missing = sorted(got - want), sorted(want - got)
        note = "ok" if ok else f"🔴 extra={extra} missing={missing}"
        print(f"  rc={rc}  alive rows FAILing {sorted(got)}   {note}   {log}")

    print("\n=== verdict")
    for tag, want, got, ok in results:
        print(f"  {tag}  want {sorted(want)}  got {sorted(got)}  "
              f"{'ok' if ok else '🔴'}")
    bad = [r for r in results if not r[3]]
    if faults:
        print(f"🔴 INSTRUMENT FAULT on {faults} -- those measured nothing.")
    print("KNIVES: PASS" if not bad and not faults
          else f"KNIVES: RED ({len(bad)} wrong, {len(faults)} fault(s))")
    return 1 if (bad or faults) else 0


if __name__ == "__main__":
    sys.exit(main())
