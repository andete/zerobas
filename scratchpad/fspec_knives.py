#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""K-FS1..3 — the D-FSPEC filespec fix, falsified by planting.

The fix has THREE independent parts and each one owns a different set of rows.
A knife per part, with the greens carrying the information:

    knife                                    rows that must go red
    K-FS1  positional split -> reject again   w.savepos, w.savenodot, w.savelong,
                                              m.long, m.both      (NOT m.twodot)
    K-FS2  '.' tested before the full check   the over-long rows only, because the
                                              leftover `.BAS` reads as a 2nd dot
    K-FS3  `Bad file name` -> bl_load_error   m.twodot/m.empty/m.dot/m.dotdot and
                                              every v.* row  (NOT the w.* ones)

🎯 K-FS3'S GREENS ARE THE SHARPEST. It changes only how a REJECT is reported, so
every row whose name is now ACCEPTED (the truncation rows) must be untouched. A
knife that reddened those too would mean the two halves of the fix are not
separable, and the rows could not tell a parse change from a reporting one.

🔴 THE ROM HASH ROUND EVERY PLANT (D-KNIFEROM2) and a REBUILD BEFORE THE
BASELINE -- a restore puts the source back but leaves build/ holding the last
knifed image, so a baseline without it measures the previous knife.

    python3 scratchpad/fspec_knives.py [--only K-FS2]
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

TMP = "scratchpad/fspec_knives"
FCB = "basic/fcbname-body.inc"
PDF = "basic/pdfcb-body.inc"
GATE = "probes/basic/basic_probe_namspc.py"
ROWS = ("m.long,m.longext,m.both,m.twodot,m.empty,m.dot,m.dotdot,"
        "v.kempty,v.k2dot,v.lempty,v.l2dot,v.sempty,v.s2dot,v.oempty,v.o2dot,"
        "w.savelong,w.saveext,w.savefit,w.savepos,w.savenodot")

KNIVES = [
    ("K-FS1", FCB,
     "                jr      z,bn_ext_pos        ; name full -> extension, positionally",
     "                jr      z,bn_reject         ; K-FS1 CUT",
     {"w.savepos", "w.savenodot", "w.savelong", "m.long", "m.both"},
     "a full name rejects again instead of starting the extension"),

    ("K-FS2", FCB,
     "                ld      a,b\n"
     "                or      a\n"
     "                jr      z,bn_skip           ; ext full -> swallow the rest (NOT\n"
     "                                            ; an error: `AB.EXTRA` -> `AB.EXT`)\n"
     "                ld      a,(hl)\n"
     "                cp      '.'",
     "                ld      a,(hl)\n"
     "                cp      '.'                 ; K-FS2 CUT: dot tested FIRST\n"
     "                jr      z,bn_reject\n"
     "                ld      a,b\n"
     "                or      a\n"
     "                jr      z,bn_skip\n"
     "                ld      a,(hl)\n"
     "                cp      '.'",
     {"m.long", "m.both", "w.savelong", "w.savepos", "w.savenodot"},
     "the '.' test moves before the full test -- leftovers read as a 2nd dot"),

    ("K-FS3", PDF,
     "                jp      pdf_badname",
     "                jp      bl_load_error       ; K-FS3 CUT",
     {"m.twodot", "m.empty", "m.dot", "m.dotdot",
      "v.kempty", "v.k2dot", "v.lempty", "v.l2dot",
      "v.sempty", "v.s2dot", "v.oempty", "v.o2dot"},
     "a malformed name goes back to load_error's print-and-return"),
]

DIFF = re.compile(r"^DIFF\s+(\S+)", re.M)


def run_gate(tag):
    log = f"{TMP}/{tag}.out"
    with open(log, "w") as fh:
        rc = subprocess.call([sys.executable, GATE, "--gate", "--only", ROWS],
                             stdout=fh, stderr=subprocess.STDOUT)
    txt = open(log, encoding="utf-8", errors="replace").read()
    return rc, set(DIFF.findall(txt)), log


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
    for tag, path, anchor, _r, _e, _w in sel:
        originals.setdefault(path, open(path).read())
        if originals[path].count(anchor) != 1:
            print(f"INSTRUMENT FAULT: {tag}'s anchor occurs "
                  f"{originals[path].count(anchor)} time(s) in {path}, not once "
                  f"-- the knife would cut nothing and its red arm would pass by "
                  f"never firing.")
            return 2
    digests = {p: hashlib.sha256(s.encode()).hexdigest()
               for p, s in originals.items()}

    def restore():
        for p, s in originals.items():
            open(p, "w").write(s)
            assert hashlib.sha256(open(p).read().encode()).hexdigest() == digests[p]
        print(f"  restored {', '.join(originals)} byte-identically")
    atexit.register(restore)

    print("=== baseline: rebuild first, then the gate must be GREEN")
    _m, _a, brc = knife_guard.build(f"{TMP}/base_build.log", None)
    if brc:
        print(f"INSTRUMENT FAULT: the clean tree does not build ({TMP}/base_build.log)")
        return 2
    print(f"  ROM {knife_guard.hashes()}")
    rc, diffs, log = run_gate("base")
    print(f"  namspc rc={rc}  DIFF rows {sorted(diffs) or 'none'}   {log}")
    if rc or diffs:
        print("INSTRUMENT FAULT: the gate is red BEFORE any cut.")
        return 2

    results, faults = [], []
    for tag, path, anchor, repl, want, why in sel:
        print(f"\n=== {tag}: {why}")
        for p, s in originals.items():
            open(p, "w").write(s)
        open(path, "w").write(originals[path].replace(anchor, repl, 1))
        before = knife_guard.hashes()
        moved, after, brc = knife_guard.build(f"{TMP}/{tag}_build.log", before)
        if brc:
            print(f"INSTRUMENT FAULT: the KNIFED tree does not build "
                  f"({TMP}/{tag}_build.log)")
            faults.append(tag)
            continue
        print(knife_guard.report(tag, moved, before, after))
        if not moved:
            faults.append(tag)
            continue
        rc, diffs, log = run_gate(tag)
        ok = diffs == want
        results.append((tag, want, diffs, ok))
        extra, missing = sorted(diffs - want), sorted(want - diffs)
        note = "ok" if ok else f"🔴 extra={extra} missing={missing}"
        print(f"  rc={rc}  DIFF rows {sorted(diffs)}   {note}   {log}")

    print("\n=== verdict")
    for tag, want, diffs, ok in results:
        print(f"  {tag}  {'ok' if ok else '🔴'}  want {len(want)} rows, got {len(diffs)}")
    bad = [r for r in results if not r[3]]
    if faults:
        print(f"🔴 INSTRUMENT FAULT on {faults} -- those knives measured nothing.")
    if bad:
        print("🔴 A prediction missed. A red arm that stayed green means the rows "
              "cannot see that part of the fix; a green control that reddened "
              "means the three parts are not separable after all.")
    print("KNIVES: PASS" if not bad and not faults
          else f"KNIVES: RED ({len(bad)} wrong, {len(faults)} fault(s))")
    return 1 if (bad or faults) else 0


if __name__ == "__main__":
    sys.exit(main())
