#!/usr/bin/env python3
"""D-CLRFIX -- CLEAR's two dangling-argument defects, and the controls for both.

Two open TODO items, one file:

  🔴 `CLEAR 200,` raises the RIGHT error and LOSES THE TRAP. clr_himem is
     `call eval` / `ld (HIMEM),de` with NO FPERR test; D-MISSOPFIX made that
     eval DEFER ERR 24, so the store happens, clr_done falls into clear_vars,
     the WIPE takes the ON ERROR trap, and exec_stmt raises into a machine
     with no handler.
  🔴 `CLEAR ,200` is Syntax error on both references and COMPLETES SILENTLY
     here -- ex_clear's own `cp ',' / jr z,clr_himem` accepts a form neither
     reference has.

Readout `[ERR 0]` from an ON ERROR GOTO handler. A pre-marker `<A>` prints
BEFORE the statement, so "the machine died AT the CLEAR" is distinguishable
from "the program never ran".

🔴 AN UNTRAPPED ABORT IS A READING, NOT A MISSING ONE -- and the alternation
below must be COMPLETE or the hole just moves one message along
([[an-unnamed-outcome-reads-as-no-outcome]], which fired twice in one
afternoon on this exact row family).
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


def tcase(stmt):
    return ["10 ONERRORGOTO900",
            '20 PRINT"<A>";',
            f"30 {stmt}",
            '40 PRINT"[";ERR;0;"]":END',
            '900 PRINT"[";ERR;0;"]":END']


CASES = {
    # --- the trailing comma: a comma consumed, then nothing --------------
    'q.trail':   tcase("CLEAR 200,"),
    'q.kcolon':  tcase("CLEAR 200,:A=1"),
    # --- the LEADING comma: a form neither reference accepts --------------
    'q.comma':   tcase("CLEAR ,200"),
    'q.commak':  tcase("CLEAR ,200:A=1"),
    'q.conly':   tcase("CLEAR ,"),          # NEW: both slots dangling at once
    # --- the SAME guard, other fault codes: does the slot defer THOSE too? -
    'q.div':     tcase("CLEAR 200,1/0"),    # NEW: FPERR=2 in the HIMEM slot
    'q.str':     tcase('CLEAR 200,"x"'),    # NEW: a TYPE fault in the HIMEM slot
    'q.ovf':     tcase("CLEAR 200,70000"),  # NEW: past int16 in the HIMEM slot
    # --- controls: every legal shape must keep completing ------------------
    'q.ok':      tcase("CLEAR 200"),
    'q.both':    tcase("CLEAR 200,&H9000"),
    'q.bare':    tcase("CLEAR"),
    'q.kbare':   tcase("CLEAR:A=1"),
    # --- 🔴 THE CHARACTERIZATION'S OWN STATEMENTS, VERBATIM ----------------
    # docs/clearpool-vg8020-characterization.md §2.4 and §2.8 record REFERENCE
    # readings for `CLEAR ,&HD000` and conclude "the ,himem-only form does not
    # resize the pool". If that form is a SYNTAX ERROR on the reference -- as
    # `CLEAR ,200` measured -- then the pool is unchanged because the statement
    # NEVER RAN, and three rows agree for the wrong reason. The hex constant is
    # the only difference from q.comma, so it is run rather than assumed.
    'z.hd000':   tcase("CLEAR ,&HD000"),
    'z.seq':     tcase("CLEAR 500:CLEAR ,&HD000"),   # §2.4's row, verbatim
    'z.neg':     tcase("CLEAR 200,-1"),              # the HIMEM slot's negative end
    # --- the trap control: the same fault with no CLEAR in front of it ----
    't.notrap':  ["10 ONERRORGOTO900", '20 PRINT"<A>";',
                  "40 A=1/0", '50 PRINT"[";ERR;0;"]":END',
                  '900 PRINT"[";ERR;0;"]":END'],
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
                batch=False, boot=cfg["boot"], step=3.0, cap_gap=8.0,
                timeout=300.0)
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
