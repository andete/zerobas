#!/usr/bin/env python3
"""D-MISSOP BLAST RADIUS — the SEVEN other jump sites the fix also changed.

🔴 FOUND BY GREPPING THE MECHANISM, NOT THE SYMBOL. `ev_f_err` looked like a
narrow tail: str-engine.asm mentions it five times and `sub/` not at all, so the
fix looked contained. But those str-engine mentions are HISTORICAL COMMENTS
about code that was converted away years of slices ago ("the old bare
`jp ev_f_err`", "was a bare ev_f_err -> silent 0"). Grepping for actual
INSTRUCTIONS finds the real set:

    expr.asm:556   ev_f_var: is_letter fails  <- THE SUBJECT (end of statement, '+')
    expr.asm:807   a parenthesised expression with no closing ')'
    expr.asm:1095  EOF(n) on a device/cassette channel
    expr.asm:1116  LOF(n) on a device/cassette channel
    expr.asm:1880  VARPTR with no '('
    expr.asm:1884  VARPTR(<not a variable>)
    expr.asm:2026  BASE with no '('
    expr.asm:2031  BASE(n with no closing ')'

ONE is the missing operand. The other SEVEN now defer ERR 24 as well, and a
missing ')' is the classic `Syntax error`. If the references say 2 (or 5) at
those slots, siting the fix at this shared tail is TOO WIDE and the design has
to be narrowed -- so this is not a curiosity, it is the acceptance test for
where the five bytes go.

⚠️ ALL EIGHT WERE SILENT BEFORE THE FIX, so a row reading the wrong code now was
reading NO code before. "Different wrong" is not "regressed", but it is not
fixed either, and the doc must say which.
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


def case(stmt):
    return ["10 ONERRORGOTO900",
            f"20 {stmt}",
            '30 SCREEN0:CLS:PRINT"[";ERR;0;"]":END',
            '900 SCREEN0:CLS:PRINT"[";ERR;0;"]":END']


CASES = {
    'b.paren':    case("A=(1+2"),          # :807  no closing ')'
    'b.vpnopar':  case("A=VARPTR 5"),      # :1880 VARPTR with no '('
    'b.vpbadarg': case("A=VARPTR(5)"),     # :1884 VARPTR of a non-variable
    'b.vpnoclose': case("A=VARPTR(B"),     # :1880/1884 region, no ')'
    'b.basenopar': case("A=BASE 5"),       # :2026 BASE with no '('
    'b.basenoclose': case("A=BASE(0"),     # :2031 no closing ')'
    'b.eofdev':   case("A=EOF(0)"),        # :1095 EOF on channel 0
    'b.lofdev':   case("A=LOF(0)"),        # :1116 LOF on channel 0
    # controls: the same constructs, well formed
    'b.parenok':  case("A=(1+2)"),
    'b.vpok':     case("A=VARPTR(B)"),
    'b.baseok':   case("A=BASE(0)"),
}

BR = re.compile(r"\[([^\]]*)\]")
NUM = re.compile(r"^[-0-9. ]*$")


def face(cap):
    if cap is None:
        return "<NO CAPTURE>"
    for m in BR.finditer("".join(cap)):
        if NUM.match(m.group(1)):
            return " ".join(m.group(1).split()) or "<EMPTY>"
    return "<NO OUTPUT>"


def main():
    only, sides = None, ["vg8020", "cf3300", "zb"]
    for a in sys.argv[1:]:
        if a.startswith("--sides="):
            sides = [x for x in a.split("=", 1)[1].split(",") if x in SIDES]
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
            print(f"  ran {s:7s} {l}", flush=True)
    print()
    W = max(len(l) for l in labels)
    ndiff = 0
    for l in labels:
        vals = {s: faces[s][l] for s in sides}
        refs = {vals[s] for s in sides if s != "zb"}
        line = f"  {l:<{W}}  " + "  ".join(f"{s}={vals[s]!r}" for s in sides)
        if not refs:
            print(line + "   (zb only)")
            continue
        if len(refs) != 1:
            note = "   ⚠️ THE REFERENCES DISAGREE — not a want"
        elif any("<NO" in v for v in vals.values()):
            note = "   .... NOT MEASURED"
        elif vals["zb"] not in refs:
            note = "   🔴 DIFF"
            ndiff += 1
        else:
            note = ""
        print(line + note)
    print(f"\nROWS: {len(labels)} printed — {ndiff} DIFF")


if __name__ == "__main__":
    main()
