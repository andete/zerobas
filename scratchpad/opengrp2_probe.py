#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-OPENGRP, measurement round 2 -- what round 1 (opengrp_probe.py) left open.
VG-8020 only (zerobas has no GRP: device yet). Each case is a stored program;
the result is read with POINT and the graphic cursor (GRPACX $FCB7 / GRPACY
$FCB9, published work-area cells), then printed in SCREEN 0 between `<` `>`.
Clean room: typed BASIC, POINT, PEEK of documented cells.

  eraseA / eraseU   a white block, then "A" at x=8 / x=10: do 0 bits erase?
                    (cell read as POINT=15 bits: FF.. = transparent)
  redge / redge2    "A" at x=248 / x=252, then "B": cursor after each, and the
                    cell at (0,16) -- does B wrap to the next line?
  bedge / bedge2    "A"+CR/LF at y=184, then "B" / "A" at y=188: cursor
  cNN               "A";CHR$(NN); at (16,16): cursor after, and the A cell
  scr3 / scr3crlf   SCREEN 3: cursor after "A", and a 4-pixel grid of 32x32

Prediction: transparent (0 bits leave the white); at the right edge the
cursor wraps to x=0 of the next 8-pixel line (B at (0,16)); at the bottom the
cursor stays put or wraps to 0 (unsure); CHR$(13) -> x=0 same line, CHR$(10)
-> next line keeping x (unsure), the other control codes draw a glyph (+8);
SCREEN 3 draws 4x4 blocks and advances 32.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

REF = "Philips_VG_8020"
SUBS = ['500 R$="":FOR Y=CY TO CY+7*S STEP S:B=0:FOR X=CX TO CX+7*S STEP S'
        ':B=B*2-(POINT(X,Y)=15):NEXT:R$=R$+RIGHT$("0"+HEX$(B),2):NEXT:RETURN',
        '510 X0=PEEK(&HFCB7)+256*PEEK(&HFCB8):Y0=PEEK(&HFCB9)+256*PEEK(&HFCBA)'
        ':RETURN',
        '90 SCREEN 0:PRINT"<E";ERR;ERL;">":END']
HEAD = ["10 ON ERROR GOTO 90:S=1", "20 SCREEN 2:COLOR 15,4:CLS",
        '30 OPEN"GRP:"FOR OUTPUT AS #1']


def case(*body):
    return HEAD + list(body) + SUBS


CASES = {
    "eraseA": case("35 LINE(0,0)-(31,31),15,BF", '40 PSET(8,8),15:PRINT #1,"A";',
                   "45 GOSUB 510:CX=8:CY=8:GOSUB 500",
                   '70 SCREEN 0:PRINT"<";R$;X0;Y0;">":END'),
    "eraseU": case("35 LINE(0,0)-(31,31),15,BF", '40 PSET(10,8),15:PRINT #1,"A";',
                   "45 GOSUB 510:CX=10:CY=8:GOSUB 500",
                   '70 SCREEN 0:PRINT"<";R$;X0;Y0;">":END'),
    "redge": case('40 PSET(248,8),4:PRINT #1,"A";:GOSUB 510:A=X0:B=Y0',
                  '45 PRINT #1,"B";:GOSUB 510:CX=0:CY=16:GOSUB 500',
                  '70 SCREEN 0:PRINT"<";A;B;X0;Y0;R$;">":END'),
    "redge2": case('40 PSET(252,8),4:PRINT #1,"A";:GOSUB 510:A=X0:B=Y0',
                   '45 PRINT #1,"B";:GOSUB 510:CX=0:CY=16:GOSUB 500',
                   '70 SCREEN 0:PRINT"<";A;B;X0;Y0;R$;">":END'),
    "bedge": case('40 PSET(8,184),4:PRINT #1,"A":GOSUB 510:A=X0:B=Y0',
                  '45 PRINT #1,"B";:GOSUB 510:CX=0:CY=0:GOSUB 500',
                  '70 SCREEN 0:PRINT"<";A;B;X0;Y0;R$;">":END'),
    "bedge2": case('40 PSET(8,188),4:PRINT #1,"A";:GOSUB 510',
                   '70 SCREEN 0:PRINT"<";X0;Y0;">":END'),
}
for c in (7, 8, 9, 10, 11, 12, 13, 28, 29, 30, 31, 127):
    CASES[f"c{c}"] = case(f'40 PSET(16,16),4:PRINT #1,"A";CHR$({c});',
                          "45 GOSUB 510:CX=16:CY=16:GOSUB 500",
                          '70 SCREEN 0:PRINT"<";X0;Y0;R$;">":END')
CASES["scr3"] = (["10 ON ERROR GOTO 90:S=4", "20 SCREEN 3:COLOR 15,4:CLS",
                  '30 OPEN"GRP:"FOR OUTPUT AS #1',
                  '40 PSET(8,8),4:PRINT #1,"A";:GOSUB 510:CX=8:CY=8:GOSUB 500',
                  '70 SCREEN 0:PRINT"<";X0;Y0;R$;">":END'] + SUBS)
CASES["scr3crlf"] = (["10 ON ERROR GOTO 90:S=4", "20 SCREEN 3:COLOR 15,4:CLS",
                      '30 OPEN"GRP:"FOR OUTPUT AS #1',
                      '40 PSET(8,8),4:PRINT #1,"A":GOSUB 510',
                      '70 SCREEN 0:PRINT"<";X0;Y0;">":END'] + SUBS)
RX = re.compile(r"<[^<>]*>")


def main():
    only = sys.argv[1:]
    for name, lines in CASES.items():
        if only and name not in only:
            continue
        raw = omsx_repl.run_cases(REF, [("direct", ["NEW"] + lines + ["RUN"])],
                                  batch=False, reset=("", "SCREEN 0"),
                                  cap_gap=15.0)[0] or ""
        flat = re.sub(r"\s+", " ", raw)
        run = flat[flat.rfind(" RUN ") + 5:] if " RUN " in flat else flat
        hits = RX.findall(run)
        print(f"{name:9s} {hits[-1] if hits else 'NONE: ' + run[-80:]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
