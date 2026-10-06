#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LINTTBWRAP: after a program PRINT that wraps on the BOTTOM row (and so
scrolls), does LINTTB still mark the wrapped row as continuing?

`PRINT STRING$(41,"a");` from the bottom row's column 1 (41 > every width
here, so it wraps once and scrolls), then the three LINTTB entries ending at
the cursor's row (CSRY, the bottom TEXT row -- NOT CRTCNT: the VG-8020's
function-key row makes CRTCNT a row longer than its text area) as flags (0 = the row continues, 1 = it ends a line) -- the
machines' row counts and countdown VALUES differ, zero/non-zero is the
semantics (docs/spec-basic-screditor.md §1). Then `re`: the cursor is moved UP
onto the wrapped row and Enter pressed on it, so the line read back is a
statement -- `A=1` + 38 spaces + `:A=A+1` across the two rows -- and A tells
whether both rows were read (2) or only the row under the cursor (... the
first row alone: 1).

    python3 -u scratchpad/linttbwrap_probe.py
"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                   # noqa: E402

FLAGS = ['10 CLS:FOR I=1 TO 30:PRINT:NEXT:PRINT STRING$(41,"a");',
         '20 C=PEEK(&HF3DC):DIM F(2):FOR I=0 TO 2:F(I)=-(PEEK(&HFBB2+C-3+I)<>0):NEXT',
         '30 PRINT:PRINT"R<";F(0);F(1);F(2);">#"', "RUN"]


def flags(machine):
    raw = omsx_repl.run_cases(machine, [("d", ["NEW"] + FLAGS)], batch=False, reset=("CLS",))[0] or ""
    scr = re.sub(r"\s+", " ", re.sub(r'"[^"\n]*"', "", raw))
    m = re.findall(r"R<([^>#]*)>#", scr)
    return " ".join(m[-1].split()) if m else None


def main():
    for m in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"):
        print(f"== {m:30} last three LINTTB flags: {flags(m)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
