#!/usr/bin/env python3
"""D-PAINT4 -- PAINT's trailing-token Syntax error: fill THEN raise, or raise?

TODO.md, filed by D-DUPSPAN §6.1: `SCREEN 2:PAINT(10,10),9,15,` then reading a
pixel -- both references FILL (POINT reads the paint colour) and THEN raise
ERR 2; zerobas raises ERR 2 BEFORE filling (POINT reads the background). Same
class as D-SWAP3: a bespoke trailing-token check (`ep_syntax`, graphics.asm:798)
raises above `ep_draw` instead of letting exec_stmt's boundary reject the
leftover after the draw. The fix candidate is to DELETE the check and delegate.

READOUT `[ERR P]` under ON ERROR GOTO 900. P = POINT(10,10) (the seed pixel),
read in SCREEN 2 BEFORE the SCREEN0:CLS -- so P is the paint colour iff the fill
happened. `UNTRAPPED <msg> in <line>` is a trappability reading, not a blank.

🔴 THE REFERENCES DECIDE. Rows where the two references disagree are not wants.
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


# ⚠️ TIMING IS PART OF THE MEASUREMENT. A PAINT flood is genuinely slow in
# emulated time (paintmc uses step=90 for a full-screen flood). So the fill is
# BOUNDED to a tiny 10x10 box drawn with border colour 15, and the seed (15,15)
# is read back -- a ~64-pixel fill completes fast enough for a modest step.
BOX = "SCREEN2:LINE(10,10)-(20,20),15,B"


def case(stmt, read="POINT(15,15)"):
    """The box is drawn on line 15; the seed pixel is read on BOTH exits in
    SCREEN 2, before SCREEN0:CLS clears VRAM and the fence prints on text."""
    return ["10 ONERRORGOTO900",
            f"15 {BOX}",
            f"20 {stmt}",
            f'30 P={read}:SCREEN0:CLS:PRINT"[";ERR;P;"]":END',
            f'900 P={read}:SCREEN0:CLS:PRINT"[";ERR;P;"]":END']


CASES = {
    # --- controls: legitimate forms must DRAW (P=9) and not error --------
    'pa.color':  case("PAINT(15,15),9,15"),       # -> 0 9 (colour 9, border 15)
    'pa.plain':  case("PAINT(15,15)"),            # default colour, bounded fill
    # a drawn-but-unpainted box: pins what "not filled" reads inside -------
    'pa.nopnt':  ["10 ONERRORGOTO900", f"15 {BOX}",
                  '30 P=POINT(15,15):SCREEN0:CLS:PRINT"[";ERR;P;"]":END',
                  '900 P=POINT(15,15):SCREEN0:CLS:PRINT"[";ERR;P;"]":END'],
    # --- THE SUBJECT: a trailing token after a COMPLETE argument list ------
    'pa.4comma': case("PAINT(15,15),9,15,"),      # trailing comma (the filed row)
    'pa.4arg':   case("PAINT(15,15),9,15,7"),     # a real 4th argument
    'pa.4colon': case("PAINT(15,15),9,15,:X=1"),  # trailing comma then a stmt
    # --- incomplete arg lists: raise BEFORE the fill (controls) -----------
    'pa.3comma': case("PAINT(15,15),9,"),         # missing border -> ERR 24
    'pa.ccomma': case("PAINT(15,15),9,,"),        # doubled comma (site :748) -> ERR 2
}

BR = re.compile(r"\[([^\]]*)\]")
NUM = re.compile(r"^[-0-9. ]*$")
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
                batch=False, boot=cfg["boot"], step=90.0, cap_gap=20.0,
                timeout=600.0)
            faces[s][l] = face(caps[0])
            print(f"  ran {s:7s} {l:9s} {faces[s][l]!r}", flush=True)
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
