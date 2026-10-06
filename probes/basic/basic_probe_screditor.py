#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""screditor-acceptance — the screen editor's happy path (docs/spec-basic-screditor.md).

Keys are TYPED (the harness sends control bytes as text: `\x1e` = cursor up,
`\x1d` = cursor left), every row boots fresh, and every readout is a VARIABLE
printed from a fresh line -- never the glass, which a working re-entry leaves
byte-identical to none (D-EDITLINE).
    e.left    A=1, LEFT, 2, Enter -> A is 2 (the ROW was read, not a buffer)
    e.csr     a two-row logical line reading PRINT CSRLIN, re-entered from its
              first row (HOME, Enter): prints 2 -- the cursor was moved below
              the line's LAST row before it executed
    x.plain   the payload printed on row 6 by a program; HOME, DOWN x5, Enter
              -> A is 1 (re-entry executes)
    x.reenter a PRINT-wrapped apostrophe row above the payload, same keys -> 0
              (the wrapped row is part of the logical line, so the ' REMs it)
    x.vpoke   the same fill by VPOKE -> 1 (no continuation: the row alone)
    i.wrap    INPUT at the bottom row, a 45-char answer that wraps and scrolls
              -> 45, the prompt excluded (the start column survives the scroll)
    i.top     the same at the top -> 45
    s2.prompt after `SCREEN 2:END`, the next line reads PEEK(&HFCAF) -> 0: the
              prompt returns to SCREEN 0 (both references)
    s2.input  INPUT inside SCREEN 2 -> mode 0 and the answer read
    s2.long   a 46-char line typed after a SCREEN 2 program -> 46
    e.tab     `A$="AB` TAB `X"` -> LEN 5: TAB blanks to the next 8-column stop
    e.tabwrap 28 x on a WIDTH 40 row, TAB from the column-33 stop -> LEN 37:
              it blanks to the row's end and wraps (D-EDCTRL)
    e.ctrl*   CTRL-E/U/B/F/N edit the line they are typed into (D-EDCTRL)
    e.f1      F1 PRESSED (key matrix) during INPUT$(6) -> `color `
    e.f6      SHIFT+F1 with KEY 6,"Q6"+CHR$(13), during LINE INPUT -> Q6 (D-EDFKEY)
Expectations are the two references' faces, measured 2026-09-11 (and 09-07 for
the x.* rows); --survey shows their columns.
"""
from __future__ import annotations
import argparse, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides                                   # noqa: E402
UP, LEFT, HOME, DOWN, TAB = "\x1e", "\x1d", "\x0b", "\x1f", "\x09"
CB, CE, CF, CN, CU = "\x02", "\x05", "\x06", "\x0e", "\x15"   # CTRL-B/E/F/N/U
PAY = "A=A+1:PRINT A"
ANS = "x" * 45
# The re-entry rows build the screen FROM A PROGRAM and navigate with HOME +
# DOWN x n: zerobas prints a `ZB` prompt where the references print an `Ok`
# line, so a cursor-UP count from the prompt lands on different rows per
# machine; from HOME the row is the same everywhere. LOCATE 0,5 is 1-based row
# 6; VPOKE 160.. is row 5, the row above it.
T = 'T$="PRINT"+CHR$(34)+"[e.csr"+CHR$(34)+";CSRLIN;"+CHR$(34)+"]"+CHR$(34)'
CASES = [
    ("e.left",    ['WIDTH 40:CLS', 'A=1' + LEFT + '2', 'PRINT"[e.left";A;"]"']),
    # a two-row logical line whose text is PRINT CSRLIN: re-entered from its FIRST
    # row, it prints the row the cursor was moved to before executing
    ("e.csr",     ['10 WIDTH 40:CLS:' + T + ':PRINT STRING$(30," ");T$:END', 'RUN', HOME + '']),
    ("x.plain",   ['10 WIDTH 40:CLS:LOCATE 0,5:PRINT"' + PAY + '":END', 'RUN', HOME + DOWN * 5, 'PRINT"[x.plain";A;"]"']),
    ("x.reenter", ['10 WIDTH 40:CLS:LOCATE 0,4:PRINT STRING$(40,"\'");"' + PAY + '":END', 'RUN', HOME + DOWN * 5, 'PRINT"[x.reenter";A;"]"']),
    ("x.vpoke",   ['10 WIDTH 40:CLS:LOCATE 0,5:PRINT"' + PAY + '":FORI=0TO39:VPOKE160+I,39:NEXT:END', 'RUN', HOME + DOWN * 5, 'PRINT"[x.vpoke";A;"]"']),
    ("i.wrap",    ['10 WIDTH 40:FOR I=1 TO 23:PRINT:NEXT:INPUT A$:PRINT"[i.wrap";LEN(A$);LEFT$(A$,2);RIGHT$(A$,2);"]"', 'RUN', ANS]),
    ("i.top",     ['10 WIDTH 40:CLS:INPUT A$:PRINT"[i.top";LEN(A$);LEFT$(A$,2);"]"', 'RUN', ANS]),
    # after a graphics program the line is read in SCREEN 0 -- the prompt's and INPUT's
    ("s2.prompt", ['10 SCREEN 2:END', 'RUN', 'PRINT"[s2.prompt";PEEK(&HFCAF);"]"']),
    ("s2.input",  ['10 SCREEN 2:INPUT A$:PRINT"[s2.input";PEEK(&HFCAF);A$;"]"', 'RUN', 'xy']),
    ("s2.long",   ['10 SCREEN 2:END', 'RUN', 'A$="0123456789012345678901234567890123456789012345":PRINT"[s2.long";LEN(A$);"]"']),
    # D-EDCTRL (2026-10-05): TAB types spaces to the next 8-column stop. `A$="AB`
    # leaves the cursor on column 7, so TAB blanks 7..8 and X lands on 9: LEN 5.
    ("e.tab",     ['WIDTH 40:CLS', 'A$="AB' + TAB + 'X":PRINT"[e.tab";LEN(A$);"]"']),
    # ...and from a stop at column 33 it blanks to the row's end and WRAPS: the Y
    # is on a continuation row, still in the same string. 28 x + 8 blanks + Y.
    ("e.tabwrap", ['WIDTH 40:CLS', 'A$="' + "x" * 28 + TAB + 'Y":PRINT"[e.tabwrap";LEN(A$);"]"']),
    # D-EDCTRL part 2 (2026-10-05): the CTRL editing keys, each read back through
    # the line it edited. CTRL-E erases from the cursor to the line's end, then
    # ENTER at once -- the unterminated literal ends there. 🔴 The first cut kept
    # typing after the CTRL-E and was BLIND: the text typed next overwrote the
    # `DEF` tail anyway, so a dropped CTRL-E read `ABC` too (the hook knife).
    ("e.ctrle",   ['WIDTH 40:CLS', 'A$="ABCDEF' + LEFT * 3 + CE, 'PRINT"[e.ctrle";A$;"]"']),
    # CTRL-U erases the whole line: only what is typed after it runs
    ("e.ctrlu",   ['WIDTH 40:CLS', 'A$="JUNK' + CU + 'A$="OK":PRINT"[e.ctrlu";A$;"]"']),
    # CTRL-B to the previous word's start, overtype it, CTRL-N to the line's end
    ("e.ctrlb",   ['WIDTH 40:CLS', 'A$="AB CD' + CB + 'X' + CN + '":PRINT"[e.ctrlb";A$;"]"']),
    # CTRL-F from the first word to the next one, overtype, CTRL-N to the end
    ("e.ctrlf",   ['WIDTH 40:CLS', 'A$="AB CD' + LEFT * 5 + CF + 'X' + CN + '":PRINT"[e.ctrlf";A$;"]"']),
    # D-EDFKEY (2026-10-06): a PRESSED function key types its KEY string. These
    # rows press the key through the MATRIX (HOLDS below) -- typed text goes to
    # KEYBUF and could never reach the function-key decode. F1's default string
    # read by INPUT$(6); SHIFT+F1 = F6, redefined with a CR, read by LINE INPUT
    # through the screen editor.
    ("e.f1",      ['10 A$=INPUT$(6):PRINT"[e.f1";A$;"]"', 'RUN']),
    ("e.f6",      ['KEY 6,"Q6"+CHR$(13)', '10 LINE INPUT A$:PRINT"[e.f6";A$;"]"', 'RUN']),
]
# matrix keys held from the RUN: F1 = row 6 bit 5; SHIFT = row 6 bit 0
HOLDS = {"e.f1": (6, 0x20), "e.f6": ((6, 0x01), (6, 0x20))}
EXPECT = {"e.left": "2", "e.csr": "2", "x.plain": "1", "x.reenter": "0", "x.vpoke": "1",
          "i.wrap": "45 xxxx", "i.top": "45 xx",
          "s2.prompt": "0", "s2.input": "0 xy", "s2.long": "46",
          "e.tab": "5", "e.tabwrap": "37",
          "e.ctrle": "ABC", "e.ctrlu": "OK", "e.ctrlb": "AB XD", "e.ctrlf": "AB XD",
          "e.f1": "color", "e.f6": "Q6"}

def fence(tag, cap):
    """The printed `[tag ...]`, never the typed echo (an echo carries `";`)."""
    c = cap or ""; k = len(c)
    while True:
        i = c.rfind("[" + tag, 0, k)
        if i < 0: return None
        j = c.find("]", i + 1)
        if j > 0 and '";' not in c[i:j]: return " ".join(c[i + len(tag) + 1:j].split())
        k = i

def read(side, cfg):
    out = {}
    for tag, lines in CASES:
        hold = HOLDS.get(tag)
        # a TAP, not a hold: pressed once the program waits (hold_lead, after
        # run_gap) and released 0.4 s later -- a hold over the run_gap window
        # autorepeats the key's string down the screen
        kw = dict(holds=[hold], hold_secs=0.5, hold_lead=0.1) if hold else {}
        cap = omsx_repl.run_cases(cfg["machine"], [(tag, lines)], batch=False, boot=cfg["boot"],
                                  reset=cfg["reset"], run_gap=25.0, **kw)[0]
        out[tag] = fence(tag, cap)
    return out

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--survey", action="store_true"); a = ap.parse_args()
    sides = ("vg8020", "cf3300", "zb") if a.survey else ("zb",)
    cfg = probe_sides.sides(*sides)
    got = {s: read(s, cfg[s]) for s in sides}
    bad = []
    for tag, _ in CASES:
        g, w = got["zb"][tag], EXPECT[tag]
        ok = g == w
        bad += [] if ok else [tag]
        extra = f"  vg8020={got['vg8020'][tag]!r} cf3300={got['cf3300'][tag]!r}" if a.survey else ""
        print(f"  {'ok  ' if ok else 'DIFF'} {tag:9} zb={g!r:12} want={w!r}{extra}")
    print(f"{len(CASES)} rows, {len(bad)} diverge: {bad or 'none'}")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
