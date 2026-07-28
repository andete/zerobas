#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WID -- `WIDTH n`'s VALID DOMAIN, characterised against the VG-8020.

WHY THIS EXISTS
===============
`4d35b6d` (the abort-depth slice) fixed the way `WIDTH 300` FAILED: the reject
now unwinds instead of returning into `ex_width` with A = the error code. It
deliberately did not open the question of which n `WIDTH` should ACCEPT --
docs/spec-basic-abort-depth.md §7 records that as "a separate question this
slice does not open". This probe opens it.

The defect hypothesis is legible in the source. `ex_width`
(basic/screen.asm:169) evaluates its argument, runs it through `get_byte_arg`
-- whose whole domain is 0..255 -- and then writes `LINLEN`, the active mode's
per-mode default (`LINL40`/`LINL32`) and calls `CHGMOD` UNCONDITIONALLY. There
is no bound anywhere, and no mode-dependence: text-1 is 40 columns wide and
text-2 is 32, so on the reference the legal n cannot be the same in both. If
the hypothesis holds, `WIDTH 200` today leaves the display exactly as unusable
as `WIDTH 300` did before `4d35b6d` -- the same severe symptom, reached through
the ACCEPT path instead of the reject path, and so untouched by that fix.

⚠️ THE SUBJECT UNDER TEST MOVES THE INSTRUMENT. Every other probe in this tree
reads a 40-column SCREEN-0 name table at a fixed stride of 40 bytes per row
(omsx_repl.COLS). `WIDTH` is the one statement whose entire job is to change
that stride: after `WIDTH 32` the console driver lays rows down 32 bytes apart
while the VDP still displays 40 per row, so the scrape shears and EVERY row
readout -- echo anchor included -- silently stops meaning anything. This is the
same class of trap as the echo-anchored readout that could not measure a
statement which moves the cursor (docs/spec-basic-missing-class.md), and it is
why this probe does NOT read the screen for its main batteries. Instead:

  * the subject runs inside a stored program;
  * the outcome is captured into NUMERIC variables (the trapped `ERR` code and
    the three width sysvars) while the screen is still wrong;
  * the program then RESTORES `SCREEN 0` + `WIDTH 40`, which re-inits the
    display through CHGMOD and so hands the capture back a 40-column screen;
  * only then does it `PRINT` the bracket-delimited readout.

So the readout is width-independent by construction, and it is also
self-healing: a case that completes leaves the machine at SCREEN 0 / WIDTH 40
for the next one.

⚠️ THE `dom` BATTERIES ARM `ON ERROR` ON PURPOSE, and that is the opposite of
the rule in basic_probe_abort_depth.py / basic_probe_str_domain.py. Those two
measure the UNWIND, which a handler hides. This probe measures the DOMAIN --
which n is rejected and with which code -- and a trapped `ERR` read is the only
readout that survives a statement that has just destroyed the screen. The
unwind is not re-litigated here; it is already gated by `make abort-acceptance`.
The `unt` battery keeps a handful of untrapped rows anyway, as the seam between
the two gates.

⚠️ THE SYSVARS ARE THE POINT, NOT THE ERROR CODE. "Did it raise?" and "did it
write the width anyway?" are different questions, and an implementation that
gets the first right and the second wrong still corrupts the screen. `LINLEN`
($F3B0), `LINL40` ($F3AE) and `LINL32` ($F3AF) are read BEFORE the restore, so
a reject that has already scribbled on them is visible. All three are published
MSX system variables (MSX2 Technical Handbook); nothing here is disassembled.

⚠️ IN-DOMAIN ROWS ARE NOT PADDING. A bound check's failure mode is rejecting
what it should accept, and a matrix of only out-of-range rows goes green on an
implementation that raises `Illegal function call` for every n.

Message CASE is folded before comparison (the documented two-spelling split,
basic/arrays.asm:44).
"""
from __future__ import annotations
import argparse, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl  # noqa: E402

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

# --- the trapped readout program --------------------------------------------
# Line numbers are positional (omsx_repl stored mode numbers bodies 10,20,...),
# so the handler's line number is fixed by its position in this list.
#   10 SCREEN 1:WIDTH 32           -- PIN the instrument: LINL32 = 32 ...
#   20 SCREEN 0:WIDTH 40           -- ... and LINL40 = 40, on BOTH machines
#   30 <mode>                      -- the screen mode under test
#   40 ON ERROR GOTO 100
#   50 E=0:<subject>               -- the WIDTH under test
#   60 L=PEEK(LINLEN):M=PEEK(LINL40)
#   70 N=PEEK(LINL32)
#   80 SCREEN 0:WIDTH 40           -- restore the INSTRUMENT before any output
#   90 PRINT"[";E;L;M;N;"]":END
#  100 E=ERR:RESUME 60             -- resume at the capture, never at the subject
#
# ⚠️ LINES 10-20 ARE THE WHOLE REASON THIS PROBE IS READABLE. The two machines
# boot at DIFFERENT text widths (reference 37, zerobas 39 -- the same asymmetry
# basic_probe_str_domain.py pins around), and both LINL40 and LINL32 carry that
# difference into the readout. Without the pin, three control rows that never
# execute a WIDTH at all diverged on width alone while their ERR codes agreed:
# the probe would have reported a defect in `WIDTH`'s domain that was really the
# boot default. The pin also gives every reject row a KNOWN prior LINLEN, which
# is what makes "did the reject scribble on the sysvars anyway?" a question the
# readout can answer.
def trapped(mode: str, subject: str) -> list[str]:
    return [
        "SCREEN 1:WIDTH 32",
        "SCREEN 0:WIDTH 40",
        mode,
        "ON ERROR GOTO 100",
        "E=0:" + subject,
        "L=PEEK(&HF3B0):M=PEEK(&HF3AE)",
        "N=PEEK(&HF3AF)",
        "SCREEN 0:WIDTH 40",
        'PRINT"[";E;L;M;N;"]":END',
        "E=ERR:RESUME 60",
    ]


# (label, battery, mode, subject). Batteries:
#   ctl -- the apparatus. READ FIRST; nothing else is readable if one diverges.
#   s0  -- SCREEN 0 (text-1, 40 columns): where is the upper bound, and is 0 legal?
#   s1  -- SCREEN 1 (text-2, 32 columns): is the bound MODE-DEPENDENT?
#   s2  -- SCREEN 2 (graphics): is WIDTH accepted at all, and what does it record?
#   co  -- coercion: truncate-before-check, and the int16/byte error boundary.
#   sx  -- the syntax surface (bare WIDTH, empty argument, trailing comma).
#   pe  -- persistence: does an accepted width survive a mode switch?
CASES = [
    # --- controls -------------------------------------------------------------
    # ctl-noop-s0/s1 are THE instrument check: a subject that touches nothing,
    # so the readout must be exactly the pinned state in each mode. They are the
    # rows that caught the un-pinned first draft of this probe.
    # ctl-ifc / ctl-ovf / ctl-syn prove the trapped readout actually captures a
    # code, and that all three codes this slice cares about are distinguishable
    # through it -- with the width now held constant so only ERR can move.
    ("ctl-noop-s0", "ctl", "SCREEN 0",  "X=1"),
    ("ctl-noop-s1", "ctl", "SCREEN 1",  "X=1"),
    ("ctl-ifc",     "ctl", "SCREEN 0",  'X=ASC("")'),
    ("ctl-ovf",     "ctl", "SCREEN 0",  "X=1E38*1E38"),
    ("ctl-syn",     "ctl", "SCREEN 0",  "X=VAL"),
    # The restore itself is load-bearing: this row sets a width the readout
    # cannot survive and then relies on line 60 to hand back a readable screen.
    # If it reports a value at all, the apparatus works. If it reports <none>,
    # nothing below that needs the restore may be read.
    ("ctl-restore", "ctl", "SCREEN 0",  "WIDTH 20"),

    # --- SCREEN 0: text-1, 40 columns ----------------------------------------
    ("s0-0",        "s0",  "SCREEN 0",  "WIDTH 0"),
    ("s0-1",        "s0",  "SCREEN 0",  "WIDTH 1"),
    ("s0-2",        "s0",  "SCREEN 0",  "WIDTH 2"),
    ("s0-29",       "s0",  "SCREEN 0",  "WIDTH 29"),
    ("s0-32",       "s0",  "SCREEN 0",  "WIDTH 32"),
    ("s0-39",       "s0",  "SCREEN 0",  "WIDTH 39"),
    ("s0-40",       "s0",  "SCREEN 0",  "WIDTH 40"),
    ("s0-41",       "s0",  "SCREEN 0",  "WIDTH 41"),
    ("s0-42",       "s0",  "SCREEN 0",  "WIDTH 42"),
    ("s0-80",       "s0",  "SCREEN 0",  "WIDTH 80"),
    ("s0-200",      "s0",  "SCREEN 0",  "WIDTH 200"),
    ("s0-255",      "s0",  "SCREEN 0",  "WIDTH 255"),
    ("s0-256",      "s0",  "SCREEN 0",  "WIDTH 256"),
    ("s0-300",      "s0",  "SCREEN 0",  "WIDTH 300"),
    ("s0-neg1",     "s0",  "SCREEN 0",  "WIDTH -1"),

    # --- SCREEN 1: text-2, 32 columns ----------------------------------------
    ("s1-0",        "s1",  "SCREEN 1",  "WIDTH 0"),
    ("s1-1",        "s1",  "SCREEN 1",  "WIDTH 1"),
    ("s1-29",       "s1",  "SCREEN 1",  "WIDTH 29"),
    ("s1-32",       "s1",  "SCREEN 1",  "WIDTH 32"),
    ("s1-33",       "s1",  "SCREEN 1",  "WIDTH 33"),
    ("s1-40",       "s1",  "SCREEN 1",  "WIDTH 40"),
    ("s1-41",       "s1",  "SCREEN 1",  "WIDTH 41"),
    ("s1-255",      "s1",  "SCREEN 1",  "WIDTH 255"),
    ("s1-256",      "s1",  "SCREEN 1",  "WIDTH 256"),

    # --- SCREEN 2: graphics. Is WIDTH legal here, and which default does it
    # record? zerobas writes LINL32 for every non-zero SCRMOD, which is a guess.
    ("s2-1",        "s2",  "SCREEN 2",  "WIDTH 1"),
    ("s2-32",       "s2",  "SCREEN 2",  "WIDTH 32"),
    ("s2-33",       "s2",  "SCREEN 2",  "WIDTH 33"),
    ("s2-40",       "s2",  "SCREEN 2",  "WIDTH 40"),
    ("s2-41",       "s2",  "SCREEN 2",  "WIDTH 41"),
    ("s2-256",      "s2",  "SCREEN 2",  "WIDTH 256"),
    ("s3-32",       "s2",  "SCREEN 3",  "WIDTH 32"),
    ("s3-41",       "s2",  "SCREEN 3",  "WIDTH 41"),
    # The low end and the negative end, in the modes the first matrix only
    # measured at the TOP. A bound is two-sided and only one side was covered.
    ("s2-0",        "s2",  "SCREEN 2",  "WIDTH 0"),
    ("s1-neg1",     "s1",  "SCREEN 1",  "WIDTH -1"),
    ("s2-neg1",     "s2",  "SCREEN 2",  "WIDTH -1"),

    # --- coercion and the two error codes ------------------------------------
    # The str-domain slice measured this rule for the string family: coercion
    # truncates toward zero BEFORE the domain check, the int16 gate is the RANGE
    # -32768..32767 (not |x|<=32767), and beyond it the error is Overflow rather
    # than Illegal function call. WIDTH goes through the same `get_byte_arg`, so
    # the same rule is PREDICTED here -- and predicted is not measured.
    ("co-40.7",     "co",  "SCREEN 0",  "WIDTH 40.7"),
    ("co-40.5",     "co",  "SCREEN 0",  "WIDTH 40.5"),
    ("co-0.5",      "co",  "SCREEN 0",  "WIDTH 0.5"),
    ("co-neg0.5",   "co",  "SCREEN 0",  "WIDTH -0.5"),
    ("co-32767",    "co",  "SCREEN 0",  "WIDTH 32767"),
    ("co-32768",    "co",  "SCREEN 0",  "WIDTH 32768"),
    ("co-n32768",   "co",  "SCREEN 0",  "WIDTH -32768"),
    ("co-n32769",   "co",  "SCREEN 0",  "WIDTH -32769"),
    ("co-99999",    "co",  "SCREEN 0",  "WIDTH 99999"),
    ("co-expr",     "co",  "SCREEN 0",  "WIDTH 20+12"),
    ("co-str",      "co",  "SCREEN 0",  'WIDTH "40"'),
    # A string LITERAL can mask a bug a string VARIABLE exposes (the VARPTR
    # FACTYP precedent), so the type-mismatch row is measured both ways. The
    # integer-typed variable is the in-domain half of the same question.
    ("co-strvar",   "co",  "SCREEN 0",  'A$="40":WIDTH A$'),
    ("co-intvar",   "co",  "SCREEN 0",  "A%=32:WIDTH A%"),
    # Truncate-then-bound, checked AT the new bound rather than at 255: if the
    # order were bound-then-truncate, 40.9 would be rejected in SCREEN 0.
    ("co-40.9",     "co",  "SCREEN 0",  "WIDTH 40.9"),
    ("co-41.9",     "co",  "SCREEN 0",  "WIDTH 41.9"),
    ("co-32.9-s1",  "co",  "SCREEN 1",  "WIDTH 32.9"),

    # --- the syntax surface ---------------------------------------------------
    ("sx-bare",     "sx",  "SCREEN 0",  "WIDTH"),
    ("sx-comma",    "sx",  "SCREEN 0",  "WIDTH ,"),
    ("sx-trail",    "sx",  "SCREEN 0",  "WIDTH 32,"),
    ("sx-two",      "sx",  "SCREEN 0",  "WIDTH 32,40"),
    ("sx-colon",    "sx",  "SCREEN 0",  "WIDTH :X=1"),
    ("sx-bare-mid", "sx",  "SCREEN 0",  "X=1:WIDTH"),
    # ⚠️ ORDERING. `WIDTH 41,` has BOTH a domain error and a trailing-comma
    # syntax error. Which one the reference reports says whether the bound is
    # checked before the rest of the line is scanned -- the same question
    # docs/spec-basic-str-domain.md settled for MID$ (`MID$(A$,0,)` -> IFC, the
    # domain check beating the deferred syntax error). An implementation that
    # gets this backwards is wrong on every row that has both.
    ("sx-ill-trail","sx",  "SCREEN 0",  "WIDTH 41,"),
    ("sx-zero-trail","sx", "SCREEN 0",  "WIDTH 0,"),

    # --- persistence: the per-mode default -----------------------------------
    # `WIDTH n` records n as the mode's default so a later `SCREEN` re-applies
    # it. zerobas implements this; whether it picks the same slot as the
    # reference in each mode has never been measured. The readout already
    # carries LINL40 and LINL32, so these rows only need to set a width, leave
    # the mode, and come back.
    ("pe-s0-back",  "pe",  "SCREEN 0",  "WIDTH 32:SCREEN 1:SCREEN 0"),
    ("pe-s1-back",  "pe",  "SCREEN 1",  "WIDTH 29:SCREEN 0:SCREEN 1"),
    ("pe-s0-in-s1", "pe",  "SCREEN 1",  "WIDTH 29:SCREEN 0"),
    ("pe-s2-back",  "pe",  "SCREEN 2",  "WIDTH 29:SCREEN 0"),
]

# The untrapped seam. Direct mode, no handler, echo-anchored screen tail -- the
# readout the user actually sees. A row whose width CHANGED cannot be read (the
# scrape shears and the echo anchor is gone); that reports as `<no echo>`, which
# is a legible apparatus failure rather than a silent agreement, and for the
# reject rows it is itself the finding.
UNTRAPPED = [
    ("unt-300",     "unt", "WIDTH 300"),
    ("unt-99999",   "unt", "WIDTH 99999"),
    ("unt-41",      "unt", "WIDTH 41"),
    ("unt-200",     "unt", "WIDTH 200"),
    ("unt-0",       "unt", "WIDTH 0"),
    ("unt-bare",    "unt", "WIDTH"),
    ("unt-str",     "unt", 'WIDTH "40"'),
]
UNT_PROLOGUE = ["SCREEN 1:WIDTH 32", "SCREEN 0:WIDTH 40", "CLS"]


def norm(s):
    """Fold message case (the documented two-spelling divergence). Runs of
    spaces are COLLAPSED but never dropped, so whitespace-only junk still
    differs from no junk at all."""
    if s is None:
        return None
    return " ".join(s.casefold().replace("|", " | ").split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default=REF_MACHINE)
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--only")
    ap.add_argument("--batch", action="store_true",
                    help="share one boot across the matrix. Sound in principle "
                         "-- every trapped case restores SCREEN 0/WIDTH 40 "
                         "itself -- but a case that WEDGES leaves no restore, "
                         "so the characterization runs boot-per-case.")
    ap.add_argument("--gate", action="store_true",
                    help="fail on any divergence; without it every row is "
                         "reported as a straight differential")
    args = ap.parse_args()

    rows = ([(lbl, bat, trapped(mode, subj), subj)
             for lbl, bat, mode, subj in CASES]
            + [(lbl, bat, UNT_PROLOGUE + [subj], subj)
               for lbl, bat, subj in UNTRAPPED])
    sel = [r for r in rows if not args.only or args.only in r[0]]
    if not sel:
        print("APPARATUS FAILURE: no rows selected")
        return 1

    specs = [(("direct" if bat == "unt" else "stored"), lines)
             for _, bat, lines, _ in sel]

    def read(i, raw):
        """The trapped batteries read the bracket span (width-independent, the
        screen having been restored first); the untrapped battery reads the
        echo-anchored tail (what the user sees)."""
        if raw is None:
            return None
        if sel[i][1] == "unt":
            t = omsx_repl.screen_tail(raw, sel[i][3])
            return t if t is not None else "<no echo>"
        v = omsx_repl.result_span(raw)
        return v if v is not None else "<none>"

    def compare(i, rr, zz):
        a, b = read(i, rr), read(i, zz)
        return a is not None and b is not None and norm(a) == norm(b)

    verdicts, ref_raws, zb_raws = omsx_repl.run_differential(
        args.machine, args.zb_machine, specs, compare,
        batch=args.batch, reset=("NEW", "CLS"))

    npass = 0
    print("readout: [ ERR LINLEN LINL40 LINL32 ]   (ERR 0 = accepted)")
    for i, (label, battery, _lines, subj) in enumerate(sel):
        rt, zt = read(i, ref_raws[i]), read(i, zb_raws[i])
        ok = verdicts[i]
        npass += 1 if ok else 0
        print(f"{'PASS' if ok else 'FAIL':5} {battery:4} {label:12} {subj[:26]:26}")
        print(f"        ref: {rt!r}")
        if not ok:
            print(f"        zb : {zt!r}")
        sys.stdout.flush()

    ntot = len(sel)
    print(f"\n{npass}/{ntot} rows agree with the reference")
    bad_ctl = [sel[i][0] for i in range(ntot)
               if sel[i][1] == "ctl" and not verdicts[i]]
    if bad_ctl:
        print(f"⚠️ CONTROL ROWS DIVERGED ({', '.join(bad_ctl)}) — no other row in "
              f"this run is readable as a D-WID finding")
        return 1
    if args.gate and npass != ntot:
        print("SOME FAILED")
        return 1
    print("ALL PASS" if npass == ntot else "REPORTED (not gated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
