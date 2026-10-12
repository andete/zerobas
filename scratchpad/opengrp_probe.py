#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-OPENGRP, measure first: what does OPEN "GRP:" do on the VG-8020?

Each case is a stored program; whatever happens in SCREEN 2 is read back with
POINT and the graphic cursor (GRPACX $FCB7 / GRPACY $FCB9, published work-area
cells), then printed in SCREEN 0 between `<` `>`. ON ERROR catches the code and
line. Clean room: typed BASIC, POINT, PEEK of documented cells.

  glyph   SCREEN 2, PSET(8,8), PRINT #1,"A";  -> the 8x8 cell as bit rows, cursor
  crlf    the same with a CR/LF after the A   -> cursor only
  scr0    OPEN "GRP:" in SCREEN 0             -> error?
  back0   OPEN in SCREEN 2, SCREEN 0, PRINT #1 -> error?
  input   OPEN "GRP:" FOR INPUT               -> error?

Prediction: the VG-8020 draws the font glyph in the foreground colour at the
cursor and advances it 8 pixels; CR/LF moves to the next text line; the
SCREEN 0 cases raise an error (code unknown); zerobas fails every row.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

REF = "Philips_VG_8020"
OURS = os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
ERR = ['90 SCREEN 0:PRINT"<E";ERR;ERL;">":END']
READ = ['50 X0=PEEK(&HFCB7)+256*PEEK(&HFCB8):Y0=PEEK(&HFCB9)+256*PEEK(&HFCBA)',
        '60 R$="":FOR Y=8 TO 15:B=0:FOR X=8 TO 15:B=B*2-(POINT(X,Y)=15):NEXT',
        '65 R$=R$+RIGHT$("0"+HEX$(B),2):NEXT']
CASES = {
    "glyph": ["10 ON ERROR GOTO 90", "20 SCREEN 2:COLOR 15,4:CLS",
              '30 OPEN"GRP:"FOR OUTPUT AS #1', "40 PSET(8,8),4:PRINT #1,\"A\";"]
             + READ + ['70 SCREEN 0:PRINT"<";R$;X0;Y0;">":END'] + ERR,
    "crlf": ["10 ON ERROR GOTO 90", "20 SCREEN 2:COLOR 15,4:CLS",
             '30 OPEN"GRP:"FOR OUTPUT AS #1', "40 PSET(8,8),4:PRINT #1,\"A\""]
            + READ[:1] + ['70 SCREEN 0:PRINT"<";X0;Y0;">":END'] + ERR,
    "scr0": ["10 ON ERROR GOTO 90", '30 OPEN"GRP:"FOR OUTPUT AS #1',
             '40 PRINT #1,"A"', '70 PRINT"<OK>":END'] + ERR,
    "back0": ["10 ON ERROR GOTO 90", "20 SCREEN 2", '30 OPEN"GRP:"FOR OUTPUT AS #1',
              '40 SCREEN 0:PRINT #1,"A"', '70 PRINT"<OK>":END'] + ERR,
    "input": ["10 ON ERROR GOTO 90", "20 SCREEN 2", '30 OPEN"GRP:"FOR INPUT AS #1',
              '70 SCREEN 0:PRINT"<OK>":END'] + ERR,
}
RX = re.compile(r"<[^<>]*>")


def main():
    for name, lines in CASES.items():
        for m in (REF, OURS):
            raw = omsx_repl.run_cases(m, [("direct", ["NEW"] + lines + ["RUN"])],
                                      batch=False, reset=("", "SCREEN 0"),
                                      cap_gap=10.0)[0] or ""
            flat = re.sub(r"\s+", " ", raw)
            run = flat[flat.rfind(" RUN ") + 5:] if " RUN " in flat else flat
            hits = RX.findall(run)
            print(f"{name:6s} {m:30s} {hits[-1] if hits else 'NONE: ' + run[-80:]}",
                  flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
