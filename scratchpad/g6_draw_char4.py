#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G6 DRAW black-box characterization on the Philips VG-8020, round 4 (final).

Round 3 measured a count wrap that is EXACTLY explained by:

    distance = ((n * S) mod 65536) interpreted signed, then / 4

  n=32767 S=4 -> 131068 mod 65536 = 65532 = -4 -> -1   (measured: down 1)
  n=32768     -> 0                             ->  0   (measured: no move)
  n=33000     ->    928                        -> 232  (measured: up 232)
  n=40000     ->  28928                        -> 7232 (measured round 2)
  n=65535     ->  65532 = -4                   -> -1   (measured: down 1)

Round 4 falsifies/confirms that model on fresh points and closes the last gaps:

  V1 scale model -- more (n,S) pairs the model predicts uniquely
  V2 rounding    -- the /4 for NEGATIVE products: truncate toward 0 or floor?
  V3 colour      -- does a COLOR statement override DRAW's persistent C?
                    does C survive a RUN / NEW like S and A do?
  V4 abs coord   -- M with operands beyond 65535, and the abs-vs-rel boundary
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


def model(n, s):
    """predicted signed dy for U<n> at scale s"""
    p = (n * s) & 0xFFFF
    if p >= 0x8000:
        p -= 0x10000
    return -(p // 4), -(int(p / 4))   # (floor, trunc-toward-zero) as dy for 'U'


CASES = [
    # V1/V2 (label, setup, draw, n, s)
    ("m_10_3",   'A0S3', 'U10',   10, 3),
    ("m_10_5",   'A0S5', 'U10',   10, 5),
    ("m_10_7",   'A0S7', 'U10',   10, 7),
    ("m_100_255",'A0S255', 'U100', 100, 255),
    ("m_1000_9", 'A0S9', 'U1000', 1000, 9),
    ("m_20000_5",'A0S5', 'U20000', 20000, 5),
    ("m_9000_9", 'A0S9', 'U9000', 9000, 9),
    ("neg_10_3", 'A0S3', 'U-10',  -10, 3),
    ("neg_10_5", 'A0S5', 'U-10',  -10, 5),
    ("neg_2_1",  'A0S1', 'U-2',   -2, 1),
    ("neg_2_3",  'A0S3', 'U-2',   -2, 3),
    # V4 absolute-coordinate range
    ("Mabs65535",'A0S4', 'M65535,0', None, None),
    ("Mabs99999",'A0S4', 'M99999,0', None, None),
    ("Mrel99999",'A0S4', 'M+99999,0', None, None),
    ("Mabs_S8",  'A0S8', 'M150,60', None, None),
]


def v12():
    print("=== V1/V2  scale arithmetic + negative rounding ===")
    print("     model: dist = signed((n*S) mod 65536) / 4")
    specs = []
    for i, (label, pre, s, n, sc) in enumerate(CASES):
        specs.append(("stored",
                      ['ON ERROR GOTO 50',
                       f'SCREEN2:DRAW"{pre}"',
                       f'PSET(100,100):DRAW"{s}"',
                       f'SCREEN0:{rd_pos(i)}:END',
                       f'SCREEN0:PRINT"Q{i}Q";-ERR;-ERR;-ERR;-ERR']))
    outs = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)
    for i, (label, pre, s, n, sc) in enumerate(CASES):
        txt = " ".join((outs[i] or "").split())
        got = _pick(txt, i)
        pred = ""
        if n is not None:
            fl, tr = model(n, sc)
            py_f = (100 + fl) & 0xFFFF
            py_t = (100 + tr) & 0xFFFF
            pred = f"   predict y: floor={py_f} trunc={py_t}"
        print(f"  {label:11s} [{pre}] DRAW\"{s}\"".ljust(40) + f"-> {got}{pred}")


def v3_colour():
    print("\n=== V3  does COLOR override DRAW's persistent C? does C survive RUN? ===")
    # run 1 sets C6 and draws; run 2 (same boot) issues COLOR then draws with no C
    specs = [
        ("stored", ['COLOR15,4,7:SCREEN2', 'PSET(100,100):DRAW"C6R8"', 'PRINT"SET"']),
        ("stored", ['COLOR11,4,7:SCREEN2', 'PSET(100,140):DRAW"R8"', 'GOTO 30']),
    ]
    x, y = 100, 140
    seg = [((y >> 3) * 256 + (x >> 3) * 8 + (y & 7), 1),
           (CTAB + (y >> 3) * 256 + (x >> 3) * 8 + (y & 7), 1)]
    # run both in one boot; capture on the second
    raw = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                              capture=("vram_segs", seg), cart=None)
    print(f"  after C6 (run1) + COLOR 11 (run2), plain DRAW at (100,140) -> {raw[-1]}")
    print("    colour byte high nibble: 6 => DRAW C persisted across RUN and beat COLOR;")
    print("                             B => COLOR/FORCLR won (C is not sticky that way)")


if __name__ == "__main__":
    which = sys.argv[1:] or ["v12", "v3"]
    if "v12" in which:
        v12()
    if "v3" in which:
        v3_colour()
