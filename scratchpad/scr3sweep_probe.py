#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSRUNG (3), the graphics-cursor family in SCREEN 3 (mapxyc3_run.out found MAPXYC
taking BLOCK coordinates there on the VG-8020, pixels on zerobas). The rest of the family,
called DIRECTLY in SCREEN 3: the six moves (CLOC / CMASK POKEd, F captured), SETC / READC
on a known pattern byte, NSETCX, and MAPXYC at the grid's edges. VRAM is read BEFORE
SCREEN 0. Reuses biossweep_probe's stubs. Black-box: registers, work-area RAM, VRAM.

    python3 -u scratchpad/scr3sweep_probe.py [ROW ...]
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import biossweep_probe as S        # noqa: E402  (prog_f, SHOWC, B with read2)

B = S.B
SHOWC = S.SHOWC
AFTER = f'SCREEN 0:PRINT "[C";{SHOWC};"]"'


def at(cloc, cmask, scr=3):
    return (f"SCREEN {scr}:POKE &HF92A,{cloc & 255}:POKE &HF92B,{cloc >> 8}:"
            f"POKE &HF92C,{cmask}")


def mv(addr, cloc, cmask, scr=3):
    return S.prog_f(addr, 0, before=at(cloc, cmask, scr), after=AFTER)


RC, LC, UC, TUC, DC, TDC = 0x00FC, 0x00FF, 0x0102, 0x0105, 0x0108, 0x010B
ROWS = {
    # RIGHTC / LEFTC: the left block ($F0) and the right one ($0F); the screen's edges
    "rc_l":     mv(RC, 0x0108, 0xF0),
    "rc_r":     mv(RC, 0x0108, 0x0F),
    "rc_edge":  mv(RC, 0x00F8, 0x0F),     # x block 63, row 0: the right edge
    "lc_l":     mv(LC, 0x0108, 0xF0),
    "lc_r":     mv(LC, 0x0108, 0x0F),
    "lc_edge":  mv(LC, 0x0000, 0xF0),     # x block 0
    # UPC / DOWNC / TUPC / TDOWNC: inside a cell's 8 bytes, across the cell (256 apart),
    # and at the top / bottom of the screen (y block 0 / 47 = $500 + 7)
    "uc_mid":   mv(UC, 0x010B, 0xF0),
    "uc_wrap":  mv(UC, 0x0108, 0xF0),
    "uc_top":   mv(UC, 0x0008, 0xF0),
    "tuc_mid":  mv(TUC, 0x010B, 0xF0),
    "tuc_wrap": mv(TUC, 0x0108, 0xF0),
    "tuc_top":  mv(TUC, 0x0008, 0xF0),
    "dc_mid":   mv(DC, 0x010B, 0xF0),
    "dc_wrap":  mv(DC, 0x010F, 0xF0),
    "dc_bot":   mv(DC, 0x050F, 0xF0),
    "tdc_mid":  mv(TDC, 0x010B, 0xF0),
    "tdc_wrap": mv(TDC, 0x010F, 0xF0),
    "tdc_bot":  mv(TDC, 0x050F, 0xF0),
    # ROUND 2: F after RIGHTC / LEFTC in SCREEN 2 (never captured there): inside a byte
    # and on the wrap
    "s2_rc_mid":  mv(RC, 0x0108, 0x10, 2),
    "s2_rc_wrap": mv(RC, 0x0108, 0x01, 2),
    "s2_lc_mid":  mv(LC, 0x0108, 0x10, 2),
    "s2_lc_wrap": mv(LC, 0x0108, 0x80, 2),
}

# SETC / READC on the pattern byte at $108 = $4C (left block 4, right block C)
SET = at(0x0108, 0xF0) + ":VPOKE &H108,&H4C"
SHOWP = 'P=VPEEK(&H108):SCREEN 0:PRINT "[C";HEX$(P);"]"'
ROWS.update({
    "setc_l":   B.prog(0x0120, 0, before=SET + ":POKE &HF3F2,9", after=SHOWP),
    "setc_r":   B.prog(0x0120, 0, before=SET + ":POKE &HF92C,15:POKE &HF3F2,9", after=SHOWP),
    "readc_l":  B.prog(0x011D, 0, before=SET, after="SCREEN 0"),
    "readc_r":  B.prog(0x011D, 0, before=SET + ":POKE &HF92C,15", after="SCREEN 0"),
    # NSETCX: 5 blocks from the right block of $108 (crosses into $110 and $118)
    "nsetcx":   B.prog(0x0123, 0, hl=5, before=at(0x0108, 0x0F) + ":VPOKE &H108,0:VPOKE &H110,0:"
                       "VPOKE &H118,0:POKE &HF3F2,9",
                       after='P=VPEEK(&H108):Q=VPEEK(&H110):R=VPEEK(&H118):SCREEN 0:'
                             f'PRINT "[C";HEX$(P);" ";HEX$(Q);" ";HEX$(R);" ";{SHOWC};"]"'),
})

# MAPXYC at the grid's corners and one past (the VG-8020: blocks 0..63 x 0..47)
SHOWM = S.SHOWM
ZG = S.ZG.replace("SCREEN 2", "SCREEN 3")
ROWS.update({
    "mxy_63_47": B.prog(0x0111, 0, bc=63, de=47, before=ZG, after=SHOWM),
    "mxy_1_1":   B.prog(0x0111, 0, bc=1, de=1, before=ZG, after=SHOWM),
    "mxy_25_27": B.prog(0x0111, 0, bc=25, de=27, before=ZG, after=SHOWM),
})


def main():
    only = sys.argv[1:] or list(ROWS)
    bad = []
    for name in only:
        got = {side: B.read(m, ROWS[name]) for side, m in B.MACHINES}
        v = "NO-REFERENCE" if not got["VG"] else ("SAME" if got["VG"] == got["ZB"] else "DIVERGES")
        if v != "SAME":
            bad.append(name)
        print(f"ROW {name:9} VG=[{got['VG']}] ZB=[{got['ZB']}] {v}", flush=True)
    print(f"\n{len(only) - len(bad)} SAME, {len(bad)} not ({', '.join(bad)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
