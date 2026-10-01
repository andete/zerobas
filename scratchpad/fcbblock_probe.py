#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""S10.0 (spec-diskcode-eviction §6.6bc) -- does the CF-3300's per-channel 37 B
block behave like a BDOS FCB moved by BLOCK I/O?

The BASIC FCB's +1..+2 points into the disk work area (`$DEB5` measured), where
37 B blocks hold the typed name. If the disk ROM moves the 256 B record with
BDOS block I/O, the 37 B block should change only when a record FILLS (every
256 bytes written), while header +6 (the buffer position) moves on every byte.
If the block changes per byte, the inference is wrong and so is §6.6bc's
design.

Clean room: this PEEKs WORK-AREA RAM that holds DATA (the block holds the typed
file name, D-DUPOPEN), which is readable. It reads no ROM byte and no
RAM-resident code, and follows nothing.

Stages, cumulative bytes written with `PRINT#1,...;` (no CR/LF): 0, 1, 255,
256, 257, 512, 513. Each prints header +6 and the 37 bytes, as hex.
"""
import os, re, shutil, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

PROG = [
    "NEW",
    "10 CLEAR 400:OPEN\"S0.TXT\"FOR OUTPUT AS#1:V=VARPTR(#1):P=PEEK(V+1)+256*PEEK(V+2)",
    "20 GOSUB 100:PRINT#1,\"A\";:GOSUB 100:PRINT#1,STRING$(254,66);:GOSUB 100",
    "30 PRINT#1,\"C\";:GOSUB 100:PRINT#1,\"D\";:GOSUB 100",
    "40 PRINT#1,STRING$(255,69);:GOSUB 100:PRINT#1,\"F\";:GOSUB 100:CLOSE:END",
    "100 S$=\"\":FOR I=0 TO 36:S$=S$+RIGHT$(\"0\"+HEX$(PEEK(P+I)),2):NEXT",
    "110 PRINT\"[\";PEEK(V+6);S$;\"]\";:RETURN",
    "SCREEN 0:WIDTH 40:CLS:RUN",
]
STAGES = [0, 1, 255, 256, 257, 512, 513]


def main():
    tmp = tempfile.mkstemp(suffix=".dsk")[1]
    shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), tmp)
    raw = omsx_repl.run_cases("National_CF-3300", [("direct", PROG)], batch=False,
                              reset=("", "SCREEN 0"), boot=14.0, step=4.0,
                              cap_gap=150.0, diska=tmp, capture="screen")[0] or ""
    got = re.findall(r"\[\s*(\d+)\s*([0-9A-F]{74})\s*\]", raw)
    if len(got) != len(STAGES):
        print(f"INSTRUMENT FAULT: {len(got)} of {len(STAGES)} stages read")
        print(repr(raw))
        return 2
    prev = None
    print(f"{'bytes':>5} {'+6':>4}  37 B block (changed offsets vs previous stage)")
    for n, (pos, hx) in zip(STAGES, got):
        b = bytes.fromhex(hx)
        ch = [] if prev is None else [i for i in range(37) if b[i] != prev[i]]
        print(f"{n:5} {pos:>4}  {hx}  changed={ch}")
        prev = b
    return 0


if __name__ == "__main__":
    sys.exit(main())
