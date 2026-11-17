#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/CHPUT.md's EXECUTABLE RULES (docs/spec-method.md §3a). Each Rule is a sentence the
page states AND a check over the measured cases: the reference (the VG-8020) must satisfy every
case a rule selects, zerobas's failures are its differences. tools/spec_rules.py runs them and
renders the page's rule tables.

Evidence (both runs through probes/bios/biosl_run.py, NODISK row, SCREEN 0 width 40):
  XCH  scratchpad/XCH_run1.out   probes/bios/spec/xchput.asm   768 cases: v alone / after ESC /
       after the graphic prefix, from (row 10, col 20) on a Q between P and R
  X2   scratchpad/XCH2_run1.out  probes/bios/spec/xchput2.asm  groups G1..G6 (its header)
  X3   scratchpad/XCH3_run2.out  probes/bios/spec/xchput3.asm  groups G1..G6 (its header); run 1
       (XCH3_run1.out) is NOT used: it left the cursor display on, so a cell under the cursor read 255
Positions in the code are 0-based; csrx / csry are the BIOS's 1-based cells.
"""
import os
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import xchput_table as T1  # noqa: E402
import xchput2_table as T2  # noqa: E402
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/CHPUT.md"
SP, P, Q, R = 32, ord("P"), ord("Q"), ord("R")
PQR = [P, Q, R]
CORNERS = ((0, 0), (0, 39), (23, 0), (23, 39))
G2BYTES = (8, 29, 127, 28, 30, 31, 10, 13, 9, ord("A"))
G4OPS = ("ESC L", "ESC M", "ESC J", "ESC K", "ESC E", "ESC j", "ESC l", "12")


def _machine(b1, b2):
    out = []
    for n in range(768):
        x = b1[2 + 6 * n: 8 + 6 * n]
        out.append(NS(src="XCH", id=f"XCH {n}", mode=n // 256, v=n % 256, csrx=x[0], csry=x[1],
                      a=x[2], cells=list(x[3:6])))

    def g(off, size, i):
        return b2[4 + off + size * i: 4 + off + size * (i + 1)]
    for i in range(40):
        x = g(0, 42, i)
        out.append(NS(src="G1", id=f"X2 G1.{i:02}", c=i, csrx=x[0], csry=x[1], row=list(x[2:42])))
    for i in range(80):
        x = g(1680, 50, i)
        key, rest = divmod(i, 40)
        cn, bi = divmod(rest, 10)
        r0, c0 = CORNERS[cn]
        last = 22 if key else 23                    # the last TEXT row (0-based)
        out.append(NS(src="G2", id=f"X2 G2.{i:02}", key=key, row=r0, col=c0, s=min(r0, last),
                      last=last, byte=G2BYTES[bi], csrx=x[0], csry=x[1], col0=list(x[2:26]),
                      lt=list(x[26:50])))
    for i in range(64):
        x = g(5680, 5, i)
        out.append(NS(src="G3", id=f"X2 G3.{i:02}", kind=27 if i < 32 else 1, c=i % 32,
                      csrx=x[0], csry=x[1], cells=list(x[2:5])))
    for i in range(8):
        x = g(6000, 53, i)
        out.append(NS(src="G4", id=f"X2 G4.{i}", op=G4OPS[i], csrx=x[0], csry=x[1],
                      col0=list(x[2:50:2]), col38=list(x[3:50:2]), cells=list(x[50:53])))
    for i in range(512):
        x = g(6424, 2, i)
        out.append(NS(src="G5", id=f"X2 G5.{i:03}", kind="row" if i < 256 else "col", v=i % 256,
                      csrx=x[0], csry=x[1]))
    for i in range(512):
        x = g(7448, 4, i)
        out.append(NS(src="G6", id=f"X2 G6.{i:03}", kind="x" if i < 256 else "y", v=i % 256,
                      csrx=x[0], csry=x[1], fca9=x[2], fcaa=x[3]))
    return out


def _round3(b3):
    out = []
    for s in range(5):
        x = b3[4 + 12 * s: 16 + 12 * s]
        out.append(NS(src="X3G1", id=f"X3 G1.{s}", seq=s, cur=[(x[2 * i], x[2 * i + 1]) for i in range(6)]))
    for i in range(512):
        x = b3[64 + 2 * i: 66 + 2 * i]
        out.append(NS(src="X3G2", id=f"X3 G2.{i:03}", kind="x" if i < 256 else "y", v=i % 256,
                      csrsw=x[0], fcaa=x[1]))
    for i in range(6):
        x = b3[1088 + 8 * i: 1096 + 8 * i]
        out.append(NS(src="X3G3", id=f"X3 G3.{i}", wrapped=i < 3, byte=(8, 29, 127)[i % 3], csrx=x[0],
                      csry=x[1], c938=x[2], c939=x[3], c100=x[4], c101=x[5], lt9=x[6], lt10=x[7]))
    for i in range(32):
        x = b3[1136 + 26 * i: 1162 + 26 * i]
        key, rest = divmod(i, 16)
        cn, cmd = divmod(rest, 4)
        r0, c0 = CORNERS[cn]
        last = 22 if key else 23
        out.append(NS(src="X3G4", id=f"X3 G4.{i:02}", key=key, row=r0, col=c0, s=min(r0, last), last=last,
                      cmd="ABCD"[cmd], csrx=x[0], csry=x[1], col0=list(x[2:26])))
    for i in range(8):
        x = b3[1968 + 53 * i: 2021 + 53 * i]
        out.append(NS(src="X3G5", id=f"X3 G5.{i}", op=G4OPS[i], csrx=x[0], csry=x[1],
                      col0=list(x[2:50:2]), col38=list(x[3:50:2]), cells=list(x[50:53])))
    out.append(NS(src="X3G6", id="X3 G6.0", sent=27, a=b3[2392]))
    out.append(NS(src="X3G6", id="X3 G6.1", sent=1, a=b3[2393]))
    return out


def _block3(text, who):
    import re
    m = re.search(rf"CAP {who}\s*:\s*([0-9a-fA-F]+)", text)
    b = bytes.fromhex(m.group(1))
    b = b + bytes(2398 - len(b))
    if b[1] != 0xA5:
        sys.exit(f"FAIL: the XCHPUT3 {who} block is not complete")
    return b


def cases():
    t1 = open(os.path.join(ROOT, "scratchpad", "XCH_run1.out")).read()
    t2 = open(os.path.join(ROOT, "scratchpad", "XCH2_run1.out")).read()
    t3 = open(os.path.join(ROOT, "scratchpad", "XCH3_run2.out")).read()
    return {"ref": _machine(T1.block(t1, "ref"), T2.block(t2, "ref")) + _round3(_block3(t3, "ref")),
            "zb": _machine(T1.block(t1, "ours"), T2.block(t2, "ours")) + _round3(_block3(t3, "ours"))}


def xch(mode, vs):
    vs = set(vs)
    return lambda c: c.src == "XCH" and c.mode == mode and c.v in vs


def at(c, x, y, cells=None):
    return c.csrx == x and c.csry == y and (cells is None or c.cells == cells)


PRINTABLE = set(range(32, 127)) | set(range(128, 256))
NOP = set(range(0, 8)) | set(range(14, 28))
ESC_CMD = set(b"ABCDEHJKLMYjlxy")
LETTERS_DONE = lambda v: v not in ESC_CMD          # noqa: E731
FRESH_LT = [24 - r for r in range(24)]              # the table after a clear: 24, 23, ..., 1
S1 = "1. One byte, from mid-screen (row 11, column 21, on a Q between P and R)"
S2 = "2. One byte at the screen's corners (key line off and on)"
S3 = "3. ESC v"
S4 = "4. The line and screen edits, on a full screen"
S5 = "5. ESC Y's parameters"
S6 = "6. The graphic prefix, and pending state"
S7 = "7. LINTTB, the line-continuation table"
S8 = "8. ESC x / ESC y"
S0 = "0. The interface"


def g2(byte, col=None, at_last=None, at_top=None, key=None):
    def sel(c):
        return (c.src == "G2" and c.byte == byte and (col is None or c.col == col)
                and (at_last is None or (c.s == c.last) == at_last)
                and (at_top is None or (c.s == 0) == at_top) and (key is None or c.key == key))
    return sel


def scrolled(c):
    """the text rows moved up one: row 0's first cell holds what row 1's did ('b')"""
    return c.col0[0] == ord("b")


Y1_SEQ = ("ESC Y 1 '%' A B", "ESC Y '%' 1 A B", "ESC Y 1 1 '%' '%'", "1 ESC Y '%' '%' A", "ESC Y 1 A '%' B")
Y1_REF = ([(1, 1), (1, 1), (1, 1), (1, 6), (34, 6), (35, 6)],
          [(1, 6), (1, 6), (1, 6), (1, 6), (2, 6), (35, 6)],
          [(1, 6), (1, 6), (1, 6), (1, 24), (6, 24), (7, 24)],
          [(1, 24), (1, 24), (1, 24), (1, 6), (6, 6), (7, 6)],
          [(1, 6), (1, 6), (1, 6), (2, 6), (2, 6), (35, 6)])
# the key-line-on screen of X3 G5 before the edit: the fill's last row went to row 23 (0-based 22), the
# ESC Y clamp; row 24 holds the key line (its first cell 'c')
KB0 = [ord("a") + r for r in range(22)] + [ord("x"), ord("c")]
KB38 = [ord("a") + r for r in range(22)] + [ord("x"), SP]


def key_edit_ok(c):
    exp = {"ESC L": (KB0[:10] + [SP] + KB0[10:22] + [KB0[23]], KB38[:10] + [SP] + KB38[10:22] + [SP], (1, 11)),
           "ESC M": (KB0[:10] + KB0[11:23] + [SP, KB0[23]], KB38[:10] + KB38[11:23] + [SP, SP], (1, 11)),
           "ESC J": (KB0[:11] + [SP] * 12 + [KB0[23]], KB38[:10] + [SP] * 14, (21, 11)),
           "ESC K": (KB0, KB38[:10] + [SP] + KB38[11:], (21, 11)),
           "ESC l": (KB0[:10] + [SP] + KB0[11:], KB38[:10] + [SP] + KB38[11:], (21, 11))}
    for op in ("ESC E", "ESC j", "12"):
        exp[op] = ([SP] * 23 + [KB0[23]], [SP] * 24, (1, 1))
    e0, e38, cur = exp[c.op]
    return c.col0 == e0 and c.col38 == e38 and (c.csrx, c.csry) == cur


S9 = "9. Round 3: byte 1 inside ESC Y, the cursor cells, DEL wrapping, the edges, the key line"

RULES = [
    Rule("R-A", S0, "CHPUT returns A unchanged (the rung passes v in A and records the A returned).",
         lambda c: c.src == "XCH", lambda c: c.a == c.v),

    Rule("R-PRINT", S1, "A byte 32–126 or 128–255 is written at the cursor, which moves right.",
         xch(0, PRINTABLE), lambda c: at(c, 22, 11, [P, c.v, R])),
    Rule("R-NOP", S1, "Bytes 0–7 and 14–27 (incl. 1, the prefix, and 27, ESC, left pending) do nothing visible.",
         xch(0, NOP), lambda c: at(c, 21, 11, PQR)),
    Rule("R-RIGHT", S1, "28 moves the cursor right one; nothing is written.",
         xch(0, [28]), lambda c: at(c, 22, 11, PQR)),
    Rule("R-LEFT", S1, "8 (BS) and 29 move the cursor left one; nothing is written.",
         xch(0, [8, 29]), lambda c: at(c, 20, 11, PQR)),
    Rule("R-DEL", S1, "127 (DEL) moves left one and blanks the cell it moves onto (nothing shifts).",
         xch(0, [127]), lambda c: at(c, 20, 11, [SP, Q, R])),
    Rule("R-DOWN", S1, "10 (LF) and 31 move the cursor down one; nothing is written.",
         xch(0, [10, 31]), lambda c: at(c, 21, 12, PQR)),
    Rule("R-UP", S1, "30 moves the cursor up one.", xch(0, [30]), lambda c: at(c, 21, 10, PQR)),
    Rule("R-HOME", S1, "11 homes the cursor (row 1, column 1); nothing is written.",
         xch(0, [11]), lambda c: at(c, 1, 1, PQR)),
    Rule("R-CLEAR", S1, "12 homes the cursor and clears the screen (the whole screen: R-ED-CLEAR).",
         xch(0, [12]), lambda c: at(c, 1, 1, [SP, SP, SP])),
    Rule("R-CR", S1, "13 (CR) moves to column 1 of the same row.", xch(0, [13]), lambda c: at(c, 1, 11, PQR)),
    Rule("R-TAB", S1, "9 (TAB) writes spaces up to the next stop of 8 (columns 9, 17, 25, 33).",
         xch(0, [9]), lambda c: at(c, 25, 11, [P, SP, SP])),
    Rule("R-TAB-ALL", S1, "From column c (0–31, 0-based) a TAB writes spaces to column 8·(c//8 + 1); from 32 on, "
         "to the row's end, and the cursor goes to the next row's column 1.",
         lambda c: c.src == "G1",
         lambda c: (c.csrx, c.csry) == ((8 * (c.c // 8 + 1) + 1, 11) if c.c < 32 else (1, 12))
         and c.row == [ord("o") if (x < c.c or (c.c < 32 and x >= 8 * (c.c // 8 + 1))) else SP
                       for x in range(40)]),

    Rule("R-E-LEFT1", S2, "BS / 29 / DEL at column 1 go to column 40 of the row above; at the top-left they stay.",
         lambda c: g2(8, 0)(c) or g2(29, 0)(c) or g2(127, 0)(c),
         lambda c: (c.csrx, c.csry) == ((1, 1) if c.s == 0 else (40, c.s))),
    Rule("R-E-LEFT40", S2, "BS / 29 / DEL at column 40 move left one.",
         lambda c: g2(8, 39)(c) or g2(29, 39)(c) or g2(127, 39)(c),
         lambda c: (c.csrx, c.csry) == (39, c.s + 1)),
    Rule("R-E-PRINT40", S2, "A printable at column 40 wraps to the next row's column 1; on the last text row the "
         "screen scrolls up one instead.",
         g2(ord("A"), 39),
         lambda c: (c.csrx, c.csry) == (1, min(c.s + 1, c.last) + 1) and scrolled(c) == (c.s == c.last)),
    Rule("R-E-RIGHT40", S2, "28 at column 40 wraps to the next row's column 1; on the last text row it stays "
         "(no scroll).", g2(28, 39),
         lambda c: (c.csrx, c.csry) == ((40, c.s + 1) if c.s == c.last else (1, c.s + 2)) and not scrolled(c)),
    Rule("R-E-UP", S2, "30 moves up one; on the top row it stays.", g2(30),
         lambda c: (c.csrx, c.csry) == (c.col + 1, max(c.s, 1))),
    Rule("R-E-DOWN31", S2, "31 moves down one; on the last text row it stays (no scroll).", g2(31),
         lambda c: (c.csrx, c.csry) == (c.col + 1, min(c.s + 1, c.last) + 1) and not scrolled(c)),
    Rule("R-E-LF", S2, "LF moves down one; on the last text row the screen scrolls up one and the cursor stays.",
         g2(10), lambda c: (c.csrx, c.csry) == (c.col + 1, min(c.s + 1, c.last) + 1)
         and scrolled(c) == (c.s == c.last)),
    Rule("R-E-CR", S2, "CR goes to column 1 of the same row.", g2(13),
         lambda c: (c.csrx, c.csry) == (1, c.s + 1) and not scrolled(c)),
    Rule("R-E-TAB40", S2, "TAB at column 40 wraps like a printable (scrolling on the last text row).", g2(9, 39),
         lambda c: (c.csrx, c.csry) == (1, min(c.s + 1, c.last) + 1) and scrolled(c) == (c.s == c.last)),
    Rule("R-E-COL1", S2, "TAB and a printable at column 1 behave as mid-screen (column 9 / column 2).",
         lambda c: g2(9, 0)(c) or g2(ord("A"), 0)(c),
         lambda c: (c.csrx, c.csry) == ((9 if c.byte == 9 else 2), c.s + 1)),
    Rule("R-E-RIGHT1", S2, "28 at column 1 moves right one.", g2(28, 0),
         lambda c: (c.csrx, c.csry) == (2, c.s + 1)),
    Rule("R-KEYROW", S2, "With the key line on, the text rows are 1–23: the cursor never reaches row 24.",
         lambda c: c.src == "G2" and c.key == 1, lambda c: c.csry <= 23),

    Rule("R-ESC-ABCD", S3, "ESC A / B / C / D move the cursor up / down / right / left one, writing nothing.",
         xch(1, b"ABCD"), lambda c: (c.csrx, c.csry, c.cells) == {
             65: (21, 10, PQR), 66: (21, 12, PQR), 67: (22, 11, PQR), 68: (20, 11, PQR)}[c.v]),
    Rule("R-ESC-H", S3, "ESC H homes the cursor; nothing is written.", xch(1, b"H"), lambda c: at(c, 1, 1, PQR)),
    Rule("R-ESC-EJ", S3, "ESC E and ESC j home the cursor and clear the screen.", xch(1, b"Ej"),
         lambda c: at(c, 1, 1, [SP, SP, SP])),
    Rule("R-ESC-KJ", S3, "ESC K and ESC J erase from the cursor on (the cursor stays).", xch(1, b"KJ"),
         lambda c: at(c, 21, 11, [P, SP, SP])),
    Rule("R-ESC-l", S3, "ESC l erases the whole line; the cursor stays where it is.", xch(1, b"l"),
         lambda c: at(c, 21, 11, [SP, SP, SP])),
    Rule("R-ESC-LM", S3, "ESC L and ESC M move the cursor to column 1 (the line edits: R-ED-L, R-ED-M).",
         xch(1, b"LM"), lambda c: (c.csrx, c.csry) == (1, 11)),
    Rule("R-ESC-OTHER", S3, "ESC then any other byte (a control code, or a non-command printable) does nothing "
         "visible; ESC Y / x / y wait for their parameters.",
         lambda c: c.src == "XCH" and c.mode == 1 and c.v not in set(b"ABCDEHJKLMjl"),
         lambda c: at(c, 21, 11, PQR)),
    Rule("R-ESC-CTRL", S3, "After ESC, a control code (but 1) is swallowed and ends the escape: a following A is "
         "printed.", lambda c: c.src == "G3" and c.kind == 27 and c.c != 1,
         lambda c: at(c, 22, 11, [P, ord("A"), R])),
    Rule("R-ESC-1", S3, "After ESC, byte 1 still acts as the graphic prefix: ESC, 1, A writes $01.",
         lambda c: c.src == "G3" and c.kind == 27 and c.c == 1, lambda c: at(c, 22, 11, [P, 1, R])),

    Rule("R-ED-L", S4, "ESC L inserts a blank line at the cursor's row: the rows below move down one, the last "
         "drops off.", lambda c: c.src == "G4" and c.op == "ESC L",
         lambda c: c.col0 == [ord("a") + r for r in range(10)] + [SP] + [ord("a") + r for r in range(10, 23)]),
    Rule("R-ED-M", S4, "ESC M deletes the cursor's row: the rows below move up one, the last row is blank.",
         lambda c: c.src == "G4" and c.op == "ESC M",
         lambda c: c.col0 == [ord("a") + r for r in range(10)] + [ord("a") + r for r in range(11, 24)] + [SP]),
    Rule("R-ED-J", S4, "ESC J erases from the cursor to the screen's end.", lambda c: c.src == "G4" and c.op == "ESC J",
         lambda c: c.col0 == [ord("a") + r for r in range(11)] + [SP] * 13
         and c.col38 == [ord("a") + r for r in range(10)] + [SP] * 14),
    Rule("R-ED-K", S4, "ESC K erases from the cursor to the line's end.", lambda c: c.src == "G4" and c.op == "ESC K",
         lambda c: c.col0 == [ord("a") + r for r in range(24)]
         and c.col38 == [ord("a") + r for r in range(10)] + [SP] + [ord("a") + r for r in range(11, 24)]),
    Rule("R-ED-l", S4, "ESC l erases the cursor's whole line and nothing else.",
         lambda c: c.src == "G4" and c.op == "ESC l",
         lambda c: c.col0 == [ord("a") + r for r in range(10)] + [SP] + [ord("a") + r for r in range(11, 24)]
         and (c.csrx, c.csry) == (21, 11)),
    Rule("R-ED-CLEAR", S4, "12, ESC E and ESC j clear the whole screen (key line off).",
         lambda c: c.src == "G4" and c.op in ("12", "ESC E", "ESC j"),
         lambda c: c.col0 == [SP] * 24 and c.col38 == [SP] * 24 and (c.csrx, c.csry) == (1, 1)),

    Rule("R-Y-ROW", S5, "ESC Y's row byte r = 32..55 puts the cursor on row r − 31 (1-based).",
         lambda c: c.src == "G5" and c.kind == "row" and 32 <= c.v <= 55, lambda c: (c.csrx, c.csry) == (6, c.v - 31)),
    Rule("R-Y-ROWCLAMP", S5, "Any other row byte but 1 clamps to the last row (24).",
         lambda c: c.src == "G5" and c.kind == "row" and not 32 <= c.v <= 55 and c.v != 1,
         lambda c: (c.csrx, c.csry) == (6, 24)),
    Rule("R-Y-COL", S5, "ESC Y's column byte c = 32..71 puts the cursor in column c − 31 (1-based).",
         lambda c: c.src == "G5" and c.kind == "col" and 32 <= c.v <= 71, lambda c: (c.csrx, c.csry) == (c.v - 31, 6)),
    Rule("R-Y-COLCLAMP", S5, "Any other column byte but 1 clamps to column 40.",
         lambda c: c.src == "G5" and c.kind == "col" and not 32 <= c.v <= 71 and c.v != 1,
         lambda c: (c.csrx, c.csry) == (40, 6)),

    Rule("R-PFX-GRAPH", S6, "The prefix, then a byte 64–95, writes byte − 64 (graphic $00–$1F) and moves right.",
         xch(2, range(64, 96)), lambda c: at(c, 22, 11, [P, c.v - 64, R])),
    Rule("R-PFX-PLAIN", S6, "The prefix, then a byte 32–63 or 96–255 but 127, writes the byte itself.",
         xch(2, set(range(32, 64)) | (set(range(96, 256)) - {127})), lambda c: at(c, 22, 11, [P, c.v, R])),
    Rule("R-PFX-CTRL", S6, "The prefix, then a control code (but 27), acts as the code and cancels the prefix: a "
         "following A is a plain A (never $01).",
         lambda c: c.src == "G3" and c.kind == 1 and c.c != 27, lambda c: 1 not in c.cells),
    Rule("R-PFX-ESC", S6, "The prefix, then ESC, arms the escape: a following A is ESC A (cursor up, nothing "
         "written).", lambda c: c.src == "G3" and c.kind == 1 and c.c == 27, lambda c: at(c, 21, 10, PQR)),

    Rule("R-LT-CLEAR", S7, "After a clear, LINTTB holds 24, 23, …, 1 down the rows (when nothing wrapped or "
         "scrolled).", lambda c: c.src == "G2" and c.byte in (8, 29, 30, 13) and c.col == 0 and c.key == 0,
         lambda c: c.lt == FRESH_LT),
    Rule("R-LT-WRAP", S7, "A printable or TAB that wraps from a row (not the last) sets that row's entry to 0 "
         "(the row continues).",
         lambda c: c.src == "G2" and c.byte in (9, ord("A")) and c.col == 39 and c.s < c.last,
         lambda c: c.lt[c.s] == 0),
    Rule("R-LT-SCROLL", S7, "A scroll moves the entries up one and gives the new last text row $AF.",
         lambda c: c.src == "G2" and c.byte == 10 and c.s == c.last,
         lambda c: c.lt[c.last] == 0xAF),

    Rule("R-XY-CURSOR", S8, "ESC x v and ESC y v never move the cursor.", lambda c: c.src == "G6",
         lambda c: (c.csrx, c.csry) == (21, 11)),
    Rule("R-Y-4", S8, "ESC y '4' sets $FCAA to 1.", lambda c: c.src == "G6" and c.kind == "y" and c.v == ord("4"),
         lambda c: c.fcaa == 1),
    Rule("R-Y-5", S8, "ESC y '5' sets CSRSW ($FCA9) to 1.",
         lambda c: c.src == "G6" and c.kind == "y" and c.v == ord("5"), lambda c: c.fca9 == 1),

    Rule("R-XY-CELLS", S9, "From both cells set, ESC x '4' clears $FCAA and ESC x '5' clears CSRSW; from both clear, "
         "ESC y '4' / '5' set them; every other byte after ESC x / y changes neither.",
         lambda c: c.src == "X3G2",
         lambda c: (c.csrsw, c.fcaa) == ({"x": {52: (1, 0), 53: (0, 1)}, "y": {52: (0, 1), 53: (1, 0)}}[c.kind]
                                         .get(c.v, (1, 1) if c.kind == "x" else (0, 0)))),
    Rule("R-Y1-SEQ", S9, "Byte 1 inside ESC Y: no general rule found; the cursor after each byte of five measured "
         "sequences (row byte '%' = 37 = row 6), as the reference gives them: "
         + "; ".join(f"`{q}` {[tuple(x) for x in r]}" for q, r in zip(Y1_SEQ, Y1_REF)) + ".",
         lambda c: c.src == "X3G1", lambda c: c.cur == Y1_REF[c.seq]),
    Rule("R-Y1-PARAM", S9, "Byte 1 as ESC Y's whole row or column parameter (the other one '%' = 37) leaves the "
         "cursor at column 1, row 6, on the reference -- see R-Y1-SEQ: no general rule found.",
         lambda c: c.src == "G5" and c.v == 1, lambda c: (c.csrx, c.csry) == (1, 6)),
    Rule("R-DEL-WRAPCELL", S9, "A DEL that wraps from column 1 to the row above blanks that row's column 40; BS and "
         "29 leave it; none of them changes the rows' LINTTB entries.",
         lambda c: c.src == "X3G3",
         lambda c: (c.csrx, c.csry) == (40, 10) and c.c939 == (SP if (c.byte == 127 or not c.wrapped) else ord("z"))
         and (c.lt9, c.lt10) == ((0 if c.wrapped else 15), 14)),
    Rule("R-ESC-EDGES", S9, "ESC A / B / C / D stop at the screen's edges: no wrap, no scroll (the last row is the "
         "last TEXT row).", lambda c: c.src == "X3G4",
         lambda c: (c.csrx, c.csry) == {"A": (c.col + 1, max(c.s, 1)), "B": (c.col + 1, min(c.s + 1, c.last) + 1),
                                        "C": (min(c.col + 2, 40), c.s + 1), "D": (max(c.col, 1), c.s + 1)}[c.cmd]
         and c.col0[0] != ord("b")),
    Rule("R-ED-KEYROW", S9, "With the key line on, the line and screen edits work on the text rows 1–23 only: ESC L "
         "drops row 23's content, ESC M blanks row 23, ESC J and the clears stop at row 23, and the key row (row 24) is "
         "never touched.", lambda c: c.src == "X3G5", lambda c: key_edit_ok(c)),
    Rule("R-A-PENDING", S9, "CHPUT returns A unchanged after an ESC or a graphic prefix too.",
         lambda c: c.src == "X3G6", lambda c: c.a == c.sent),
]
