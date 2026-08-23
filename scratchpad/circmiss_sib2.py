#!/usr/bin/env python3
"""D-CIRCMISS sibling sweep, ROUND 2 -- the five NOT MEASURED rows, instrument fixed.

Round 1 (scratchpad/circmiss_siblings.out) scored 9 rows and measured 4. The
five `<NO OUTPUT>` rows were the INSTRUMENT, and the source says exactly how:

  🔴 PAINT's BORDER DEFAULTS TO THE FILL COLOUR (basic/graphics.asm ep_default_b,
     "no ,B -> B = C"). Round 1 drew its stop-box in 15 and filled with 5, so
     B was 5, nothing on screen was 5, and the fill NEVER TERMINATED -- which is
     why `p.b` / `p.kb` timed out on zerobas (which paints, i.e. HAS the defect)
     while both references, which abort at ERR 24 before painting, read fine.
     🎯 The row's own failure mode was a CONSEQUENCE of the defect it was
     measuring, and it read as an apparatus fault on one side only.

  🔴 AND `p.ok` (C=5, B=15) FAILED ON ALL THREE, which is the tell that the case
     and not the machine was wrong: in SCREEN 2 one 8x1 cell holds two colours,
     so writing 5 into a cell that already held border-15 + background-4 forces
     the third colour out and the border stops reading as 15. The fill escapes
     on every machine.

  FIX: fill with the SAME colour as the stop-box, so B == C == the box and no
  cell ever needs three colours. Every row below terminates by construction.

  🔴 CLEAR: `q.trail` / `q.kcolon` read `24` on both references and `<NO OUTPUT>`
     here. A pre-marker now distinguishes "the machine died AT the CLEAR" from
     "the program never ran", and --raw dumps the screen so an untrapped abort
     is readable instead of being scored as nothing.

Readout `[ERR R]`. R = POINT(50,50), the PAINT seed: 4 = nothing filled,
15 = filled. `<NO OUTPUT>` is NOT MEASURED, never agreement.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}

# the stop-box and the fill are BOTH 15, so B (given or defaulted to C) always
# matches the box and the fill always terminates.
SETUP = "SCREEN2:LINE(40,40)-(60,60),15,B"
READ = "R=POINT(50,50)"


def gcase(stmt):
    return ["10 ONERRORGOTO900",
            f"15 {SETUP}",
            f"20 {stmt}",
            f'30 {READ}:SCREEN0:CLS:PRINT"[";ERR;R;"]":END',
            f'900 {READ}:SCREEN0:CLS:PRINT"[";ERR;R;"]":END']


def tcase(stmt):
    # a marker BEFORE the statement: if it is on screen and the fence is not,
    # the machine died AT the statement rather than never having run.
    return ["10 ONERRORGOTO900",
            '20 PRINT"<A>";',
            f"30 {stmt}",
            '40 PRINT"[";ERR;0;"]":END',
            '900 PRINT"[";ERR;0;"]":END']


CASES = {
    # --- PAINT's C slot: a comma consumed, then end of statement -----------
    'p.colour':  gcase("PAINT(50,50),"),
    'p.kcolour': gcase("PAINT(50,50),:A=1"),
    # --- PAINT's B slot, the two ways to reach it --------------------------
    'p.b':       gcase("PAINT(50,50),15,"),
    'p.kb':      gcase("PAINT(50,50),15,:A=1"),
    'p.cc':      gcase("PAINT(50,50),,"),        # ",," -> ep_c_empty -> ep_parse_b
    'p.kcc':     gcase("PAINT(50,50),,:A=1"),
    # --- THE TRAP: legitimate omissions that must keep painting ------------
    'p.none':    gcase("PAINT(50,50)"),          # no comma at all
    'p.omit':    gcase("PAINT(50,50),,15"),      # C omitted BETWEEN commas
    'p.plain':   gcase("PAINT(50,50),15"),       # C only
    'p.ok':      gcase("PAINT(50,50),15,15"),    # both fields present
    # --- CLEAR: the third candidate, with a pre-marker ---------------------
    'q.trail':   tcase("CLEAR 200,"),
    'q.kcolon':  tcase("CLEAR 200,:A=1"),
    'q.comma':   tcase("CLEAR ,200"),            # string space omitted -- legal
    'q.ok':      tcase("CLEAR 200"),
    # --- 🔴 DOES A *SUCCESSFUL* CLEAR KILL THE ON ERROR TRAP? --------------
    # If it does, the dangling comma is a symptom and the real rule is far
    # wider. `t.notrap` is the control: the SAME fault with no CLEAR in front
    # of it MUST be trapped on every machine, or the row says nothing.
    't.after':   ["10 ONERRORGOTO900", '20 PRINT"<A>";', "30 CLEAR 200",
                  "40 A=1/0", '50 PRINT"[";ERR;0;"]":END',
                  '900 PRINT"[";ERR;0;"]":END'],
    't.notrap':  ["10 ONERRORGOTO900", '20 PRINT"<A>";',
                  "40 A=1/0", '50 PRINT"[";ERR;0;"]":END',
                  '900 PRINT"[";ERR;0;"]":END'],
}

BR = re.compile(r"\[([^\]]*)\]")
NUM = re.compile(r"^[-0-9. ]*$")
# 🔴 AN UNTRAPPED ABORT IS A READING, NOT A MISSING ONE. zerobas raises
# `Missing operand in 30` at `CLEAR 200,` and ON ERROR GOTO does not catch it,
# so the fence never prints and the row scored <NO OUTPUT> -- an apparatus gap
# that was really the finding. Naming the outcome is what turns it back into a
# measurement ([[a-probe-whose-answer-is-nothing-happened]]).
# ⚠️ AND THE LIST MUST BE COMPLETE, OR THE HOLE JUST MOVES. `t.after` scored
# <NO OUTPUT> ON ALL THREE MACHINES for one reason only: "Division by zero" was
# missing from this alternation, so a perfectly good reading -- the reference
# printing `Division by zero in 40` untrapped -- read as nothing at all. That is
# the SAME failure the UNTRAPPED branch was added to fix, one message along.
ERRMSG = re.compile(r"(Missing operand|Syntax error|Illegal function call|"
                    r"Type mismatch|Overflow|Out of memory|Undefined line number|"
                    r"Division by zero|Redimensioned array|Subscript out of range|"
                    r"NEXT without FOR|RETURN without GOSUB|Out of DATA|"
                    r"String too long|Bad file mode|File not found)"
                    r"\s+in\s+(\d+)")


def face(cap):
    if cap is None:
        return "<NO CAPTURE>"
    txt = "".join(cap)
    for m in BR.finditer(txt):
        if NUM.match(m.group(1)):
            return " ".join(m.group(1).split()) or "<EMPTY>"
    m = ERRMSG.search(txt)
    if m:
        return f"UNTRAPPED {m.group(1)} in {m.group(2)}"
    return "<NO OUTPUT>"


def main():
    only, sides, raw = None, ["vg8020", "cf3300", "zb"], False
    for a in sys.argv[1:]:
        if a.startswith("--sides="):
            sides = [x for x in a.split("=", 1)[1].split(",") if x in SIDES]
        elif a == "--raw":
            raw = True
        else:
            only = a.split(",")
    labels = [l for l in CASES if not only or any(o in l for o in only)]
    faces = {}
    for s in sides:
        cfg = SIDES[s]
        faces[s] = {}
        for l in labels:
            caps = omsx_repl.run_cases(
                cfg["machine"],
                [("direct", list(cfg["reset"]) + CASES[l] + ["RUN"])],
                batch=False, boot=cfg["boot"], step=3.0, cap_gap=8.0,
                timeout=300.0)
            faces[s][l] = face(caps[0])
            print(f"  ran {s:7s} {l:10s} {faces[s][l]!r}", flush=True)
            if raw and ("<NO" in faces[s][l] or "UNTRAP" in faces[s][l]):
                scr = "".join(caps[0] or [])
                keep = [ln.rstrip() for ln in scr.split("\n") if ln.strip()]
                print(f"      RAW: {keep[-8:]}", flush=True)
    print()
    W = max(len(l) for l in labels)
    ndiff = nmeas = 0
    for l in labels:
        vals = {s: faces[s][l] for s in sides}
        refs = {vals[s] for s in sides if s != "zb"}
        line = f"  {l:<{W}}  " + "  ".join(f"{s}={vals[s]!r}" for s in sides)
        if not refs:
            print(line + "   (zb only)"); continue
        if len(refs) != 1:
            print(line + "   !! THE REFERENCES DISAGREE -- not a want"); continue
        if any("<NO" in v for v in vals.values()):
            print(line + "   .... NOT MEASURED"); continue
        nmeas += 1
        if vals["zb"] not in refs:
            ndiff += 1; print(line + "   *** DIFF")
        else:
            print(line)
    print(f"\nROWS: {len(labels)} printed, {nmeas} scored -- {ndiff} DIFF")


if __name__ == "__main__":
    main()
