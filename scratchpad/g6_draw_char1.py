#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G6 DRAW black-box characterization on the Philips VG-8020, round 1.

Read-only investigation (nothing asserted): DUMP reference DRAW behaviour so the
G6 pins can be written from measured fact (the recurring arc lesson). Pure black
box -- no ROM disassembly. Mirrors g5_paint_char1.py / g4_circle_char1.py.

KEY METHOD NOTE: DRAW is (mostly) an *endpoint arithmetic* problem on top of the
already-landed G3 line rasteriser. So round 1 measures endpoints CHEAPLY via the
GRPAC work-area cells (batched text mode, no VRAM capture, no boot-per-case),
and only spot-checks the actual bitmap where line-identity matters.

  C1 tokens   -- crunch of DRAW forms (string literal / var / expression)
  C2 endpoints-- GRPAC/GXPOS after each movement command: U D L R E F G H (with
                 and without count), M absolute, M relative (+/- prefixes),
                 B (blank) / N (no-update) prefixes, scale S, angle A, colour C,
                 command chaining + separators, "=var;" substitution
  C3 errors   -- bad letters, out-of-range args, off-screen motion, SCREEN 0/1,
                 empty string, missing count, X substring form
"""
from __future__ import annotations
import os, sys, re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
TXTTAB = 0xF676
CTAB = 0x2000
INIT = "COLOR15,1,1:SCREEN2:CLS"

# work-area cells (spec §5 [PIN]): GXPOS $FCB3/$FCB5, GRPACX $FCB7 / GRPACY $FCB9
def rd_pos(tag: int) -> str:
    """Print the 4 work-area cells behind a per-case tag, so a stale line left on
    screen from an earlier batched case can never be mistaken for this one."""
    return (f'PRINT"Q{tag}Q";PEEK(&HFCB7)+256*PEEK(&HFCB8);PEEK(&HFCB9)+256*PEEK(&HFCBA);'
            'PEEK(&HFCB3)+256*PEEK(&HFCB4);PEEK(&HFCB5)+256*PEEK(&HFCB6)')


# ---- C1: token crunch -------------------------------------------------------
C1 = [
    'draw"u10"',
    'draw a$',
    'draw"u10"+"d10"',
    'draw "bm100,100u10"',
    'draw',
]


def c1_tokens():
    print("=== C1  DRAW token crunch (grammar) ===")
    specs = [("direct", [f"1 {b}"]) for b in C1]
    raws = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                               capture=("stored_line", TXTTAB), cart=None)
    for b, raw in zip(C1, raws):
        rb = bytes.fromhex(raw) if raw else b""
        body = rb[4:] if len(rb) >= 5 else b""
        s = " ".join(f"{x:02X}" for x in body) if body else "<not stored>"
        print(f"  {b:26s} -> {s}")


# ---- C2: endpoint arithmetic ------------------------------------------------
# each entry: (label, extra setup lines, draw string)
C2_CASES = [
    # bare direction, no count -> implied 1?
    ("U",        [], "U"),
    ("D",        [], "D"),
    ("L",        [], "L"),
    ("R",        [], "R"),
    ("U0",       [], "U0"),
    ("U1",       [], "U1"),
    ("U10",      [], "U10"),
    ("D10",      [], "D10"),
    ("L10",      [], "L10"),
    ("R10",      [], "R10"),
    ("E10",      [], "E10"),
    ("F10",      [], "F10"),
    ("G10",      [], "G10"),
    ("H10",      [], "H10"),
    # absolute / relative M
    ("Mabs",     [], "M150,60"),
    ("Mrelpp",   [], "M+20,+10"),
    ("Mrelmm",   [], "M-20,-10"),
    ("Mmix1",    [], "M+20,10"),     # 2nd operand unprefixed
    ("Mmix2",    [], "M20,+10"),     # 1st unprefixed, 2nd prefixed
    # prefixes
    ("BU10",     [], "BU10"),
    ("NU10",     [], "NU10"),
    ("BNU10",    [], "BNU10"),
    ("NBU10",    [], "NBU10"),
    ("BM150,60", [], "BM150,60"),
    ("NM150,60", [], "NM150,60"),
    # scale
    ("S1U10",    [], "S1U10"),
    ("S2U10",    [], "S2U10"),
    ("S4U10",    [], "S4U10"),
    ("S8U10",    [], "S8U10"),
    ("S3U10",    [], "S3U10"),       # rounding of 10*3/4 = 7.5
    ("S5U2",     [], "S5U2"),        # 2*5/4 = 2.5
    ("S8M+10,0", [], "S8M+10,0"),    # does scale apply to relative M?
    ("S8M150,60",[], "S8M150,60"),   # ... and to absolute M? (expect no)
    # angle
    ("A1U10",    [], "A1U10"),
    ("A2U10",    [], "A2U10"),
    ("A3U10",    [], "A3U10"),
    ("A1E10",    [], "A1E10"),
    ("A1M+10,0", [], "A1M+10,0"),
    ("A1M150,60",[], "A1M150,60"),
    # chaining + separators
    ("chain",    [], "U10D5"),
    ("semi",     [], "U10;D5"),
    ("space",    [], "U 10"),
    ("spacesep", [], "U10 D5"),
    ("comma",    [], "U10,D5"),
    ("lower",    [], "u10"),
    ("empty",    [], ""),
    # colour (does it move? does it stick?)
    ("C4U10",    [], "C4U10"),
    # variable substitution
    ("eqvar",    ["V=10"], "U=V;"),
    ("eqvar_M",  ["V=150", "W=60"], "M=V;,=W;"),
    ("eqvar_S",  ["V=8"], "S=V;U10"),
]


def _mk_prog(setup, s, tag, pre="PSET(100,100)"):
    """Fixed 3-line shape (10/20/30) so no case shifts the line numbering."""
    q = s.replace('"', '')
    head = ":".join(["SCREEN2"] + setup)
    return [head, f'{pre}:DRAW"{q}"', f'SCREEN0:{rd_pos(tag)}']


def _pick(txt, tag):
    m = re.search(rf"Q{tag}Q([ \d\-]+)", txt)
    return m.group(1).strip() if m else f"<none> raw={txt[:60]!r}"


def c2_endpoints():
    print("\n=== C2  endpoints after DRAW (start PSET(100,100)) ===")
    print("      <grpacx> <grpacy> <gxpos> <gypos>")
    specs = [("stored", _mk_prog(setup, s, i))
             for i, (_, setup, s) in enumerate(C2_CASES)]
    outs = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)
    for i, ((label, _, s), o) in enumerate(zip(C2_CASES, outs)):
        txt = " ".join((o or "").split())
        print(f"  {label:10s} {'DRAW\"'+s+'\"':18s} -> {_pick(txt, i)}")


# ---- C3: errors -------------------------------------------------------------
C3_CASES = [
    ("badletter",  [], "SCREEN2:DRAW\"Z10\""),
    ("negcount",   [], "SCREEN2:DRAW\"U-5\""),
    ("S0",         [], "SCREEN2:DRAW\"S0U10\""),
    ("S256",       [], "SCREEN2:DRAW\"S256U10\""),
    ("S255",       [], "SCREEN2:DRAW\"S255U1\""),
    ("A4",         [], "SCREEN2:DRAW\"A4U10\""),
    ("C16",        [], "SCREEN2:DRAW\"C16U10\""),
    ("C_1",        [], "SCREEN2:DRAW\"C-1U10\""),
    ("scr0",       [], "SCREEN0:DRAW\"U10\""),
    ("scr1",       [], "SCREEN1:DRAW\"U10\""),
    ("offscr",     [], "SCREEN2:PSET(5,5):DRAW\"U100\""),
    ("offscr_M",   [], "SCREEN2:DRAW\"M300,300\""),
    ("bigcount",   [], "SCREEN2:DRAW\"U40000\""),
    ("emptystr",   [], "SCREEN2:DRAW\"\""),
    ("numarg",     [], "SCREEN2:DRAW 5"),
    ("Mmissing",   [], "SCREEN2:DRAW\"M100\""),
    ("Xform",      ['A$="U10"'], "SCREEN2:DRAW\"XA$;\""),
    ("Xform_var",  ['A$="U10"'], "SCREEN2:DRAW\"X\"+VARPTR(A$)"),
    ("eq_missing", ["V=10"], "SCREEN2:DRAW\"U=V\""),
]


def c3_errors():
    print("\n=== C3  errors / edges (K=ok, E<n>=err) ===")
    progs = []
    for l, setup, stmt in C3_CASES:
        body = ":".join(setup + [stmt])
        progs.append(("stored", ["ON ERROR GOTO 40", body,
                      'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END']))
    outs = omsx_repl.run_cases(REF, progs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)
    for (l, _, stmt), o in zip(C3_CASES, outs):
        toks = [ln.strip() for ln in (o or "").splitlines()
                if ln.strip().startswith("K") or ln.strip().startswith("E")]
        print(f"  {l:12s} -> {toks}")


if __name__ == "__main__":
    which = sys.argv[1:] or ["c1", "c2", "c3"]
    if "c1" in which:
        c1_tokens()
    if "c2" in which:
        c2_endpoints()
    if "c3" in which:
        c3_errors()
