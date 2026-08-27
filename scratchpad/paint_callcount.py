#!/usr/bin/env python3
"""D-PAINTVRAM §7.1 -- WHERE DOES A PAINT SPEND ITS VDP ACCESSES?

The stopwatch says PAINT went 46.25 -> 29.74 emulated seconds and is still 2.02x
slower than both references. That is a number, not a cause. This counts the two
things a fill actually does to the VDP, by trapping them in the host Z80 sim
(tests/msxtest) and driving the REAL gfx_paint_op:

  * gfx_paint_read   -- one per pixel TESTED (gfx_paint_inside + _passable, i.e.
                        the neighbour-row scan AND extend_lr's walk).
                        Costs 2 VDP reads (pattern + colour), each with the
                        fetch-window settle.
  * gfx_span_bytes   -- one per SPAN, carrying B whole cells.
                        Costs 2 VDP writes per cell, blind.
  * gfx_paint_plot   -- one per pixel painted per-pixel (the two partials, and
                        extend_lr's paint-as-it-walks). 2 reads + up to 2 writes.

Two box sizes, so the SCALING is measured and not assumed: if the scan really
dominates, its share must stay high as the area grows.
"""
from __future__ import annotations
import os, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from _tmp import tp                                                # noqa: E402
from msxtest import Machine                                        # noqa: E402

SUB_ROM, SUB_SYM = tp("zb_graphics_sub.rom"), tp("zb_graphics_sub.sym")


def ring(x0, y0, x1, y1):
    pts = set()
    for x in range(x0, x1 + 1):
        pts.add((x, y0)); pts.add((x, y1))
    for y in range(y0, y1 + 1):
        pts.add((x0, y)); pts.add((x1, y))
    return pts


def run(m, x0, y0, x1, y1):
    walls = ring(x0, y0, x1, y1)
    screen = {p: 2 for p in walls}
    n = collections.Counter()
    cells = [0]

    def do_read(mm):
        n["read"] += 1
        pt = (mm.cpu.e, mm.cpu.d)
        mm.cpu.a = screen.get(pt, 0)
        mm.cpu.f = 0x00 if pt in screen else 0x40

    def do_plot(mm):
        n["plot"] += 1
        x = mm.peek(mm.addr("GFX_PTESTX"))[0]
        y = mm.peek(mm.addr("GFX_PTESTY"))[0]
        screen[(x, y)] = mm.peek(mm.addr("GFX_C"))[0]

    def do_bytes(mm):
        n["spans"] += 1
        cells[0] += mm.cpu.b
        c = mm.peek(mm.addr("GFX_C"))[0]
        for k in range(mm.cpu.b * 8):
            screen[(mm.cpu.e + k, mm.cpu.d)] = c

    m.trap("gfx_paint_read", do_read)
    m.trap("gfx_paint_plot", do_plot)
    m.trap("gfx_span_bytes", do_bytes)
    m.poke(m.addr("SCRMOD"), 2)
    m.poke(m.addr("GFX_PTOP"), 0)
    m.poke(m.addr("GFX_POVF"), 0)
    m.poke_w(m.addr("GXPOS"), (x0 + x1) // 2)
    m.poke_w(m.addr("GYPOS"), (y0 + y1) // 2)
    m.poke(m.addr("GFX_C"), 2)
    m.poke(m.addr("GFX_B"), 2)
    m.call("gfx_paint_op", max_steps=200_000_000)
    return n, cells[0], len(walls)


def main():
    m = Machine(SUB_ROM, SUB_SYM, rom_base=0)
    print(f"{'box interior':<16} {'px':>7} {'reads':>8} {'plots':>7} "
          f"{'cells':>7} | {'VDP rd':>9} {'VDP wr':>8}  scan share")
    for (x0, y0, x1, y1) in [(4, 4, 36, 28), (4, 4, 68, 52), (4, 4, 132, 100)]:
        n, cells, _ = run(m, x0, y0, x1, y1)
        px = (x1 - x0 - 1) * (y1 - y0 - 1)
        # gfx_paint_read = 2 VDP reads; gfx_paint_plot = 2 reads + <=2 writes;
        # gfx_span_bytes = 2 blind writes per cell.
        rd = 2 * n["read"] + 2 * n["plot"]
        wr = 2 * n["plot"] + 2 * cells
        share = 2 * n["read"] / (rd + wr)
        print(f"{f'{x0},{y0}-{x1},{y1}':<16} {px:>7} {n['read']:>8} "
              f"{n['plot']:>7} {cells:>7} | {rd:>9} {wr:>8}  {share:6.1%}")
    print()
    print("scan share = the fraction of ALL VDP accesses that are the "
          "neighbour-row/walk pixel TESTS (gfx_paint_read).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
