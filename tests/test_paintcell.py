# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: D-PAINTCELL -- PAINT's SCREEN-2 neighbour-row scan, a CELL at a
time (sub/graphics.asm gpsr_cells / gfx_paint_cell), against the per-column
loop it replaced, on REAL VRAM BYTES. No emulator.

🔴 WHY THIS FILE EXISTS: tests/test_graphics.py IS BLIND HERE. It drives the
real gfx_paint_op but traps the VDP-touching leaves (gfx_paint_read,
gfx_paint_plot, gfx_span_bytes, and now gfx_paint_cell) against a pixel dict,
so nothing below those traps -- the byte encoding, the mask arithmetic, the
colour-clash interplay -- is under test there. Here NOTHING is trapped: the
VDP's two ports are modelled over a 16 KB VRAM array (address latch,
read-ahead, auto-increment), so every byte the fill reads or writes goes
through the shipped code path.

THE OLD SIDE IS IN THE SAME ROM. gfx_paint_scan_row still carries the
per-column loop (gpsr_columns, MULTICOLOUR's path), and it is exactly the
pre-D-PAINTCELL SCREEN-2 scan: pitch 1, gfx_paint_inside -> gfx_paint_read's
SCREEN-2 arm. OLD runs are made by trapping gpsr_cells and RETurning into
gpsr_columns -- the trap pushes that address, msxtest's trap return pops it --
so the comparison needs no second build and cannot rot when HEAD moves.

What must be IDENTICAL, per case, OLD vs NEW:
  * the final VRAM, pattern AND colour tables (all 16 KB, in fact);
  * every gfx_pstk_push, in order -- (y, xL, xR) -- which is the visit order;
  * GFX_POVF (the Out-of-memory edge: an overflow case is in the corpus).

And the speed: whole-gfx_paint_op Z80 T-states are counted (a timing model
over the executed instructions, below), and the full-screen flood must be at
least 1.3x cheaper NEW than OLD (the slice's own bar).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from _tmp import tp                                   # noqa: E402
from msxtest import Machine                           # noqa: E402

SUB_ROM = tp("zb_paintcell_sub.rom")
SUB_SYM = tp("zb_paintcell_sub.sym")

VDP_DATA, VDP_ADDR = 0x98, 0x99
PAT, COL = 0x0000, 0x2000


# --- Z80 T-state model ---------------------------------------------------------
# Own table (Zilog Z80 CPU User Manual timings). Conditional instructions are
# scored from where the PC went. M1 cycles are counted too: an MSX inserts one
# wait state per M1, so `t + m1` is the MSX figure.
_BASE = [
    4, 10, 7, 6, 4, 4, 7, 4, 4, 11, 7, 6, 4, 4, 7, 4,
    8, 10, 7, 6, 4, 4, 7, 4, 12, 11, 7, 6, 4, 4, 7, 4,
    7, 10, 16, 6, 4, 4, 7, 4, 7, 11, 16, 6, 4, 4, 7, 4,
    7, 10, 13, 6, 11, 11, 10, 4, 7, 11, 13, 6, 4, 4, 7, 4,
] + [0] * 128 + [
    5, 10, 10, 10, 10, 11, 7, 11, 5, 10, 10, 0, 10, 17, 7, 11,
    5, 10, 10, 11, 10, 11, 7, 11, 5, 4, 10, 11, 10, 0, 7, 11,
    5, 10, 10, 19, 10, 11, 7, 11, 5, 4, 10, 4, 10, 0, 7, 11,
    5, 10, 10, 4, 10, 11, 7, 11, 5, 6, 10, 4, 10, 0, 7, 11,
]
for _op in range(0x40, 0xC0):
    _BASE[_op] = 7 if (_op & 7) == 6 or (0x70 <= _op <= 0x77 and _op != 0x76) else 4
_JR_CC = {0x20, 0x28, 0x30, 0x38}
_RET_CC = {0xC0, 0xC8, 0xD0, 0xD8, 0xE0, 0xE8, 0xF0, 0xF8}
_CALL_CC = {0xC4, 0xCC, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4, 0xFC}
_IX_FIXED = {0x21: 14, 0x22: 20, 0x2A: 20, 0x23: 10, 0x2B: 10, 0x09: 15,
             0x19: 15, 0x29: 15, 0x39: 15, 0x34: 23, 0x35: 23, 0x36: 19,
             0xE1: 14, 0xE5: 15, 0xE3: 23, 0xE9: 8, 0xF9: 10}


def _timing(mem, pc, new_pc):
    """(T-states, M1 cycles) of the instruction at pc, given where it went."""
    op = mem[pc]
    if op == 0xCB:
        op2 = mem[(pc + 1) & 0xFFFF]
        if (op2 & 7) == 6:
            return (12 if 0x40 <= op2 <= 0x7F else 15), 2
        return 8, 2
    if op == 0xED:
        op2 = mem[(pc + 1) & 0xFFFF]
        if 0x40 <= op2 <= 0x7F:
            k = op2 & 7
            if k == 7:
                return (18 if op2 in (0x67, 0x6F) else 9), 2
            return (12, 12, 15, 20, 8, 14, 8)[k], 2
        if op2 in (0xA0, 0xA1, 0xA2, 0xA3, 0xA8, 0xA9, 0xAA, 0xAB):
            return 16, 2
        if op2 in (0xB0, 0xB1, 0xB2, 0xB3, 0xB8, 0xB9, 0xBA, 0xBB):
            return (21 if new_pc == pc else 16), 2
        return 8, 2
    if op in (0xDD, 0xFD):
        op2 = mem[(pc + 1) & 0xFFFF]
        if op2 == 0xCB:
            op4 = mem[(pc + 3) & 0xFFFF]
            return (20 if 0x40 <= op4 <= 0x7F else 23), 2
        if op2 in _IX_FIXED:
            return _IX_FIXED[op2], 2
        if 0x40 <= op2 <= 0xBF and op2 != 0x76 and (
                (op2 & 7) == 6 or (0x70 <= op2 <= 0x77)):
            return 19, 2
        return _BASE[op2] + 4, 2
    if op in _JR_CC:
        return (12 if new_pc != (pc + 2) & 0xFFFF else 7), 1
    if op == 0x10:
        return (13 if new_pc != (pc + 2) & 0xFFFF else 8), 1
    if op in _RET_CC:
        return (11 if new_pc != (pc + 1) & 0xFFFF else 5), 1
    if op in _CALL_CC:
        return (17 if new_pc != (pc + 3) & 0xFFFF else 10), 1
    return _BASE[op], 1


class VDP:
    """The TMS9918 port pair, as far as a VRAM read/write path uses it: the
    two-write address latch (2nd byte bit 6 = write mode, bit 7 = register),
    the read-ahead buffer (filled at address-set-for-read and after each data
    read), auto-increment, and a status read resetting the latch."""

    def __init__(self, vram):
        self.v, self.latch, self.first, self.addr, self.buf = vram, 0, True, 0, 0

    def out(self, port, val):
        port &= 0xFF
        if port == VDP_ADDR:
            if self.first:
                self.latch, self.first = val, False
                return
            self.first = True
            if val & 0x80:
                return                                  # register write: ignored
            self.addr = ((val & 0x3F) << 8) | self.latch
            if not val & 0x40:                          # read setup: pre-fetch
                self.buf = self.v[self.addr]
                self.addr = (self.addr + 1) & 0x3FFF
        elif port == VDP_DATA:
            self.first = True
            self.v[self.addr] = val
            self.buf = val
            self.addr = (self.addr + 1) & 0x3FFF

    def inp(self, port):
        port &= 0xFF
        self.first = True
        if port == VDP_DATA:
            r = self.buf
            self.buf = self.v[self.addr]
            self.addr = (self.addr + 1) & 0x3FFF
            return r
        return 0x00                                     # status


def blank(fg=15, bg=4):
    """A cleared SCREEN 2: pattern $00, every colour byte fg:bg."""
    v = bytearray(0x4000)
    v[COL:COL + 0x1800] = bytes([(fg << 4) | bg]) * 0x1800
    return v


def pset(v, x, y, c):
    """The colour-clash PSET (the rule test_graphics.py's RMW_CASES pin):
    c == the cell's bg nibble clears the bit; else set it and fg := c."""
    if not (0 <= x <= 255 and 0 <= y <= 191):
        return
    a = (y >> 3) * 256 + (x & 0xF8) + (y & 7)
    mask = 0x80 >> (x & 7)
    col = v[COL + a]
    if c == col & 0x0F:
        v[PAT + a] &= ~mask & 0xFF
    else:
        v[PAT + a] |= mask
        v[COL + a] = (c << 4) | (col & 0x0F)


def hline(v, x0, x1, y, c):
    for x in range(x0, x1 + 1):
        pset(v, x, y, c)


def vline(v, x, y0, y1, c):
    for y in range(y0, y1 + 1):
        pset(v, x, y, c)


def box(v, x0, y0, x1, y1, c):
    hline(v, x0, x1, y0, c); hline(v, x0, x1, y1, c)
    vline(v, x0, y0, y1, c); vline(v, x1, y0, y1, c)


def circle(v, cx, cy, r, c):
    x, y, d = 0, r, 1 - r
    while x <= y:
        for px, py in ((x, y), (y, x)):
            for sx in (1, -1):
                for sy in (1, -1):
                    pset(v, cx + sx * px, cy + sy * py, c)
        if d < 0:
            d += 2 * x + 3
        else:
            d += 2 * (x - y) + 5
            y -= 1
        x += 1


def _lcg(seed):
    s = seed
    while True:
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        yield s >> 8


def colour_at(v, x, y):
    """The effective colour of (x,y): the fg nibble if its pattern bit is set."""
    a = (y >> 3) * 256 + (x & 0xF8) + (y & 7)
    col = v[COL + a]
    return col >> 4 if v[PAT + a] & (0x80 >> (x & 7)) else col & 0x0F


def fill_disc(v, cx, cy, r, c):
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                pset(v, x, y, c)


# --- the corpus: (name, vram, seed (x,y), C, B, span-stack capacity or None) ----
# Sized for the host sim: the OLD side is the expensive one, and the full-screen
# flood is most of the run. ⚠️ A C != B case cannot be FENCED by a box: with
# C != B nothing bounds extend_lr's walk (R-FLOOD -- `passable` is true for
# every pixel), and only gfx_paint_inside's "already C" stops a PUSH. So those
# cases are kept small by two FULL-WIDTH rows in colour C above and below --
# the walk runs to x=0..255 between them (which is itself the edge case
# wanted) and no push ever crosses them.
def corpus():
    cases = []
    cases.append(("flood", blank(), (128, 96), 15, 15, None))

    v = blank(); circle(v, 128, 96, 60, 15)
    cases.append(("circle", v, (128, 96), 15, 15, None))

    v = blank(); box(v, 37, 50, 110, 90, 7)
    cases.append(("box", v, (70, 70), 7, 7, None))

    v = blank()
    for r, c in ((44, 9), (33, 7), (22, 9), (11, 11)):
        circle(v, 128, 96, r, c)
    cases.append(("concentric-in-9", v.copy(), (128, 96 - 16), 9, 9, None))
    cases.append(("concentric-c11", v.copy(), (128, 96 - 5), 11, 11, None))
    hline(v, 0, 255, 76, 7); hline(v, 0, 255, 90, 7)   # C rows for C != B
    cases.append(("concentric-c7-b9", v, (128, 96 - 14), 7, 9, None))

    # a comb: a bar with teeth every 3 px hanging down -> many small spans
    v = blank(); hline(v, 10, 130, 60, 15); vline(v, 10, 60, 90, 15)
    vline(v, 130, 60, 90, 15); hline(v, 10, 130, 90, 15)
    for x in range(13, 130, 3):
        vline(v, x, 60, 75 + (x % 7), 15)
    cases.append(("comb", v, (11, 70), 15, 15, None))

    # every x mod 8 alignment, both ends: one box per left phase, the right
    # phase running the other way round, so both ends see all eight
    for a in range(8):
        v = blank()
        x0, x1 = 16 + a, 80 + (7 - a) + 8 * a
        box(v, x0, 20, x1, 32, 15)
        cases.append((f"align-{a}", v, (x0 + 2, 26), 15, 15, None))

    # spans touching x=0 and x=255: a full-width band
    v = blank(); hline(v, 0, 255, 50, 13); hline(v, 0, 255, 56, 13)
    cases.append(("band-0-255", v, (200, 53), 13, 13, None))
    # ...and spans cut at x=0 / x=255 by the screen alone, with obstacles so
    # spans start AT 0 and end AT 255 in the middle of the region
    v = blank(); hline(v, 0, 255, 100, 13); hline(v, 0, 255, 124, 13)
    vline(v, 3, 101, 110, 13); vline(v, 250, 114, 123, 13)
    box(v, 100, 106, 140, 118, 13)
    cases.append(("edges", v, (50, 112), 13, 13, None))

    # the seed ON a drawn border pixel (G5's `PAINT(16,16),7,15`: C != B, the
    # seed reads B and is admitted), fenced in colour C
    v = blank(); box(v, 30, 36, 90, 64, 15)
    hline(v, 0, 255, 30, 7); hline(v, 0, 255, 70, 7)
    cases.append(("seed-on-border", v, (30, 50), 7, 15, None))
    # C != B with walls in B, in a third colour, and in C itself (R-FLOOD)
    v = blank(); hline(v, 0, 255, 10, 6); hline(v, 0, 255, 34, 6)
    box(v, 30, 16, 60, 28, 15); circle(v, 90, 22, 8, 3); vline(v, 75, 12, 32, 6)
    cases.append(("c-ne-b", v, (20, 20), 6, 15, None))
    # C == the background nibble: only DRAWN non-C pixels are inside, and
    # painting them clears their bits (the clash rule's c == bg arm)
    v = blank(); fill_disc(v, 60, 60, 7, 9); circle(v, 60, 60, 3, 4)
    cases.append(("c-is-bg", v, (60, 55), 4, 4, None))

    # mixed fg/bg cells: random pattern bytes, colour nibbles drawn from
    # {C, B, two others}, so every (fg==C?, bg==C?) combination of
    # gfx_paint_cell's four masks occurs many times over; fenced in C
    for name, seed, C, B in (("mixed-cb", 1, 9, 9), ("mixed-c-ne-b", 2, 9, 5),
                             ("mixed-cb2", 4, 5, 5)):
        rnd = _lcg(seed)
        v = blank()
        nib = (C, B, 2, 12)
        for cy in ((4, 5) if C == B else (4,)):
            for cx in range(4, 20):
                for row in range(8):
                    a = cy * 256 + cx * 8 + row
                    r = next(rnd)
                    v[PAT + a] = (r & 0xFF) & ((r >> 8) & 0xFF)
                    v[COL + a] = (nib[(r >> 20) & 3] << 4) | nib[(r >> 22) & 3]
        bottom = 48 if C == B else 40      # C != B walks every row full-width
        hline(v, 0, 255, 31, C); hline(v, 0, 255, bottom, C)
        sx, sy = next((x, y) for y in range(34, bottom) for x in range(64, 160)
                      if colour_at(v, x, y) != C)
        cases.append((name, v, (sx, sy), C, B, None))

    # the Out-of-memory edge: a span stack with room for 4 entries, on a comb
    v = blank(); hline(v, 10, 245, 60, 15)
    for x in range(10, 246, 3):
        vline(v, x, 60, 100, 15)
    cases.append(("overflow", v, (11, 70), 15, 15, 4))
    return cases


def build():
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "sub"), "--bin",
                    os.path.join(ROOT, "sub", "sub.asm"), SUB_ROM, SUB_SYM],
                   check=True, capture_output=True, cwd=ROOT)


def paint(rom, sym, vram, seed, C, B, cap=None, old=False, scrmod=2):
    """Run the real gfx_paint_op over `vram` (mutated). Returns
    (pushes, povf, T-states, M1 cycles, [cell path entered, gfx_paint_inside
    calls])."""
    m = Machine(rom, sym, rom_base=0)
    vdp = VDP(vram)
    m.cpu.io_out = vdp.out
    m.cpu.io_in = vdp.inp
    m.poke(m.addr("SCRMOD"), scrmod)
    m.poke_w(m.addr("GXPOS"), seed[0])
    m.poke_w(m.addr("GYPOS"), seed[1])
    m.poke(m.addr("GFX_C"), C)
    m.poke(m.addr("GFX_B"), B)
    m.poke(m.addr("GFX_POVF"), 0)
    ary = 0x9000
    if cap is not None:
        # base = SP at gfx_pstk_reset - GFX_PAINT_MARGIN; floor = ARYEND + 2.
        # SP there is the harness's $F380 less the sentinel and one return.
        base = 0xF380 - 2 - 2 - m.addr("GFX_PAINT_MARGIN")
        ary = base - 3 * cap - 2
    m.poke_w(m.addr("ARYTAB"), ary)
    m.poke(ary, b"\x00")

    cells = m.sym.get("gpsr_cells")
    if old:
        cols = m.addr("gpsr_columns")
        m.trap(cells, lambda mm: mm.cpu.push(cols))   # RET lands in gpsr_columns

    push_at, inside_at = m.addr("gfx_pstk_push"), m.addr("gfx_paint_inside")
    pushes, acc, seen = [], [0, 0], [False, 0]
    cpu, mem, step0 = m.cpu, m.mem, m.cpu.step

    def step():
        pc = cpu.pc
        if pc == push_at:
            pushes.append((cpu.a, cpu.b, cpu.c))
        elif pc == cells:
            seen[0] = True
        elif pc == inside_at:
            seen[1] += 1
        step0()
        t, m1 = _timing(mem, pc, cpu.pc)
        acc[0] += t
        acc[1] += m1
    cpu.step = step
    m.call("gfx_paint_op", max_steps=60_000_000)
    if cap is not None:
        assert m.peek(m.addr("GFX_PBASE"), 2) == bytes([base & 0xFF, base >> 8]), \
            "the overflow case's span-stack base is not where the test computed it"
    return pushes, m.peek(m.addr("GFX_POVF"))[0], acc[0], acc[1], seen


def run():
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'} {msg}", flush=True)

    build()
    timing, povfs = {}, {}
    cases = corpus()
    for name, vram, seed, C, B, cap in cases:
        v_old, v_new = bytearray(vram), bytearray(vram)
        p_old, o_old, t_old, m_old, s_old = paint(SUB_ROM, SUB_SYM, v_old, seed,
                                                  C, B, cap, old=True)
        p_new, o_new, t_new, m_new, s_new = paint(SUB_ROM, SUB_SYM, v_new, seed,
                                                  C, B, cap, old=False)
        changed = sum(a != b for a, b in zip(vram, v_new))
        # teeth: OLD really ran the per-column loop, NEW really did not
        sides = s_old[1] > 0 and not s_old[0] and s_new[0] and s_new[1] == 0
        check(v_old == v_new and p_old == p_new and o_old == o_new and sides
              and changed > 0,
              f"{name:<18} VRAM {'==' if v_old == v_new else '!='}, "
              f"{len(p_new)} pushes {'==' if p_old == p_new else '!='} "
              f"({len(p_old)} old), POVF {o_old}/{o_new}, "
              f"{changed} bytes changed, T {t_old} -> {t_new} "
              f"({t_old / t_new:.2f}x)")
        timing[name] = (t_old, t_new, m_old, m_new)
        povfs[name] = o_new

    # teeth: the edge case must really BE the edge, and only it
    check(povfs["overflow"] == 1 and sum(povfs.values()) == 1,
          "the overflow case (and no other) reaches the Out-of-memory edge")

    # MULTICOLOUR keeps the per-column loop: the cell path is never entered
    vmc = bytearray([0x44]) * 0x4000
    _, _, _, _, seen = paint(SUB_ROM, SUB_SYM, vmc, (10, 10), 9, 9, scrmod=3)
    check(not seen[0] and seen[1] > 0,
          "SCREEN 3 never enters gpsr_cells (and still scans per column)")

    # the speed bar
    t_old, t_new, m_old, m_new = timing["flood"]
    check(t_old >= 1.3 * t_new,
          f"flood T-states {t_old} -> {t_new}: {t_old / t_new:.2f}x (bar 1.30x)")
    for name in ("flood", "circle"):
        t_old, t_new, m_old, m_new = timing[name]
        print(f"     {name:<7} Z80 T {t_old:>10} -> {t_new:>10} "
              f"({t_old / t_new:.2f}x); MSX T (+M1 wait) {t_old + m_old:>10} -> "
              f"{t_new + m_new:>10} ({(t_old + m_old) / (t_new + m_new):.2f}x)")

    print("-------------------")
    print(f"test_paintcell: {'PASS' if fails == 0 else f'FAIL ({fails})'}")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
