#!/usr/bin/env python3
"""D-PAINTSCAN scout: PRICE the per-cell cache BEFORE writing a byte of ROM.

D-PAINTVRAM left PAINT 2.02x slower than both references and counted the cause:
`gfx_paint_scan_row` tests EVERY column one pixel at a time, and the scan is
76.9% -> 89.0% of all VDP accesses as the fill grows. The candidate fix is pure
caching -- eight consecutive columns of a row share ONE pattern byte and ONE
colour byte, and scan_row only TESTS (it never writes), so the row is stable
across its own pass.

But "eight columns share a byte" is the BEST case. It only pays if the tests
actually ARRIVE grouped by cell. This counts, per fill:

    tests            -- calls to gfx_paint_read (each = gfx_calc_addr + 2 VDP reads)
    distinct (y,cell)-- how many pattern/colour PAIRS those tests actually touch
    consecutive-hit  -- tests whose (y,cell) equals the IMMEDIATELY PRECEDING
                        test's, i.e. what a ONE-ENTRY cache would serve.

🔴 The one-entry number is the one that matters. A cache that must remember more
than the last cell is a different, more expensive design, and the gap between
the two columns is exactly how much a bigger cache would buy.
"""
from __future__ import annotations
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.chdir(ROOT)
from _tmp import tp                                                # noqa: E402
from msxtest import Machine                                        # noqa: E402


def ring(x0, y0, x1, y1):
    pts = set()
    for x in range(x0, x1 + 1):
        pts.add((x, y0)); pts.add((x, y1))
    for y in range(y0, y1 + 1):
        pts.add((x0, y)); pts.add((x1, y))
    return pts


def run(m, x0, y0, x1, y1):
    screen = {p: 2 for p in ring(x0, y0, x1, y1)}
    st = dict(tests=0, hits=0, plots=0, cells=0)
    seen, last = set(), [None]

    def do_read(mm):
        pt = (mm.cpu.e, mm.cpu.d)                 # E=x, D=y
        key = (pt[1], pt[0] >> 3)                 # (row, cell column)
        st["tests"] += 1
        if key == last[0]:
            st["hits"] += 1
        last[0] = key
        seen.add(key)
        mm.cpu.a = screen.get(pt, 0)
        mm.cpu.f = 0x00 if pt in screen else 0x40

    def do_plot(mm):
        st["plots"] += 1
        x = mm.peek(mm.addr("GFX_PTESTX"))[0]
        y = mm.peek(mm.addr("GFX_PTESTY"))[0]
        screen[(x, y)] = mm.peek(mm.addr("GFX_C"))[0]
        last[0] = None                            # a WRITE invalidates the cache

    def do_bytes(mm):
        st["cells"] += mm.cpu.b
        c = mm.peek(mm.addr("GFX_C"))[0]
        for k in range(mm.cpu.b * 8):
            screen[(mm.cpu.e + k, mm.cpu.d)] = c
        last[0] = None                            # ...as does the blind fill

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
    return st, len(seen)


def main():
    m = Machine(tp("zb_graphics_sub.rom"), tp("zb_graphics_sub.sym"), rom_base=0)
    print(f"{'box interior':<16} {'px':>6} {'tests':>7} {'pairs':>6} "
          f"{'1-entry hits':>13} {'hit rate':>9} {'ideal':>7}")
    for box in [(4, 4, 36, 28), (4, 4, 68, 52), (4, 4, 132, 100)]:
        st, pairs = run(m, *box)
        px = (box[2] - box[0] - 1) * (box[3] - box[1] - 1)
        rate = st["hits"] / st["tests"] if st["tests"] else 0
        ideal = 1 - pairs / st["tests"] if st["tests"] else 0
        print(f"{f'{box[0]},{box[1]}-{box[2]},{box[3]}':<16} {px:>6} "
              f"{st['tests']:>7} {pairs:>6} {st['hits']:>13} "
              f"{rate:>8.1%} {ideal:>6.1%}")
    print()
    print("hit rate = VDP read pairs a ONE-ENTRY cache removes (the cheap design).")
    print("ideal    = what an unbounded cache could remove. The gap is what a")
    print("           bigger cache would buy, and it must be worth its bytes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
