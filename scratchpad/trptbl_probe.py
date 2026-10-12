#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""RAM usage (TIER 4): the VG-8020's trap table TRPTBL ($FC4C, 78 B) -- its
entry order, its state bits and what its address field points at -- so that
zerobas's ZTRAP (own layout, $E1D1, 54 B) can move INTO it in the reference's
own format (refwork_probe.out: zerobas never writes TRPTBL; the VG-8020 does).

Each case is a stored program that arms some traps, then PEEKs the 78 bytes
and the handler lines' addresses (walked from TXTTAB, $F676: [link][line no]
...), and prints them in SCREEN 0. TRPTBL is DATA in the work area -- clean
room allows reading it; no ROM byte, no RAM-resident code is read.

  idle     after RUN, nothing armed
  key      ON KEY GOSUB 100,200 : KEY(1) ON : KEY(2) STOP
  stop     ON STOP GOSUB 100 : STOP ON
  sprite   ON SPRITE GOSUB 100 : SPRITE ON
  strig    ON STRIG GOSUB 100,200 : STRIG(0) ON : STRIG(1) STOP
  interval ON INTERVAL=50 GOSUB 100 : INTERVAL ON
  ioff     ... INTERVAL ON then INTERVAL OFF
  pending  ON INTERVAL=1 GOSUB 100 : INTERVAL STOP, wait, read (event latched)

Prediction: 3-byte entries; order KEY 1-10 ($FC4C..), STOP, SPRITE, STRIG 0-4,
INTERVAL; byte 0 flags with ON = bit 0, STOP = bit 1, an event latched = bit 2;
bytes 1-2 the address of the handler line (its link field, little-endian).
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

REF = os.environ.get("TRPTBL_MACHINE", "Philips_VG_8020")
# 900: the 78 bytes as hex, 3 per group; 910: the addresses of lines 100 / 200
TAIL = ['900 T$="":FOR I=0 TO 77:T$=T$+RIGHT$("0"+HEX$(PEEK(&HFC4C+I)),2)',
        '905 IF I MOD 3=2 THEN T$=T$+" "',
        '906 NEXT',
        '910 A=PEEK(&HF676)+256*PEEK(&HF677)',
        '915 L=PEEK(A+2)+256*PEEK(A+3):IF L=100 THEN P1=A ELSE IF L=200 THEN P2=A',
        '916 N=PEEK(A)+256*PEEK(A+1):IF N<>0 THEN A=N:GOTO 915',
        '920 SCREEN 0:PRINT"<";HEX$(P1);" ";HEX$(P2);"|";T$;">":END',
        '100 RETURN', '200 RETURN']
CASES = {
    "idle": ["10 GOTO 900"],
    "key": ["10 ON KEY GOSUB 100,200:KEY(1) ON:KEY(2) STOP:GOTO 900"],
    "stop": ["10 ON STOP GOSUB 100:STOP ON:GOTO 900"],
    "sprite": ["10 ON SPRITE GOSUB 100:SPRITE ON:GOTO 900"],
    "strig": ["10 ON STRIG GOSUB 100,200:STRIG(0) ON:STRIG(1) STOP:GOTO 900"],
    "interval": ["10 ON INTERVAL=50 GOSUB 100:INTERVAL ON:GOTO 900"],
    "ioff": ["10 ON INTERVAL=50 GOSUB 100:INTERVAL ON:INTERVAL OFF:GOTO 900"],
    "pending": ["10 ON INTERVAL=1 GOSUB 100:INTERVAL STOP:FOR I=1 TO 300:NEXT:GOTO 900"],
}


def main():
    for name, body in CASES.items():
        raw = omsx_repl.run_cases(REF, [("direct", ["NEW", "5 CLEAR 500"] + body + TAIL + ["RUN"])],
                                  batch=False, reset=("", "SCREEN 0"), run_gap=30.0)[0] or ""
        flat = raw.replace("\n", "")
        run = flat[flat.rfind("RUN") + 3:] if "RUN" in flat else flat
        hits = re.findall(r"<[^<>]*>", run)
        print(f"{name:9s} {re.sub(' +', ' ', hits[-1]) if hits else 'NONE: ' + run[-60:]}",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
