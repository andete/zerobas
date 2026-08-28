#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CLP -- the `CLEAR` STRING-POOL PARTITION, characterised against the VG-8020.

WHY THIS EXISTS
===============
zerobas has ONE free gap where the reference has TWO POOLS. Strings allocate
DOWN from a ceiling into `[FRETOP, C)` and variables/arrays grow UP to `ARYEND`;
`heap_alloc` fails only when the two meet (sub/strheap.asm `ha_ok`). So the
string area and the variable area are the same piece of memory, and `CLEAR`'s
`<string-space>` argument is evaluated and **discarded**
([`basic/clear.asm:61`](../basic/clear.asm:61)).

The reference partitions them: `CLEAR n` sizes a string pool, and the
`BIN$`/`FRE` slice already measured the headline contract exactly, to the byte
(docs/binfre-vg8020-characterization.md §1) --

    CLEAR 500 : PRINT FRE("")                        -> 500
    CLEAR 100 : PRINT FRE("")                        -> 100
    CLEAR 500 : A$=STRING$(100,"A") : PRINT FRE("")  -> 400

-- and then deferred the whole thing, leaving six rows recorded-not-gated
because no partition exists on this side to pin them against. This probe is the
measurement that turns that into an implementable contract.

⚠️ `FRE("")` IS THE ONE MEMORY READOUT THAT IS MACHINE-INDEPENDENT, and that is
what makes this gateable at all. `FRE(0)` answers with free *variable* space,
which is a property of each machine's memory map -- the `BIN$`/`FRE` slice could
only ever gate it as a RELATION. But once the string pool is sized by `CLEAR n`,
`FRE("")` answers with a number the USER chose, so the two machines must agree
on the nose. Absolute rows are legitimate here and nowhere else.

⚠️ EVERY `FRE(0)` PAIR IS READ AT EQUAL DEPTH, via pre-created variables. `FRE(0)`
counts down to **SP** at ~6 bytes per nesting level, so the natural
`X=FRE(0): <allocate> :PRINT X-FRE(0)` straddles two evaluation depths and folds
the evaluator's own frame size into the answer -- gating that would demand
zerobas carry a VG-8020-sized stack frame. The `BIN$`/`FRE` slice measured this
the hard way (mixed 828/108/23/18 vs equal-depth 816/96/11/6); the equal-depth
form cancels the frame term and leaves the allocation cost. `FRE("")` is
depth-IMMUNE on the reference, which is itself evidence for the two-pool model.

⚠️ `CLEAR` RESETS ALL VARIABLES, so in every case the `CLEAR` comes FIRST and
the subject's variables are created after it. A row that sets a variable and
then clears is measuring the wipe, not the pool.

⚠️ NO ROW MAY DEPEND ON THE ABSOLUTE VALUE OF `FRE(0)`. The two machines have
different memory maps by construction (C-BIOS vs a stock VG-8020) and always
will. Every numeric-pool row is a RELATION or an equal-depth DELTA.

Error rows are read UNTRAPPED, through the echo-anchored screen tail, because
`Out of string space` and `Out of memory` are DIFFERENT errors and this probe
has to tell them apart -- an `ERR`-code readout would work too, but the message
is what a user sees and the tail shows an abort's trailing junk as well.

⚠️ EVERY LINE IS KEPT UNDER 37 CHARACTERS (see ECHO_MAX below -- it was 40, and
that was three too many), AND THE READOUT ALWAYS ANCHORS ON A SHORT ONE. Both
readouts here are echo-anchored, and the echo of a line longer than the screen's
`LINLEN` WRAPS onto a second row -- after which `_echo_idx` can never match it,
because it compares whole rows. The first draft of this
probe put each case on one `:`-joined line, and eleven of them came back
`<none>` **on the reference**, several of which then read as PASS because
zerobas answered `<none>` too. Agreeing on nothing is the failure mode this
whole file exists to avoid, so each case is now a LIST of short lines with the
`PRINT` last. `basic_probe_str_domain.py`'s docstring already warned about
exactly this; the warning was read and walked into anyway.

Message CASE is folded before comparison (the documented two-spelling split,
basic/arrays.asm:44).
"""
from __future__ import annotations
import argparse, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl  # noqa: E402

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

# ⚠️ THIS GUARD WAS THREE CHARACTERS TOO LOOSE (corrected 2026-07-29, D-ARR-B).
# It tested `omsx_repl.COLS` (40, the screen width), but a line wraps at
# `LINLEN`, and the two machines do not boot at the same one: D-WID measured the
# reference at 37 and zerobas at 39 (docs/width-vg8020-characterization.md). The
# D-ARR-B matrix hit it for real -- a 39-character row read `<no echo>` on BOTH
# machines and scored PASS, the same agreeing-on-nothing this guard exists to
# prevent. No row in THIS file was ever over 37 (the longest is 35), so no
# clearpool measurement changes; the guard was simply not checking what it said.
ECHO_MAX = 37

# Batteries reported but never gated. ⚠️ `arr` IS GONE (2026-07-29): its one
# row, `oos-dim-huge`, graduated into the gated `oos` battery when D-ARR-B
# implemented the array size rule, which is exactly what its own comment said
# would happen. A never-gated bucket that outlives its reason is a gate that
# has quietly stopped measuring what it claims to.
# `topen` joins these: a KNOWN-divergent half, reported every run so it stays
# visible, but not gated -- gating it would make the suite permanently red.
# `topen` is GONE: D-CONCATPEAK closed that half and the rows are gated.
UNGATED = ("rep", "share")

# the D-POOLCAP subject: a 20 B variable whose SELF-CONCATENATION is sliced.
# 40 B of result over 20+20 of transient, which is the whole finding.
BIG = 'X$="ABCDEFGHIJ"+"KLMNOPQRST"'

# (label, battery, [lines]). The LAST line carries the readout and is always
# short enough not to wrap (see the docstring). Batteries:
#   ctl   -- the apparatus. READ FIRST; nothing else is readable if one fails.
#   repro -- the ORACLE's own recorded answers, checked against the reference
#            column ALONE (REPRO_EXPECT). Not a statement about zerobas.
#   size  -- does `CLEAR n` size the pool to exactly n?
#   hold  -- does allocating charge the pool, and does freeing give it back?
#   indep -- are the two pools INDEPENDENT? the core architectural claim.
#   oos   -- `Out of string space`, and is it distinct from `Out of memory`?
#   dflt  -- the boot default, and what a BARE `CLEAR` does to the size.
#   dom   -- `CLEAR n`'s own argument domain.
#   hmem  -- the `,himem` argument's interaction with the pool.
#   share -- REPORTED, NEVER GATED: the body-OWNERSHIP divergence (S-CLP-5,
#            signed off out of scope). zerobas owns a body per variable; the
#            reference decides ownership per source, which shows up in BOTH
#            directions (an alias charges twice there, a stored literal
#            charges nothing). Reconciling them changes WHO OWNS A BODY, not
#            how big the pool is, so no pool arithmetic can make them agree.
#   rep   -- REPORTED, NEVER GATED: rows whose answer is a property of each
#            machine's memory map, so they can never be made to agree.
#   arychg-- the pool arithmetic of a string ARRAY-ELEMENT store. GATED, and
#            that was a MEASUREMENT, not a plan: these were written as
#            reported-only on the assumption that they ride on S-CLP-5 body
#            ownership like the `share` rows do, and all four agree to the
#            byte. They SIZE the `oos` D-ARYOOS error rows -- they are the
#            denominator, and gating them keeps the sizing honest.
CASES = [
    # --- controls: TWO-SIDED apparatus rows -----------------------------------
    # A control must be a row BOTH machines are expected to pass TODAY. The
    # obvious candidates -- `CLEAR 500:PRINT FRE("")` -> 500 -- are exactly what
    # zerobas is expected to FAIL, so they are `repro` rows instead.
    ("ctl-strlen",   "ctl",  ['PRINT "[";LEN(STRING$(100,"A"));"]"']),
    ("ctl-strval",   "ctl",  ['A$="ABC"', 'PRINT "[";A$;"]"']),
    ("ctl-fre0",     "ctl",  ['PRINT "[";FRE(0)>1000;"]"']),
    ("ctl-frestr",   "ctl",  ['PRINT "[";FRE("")>0;"]"']),
    ("ctl-abort",    "ctl",  ['PRINT "[";ASC("");"]"']),
    # ⚠️ the anti-<none> control: a MULTI-LINE case whose subject allocates, so
    # the readout shape used by most rows below is itself proven to report a
    # value rather than <none>. This is the row that would have caught the
    # wrapped-echo fault immediately.
    ("ctl-multi",    "ctl",  ['A$=STRING$(100,"A")', 'PRINT "[";LEN(A$);"]"']),

    # --- reproduction: the ORACLE must still answer what it answered before ---
    ("repro-500",    "repro", ['CLEAR 500', 'PRINT "[";FRE("");"]"']),
    ("repro-200",    "repro", ['CLEAR 200', 'PRINT "[";FRE("");"]"']),
    ("repro-100",    "repro", ['CLEAR 100', 'PRINT "[";FRE("");"]"']),
    ("repro-hold",   "repro", ['CLEAR 500', 'A$=STRING$(100,"A")',
                               'PRINT "[";FRE("");"]"']),

    # --- does CLEAR n size the pool to exactly n? -----------------------------
    ("size-0",       "size", ['CLEAR 0', 'PRINT "[";FRE("");"]"']),
    ("size-1",       "size", ['CLEAR 1', 'PRINT "[";FRE("");"]"']),
    ("size-2",       "size", ['CLEAR 2', 'PRINT "[";FRE("");"]"']),
    ("size-50",      "size", ['CLEAR 50', 'PRINT "[";FRE("");"]"']),
    ("size-255",     "size", ['CLEAR 255', 'PRINT "[";FRE("");"]"']),
    ("size-256",     "size", ['CLEAR 256', 'PRINT "[";FRE("");"]"']),
    ("size-1000",    "size", ['CLEAR 1000', 'PRINT "[";FRE("");"]"']),
    ("size-4000",    "size", ['CLEAR 4000', 'PRINT "[";FRE("");"]"']),
    ("size-frac",    "size", ['CLEAR 100.7', 'PRINT "[";FRE("");"]"']),

    # --- does allocating charge the pool, and does freeing give it back? ------
    ("hold-1",       "hold", ['CLEAR 500', 'A$="A"', 'PRINT "[";FRE("");"]"']),
    ("hold-100-50",  "hold", ['CLEAR 500', 'A$=STRING$(100,"A")',
                              'B$=STRING$(50,"B")', 'PRINT "[";FRE("");"]"']),
    # REASSIGNMENT: the old body becomes garbage. Does FRE("") reclaim it (a
    # collection) or does it stay charged? This decides whether the pool needs
    # its own GC or shares strheap_gc.
    ("hold-reassign","hold", ['CLEAR 500', 'A$=STRING$(100,"A")', 'A$="B"',
                              'PRINT "[";FRE("");"]"']),
    # a literal from the token stream -- is it copied into the pool at all?
    ("hold-literal", "hold", ['CLEAR 500', 'A$="ABCDE"',
                              'PRINT "[";FRE("");"]"']),
    # a string ARRAY element: same pool as a scalar's body?
    ("hold-array",   "hold", ['CLEAR 500', 'DIM A$(2)', 'A$(1)=STRING$(100,"A")',
                              'PRINT "[";FRE("");"]"']),
    # ...and at the SAME COST. hold-array above is a RESTING reading in a pool
    # with 400 bytes of slack, so it agrees whether the element store peaks at
    # 100 or at 200 -- `FRE` GCs first and the transient is gone before the
    # readout. This row removes the slack: an EXACT-fit pool can only be
    # satisfied by a store that peaks at 100, and it is the array-element
    # counterpart of oos-exact.
    ("hold-arr-fit", "hold", ['CLEAR 100', 'DIM A$(2)', 'A$(1)=STRING$(100,"A")',
                              'PRINT "[";FRE("");"]"']),
    # a temp that is never stored: does an expression temp come out of the pool
    # and go straight back?
    ("hold-temp",    "hold", ['CLEAR 500', 'X=LEN(STRING$(100,"A"))',
                              'PRINT "[";FRE("");"]"']),

    # --- ARE THE TWO POOLS INDEPENDENT? the core architectural claim ----------
    # If they are, a string BODY is charged to the string pool and only the
    # variable ENTRY to the numeric pool -- so this delta is the entry size, NOT
    # entry+100. EQUAL DEPTH via pre-created variables (see the docstring).
    ("ind-body",     "indep", ['CLEAR 500', 'X=0:Y=0', 'X=FRE(0)',
                               'A$=STRING$(100,"A")', 'Y=FRE(0)',
                               'PRINT "[";X-Y;"]"']),
    ("ind-body200",  "indep", ['CLEAR 500', 'X=0:Y=0', 'X=FRE(0)',
                               'A$=STRING$(200,"A")', 'Y=FRE(0)',
                               'PRINT "[";X-Y;"]"']),
    # ... and the converse: a NUMERIC variable must not touch the string pool.
    ("ind-numvar",   "indep", ['CLEAR 500', 'Q=1', 'PRINT "[";FRE("");"]"']),
    ("ind-numarray", "indep", ['CLEAR 500', 'DIM Q(50)',
                               'PRINT "[";FRE("");"]"']),

    # --- `Out of string space` -- a DISTINCT error from `Out of memory`? ------
    ("oos-over",     "oos", ['CLEAR 100', 'A$=STRING$(200,"A")']),
    ("oos-exact",    "oos", ['CLEAR 100', 'A$=STRING$(100,"A")',
                             'PRINT "[";FRE("");"]"']),
    ("oos-one-over", "oos", ['CLEAR 100', 'A$=STRING$(101,"A")']),
    ("oos-zero",     "oos", ['CLEAR 0', 'A$="X"']),
    ("oos-cumul",    "oos", ['CLEAR 100', 'A$=STRING$(60,"A")',
                             'B$=STRING$(60,"B")']),
    # Is it distinct from `Out of memory`? An over-large DIM must give the OTHER
    # error -- the numeric pool's exhaustion, not the string pool's. `DIM Q(5000)`
    # asks for 5001*8 = 40008 bytes, which overruns the free VARIABLE space on
    # BOTH machines (the reference had 28815 at CLEAR 200, zerobas 15667), so
    # both must answer `Out of memory` and neither may answer `Out of string
    # space`. That is the claim this battery makes, and it is gateable.
    ("oos-vs-oom",   "oos", ['CLEAR 100', 'DIM Q(5000)']),
    # An over-large alloc followed by a READ of the pool: the reference aborts
    # so the PRINT never runs and the span reads <none>; a machine that does NOT
    # raise prints a number instead. The asymmetry is the finding.
    ("oos-noread",   "oos", ['CLEAR 100', 'A$=STRING$(200,"A")',
                             'PRINT "[";FRE("");"]"']),

    # --- D-ARYOOS: the STRING ARRAY-ELEMENT store's own pool exhaustion -------
    # TODO.md "`ex_let_arr_str` SWALLOWS AN OUT-OF-STRING-SPACE AND THE PROGRAM
    # RUNS ON" (measured 2026-08-08, re-measured 2026-08-09). The claim under
    # measurement is NOT "zerobas has no string-space error" -- the SCALAR store
    # gets it right, which is what makes this a finding about ONE store rather
    # than about the engine. So the scalar row sits right beside the array one
    # and both are gated: a fix that broke the scalar path would show HERE.
    #
    # 🎯 THE DISCRIMINATOR IS THE MESSAGE, NEVER "did it error". Adding the
    # missing check to `ex_let_arr_str` without splitting `ARY_ERR=4` raises
    # FPERR=6 -> ERR 7 `Out of memory`, where the reference says `Out of string
    # space` (ERR 14). Every row below is read as TEXT through the echo-anchored
    # tail (or the bracket span), so the two are told apart; a row scored
    # error-vs-no-error would go green on that wrong fix.
    #
    # PREDICTIONS, WRITTEN BEFORE THE FIRST RUN (2026-08-20):
    #   oos-arystore-ctl  ref " 25 "                zb " 25 "               PASS
    #   oos-arystore      ref "Out of string space" zb ""      (swallowed)  FAIL
    #   oos-autostore     ref "Out of string space" zb ""      (swallowed)  FAIL
    #   oos-arycont       ref "<none>" (aborted)    zb "OK"                 FAIL
    #   oos-scalarstore   ref "Out of string space" zb "Out of string space" PASS
    #   oos-strdim-oom    ref "Out of memory"       zb "Out of memory"      PASS
    #
    # POOL ARITHMETIC THESE ROWS ARE SIZED AGAINST (the `arychg` battery below
    # measures it; the sizes here are chosen so the LAST line is a store that
    # cannot fit on EITHER machine, which is the only thing an echo-anchored
    # tail can read in direct mode -- an earlier line's abort is invisible to
    # the tail of a later one).
    ("oos-arystore-ctl", "oos", ['CLEAR 200', 'DIM A$(5)',
                                 'B$=STRING$(25,"A")', 'A$(1)=B$',
                                 'PRINT "[";LEN(A$(1));"]"']),
    ("oos-arystore",  "oos", ['CLEAR 60', 'DIM A$(5)', 'B$=STRING$(25,"A")',
                              'A$(1)=B$', 'A$(2)=B$']),
    # the same store reached through AUTO-DIM rather than an explicit DIM: the
    # element is created by the resolve, and the copy is the same op=3.
    ("oos-autostore", "oos", ['CLEAR 60', 'B$=STRING$(25,"A")',
                              'A$(1)=B$', 'A$(2)=B$']),
    # 🔴 THE PROGRAM RUNS ON. Direct mode cannot see an earlier LINE's abort, so
    # the continuation claim is expressed WITHIN ONE LINE: the failing store and
    # the PRINT are `:`-joined, and a machine that aborts never reaches the
    # bracket. ref <none> / zb "OK" is the whole finding in one row.
    ("oos-arycont",   "oos", ['CLEAR 60:DIM A$(5)', 'B$=STRING$(25,"A")',
                              'A$(1)=B$:A$(2)=B$:PRINT"[OK]"']),
    # 🎯 THE ROW THAT MAKES IT SPECIFIC TO THE ARRAY-ELEMENT STORE. Same pool,
    # same sizes, same source variable -- only the DESTINATION differs.
    ("oos-scalarstore","oos", ['CLEAR 60', 'B$=STRING$(25,"A")', 'C$=B$',
                               'D$=B$']),
    # 🎯 THE DENOMINATOR ROW FOR THE SPLIT, and it is the one that rules out the
    # cheap reading of it. `ARY_ERR=4` serves TWO failures: the array's own
    # ALLOCATION (variable space) and `aeng_copy_str`'s heap_alloc (the string
    # pool). A split keyed on the array's TYPE would send this row -- a STRING
    # array whose SLOTS will not fit -- to `Out of string space`, and it is
    # `Out of memory` on both machines. So the split must be by SITE.
    # 3 * 20001 = 60003 bytes: under $FFFF, so D-ARR-B's size rule does NOT
    # fire (that would be `Subscript out of range`), and over the free variable
    # space of BOTH machines (28815 ref / 15667 zb), so both must allocate-and-
    # fail. The numeric twin is `oos-vs-oom` above.
    ("oos-strdim-oom","oos", ['CLEAR 100', 'DIM A$(20000)']),

    # --- the boot default, and what a BARE `CLEAR` does -----------------------
    ("dflt-boot",    "dflt", ['PRINT "[";FRE("");"]"']),
    # A bare CLEAR: does it RESET the size to the default, or KEEP the current
    # one? Two defensible designs; dflt-keep is the discriminator.
    ("dflt-bare",    "dflt", ['CLEAR', 'PRINT "[";FRE("");"]"']),
    ("dflt-keep",    "dflt", ['CLEAR 500', 'CLEAR', 'PRINT "[";FRE("");"]"']),
    # 🔴 D-CLRFIX 2026-08-23: THIS ROW USED TO ASK A QUESTION ITS STATEMENT
    # COULD NOT REACH. It was `CLEAR 500 : CLEAR ,&HD000: PRINT FRE("")` and it
    # passed on both machines -- because `CLEAR ,himem` is a **Syntax error on
    # the reference**, so FRE printed 500 for the trivial reason that the second
    # statement NEVER RAN. It scored "the ,himem-only form does not resize the
    # pool" and was measuring "the ,himem-only form does not exist".
    # docs/clearpool-vg8020-characterization.md §2.4 is annotated with the same
    # correction. Re-pointed at what is actually there: the CLEAR is now the LAST
    # line, so read() anchors on its ERROR TAIL and both machines must print the
    # same refusal. A vacuous agreement becomes a real differential.
    ("dflt-comma",   "dflt", ['CLEAR 500', 'CLEAR ,&HD000']),
    # RUN and NEW also reset variables -- do they resize the pool?
    ("dflt-new",     "dflt", ['CLEAR 500', 'NEW', 'PRINT "[";FRE("");"]"']),
    ("dflt-run",     "dflt", ['CLEAR 500', 'RUN', 'PRINT "[";FRE("");"]"']),

    # --- CLEAR n's own argument domain ---------------------------------------
    ("dom-neg",      "dom", ['CLEAR -1']),
    ("dom-huge",     "dom", ['CLEAR 60000']),
    ("dom-32768",    "dom", ['CLEAR 32768']),
    ("dom-99999",    "dom", ['CLEAR 99999']),
    ("dom-str",      "dom", ['CLEAR "200"']),

    # --- the `,himem` argument's interaction with the pool --------------------
    ("hmem-both",    "hmem", ['CLEAR 500,&HD000', 'PRINT "[";FRE("");"]"']),
    ("hmem-tight",   "hmem", ['CLEAR 500,&H9000', 'PRINT "[";FRE("");"]"']),
    # 🔴 D-CLRFIX 2026-08-23: vacuous for the same reason as dflt-comma above --
    # §2.8's "`CLEAR ,&HD000` -> 200 (unchanged)" is the BOOT DEFAULT surviving a
    # statement that did not execute. Now anchored on the refusal itself.
    ("hmem-only",    "hmem", ['CLEAR ,&HD000']),

    # --- ✅ GRADUATED 2026-07-29: the ARRAYS-arc divergence this probe found ---
    # ⚠️ This row USED to be the oos-vs-oom row above, with `DIM Q(20000)`, and
    # it was gated. It was measuring two things at once: "the two errors are
    # distinct" (a D-CLP claim, and true) and "which non-string error a huge DIM
    # gives" (an ARRAYS-arc claim, and divergent). The reference answers
    # `Subscript out of range` because it BOUNDS THE ARRAY SIZE BEFORE
    # ALLOCATING; zerobas allocated until it failed and so answered `Out of
    # memory`. The two claims were split into separate rows, the gateable one
    # gated, and this one kept in an `arr` battery as the standing record --
    # "it will turn from `----` to a gateable row the day the ARRAYS arc fixes
    # it."
    #
    # That day is D-ARR-B (docs/spec-basic-arrdim.md): the rule is
    # `elsize * PI(bound_k+1) > $FFFF` and it is now implemented, so the row
    # moves into the gated `oos` battery where it always belonged. Keeping a
    # never-gated row after its reason expires is how a gate quietly stops
    # measuring what it says it measures.
    ("oos-dim-huge", "oos", ['CLEAR 100', 'DIM Q(20000)']),

    # --- BODY SHARING: reported, never gated (S-CLP-5, signed off OUT) --------
    # zerobas OWNS a body per variable (sh_var_store heap-copies whatever the
    # rvalue descriptor points at); the reference decides ownership per SOURCE.
    # That single difference shows up in BOTH directions, which is why these
    # three sit together and why no amount of pool arithmetic reconciles them:
    # making them agree means changing who owns a string body, not how big the
    # pool is. S-CLP-5 puts that out of D-CLP's scope; it is its own slice.
    ("hold-alias",   "share", ['CLEAR 500', 'A$=STRING$(100,"A")', 'B$=A$',
                               'PRINT "[";FRE("");"]"']),
    # ⚠️ S-CLP-4, MEASURED 2026-07-29 (it was the open question the spec §4 and
    # the slice brief both said to settle BEFORE writing literal handling):
    #   direct  `A$="ABCDE"`            -> 495  (hold-literal, above: charges 5)
    #   stored  `10 A$="ABCDE" : RUN`   -> 500  (charges NOTHING)
    #   stored  a 25-char literal       -> 500  (still nothing -- so it is not
    #                                            5-bytes-of-noise, it is zero)
    # The reference points a stored literal's descriptor straight AT THE PROGRAM
    # TEXT, whose bytes are permanent; a direct line's buffer is transient, so
    # there it is forced to copy. The 25-char row is the discriminator: 5 vs 0
    # is arguable as slack, 25 vs 0 is not.
    # ⚠️ The finding does NOT change heap_alloc, which is what S-CLP-4 expected.
    # Charging zero requires STORING BY REFERENCE, i.e. exactly the body-sharing
    # machinery hold-alias is about -- so it lands in S-CLP-5's scope, not this
    # slice's, and it is reported here rather than gated. It also carries a real
    # hazard worth writing down before anyone implements it: a variable pointing
    # into program text means `MID$(A$,1,1)="X"` writes into the PROGRAM.
    # RUN keeps POOLSIZE (dflt-run pins that separately), so `CLEAR 500` still
    # holds when the readout is taken.
    ("hold-lit-prog","share", ['CLEAR 500', '10 A$="ABCDE"', 'RUN',
                               'PRINT "[";FRE("");"]"']),
    ("hold-lit-p25", "share", ['CLEAR 500', '10 A$="AAAAAAAAAAAAAAAAAAAAAAAAA"',
                               'RUN', 'PRINT "[";FRE("");"]"']),

    # --- REPORTED, NEVER GATED ------------------------------------------------
    # Does the pool come OUT of the variable space? If it does, FRE(0) after
    # CLEAR 4000 is ~3800 less than after CLEAR 200. FRE(0) is a property of
    # each machine's memory map and can never be made to agree across two
    # different machines, so these are read as a PAIR on the reference column
    # and their DIFFERENCE is the finding. (The tempting one-line form
    # `CLEAR 200:X=FRE(0):CLEAR 1000:PRINT X>FRE(0)` measures nothing: the
    # second CLEAR wipes X.)
    # --- D-ARYOOS pool arithmetic --------------------------------------------
    # What a string ARRAY-ELEMENT store charges the pool, step by step. These
    # rows exist to SIZE the `oos` error rows above -- an error row is only
    # readable if the LAST line is the one that cannot fit -- and to pin
    # `arychg-dimonly`: a `DIM A$(n)` charges the pool NOTHING, because the
    # 3-byte [len][ptr] slots come out of VARIABLE space. That is the
    # arithmetic behind `oos-strdim-oom` and the whole reason the ARY_ERR
    # split is by SITE.
    # 🔴 THREE OF THE FOUR PREDICTIONS WERE WRONG, AND IN THE SAME DIRECTION.
    # Written before the first run (2026-08-20), ref / zb:
    #   arychg-dimonly  200 / 200   -> 200 / 200   ✅ exact
    #   arychg-scalar   150 / 175   -> 175 / 175   🔴 ref charges 25, not 50
    #   arychg-store1   125 / 150   -> 150 / 150   🔴
    #   arychg-store2   100 / 125   -> 125 / 125   🔴
    # The prediction came from the `share` battery's "an alias charges twice
    # there", which is a statement about `B$=A$` and does NOT generalise to a
    # store out of a temp: the reference ADOPTS a temp's body exactly as
    # zerobas does. All four agree to the byte, so all four are gated. The
    # sizing survived the miss only by luck of direction -- an over-estimate of
    # the reference's charge, which moves the failure EARLIER, and both
    # machines happen to fail on the same line anyway.
    ("arychg-dimonly","arychg", ['CLEAR 200', 'DIM A$(5)',
                                 'PRINT "[";FRE("");"]"']),
    ("arychg-scalar", "arychg", ['CLEAR 200', 'B$=STRING$(25,"A")',
                                 'PRINT "[";FRE("");"]"']),
    ("arychg-store1", "arychg", ['CLEAR 200', 'DIM A$(5)',
                                 'B$=STRING$(25,"A")', 'A$(1)=B$',
                                 'PRINT "[";FRE("");"]"']),
    ("arychg-store2", "arychg", ['CLEAR 200', 'DIM A$(5)',
                                 'B$=STRING$(25,"A")', 'A$(1)=B$', 'A$(2)=B$',
                                 'PRINT "[";FRE("");"]"']),

    ("rep-fre0-200", "rep", ['CLEAR 200', 'PRINT "[";FRE(0);"]"']),
    ("rep-fre0-4000","rep", ['CLEAR 4000', 'PRINT "[";FRE(0);"]"']),

    # --- tslice: what does slicing a TEMP charge the pool? (D-POOLCAP) --------
    # The transient PEAK of `LEFT$(X$+X$,0)`, which a before/after FRE("") cannot
    # see. D-POOLCAP moved the threshold 120 -> 100 by routing LEFT$/RIGHT$/MID$
    # through str_snapshot_keep, and NOTHING PINNED THE RECOVERED GROUND -- the
    # fix could regress silently. 100 and 120 are gated here for exactly that.
    ("tslice-100",  "tslice", ['CLEAR 100', BIG,
                               'PRINT "[";LEN(LEFT$(X$+X$,0));"]"']),
    ("tslice-120",  "tslice", ['CLEAR 120', BIG,
                               'PRINT "[";LEN(LEFT$(X$+X$,0));"]"']),
    # 🎯 THE ROW THAT SEPARATES THE MECHANISM: slicing a VARIABLE is green at
    # CLEAR 70 on every side. Only slicing a TEMP diverges, so a tslice-70
    # failure that took this row with it would be a different defect.
    ("tslice-var70","tslice", ['CLEAR 70', BIG,
                               'PRINT "[";LEN(LEFT$(X$,0));"]"']),

    # --- ✅ PROMOTED TO GATED 2026-08-28 (D-CONCATPEAK) -----------------------
    # These were `topen` -- reported, never gated -- because zerobas raised
    # `Out of string space` at CLEAR 70/80 where both references answer 0. The
    # cause is fixed: sh_append now grows the accumulator IN PLACE when it is the
    # top heap body, so the transient peak is 3L+4 instead of 4L+4. The rows that
    # DOCUMENTED the open half are now the rows that stop it reopening.
    ("tslice-70",   "tslice", ['CLEAR 70', BIG,
                               'PRINT "[";LEN(LEFT$(X$+X$,0));"]"']),
    ("tslice-80",   "tslice", ['CLEAR 80', BIG,
                               'PRINT "[";LEN(LEFT$(X$+X$,0));"]"']),
    # 🎯 AND THE PAIR THAT PINS THE PEAK TO A SINGLE BYTE. These rows hold only
    # X$ (20 B) -- there is no A$ here -- so the model is peak = 3L = 60, and it
    # was MEASURED on all three sides, not computed: 59 is `Out of string space`
    # everywhere, 60 answers 0 everywhere. zerobas's peak now equals the
    # references' peak EXACTLY, not approximately.
    # 🔴 tslice-59 IS THE LOAD-BEARING HALF. A row that merely passes says the
    # pool was big enough; a row that FAILS one byte lower says the peak is what
    # the mechanism claims. Without it, a change that stopped enforcing the pool
    # at all would leave every other tslice row green.
    # ⚠️ An earlier version of this comment asserted 3L+4 = 64 and predicted 60
    # would FAIL -- carried over from scratchpad/concatpeak_probe.py, whose rows
    # DO also hold a 4-byte A$. The row was right and the arithmetic beside it
    # was wrong; the constant did not survive the change of fixture.
    ("tslice-59",   "tslice", ['CLEAR 59', BIG,
                               'PRINT "[";LEN(LEFT$(X$+X$,0));"]"']),
    ("tslice-60",   "tslice", ['CLEAR 60', BIG,
                               'PRINT "[";LEN(LEFT$(X$+X$,0));"]"']),
]


# The `repro` battery's expected REFERENCE answers, recorded 2026-07-27 in
# docs/binfre-vg8020-characterization.md §1. Checked against the oracle column
# alone: if the VG-8020 stops answering these, the oracle or the harness moved
# and no other row in the run means anything -- regardless of whether zerobas
# happens to agree with it. [[validate-oracle-artifacts]]
REPRO_EXPECT = {
    "repro-500":  "500",
    "repro-200":  "200",
    "repro-100":  "100",
    "repro-hold": "400",
}


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
                    help="share one boot across the matrix. NOT the default: a "
                         "case's CLEAR resizes the pool PERSISTENTLY, so it "
                         "leaks into every follower, and the reset that would "
                         "undo it is the very thing under measurement.")
    ap.add_argument("--gate", action="store_true",
                    help="fail on any divergence; without it every row is "
                         "reported as a straight differential")
    args = ap.parse_args()

    sel = [c for c in CASES if not args.only or args.only in c[0]]
    if not sel:
        print("APPARATUS FAILURE: no rows selected")
        return 1
    # ⚠️ APPARATUS GUARD. The readouts are echo-anchored and an echo longer than
    # the 40-column screen wraps, after which it can never be matched -- the
    # fault that made eleven rows of the first run read <none> on the REFERENCE.
    # A row that cannot be read is a silent hole, so this is an error, not a
    # warning, and it fires before a single emulator is booted.
    toolong = [(lbl, ln) for lbl, _b, lines in sel for ln in lines
               if len(ln) >= ECHO_MAX]
    if toolong:
        print(f"APPARATUS FAILURE: these lines are >= the reference's boot LINLEN "
              f"({ECHO_MAX}), so their echo wraps and the readout cannot anchor "
              f"on it:")
        for lbl, ln in toolong:
            print(f"     {lbl}: {len(ln)} chars {ln!r}")
        return 1

    specs = [("direct", ["CLS"] + lines) for _, _, lines in sel]

    def read(i, raw):
        """A value row reads the bracket span; an error row reads the
        echo-anchored tail. Both anchor on the case's LAST line. A value row
        that ABORTED has no ']' and reads <none>, which is distinguishable from
        a wrong value."""
        if raw is None:
            return None
        last = sel[i][2][-1]
        if "[" in last:
            v = omsx_repl.result_span_after_echo(raw, last)
            return v if v is not None else "<none>"
        t = omsx_repl.screen_tail(raw, last)
        return t if t is not None else "<no echo>"

    def compare(i, rr, zz):
        a, b = read(i, rr), read(i, zz)
        return a is not None and b is not None and norm(a) == norm(b)

    verdicts, ref_raws, zb_raws = omsx_repl.run_differential(
        args.machine, args.zb_machine, specs, compare,
        batch=args.batch, reset=("NEW", "CLS"))

    npass = 0
    for i, (label, battery, lines) in enumerate(sel):
        rt, zt = read(i, ref_raws[i]), read(i, zb_raws[i])
        ok = verdicts[i]
        gated = battery not in UNGATED
        npass += 1 if (ok and gated) else 0
        mark = "----" if not gated else ("PASS" if ok else "FAIL")
        print(f"{mark:5} {battery:5} {label:14} {':'.join(lines)[:44]:44}")
        print(f"        ref: {rt!r}")
        if not ok:
            print(f"        zb : {zt!r}")
        sys.stdout.flush()

    ntot = sum(1 for c in sel if c[1] not in UNGATED)
    nrep = len(sel) - ntot
    print(f"\n{npass}/{ntot} gated rows agree with the reference"
          + (f"  ({nrep} reported, never gated)" if nrep else ""))

    # --- the ORACLE check, before any verdict is read as a finding ------------
    bad_repro = []
    for i, (label, _b, _l) in enumerate(sel):
        want = REPRO_EXPECT.get(label)
        if want is None:
            continue
        got = read(i, ref_raws[i])
        if norm(got) != norm(want):
            bad_repro.append(f"{label}: want {want!r}, oracle said {got!r}")
    if bad_repro:
        print("⚠️ THE ORACLE DID NOT REPRODUCE ITS OWN RECORDED ANSWERS:")
        for b in bad_repro:
            print(f"     {b}")
        print("   No row in this run is readable — the reference or the harness "
              "moved since docs/binfre-vg8020-characterization.md §1.")
        return 1

    bad_ctl = [sel[i][0] for i in range(len(sel))
               if sel[i][1] == "ctl" and not verdicts[i]]
    if bad_ctl:
        print(f"⚠️ CONTROL ROWS DIVERGED ({', '.join(bad_ctl)}) — no other row in "
              f"this run is readable as a D-CLP finding")
        return 1
    if args.gate and npass != ntot:
        print("SOME FAILED")
        return 1
    print("ALL PASS" if npass == ntot else "REPORTED (not gated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
