#!/usr/bin/env python3
"""D-DEFERBLIND scout — what ELSE is left standing when a fault is IMMEDIATE?

D-DEFFNKNIFE's K-FE1 found that `raise_error`'s FN_FEND reset had no witness,
because every error row in the DEF FN set provokes a DEFERRED fault:
`fp_runtime_error`'s header says the float ops "have no mid-expression unwind,
only SET FPERR and yield a defined value (0)" and the abort is "realized at the
statement boundary". A deferred fault therefore lets every construct it is
nested inside EXIT NORMALLY first, and only then raises.

📏 THE SOURCE SPLIT, COUNTED: 21 call sites of `penderr_set` (the deferred-error
write) across basic/ and sub/. Exactly ONE (`str_heap_oom_error`,
str-engine.asm:90) follows it with `jp fp_runtime_error`; the other 20 RETURN.
So overflow, division by zero, illegal function call, syntax, subscript, OOM,
redimension and type mismatch can EACH arrive deferred or immediate depending
on the SITE -- the ERR code tells you nothing, and neither does the prose.

🎯 THE CLASS, STATED PRECISELY. `exec_stmt` opens every statement with
`xor a / ld (PRDEST),a`, so PRDEST cannot be left stale by any fault: the
handler's first statement resets it. FN_FEND is NOT reset there -- which is why
it needed its own store in raise_error, and why removing that store was
invisible. So the class is:

    a RAM cell that says "we are inside X", cleared by X's NORMAL exit,
    not cleared at the statement boundary, and reachable by a fault that
    raises BEFORE X's normal exit.

This scout asks the machines which constructs are in that class, using an
IMMEDIATE fault (`FNZ(0)` -- an undefined user function is ERR 18 raised on the
spot, available on every MSX1 and needing no DEF FN of our own) against the
same program with a DEFERRED one (`1/0`) as the separating control. If the two
columns differ on any machine, the deferral is what separates them.

🔴 THE REFERENCES DECIDE. Nothing here is predicted; a row whose two reference
machines disagree is NOT a want and is reported as such.
"""
from __future__ import annotations

import os
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

IMM = "X=FNZ(0)"        # ERR 18, raised on the spot by the DEF FN tenant
DEF = "X=1/0"           # ERR 11, deferred to the statement boundary

# Each program prints ONE fenced value. The fall-through prints nothing, so a
# row that produced no value reads <NO OUTPUT> -- a missing measurement, which
# is not a divergence and must not read as agreement.
def forloop(fault):
    return ['10 ON ERROR GOTO 800',
            '20 FOR I=1 TO 3',
            f'30 {fault}',
            '40 S=S+I',
            '50 NEXT I',
            '60 CLS:PRINT"[";S;"]":END',
            '800 RESUME NEXT']


def gosub(fault):
    return ['10 ON ERROR GOTO 800',
            '20 GOSUB 100',
            '30 CLS:PRINT"[BACK]":END',
            f'100 {fault}',
            '110 RETURN',
            '800 RESUME NEXT']


def strheap(fault):
    return ['10 ON ERROR GOTO 800',
            '20 F=FRE("")',
            '30 FOR I=1 TO 5',
            f'40 A$="ab"+"cd":{fault}',
            '50 NEXT I',
            '60 CLS:PRINT"[";F-FRE("");"]":END',
            '800 RESUME NEXT']


def fnframe(fault):
    """THE KNOWN POSITIVE. FN_FEND says "a DEF FN call is in progress" and is
    cleared by fn_leave's ordinary restore -- not at the statement boundary. A
    fault that raises BEFORE fn_leave leaves it standing, and every later
    reference to the formal's NAME then reads the dead slot. This is the one
    member of the class that is known to exist, so it is what says the row
    SHAPE below can detect a member at all: under K-FE1 (raise_error's reset
    disabled) `fn.imm` must go RED while every other row stays green."""
    return ['10 ON ERROR GOTO 800',
            '20 X=5',
            f'30 DEF FNA(X)={fault}',
            '40 Y=FNA(2)',
            '60 CLS:PRINT"[";X;"]":END',
            '800 RESUME 60']


CASES = {
    # the DEF FN shadow frame -- the CALIBRATION row, not a subject
    'fn.imm':       fnframe('FNZ(0)'),            # ERR 18 from inside a live frame
    'fn.def':       fnframe('X/0'),               # separating control (deferred)
    'fn.ctl':       ['10 ON ERROR GOTO 800',
                     '20 X=5',
                     '30 DEF FNA(X)=X+1',
                     '40 Y=FNA(2)',
                     '60 CLS:PRINT"[";X;"]":END',
                     '800 RESUME 60'],
    # the FOR stack: does a trapped IMMEDIATE fault inside the body leave NEXT
    # able to find its frame?  6 = the loop ran all three times.
    'for.imm':      forloop(IMM),
    'for.def':      forloop(DEF),                 # separating control
    'for.ctl':      ['10 ON ERROR GOTO 800',      # no fault at all
                     '20 FOR I=1 TO 3',
                     '40 S=S+I',
                     '50 NEXT I',
                     '60 CLS:PRINT"[";S;"]":END',
                     '800 RESUME NEXT'],
    # the GOSUB stack: can RETURN still find its frame after a trapped fault?
    'gos.imm':      gosub(IMM),
    'gos.def':      gosub(DEF),                   # separating control
    'gos.ctl':      ['10 ON ERROR GOTO 800',
                     '20 GOSUB 100',
                     '30 CLS:PRINT"[BACK]":END',
                     '100 X=1',
                     '110 RETURN',
                     '800 RESUME NEXT'],
    # the string temp descriptors: does a fault mid string-expression leak?
    # 0 = nothing lost across five faulting iterations.
    'fre.imm':      strheap(IMM),
    'fre.def':      strheap(DEF),                 # separating control
    'fre.ctl':      ['10 ON ERROR GOTO 800',
                     '20 F=FRE("")',
                     '30 FOR I=1 TO 5',
                     '40 A$="ab"+"cd":X=1',
                     '50 NEXT I',
                     '60 CLS:PRINT"[";F-FRE("");"]":END',
                     '800 RESUME NEXT'],
}

import re                                                          # noqa: E402
BR = re.compile(r"\[([^\]]*)\]")


def face(cap):
    if cap is None:
        return "<NO CAPTURE>"
    m = BR.search("".join(cap))
    return " ".join(m.group(1).split()) if m else "<NO OUTPUT>"


def main():
    args = [a for a in sys.argv[1:]]
    only = None
    sides = ["vg8020", "cf3300", "zb"]
    for a in args:
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
                cfg["machine"], [("direct", list(cfg["reset"]) + CASES[l]
                                  + ["RUN"])],
                batch=False, boot=cfg["boot"], step=8.0, cap_gap=10.0,
                timeout=300.0)
            faces[s][l] = face(caps[0])
            print(f"  ran {s:7s} {l}", flush=True)
    print()
    W = max(len(l) for l in labels)
    for l in labels:
        vals = {s: faces[s][l] for s in sides}
        refs = {vals[s] for s in sides if s != "zb"}
        note = ""
        if not refs:
            note = "   (zb only -- no reference column in this run)"
            print(f"  {l:<{W}}  "
                  + "  ".join(f"{s}={vals[s]!r}" for s in sides) + note)
            continue
        if len(refs) != 1:
            note = "   ⚠️ THE REFERENCES DISAGREE — not a want"
        elif "<NO" in vals["zb"] or any("<NO" in v for v in vals.values()):
            note = "   .... NOT MEASURED (blank reading, not a divergence)"
        elif vals["zb"] not in refs:
            note = "   🔴 DIFF"
        print(f"  {l:<{W}}  " + "  ".join(f"{s}={vals[s]!r}" for s in sides)
              + note)
    print(f"\nROWS: {len(labels)} printed")


if __name__ == "__main__":
    main()
