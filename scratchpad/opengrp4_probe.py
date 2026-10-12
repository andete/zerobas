#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-OPENGRP, measurement round 4: is `PRINT #1` on GRP: the same as setting
each of the glyph's 1 bits with PSET in the foreground colour? Decides the
build -- C-BIOS's own GRPPRT (SCREEN 2 only, no wrap, no CHR$(1) header) or a
loop over our PSET primitive (SCREEN 2 and 3 alike).

Both drawings on the VG-8020, on a background that makes SCREEN 2's 8x1
colour cells clash, at an UNALIGNED x (10) so the glyph straddles two cells;
then every pixel's POINT colour over (8..23, 8..15), one hex digit each. The
glyph's bits are round 1's reading (20 50 88 88 F8 88 88 00). zerobas runs the
PSET drawing too (its PSET against the reference's).
Both start with the same `PSET(10,8),15` (the first run put it in the grp
drawing only, and the one pixel it set was the whole difference).
Clean room: typed BASIC and POINT.

  blk    the 16x8 area filled with colour 6 first
  half   only (12..19, 8..15) filled with 6 -- straddling the glyph's cells

Prediction: grp == pset on the VG-8020 in both backgrounds (the drawing is
"PSET each 1 bit"), and zerobas's pset == the VG-8020's.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

REF = "Philips_VG_8020"
OURS = os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
BG = {"blk": "35 LINE(8,8)-(23,15),6,BF", "half": "35 LINE(12,8)-(19,15),6,BF"}
DRAW = {"grp": ['40 PSET(10,8),15:PRINT #1,"A";'],
        "pset": ["39 PSET(10,8),15", "40 FOR J=0 TO 7:READ V:FOR I=0 TO 7",
                 "41 IF V AND 2^(7-I) THEN PSET(10+I,8+J),15",
                 "42 NEXT:NEXT",
                 "43 DATA &H20,&H50,&H88,&H88,&HF8,&H88,&H88,0"]}


def prog(bg, draw):
    return (["10 CLEAR 1000:ON ERROR GOTO 90", "20 SCREEN 2:COLOR 15,4:CLS",
             '30 OPEN"GRP:"FOR OUTPUT AS #1', BG[bg]] + DRAW[draw]
            + ["50 FOR Y=8 TO 15:FOR X=8 TO 23:T$=T$+HEX$(POINT(X,Y)):NEXT:NEXT",
               '70 SCREEN 0:PRINT"<";T$;">":END',
               '90 SCREEN 0:PRINT"<E";ERR;ERL;">":END'])


RX = re.compile(r"<[^<>]*>")


def read(m, lines):
    raw = omsx_repl.run_cases(m, [("direct", ["NEW"] + lines + ["RUN"])],
                              batch=False, reset=("", "SCREEN 0"), run_gap=60.0)[0] or ""
    flat = raw.replace("\n", "")
    run = flat[flat.rfind("RUN") + 3:] if "RUN" in flat else flat
    hits = RX.findall(run)
    return re.sub(" +", "", hits[-1]) if hits else None


def main():
    bad = 0
    for bg in BG:
        got = {"grp": read(REF, prog(bg, "grp")), "pset": read(REF, prog(bg, "pset"))}
        # zerobas has no GRP: yet -- the OPEN is dropped from its program
        got["ours"] = read(OURS, [l for l in prog(bg, "pset") if not l.startswith("30 ")])
        if got["grp"] is None or got["pset"] is None:
            print(f"{bg}: INSTRUMENT FAULT, no reference reading: {got}")
            return 2
        for k, v in got.items():
            rows = [v[1 + i * 16:17 + i * 16] for i in range(8)] if v and len(v) == 130 else [v]
            print(f"{bg:5s} {k:5s} {' '.join(str(r) for r in rows)}")
        same, ours = got["grp"] == got["pset"], got["ours"] == got["pset"]
        bad += not same
        print(f"{bg:5s} grp==pset on the VG-8020: {same}; zerobas pset == VG pset: {ours}\n",
              flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
