#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-OPENGRP, measurement round 3 -- what round 2 (opengrp2_probe.py) opened.
VG-8020 only. Same reading method: POINT and the graphic cursor (GRPACX
$FCB7 / GRPACY $FCB9), printed in SCREEN 0 between `<` `>`. Clean room: typed
BASIC, POINT, PEEK of documented cells. (`cap_gap` is NOT the run budget -- `run_gap` is; round 3's
first pass captured two cases mid-run. Round 2's `B=Y0` was clobbered by
subroutine 500's B; the cursor variables here are P / Q / T$.)

  sweep     CHR$(0..255) one at a time at (16,16): every code whose cursor
            is NOT (24,16), as code:x,y
  drawsA/B  what CHR$(1/7/10/12) and CHR$(27/127/255/32) draw at (16,16)
            and (24,16), and the cursor after
  pair      "A";CR;LF / "A";LF;CR / "A";CR;"B" -- where the cursor ends
  edges     cursor after "A" at x=240 / 244 / 248 at y=184, and after
            "A";CR at y=176 / 180
  scr3edge  SCREEN 3: cursor after "A" at x=220 / 224

Prediction: the sweep lists 0D (CR, -> 0,24) and 7F (DEL, -> 32,16) and
nothing else; the control codes draw their font glyph; CR;LF ends at (0,16)
with the LF swallowed after a CR, and LF;CR at (0,16) after a +8 LF; x wraps
when x+8 > 255 (240 -> 248, 244 -> 252, 248 at y=184 -> 0,0); y wraps when
y+8 > 191 (176 -> 184, 180 -> 0); SCREEN 3 wraps when x+32 > 255.
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
        '520 T$=T$+MID$(STR$(X0),2)+","+MID$(STR$(Y0),2)+" ":RETURN',
        '90 SCREEN 0:PRINT"<E";ERR;ERL;">":END']


def prog(scr, *body, s=1):
    return ([f"10 CLEAR 1000:ON ERROR GOTO 90:S={s}", f"20 SCREEN {scr}:COLOR 15,4:CLS",
             '30 OPEN"GRP:"FOR OUTPUT AS #1'] + list(body)
            + ['70 SCREEN 0:PRINT"<";T$;">":END'] + SUBS)


def draws(codes):
    return prog(2, "40 FOR I=1 TO 4:READ C:CLS:PSET(16,16),4:PRINT #1,CHR$(C);",
                '45 GOSUB 510:T$=T$+HEX$(C)+"=":GOSUB 520:CX=16:CY=16:GOSUB 500',
                '50 T$=T$+R$+"/":CX=24:GOSUB 500:T$=T$+R$+" ":NEXT',
                "60 DATA " + ",".join(str(c) for c in codes))


CASES = {
    # one character per code: `.` = cursor (24,16) (a glyph), `c` = (16,16)
    # (ignored), anything else spelled out -- 128 codes per run (a whole
    # 0..255 sweep overflows a 255-character string: round 3's first ERR 15)
    "sweepLo": prog(2, "40 FOR C=0 TO 127:PSET(16,16),4:PRINT #1,CHR$(C);:GOSUB 510",
                    '45 IF X0=24 AND Y0=16 THEN T$=T$+"." ELSE IF X0=16 AND Y0=16 '
                    'THEN T$=T$+"c" ELSE T$=T$+"["+HEX$(C)+":":GOSUB 520:T$=T$+"]"',
                    "50 NEXT"),
    "sweepHi": prog(2, "40 FOR C=128 TO 255:PSET(16,16),4:PRINT #1,CHR$(C);:GOSUB 510",
                    '45 IF X0=24 AND Y0=16 THEN T$=T$+"." ELSE IF X0=16 AND Y0=16 '
                    'THEN T$=T$+"c" ELSE T$=T$+"["+HEX$(C)+":":GOSUB 520:T$=T$+"]"',
                    "50 NEXT"),
    "drawsA": draws((1, 7, 10, 12)),
    "drawsB": draws((27, 127, 255, 32)),
    "pair": prog(2, '40 PSET(8,8),4:PRINT #1,"A";CHR$(13);CHR$(10);:GOSUB 510:GOSUB 520',
                 '45 PSET(8,8),4:PRINT #1,"A";CHR$(10);CHR$(13);:GOSUB 510:GOSUB 520',
                 '50 PSET(8,8),4:PRINT #1,"A";CHR$(13);"B";:GOSUB 510:GOSUB 520'),
    "edges": prog(2, '40 PSET(240,8),4:PRINT #1,"A";:GOSUB 510:GOSUB 520',
                  '41 PSET(244,8),4:PRINT #1,"A";:GOSUB 510:GOSUB 520',
                  '42 PSET(248,184),4:PRINT #1,"A";:GOSUB 510:GOSUB 520',
                  '43 PSET(8,176),4:PRINT #1,"A";CHR$(13);:GOSUB 510:GOSUB 520',
                  '44 PSET(8,180),4:PRINT #1,"A";CHR$(13);:GOSUB 510:GOSUB 520'),
    # CHR$(1) is CHPUT's graphic-character header (CHR$(1)+CHR$(65) = glyph 1):
    # does GRP: honour it? cursor after, and the cell the "A" lands in
    "header": prog(2, '40 PSET(16,16),4:PRINT #1,CHR$(1);"A";:GOSUB 510:GOSUB 520',
                   "45 CX=16:CY=16:GOSUB 500:T$=T$+R$"),
    "scr3edge": prog(3, '40 PSET(220,8),4:PRINT #1,"A";:GOSUB 510:GOSUB 520',
                     '41 PSET(224,8),4:PRINT #1,"A";:GOSUB 510:GOSUB 520', s=4),
}
RX = re.compile(r"<[^<>]*>")


def main():
    only = sys.argv[1:]
    for name, lines in CASES.items():
        if only and name not in only:
            continue
        raw = omsx_repl.run_cases(REF, [("direct", ["NEW"] + lines + ["RUN"])],
                                  batch=False, reset=("", "SCREEN 0"),
                                  run_gap=60.0)[0] or ""
        flat = raw.replace("\n", "")
        run = flat[flat.rfind("RUN") + 3:] if "RUN" in flat else flat
        hits = RX.findall(run)
        print(f"{name:9s} {re.sub(' +', ' ', hits[-1]) if hits else 'NONE: ' + run[-80:]}",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
