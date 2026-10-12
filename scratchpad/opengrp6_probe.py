#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-OPENGRP round 6: what the CHR$(1) header does with the byte after it.
The gate's sweep found it: CHR$(1) then CHR$(2) draws NOTHING on the VG-8020
(zerobas drew glyph 2-64). Font-free: each glyph is compared with a cell drawn
on the SAME machine (POINT bits), never across machines.
Clean room: typed BASIC and POINT; the cursor from GRPACX/GRPACY.

  h2    CHR$(1);CHR$(2)       cursor
  h48   CHR$(1);"0"           cursor; is the cell glyph 240 (=48-64), or blank?
  h2A   CHR$(1);CHR$(2);"A"   is the cell "A" (header consumed) or glyph 1?
  h13   CHR$(1);CHR$(13)      cursor (a new line, or nothing?)
  h255  CHR$(1);CHR$(255)     cursor; is the cell glyph 191 (=255-64)?

Prediction: h2 ignored (16,16); h48 glyph 240, +8; h2A plain "A" (the control
consumes the header); h13 a new line (0,72); h255 glyph 191, +8.
FIRST RUN (VG-8020): h2 / h2A / h13 HIT; h48 and h255 each draw a glyph (+8) that
is NEITHER byte-64 NOR blank -- MISS. So round 6b (the `which` row) compares
them with the other candidates: byte AND 31 (glyph 16 / 31, drawn through
CHR$(1)+CHR$(64+g), where every candidate rule agrees), byte AND 63, and the
byte itself (the header ignored). (The first run's parser also looked for
"RUN", which had scrolled off: fixed.)
6b on the VG-8020: w48=01, w255=001 -- the header is IGNORED there and the byte
draws itself. 6c checks the range's edges (63, 96): predicted plain both.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
P = ["10 CLEAR 1000:ON ERROR GOTO 90", "20 SCREEN 2:COLOR 15,4:CLS",
     '30 OPEN"GRP:"FOR OUTPUT AS #1',
     "40 PSET(16,16),4:PRINT #1,CHR$(1);CHR$(2);:GOSUB 510",
     '41 PSET(16,32),4:PRINT #1,CHR$(1);"0";:GOSUB 510',
     '42 PSET(16,48),4:PRINT #1,CHR$(1);CHR$(2);"A";:GOSUB 510',
     "43 PSET(16,64),4:PRINT #1,CHR$(1);CHR$(13);:GOSUB 510",
     "44 PSET(16,80),4:PRINT #1,CHR$(1);CHR$(255);:GOSUB 510",
     '45 PSET(100,100),4:PRINT #1,"A";:PSET(120,100),4:PRINT #1,CHR$(1);"A";',
     "46 PSET(140,100),4:PRINT #1,CHR$(240);:PSET(160,100),4:PRINT #1,CHR$(191);",
     "50 X=16:Y=48:GOSUB 600:A$=R$:X=100:Y=100:GOSUB 600:B$=R$:X=120:GOSUB 600:C$=R$",
     '51 T$=T$+" 2A="+MID$(STR$(-(A$=B$)),2)+MID$(STR$(-(A$=C$)),2)',
     "52 X=16:Y=32:GOSUB 600:A$=R$:X=140:Y=100:GOSUB 600",
     '53 T$=T$+" 48="+MID$(STR$(-(A$=R$)),2)+MID$(STR$(-(A$=STRING$(16,"0"))),2)',
     "54 X=16:Y=80:GOSUB 600:A$=R$:X=160:Y=100:GOSUB 600",
     '55 T$=T$+" 255="+MID$(STR$(-(A$=R$)),2)',
     # 6b: which glyph? cells at y=120: g16 g31 '0'(48) ?(63) 255, via the header
     # for 0..31 (CHR$(1)+CHR$(64+g): every candidate rule agrees there)
     '56 PSET(0,120),4:PRINT #1,CHR$(1);CHR$(80);:PSET(20,120),4:PRINT #1,CHR$(1);CHR$(95);',
     '57 PSET(40,120),4:PRINT #1,"0";:PSET(60,120),4:PRINT #1,"?";:PSET(80,120),4:PRINT #1,CHR$(255);',
     '58 X=16:Y=32:GOSUB 600:H$=R$:X=0:Y=120:GOSUB 600:K$=R$:X=40:GOSUB 600:L$=R$',
     '59 T$=T$+" w48="+MID$(STR$(-(H$=K$)),2)+MID$(STR$(-(H$=L$)),2)',
     '60 X=16:Y=80:GOSUB 600:H$=R$:X=20:Y=120:GOSUB 600:K$=R$:X=60:GOSUB 600:L$=R$',
     '61 X=80:GOSUB 600:T$=T$+" w255="+MID$(STR$(-(H$=K$)),2)+MID$(STR$(-(H$=L$)),2)+MID$(STR$(-(H$=R$)),2)',
     # 6c: the range's edges -- header + 63 and + 96 against the plain glyph
     '62 PSET(0,140),4:PRINT #1,CHR$(1);"?";:PSET(20,140),4:PRINT #1,"?";',
     '63 PSET(40,140),4:PRINT #1,CHR$(1);CHR$(96);:PSET(60,140),4:PRINT #1,CHR$(96);',
     '64 X=0:Y=140:GOSUB 600:H$=R$:X=20:GOSUB 600:T$=T$+" e63="+MID$(STR$(-(H$=R$)),2)',
     '65 X=40:GOSUB 600:H$=R$:X=60:GOSUB 600:T$=T$+" e96="+MID$(STR$(-(H$=R$)),2)',
     '70 SCREEN 0:PRINT"<";T$;">":END',
     '90 SCREEN 0:PRINT"<E";ERR;ERL;">":END',
     '510 T$=T$+MID$(STR$(PEEK(&HFCB7)+256*PEEK(&HFCB8)),2)+","+'
     'MID$(STR$(PEEK(&HFCB9)+256*PEEK(&HFCBA)),2)+" ":RETURN',
     '600 R$="":FOR J=0 TO 7:B=0:FOR I=0 TO 7:B=B*2-(POINT(X+I,Y+J)=15):NEXT',
     '610 R$=R$+RIGHT$("0"+HEX$(B),2):NEXT:RETURN']


def main():
    for m in MACHINES:
        raw = omsx_repl.run_cases(m, [("direct", ["NEW"] + P + ["RUN"])], batch=False,
                                  reset=("", "SCREEN 0"), run_gap=60.0)[0] or ""
        flat = raw.replace("\n", "")
        hits = re.findall(r"<[^<>]*>", flat[flat.rfind("RUN"):] if "RUN" in flat else flat)
        print(f"{m:30s} {re.sub(' +', ' ', hits[-1]) if hits else 'NONE'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
