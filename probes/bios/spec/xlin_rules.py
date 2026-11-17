#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/PINLIN.md's EXECUTABLE RULES (docs/spec-method.md §3a): PINLIN ($00AE), QINLIN ($00B4) and INLIN ($00B1),
from the keyed XLIN probe -- scratchpad/XLIN_run1.out (probes/bios/spec/xlin.asm documents the six calls, the typed
burst and the 29-byte record)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/PINLIN.md"
OUTPUTS = {"XL": ["stage", "hl", "f", "csrx", "csry", "buf", "row"]}
BUFM1 = 0xF55D                  # BUF ($F55E) − 1
# the six calls (xlin.asm): the call, the cursor at entry, the row's pre-written text, the typed keys
CALLS = [("PINLIN", 1, 3, b"", b"AB"), ("QINLIN", 1, 5, b"", b"CD"), ("PINLIN", 4, 7, b"XYZ", b"Q"),
         ("INLIN", 4, 9, b"XYZ", b"Q"), ("PINLIN", 1, 11, b"", b"AC"), ("PINLIN", 1, 13, b"XYZ", b"")]


def cases():
    t = open(os.path.join(ROOT, "scratchpad", "XLIN_run1.out")).read()
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        if len(b) < 1 + 29 * 6 + 1 or b[1 + 29 * 6] != 0xC3:
            sys.exit("FAIL: the XLIN block has no sentinel after six records")
        cs = []
        for i, (name, x, y, pre, typed) in enumerate(CALLS):
            r = b[1 + 29 * i: 30 + 29 * i]
            cs.append(NS(src="XL", id=f"XL {i + 1}", name=name, x=x, y=y, pre=pre, typed=typed, stage=b[0],
                         hl=r[0] | (r[1] << 8), f=r[2], csrx=r[3], csry=r[4], buf=list(r[5:17]), row=list(r[17:29])))
        out[who] = cs
    return out


def shown(c):
    """The row's text after the input: the pre-written cells, the prompt, then what was typed from the cursor."""
    if c.name == "QINLIN":
        return b"? " + c.typed
    return (c.pre + b" " * 12)[:c.x - 1] + c.typed if c.typed else c.pre


def buf_of(text):
    """BUF as recorded: the text, its terminating 0, then the spaces the reference leaves after it."""
    return list((text + b"\0" + b" " * 12)[:12])


S1 = "1. PINLIN ($00AE), QINLIN ($00B4), INLIN ($00B1): read a line"

RULES = [
    Rule("R-L-PIN", S1, "PINLIN returns the WHOLE screen line the cursor is on, from column 1 -- text that was on the "
         "line before the call included ('XYZ' + typed 'Q' gives 'XYZQ'; Enter alone over 'XYZ' gives 'XYZ'), with "
         "BS editing applied ('AB' BS 'C' gives 'AC') -- in BUF, terminated by 0.",
         lambda c: c.name == "PINLIN", lambda c: c.buf == buf_of(shown(c))),
    Rule("R-L-INLIN", S1, "INLIN returns only the text from the column the cursor was at when it was called ('XYZ' "
         "before the cursor, typed 'Q': 'Q').", lambda c: c.name == "INLIN", lambda c: c.buf == buf_of(c.typed)),
    Rule("R-L-QIN", S1, "QINLIN first prints '? ' and returns the text typed after it (the prompt not included).",
         lambda c: c.name == "QINLIN", lambda c: c.buf == buf_of(c.typed)),
    Rule("R-L-RET", S1, "All three return HL = BUF − 1 ($F55D) with the carry clear (Enter, not STOP), echo the line "
         "on the screen, and leave the cursor at column 1 of the next row.", lambda c: True,
         lambda c: (c.stage == 6 and c.hl == BUFM1 and c.f & 1 == 0 and (c.csrx, c.csry) == (1, c.y + 1)
                    and c.row == list((shown(c) + b" " * 12)[:12]))),
    Rule("R-L-F", S1, "The whole F on return (only the carry published): 18.", lambda c: True, lambda c: c.f == 0x18),
]


# ---- round 2: XLIN2A / XLIN2B (probes/bios/spec/xlin2_gen.py; scratchpad/XLIN2A_run1.out, XLIN2B_run1.out)
sys.path.insert(0, HERE)
import xlin2_gen as G  # noqa: E402

OUTPUTS["XL2"] = ["stage", "hl", "f", "csrx", "csry", "buf", "row"]
_cases1 = cases


def cases():                                     # noqa: F811
    out = _cases1()
    for p in "ab":
        t = open(os.path.join(ROOT, "scratchpad", f"XLIN2{p.upper()}_run1.out")).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            for c in G.decode(p, bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))):
                c.src, c.id, c.probe = "XL2", f"XL2{p.upper()} {c.idx}", p
                out[who].append(c)
    return out


def line_model(c):
    """The row after the input, and the line the reference returns: the screen row with the pre-written text, QINLIN's
    '? ' at the entry column and the typed keys over it (overtyping); read from column 1 for PINLIN -- and for INLIN when
    AUTFLG is set -- else from the entry column (after the prompt for QINLIN); trailing spaces dropped."""
    row = bytearray(b" " * 40)
    for col, txt in c.pre:
        row[col - 1:col - 1 + len(txt)] = txt
    x = c.x
    if c.name == "QINLIN":
        row[x - 1:x + 1] = b"? "
        x += 2
    row[x - 1:x - 1 + len(c.typed)] = c.typed
    start = 1 if c.name == "PINLIN" or (c.name == "INLIN" and c.autflg) else x
    text = bytes(row[start - 1:]).rstrip(b" ")
    return bytes(row), text, start


def buf_model(c):
    """BUF as recorded: the line, its 0, then the rest of the row read (spaces)."""
    row, text, start = line_model(c)
    return list((text + b"\0" + row[start - 1 + len(text) + 1:] + b"\xff" * 40)[:len(c.buf)])


for _r in RULES:
    _r.select = (lambda s: (lambda c: c.src == "XL" and s(c)))(_r.select)

S2 = "2. Round 2: where the line starts and ends (XLIN2A / XLIN2B)"

RULES += [
    Rule("R-L-START", S2, "INLIN and QINLIN read the SCREEN, not the keys typed: from the entry column -- Enter alone "
         "at column 1 over 'XYZ' gives 'XYZ'; 'Q' typed at column 4 over 'XYZWV' gives 'QV' (the text right of the "
         "cursor included); with a gap ('XYZ', cursor at 6) 'Q' -- and QINLIN prints '? ' AT the entry column (column 4 "
         "over 'XYZ': the row reads 'XYZ? R') and reads after it.",
         lambda c: c.src == "XL2" and c.name in ("INLIN", "QINLIN") and not c.autflg,
         lambda c: c.buf == buf_model(c) and c.row == list(line_model(c)[0][:12])),
    Rule("R-L-AUTFLG", S2, "With AUTFLG set ($FF), INLIN reads from column 1 like PINLIN ('XYZ' + 'Q' at column 4: "
         "'XYZQ'); PINLIN does so either way.", lambda c: c.src == "XL2" and c.autflg,
         lambda c: c.buf == buf_model(c) and c.row == list(line_model(c)[0][:12])),
    Rule("R-L-EDGES", S2, "PINLIN's line: leading spaces kept ('  XYZ' at columns 3-5, cursor at 6: '  XYZ'), inner "
         "spaces kept ('A B'; 'XYZ' and a 'W' at column 18: everything between), trailing spaces dropped ('A B  ' "
         "typed: 'A B'); an empty row gives an empty line; BUF holds the line, its 0, then the rest of the row.",
         lambda c: c.src == "XL2" and c.probe == "b", lambda c: c.buf == buf_model(c) and c.row == []),
    Rule("R-L-RET2", S2, "Each returns HL = BUF − 1 with the carry clear, and the cursor at column 1 of the next row -- "
         "on row 24 the screen scrolls and the cursor stays on row 24; each call's own STAGE byte shows it returned.",
         lambda c: c.src == "XL2",
         lambda c: ((c.hl, c.f & 1, c.csrx, c.csry) == (BUFM1, 0, 1, min(c.y + 1, 24)) and c.stage == c.idx)),
    Rule("R-L-F2", S2, "The whole F (not published) is 18 here too.", lambda c: c.src in ("XL2", "XL2C"),
         lambda c: c.f == 0x18),
]


# ---- the confirming pass: XLIN2C (xlin2_gen.py probe c; scratchpad/XLIN2C_run1.out)
OUTPUTS["XL2C"] = ["stage", "hl", "f", "csrx", "csry", "buf", "row", "xrows"]
_cases2 = cases


def cases():                                     # noqa: F811
    out = _cases2()
    t = open(os.path.join(ROOT, "scratchpad", "XLIN2C_run1.out")).read()
    for who, key in (("ref", "ref"), ("zb", "ours")):
        for c in G.decode("c", bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))):
            c.src, c.id, c.probe = "XL2C", f"XL2C {c.idx}", "c"
            c.xrows = {r: list(v) for r, v in c.xrows.items()}
            out[who].append(c)
    return out


def cells(text):
    return list((text + b" " * 12)[:12])


RULES += [
    Rule("R-L-QSCREEN", S2, "QINLIN too reads the SCREEN after its prompt: at column 1 over 'ABCDEF' with Enter alone it "
         "prints '? ' over 'AB' and returns 'CDEF' -- the cells after the prompt, not the keys typed (none).",
         lambda c: c.src == "XL2C" and c.name == "QINLIN",
         lambda c: (c.buf == list((b"CDEF\0" + b" " * 16)[:16]) and c.row == cells(b"? CDEF")
                    and c.xrows == {4: cells(b""), 23: cells(b""), 24: cells(b"")} and c.stage == 1)),
    Rule("R-L-SCROLL24", S2, "On row 24, Enter SCROLLS the screen: after 'AB' typed on row 24 the line read is 'AB', row "
         "23 holds 'AB', row 24 is blank, and the row above moved up (row 5's '? CDEF' is on row 4); the cursor is at "
         "column 1 of row 24.", lambda c: c.src == "XL2C" and c.name == "PINLIN",
         lambda c: (c.buf == list((b"AB\0" + b" " * 16)[:16]) and c.row == cells(b"")
                    and c.xrows == {4: cells(b"? CDEF"), 23: cells(b"AB"), 24: cells(b"")} and c.stage == 2)),
    Rule("R-L-RET3", S2, "Both return HL = BUF − 1 with the carry clear, the cursor at column 1 of the next row (of "
         "row 24 after the scroll).", lambda c: c.src == "XL2C",
         lambda c: (c.hl, c.f & 1, c.csrx, c.csry) == (BUFM1, 0, 1, min(c.y + 1, 24))),
]
