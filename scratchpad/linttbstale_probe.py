#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LINTTBSTALE: after scrolls, can an older row carry a stale "continues"
mark that glues an unrelated row onto a line being re-entered?

Each case: a program builds the screen, ENDs, and the keys then move the
cursor onto a one-row statement `A=A+1` printed AFTER the scrolling, press
Enter there, and print A. If the line read is the row alone, A is 1; a stale
zero in the row ABOVE would prepend that row's text to the line read (it is a
row of `'` -- a REM -- so a glued read leaves A at 0).

  wrap_off   a PRINT that wraps at the top, then enough PRINTs to scroll it
             off the top, then `'''...` filling a row, then the payload row
  wrap_mid   the same with the wrap only half scrolled: it is still on screen,
             two rows above the payload row
  wrap_low   a wrap whose first row is the SECOND-TO-LAST one, a scroll, then
             the payload: the one geometry the old scroll's one-short LINTTB
             move can leave a stale zero in (read from the C-BIOS source)

Also the LINTTB flags of the three rows ending at the payload row.

    python3 -u scratchpad/linttbstale_probe.py
"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                   # noqa: E402

UP = "\x1e"
PAY = "A=A+1"
CASES = {
    # wrap at row 1, then 23 PRINTs: the wrap scrolls off; then a quote row and the payload
    "wrap_off": ['10 CLS:PRINT STRING$(41,"w");:FOR I=1 TO 24:PRINT I:NEXT:PRINT STRING$(30,"\'"):PRINT"' + PAY + '";:END'],
    "wrap_mid": ['10 CLS:FOR I=1 TO 18:PRINT I:NEXT:PRINT STRING$(41,"w");:PRINT:PRINT STRING$(30,"\'"):PRINT"' + PAY + '";:END'],
    # the geometry the old scroll's one-short LINTTB move can reach: a wrap
    # whose FIRST row is the second-to-last one, then a scroll. Its zero stays
    # put while the rows move up, so the wrap's SECOND row would read as
    # continuing into the next line -- the payload printed after it.
    "wrap_low": ['10 CLS:FOR I=1 TO 30:PRINT I:NEXT:LOCATE 0,CSRLIN-1:PRINT STRING$(41,"\'");:PRINT:PRINT"' + PAY + '";:END'],
}


def run(machine, lines):
    keys = ["RUN", UP * 2, 'PRINT"[R";A;"]"']
    raw = omsx_repl.run_cases(machine, [("d", ["NEW"] + lines + keys)], batch=False, reset=("CLS",),
                              run_gap=10.0)[0] or ""
    scr = re.sub(r"\s+", " ", raw)
    m = [h for h in re.findall(r"\[R([^\]]*)\]", scr) if '";' not in h]
    return " ".join(m[-1].split()) if m else None


def main():
    for case, lines in CASES.items():
        for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"):
            print(f"== {case:9} {mach:30} A = {run(mach, lines)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
