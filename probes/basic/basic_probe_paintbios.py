#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSRUNG (3), PNTINI / SCANR / SCANL ($0129 / $012C / $012F), PAINT's published BIOS
helpers, called DIRECTLY -- VG-8020 against zerobas (sub/paintbios.asm behind the page-0
stub in basic/biosfnk.asm).

Our own code: ATRBYT := the paint colour, MAPXYC (BC = x, DE = y) places the cursor, PNTINI
with A = the border colour, then SCANR or SCANL with B = the fill switch and DE = the skip
count; HL / DE / BC / A stored. BASIC then records CLOC / CMASK, BDRATR ($FCB2) and twelve
pattern bytes of the scanned row (SCREEN 2: their colour bytes too) before SCREEN 0.

Compared: HL (the count), DE (SCANR only -- SCANL's is a leftover), CLOC / CMASK, BDRATR,
the pattern window and, in SCREEN 2, the colour window. NOT compared: BC / A (the
VG-8020's leftovers, no documented contract) and SCREEN 3's +$2000 window (VRAM SCREEN 3
does not use). Black-box: registers, work-area RAM, VRAM.

    python3 -u probes/basic/basic_probe_paintbios.py [--gate] [ROW ...]

`make paintbios-acceptance` runs it; scratchpad/paintbios_probe.py is the development copy
(paintbios_run.out .. paintbios_run11.out). A side with no reading is an instrument fault (2).
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import basic_probe_biosregs as B   # noqa: E402  (read, MACHINES)

SCANR, SCANL = 0x012C, 0x012F


def code(x, y, border, paint, entry, fill, skip):
    return [0x3E, paint, 0x32, 0xF2, 0xF3,                  # ld a,paint / ld (ATRBYT),a
            0x01, x & 255, x >> 8, 0x11, y & 255, y >> 8,   # ld bc,x / ld de,y
            0xCD, 0x11, 0x01,                               # call MAPXYC
            0x3E, border, 0xCD, 0x29, 0x01,                 # ld a,border / call PNTINI
            0x06, fill, 0x11, skip & 255, skip >> 8,        # ld b,fill / ld de,skip
            0xCD, entry & 255, entry >> 8,                  # call SCANR / SCANL
            0x22, 0x00, 0xD1, 0xED, 0x53, 0x02, 0xD1,       # ld ($D100),hl / ld ($D102),de
            0xED, 0x43, 0x04, 0xD1, 0x32, 0x06, 0xD1,       # ld ($D104),bc / ld ($D106),a
            0xC9]


def code2(x, y, col):
    # SCANR filling from (x, y), then MAPXYC again and SCANR with B = 1, DE = 5 across
    # the now-painted run (the skip count); the second call's registers are stored
    c = code(x, y, col, col, SCANR, 1, 0)[:-15]
    c += [0x01, x & 255, x >> 8, 0x11, y & 255, y >> 8, 0xCD, 0x11, 0x01,
          0x06, 1, 0x11, 5, 0, 0xCD, 0x2C, 0x01]
    return c + code(x, y, col, col, SCANR, 1, 0)[-15:]


# SCREEN 2: row 55, x 16..111; SCREEN 3: block row 13, blocks 4..27
WIN2 = ",".join(f"&H{(55 // 8) * 256 + (x // 8) * 8 + 55 % 8:X}" for x in range(16, 112, 8))
WIN3 = ",".join(f"&H{(13 // 8) * 256 + (bx // 2) * 8 + 13 % 8:X}" for bx in range(4, 28, 2))


def prog(c, scr=2, lc=15, extra=""):
    rd = ('C=PEEK(&HF92A)+256*PEEK(&HF92B):M=PEEK(&HF92C):D=PEEK(&HFCB2):V$="":'
          'FOR I=0 TO 11:READ A:V$=V$+RIGHT$("0"+HEX$(VPEEK(A)),2):'
          'W$=W$+RIGHT$("0"+HEX$(VPEEK(A+&H2000)),2):NEXT')
    return ["NEW",
            f"10 CLEAR 200,&HCFFF:SCREEN {scr}:LINE (100,40)-(100,70),{lc}:"
            f"LINE (20,40)-(20,70),{lc}{extra}",
            f"20 FOR I=0 TO {len(c) - 1}:READ X:POKE &HD000+I,X:NEXT",
            "30 DEFUSR=&HD000:Q=USR(0):" + rd,
            '40 SCREEN 0:S$="":FOR I=0 TO 3:S$=S$+" "+HEX$(PEEK(&HD101+2*I)*256+PEEK(&HD100+2*I)):NEXT',
            '50 PRINT"[R";S$;"]":PRINT"[C";HEX$(C);" ";HEX$(M);" ";HEX$(D);"]":PRINT"[C ";V$;"]":PRINT"[C ";W$;"]"',
            "60 DATA " + ",".join(str(b) for b in c),
            "70 DATA " + (WIN3 if scr == 3 else WIN2),
            "RUN"]


# name -> (program, screen, entry)
ROWS = {
    # SCREEN 2, paint = border = 15 (the natural PAINT case): fill, no fill, SCANL, a skip
    # count, a second SCANR across the painted run
    "r15_fill":   (prog(code(50, 55, 15, 15, SCANR, 1, 0)), 2, SCANR),
    "r15_nofill": (prog(code(50, 55, 15, 15, SCANR, 0, 0)), 2, SCANR),
    "l15_fill":   (prog(code(50, 55, 15, 15, SCANL, 1, 0)), 2, SCANL),
    "r15_skip5":  (prog(code(50, 55, 15, 15, SCANR, 1, 5)), 2, SCANR),
    "r15_twice":  (prog(code2(50, 55, 15)), 2, SCANR),
    # paint 4 = the background: the start pixel IS border-coloured, DE runs negative
    "scanr_bg":   (prog(code(50, 55, 15, 4, SCANR, 1, 0)), 2, SCANR),
    # paint = border = 9: the whole-byte rule, also over a $C4 colour byte; the edges
    "r9_fill":    (prog(code(50, 55, 9, 9, SCANR, 1, 0), lc=9), 2, SCANR),
    "r9_fgc":     (prog(code(50, 55, 9, 9, SCANR, 1, 0), lc=9,
                        extra=":FOR I=&H263F TO &H265F STEP 8:VPOKE I,&HC4:NEXT"), 2, SCANR),
    "r9_edge":    (prog(code(150, 55, 9, 9, SCANR, 1, 0), lc=9), 2, SCANR),
    "l9_edge":    (prog(code(10, 55, 9, 9, SCANL, 1, 0), lc=9), 2, SCANL),
    # SCREEN 3 in blocks: PNTINI's A is the border; SCANR ignores B; the edges
    "b3_r_fill":  (prog(code(12, 13, 15, 9, SCANR, 1, 0), scr=3), 3, SCANR),
    "b3_r_b0":    (prog(code(12, 13, 15, 7, SCANR, 0, 0), scr=3), 3, SCANR),
    "b3_l_fill":  (prog(code(12, 13, 15, 9, SCANL, 1, 0), scr=3), 3, SCANL),
    "b3_r_edge":  (prog(code(40, 13, 15, 9, SCANR, 1, 0), scr=3), 3, SCANR),
    "b3_l_edge":  (prog(code(2, 13, 15, 9, SCANL, 1, 0), scr=3), 3, SCANL),
}
for _n, (_p, _s, _e) in ROWS.items():          # the POKE count FROM the bytes
    _data = _p[6].split(" ", 1)[1].split(",")
    assert f"TO {len(_data) - 1}:" in _p[2], _n


def fields(raw, scr, entry):
    """The compared fields of one reading, or None when it is not whole."""
    if not raw:
        return None
    segs = [s.strip(" []") for s in raw.split("|")]
    if len(segs) < 4 or not segs[0].startswith("R"):
        return None
    r = segs[0].split()
    if len(r) < 5:
        return None
    f = {"HL": r[1], "CUR": segs[1], "PAT": segs[2]}
    if entry == SCANR:
        f["DE"] = r[2]
    if scr == 2:
        f["COL"] = segs[3]
    return f


def main():
    args = [a for a in sys.argv[1:] if a != "--gate"]
    names = args or list(ROWS)
    bad = blind = 0
    for name in names:
        p, scr, entry = ROWS[name]
        raw = {side: B.read(m, p) for side, m in B.MACHINES}
        got = {side: fields(raw[side], scr, entry) for side in raw}
        if not got["VG"] or not got["ZB"]:
            verdict = "NO-READING"
            blind += 1
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES " + ",".join(k for k in got["VG"] if got["VG"][k] != got["ZB"].get(k))
            bad += 1
        print(f"ROW {name:11} VG=[{raw['VG']}] ZB=[{raw['ZB']}] {verdict}", flush=True)
    if blind:
        print("INSTRUMENT FAULT: a side gave no reading")
        return 2
    n = len(names)
    print(f"{'PASS' if not bad else 'FAIL'}: PNTINI / SCANR / SCANL against the VG-8020 ({n - bad}/{n})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
