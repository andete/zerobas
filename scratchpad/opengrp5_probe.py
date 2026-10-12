#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-OPENGRP, measurement round 5: the CHANNEL around a GRP: device -- what
every FCH_MODES consumer must do with it. VG-8020 only (zerobas has no GRP:
yet). Each case is a stored program under ON ERROR; the answer is printed in
SCREEN 0 between `<` `>`. Clean room: typed BASIC, PEEK of the channel's FCB
header through VARPTR(#n) (the documented FCB pointer), and the screen.

  hdr      VARPTR(#1)+0 (mode) and +4 (device) after OPEN"GRP:" -- the codes
           the FCB-header stamp must write (LPT $FE, CRT $FD, CAS $FF today)
  bare     OPEN"GRP:"AS #1 (no FOR): accepted? PRINT #1 works?
  input    INPUT #1,A$ on the GRP: OUTPUT channel -> which error
  linput   LINE INPUT #1,A$
  inputd   INPUT$(1,#1)
  eof      EOF(1)
  loc      LOC(1)
  lof      LOF(1)
  close    CLOSE #1 then PRINT #1 -> which error (the channel is gone)
  two      two GRP: channels at once (#1 and #2), PRINT to both
  num      PRINT #1,12;-3 -- numbers, their spaces: cursor after
  comma    PRINT #1,"A","B" -- the 14-column zone: cursor after
  scr1     PRINT #1 in SCREEN 0 is 5 (round 1); SCREEN 1 too? (`SCREEN 1`,
           OPEN, PRINT #1). An INPUT-side case that never returns reads NONE:
           a hang is an answer here, not an instrument fault.

Prediction: hdr mode 2 device $FC; bare accepted and works; input/linput/
inputd 55 (Input past end) or 52 (unsure); eof -1 or 0 (unsure); loc 0; lof 0;
close -> 52; two both work; num: "12 -3 " = 7 glyphs -> x+56 (" 12 -3 ": 7 ->
8 glyphs counting the leading space: unsure); comma -> x+8*14+8; scr1 5 at
PRINT #1.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

REF = "Philips_VG_8020"
CUR = '510 X0=PEEK(&HFCB7)+256*PEEK(&HFCB8):Y0=PEEK(&HFCB9)+256*PEEK(&HFCBA):RETURN'
ERR = '90 SCREEN 0:PRINT"<E";ERR;ERL;">":END'
OPEN = ['10 ON ERROR GOTO 90', '20 SCREEN 2', '30 OPEN"GRP:"FOR OUTPUT AS #1']


def out(expr):
    return f'70 SCREEN 0:PRINT"<";{expr};">":END'


CASES = {
    "hdr": OPEN + ['40 V=VARPTR(#1):M=PEEK(V):D=PEEK(V+4)', out("M;D"), ERR],
    "bare": ['10 ON ERROR GOTO 90', '20 SCREEN 2', '30 OPEN"GRP:"AS #1',
             '40 PSET(8,8),4:PRINT #1,"A";:GOSUB 510', out('"ok";X0;Y0'), ERR, CUR],
    "input": OPEN + ['40 INPUT #1,A$', out('"noerr"'), ERR],
    "linput": OPEN + ['40 LINE INPUT #1,A$', out('"noerr"'), ERR],
    "inputd": OPEN + ['40 A$=INPUT$(1,#1)', out('"noerr"'), ERR],
    "eof": OPEN + ['40 E=EOF(1)', out("E"), ERR],
    "loc": OPEN + ['40 E=LOC(1)', out("E"), ERR],
    "lof": OPEN + ['40 E=LOF(1)', out("E"), ERR],
    "close": OPEN + ['40 CLOSE #1:PRINT #1,"A"', out('"noerr"'), ERR],
    "two": OPEN + ['35 OPEN"GRP:"FOR OUTPUT AS #2',
                   '40 PSET(8,8),4:PRINT #1,"A";:PRINT #2,"B";:GOSUB 510',
                   out('"ok";X0;Y0'), ERR, CUR],
    "num": OPEN + ['40 PSET(0,8),4:PRINT #1,12;-3;:GOSUB 510', out("X0;Y0"), ERR, CUR],
    "comma": OPEN + ['40 PSET(0,8),4:PRINT #1,"A","B";:GOSUB 510', out("X0;Y0"), ERR, CUR],
    # the comma zone: does the GRP: channel's column ADVANCE? "A","B" read 16
    # glyphs (A + 14 spaces + B) -- also what a column stuck at 0 gives. "AB","C"
    # separates them: 15 (column advances) vs 17 (stuck at 0).
    "comma2": OPEN + ['40 PSET(0,8),4:PRINT #1,"AB","C";:GOSUB 510', out("X0;Y0"), ERR, CUR],
    "comma3": OPEN + ['40 PSET(0,8),4:PRINT #1,"A","B","C";:GOSUB 510', out("X0;Y0"), ERR, CUR],
    # the two rules "zone from CSRX" and "zone from column 0" COINCIDE while the
    # text cursor sits at column 1 (knife K-G2 went green): move CSRX ($F3DD,
    # published) to 11 first. CSRX rule -> 3 spaces (x 40); column 0 -> 14 (x 128)
    "commacsrx": OPEN + ['40 POKE &HF3DD,11:PSET(0,8),4:PRINT #1,"A","B";:GOSUB 510',
                         out("X0;Y0;PEEK(&HF3DD)"), ERR, CUR],
    "scr1": ['10 ON ERROR GOTO 90', '20 SCREEN 1', '30 OPEN"GRP:"FOR OUTPUT AS #1',
             '40 PRINT #1,"A"', out('"noerr"'), ERR],
}
RX = re.compile(r"<[^<>]*>")


def main():
    only = sys.argv[1:]
    for name, lines in CASES.items():
        if only and name not in only:
            continue
        raw = omsx_repl.run_cases(REF, [("direct", ["NEW"] + lines + ["RUN"])],
                                  batch=False, reset=("", "SCREEN 0"), run_gap=30.0)[0] or ""
        flat = raw.replace("\n", "")
        run = flat[flat.rfind("RUN") + 3:] if "RUN" in flat else flat
        hits = RX.findall(run)
        print(f"{name:7s} {re.sub(' +', ' ', hits[-1]) if hits else 'NONE: ' + run[-80:]}",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
