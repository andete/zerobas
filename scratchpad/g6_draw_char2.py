#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G6 DRAW black-box characterization on the Philips VG-8020, round 2.

Round 1 (g6_draw_char1.py) established: U/D/L/R/E/F/G/H + M abs/rel + B/N
prefixes + S scale (quarter units, truncating) + A angle (0..3, 90 deg steps,
applies to relative motion only) + "=var;" substitution + spaces skipped +
lowercase accepted; errors: bad letter/A>3/C>15/S>255/SCREEN 0,1/M missing 2nd
operand/"=var" without ';' -> ERR 5, numeric arg -> ERR 13, off-screen -> ok.

*** AND: the A / S state PERSISTS across DRAW statements and across RUNs. ***
Round 1's "odd" rows are all exactly explained by a carried-over S=8, A=1.

Round 2 pins what that persistence actually is, plus the values round 1 only
proved non-erroring:

  P1 persist  -- what resets A / S / C: nothing / RUN / NEW / SCREEN 2 / CLEAR?
                 and the power-on defaults (fresh boot, one case per boot).
  P2 colour   -- default DRAW colour; does C<n> persist; does it change FORCLR
                 (i.e. leak into a later LINE/PSET default)?
  P3 values   -- endpoints for the accepted-but-odd forms: U-5, S0, U40000,
                 off-screen runs, M with >int16 operands, multi-digit / leading
                 zero counts, "=var;" with a float or negative value.
  P4 Xsub     -- the X<var>; substring form: does it execute, nest, and does
                 state set inside it persist after it returns?
  P5 bitmap   -- is a DRAW M-line byte-identical to the same LINE? (the G3
                 rasteriser identity question) + colour plane.
"""
from __future__ import annotations
import os, sys, re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
CTAB = 0x2000


def rd_pos(tag: int) -> str:
    return (f'PRINT"Q{tag}Q";PEEK(&HFCB7)+256*PEEK(&HFCB8);PEEK(&HFCB9)+256*PEEK(&HFCBA);'
            'PEEK(&HFCB3)+256*PEEK(&HFCB4);PEEK(&HFCB5)+256*PEEK(&HFCB6)')


def _pick(txt, tag):
    m = re.search(rf"Q{tag}Q([ \d\-]+)", txt)
    return m.group(1).strip() if m else f"<none> raw={txt[:70]!r}"


def _run(specs):
    return omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)


# ---- P1: what resets the persistent A/S state -------------------------------
# Probe: set S8 A1 in one run, then in a SECOND run (after the named reset)
# measure a plain "U10" from (100,100). 100/90 => state was reset to S4 A0;
# 80/100 => S8 A1 survived.
P1_CASES = [
    ("nothing",  []),
    ("screen2",  []),          # line 10 always does SCREEN2 anyway
    ("cls",      ["CLS"]),
    ("clear",    ["CLEAR"]),
    ("color",    ["COLOR15,1,1"]),
    ("scr0scr2", ["SCREEN0", "SCREEN2"]),
]


def p1_persist():
    print("=== P1  what resets the persistent A/S state ===")
    print("     (expect 100 90 = reset to S4/A0;  80 100 = S8/A1 survived)")
    specs = []
    for i, (label, resets) in enumerate(P1_CASES):
        # run 1 sets the state; run 2 (same boot) applies the reset then measures
        specs.append(("stored", ['SCREEN2:DRAW"S8A1BM100,100"',
                                 'PRINT"SET"']))
        mid = ":".join(["SCREEN2"] + resets)
        specs.append(("stored", [mid, 'PSET(100,100):DRAW"U10"',
                                 f'SCREEN0:{rd_pos(i)}']))
    outs = _run(specs)
    for i, (label, resets) in enumerate(P1_CASES):
        txt = " ".join((outs[2 * i + 1] or "").split())
        print(f"  {label:10s} {str(resets):28s} -> {_pick(txt, i)}")


def p1_boot_default():
    """Power-on default, one case per boot (no prior DRAW in the session)."""
    print("\n=== P1b  power-on defaults (fresh boot, no prior DRAW) ===")
    prog = ["SCREEN2", 'PSET(100,100):DRAW"U10"', f'SCREEN0:{rd_pos(0)}']
    o = omsx_repl.run_cases(REF, [("stored", prog)], batch=False,
                            capture="screen", cart=None)[0]
    print(f"  fresh U10 -> {_pick(' '.join((o or '').split()), 0)}   (100 90 => S4/A0)")


# ---- P2: colour -------------------------------------------------------------
def p2_colour():
    print("\n=== P2  colour: default / persistence / FORCLR leak ===")
    # read back the pattern+colour byte at a known pixel after each op
    cases = [
        ("default",   ['COLOR15,4,7:SCREEN2', 'PSET(100,100):DRAW"R8"']),
        ("C6",        ['COLOR15,4,7:SCREEN2', 'PSET(100,100):DRAW"C6R8"']),
        # does C persist into the NEXT DRAW (same run)?
        ("C6_then",   ['COLOR15,4,7:SCREEN2', 'PSET(100,100):DRAW"C6R8":DRAW"BM100,120R8"']),
        # does C leak into a later LINE (i.e. is FORCLR changed)?
        ("C6_line",   ['COLOR15,4,7:SCREEN2', 'PSET(100,100):DRAW"C6R8":LINE(100,120)-(108,120)']),
    ]
    for label, body in cases:
        prog = body + ["GOTO 30"]
        for (x, y) in ((100, 100), (100, 120)):
            seg = [(( y >> 3) * 256 + (x >> 3) * 8 + (y & 7), 1),
                   (CTAB + (y >> 3) * 256 + (x >> 3) * 8 + (y & 7), 1)]
            raw = omsx_repl.run_cases(REF, [("stored", prog)], batch=False,
                                      capture=("vram_segs", seg), cart=None)[0]
            print(f"  {label:10s} @({x},{y}) -> {raw}")


# ---- P3: the accepted-but-odd values ----------------------------------------
P3_CASES = [
    ("neg5",      'U-5'),
    ("S0U10",     'S0U10'),
    ("S0_then",   'S0U10;S4U10'),
    ("big",       'U40000'),
    ("bigR",      'R40000'),
    ("offtop",    'BM5,5U100'),
    ("offright",  'BM250,100R100'),
    ("Mbig",      'M40000,0'),
    ("Mnegbig",   'M-40000,0'),
    ("lead0",     'U007'),
    ("multi",     'R123'),
    ("eqfloat",   'U=V;'),        # V = 10.6
    ("eqneg",     'U=W;'),        # W = -5
    ("eqbig",     'U=Z;'),        # Z = 300
]
P3_SETUP = "V=10.6:W=-5:Z=300"


def p3_values():
    print("\n=== P3  endpoints for the accepted-but-odd forms ===")
    specs = []
    for i, (label, s) in enumerate(P3_CASES):
        specs.append(("stored",
                      [f'SCREEN2:{P3_SETUP}:DRAW"A0S4"',
                       f'PSET(100,100):DRAW"{s}"',
                       f'SCREEN0:{rd_pos(i)}']))
    outs = _run(specs)
    for i, (label, s) in enumerate(P3_CASES):
        txt = " ".join((outs[i] or "").split())
        print(f"  {label:10s} {'DRAW\"'+s+'\"':16s} -> {_pick(txt, i)}")


# ---- P4: the X substring form ----------------------------------------------
P4_CASES = [
    ("x_exec",    'A$="U10"',              'XA$;'),
    ("x_then",    'A$="U10"',              'XA$;R5'),
    ("x_state",   'A$="S8"',               'XA$;U10'),      # state set inside X leaks out?
    ("x_nest",    'A$="XB$;":B$="U10"',    'XA$;'),          # nesting
    ("x_empty",   'A$=""',                 'XA$;'),
    ("x_nosemi",  'A$="U10"',              'XA$'),
]


def p4_xsub():
    print("\n=== P4  X<var>; substring execution ===")
    specs = []
    for i, (label, setup, s) in enumerate(P4_CASES):
        specs.append(("stored",
                      ['ON ERROR GOTO 50',
                       f'SCREEN2:{setup}:DRAW"A0S4"',
                       f'PSET(100,100):DRAW"{s}"',
                       f'SCREEN0:{rd_pos(i)}:END',
                       f'SCREEN0:PRINT"Q{i}Q";-ERR;-ERR;-ERR;-ERR']))
    outs = _run(specs)
    for i, (label, setup, s) in enumerate(P4_CASES):
        txt = " ".join((outs[i] or "").split())
        print(f"  {label:10s} {setup:22s} DRAW\"{s}\" -> {_pick(txt, i)}")


# ---- P5: is a DRAW line the same bitmap as LINE? ----------------------------
def _band(x0, y0, x1, y1, pad=1):
    a = (max(0, min(x0, x1) - pad), max(x0, x1) + pad)
    b = (max(0, min(y0, y1) - pad), max(y0, y1) + pad)
    return a, b


def _band_segs(xr, yr, base=0):
    cols = range(xr[0] >> 3, (xr[1] >> 3) + 1)
    rows = range(yr[0] >> 3, (yr[1] >> 3) + 1)
    cells = [(cr, cc) for cr in rows for cc in cols]
    return cells, [(base + cr * 256 + cc * 8, 8) for cr, cc in cells]


def _byte_at(b, cells, x, y):
    idx = {c: i for i, c in enumerate(cells)}
    blk = idx[(y >> 3, x >> 3)] * 8 + (y & 7)
    return b[blk] if blk < len(b) else 0


def _render(php, cells, xr, yr):
    pb = bytes.fromhex(php) if php else b""
    out = []
    for y in range(yr[0], yr[1] + 1):
        out.append("".join("#" if _byte_at(pb, cells, x, y) & (0x80 >> (x & 7))
                           else "." for x in range(xr[0], xr[1] + 1)))
    return out


def p5_bitmap():
    print("\n=== P5  DRAW M-line vs LINE bitmap identity ===")
    for label, stmts in [
        ("draw_m",  ['COLOR15,1,1:SCREEN2:CLS', 'PSET(20,20):DRAW"M53,37"']),
        ("line",    ['COLOR15,1,1:SCREEN2:CLS', 'LINE(20,20)-(53,37),15']),
        ("draw_e",  ['COLOR15,1,1:SCREEN2:CLS', 'PSET(20,20):DRAW"E17"']),
    ]:
        xr, yr = _band(20, 20, 53, 37, pad=1)
        cells, seg = _band_segs(xr, yr)
        raw = omsx_repl.run_cases(REF, [("stored", stmts + ["GOTO 30"])],
                                  batch=False, capture=("vram_segs", seg),
                                  cart=None)[0]
        print(f"  -- {label}")
        for y, r in zip(range(yr[0], yr[1] + 1), _render(raw, cells, xr, yr)):
            print(f"   y{y:3d} {r}")


if __name__ == "__main__":
    which = sys.argv[1:] or ["p1", "p1b", "p2", "p3", "p4", "p5"]
    if "p1" in which:
        p1_persist()
    if "p1b" in which:
        p1_boot_default()
    if "p2" in which:
        p2_colour()
    if "p3" in which:
        p3_values()
    if "p4" in which:
        p4_xsub()
    if "p5" in which:
        p5_bitmap()
