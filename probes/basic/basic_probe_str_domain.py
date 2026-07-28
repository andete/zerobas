#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-MISS-2 -- the string functions' ARGUMENT-DOMAIN checks, characterised.

WHY THIS EXISTS
===============
`CHR$` / `LEFT$` / `RIGHT$` / `MID$` accept out-of-range arguments SILENTLY and
compute a wrong answer, where the reference raises. Found by the MISSING-class
calibration battery (docs/missing-vg8020-characterization.md §8), which was not
looking for it. Those seven rows are enough to prove the defect and nowhere near
enough to state the RULE, which is what an implementation needs:

  * seven rows measured `-1`, `0`, `256`, `32768`, `99999` on SOME arguments and
    no argument's domain end-to-end. `LEFT$("abc",256)`, `MID$("abc",1,-1)` and
    `MID$("abc",256)` were never measured at all.
  * `MID$`'s position argument is the one member of the family whose legal
    domain is suspected to START AT 1, not 0 (`MID$("abc",0)` raises). If that
    is real it is NOT `get_byte_arg`'s rule and cannot be implemented by calling
    it, which changes the cost of the slice.
  * the family has TWO reference errors, not one -- `Illegal function call`
    inside int16, `Overflow` beyond it -- and the BOUNDARY between them was
    measured on `CHR$` alone.
  * whether the coercion TRUNCATES before the domain check decides
    `CHR$(255.9)` and `CHR$(-0.5)`, and neither has ever been run.

⚠️ IN-DOMAIN ROWS ARE NOT PADDING. Half this matrix is arguments that MUST keep
working. A domain check is the one kind of fix whose failure mode is rejecting
what it should accept, and a matrix of only out-of-range rows goes green on an
implementation that raises `Illegal function call` for everything.

⚠️ NOT ONE ROW MAY ARM `ON ERROR`. Same reason as
`basic_probe_abort_depth.py`: a handler selects `raise_error`'s TRAP branch,
which was always correct. These functions are evaluated from deep inside the
expression evaluator -- far below statement-handler depth -- so the UNTRAPPED
path is exactly the one at risk, and it is also the one a user sees. (`4d35b6d`
fixed the unwind for every depth; this probe is downstream of that and would
have been unreadable before it.)

⚠️ EVERY VALUE ROW IS BRACKET-DELIMITED (`PRINT "[";...;"]"`), because the junk
a half-aborted statement leaves can be WHITESPACE and a right-stripped scrape
reads that as clean.

⚠️ WIDTH 40 IS PINNED AND THE SOURCE STRING IS A VARIABLE. The two machines boot
at different text widths (reference 37, zerobas 39), and a direct line whose
ECHO WRAPS breaks the `screen_tail` readout silently -- the row then reports
`<no echo>` or, worse, agrees while measuring nothing. Pinning the width and
carrying the subject in `A$` keeps every line inside one row with margin.

Message CASE is folded before comparison: zerobas ships two spellings of the
same message on purpose (lowercase house style, and the reference-verbatim
capitalised text on the arrays path, basic/arrays.asm:44).
"""
from __future__ import annotations
import argparse, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl  # noqa: E402

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

COLS, ROWS = 40, 24

# Injected before the subject line of every case, so a boot-per-case run and a
# batched run see the same machine state.
PROLOGUE = ['WIDTH 40', 'A$="abc"', 'CLS']

# (label, battery, subject line). Batteries:
#   ctl   -- the mechanism exists and the readout works. READ FIRST.
#   in    -- arguments that MUST keep working (the anti-over-rejection half).
#   out   -- arguments the reference rejects.
#   ord   -- which argument is rejected first when more than one is bad.
CASES = [
    # --- controls -------------------------------------------------------------
    # `LEN("abc")` proves the readout; `ASC("")` proves an abort is reachable at
    # evaluator depth; STRING$/SPACE$ are the family members that ALREADY check,
    # and they are the working reference implementation of the two-stage rule.
    ("ctl-value",     "ctl", 'PRINT "[";LEN(A$);"]"'),
    ("ctl-ifc",       "ctl", 'PRINT "[";ASC("");"]"'),
    ("ctl-str-neg",   "ctl", 'PRINT "[";LEN(STRING$(-1,65));"]"'),
    ("ctl-str-256",   "ctl", 'PRINT "[";LEN(STRING$(256,65));"]"'),
    ("ctl-str-ovf",   "ctl", 'PRINT "[";LEN(STRING$(99999,65));"]"'),
    ("ctl-spc-neg",   "ctl", 'PRINT "[";LEN(SPACE$(-1));"]"'),
    ("ctl-spc-ovf",   "ctl", 'PRINT "[";LEN(SPACE$(99999));"]"'),

    # --- CHR$: in-domain, including the coercion rule -------------------------
    ("chr-in-0",      "in",  'PRINT "[";LEN(CHR$(0));"]"'),
    ("chr-in-65",     "in",  'PRINT "[";CHR$(65);"]"'),
    ("chr-in-255",    "in",  'PRINT "[";LEN(CHR$(255));"]"'),
    ("chr-trunc-lo",  "in",  'PRINT "[";CHR$(65.7);"]"'),
    ("chr-trunc-half","in",  'PRINT "[";CHR$(64.5);"]"'),
    # Does the coercion truncate BEFORE the domain check? 255.9 -> 255 is legal
    # if it does and out of range if it rounds; -0.5 -> 0 is legal if it
    # truncates toward zero and illegal if it floors. Never measured.
    ("chr-trunc-hi",  "in",  'PRINT "[";LEN(CHR$(255.9));"]"'),
    ("chr-trunc-neg", "in",  'PRINT "[";LEN(CHR$(-0.5));"]"'),
    # --- CHR$: out of domain, and the IFC/Overflow boundary -------------------
    ("chr-neg1",      "out", 'PRINT "[";LEN(CHR$(-1));"]"'),
    ("chr-256",       "out", 'PRINT "[";LEN(CHR$(256));"]"'),
    ("chr-32767",     "out", 'PRINT "[";LEN(CHR$(32767));"]"'),
    ("chr-32768",     "out", 'PRINT "[";LEN(CHR$(32768));"]"'),
    ("chr-neg32768",  "out", 'PRINT "[";LEN(CHR$(-32768));"]"'),
    ("chr-neg32769",  "out", 'PRINT "[";LEN(CHR$(-32769));"]"'),
    ("chr-99999",     "out", 'PRINT "[";LEN(CHR$(99999));"]"'),

    # --- LEFT$ ----------------------------------------------------------------
    ("left-in-0",     "in",  'PRINT "[";LEFT$(A$,0);"]"'),
    ("left-in-2",     "in",  'PRINT "[";LEFT$(A$,2);"]"'),
    ("left-in-9",     "in",  'PRINT "[";LEFT$(A$,9);"]"'),
    ("left-in-255",   "in",  'PRINT "[";LEFT$(A$,255);"]"'),
    ("left-neg1",     "out", 'PRINT "[";LEN(LEFT$(A$,-1));"]"'),
    ("left-256",      "out", 'PRINT "[";LEN(LEFT$(A$,256));"]"'),
    ("left-32768",    "out", 'PRINT "[";LEN(LEFT$(A$,32768));"]"'),
    ("left-99999",    "out", 'PRINT "[";LEN(LEFT$(A$,99999));"]"'),
    # An EMPTY source: does the domain check still fire when there is nothing to
    # slice? An implementation that checks only on the slicing path would pass
    # every row above and fail this one.
    ("left-empty-neg","out", 'PRINT "[";LEN(LEFT$("",-1));"]"'),

    # --- RIGHT$ ---------------------------------------------------------------
    ("right-in-0",    "in",  'PRINT "[";RIGHT$(A$,0);"]"'),
    ("right-in-2",    "in",  'PRINT "[";RIGHT$(A$,2);"]"'),
    ("right-in-9",    "in",  'PRINT "[";RIGHT$(A$,9);"]"'),
    ("right-in-255",  "in",  'PRINT "[";RIGHT$(A$,255);"]"'),
    ("right-neg1",    "out", 'PRINT "[";LEN(RIGHT$(A$,-1));"]"'),
    ("right-256",     "out", 'PRINT "[";LEN(RIGHT$(A$,256));"]"'),
    ("right-32768",   "out", 'PRINT "[";LEN(RIGHT$(A$,32768));"]"'),
    ("right-99999",   "out", 'PRINT "[";LEN(RIGHT$(A$,99999));"]"'),

    # --- MID$ position: the argument suspected of a 1-based domain ------------
    ("mid-p-in-1",    "in",  'PRINT "[";MID$(A$,1);"]"'),
    ("mid-p-in-3",    "in",  'PRINT "[";MID$(A$,3);"]"'),
    ("mid-p-in-4",    "in",  'PRINT "[";LEN(MID$(A$,4));"]"'),
    ("mid-p-in-255",  "in",  'PRINT "[";LEN(MID$(A$,255));"]"'),
    ("mid-p-0",       "out", 'PRINT "[";LEN(MID$(A$,0));"]"'),
    ("mid-p-neg1",    "out", 'PRINT "[";LEN(MID$(A$,-1));"]"'),
    ("mid-p-256",     "out", 'PRINT "[";LEN(MID$(A$,256));"]"'),
    ("mid-p-32768",   "out", 'PRINT "[";LEN(MID$(A$,32768));"]"'),
    ("mid-p-99999",   "out", 'PRINT "[";LEN(MID$(A$,99999));"]"'),

    # --- MID$ count: present only in the three-argument form ------------------
    # The two-argument form must NOT get a domain check: `n` is synthesised as
    # $FFFF ("to end") and checking that would reject every `MID$(A$,p)`.
    ("mid-n-in-0",    "in",  'PRINT "[";LEN(MID$(A$,1,0));"]"'),
    ("mid-n-in-2",    "in",  'PRINT "[";MID$(A$,1,2);"]"'),
    ("mid-n-in-9",    "in",  'PRINT "[";MID$(A$,1,9);"]"'),
    ("mid-n-in-255",  "in",  'PRINT "[";LEN(MID$(A$,1,255));"]"'),
    ("mid-n-neg1",    "out", 'PRINT "[";LEN(MID$(A$,1,-1));"]"'),
    ("mid-n-256",     "out", 'PRINT "[";LEN(MID$(A$,1,256));"]"'),
    ("mid-n-99999",   "out", 'PRINT "[";LEN(MID$(A$,1,99999));"]"'),

    # --- ORDER: which bad argument is reported when both are bad --------------
    # These pin the evaluation order the implementation must reproduce. If the
    # reference reports Overflow for the first and IFC for the second, the
    # checks run left-to-right ARGUMENT BY ARGUMENT rather than in two passes.
    ("ord-p-ovf",     "ord", 'PRINT "[";LEN(MID$(A$,99999,-1));"]"'),
    ("ord-p-ifc",     "ord", 'PRINT "[";LEN(MID$(A$,0,99999));"]"'),
    ("ord-type",      "ord", 'PRINT "[";LEN(LEFT$(1,-1));"]"'),
    # Domain vs the DEFERRED syntax error: `MID$(A$,0,)` is both out of domain
    # and malformed. Which one the reference reports says whether the domain
    # check may sit immediately after its own argument's eval (where the
    # trailing `)` has not been looked at yet) or must wait for the close.
    ("ord-syn",       "ord", 'PRINT "[";LEN(MID$(A$,0,));"]"'),

    # --- the int16 BOUNDARY, on the callers that already check ----------------
    # `chr-neg32768` reported Illegal function call and `chr-neg32769` reported
    # Overflow, so the reference's stage-1 gate is the int16 RANGE
    # (-32768..32767) and NOT the magnitude |x| <= 32767. zerobas's existing
    # `get_byte_arg` is documented as `fac_to_int_strict` + "FPERR set if
    # |x| > 32767", which would make -32768 an Overflow. If that is what it
    # does, every EXISTING caller (STRING$/SPACE$/ON/WIDTH) is already off by
    # one at that single value, and a D-MISS-2 fix built on `get_byte_arg`
    # inherits it. These rows are calibration, not subject.
    ("bnd-str-32767", "bnd", 'PRINT "[";LEN(STRING$(32767,65));"]"'),
    ("bnd-str-n32768","bnd", 'PRINT "[";LEN(STRING$(-32768,65));"]"'),
    ("bnd-str-n32769","bnd", 'PRINT "[";LEN(STRING$(-32769,65));"]"'),
    ("bnd-spc-n32768","bnd", 'PRINT "[";LEN(SPACE$(-32768));"]"'),
    ("bnd-left-32767","bnd", 'PRINT "[";LEN(LEFT$(A$,32767));"]"'),
    ("bnd-left-n32768","bnd",'PRINT "[";LEN(LEFT$(A$,-32768));"]"'),
    ("bnd-mid-n32768","bnd", 'PRINT "[";LEN(MID$(A$,-32768));"]"'),

    # --- the MID$ STATEMENT: a SECOND surface with the same arguments ---------
    # `MID$(A$,p[,n])=B$` is a different code path (basic/str-engine.asm, the
    # assignment statement) from the MID$ FUNCTION. It takes the same two
    # numeric arguments, so it has the same domain question -- and a slice that
    # fixes only the function would leave half the surface silently wrong.
    # Whether it is IN scope is a sign-off question; whether it is BROKEN is
    # measured here.
    ("stmt-p-in-1",   "stmt", 'MID$(A$,1)="X":PRINT "[";A$;"]"'),
    ("stmt-p-0",      "stmt", 'MID$(A$,0)="X":PRINT "[";A$;"]"'),
    ("stmt-p-neg1",   "stmt", 'MID$(A$,-1)="X":PRINT "[";A$;"]"'),
    ("stmt-p-256",    "stmt", 'MID$(A$,256)="X":PRINT "[";A$;"]"'),
    ("stmt-p-99999",  "stmt", 'MID$(A$,99999)="X":PRINT "[";A$;"]"'),
    # p PAST the end of A$ is a range error too (`n>La`, which zerobas already
    # detects sub-side) -- so the statement's error CODE has to be right for a
    # case that is neither 0 nor out of byte range, and `ems_range` currently
    # funnels all three into one `stmt_error`.
    ("stmt-p-past",   "stmt", 'MID$(A$,4)="X":PRINT "[";A$;"]"'),
    ("stmt-p-255",    "stmt", 'MID$(A$,255)="X":PRINT "[";A$;"]"'),
    ("stmt-n-0",      "stmt", 'MID$(A$,1,0)="X":PRINT "[";A$;"]"'),
    ("stmt-n-in-1",   "stmt", 'MID$(A$,1,1)="XY":PRINT "[";A$;"]"'),
    ("stmt-n-neg1",   "stmt", 'MID$(A$,1,-1)="X":PRINT "[";A$;"]"'),
    ("stmt-n-256",    "stmt", 'MID$(A$,1,256)="X":PRINT "[";A$;"]"'),
    ("stmt-n-99999",  "stmt", 'MID$(A$,1,99999)="X":PRINT "[";A$;"]"'),

    # --- the REST of the string engine's numeric arguments (S-SD-3) -----------
    # "No silent row is on record" is exactly how D-MISS-2 itself survived the
    # SILENT-GAP sweep, so the rest of the family is MEASURED rather than
    # assumed clean. INSTR's start position is a 1-based argument of the same
    # kind §2.3 found wrong in MID$, which makes it the prime suspect.
    ("ext-instr-in",  "ext", 'PRINT "[";INSTR(1,A$,"b");"]"'),
    ("ext-instr-0",   "ext", 'PRINT "[";INSTR(0,A$,"b");"]"'),
    ("ext-instr-neg", "ext", 'PRINT "[";INSTR(-1,A$,"b");"]"'),
    ("ext-instr-256", "ext", 'PRINT "[";INSTR(256,A$,"b");"]"'),
    ("ext-instr-ovf", "ext", 'PRINT "[";INSTR(99999,A$,"b");"]"'),
    ("ext-str-chr-n", "ext", 'PRINT "[";LEN(STRING$(5,-1));"]"'),
    ("ext-str-chr-o", "ext", 'PRINT "[";LEN(STRING$(5,99999));"]"'),
    ("ext-spc-256",   "ext", 'PRINT "[";LEN(SPACE$(256));"]"'),
    ("ext-hex-neg",   "ext", 'PRINT "[";HEX$(-1);"]"'),
    ("ext-hex-ovf",   "ext", 'PRINT "[";HEX$(99999);"]"'),
    ("ext-oct-neg",   "ext", 'PRINT "[";OCT$(-1);"]"'),
    ("ext-oct-ovf",   "ext", 'PRINT "[";OCT$(99999);"]"'),
]


def norm(s):
    """Fold message case (the documented two-spelling divergence). Runs of
    spaces are COLLAPSED but never dropped, so whitespace-only junk still
    differs from no junk at all."""
    if s is None:
        return None
    return " ".join(s.casefold().replace("|", " | ").split())


def tail_of(raw, line):
    if raw is None:
        return None
    t = omsx_repl.screen_tail(raw, line)
    return t if t is not None else "<no echo>"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default=REF_MACHINE)
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--only")
    ap.add_argument("--boot-per-case", dest="boot_per_case", action="store_true",
                    help="force boot-per-case on every row (the isolation "
                         "escape hatch; the default already self-heals any row "
                         "that disagrees)")
    ap.add_argument("--gate", action="store_true",
                    help="fail on any divergence; without it every row is "
                         "reported as a straight differential")
    args = ap.parse_args()

    sel = [c for c in CASES if not args.only or args.only in c[0]]
    if not sel:
        print("APPARATUS FAILURE: no rows selected")
        return 1
    specs = [("direct", PROLOGUE + [line]) for _, _, line in sel]

    def compare(i, rr, zz):
        rt, zt = tail_of(rr, sel[i][2]), tail_of(zz, sel[i][2])
        return rt is not None and zt is not None and norm(rt) == norm(zt)

    verdicts, ref_raws, zb_raws = omsx_repl.run_differential(
        args.machine, args.zb_machine, specs, compare,
        batch=not args.boot_per_case, reset=())

    npass = 0
    for i, (label, battery, line) in enumerate(sel):
        rt, zt = tail_of(ref_raws[i], line), tail_of(zb_raws[i], line)
        ok = verdicts[i]
        npass += 1 if ok else 0
        print(f"{'PASS' if ok else 'FAIL':5} {battery:4} {label:15} {line[:34]:34}")
        print(f"        ref: {rt!r}")
        if not ok:
            print(f"        zb : {zt!r}")
        sys.stdout.flush()

    ntot = len(sel)
    print(f"\n{npass}/{ntot} rows agree with the reference")
    # The control battery is read FIRST and separately: if a control diverges,
    # nothing else in the run may be read as a finding about CHR$/LEFT$/RIGHT$/
    # MID$ -- it is a statement about the apparatus or the abort chain.
    bad_ctl = [sel[i][0] for i in range(ntot)
               if sel[i][1] == "ctl" and not verdicts[i]]
    if bad_ctl:
        print(f"⚠️ CONTROL ROWS DIVERGED ({', '.join(bad_ctl)}) — no other row in "
              f"this run is readable as a D-MISS-2 finding")
        return 1
    if args.gate and npass != ntot:
        print("SOME FAILED")
        return 1
    print("ALL PASS" if npass == ntot else "REPORTED (not gated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
