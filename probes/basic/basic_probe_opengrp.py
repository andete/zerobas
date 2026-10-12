#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-OPENGRP gate: `OPEN "GRP:"` -- text on the graphics screen -- against the
VG-8020, on BOTH repack machines. `make opengrp-acceptance`.

The rule (TODO.md D-OPENGRP, measured in five rounds, scratchpad/opengrp*_probe):
PRINT # draws each byte's font glyph at the graphic cursor, every 1 bit set
exactly as PSET sets a pixel in FORCLR, 0 bits transparent; +8 per glyph
(SCREEN 3: 4x4 blocks, +32); x reaching 256 -> next line, y reaching 192 -> top;
CR is a new line, every other code below 32 is ignored; CHR$(1) then a byte in
64..95 draws glyph byte-64, then anything else acts as if no header came; SCREEN 0/1 is ERR 5 at PRINT #; FOR INPUT is 56; one GRP:
channel at a time (52); the comma zone always pads 14.

🔴 THE FONT IS NOT COMPARED ACROSS MACHINES. zerobas draws C-BIOS's font, as its
text screen does; the VG-8020 draws its own (`A` is 70 88 88 F8 88 88 00 00
against 20 50 88 88 F8 88 88 00). So:
  * every CROSS-machine row is font-free: cursor positions, error codes, wraps,
    control codes, comma zones, the FCB header bytes;
  * `model` is font-free BY CONSTRUCTION: each machine draws "A" on a blank
    area, reads its bits back with POINT (observation -- clean room on the
    reference too), then draws it both ways over clashing 8x1 colour cells at
    an unaligned x -- PRINT # and PSET-each-bit -- and compares all 128
    pixels: `1 1` = identical AND something lit (two blank drawings would
    compare equal too). The VG-8020 reads `1 1` (round 4's finding);
  * `font` (zerobas only) checks the drawn bits ARE zerobas's own font bytes,
    PEEKed through CGPNT -- our own ROM, which the clean room allows.
The VG-8020 side comes through the refcache; a reference with no reading is an
INSTRUMENT FAULT, never a pass (the first C5-LOW probe agreed on None x3).
Clean room: typed BASIC, POINT, PEEK of published work-area cells.
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = "Philips_VG_8020"
OURS = ("C-BIOS_MSX1_EU_REPACK_NODISK", "C-BIOS_MSX1_EU_REPACK_DISK")
CUR = ('510 T$=T$+MID$(STR$(PEEK(&HFCB7)+256*PEEK(&HFCB8)),2)+","+'
       'MID$(STR$(PEEK(&HFCB9)+256*PEEK(&HFCBA)),2)+" ":RETURN')
OUT = ['70 SCREEN 0:PRINT"<";T$;">":END', '90 SCREEN 0:PRINT"<E";ERR;ERL;">":END']


def prog(scr, body):
    return (["10 CLEAR 1000:ON ERROR GOTO 90", f"20 SCREEN {scr}:COLOR 15,4:CLS",
             '30 OPEN"GRP:"FOR OUTPUT AS #1'] + body + OUT + [CUR])


def at(n, x, y, what):
    return f"{n} PSET({x},{y}),4:PRINT #1,{what};:GOSUB 510"


SWEEP = ('45 IF X0=24 AND Y0=16 THEN T$=T$+"." ELSE IF X0=16 AND Y0=16 '
         'THEN T$=T$+"c" ELSE T$=T$+"["+HEX$(C)+":"+STR$(X0)+STR$(Y0)+"]"')
SW_CUR = "41 X0=PEEK(&HFCB7)+256*PEEK(&HFCB8):Y0=PEEK(&HFCB9)+256*PEEK(&HFCBA)"


def model(bg):
    return prog(2, [
        '35 PSET(100,100),4:PRINT #1,"A";',
        "36 FOR J=0 TO 7:B=0:FOR I=0 TO 7:B=B*2-(POINT(100+I,100+J)=15):NEXT:G(J)=B:NEXT",
        f"40 LINE({bg},8)-(23,15),6,BF:LINE({bg},24)-(23,31),6,BF",
        '41 PSET(10,8),15:PRINT #1,"A";',
        "42 PSET(10,24),15:FOR J=0 TO 7:FOR I=0 TO 7",
        "43 IF G(J) AND 2^(7-I) THEN PSET(10+I,24+J),15",
        "44 NEXT:NEXT",
        "45 FOR Y=0 TO 7:FOR X=8 TO 23:T$=T$+HEX$(POINT(X,8+Y)):U$=U$+HEX$(POINT(X,24+Y))",
        # equal AND not vacuous: two blank drawings would compare equal too. The
        # observed glyph being non-empty is the guard (U$ is PSET of it, so a
        # T$ equal to it has lit pixels). Not INSTR: zerobas's INSTR read 0 on
        # these 128-character strings (D-INSTR128, found by this gate).
        "46 NEXT:NEXT:S=0:FOR J=0 TO 7:S=S OR G(J):NEXT",
        "47 T$=MID$(STR$(-(T$=U$)),2)+\" \"+MID$(STR$(-(S>0)),2)"])


CASES = {
    # cursor walk: glyph, CR/LF, the right edge (no wrap at 240/244, wrap at
    # 248/252), the bottom (184+CR -> 0, 176/180+CR stay), CR LF pairs, the
    # CHR$(1) header, ignored codes, a clipped glyph at y=188
    "core": prog(2, [
        at(40, 8, 8, '"A"'), "41 PSET(8,8),4:PRINT #1,\"A\":GOSUB 510",
        at(42, 240, 8, '"A"'), at(43, 244, 8, '"A"'), at(44, 248, 8, '"A"'),
        at(45, 252, 8, '"A"'), at(46, 248, 184, '"A"'),
        at(47, 8, 176, '"A";CHR$(13)'), at(48, 8, 180, '"A";CHR$(13)'),
        at(49, 8, 184, '"A";CHR$(13)'), at(50, 8, 8, '"A";CHR$(13);CHR$(10)'),
        at(51, 8, 8, '"A";CHR$(10);CHR$(13)'), at(52, 8, 8, '"A";CHR$(13);"B"'),
        at(53, 16, 16, 'CHR$(1);"A"'), at(54, 16, 16, '"A";CHR$(12);CHR$(7);CHR$(127)'),
        at(55, 8, 188, '"A"')]),
    # the channel: errors under RESUME NEXT, the FCB header, a bare OPEN
    "errors": ["10 CLEAR 1000:ON ERROR GOTO 900", "20 SCREEN 0",
               '30 OPEN"GRP:"FOR OUTPUT AS #1', '31 PRINT #1,"A"',
               '32 SCREEN 1:PRINT #1,"A"', "33 SCREEN 2:CLOSE",
               '34 OPEN"GRP:"FOR INPUT AS #1', '35 OPEN"GRP:"FOR OUTPUT AS #1',
               '36 OPEN"GRP:"FOR OUTPUT AS #2', "37 INPUT #1,A$", "38 LINE INPUT #1,A$",
               "39 A$=INPUT$(1,#1)", "40 E=EOF(1)", "41 E=LOC(1)", "42 E=LOF(1)",
               '43 V=VARPTR(#1):T$=T$+" H"+STR$(PEEK(V))+STR$(PEEK(V+4))',
               '44 CLOSE #1:PRINT #1,"A"',
               '45 OPEN"GRP:"AS #1:PSET(8,8),4:PRINT #1,"A";:T$=T$+" B"+STR$(PEEK(&HFCB7))',
               '70 SCREEN 0:PRINT"<";T$;">":END',
               '900 T$=T$+" "+MID$(STR$(ERR),2)+"@"+MID$(STR$(ERL),2):RESUME NEXT'],
    # PRINT's spacing and the comma zone (always 14 on GRP:)
    # (44: the text cursor moved to column 11 first. "Zone from CSRX" and "zone
    # from column 0" COINCIDE while CSRX is 1 -- knife K-G2 went green on 40-43
    # alone; the VG-8020 pads 14 here too, so the column-0 rule is its rule.)
    "zones": prog(2, [at(40, 0, 8, "12;-3"), at(41, 0, 8, '"A","B"'),
                      at(42, 0, 8, '"AB","C"'), at(43, 0, 8, '"A","B","C"'),
                      '44 POKE &HF3DD,11:PSET(0,8),4:PRINT #1,"A","B";:GOSUB 510']),
    "sweepLo": prog(2, ["40 FOR C=0 TO 127:PSET(16,16),4:PRINT #1,CHR$(C);", SW_CUR,
                        SWEEP, "50 NEXT"]),
    "sweepHi": prog(2, ["40 FOR C=128 TO 255:PSET(16,16),4:PRINT #1,CHR$(C);", SW_CUR,
                        SWEEP, "50 NEXT"]),
    "scr3": prog(3, [at(40, 8, 8, '"A"'), "41 PSET(8,8),4:PRINT #1,\"A\":GOSUB 510",
                     at(42, 220, 8, '"A"'), at(43, 224, 8, '"A"')]),
    # the CHR$(1) header (round 6): + a control (ignored, CR a new line),
    # + 64..95 (glyph byte-64), + 48 / 255 / 63 / 96 (the byte itself); flags
    # compare cells drawn on the SAME machine, so font-free
    "header": prog(2, [
        "40 PSET(16,16),4:PRINT #1,CHR$(1);CHR$(2);:GOSUB 510",
        '41 PSET(16,32),4:PRINT #1,CHR$(1);"0";:GOSUB 510',
        '42 PSET(16,48),4:PRINT #1,CHR$(1);CHR$(2);"A";:GOSUB 510',
        "43 PSET(16,64),4:PRINT #1,CHR$(1);CHR$(13);:GOSUB 510",
        '44 PSET(100,100),4:PRINT #1,"A";:PSET(120,100),4:PRINT #1,CHR$(1);"A";',
        '45 PSET(140,100),4:PRINT #1,"0";:PSET(160,100),4:PRINT #1,CHR$(1);CHR$(96);',
        "46 PSET(180,100),4:PRINT #1,CHR$(96);",
        "47 X=16:Y=48:GOSUB 600:A$=R$:X=100:Y=100:GOSUB 600:B$=R$:X=120:GOSUB 600",
        '48 T$=T$+"2A="+MID$(STR$(-(A$=B$)),2)+MID$(STR$(-(A$=R$)),2)',
        "49 X=16:Y=32:GOSUB 600:A$=R$:X=140:Y=100:GOSUB 600",
        '50 T$=T$+" 48="+MID$(STR$(-(A$=R$)),2)',
        "51 X=160:GOSUB 600:A$=R$:X=180:GOSUB 600",
        '52 T$=T$+" 96="+MID$(STR$(-(A$=R$)),2)',
        '600 R$="":FOR J=0 TO 7:B=0:FOR I=0 TO 7:B=B*2-(POINT(X+I,Y+J)=15):NEXT',
        '610 R$=R$+RIGHT$("0"+HEX$(B),2):NEXT:RETURN']),
    "modelblk": model(8),
    "modelhalf": model(12),
}
FONT = prog(2, ['35 PSET(100,100),4:PRINT #1,"A";',
                "36 F=PEEK(&HF920)+256*PEEK(&HF921)+8*65:S=1",
                "37 FOR J=0 TO 7:B=0:FOR I=0 TO 7:B=B*2-(POINT(100+I,100+J)=15):NEXT",
                "38 S=S*-(B=PEEK(F+J)):NEXT:T$=MID$(STR$(S),2)"])
RX = re.compile(r"<[^<>]*>")


def read(machine, lines):
    raw = omsx_repl.run_cases(machine, [("direct", ["NEW"] + lines + ["RUN"])],
                              batch=False, reset=("", "SCREEN 0"), run_gap=60.0)[0] or ""
    flat = raw.replace("\n", "")
    run = flat[flat.rfind("RUN") + 3:] if "RUN" in flat else flat
    hits = RX.findall(run)
    return re.sub(" +", " ", hits[-1]) if hits else None


def main() -> int:
    bad = 0
    for name, lines in CASES.items():
        ref = read(REF, lines)
        if ref is None or ref.startswith("<E"):
            print(f"{name:9s} INSTRUMENT FAULT: the VG-8020 gave {ref!r}")
            return 2
        print(f"{name:9s} {'VG-8020':30s} {ref}", flush=True)
        for m in OURS:
            got = read(m, lines)
            same = got == ref
            bad += not same
            print(f"{name:9s} {m:30s} {got}  {'SAME' if same else 'DIVERGES'}", flush=True)
    for m in OURS:
        got = read(m, FONT)
        good = got == "<1>"
        bad += not good
        print(f"{'font':9s} {m:30s} {got} (expect <1>: the drawn A is our own font's)"
              f"  {'PASS' if good else 'FAIL'}", flush=True)
    print("-------------------")
    print("opengrp gate:", "PASS" if not bad else f"FAIL ({bad})")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
