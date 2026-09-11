#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""nodiskerr-acceptance — a disk verb on an EMPTY drive is ERR 70 (docs/spec-basic-diskerr.md).

D-NMFAIL measured (2026-09-10): NAME / KILL / FILES / LOAD / SAVE on a drive with
no image mounted, `ON ERROR GOTO 900` armed -- the CF-3300 says `Disk offline`,
ERR 70, ERL 20, TRAPPED, and the program STOPS; zerobas printed `load error`,
never trapped, and RAN THE NEXT LINE. The eight rows below run with NO image
mounted; the fence carries its own row name (these programs CLS, so there is no
anchor row on the glass and a stale fence would name itself).
    n.name k.kill f.files l.load s.save    the five measured verbs
    d.dski d.dsko c.copy                   DSKI$ / DSKO$ / COPY (D-DSKNODISK's residual)
    b.bload m.merge                        BLOAD / MERGE (measured 2026-09-11: ERR 70 too)
The three message rows run WITH the image (the codes are raised by `ERROR n`):
    m.68 m.69 m.70    `Disk write protected` / `Disk I/O error` / `Disk offline`
                      (measured on the CF-3300; the diskless VG-8020 says
                      `Unprintable error` to 70 -- nodisk-acceptance's territory)
"""
from __future__ import annotations
import argparse, os, sys, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides, probe_tmp                       # noqa: E402
FIXTURE = os.path.join(REPO, "disk", "test720.dsk")
STMTS = {
    "n.name":  'NAME "A.BAS" AS "B.BAS"',
    "k.kill":  'KILL "A.BAS"',
    "f.files": 'FILES',
    "l.load":  'LOAD "A.BAS"',
    "s.save":  'SAVE "A.BAS"',
    "d.dski":  'A$=DSKI$(0,0)',
    "d.dsko":  'DSKO$ 0,0',
    "c.copy":  'COPY "A.BAS" TO "B.BAS"',
    "b.bload": 'BLOAD "A.BIN"',
    "m.merge": 'MERGE "A.BAS"',
}
def prog(tag, stmt):
    return ["10 ON ERROR GOTO 900", f"20 {stmt}",
            f'30 CLS:PRINT"[{tag} NO ERROR]":END',
            f'900 CLS:PRINT"[{tag} ERR";ERR;"AT";ERL;"]":END', "RUN"]
MSGS = {"m.68": 68, "m.69": 69, "m.70": 70}
EXPECT = {k: "ERR 70 AT 20" for k in STMTS}
EXPECT.update({"m.68": "Disk write protected in 10", "m.69": "Disk I/O error in 10", "m.70": "Disk offline in 10"})

def fence(tag, cap):
    c = cap or ""; k = len(c)
    while True:
        i = c.rfind("[" + tag, 0, k)
        if i < 0: return None
        j = c.find("]", i + 1)
        if j > 0 and '";' not in c[i:j]: return " ".join(c[i + len(tag) + 1:j].split())
        k = i

def msg_row(cap, code):
    """The interpreter's own error line for `ERROR n` at line 10: `<text> in 10`."""
    rows = [(cap or "")[k:k + 40].strip() for k in range(0, len(cap or ""), 40)]
    hits = [r for r in rows if r.endswith(" in 10") and "ERROR" not in r]
    return hits[-1] if hits else None

def read(side, cfg):
    out = {}
    for tag, stmt in STMTS.items():
        cap = omsx_repl.run_cases(cfg["machine"], [(tag, prog(tag, stmt))], batch=False, boot=cfg["boot"],
                                  reset=cfg["reset"], run_gap=30.0)[0]          # NO image mounted
        out[tag] = fence(tag, cap)
    for tag, code in MSGS.items():
        dsk = probe_tmp.tmp(f"nde_{tag}_{side}.dsk"); shutil.copyfile(FIXTURE, dsk)
        cap = omsx_repl.run_cases(cfg["machine"], [(tag, [f"10 ERROR {code}", "RUN"])], batch=False, boot=cfg["boot"],
                                  reset=cfg["reset"], diska=probe_sides.diska(side, dsk), run_gap=15.0)[0]
        out[tag] = msg_row(cap, code)
    return out

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--survey", action="store_true"); a = ap.parse_args()
    sides = ("cf3300", "zb") if a.survey else ("zb",)
    cfg = probe_sides.sides(*sides)
    got = {s: read(s, cfg[s]) for s in sides}
    bad = []
    for tag in list(STMTS) + list(MSGS):
        g, w = got["zb"][tag], EXPECT[tag]
        ok = g == w
        bad += [] if ok else [tag]
        extra = f"  cf3300={got['cf3300'][tag]!r}" if a.survey else ""
        print(f"  {'ok  ' if ok else 'DIFF'} {tag:8} zb={g!r:30} want={w!r}{extra}")
    print(f"{len(STMTS) + len(MSGS)} rows, {len(bad)} diverge: {bad or 'none'}")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
