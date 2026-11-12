#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSRUNG (3): PNTINI / SCANR / SCANL ($0129 / $012C / $012F), PAINT's published
helpers, called DIRECTLY in SCREEN 2 -- VG-8020 against zerobas (whose three are still bare
`ret`s: the measurement comes first, Joost's plan builds them as sub-ROM tenants and later
moves PAINT onto them).

A border is drawn by BASIC (`LINE (100,40)-(100,70),15`, and a second one at x = 20 for
SCANL). Our own code: ATRBYT := the paint colour, MAPXYC (BC = x, DE = y) places the cursor,
PNTINI with A = the border colour, then SCANR or SCANL with B = the fill flag and DE = the
skip count; HL / DE / BC / A are stored. Before SCREEN 0 (which would wipe the graphics
VRAM) BASIC records CLOC / CMASK ($F92A / $F92C), BDRATR ($FCB2) and the pattern bytes of
row 55 from x = 16 to 111 (12 bytes). Black-box: registers, work-area RAM, VRAM.

    python3 -u scratchpad/paintbios_probe.py [ROW ...]
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import basic_probe_biosregs as B   # noqa: E402  (read, MACHINES)


def code(x, y, border, paint, entry, fill, skip):
    c = [0x3E, paint, 0x32, 0xF2, 0xF3,                  # ld a,paint / ld (ATRBYT),a
         0x01, x & 255, x >> 8, 0x11, y & 255, y >> 8,   # ld bc,x / ld de,y
         0xCD, 0x11, 0x01,                               # call MAPXYC
         0x3E, border, 0xCD, 0x29, 0x01,                 # ld a,border / call PNTINI
         0x06, fill, 0x11, skip & 255, skip >> 8,        # ld b,fill / ld de,skip
         0xCD, entry & 255, entry >> 8,                  # call SCANR / SCANL
         0x22, 0x00, 0xD1, 0xED, 0x53, 0x02, 0xD1,       # ld ($D100),hl / ld ($D102),de
         0xED, 0x43, 0x04, 0xD1, 0x32, 0x06, 0xD1,       # ld ($D104),bc / ld ($D106),a
         0xC9]
    return c


def code2(x, y, col):
    # first: as code() with SCANR, fill, DE = 0 -- minus its stores and ret; then MAPXYC
    # again and SCANR with B = 1, DE = 5; the stores and ret
    c = code(x, y, col, col, 0x012C, 1, 0)[:-15]
    c += [0x01, x & 255, x >> 8, 0x11, y & 255, y >> 8, 0xCD, 0x11, 0x01,
          0x06, 1, 0x11, 5, 0, 0xCD, 0x2C, 0x01]
    return c + code(x, y, col, col, 0x012C, 1, 0)[-15:]


# the row's pattern bytes: row 55 lives in char row 6 (y // 8), line 7 (y % 8); byte for
# x is (y//8)*256 + (x//8)*8 + y%8
ROWB = ",".join(f"&H{(55 // 8) * 256 + (x // 8) * 8 + 55 % 8:X}" for x in range(16, 112, 8))


# ROUND 4: SCREEN 3 (multicolour) -- each pattern byte two 4x4 blocks; byte for (x, y) is
# (y//32)*256 + (x//8)*8 + (y//4)%8
ROWB3 = ",".join(f"&H{(55 // 32) * 256 + (x // 8) * 8 + (55 // 4) % 8:X}" for x in range(16, 112, 8))


# ROUND 5: SCREEN 3 in BLOCK coordinates (MAPXYC takes blocks there, mapxyc3_run.out):
# the borders at pixel x 20 / 100 are blocks 5 / 25, y 40..70 blocks 10..17; the cursor at
# block (12, 13); the window is block row 13, blocks 4..27 (12 bytes, two blocks each)
ROWB3B = ",".join(f"&H{(13 // 8) * 256 + (bx // 2) * 8 + 13 % 8:X}" for bx in range(4, 28, 2))


def prog(c, extra="", scr=2, win=None, lc=15):
    n = len(c)
    rd = ('C=PEEK(&HF92A)+256*PEEK(&HF92B):M=PEEK(&HF92C):D=PEEK(&HFCB2):V$="":'
          f'FOR I=0 TO 11:READ A:V$=V$+RIGHT$("0"+HEX$(VPEEK(A)),2):'
          f'W$=W$+RIGHT$("0"+HEX$(VPEEK(A+&H2000)),2):NEXT')   # ROUND 3: the colour table too
    return ["NEW",
            f"10 CLEAR 200,&HCFFF:SCREEN {scr}:LINE (100,40)-(100,70),{lc}:LINE (20,40)-(20,70),{lc}{extra}",
            f"20 FOR I=0 TO {n - 1}:READ X:POKE &HD000+I,X:NEXT",
            "30 DEFUSR=&HD000:Q=USR(0):" + rd,
            '40 SCREEN 0:S$="":FOR I=0 TO 3:S$=S$+" "+HEX$(PEEK(&HD101+2*I)*256+PEEK(&HD100+2*I)):NEXT',
            '50 PRINT"[R";S$;"]":PRINT"[C";HEX$(C);" ";HEX$(M);" ";HEX$(D);"]":PRINT"[C ";V$;"]":PRINT"[C ";W$;"]"',
            "60 DATA " + ",".join(str(b) for b in c),
            "70 DATA " + (win or (ROWB3 if scr == 3 else ROWB)),
            "RUN"]


ROWS = {
    # PNTINI + SCANR from x = 50, filling (B = 1), no skip
    "scanr_fill":   prog(code(50, 55, 15, 4, 0x012C, 1, 0)),
    # the same without filling (B = 0): the count only?
    "scanr_nofill": prog(code(50, 55, 15, 4, 0x012C, 0, 0)),
    # SCANL from x = 50 towards the x = 20 border, filling
    "scanl_fill":   prog(code(50, 55, 15, 4, 0x012F, 1, 0)),
    # a skip count: DE = 5
    "scanr_skip5":  prog(code(50, 55, 15, 4, 0x012C, 1, 5)),
    # ROUND 2: paint colour = border colour 15 -- in SCREEN 2 PNTINI ignores A and BDRATR
    # takes the PAINT colour (paintbios_run.out), so this is the case PAINT makes
    "r15_fill":   prog(code(50, 55, 15, 15, 0x012C, 1, 0)),
    "r15_nofill": prog(code(50, 55, 15, 15, 0x012C, 0, 0)),
    "l15_fill":   prog(code(50, 55, 15, 15, 0x012F, 1, 0)),
    "l15_nofill": prog(code(50, 55, 15, 15, 0x012F, 0, 0)),
    "r15_skip5":  prog(code(50, 55, 15, 15, 0x012C, 1, 5)),
    # ROUND 3: SCANR TWICE from x = 50 -- fill, then a second scan with DE = 5 across the
    # now-painted run: what the skip count does (the regs are the SECOND call's)
    "r15_twice":  prog(code2(50, 55, 15)),
    # ROUND 4: SCREEN 3 -- PNTINI's A is the border there (paint 4, border 15)
    "s3_r_fill":  prog(code(50, 55, 15, 4, 0x012C, 1, 0), scr=3),
    "s3_r_nofill": prog(code(50, 55, 15, 4, 0x012C, 0, 0), scr=3),
    "s3_l_fill":  prog(code(50, 55, 15, 4, 0x012F, 1, 0), scr=3),
    # paint 4 is SCREEN 3's default BACKGROUND -- a fill does not show (paintbios_run4.out);
    # paint 9 instead
    "s3_r9_fill":   prog(code(50, 55, 15, 9, 0x012C, 1, 0), scr=3),
    "s3_r9_nofill": prog(code(50, 55, 15, 9, 0x012C, 0, 0), scr=3),
    "s3_l9_fill":   prog(code(50, 55, 15, 9, 0x012F, 1, 0), scr=3),
    # ROUND 5: block coordinates
    "b3_r_fill":    prog(code(12, 13, 15, 9, 0x012C, 1, 0), scr=3, win=ROWB3B),
    "b3_r_nofill":  prog(code(12, 13, 15, 9, 0x012C, 0, 0), scr=3, win=ROWB3B),
    "b3_l_fill":    prog(code(12, 13, 15, 9, 0x012F, 1, 0), scr=3, win=ROWB3B),
    "b3_r_skip3":   prog(code(12, 13, 15, 9, 0x012C, 1, 3), scr=3, win=ROWB3B),
    # ROUND 6: did B = 0 really fill in SCREEN 3? paint 7, B = 0 and B = 2
    "b3_r7_b0":     prog(code(12, 13, 15, 7, 0x012C, 0, 0), scr=3, win=ROWB3B),
    # ROUND 6: SCREEN 2 with paint = border = 9 (lines in 9): which nibble a whole-byte
    # fill writes (round 3's 0F could not tell, paint was 15)
    "r9_fill":      prog(code(50, 55, 9, 9, 0x012C, 1, 0), lc=9),
    "l9_fill":      prog(code(50, 55, 9, 9, 0x012F, 1, 0), lc=9),
    # ROUND 7: whole bytes whose foreground is NOT 0 (colour $C4 at x 56..95 of row 55)
    # ROUND 8: no border before the screen's edge -- SCANR from x 150 (right of the x 100
    # line), SCANL from x 10 (left of the x 20 line); SCREEN 3 the same in blocks
    "r9_edge":      prog(code(150, 55, 9, 9, 0x012C, 1, 0), lc=9),
    "l9_edge":      prog(code(10, 55, 9, 9, 0x012F, 1, 0), lc=9),
    "b3_r_edge":    prog(code(40, 13, 15, 9, 0x012C, 1, 0), scr=3, win=ROWB3B),
    "b3_l_edge":    prog(code(2, 13, 15, 9, 0x012F, 1, 0), scr=3, win=ROWB3B),
    "r9_fgc":       prog(code(50, 55, 9, 9, 0x012C, 1, 0), lc=9,
                         extra=":FOR I=&H263F TO &H265F STEP 8:VPOKE I,&HC4:NEXT"),
    "b3_r7_b2":     prog(code(12, 13, 15, 7, 0x012C, 2, 0), scr=3, win=ROWB3B),
}
for _n, _p in ROWS.items():                       # the POKE count FROM the bytes
    _data = _p[6].split(" ", 1)[1].split(",")
    assert f"TO {len(_data) - 1}:" in _p[2], _n


def main():
    for name in sys.argv[1:] or list(ROWS):
        got = {side: B.read(m, ROWS[name]) for side, m in B.MACHINES}
        verdict = "NO-REFERENCE" if not got["VG"] else (
            "SAME" if got["VG"] == got["ZB"] else "DIVERGES")
        print(f"ROW {name:13} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
