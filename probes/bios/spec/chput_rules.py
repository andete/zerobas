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


R4_STARTS = ((0, 0, 0), (0, 0, 39), (0, 23, 0), (0, 23, 39), (1, 0, 0), (1, 0, 39), (1, 22, 0), (1, 22, 39),
             (1, 23, 0), (1, 23, 39))
R4_SEQS = ((8,), (29,), (127,), (28,), (30,), (31,), (10,), (13,), (9,), (65,), (27, 65), (27, 66), (27, 67), (27, 68))
R4_G3 = ("ESC Z A", "ESC ~ A", "ESC DEL A", "ESC x 1 A", "ESC x ESC A A", "ESC y 1 A", "ESC y ESC A A",
         "prefix DEL A", "DEL from (10,0)", "key on: ESC Y 55 52", "key on: ESC Y 200 52", "ESC Y 54 52")


def _round4(b):
    out = []
    for i in range(140):
        x = b[4 + 42 * i: 46 + 42 * i]
        key, s0, c0 = R4_STARTS[i // 14]
        rows = [0, max(s0 - 1, 0), s0, min(s0 + 1, 23), 23]
        out.append(NS(src="R4G1", id=f"X4 G1.{i:03}", key=key, s=s0, c=c0, last=22 if key else 23,
                      seq=R4_SEQS[i % 14], rows=rows, csrx=x[0], csry=x[1], a=x[2], lt=list(x[3:27]),
                      cells=list(x[27:42])))
    for i in range(16):
        x = b[5884 + 170 * i: 6054 + 170 * i]
        out.append(NS(src="R4G2", id=f"X4 G2.{i:02}", key=i // 8, op=G4OPS[i % 8], last=22 if i >= 8 else 23,
                      csrx=x[0], csry=x[1], lt=list(x[2:26]), grid=list(x[26:170])))
    for i in range(12):
        x = b[8604 + 9 * i: 8613 + 9 * i]
        out.append(NS(src="R4G3", id=f"X4 G3.{i:02}", what=R4_G3[i], csrx=x[0], csry=x[1], a=x[2],
                      cells=list(x[3:8]), c939=x[8]))
    return out


def _block(text, who, n):
    import re
    m = re.search(rf"CAP {who}\s*:\s*([0-9a-fA-F]+)", text)
    b = bytes.fromhex(m.group(1))
    b = b + bytes(n - len(b))
    if b[1] != 0xA5:
        sys.exit(f"FAIL: a {who} block is not complete")
    return b


# RETIRED from the rules (kept as evidence): the groups whose setup placed the cursor with ESC Y and wrote
# the markers with CHPUT -- where the two machines' ESC Y differs (the key line on) they STARTED in different
# places, so a difference there was the setup's (the third review). Round 4 re-measures them with a neutral
# setup: X2 G2 (corners), X2 G4 (edits), X3 G4 (ESC A-D at the edges), X3 G5 (edits, key on).
RETIRED = {"G2", "G4", "X3G4", "X3G5"}


def cases():
    t1 = open(os.path.join(ROOT, "scratchpad", "XCH_run1.out")).read()
    t2 = open(os.path.join(ROOT, "scratchpad", "XCH2_run1.out")).read()
    t3 = open(os.path.join(ROOT, "scratchpad", "XCH3_run2.out")).read()
    t4 = open(os.path.join(ROOT, "scratchpad", "XCH4_run1.out")).read()
    out = {}
    ref_alone = None
    for who, key in (("ref", "ref"), ("zb", "ours")):
        cs = (_machine(T1.block(t1, key), T2.block(t2, key)) + _round3(_block3(t3, key))
              + _round4(_block(t4, key, 8712)))
        import xchput5_cases as X5
        t5 = open(os.path.join(ROOT, "scratchpad", "XCH5_run1.out")).read()
        for d in X5.decode(_block(t5, key, X5.caplen())):
            d.src, d.id = "R5" + d.group, f"X5 {d.group}.{d.idx:03}"
            cs.append(d)
        cs = [c for c in cs if c.src not in RETIRED]
        # each XCH prefix case carries its sibling's result: v sent ALONE (mode 0), same machine
        # each XCH prefix case's expectation: the REFERENCE's result for that byte sent ALONE -- never the
        # machine's own (the fourth review: comparing zerobas with its own sibling hid prefix + DEL)
        if ref_alone is None:
            ref_alone = {c.v: (c.csrx, c.csry, list(c.cells)) for c in cs if c.src == "XCH" and c.mode == 0}
        for c in cs:
            if c.src == "XCH" and c.mode == 2:
                c.alone = ref_alone[c.v]
        # the key row's own text on THIS machine (DSPFNK's labels, not CHPUT's): X4 G1.065 starts at
        # (0, 0) with the key line on, far from row 24
        kb = [c for c in cs if c.id == "X4 G1.065"][0].cells[12:15]
        # the key row's six grid cells for X4 G2 (key on), from this machine's ESC K case, which erases only
        # row 11 (the baseline is the machine's own, so DSPFNK's labels never read as a CHPUT difference)
        k2 = [c for c in cs if c.id == "X4 G2.11"][0].grid[23 * 6: 24 * 6]
        for c in cs:
            c.kbase = kb                    # NOT `keyrow`: round 5 records a field by that name
            c.kr2 = k2
        out[who] = cs
    return out


# each case group's RECORDED outputs (tools/spec_rules.py: field-level coverage)
OUTPUTS = {
    "XCH": ["csrx", "csry", "a", "cells"],
    "G1": ["csrx", "csry", "row"],
    "G2": ["csrx", "csry", "col0", "lt"],
    "G3": ["csrx", "csry", "cells"],
    "G4": ["csrx", "csry", "col0", "col38", "cells"],
    "G5": ["csrx", "csry"],
    "G6": ["csrx", "csry", "fca9", "fcaa"],
    "X3G1": ["cur"],
    "X3G2": ["csrsw", "fcaa"],
    "X3G3": ["csrx", "csry", "c938", "c939", "c100", "c101", "lt9", "lt10"],
    "X3G4": ["csrx", "csry", "col0"],
    "X3G5": ["csrx", "csry", "col0", "col38", "cells"],
    "X3G6": ["a"],
    "R4G1": ["csrx", "csry", "a", "lt", "cells"],
    "R4G2": ["csrx", "csry", "lt", "grid"],
    "R4G3": ["csrx", "csry", "a", "cells", "c939"],
    "R5G1": ["csrx", "csry", "cells"], "R5G2": ["csrx", "csry", "cells"], "R5G3": ["csrsw", "fcaa"],
    "R5G4": ["cur", "cells"], "R5G5": ["csrx", "csry", "keyrow"], "R5G6": ["csrx", "csry", "lt", "col0", "col39"],
    "R5G7": ["csrx", "csry", "lt2", "cells"],
}


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


# ---- round 4: a model of CHPUT at the edges (X4 G1) -- the rules below compare it, piece by piece ----
def _mark(r, col, c):
    """the setup's cell (r, col) for col 0 / 38 / 39; the key row is this machine's own (c.kbase)"""
    if r > c.last:
        return c.kbase[(0, 38, 39).index(col)]
    return {0: ord("a"), 38: ord("A"), 39: ord("0")}[col] + r


def r4_model(c):
    """(x, y, cells{(r, col)}, lt[24]) after c.seq, from (c.c, c.s): x, y 0-based"""
    L = c.last
    cell = {(r, col): _mark(r, col, c) for r in range(24) for col in (0, 38, 39)}
    lt = [24 - r for r in range(24)]
    x, y = c.c, c.s

    def scroll():
        for r in range(L):
            for col in (0, 38, 39):
                cell[(r, col)] = cell[(r + 1, col)]
            lt[r] = lt[r + 1]
        for col in (0, 38, 39):
            cell[(L, col)] = SP
        lt[L] = 0xAF

    def down(scrolls):
        nonlocal y
        if y < L:
            y += 1
        elif y == L:
            if scrolls:
                scroll()
        else:
            y = L                                       # from the key row: onto the last text row,
            if scrolls:                                 # and a scrolling action scrolls the text rows
                scroll()

    def write(ch):
        nonlocal x
        if (y, x) in cell:
            cell[(y, x)] = ch
        if x < 39:
            x += 1
        else:
            lt[y] = 0                                   # the row continues (the key row's entry too)
            x = 0
            down(True)
    seq = list(c.seq)
    if seq[0] == 27:
        cmd = seq[1]
        if cmd == 65 and y > 0:
            y -= 1
        elif cmd == 66:
            down(False)
        elif cmd == 67 and x < 39:
            x += 1
        elif cmd == 68 and x > 0:
            x -= 1
        return x, y, cell, lt
    b = seq[0]
    if b in (8, 29, 127):
        moved = True
        if x > 0:
            x -= 1
        elif y > 0:
            x, y = 39, y - 1
        else:
            moved = False
        if b == 127 and moved and (y, x) in cell:
            cell[(y, x)] = SP
    elif b == 28:
        if x < 39:
            x += 1
        elif y < L:
            x, y = 0, y + 1
        elif y > L:
            x, y = 0, L
    elif b == 30:
        if y > 0:
            y -= 1
    elif b == 31:
        down(False)
    elif b == 10:
        down(True)
    elif b == 13:
        x = 0
    elif b == 9:
        stop = 8 * (x // 8 + 1) if x < 32 else 40
        while x < stop and not (x == 0 and stop == 40 and False):
            was = x
            write(SP)
            if x == 0 and was == 39:
                break
            if x >= stop:
                break
    else:
        write(b)
    return x, y, cell, lt


def r4_cells(c):
    _, _, cell, _ = r4_model(c)
    return [cell[(r, col)] for r in c.rows for col in (0, 38, 39)]


# ---- round 4: the edits (X4 G2), the grid = columns 0, 19, 20, 21, 38, 39 of rows 0..23 ----
G2C = (0, 19, 20, 21, 38, 39)


def r4_edit_lt(c):
    """LINTTB after an X4 G2 edit (from 24 .. 1): $AF marks a row the edit blanked from the cursor or
    inserted; ESC L also puts $FB on the last text row; the key row's entry is never touched"""
    L = c.last
    lt = [24 - r for r in range(24)]
    if c.op == "ESC L":
        lt[11:L] = [24 - r for r in range(10, L - 1)]
        lt[10], lt[L] = 0xAF, 0xFB
    elif c.op == "ESC M":
        lt[10:L] = [24 - r for r in range(11, L + 1)]
        lt[L] = 0xAF
    elif c.op == "ESC J":
        for r in range(10, L + 1):
            lt[r] = 0xAF
    elif c.op in ("ESC K", "ESC l"):
        lt[10] = 0xAF
    return lt


def r4_edit(c, keyrow):
    L = c.last
    base = {0: lambda r: ord("a") + r, 38: lambda r: ord("A") + r, 39: lambda r: ord("0") + r}
    g = {}
    for r in range(L + 1):
        for col in G2C:
            g[(r, col)] = base[col](r) if col in base else (PQR[col - 19] if r == 10 else SP)
    blank = lambda r: [g.__setitem__((r, col), SP) for col in G2C]  # noqa: E731
    x, y = 20, 10
    if c.op == "ESC L":
        for r in range(L, 10, -1):
            for col in G2C:
                g[(r, col)] = g[(r - 1, col)]
        blank(10)
        x = 0
    elif c.op == "ESC M":
        for r in range(10, L):
            for col in G2C:
                g[(r, col)] = g[(r + 1, col)]
        blank(L)
        x = 0
    elif c.op in ("ESC J", "ESC K"):
        for col in G2C:
            if col >= 20:
                g[(10, col)] = SP
        if c.op == "ESC J":
            for r in range(11, L + 1):
                blank(r)
    elif c.op == "ESC l":
        blank(10)
    else:                                               # 12, ESC E, ESC j
        for r in range(L + 1):
            blank(r)
        x, y = 0, 0
    flat = []
    for r in range(24):
        flat += keyrow if r > L else [g[(r, col)] for col in G2C]
    return x, y, flat


def pfx_ctrl(c):
    """X2 G3 kind 1 (prefix, control code c, then 'A'): the cursor and cells when the code acts and 'A'
    is then written plainly, from (row 10, col 20) on P Q R; None for codes whose result leaves row 10"""
    x, y = 20, 10
    cells = {19: P, 20: Q, 21: R}
    v = c.c
    if v in (8, 29, 127):
        x -= 1
        if v == 127:
            cells[x] = SP
    elif v == 28:
        x += 1
    elif v == 13:
        x = 0
    elif v == 9:
        for k in range(x, 24):
            cells[k] = SP
        x = 24
    elif v in (10, 30, 31, 11, 12):
        return None
    if x in cells:
        cells[x] = ord("A")
    return x + 2, y + 1, [cells[19], cells[20], cells[21]]


def g6_states(cs):
    """X2 G6's carried state: ($FCA9, $FCAA) after each case, from (0, 0) -- 'ESC x/y 4' clears / sets
    $FCAA, '5' clears / sets $FCA9, nothing else changes them"""
    st, exp = [0, 0], {}
    for c in cs:
        if c.src == "G6":
            if c.v == 52:
                st[1] = 0 if c.kind == "x" else 1
            elif c.v == 53:
                st[0] = 0 if c.kind == "x" else 1
            exp[c.id] = tuple(st)
    return exp


def _g6_static():
    st, exp = [0, 0], {}
    for i in range(512):
        kind, v = ("x" if i < 256 else "y"), i % 256
        if v == 52:
            st[1] = 0 if kind == "x" else 1
        elif v == 53:
            st[0] = 0 if kind == "x" else 1
        exp[f"X2 G6.{i:03}"] = tuple(st)
    return exp


G6_EXP = _g6_static()

UNREAD = {"XCH 333": (["cells"], "ESC M pulls up the NEXT row, whose content the case before left there "
                                 "(the matrix does not set it); X4 G2 measures ESC M on a known screen")}
S10 = "10. Round 4: the edges, the key row and the edits, from a NEUTRAL setup"


# ---- round 5 ----
ESC_CMDS = set(b"ABCDEHJKLMYjlxy") | {1}
R5_ESC_CMD = {65: (22, 10, [SP, P, Q, R, SP]), 66: (22, 12, [SP, P, Q, R, SP]), 67: (23, 11, [SP, P, Q, ord("A"), SP]),
              68: (21, 11, [SP, ord("A"), Q, R, SP]), 69: (2, 1, [SP] * 5), 106: (2, 1, [SP] * 5),
              72: (2, 1, [SP, P, Q, R, SP]), 74: (22, 11, [SP, P, ord("A"), SP, SP]), 75: (22, 11, [SP, P, ord("A"), SP, SP]),
              76: (2, 11, [SP] * 5), 77: (2, 11, [SP] * 5), 108: (22, 11, [SP, SP, ord("A"), SP, SP]),
              120: (21, 11, [SP, P, Q, R, SP]), 121: (21, 11, [SP, P, Q, R, SP]), 89: (21, 24, [SP, P, Q, R, SP]),
              1: (22, 11, [SP, P, 1, R, SP])}


def r5_alone_a(v):
    """X5 G2: v then A, from (row 11, col 21) on P Q R (cells 18..22): v acts as it does alone, then A prints"""
    x, cells = 20, {18: SP, 19: P, 20: Q, 21: R, 22: SP}
    y = 10
    if v in (8, 29):
        x -= 1
    elif v == 28:
        x += 1
    elif v in (10, 31):
        y += 1
    elif v == 30:
        y -= 1
    elif v == 11:
        x, y = 0, 0
    elif v == 12:
        x, y = 0, 0
        cells = {k: SP for k in cells}
    elif v == 13:
        x = 0
    elif v == 9:
        for k in range(x, 24):
            if k in cells:
                cells[k] = SP
        x = 24
    elif v == 1:
        cells[20] = 1
        return 22, 11, [cells[k] for k in range(18, 23)]
    elif v == 27:
        return 21, 10, [cells[k] for k in range(18, 23)]          # ESC A: up, nothing printed
    if y == 10 and x in cells:
        cells[x] = ord("A")
    return x + 2, y + 1, [cells[k] for k in range(18, 23)]


def r5_y1(c):
    """the unified rule (the fourth review's): inside ESC Y, byte 1 is the graphic prefix, not a parameter;
    if the next byte is 64..95 it is written as a graphic and the escape keeps waiting, else that byte is the
    parameter. X5 G4's 'ESC Y 1 v % A' from (row 11, col 21): the cursor after each byte"""
    v = c.seq[3]
    start = (21, 11)
    if 64 <= v <= 95:
        return [start, start, start, (22, 11), (22, 6), (34, 6)]
    row = v - 31 if 32 <= v <= 55 else 24
    return [start, start, start, (21, row), (6, row), (7, row)]


def r5_edit(c):
    """X5 G6: an edit from (c.row, c.col), key line off (L = 23), on the round-4 markers (columns 0 / 39) and
    a fresh LINTTB (rows 11, 12 := 0 when CONT): (csrx, csry, col0, col39, lt)"""
    L, r, x = 23, c.row, c.col
    c0 = [ord("a") + k for k in range(24)]
    c39 = [ord("0") + k for k in range(24)]
    lt = [24 - k for k in range(24)]
    if c.flags & 4:
        lt[11] = lt[12] = 0
    op = c.what.split(" from")[0]
    cur = (x + 1, r + 1)
    if op == "ESC L":
        for k in range(L, r, -1):
            c0[k], c39[k], lt[k] = c0[k - 1], c39[k - 1], lt[k - 1]
        c0[r] = c39[r] = SP
        lt[r] = 0xAF
        if r < L:
            lt[L] = 0xFB
        cur = (1, r + 1)
    elif op == "ESC M":
        for k in range(r, L):
            c0[k], c39[k], lt[k] = c0[k + 1], c39[k + 1], lt[k + 1]
        c0[L] = c39[L] = SP
        lt[L] = 0xAF
        cur = (1, r + 1)
    elif op in ("ESC J", "ESC K"):
        if x == 0:
            c0[r] = SP
        c39[r] = SP
        lt[r] = 0xAF
        if op == "ESC J":
            for k in range(r + 1, L + 1):
                c0[k] = c39[k] = SP
                lt[k] = 0xAF
    elif op == "ESC l":
        c0[r] = c39[r] = SP
        lt[r] = 0xAF
    return cur[0], cur[1], c0, c39, lt


R5_KEY = {"A on the key row": (2, 24, [ord("A"), ord("L"), ord("M"), ord("N")]),
          "TAB on the key row": (9, 24, [SP, SP, ord("M"), ord("N")]),
          "DEL on the key row": (1, 24, [SP, ord("L"), ord("M"), ord("N")]),
          "ESC J": (21, 23, [ord("K"), ord("L"), ord("M"), ord("N")]),
          "LF from the last text row": (40, 23, [ord("K"), ord("L"), ord("M"), ord("N")]),
          "A at the last text row's end": (1, 23, [ord("K"), ord("L"), ord("M"), ord("N")])}
S11 = "11. Round 5: every escape, pending state, ESC x / y both ways, the key row, the edits anywhere"

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
    Rule("R-CLEAR", S1, "12 homes the cursor and clears the text rows (with the key line on, the key line is redrawn: R5-KEYROW).",
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
    Rule("R-ESC-LM", S3, "ESC L and ESC M move the cursor to column 1 (the line edits: R4-EDIT, R5-EDIT).",
         xch(1, b"LM"), lambda c: (c.csrx, c.csry) == (1, 11)),
    Rule("R-ESC-OTHER", S3, "ESC then any other byte (a control code, or a non-command printable) does nothing "
         "visible (that it also ENDS the escape: R5-ESC-ENDS; ESC Y / x / y: R5-ESC-CMD).",
         lambda c: c.src == "XCH" and c.mode == 1 and c.v not in set(b"ABCDEHJKLMjl"),
         lambda c: at(c, 21, 11, PQR)),
    Rule("R-ESC-CTRL", S3, "After ESC, a control code (but 1) is swallowed and ends the escape: a following A is "
         "printed.", lambda c: c.src == "G3" and c.kind == 27 and c.c != 1,
         lambda c: at(c, 22, 11, [P, ord("A"), R])),
    Rule("R-ESC-1", S3, "After ESC, byte 1 still acts as the graphic prefix: ESC, 1, A writes $01.",
         lambda c: c.src == "G3" and c.kind == 27 and c.c == 1, lambda c: at(c, 22, 11, [P, 1, R])),

    Rule("R-Y-ROW", S5, "Key line off: ESC Y's row byte r = 32..55 puts the cursor on row r − 31 (1-based) (key line on: R4-Y-KEYCLAMP).",
         lambda c: c.src == "G5" and c.kind == "row" and 32 <= c.v <= 55, lambda c: (c.csrx, c.csry) == (6, c.v - 31)),
    Rule("R-Y-ROWCLAMP", S5, "Key line off: any other row byte but 1 clamps to the last row (24).",
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
    Rule("R-PFX-ESC", S6, "The prefix, then ESC, arms the escape: a following A is ESC A (cursor up, nothing "
         "written).", lambda c: c.src == "G3" and c.kind == 1 and c.c == 27, lambda c: at(c, 21, 10, PQR)),

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
    Rule("R-Y1-SEQ", S9, "Byte 1 inside ESC Y (the general rule: R5-Y1): the cursor after each byte of five measured "
         "sequences (row byte '%' = 37 = row 6), as the reference gives them: "
         + "; ".join(f"`{q}` {[tuple(x) for x in r]}" for q, r in zip(Y1_SEQ, Y1_REF)) + ".",
         lambda c: c.src == "X3G1", lambda c: c.cur == Y1_REF[c.seq]),
    Rule("R-Y1-PARAM", S9, "Byte 1 as ESC Y's row or column byte (the other '%' = 37): a SNAPSHOT mid-sequence -- the "
         "1 is not a parameter and the escape is still waiting (R5-Y1); the cursor reads column 1, row 6.",
         lambda c: c.src == "G5" and c.v == 1, lambda c: (c.csrx, c.csry) == (1, 6)),
    Rule("R-DEL-WRAPCELL", S9, "A DEL that wraps from column 1 to the row above blanks that row's column 40; BS and "
         "29 leave it; none of them changes the rows' LINTTB entries.",
         lambda c: c.src == "X3G3",
         lambda c: (c.csrx, c.csry) == (40, 10) and c.c939 == (SP if (c.byte == 127 or not c.wrapped) else ord("z"))
         and (c.lt9, c.lt10) == ((0 if c.wrapped else 15), 14)),
    Rule("R-A-PENDING", S9, "CHPUT returns A unchanged after an ESC or a graphic prefix too.",
         lambda c: c.src == "X3G6", lambda c: c.a == c.sent),
    Rule("R-PFX-ALONE", S6, "The prefix, then a control code (0–31) or DEL, does what the REFERENCE does with that byte alone "
         "(cursor and cells as the VG-8020's mode-0 case); no graphic is written (but 1: R-PFX-1).",
         lambda c: c.src == "XCH" and c.mode == 2 and (c.v < 32 or c.v == 127),
         lambda c: (c.csrx, c.csry, c.cells) == c.alone),
    Rule("R-PFX-CTRL", S6, "The prefix, then a control code (not 1 or 27), then A: the code acts and the prefix "
         "is cancelled -- A is written plainly where the code left the cursor.",
         lambda c: c.src == "G3" and c.kind == 1 and c.c not in (1, 27) and pfx_ctrl(c) is not None,
         lambda c: (c.csrx, c.csry, c.cells) == pfx_ctrl(c)),
    Rule("R-PFX-CTRL-MOVE", S6, "… and for codes that move the cursor off row 11 (10, 11, 12, 30, 31), A is not "
         "written on row 11.", lambda c: c.src == "G3" and c.kind == 1 and c.c in (10, 11, 12, 30, 31),
         lambda c: ord("A") not in c.cells and c.csry != 11 and c.csrx == (2 if c.c in (11, 12) else 22)),
    Rule("R-PFX-1", S6, "The prefix, then 1, then A writes a plain A (the second 1 cancels, it does not re-arm).",
         lambda c: c.src == "G3" and c.kind == 1 and c.c == 1, lambda c: at(c, 22, 11, [P, ord("A"), R])),
    Rule("R-ESC-L-CELLS", S3, "ESC L leaves the cursor's row blank (an inserted line).", xch(1, b"L"),
         lambda c: c.cells == [SP, SP, SP]),
    Rule("R-G6-STATE", S8, "ESC x / ESC y with any other byte than '4' / '5' leave $FCA9 and $FCAA as they were "
         "(round 2's carried state, from 0 / 0).", lambda c: c.src == "G6",
         lambda c: (c.fca9, c.fcaa) == G6_EXP[c.id]),
    Rule("R-DEL-WRAP-ROWS", S9, "… and the row DEL / BS / 29 left (row 11) keeps its blank cells at columns 1 and 2, "
         "the row above its column 39.", lambda c: c.src == "X3G3",
         lambda c: (c.c100, c.c101, c.c938) == (SP, SP, ord("z"))),

    Rule("R4-CURSOR", S10, "From every corner, key line off and on (and ON the key row): BS / 29 / DEL move left, "
         "at column 1 to the row above's column 40, not past the top-left; 28 moves right, at column 40 to the "
         "next row unless on the last text row (it stays), from the key row into the last text row; 30 / ESC A up, "
         "not past row 1; 31 / ESC B / LF down, not past the last text row, from the key row INTO the last text "
         "row; CR to column 1; TAB to the next stop of 8, from column 33 on wrapping like a printable; a "
         "printable writes and moves right, at column 40 wrapping; ESC C / D right / left, not past the edges.",
         lambda c: c.src == "R4G1", lambda c: (c.csrx, c.csry) == tuple(v + 1 for v in r4_model(c)[:2])),
    Rule("R4-CELLS", S10, "The cells: DEL blanks the cell it moves onto (a row's column 40 included, continued or "
         "not); a printable writes its cell; TAB writes spaces; LF from the last text row, and a printable or TAB "
         "wrapping from it (or from the key row, from which they first move onto the last text row) scroll rows "
         "1..last up one and blank the last. The key row changes only where the cursor itself writes on it "
         "(the key-row cells here compare with each machine's OWN labels -- DSPFNK's text differs; R5-KEYROW "
         "pins them against the probe's own markers).",
         lambda c: c.src == "R4G1", lambda c: c.cells == r4_cells(c)),
    Rule("R4-LT", S10, "LINTTB: after a clear 24, 23, …, 1 down the rows; a wrap from a row sets its entry to 0 "
         "(continued) -- the key row's too, when the wrap starts there; a scroll shifts the text rows' entries "
         "up one and gives the last text row $AF.", lambda c: c.src == "R4G1", lambda c: c.lt == r4_model(c)[3]),
    Rule("R4-A", S10, "A comes back as the last byte sent.", lambda c: c.src == "R4G1", lambda c: c.a == c.seq[-1]),
    Rule("R4-EDIT", S10, "The edits from (row 11, column 21), on rows 1..last text row only: ESC L inserts a blank "
         "line (the last text row's content drops off), ESC M deletes the line (a blank last text row), ESC K "
         "erases to the line's end, ESC J to the last text row's end, ESC l the whole line, 12 / ESC E / ESC j "
         "clear the text rows and home; the key row is never touched.",
         lambda c: c.src == "R4G2",
         lambda c: [c.csrx - 1, c.csry - 1, c.grid] == list(r4_edit(c, c.kr2))),
    Rule("R4-EDIT-LT", S10, "LINTTB after an edit from (row 11, column 21), from a fresh table: ESC K / ESC l give the "
         "cursor's row $AF; ESC J gives it and every text row below $AF; ESC M shifts the entries below up and "
         "gives the last text row $AF; ESC L shifts them down, gives the inserted row $AF and the last text row "
         "$FB; 12 / ESC E / ESC j restore 24 … 1 (all positions, continued rows: R5-EDIT).", lambda c: c.src == "R4G2", lambda c: c.lt == r4_edit_lt(c)),
    Rule("R4-ESC-ENDS", S10, "ESC then a non-command byte (Z, ~, DEL) does nothing and ends the escape: the next A "
         "is printed.", lambda c: c.src == "R4G3" and c.what in ("ESC Z A", "ESC ~ A", "ESC DEL A"),
         lambda c: (c.csrx, c.csry, c.cells) == (22, 11, [SP, P, ord("A"), R, SP])),
    Rule("R4-ESCXY-1", S10, "ESC x / ESC y, then 1: the 1 is NOT taken as the parameter -- it arms the graphic "
         "prefix, and the next A writes $01.", lambda c: c.src == "R4G3" and c.what in ("ESC x 1 A", "ESC y 1 A"),
         lambda c: (c.csrx, c.csry, c.cells) == (22, 11, [SP, P, 1, R, SP])),
    Rule("R4-ESCXY-ESC", S10, "ESC x / ESC y, then ESC: the ESC IS taken as the parameter; the A's after it print.",
         lambda c: c.src == "R4G3" and c.what in ("ESC x ESC A A", "ESC y ESC A A"),
         lambda c: (c.csrx, c.csry, c.cells) == (23, 11, [SP, P, ord("A"), ord("A"), SP])),
    Rule("R4-PFX-DEL", S10, "The prefix, then DEL, then A: DEL acts (left, blanking P), then A is written there.",
         lambda c: c.src == "R4G3" and c.what == "prefix DEL A",
         lambda c: (c.csrx, c.csry, c.cells) == (21, 11, [SP, ord("A"), Q, R, SP])),
    Rule("R4-DEL-NOCONT", S10, "DEL at column 1 onto a row that does NOT continue still blanks its column 40.",
         lambda c: c.src == "R4G3" and c.what == "DEL from (10,0)", lambda c: (c.csrx, c.csry, c.c939) == (40, 10, SP)),
    Rule("R4-Y-KEYCLAMP", S10, "ESC Y's row, with the key line on, clamps to the last TEXT row (23); key line off, "
         "row byte 54 is row 23.", lambda c: c.src == "R4G3" and c.what.startswith(("key on", "ESC Y 54")),
         lambda c: (c.csrx, c.csry) == (21, 23)),
    Rule("R4-G3-REST", S10, "In these cases A comes back as the last byte sent, and the row above's column 40 ('z') is "
         "untouched but by the DEL case; the cells of row 11 are as stated above (Y cases: untouched).",
         lambda c: c.src == "R4G3",
         lambda c: (c.a == {"DEL from (10,0)": 127}.get(c.what, 52 if "ESC Y" in c.what else 65))
         and (c.c939 == ord("z") or c.what == "DEL from (10,0)")
         and (not ("ESC Y" in c.what or c.what == "DEL from (10,0)") or c.cells == [SP, P, Q, R, SP])),
    Rule("R5-ESC-ENDS", S11, "ESC then any byte that is not a command (A B C D E H J K L M Y j l x y) or 1 does "
         "nothing and ENDS the escape: a following A is printed (240 bytes).",
         lambda c: c.src == "R5G1" and c.seq[1] not in ESC_CMDS,
         lambda c: (c.csrx, c.csry, c.cells) == (22, 11, [SP, P, ord("A"), R, SP])),
    Rule("R5-ESC-CMD", S11, "ESC then a command, then A: the command acts (A B C D move; E j clear; H homes; J K "
         "erase; L M edit; l erases the line) and A prints; after ESC x / y / Y the A is their PARAMETER "
         "(nothing printed; ESC Y A puts the cursor on the clamped row 24); ESC 1 A writes $01.",
         lambda c: c.src == "R5G1" and c.seq[1] in ESC_CMDS,
         lambda c: (c.csrx, c.csry, c.cells) == R5_ESC_CMD[c.seq[1]]),
    Rule("R5-NOPEND", S11, "A control code alone leaves nothing pending but 1 (the prefix: the next A is $01) and 27 "
         "(ESC: the next A is ESC A): each acts, then A prints where it left the cursor.",
         lambda c: c.src == "R5G2", lambda c: (c.csrx, c.csry, c.cells) == r5_alone_a(c.seq[0])),
    Rule("R5-XY", S11, "From both cursor cells SET, ESC y v changes neither for every v; from both CLEAR, ESC x v "
         "changes neither for every v (with R-XY-CELLS: only x / y '4' / '5' clear / set them).",
         lambda c: c.src == "R5G3",
         lambda c: (c.csrsw, c.fcaa) == ((1, 1) if c.what.startswith("ESC y") else (0, 0))),
    Rule("R5-PENDING", S11, "ESC, ESC x and ESC y STAY PENDING across the prefix + a graphic: ESC 1 A B is a graphic "
         "then ESC B (down); ESC 1 A K a graphic then ESC K; ESC x / y 1 A 5: the 5 is their parameter.",
         lambda c: c.src == "R5G4" and not c.what.startswith("ESC Y"),
         lambda c: c.cur == {"ESC 1 A B": [(21, 11), (21, 11), (22, 11), (22, 12)],
                             "ESC 1 A K": [(21, 11), (21, 11), (22, 11), (22, 11)]}.get(
             c.what, [(21, 11), (21, 11), (21, 11), (22, 11), (22, 11)])),
    Rule("R5-Y1", S11, "Inside ESC Y, byte 1 is the graphic prefix, NOT a parameter: if the next byte is 64–95 it is "
         "written as a graphic and ESC Y keeps waiting; any other next byte IS the parameter (so row bytes 0, 13, "
         "31, 96, 128, 255 clamp to row 24).", lambda c: c.src == "R5G4" and c.what.startswith("ESC Y"),
         lambda c: c.cur == r5_y1(c)),
    Rule("R5-UNTOUCHED", S11, "In these pending-state sequences no other row changes: (row 6, columns 1–3) and the "
         "last row's (columns 1–3) keep their markers.", lambda c: c.src == "R5G4",
         lambda c: c.cells == [ord("f"), SP, SP, ord("x"), SP, SP]),
    Rule("R5-KEYROW", S11, "With the key line on and the KEY ROW marked: a printable / TAB / DEL on the key row write "
         "there as anywhere; ESC J, LF and a wrap from the last text row leave it; 12 / ESC E / ESC j REDRAW it "
         "(the probe's markers are replaced by the key line's labels: 'c', 'o' at columns 1, 2 on the VG-8020).",
         lambda c: c.src == "R5G5",
         lambda c: (c.csrx, c.csry, c.keyrow) == R5_KEY.get(c.what, (1, 1, [ord("c"), ord("o"), SP, SP]))),
    Rule("R5-EDIT", S11, "Every edit works from any row and column the same way (key line off): ESC L / M at the "
         "last text row only blank it ($AF); LINTTB entries MOVE with their rows (a continued row's 0 shifts down "
         "under ESC L, up under ESC M -- not a renumbering); ESC J / K / l mark the rows they blank $AF.",
         lambda c: c.src == "R5G6", lambda c: (c.csrx, c.csry, c.col0, c.col39, c.lt) == r5_edit(c)),
    Rule("R5-TAB-LAST", S11, "TAB from columns 33–39 on the last text row wraps and scrolls: the cursor at (1, 24), "
         "row 23's entry 0 (continued), row 24's $AF, the rows moved up.", lambda c: c.src == "R5G7",
         lambda c: (c.csrx, c.csry, c.lt2, c.cells) == (1, 24, [0, 0xAF], [ord("x"), SP, SP, SP, ord("b")])),
]
