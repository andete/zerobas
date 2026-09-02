#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WID -- `WIDTH n`'s VALID DOMAIN, and (D-EVALCHK) WHICH deferred error wins.

WHY THIS EXISTS
===============
`4d35b6d` (the abort-depth slice) fixed the way `WIDTH 300` FAILED: the reject
now unwinds instead of returning into `ex_width` with A = the error code. It
deliberately did not open the question of which n `WIDTH` should ACCEPT --
docs/spec-basic-abort-depth.md §7 records that as "a separate question this
slice does not open". D-WID opened it (the `s0`/`s1`/`s2`/`co`/`sx`/`pe`
batteries below).

🔴 AND D-EVALCHK (2026-08-09, docs/spec-basic-evalchk.md) OPENED THE ONE
QUESTION D-WID DID NOT ASK: when the argument expression has ALREADY FAULTED --
a deferred `1/0`, a deferred `SQR(-1)` -- and the value it nevertheless leaves
in FAC is ALSO out of int16, WHICH ERROR does the reference report? Two rules
are competing inside one statement and only a row with BOTH faults in it can
order them. The `dfe`/`cl` batteries are that row set. It matters because
`ex_width`'s argument check was 13 bytes written out inline where `ex_field`'s
is a 3-byte call, and the shared helper that collapses them (`eval_byte_checked`
/ `eval_int16_checked`, basic/interp.asm) runs `check_expr_errors` BEFORE the
coercion instead of after -- which is exactly the ordering these rows measure.

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

🔴 TWO REFERENCES, BECAUSE `WIDTH` IS NOT DISK BASIC. D-WID ran against the
Philips VG-8020 alone. `WIDTH`/`CLEAR` are plain BASIC, so the National CF-3300
can express every row here too, and D-EVALCHK added it: a row the two
references answer DIFFERENTLY has NO ORACLE and is printed as such rather than
scored. (That is a real strengthening, not bookkeeping -- the `dfe` rows decide
a fix, and one machine agreeing with a hypothesis is not the same evidence as
two.)

🔴 A CONTROL FAILING ON A **REFERENCE** AND ON **zb** ARE DIFFERENT EVENTS
([[classify-a-control-failure-by-which-side-failed-it]]): a reference miss means
the fixture is broken -> exit 2, score nothing; a zb miss is an ordinary
divergence, scored.

Message CASE is folded before comparison (the documented two-spelling split,
basic/arrays.asm:44); the readout is numeric ERR codes anyway.
"""
from __future__ import annotations
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_repl                                                   # noqa: E402
import probe_report                                                # noqa: E402
import probe_tmp                                                   # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
TEST_DSK = os.path.join(REPO, "disk", "test720.dsk")
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE",
                            "C-BIOS_MSX1_EU_REPACK_DISK")

# ⚠️ `diska` is a /tmp COPY, never the committed image: nothing here writes to a
# disk, but a probe that hands openMSX the repo's own .dsk is one bug away from
# mutating a committed artifact. The CF-3300 needs one to reach its BASIC prompt
# in a predictable state; the diskless VG-8020 must not be given one.
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW", "CLS"), diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW", "CLS"), diska=True),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW", "CLS"), diska=True),
}
REF_SIDES = ("vg8020", "cf3300")

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
# ⚠️ LINES 10-20 ARE THE WHOLE REASON THIS PROBE IS READABLE. The machines boot
# at DIFFERENT text widths (VG-8020 37, CF-3300 39 in disk BASIC, zerobas 39 --
# the same asymmetry basic_probe_str_domain.py pins around), and both LINL40 and
# LINL32 carry that difference into the readout. Without the pin, three control
# rows that never execute a WIDTH at all diverged on width alone while their ERR
# codes agreed: the probe would have reported a defect in `WIDTH`'s domain that
# was really the boot default. The pin also gives every reject row a KNOWN prior
# LINLEN, which is what makes "did the reject scribble on the sysvars anyway?" a
# question the readout can answer.
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


# --- the PLAIN trapped program, for subjects that do not move the instrument --
# 🔴 `CLEAR` CANNOT USE `trapped()` AND THAT IS NOT A STYLE CHOICE: a CLEAR that
# SUCCEEDS wipes every variable, so E/L/M/N would be read back as zeros and the
# accepting rows would report a fault that never happened. This fixture reads
# the trapped ERR only -- which is sound here precisely because `CLEAR` touches
# none of the three width sysvars, so there is nothing else to read.
#   10 ON ERROR GOTO 40
#   20 E=0:<subject>
#   30 PRINT"[";E;"]":END
#   40 E=ERR:RESUME 30
def plain(subject: str) -> list[str]:
    return ["ON ERROR GOTO 40", "E=0:" + subject,
            'PRINT"[";E;"]":END', "E=ERR:RESUME 30"]


# (label, battery, mode, subject). Batteries:
#   ctl -- the apparatus. READ FIRST; nothing else is readable if one diverges.
#   s0  -- SCREEN 0 (text-1, 40 columns): where is the upper bound, and is 0 legal?
#   s1  -- SCREEN 1 (text-2, 32 columns): is the bound MODE-DEPENDENT?
#   s2  -- SCREEN 2 (graphics): is WIDTH accepted at all, and what does it record?
#   co  -- coercion: truncate-before-check, and the int16/byte error boundary.
#   sx  -- the syntax surface (bare WIDTH, empty argument, trailing comma).
#   pe  -- persistence: does an accepted width survive a mode switch?
#   dfe -- D-EVALCHK: a DEFERRED expression error against the coercion's own.
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
    # 🟢 D-EVALCHK's own apparatus rows: the two DEFERRED faults, on their own,
    # in an expression that is NOT an argument to anything. They say what the
    # trapped readout should show for each fault CLASS before any competition is
    # introduced -- without them, `dfe-ovfsqr` reading 5 has two explanations.
    ("ctl-div0",    "ctl", "SCREEN 0",  "X=1/0"),
    ("ctl-sqr",     "ctl", "SCREEN 0",  "X=SQR(-1)"),

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

    # === D-EVALCHK: WHICH ERROR WINS WHEN TWO OF THEM ARE PENDING ============
    # `ex_width` runs `eval`, tests TMISMATCH, then coerces. The coercion
    # (fac_to_int_strict) SETS FPERR=1 on an out-of-int16 magnitude and does NOT
    # first clear whatever FPERR the expression already left there -- so a value
    # that both FAULTED and OVERFLOWS reports whichever of the two is tested
    # last. Which one the reference reports is the whole question, and it is one
    # no single-fault row can answer.
    #
    # 🔴 EVERY VALUE HERE LEAVES THE BOUND IT IS SUPPOSED TO LEAVE, checked
    # rather than assumed (D-LPTVERB's R-LS4 was filed with "out-of-byte"
    # evidence that was IN byte range): 70000 > 32767 leaves int16, and
    # `0*(1/0)` / `0*SQR(-1)` contribute a DEFERRED fault while contributing
    # ZERO to the value, so the two clauses are independently controlled.
    #
    # 🟢 dfe-70000 is the same value with the deferred fault taken OUT, and
    # dfe-plus0 is the same expression SHAPE with the fault taken out. Without
    # both, a reading of 6 on dfe-ovfdiv has three explanations.
    ("dfe-div0",    "dfe", "SCREEN 0",  "WIDTH 1/0"),
    ("dfe-defer",   "dfe", "SCREEN 0",  "WIDTH 1+0*(1/0)"),
    ("dfe-sqr",     "dfe", "SCREEN 0",  "WIDTH SQR(-1)"),
    ("dfe-70000",   "dfe", "SCREEN 0",  "WIDTH 70000"),
    ("dfe-plus0",   "dfe", "SCREEN 0",  "WIDTH 30+0*1"),
    # 🎯 THE TWO ROWS THAT DECIDE THE FIX -- a deferred fault AND an int16
    # overflow in one expression, once per fault class so the answer cannot be
    # "division by zero is special".
    ("dfe-ovfdiv",  "dfe", "SCREEN 0",  "WIDTH 70000+0*(1/0)"),
    ("dfe-ovfsqr",  "dfe", "SCREEN 0",  "WIDTH 70000+0*SQR(-1)"),
    # ...and the ORDER of the OTHER pair: a deferred TYPE mismatch against a
    # deferred FPERR. Both post-eval checks are in play at once; whichever the
    # reference reports is the order the shared helper has to keep.
    ("dfe-tmfp",    "dfe", "SCREEN 0",  'A$="X":WIDTH (A$<5)+0*(1/0)'),
    # 🟢 ...and its own control: the same comparison with no FPERR beside it.
    ("dfe-tmonly",  "dfe", "SCREEN 0",  'A$="X":WIDTH (A$<5)'),

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
    ("sx-ill-trail", "sx", "SCREEN 0",  "WIDTH 41,"),
    ("sx-zero-trail", "sx", "SCREEN 0", "WIDTH 0,"),

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

# === D-EVALCHK, SITE TWO: the SAME rule at `CLEAR` ===========================
# 🔴 THIS IS A DIFFERENT VERB IN A PROBE NAMED FOR `WIDTH`, ON PURPOSE AND WITH
# A REASON. The subject of the `dfe` battery is not `WIDTH`; it is the ORDER of
# the two post-`eval` checks at a CHECKED-COERCION argument site, and
# basic/clear.asm carries a third verbatim copy of the same five instructions
# (`call eval` / `ld a,(TMISMATCH)` / `or a` / `jp nz` / `call
# get_int16_checked`). Measuring the rule at one site and fixing it at three is
# how a "shared helper" ships an unmeasured behaviour change at two of them.
# `CLEAR`'s own DOMAIN stays where it belongs -- basic_probe_clearpool.py, D-CLP
# -- and none of its 51 rows can reach this class, because none of them puts a
# deferred fault and an int16 overflow in the same expression.
#
# ⚠️ `get_int16_checked`, NOT `get_byte_arg`: `CLEAR`'s argument is an int16
# with a sign test, not a byte. That is why the helper has two entry points and
# why cl-neg / cl-70000 are here -- they are the two stages this must not lose.
PLAIN_CASES = [
    ("cl-ok",       "cl",  "CLEAR 200"),
    ("cl-str",      "cl",  'CLEAR "200"'),
    ("cl-neg",      "cl",  "CLEAR -1"),
    # 🎯 IN int16, OUT of the BYTE, and ACCEPTED. This is the row that says
    # `CLEAR`'s argument is an int16 and not a byte -- i.e. that the helper
    # genuinely needs two entry points rather than one. It is also K-EV3's whole
    # red set: narrowing `ex_clear` to the byte entry moves this row and nothing
    # else in the matrix.
    ("cl-500",      "cl",  "CLEAR 500"),
    ("cl-70000",    "cl",  "CLEAR 70000"),
    ("cl-div0",     "cl",  "CLEAR 1/0"),
    # 🎯 the deciding row at site two.
    ("cl-ovfdiv",   "cl",  "CLEAR 70000+0*(1/0)"),
]

# The untrapped seam. Direct mode, no handler, echo-anchored screen tail -- the
# readout the user actually sees. A row whose width CHANGED cannot be read (the
# scrape shears and the echo anchor is gone); that reports as `<no echo>`, which
# is a legible apparatus failure rather than a silent agreement, and for the
# reject rows it is itself the finding.
#
# ⚠️ VG-8020 + zb ONLY. This battery reads the RAW SCREEN TAIL, so it is the one
# place the two machines' different boot state is not pinned away; the CF-3300
# reaches its prompt through a disk boot with its own banner and its own text
# width, and a `<no echo>` there would be the disk ROM's, not `WIDTH`'s. The
# trapped batteries carry the two-reference weight.
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
UNT_SIDES = ("vg8020", "zb")

LABEL_W = 13

# The apparatus rows, and what each must read. A miss on a REFERENCE means the
# fixture is broken (exit 2, nothing scored); a miss on `zb` is an ordinary
# divergence and is scored like any other row.
CONTROLS = ("ctl-noop-s0", "ctl-noop-s1", "ctl-ifc", "ctl-ovf", "ctl-syn",
            "ctl-restore", "ctl-div0", "ctl-sqr", "cl-ok")
CONTROL_WANT = {
    "ctl-noop-s0": " 0  40  40  32 ",
    "ctl-noop-s1": " 0  32  40  32 ",
    "ctl-ifc":     " 5  40  40  32 ",
    "ctl-ovf":     " 6  40  40  32 ",
    "ctl-syn":     " 2  40  40  32 ",
    # ⚠️ ` 20  20 `, NOT ` 40  40 `: line 60 captures BEFORE line 80 restores, so
    # this row reads back the width it just set -- which is the whole point of it
    # (a restore that never ran would show ` 40  40 ` and read as "fine"). The
    # first draft wanted ` 0  40  40  32 ` and the reference side refused the run.
    "ctl-restore": " 0  20  20  32 ",
    "ctl-div0":    " 11  40  40  32 ",
    "ctl-sqr":     " 5  40  40  32 ",
    "cl-ok":       " 0 ",
}

# Each row is evidence about its own question only while its group's control is
# green on zerobas.
SITE_CONTROL = {lab: "ctl-noop-s0"
                for lab, bat, _m, _s in CASES if bat != "ctl"}
SITE_CONTROL.update({lab: "cl-ok" for lab, _b, _s in PLAIN_CASES})
SITE_CONTROL.update({lab: "ctl-restore" for lab, _b, _s in UNTRAPPED})
# the SCREEN-1 rows read the SCREEN-1 instrument row, not the SCREEN-0 one
for _lab, _bat, _mode, _subj in CASES:
    if _mode == "SCREEN 1" and _bat != "ctl":
        SITE_CONTROL[_lab] = "ctl-noop-s1"
# the two deferred-fault classes each have their own apparatus row
for _lab in ("dfe-div0", "dfe-defer", "dfe-ovfdiv", "dfe-tmfp"):
    SITE_CONTROL[_lab] = "ctl-div0"
for _lab in ("dfe-sqr", "dfe-ovfsqr"):
    SITE_CONTROL[_lab] = "ctl-sqr"

SENTINELS = ("<none>", "<no echo>", "<NO CAPTURE>")


def norm(s):
    """Fold message case (the documented two-spelling divergence). Runs of
    spaces are COLLAPSED but never dropped, so whitespace-only junk still
    differs from no junk at all."""
    if s is None:
        return None
    return " ".join(s.casefold().replace("|", " | ").split())


def _rows(only: str):
    """(label, battery, mode, lines, subject, sides) for every selected case."""
    out = []
    for lab, bat, mode, subj in CASES:
        out.append((lab, bat, "stored", trapped(mode, subj), subj,
                    tuple(SIDES)))
    for lab, bat, subj in PLAIN_CASES:
        out.append((lab, bat, "stored", plain(subj), subj, tuple(SIDES)))
    for lab, bat, subj in UNTRAPPED:
        out.append((lab, bat, "direct", UNT_PROLOGUE + [subj], subj,
                    UNT_SIDES))
    return [r for r in out if not only or only in r[0]]


def read(bat: str, subj: str, raw) -> str:
    """The trapped batteries read the bracket span (width-independent, the
    screen having been restored first); the untrapped battery reads the
    echo-anchored tail (what the user sees)."""
    if raw is None:
        return "<NO CAPTURE>"
    if bat == "unt":
        t = omsx_repl.screen_tail(raw, subj)
        return t if t is not None else "<no echo>"
    v = omsx_repl.result_span(raw)
    return v if v is not None else "<none>"


def run_side(side: str, rows) -> dict:
    cfg = SIDES[side]
    out = {}
    # BATCHED (D-BATCH8). `WIDTH` is exactly the kind of state that does not
    # survive sharing a boot, so this only lands because
    # `scratchpad/batchcheck.py` found every row identical both ways: each
    # case's own `cfg["reset"]` is prepended to its lines and re-establishes the
    # screen before it runs.
    # ⚠️ The disk is now one per SIDE rather than one per case -- a real
    # reduction in isolation, covered by the same control.
    group = [r for r in rows if side in r[5]]
    if not group:
        return out
    kw = {}
    if cfg["diska"]:
        dsk = probe_tmp.tmp(f"zb_width_{side}_batch.dsk")
        shutil.copy(TEST_DSK, dsk)
        kw["diska"] = dsk
    specs = []
    for lab, bat, mode, lines, subj, _sides in group:
        body = ([f"{10 * (k + 1)} {ln}" for k, ln in enumerate(lines)] + ["RUN"]
                if mode == "stored" else list(lines))
        specs.append(("direct", list(cfg["reset"]) + body))
    caps = omsx_repl.run_cases(
        cfg["machine"], specs,
        batch=True, reset=(), boot=cfg["boot"], step=cfg["step"], **kw)
    for (lab, bat, _m, _l, subj, _s), cap in zip(group, caps):
        out[lab] = read(bat, subj, cap)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-WID/D-EVALCHK: WIDTH's valid domain, and which deferred "
                    "error wins at a checked-coercion argument site")
    ap.add_argument("--sides", default="vg8020,cf3300,zb")
    ap.add_argument("--machine", help=argparse.SUPPRESS)   # legacy no-op
    ap.add_argument("--zb-machine", dest="zb_machine", default=None)
    ap.add_argument("--only", default="")
    ap.add_argument("--batch", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--gate", action="store_true",
                    help="fail on any divergence; without it every row is "
                         "reported as a straight differential")
    a = ap.parse_args()

    if a.zb_machine:
        SIDES["zb"]["machine"] = a.zb_machine
    sides = [s for s in a.sides.split(",") if s]
    for s in sides:
        if s not in SIDES:
            sys.stderr.write(f"unknown side {s!r}\n")
            return 2

    rows = _rows(a.only)
    if not rows:
        print("APPARATUS FAILURE: no rows selected")
        return 2

    results = {s: run_side(s, rows) for s in sides}
    present = [r for r in rows if any(r[0] in results[s] for s in sides)]

    print("readout: [ ERR LINLEN LINL40 LINL32 ]   (ERR 0 = accepted); the "
          "`cl` battery reads [ ERR ] only")
    print(f"sides: {', '.join(sides)}")
    print("=" * 78)

    # 🔴 ONLY A REFERENCE CAN SAY THE APPARATUS IS BROKEN. A control that fails
    # on `zb` is a finding and is scored below like any other row.
    bad = []
    for lab, _bat, _m, _l, _s, _sd in present:
        if lab not in CONTROLS:
            continue
        for s in sides:
            if s == "zb" or lab not in results[s]:
                continue
            got = results[s][lab]
            if norm(got) != norm(CONTROL_WANT[lab]):
                bad.append((lab, s, got, CONTROL_WANT[lab]))
    if bad:
        for lab, s, got, exp in bad:
            print(probe_report.row("FAIL", lab, LABEL_W, {s: got},
                                   "   [POSITIVE CONTROL]"))
            print(f"        wanted {exp!r}")
        print("\n*** A POSITIVE CONTROL FAILED ON A REFERENCE, so nothing was "
              "measured.\n"
              "    These rows are the INSTRUMENT: the pinned no-op readout in "
              "each mode, the\n"
              "    three trapped error codes, the restore, the two deferred "
              "fault classes,\n"
              "    and CLEAR's accepting form. A REFERENCE failing one means "
              "the fixture is\n"
              "    broken (a boot that did not settle, a disk that did not "
              "mount), not that\n"
              "    the rule is wrong. (A control failing on `zb` is NOT this: "
              "that is an\n"
              "    ordinary divergence and IS scored.) Check build/*.rom, "
              "`make\n"
              "    repack-machine` and `make latch-check`, THEN re-read the "
              "rows. Exit 2 (not\n"
              "    1) = the instrument was broken, NOT a regression.")
        for lab, _bat, _m, _l, _s, _sd in present:
            vals = {s: results[s][lab] for s in sides if lab in results[s]}
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   "   (not scored)"))
        print(probe_report.footer(len(bad) + len(present), 0,
                                  "NOT MEASURED (a positive control failed)"))
        return 2

    def ctl_red_on_zb(ctl: str) -> bool:
        got = results.get("zb", {}).get(ctl)
        return got is not None and norm(got) != norm(CONTROL_WANT[ctl])

    if len(sides) < 2:
        n = 0
        for lab, _bat, _m, _l, _s, _sd in present:
            for s in sides:
                if lab in results[s]:
                    print(probe_report.row("--", lab, LABEL_W,
                                           {s: results[s][lab]}))
                    n += 1
        print(probe_report.footer(n, 0, "CHARACTERIZATION (one side)"))
        return 0

    agree = dis = noref = onlyone = refsplit = 0
    for lab, _bat, _m, _l, _s, _sd in present:
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        refs = {s: v for s, v in vals.items()
                if s in REF_SIDES and v not in SENTINELS}
        note = "   [POSITIVE CONTROL]" if lab in CONTROLS else ""
        own = SITE_CONTROL.get(lab)
        if own and own in results.get("zb", {}) and ctl_red_on_zb(own):
            note += (f"   [ITS OWN GROUP CONTROL ({own}) IS RED ON zb — this "
                     f"row is NOT evidence about WIDTH]")
        if not refs:
            noref += 1
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   "   [NO REFERENCE ON ANY REQUESTED SIDE]"))
            continue
        if len({norm(v) for v in refs.values()}) > 1:
            # 🔴 NOT SCORED, and that is the honest disposition rather than a
            # softened gate: two references that answer differently do not
            # constitute an oracle, so there is nothing for zb to be right or
            # wrong about. Printed loudly so a row that STARTS disagreeing is
            # visible rather than quietly dropped.
            refsplit += 1
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   note + "   [REFERENCES DISAGREE — no "
                                          "oracle, not scored]"))
            continue
        if len(refs) == 1:
            onlyone += 1
            note += f"   [ONE REFERENCE ONLY ({list(refs)[0]})]"
        oracle = list(refs.values())[0]
        zb = vals.get("zb")
        ok = zb is not None and norm(zb) == norm(oracle) and zb not in SENTINELS
        agree += ok
        dis += not ok
        print(probe_report.row("ok" if ok else "DIFF", lab, LABEL_W, vals,
                               note))

    print(probe_report.footer(len(present), agree + dis,
                              f"{agree} agree, {dis} diverge, "
                              f"{noref} without a reference, "
                              f"{refsplit} without an oracle (refs disagree)"))
    print("=" * 78)
    print(f"{agree}/{agree + dis} readings match their reference "
          f"({len(CASES) + len(PLAIN_CASES) + len(UNTRAPPED)} cases, "
          f"{len(CONTROLS)} positive controls, "
          f"{onlyone} row(s) with ONE reference only, "
          f"{noref} row(s) without a reference, "
          f"{refsplit} row(s) where the references disagree)")
    print("DENOMINATOR: (WHICH n each SCREEN mode accepts: 0, 1, the mode's "
          "maximum and one past it, 255/256, 300, negative, in text-1, text-2 "
          "and two graphics modes) x (WHICH of four errors otherwise, and "
          "whether the reject SCRIBBLED on LINLEN/LINL40/LINL32 anyway) x "
          "(WHICH per-mode default slot is recorded, checked by leaving the "
          "mode and coming back) x (COERCION: truncate-vs-round, the "
          "int16/byte error boundary at -32769/-32768/32767/32768, a string "
          "literal and a string VARIABLE) x (the SYNTAX surface: bare, empty, "
          "trailing comma, and a row with BOTH a domain and a syntax fault) x "
          "(🔴 D-EVALCHK: WHICH of two PENDING errors is reported -- a "
          "deferred `1/0` and a deferred `SQR(-1)` each against an int16 "
          "overflow in the same expression, a deferred TYPE mismatch against a "
          "deferred FPERR, and the same rule at its SECOND site, `CLEAR`'s "
          "`get_int16_checked` argument). Every group carries a positive "
          "control on the same fixture, and the accepting rows read the WIDTH "
          "BACK out of the sysvars rather than printing OK. NOT COVERED: the "
          "UNWIND (make abort-acceptance owns it), `WIDTH` on a printer "
          "channel (`WIDTH LPRINT n`), message WORDING (D-MSGEXACT), and "
          "`CLEAR`'s own domain (D-CLP, basic_probe_clearpool.py).")
    if a.gate and dis:
        sys.stderr.write(f"width: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
