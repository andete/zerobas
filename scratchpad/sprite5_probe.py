#!/usr/bin/env python3
"""D-SPRITE5 -- PUT SPRITE's 5th-argument error: place THEN raise, or raise?

Third verb from the generic error-layer seam (after D-SWAP3, D-PAINT4).
`PUT SPRITE p,(x,y),c,n,<trailing>` PLACES the sprite then raises ERR 2 on both
references; zerobas raises ERR 2 BEFORE placing via a bespoke gfx_syntax check
(graphics.asm:1250) above pspr_go. pspr_go guards the cursor (push hl / tenant /
pop hl) and jp exec_stmt's -- PAINT's exact shape -- so the fix is a DELETE.

READOUT `[ERR P]` under ON ERROR GOTO 900. P = VPEEK(&H1B00) = sprite-0 Y
attribute (SCREEN 2 attr table): 30 when placed at y=30, 209 when the plane is
untouched (the hidden-sprite Y). `UNTRAPPED <msg>` is a trappability reading.

🔴 THE REFERENCES DECIDE.
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

SETUP = "SCREEN2:SPRITE$(0)=STRING$(8,255)"
READ = "VPEEK(&H1B00)"


def case(stmt, read=READ):
    return ["10 ONERRORGOTO900",
            f"15 {SETUP}",
            f"20 {stmt}",
            f'30 P={read}:SCREEN0:CLS:PRINT"[";ERR;P;"]":END',
            f'900 P={read}:SCREEN0:CLS:PRINT"[";ERR;P;"]":END']


CASES = {
    # --- controls: legitimate forms PLACE (Y=30) and do not error ---------
    'sp.ok':     case("PUTSPRITE0,(20,30),1,0"),          # -> 0 30
    'sp.noc':    case("PUTSPRITE0,(20,30)"),              # coords only -> 0 30
    # sprite 0 untouched (place a DIFFERENT plane): pins "not placed" = 209 --
    'sp.none':   case("PUTSPRITE1,(40,50),1,0"),          # -> 0 209
    # --- THE SUBJECT: a trailing token after a COMPLETE argument list ------
    'sp.5comma': case("PUTSPRITE0,(20,30),1,0,"),         # trailing comma
    'sp.5arg':   case("PUTSPRITE0,(20,30),1,0,9"),        # a real 5th argument
    'sp.5colon': case("PUTSPRITE0,(20,30),1,0,:X=1"),     # trailing comma then stmt
    # --- incomplete arg lists: raise BEFORE the place (controls, KEEP) -----
    'sp.incomp': case("PUTSPRITE0,"),                     # missing coords -> ERR 2
    'sp.barep':  case("PUTSPRITE0"),                      # bare plane -> ERR 2
}

BR = re.compile(r"\[([^\]]*)\]")
NUM = re.compile(r"^[-0-9. ]*$")
ERRMSG = re.compile(r"(Missing operand|Syntax error|Illegal function call|"
                    r"Type mismatch|Overflow|Out of memory|Undefined line number|"
                    r"Division by zero|Bad file mode|File not found)\s+in\s+(\d+)")


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
                batch=False, boot=cfg["boot"], step=6.0, cap_gap=12.0,
                timeout=400.0)
            faces[s][l] = face(caps[0])
            print(f"  ran {s:7s} {l:9s} {faces[s][l]!r}", flush=True)
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
            print(line + "   !! REFS DISAGREE"); continue
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
