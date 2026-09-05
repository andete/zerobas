#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""K-FC1..3 — the 8.3 character check, falsified by planting.

The fix has two independent halves and one shape it must NOT have, so there are
three knives and the third is the interesting one:

    knife                                   rows that must go red
    K-FC1  the control-band test removed    m.ctlchar            (separators hold)
    K-FC2  the separator table emptied      m.sepchar, m.ffchar  (controls hold)
    K-FC3  rewritten as a HIGH-BIT test     m.hi80, m.sepchar    (m.ffchar holds!)

🎯 K-FC3 IS THE POINT. `$80` accepted beside `$FF` refused is the measurement
that forbids implementing this as `cp $80 / ret nc`, and a knife that plants
exactly that mistake is the only thing that proves `m.hi80` earns its place.
⚠️ Its prediction is deliberately awkward: under a high-bit test `m.ffchar` still
REDDENS NOTHING, because $FF is high-bit and stays refused — the wrong rule gets
that row right. A knife whose every predicted row moved would not be
distinguishing the rules at all.

🔴 ROM-HASHED ROUND EVERY PLANT (D-KNIFEROM2) and the source restored
byte-identically.

    python3 scratchpad/fspecchar_knives.py [--only K-FC3]
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

TMP = "scratchpad/fspecchar_knives"
SRC = "basic/fcbname-body.inc"
GATE = "probes/basic/basic_probe_namspc.py"
ROWS = "m.ctlchar,m.sepchar,m.ffchar,m.hi80,m.gtchar,m.long,f.fileslit"

CTL = """                cp      ' '
                ret     c                   ; $01..$1F -> CF set by the compare
"""
KNIVES = [
    ("K-FC1", CTL,
     "                                            ; K-FC1 CUT: no control band\n",
     {"m.ctlchar"},
     "the control-band test removed -- only the control row may move"),
    # 🔴 `BN_NBAD equ 0` WAS THE FIRST CUT AND IT BROKE THE MACHINE, NOT THE
    # TABLE: `ld bc,0` makes `cpir` run 65536 times and walk all of memory, so
    # four unrelated rows moved and neither predicted row did. The table is
    # emptied instead by filling it with $01 -- a control byte, already refused
    # by the band test above, so it can never reach the walk and the table
    # matches nothing.
    ("K-FC2", "                db      '+', ',', '/', ':', ';', '=', '[', $5C, ']', $FF",
     "                db      1,1,1,1,1,1,1,1,1,1  ; K-FC2 CUT: table neutered",
     {"m.sepchar", "m.ffchar"},
     "the separator table neutered -- the controls must still be refused"),
    ("K-FC3", CTL + """                push    bc
                push    hl
                ld      hl,bn_badchars
                ld      bc,BN_NBAD
                cpir                        ; Z if A is in the table (A untouched)
                pop     hl
                pop     bc
                scf
                ret     z                   ; illegal
                or      a                   ; legal -> CF clear
                ret""",
     """                cp      $80                 ; K-FC3 CUT: the HIGH-BIT rule
                ccf                         ; the measurement says is WRONG
                ret""",
     # 🔴 THE FIRST PREDICTION HERE SAID {m.hi80, m.sepchar} AND WAS ONE ROW
     # SHORT: a high-bit-only rule drops the CONTROL BAND as well, so m.ctlchar
     # moves too. What still holds -- and is the whole reason this knife exists --
     # is `m.ffchar`: $FF is high-bit, so the WRONG rule gets that row right.
     {"m.ctlchar", "m.hi80", "m.sepchar"},
     "rewritten as a high-bit test -- m.hi80 is the row that forbids this, and "
     "m.ffchar HOLDING is what shows a wrong rule can still pass a row"),
]

ROW = re.compile(r"^\s*(?:ok|DIFF)\s+(\S+)\s", re.M)
DIFF = re.compile(r"^\s*DIFF\s+(\S+)\s", re.M)


def run_gate(tag):
    log = f"{TMP}/{tag}.out"
    with open(log, "w") as fh:
        rc = subprocess.call([sys.executable, GATE, "--gate", "--only", ROWS],
                             stdout=fh, stderr=subprocess.STDOUT)
    txt = open(log, encoding="utf-8", errors="replace").read()
    return rc, set(DIFF.findall(txt)), set(ROW.findall(txt)), log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    args = ap.parse_args()
    os.makedirs(TMP, exist_ok=True)
    sel = [k for k in KNIVES if not args.only or k[0] == args.only]
    if not sel:
        print(f"no knife matches {args.only!r}")
        return 2

    src = open(SRC).read()
    for tag, anchor, _r, _w, _y in sel:
        if src.count(anchor) != 1:
            print(f"INSTRUMENT FAULT: {tag}'s anchor occurs {src.count(anchor)} "
                  f"time(s), not once -- it would cut nothing and its red arm "
                  f"would pass by never firing.")
            return 2
    digest = hashlib.sha256(src.encode()).hexdigest()

    def restore():
        open(SRC, "w").write(src)
        assert hashlib.sha256(open(SRC).read().encode()).hexdigest() == digest
        print(f"  restored {SRC} byte-identically")
    atexit.register(restore)

    print("=== baseline")
    _m, _a, brc = knife_guard.build(f"{TMP}/base_build.log", None)
    if brc:
        print(f"INSTRUMENT FAULT: clean tree does not build ({TMP}/base_build.log)")
        return 2
    print(f"  ROM {knife_guard.hashes()}")
    rc0, diffs, rows, log0 = run_gate("base")
    print(f"  namspc rc={rc0}, {len(rows)} row(s), DIFF {sorted(diffs) or 'none'}   {log0}")
    if rc0 or diffs:
        print("INSTRUMENT FAULT: the gate is red BEFORE any cut.")
        return 2

    results, faults = [], []
    for tag, anchor, repl, want, why in sel:
        print(f"\n=== {tag}: {why}")
        open(SRC, "w").write(src.replace(anchor, repl, 1))
        h0 = knife_guard.hashes()
        moved, h1, brc = knife_guard.build(f"{TMP}/{tag}_build.log", h0)
        if brc:
            print(f"INSTRUMENT FAULT: knifed tree does not build "
                  f"({TMP}/{tag}_build.log)")
            faults.append(tag)
            open(SRC, "w").write(src)
            continue
        print(knife_guard.report(tag, moved, h0, h1))
        if not moved:
            faults.append(tag)
            continue
        rc, diffs, _rows, log = run_gate(tag)
        ok = diffs == want
        results.append((tag, want, diffs, ok))
        extra, missing = sorted(diffs - want), sorted(want - diffs)
        note = "ok" if ok else f"🔴 extra={extra} missing={missing}"
        print(f"  rc={rc}  DIFF {sorted(diffs)}   {note}   {log}")

    print("\n=== verdict")
    for tag, want, diffs, ok in results:
        print(f"  {tag}  want {sorted(want)}  got {sorted(diffs)}  "
              f"{'ok' if ok else '🔴'}")
    bad = [r for r in results if not r[3]]
    if faults:
        print(f"🔴 INSTRUMENT FAULT on {faults} -- those measured nothing.")
    print("KNIVES: PASS" if not bad and not faults
          else f"KNIVES: RED ({len(bad)} wrong, {len(faults)} fault(s))")
    return 1 if (bad or faults) else 0


if __name__ == "__main__":
    sys.exit(main())
