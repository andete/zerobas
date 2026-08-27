#!/usr/bin/env python3
"""D-PAINTSCAN: is GFX_CX/GFX_CY REALLY dead for the duration of a PAINT?

The scan cache needs 4 bytes and the usual RAM regions are exhausted
(sysvars.inc: "SQRT_POW10 took the last free byte"), so the cheap route is to
ALIAS a cell that no code reachable from `gfx_paint_op` touches. GFX_CX/GFX_CY
($E109, 4 B) belong to gfx_plot_cur and the Bresenham stepper, and PAINT reaches
VRAM through gfx_rmw_at directly -- never through either.

🔴 THAT IS A CLAIM, AND THIS PROJECT HAS BEEN BITTEN BY ALIASING CLAIMS. Two
independent checks, because either alone can be fooled:

  STATIC  -- walk the REAL call graph from gfx_paint_op with the gate's own
             fallthrough-aware walker (tools/check_tenant_closure.py), then ask
             whether ANY routine in the closure mentions GFX_CX/GFX_CY in its
             linear span. ⚠️ An UNDER-approximated closure yields a false
             "dead", so every unresolved transfer target is reported loudly --
             silence here would be the failure mode, not the result.

  DYNAMIC -- run the REAL gfx_paint_op in the host Z80 sim twice, with
             GFX_CX/GFX_CY seeded to two different poison values, and compare
             (a) the painted pixel set and (b) the cells afterwards. If PAINT
             READ them the fills would differ; if it WROTE them the poison would
             not survive.
"""
from __future__ import annotations
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import check_tenant_closure as ctc                                 # noqa: E402
from _tmp import tp                                                # noqa: E402
from msxtest import Machine                                        # noqa: E402

CELLS = ("GFX_CX", "GFX_CY")
ROOTS = ("gfx_paint_op",)


def static_check():
    files = ctc.collect_sources("sub/sub.asm")
    graph = ctc.build_callgraph(files)
    data = ctc.build_datagraph(files)
    seen, stack, unresolved = set(), list(ROOTS), set()
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        if n not in graph:
            unresolved.add(n)
            continue
        stack.extend(graph[n] - seen)
    print(f"STATIC: closure of {ROOTS[0]} = {len(seen)} routines "
          f"over {len(files)} source files")
    if unresolved:
        # Names with no body in the scanned set: equates, RAM cells, BIOS entries.
        # Harmless as leaves, but they must be SHOWN -- an unresolved name that is
        # really a routine would mean the closure stopped early.
        print(f"  unresolved leaf names ({len(unresolved)}): "
              f"{sorted(unresolved)[:12]}{' ...' if len(unresolved) > 12 else ''}")
    hits = []
    for r in sorted(seen):
        for c in CELLS:
            if c in data.get(r, set()) or c in graph.get(r, set()):
                hits.append((r, c))
    if hits:
        print(f"  🔴 {len(hits)} mention(s) INSIDE the PAINT closure: {hits}")
    else:
        print(f"  ✅ no routine in the closure mentions {' / '.join(CELLS)}")
    # control: the cells must be mentioned SOMEWHERE, or the check is vacuous
    everywhere = [r for r in data if any(c in data[r] for c in CELLS)]
    print(f"  control: {len(everywhere)} routine(s) in the whole sub image DO "
          f"mention them{' -- ' + str(sorted(everywhere)[:6]) if everywhere else ''}")
    if not everywhere:
        print("  🔴 VACUOUS: the names appear nowhere at all -- the scan is "
              "matching nothing, so 'not in the closure' means nothing")
    return not hits and bool(everywhere)


def ring(x0, y0, x1, y1):
    pts = set()
    for x in range(x0, x1 + 1):
        pts.add((x, y0)); pts.add((x, y1))
    for y in range(y0, y1 + 1):
        pts.add((x0, y)); pts.add((x1, y))
    return pts


def fill_with(m, poison):
    screen = {p: 2 for p in ring(4, 4, 68, 52)}

    def do_read(mm):
        pt = (mm.cpu.e, mm.cpu.d)
        mm.cpu.a = screen.get(pt, 0)
        mm.cpu.f = 0x00 if pt in screen else 0x40

    def do_plot(mm):
        x = mm.peek(mm.addr("GFX_PTESTX"))[0]
        y = mm.peek(mm.addr("GFX_PTESTY"))[0]
        screen[(x, y)] = mm.peek(mm.addr("GFX_C"))[0]

    def do_bytes(mm):
        c = mm.peek(mm.addr("GFX_C"))[0]
        for k in range(mm.cpu.b * 8):
            screen[(mm.cpu.e + k, mm.cpu.d)] = c

    m.trap("gfx_paint_read", do_read)
    m.trap("gfx_paint_plot", do_plot)
    m.trap("gfx_span_bytes", do_bytes)
    m.poke(m.addr("SCRMOD"), 2)
    m.poke(m.addr("GFX_PTOP"), 0)
    m.poke(m.addr("GFX_POVF"), 0)
    m.poke_w(m.addr("GFX_CX"), poison)
    m.poke_w(m.addr("GFX_CY"), poison ^ 0xFFFF)
    m.poke_w(m.addr("GXPOS"), 36)
    m.poke_w(m.addr("GYPOS"), 28)
    m.poke(m.addr("GFX_C"), 2)
    m.poke(m.addr("GFX_B"), 2)
    m.call("gfx_paint_op", max_steps=200_000_000)
    after = (m.peek(m.addr("GFX_CX"))[0] | (m.peek(m.addr("GFX_CX") + 1)[0] << 8),
             m.peek(m.addr("GFX_CY"))[0] | (m.peek(m.addr("GFX_CY") + 1)[0] << 8))
    painted = frozenset(p for p, c in screen.items() if c == 2)
    return painted, after


def dynamic_check():
    m = Machine(tp("zb_graphics_sub.rom"), tp("zb_graphics_sub.sym"), rom_base=0)
    a_px, a_after = fill_with(m, 0x0000)
    b_px, b_after = fill_with(m, 0xA55A)
    print("\nDYNAMIC: the same fill run with GFX_CX/CY seeded differently")
    same = a_px == b_px
    print(f"  painted set identical            : {'✅' if same else '🔴'} "
          f"({len(a_px)} vs {len(b_px)} px)")
    kept_a = a_after == (0x0000, 0xFFFF)
    kept_b = b_after == (0xA55A, 0x5AA5)
    print(f"  seed 0000/FFFF survived the fill : {'✅' if kept_a else '🔴'} "
          f"-> {a_after[0]:04X}/{a_after[1]:04X}")
    print(f"  seed A55A/5AA5 survived the fill : {'✅' if kept_b else '🔴'} "
          f"-> {b_after[0]:04X}/{b_after[1]:04X}")
    return same and kept_a and kept_b


def main():
    ok_s = static_check()
    ok_d = dynamic_check()
    print(f"\n=== GFX_CX/GFX_CY dead for the duration of a PAINT: "
          f"{'✅ BOTH CHECKS AGREE' if ok_s and ok_d else '🔴 NOT ESTABLISHED'} ===")
    return 0 if (ok_s and ok_d) else 1


if __name__ == "__main__":
    raise SystemExit(main())
