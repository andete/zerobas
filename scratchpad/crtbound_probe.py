#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""CRTCNT UNDER KEY ON -- the investigation (Joost 2026-11-10: "This needs further
investigation."): how does the VG-8020's console find its bottom row?

Each row is one direct statement, VG-8020 against zerobas (biossweep_probe.py's
runner): it sets the key line and CRTCNT ($F3B1), scrolls 30 numbered lines or
LOCATEs to the bottom, keeps CSRY ($F3DC, 1-based) and the first character of rows
22 / 23 (0-based, the name table at 0 in SCREEN 0 / WIDTH 40), puts CRTCNT back,
and prints them. Black box: the work area and VRAM only.

    python3 -u scratchpad/crtbound_probe.py [ROW ...]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import biossweep_probe as S  # noqa: E402

KEEP = 'Y=PEEK(&HF3DC):A=VPEEK(22*40):B=VPEEK(23*40):C=PEEK(&HF3B1):POKE &HF3B1,V:'
SHOW = 'PRINT:PRINT "[C";Y;A;B;C;"]"'
SCROLL = 'FOR I=1 TO 30:PRINT I:NEXT:'
ROWS = {
    "on_scroll":   'V=PEEK(&HF3B1):KEY ON:CLS:' + SCROLL + KEEP + SHOW,
    "off_scroll":  'V=PEEK(&HF3B1):KEY OFF:CLS:' + SCROLL + KEEP + SHOW,
    "on_crt20":    'V=PEEK(&HF3B1):KEY ON:CLS:POKE &HF3B1,20:' + SCROLL + KEEP + SHOW,
    "off_crt20":   'V=PEEK(&HF3B1):KEY OFF:CLS:POKE &HF3B1,20:' + SCROLL + KEEP + SHOW,
    "on_loc23":    'V=PEEK(&HF3B1):KEY ON:CLS:LOCATE 0,23:' + KEEP + SHOW,
    "off_loc23":   'V=PEEK(&HF3B1):KEY OFF:CLS:LOCATE 0,23:' + KEEP + SHOW,
    "on_crt20loc": 'V=PEEK(&HF3B1):KEY ON:CLS:POKE &HF3B1,20:LOCATE 0,22:' + KEEP + SHOW,
}
S.ROWS = {k: ["10 " + v, "RUN"] for k, v in ROWS.items()}   # prog shape: lines + RUN
if __name__ == "__main__":
    sys.exit(S.main())
