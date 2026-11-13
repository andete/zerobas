#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ROBOREG: what the disk ROM's $5C11 does, as a black box. ROBOCOP's boot code CALSLTs
it with A = $F1, BC = 0, DE = $8780, HL = $8680 on both machines (roboirq_run9.out). Our
own code here calls it the same way from Disk BASIC (an empty data disk in the drive),
with HL / DE moved to a $55-filled buffer at $C000 / $C100, and records AF / BC / DE / HL
out and every changed byte of $C000-$C2FF. Black-box: registers and RAM.

    DISKCORPUS_DIR=... python3 -u scratchpad/k5c11_probe.py [ROW ...]
"""
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402
import probe_tmp  # noqa: E402

MACHS = (("REF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK"))
if os.environ.get("K5_REF_ONLY"):
    MACHS = MACHS[:1]


def code(a, bc, de, hl):
    # di / fill $C000..$C2FF with $55 / regs / ld iy,$8700 / ld ix,$5C11 / call CALSLT /
    # push af / store HL DE BC / pop -> store AF / ei / ret
    c = [0x21, 0x00, 0xC0, 0x11, 0x01, 0xC0, 0x01, 0xFF, 0x02, 0x36, 0x55, 0xED, 0xB0,
         0x3E, a, 0x01, bc & 255, bc >> 8, 0x11, de & 255, de >> 8, 0x21, hl & 255, hl >> 8,
         0xFD, 0x21, 0x00, 0x87, 0xDD, 0x21, 0x11, 0x5C, 0xCD, 0x1C, 0x00,
         0xF5, 0x22, 0x00, 0xD2, 0xED, 0x53, 0x02, 0xD2, 0xED, 0x43, 0x04, 0xD2,
         0xE1, 0x22, 0x06, 0xD2, 0xFB, 0xC9]
    return c


def prog(c):
    return ["NEW", "10 CLEAR 200,&HCFFF",
            f"20 FOR I=0 TO {len(c) - 1}:READ X:POKE &HD000+I,X:NEXT",
            '30 DEFUSR=&HD000:Q=USR(0):S$="":FOR I=0 TO 3:S$=S$+" "+HEX$(PEEK(&HD201+2*I)*256+PEEK(&HD200+2*I)):NEXT',
            '40 N=0:F$="":FOR I=&HC000 TO &HC2FF:IF PEEK(I)<>&H55 THEN N=N+1:IF LEN(F$)<40 THEN F$=F$+HEX$(I-&HC000)+":"+HEX$(PEEK(I))+" "',
            "50 NEXT",
            '60 PRINT "[K";S$;" N";N;"]":PRINT "[F ";F$;"]"',
            "70 DATA " + ",".join(str(b) for b in c),
            "RUN"]


ROWS = {
    "game": prog(code(0xF1, 0x0000, 0xC100, 0xC000)),
    # ROUND 2: one input at a time
    "a00":  prog(code(0x00, 0x0000, 0xC100, 0xC000)),
    "a01":  prog(code(0x01, 0x0000, 0xC100, 0xC000)),
    "bc1":  prog(code(0xF1, 0x0001, 0xC100, 0xC000)),
    "bcff": prog(code(0xF1, 0x0302, 0xC100, 0xC000)),
    "dehl": prog(code(0xF1, 0x0000, 0xC280, 0xC040)),
}


def main():
    names = sys.argv[1:] or list(ROWS)
    src = os.path.join(os.environ["DISKCORPUS_DIR"], "empty.dsk")
    for side, mach in MACHS:
        for n in names:
            dsk = probe_tmp.tmp(f"k5c11_{side}.dsk")
            shutil.copyfile(src, dsk)
            raw = omsx_repl.run_cases(mach, [("direct", ROWS[n])], batch=False, diska=dsk,
                                      reset=("", "SCREEN 0", "NEW"), boot=14.0, step=3.0,
                                      run_gap=12.0)[0] or ""
            t = " ".join(raw.split())
            t = t[t.rfind("RUN"):]
            i, j = t.find("[K"), t.find("[F")
            print(f"{side} {n:6} {t[i:t.find(']', i) + 1] if i >= 0 else '<NO [K>'} "
                  f"{t[j:t.find(']', j) + 1] if j >= 0 else t[:160]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
