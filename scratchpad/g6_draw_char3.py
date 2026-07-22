#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G6 DRAW black-box characterization on the Philips VG-8020, round 3.

Closes the last grammar corners left open by rounds 1-2:

  R1 S0        -- is "S0" scale-4, or "leave the previous scale alone"?
                  (round 2 tested it only with S4 already in force -> ambiguous)
  R2 number    -- the 15-bit count wrap measured in round 2 (40000 -> 7232 =
                  40000 & 0x7FFF): confirm across 32767 / 32768 / 33000 / 65535
  R3 bareCmd   -- letter with NO argument: U..H = 1, but what do bare
                  S / A / C / M / X / B / N do?
  R4 angleB    -- does the angle rotate B-prefixed and N-prefixed moves too?
  R5 misc      -- '+' prefixed count, C=var;, A=var;, junk chars, trailing
                  separators, very long chains
"""
from __future__ import annotations
import os, sys, re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")


def rd_pos(tag: int) -> str:
    return (f'PRINT"Q{tag}Q";PEEK(&HFCB7)+256*PEEK(&HFCB8);PEEK(&HFCB9)+256*PEEK(&HFCBA);'
            'PEEK(&HFCB3)+256*PEEK(&HFCB4);PEEK(&HFCB5)+256*PEEK(&HFCB6)')


def _pick(txt, tag):
    m = re.search(rf"Q{tag}Q([ \d\-]+)", txt)
    return m.group(1).strip() if m else f"<none> raw={txt[:70]!r}"


# (label, setup-DRAW establishing state, measured DRAW)  -- start PSET(100,100)
CASES = [
    # R1 -- S0 semantics: pre-set S8, then S0U10. 80 => S0 kept 8; 90 => S0 == S4
    ("S0_after_S8",  'A0S8', 'S0U10'),
    ("S8_ctl",       'A0S8', 'U10'),
    ("S0_after_S2",  'A0S2', 'S0U10'),
    # R2 -- the 15-bit count wrap
    ("n32767",       'A0S4', 'U32767'),
    ("n32768",       'A0S4', 'U32768'),
    ("n33000",       'A0S4', 'U33000'),
    ("n65535",       'A0S4', 'U65535'),
    ("n99999",       'A0S4', 'U99999'),
    # R3 -- bare command letters
    ("bareS",        'A0S8', 'SU10'),
    ("bareA",        'A0S4', 'AU10'),
    ("bareC",        'A0S4', 'CU10'),
    ("bareM",        'A0S4', 'MU10'),
    ("bareX",        'A0S4', 'XU10'),
    ("bareB",        'A0S4', 'B'),
    ("bareN",        'A0S4', 'N'),
    # R4 -- does the angle rotate B / N moves?
    ("A1_BU10",      'A1S4', 'BU10'),
    ("A1_NU10",      'A1S4', 'NU10'),
    ("A1_BM_rel",    'A1S4', 'BM+10,0'),
    # R5 -- misc
    ("plusCount",    'A0S4', 'U+5'),
    ("Cvar",         'A0S4', 'C=V;U10'),      # V=6
    ("Avar",         'A0S4', 'A=U;U10'),      # U=1
    ("Svar",         'A0S4', 'S=T;U10'),      # T=8
    ("trailsemi",    'A0S4', 'U10;'),
    ("leadsemi",     'A0S4', ';U10'),
    ("dblsemi",      'A0S4', 'U10;;D5'),
    ("longchain",    'A0S4', 'R2R2R2R2R2R2R2R2R2R2'),
    ("junk",         'A0S4', 'U10*'),
    ("tab",          'A0S4', 'U10\tD5'),
]
SETUP = "V=6:U=1:T=8"


def run():
    print("=== G6 round 3  (start PSET(100,100); setup DRAW sets A/S first) ===")
    specs = []
    for i, (label, pre, s) in enumerate(CASES):
        specs.append(("stored",
                      ['ON ERROR GOTO 50',
                       f'SCREEN2:{SETUP}:DRAW"{pre}"',
                       f'PSET(100,100):DRAW"{s}"',
                       f'SCREEN0:{rd_pos(i)}:END',
                       f'SCREEN0:PRINT"Q{i}Q";-ERR;-ERR;-ERR;-ERR']))
    outs = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)
    for i, (label, pre, s) in enumerate(CASES):
        txt = " ".join((outs[i] or "").split())
        disp = s.replace("\t", "<TAB>")
        print(f"  {label:12s} [{pre}] DRAW\"{disp}\"".ljust(46) + f"-> {_pick(txt, i)}")


if __name__ == "__main__":
    run()
