#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-LOC — `LOC(#n)`, gated: the record number on a RANDOM channel, the file
size on a sequential one, per channel.

The three rows are D-LOCSEM's (scratchpad/loc_probe.py), which measured the
CF-3300 before LOC existed here; the fourth is new and is the row the shape was
chosen FOR: two random channels open at once, each LOC reading its OWN last
record -- a single global (GP_RECNO) would answer the second channel's number
for both. Expectations are the CF-3300's measured faces; `--survey` re-reads it.

    s.seq   sequential: LOC before / after 5 B / after 10 B   -> 26,26,26
    r.get   random: GET #1,3 then GET #1,7                    -> 0,3,7
    w.put   random: PUT #1,4                                  -> 0,4,0
    t.two   two random channels: GET #1,3 / GET #2,5 (LEN=8 -- PROG.BIN is 57 B), then LOC(1);LOC(2) -> 3,5

Every row mounts its OWN copy of disk/test720.dsk (w.put creates a file;
"it only reads" is an assumption, not a guarantee -- D-LOCSEM's rule).
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                              # noqa: E402
import probe_sides                                            # noqa: E402
import probe_tmp                                              # noqa: E402

FIXTURE = os.path.join(REPO, "disk", "test720.dsk")
CASES = [
    ("s.seq", ['10 ON ERROR GOTO 90', '20 OPEN"HI.TXT"FOR INPUT AS #1', '30 A=LOC(1)',
               '40 X$=INPUT$(5,#1):B=LOC(1)', '50 X$=INPUT$(5,#1):C=LOC(1)',
               '70 PRINT"[s.seq";A;",";B;",";C;"]":END', '90 PRINT"[s.seq ERR";ERR;"]":END']),
    ("r.get", ['10 ON ERROR GOTO 90', '20 OPEN"TEST.BIN"AS #1 LEN=128', '30 A=LOC(1)',
               '40 GET #1,3:B=LOC(1)', '50 GET #1,7:C=LOC(1)',
               '70 PRINT"[r.get";A;",";B;",";C;"]":END', '90 PRINT"[r.get ERR";ERR;"]":END']),
    ("w.put", ['10 ON ERROR GOTO 90', '20 OPEN"LOCW.DAT"AS #1 LEN=32', '30 FIELD #1,32 AS F$',
               '40 LSET F$="x":PUT #1,4:B=LOC(1)', '50 CLOSE',
               '60 PRINT"[w.put";0;",";B;",";0;"]":END', '90 PRINT"[w.put ERR";ERR;"]":END']),
    ("t.two", ['10 ON ERROR GOTO 90', '15 MAXFILES=2', '20 OPEN"TEST.BIN"AS #1 LEN=128',
               '25 OPEN"PROG.BIN"AS #2 LEN=8', '30 GET #1,3:GET #2,5',
               '70 PRINT"[t.two";LOC(1);",";LOC(2);"]":END', '90 PRINT"[t.two ERR";ERR;"]":END']),
]
EXPECT = {"s.seq": "26 , 26 , 26", "r.get": "0 , 3 , 7", "w.put": "0 , 4 , 0", "t.two": "3 , 5"}
# t.two is GATED since 2026-09-11. It was filed as blocked by D-OPEN2 (a second
# concurrent disk OPEN raised ERR 2); D-OPEN2 closed by measurement the same day
# and the row STILL read no fence -- because it was mis-authored: channel 2 opened
# PROG.BIN (57 B) with LEN=128 and asked for record 5, which is `Input past end`
# on the CF-3300 too. A row that cannot reach its own face on the oracle gates
# nothing; LEN=8 puts record 5 at offset 32, inside the file, on both machines.
NEXT_GATE = set()


def fence(tag, cap):
    """The printed `[tag ...]`, never the typed echo of the PRINT that makes it:
    an echo carries `";` between its brackets (`PRINT"[t.two ERR";ERR;"]"`), a
    printed fence never does. The first cut read t.two's echo as its face."""
    c = cap or ""
    k = len(c)
    while True:
        i = c.rfind("[" + tag, 0, k)
        if i < 0:
            return None
        j = c.find("]", i + 1)
        if j > 0 and '";' not in c[i:j]:
            return " ".join(c[i + len(tag) + 1:j].split())
        k = i


def read(side, cfg):
    out = {}
    for tag, prog in CASES:
        dsk = probe_tmp.tmp(f"loc_{tag}_{side}.dsk")
        shutil.copyfile(FIXTURE, dsk)
        cap = omsx_repl.run_cases(cfg["machine"], [(tag, prog + ["RUN"])], batch=False,
                                  boot=cfg["boot"], reset=cfg["reset"],
                                  diska=probe_sides.diska(side, dsk), run_gap=60.0)[0]
        out[tag] = fence(tag, cap)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--survey", action="store_true")
    a = ap.parse_args()
    sides = ("cf3300", "zb") if a.survey else ("zb",)          # the VG-8020 has no drive
    cfg = probe_sides.sides(*sides)
    got = {s: read(s, cfg[s]) for s in sides}
    bad = []
    for tag, _ in CASES:
        g, w = got["zb"][tag], EXPECT[tag]
        ok = g == w
        if tag in NEXT_GATE and not ok:
            print(f"  wait {tag:6} zb={g!r:16} want={w!r}  (blocked by D-OPEN2, not gated)")
            continue
        bad += [] if ok else [tag]
        extra = f"  cf3300={got['cf3300'][tag]!r}" if a.survey else ""
        print(f"  {'ok  ' if ok else 'DIFF'} {tag:6} zb={g!r:16} want={w!r}{extra}")
    print(f"{len(CASES)} rows, {len(bad)} diverge: {bad or 'none'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
