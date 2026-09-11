#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""dskio-acceptance — DSKI$ / DSKO$ against the CF-3300 (docs/spec-basic-dskio.md).

Rows (each on a PRIVATE copy of disk/test720.dsk, because DSKO$ writes):
    len    A$=DSKI$(0,0) -> LEN(A$) is 0 (the value is the empty string)
    dir    DSKI$(0,7), then read the buffer THROUGH the pointer at $F351: the
           root directory's first entry name, `TEST    BIN`
    boot   DSKI$(0,0), same readout: `EB FE 90` and `ZEROBAS ` at +3
    dsko   DSKI$(0,7), POKE the buffer's first byte to "X", DSKO$ 0,7, then
           FILES: the listing shows `XEST` -- and the host reads sector 7 of
           the private image and finds `XEST    BIN` (the disk, not the screen)
    o1     DSKO$ 0 (one argument) -> ERR 2
The buffer ADDRESS differs between machines by design ($EB95 on the CF-3300,
FSECTOR_BUF here) -- every row reads it through the pointer, never a literal.
The VG-8020 has no drive: nodisk-acceptance carries the diskless faces.
"""
from __future__ import annotations
import argparse, os, sys, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides, probe_tmp                       # noqa: E402
FIXTURE = os.path.join(REPO, "disk", "test720.dsk")
RD = '30 P=PEEK(&HF351)+256*PEEK(&HF352)'
CASES = [
    ("len",  ['20 A$=DSKI$(0,0)', '40 PRINT"[len";LEN(A$);"]":END']),
    ("dir",  ['20 A$=DSKI$(0,7)', RD, '40 PRINT"[dir";CHR$(PEEK(P));CHR$(PEEK(P+1));CHR$(PEEK(P+2));CHR$(PEEK(P+3));CHR$(PEEK(P+8));CHR$(PEEK(P+9));CHR$(PEEK(P+10));"]":END']),
    ("boot", ['20 A$=DSKI$(0,0)', RD, '40 PRINT"[boot";PEEK(P);PEEK(P+1);PEEK(P+2);CHR$(PEEK(P+3));CHR$(PEEK(P+4));CHR$(PEEK(P+5));CHR$(PEEK(P+6));"]":END']),
    ("dsko", ['20 A$=DSKI$(0,7)', RD + ':POKE P,ASC("X")', '40 DSKO$ 0,7', '50 FILES', '60 PRINT"[dsko OK]":END']),
    ("o1",   ['20 DSKO$ 0', '40 PRINT"[o1 OK]":END']),
]
EXPECT = {"len": "0", "dir": "TESTBIN", "boot": "235 254 144 ZERO", "dsko": "OK", "o1": "ERR 2"}
DISK = {"dsko": b"XEST    BIN"}        # host-side readout of sector 7, the disk not the screen

def fence(tag, cap):
    """The printed `[tag ...]`, never the typed echo (an echo carries `";`)."""
    c = cap or ""; k = len(c)
    while True:
        i = c.rfind("[" + tag, 0, k)
        if i < 0: return None
        j = c.find("]", i + 1)
        if j > 0 and '";' not in c[i:j]: return " ".join(c[i + len(tag) + 1:j].split())
        k = i

def read(side, cfg):
    out, disk = {}, {}
    for tag, body in CASES:
        dsk = probe_tmp.tmp(f"dskio_{tag}_{side}.dsk"); shutil.copyfile(FIXTURE, dsk)
        prog = ['10 ON ERROR GOTO 90'] + body + [f'90 PRINT"[{tag} ERR";ERR;"]":END', 'RUN']
        cap = omsx_repl.run_cases(cfg["machine"], [(tag, prog)], batch=False, boot=cfg["boot"],
                                  reset=cfg["reset"], diska=probe_sides.diska(side, dsk), run_gap=40.0)[0]
        out[tag] = fence(tag, cap)
        if tag in DISK: disk[tag] = open(dsk, "rb").read()[7 * 512:7 * 512 + 11]
    return out, disk

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--survey", action="store_true"); a = ap.parse_args()
    sides = ("cf3300", "zb") if a.survey else ("zb",)
    cfg = probe_sides.sides(*sides)
    got = {s: read(s, cfg[s]) for s in sides}
    bad = []
    for tag, _ in CASES:
        g, w = got["zb"][0][tag], EXPECT[tag]
        ok = g == w
        if tag in DISK:
            d = got["zb"][1][tag]; ok = ok and d == DISK[tag]
            g = f"{g!r} disk={d!r}"
        bad += [] if ok else [tag]
        extra = f"  cf3300={got['cf3300'][0][tag]!r}" + (f" disk={got['cf3300'][1][tag]!r}" if tag in DISK else "") if a.survey else ""
        print(f"  {'ok  ' if ok else 'DIFF'} {tag:5} zb={g!s:34} want={w!r}{extra}")
    print(f"{len(CASES)} rows, {len(bad)} diverge: {bad or 'none'}")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
