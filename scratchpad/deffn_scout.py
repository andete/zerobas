#!/usr/bin/env python3
"""DEF FN SCOUT, round 1 — what does the reference STORE?

`make kwsweep` at `4b2c5a5`: MISSING=1, and it is `deffn`.
    DEF FNA(X)=X+1:PRINT"[";FNA(2);"]"   ref '[ 3 ]'   zb 'Syntax error in 10'
It is the ONLY genuinely missing MSX1 reserved word, and `TODO.md` has carried
its price as *"an arc, not a slice (200-400 B): a definition table, argument
binding, re-entrant evaluation"* — an ASSERTION that has never been measured.
SCREEN 3 sat in exactly that position ("unpriced, NEVER SCOUTED") until it was
priced and FIT, so the first job is to stop guessing.

🎯 AND THE FIRST THING TO MEASURE IS THE CRUNCH, NOT THE BEHAVIOUR. D-FNRUN's
whole finding was that a filed DECLINE was refuted by the STORED TOKEN BYTES:
what a statement costs is decided by what the tokeniser has to emit, and this
tree has no `FN` token at all (`basic/kwtable.inc` has a row for "DEF" and none
for "FN"). Whether `FN` is its own token, whether `DEF FN` is one token or two,
and whether the NAME is stored as ASCII or as a variable reference are all
questions the reference answers by what it puts in memory.

⚠️ THE PROGRAM IS NEVER RUN. The dump starts at line 100, so lines 10/20 are
crunched and stored but never executed -- which is the only way to read zerobas's
crunch of a statement it cannot execute. `TXTTAB` ($F676) is read at run time
rather than assumed, because the program area start differs between a
disk-equipped machine and a bare one.
"""
from __future__ import annotations
import os, re, sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}
_only = os.environ.get("DEFFN_SIDES")
if _only:
    SIDES = {k: v for k, v in SIDES.items() if k in _only.split(",")}

# the dumper: read TXTTAB, then 4 rows of 16 bytes as hex, each fenced so the
# scrape can find it even if the screen wraps around it
# 🔴 THE DUMP IS A DIRECT-MODE COMMAND, NOT PART OF THE PROGRAM. Round 1 put it
# at lines 100..140 and ran `RUN 100`, and on zerobas that returned NOTHING with
# the raw screen reading `Syntax error in 10` -- so a line the dump was supposed
# to READ stopped the dump from running at all. A stored line this build cannot
# execute must be read WITHOUT executing anything, which direct mode does.
# ⚠️ The echo of this command cannot be mistaken for its output: the fence wants
# exactly 32 hex digits between < and >, which the source text does not contain.
DUMP_DIRECT = ('T=PEEK(&HF676)+256*PEEK(&HF677):FORJ=0TO3:S$="":FORI=0TO15:'
               'S$=S$+RIGHT$("0"+HEX$(PEEK(T+J*16+I)),2):NEXT:'
               'PRINT"<";S$;">":NEXT')

SUBJECTS = {
    # the kwsweep row itself, split so the definition and the call are separate
    # stored lines and their bytes can be told apart
    "deffn.basic":  ["10 DEF FNA(X)=X+1", "20 PRINT FNA(2)"],
    # a two-letter name and a different parameter letter: says whether the name
    # is stored as ASCII characters or as something narrower
    "deffn.name2":  ["10 DEF FNQZ(Y)=Y*2", "20 PRINT FNQZ(3)"],
    # 🟢 CONTROL: `DEF USR` already exists here and already crunches. If its bytes
    # match on all three sides, the dumper and the DEF token are fine and any
    # divergence in the FN rows is about FN.
    "defusr.ctl":   ["10 DEF USR=&HC000", "20 PRINT USR(0)"],
    # ...and a plain expression with a variable call-shape, so "A(2)" as an ARRAY
    # reference can be told from "FNA(2)" as a function call in the crunch.
    "array.ctl":    ["10 DIM A(5)", "20 PRINT A(2)"],
}

# ===========================================================================
# ROUND 2 — the SEMANTICS, because they are what the price is made of.
#
# 🎯 ROUND 1 DECODED, and the two controls (`defusr.ctl`, `array.ctl`) are
# BYTE-IDENTICAL on all three sides, so the dumper and the DEF path are sound and
# any FN divergence is about FN:
#
#   10 DEF FNA(X)=X+1   ->  97 20 DE 41 28 58 29 EF 58 F1 12 00
#                           DEF sp FN  A  (  X  )  =  X  +  1  eol
#   10 DEF FNQZ(Y)=Y*2  ->  97 20 DE 51 5A 28 59 29 EF 59 F3 13 00
#   10 DEF USR=&HC000   ->  97 20 DD EF 0C 00 C0 00
#
# `FN` IS ONE TOKEN, $DE -- the byte immediately after `USR`'s $DD, which this
# tree already emits and already dispatches. The NAME is stored as plain ASCII
# after the token, arbitrary length, exactly like a variable name; there is no
# name table in the crunch. That already contradicts half of the filed price
# ("a definition table"): the reference keeps the definition wherever it keeps
# variables, and reads the name out of the program text at run time.
#
# ⚠️ SO THE REMAINING COST IS RUNTIME SEMANTICS, AND EVERY ONE OF THESE ROWS
# CHANGES THE DESIGN. Whether the parameter is a REAL variable that survives the
# call decides whether a save/restore is needed at all; whether more than one
# parameter is legal decides whether there is a list walk; whether a string form
# exists decides whether the entry is typed. Guessing any of them from the
# manual is how a filed price gets to be wrong by 3x.
# 🔴 ROUND 2's READOUT WAS BROKEN AND ITS OWN CONTROL CAUGHT IT. Every one of the
# eleven rows came back as the SOURCE TEXT -- `b.ctl` returned '";X+1;"' -- because
# the fixture ended in `PRINT"[";V;"]"` typed in DIRECT mode, so the line's ECHO
# sits on the screen containing `[";V;"]`, and the `[...]` regex found THAT. All
# eleven "agreed" and not one was a measurement.
# 🎯 THE FIX IS THE ONE THE PAINT PROBES ALREADY USE: clear the screen between the
# echo and the print. Each case is now (setup lines, the expression to capture),
# and the harness appends `CLS:PRINT"[";<expr>;"]"` on its own line -- so the only
# `[...]` left on the screen is the answer. The error handler clears too.
# 🟢 `b.ctl` stays, and it is now load-bearing twice: it says the fixture runs AND
# that the readout reads the output rather than the source.
BEHAV: dict[str, tuple[list[str], str]] = {
    # does calling FNA(2) clobber a REAL variable X? MS BASIC binds through the
    # ordinary variable table, which would leave X = 2, not 5.
    "b.param":    (['X=5:DEF FNA(X)=X+1', 'Y=FNA(2)'], 'Y;X'),
    # ...and the same question when the parameter name is NOT otherwise used
    "b.paramnew": (['DEF FNA(Q)=Q+1', 'Y=FNA(7)'], 'Y;Q'),
    # calling an undefined function -- which ERR?
    "b.undef":    ([], 'FNZ(1)'),
    # ...and calling one defined on a LATER line (never executed yet)
    "b.forward":  (['GOTO 60', 'DEF FNA(X)=X+1'], 'FNA(2)'),
    # a string-typed function
    "b.str":      (['DEF FNA$(X$)=X$+"!"'], 'FNA$("hi")'),
    # more than one parameter: legal, or Syntax error?
    "b.two":      (['DEF FNA(X,Y)=X+Y'], 'FNA(2,3)'),
    # no parameter at all
    "b.noarg":    (['DEF FNA=7'], 'FNA'),
    # redefinition
    "b.redef":    (['DEF FNA(X)=X+1', 'DEF FNA(X)=X+2'], 'FNA(1)'),
    # one function calling another -- says whether evaluation must be re-entrant
    "b.nested":   (['DEF FNA(X)=X+1', 'DEF FNB(X)=FNA(X)*2'], 'FNB(3)'),
    # direct recursion -- what the reference DOES, not what it should
    "b.recurse":  (['DEF FNA(X)=FNA(X)'], 'FNA(1)'),
    # 🟢 CONTROL: an ordinary expression through the same fixture shape.
    "b.ctl":      (['X=5'], 'X+1'),
}


# ===========================================================================
# ROUND 5 — WHAT THE SCOUT EXPLICITLY DID NOT CLAIM (D-DEFFN, 2026-08-22).
#
# The scout's §6 lists five open questions and this round answers them, BEFORE
# any code is written, because each one changes the design:
#
#   * ERROR ORDERING. D-LINERR's rule: WHERE a check sits is itself a claim.
#     Nothing here is measured. In particular: is the DEF body PARSED at
#     definition time or only at call time (that decides whether `DEF` is a
#     scan-to-end-of-statement or a real parse); which fault wins when a line is
#     wrong in two ways; does an undefined NAME beat a wrong argument COUNT; and
#     -- the one that decides how expensive the restore is -- IS THE FORMAL
#     RESTORED WHEN THE BODY RAISES?
#   * THE PARAMETER CEILING. Two are measured; the maximum is not.
#   * DEF FN in DIRECT mode, and DEF FN inside `IF ... THEN`.
#   * DEFINT/DEFSTR interaction -- does a DEFtbl default reach the formal?
#   * Must the formal be a SIMPLE variable (`DEF FNA(B(1))=...`)?
#
# 🔴 EVERY ROW HERE RUNS THROUGH run_behav's fixture, which round 3 and round 4
# already debugged (the CLS before the print, and the expression going straight
# into the PRINT rather than through `V=`). A row whose face is <NO OUTPUT> is a
# MISSING MEASUREMENT, not a divergence, and main() now says so out loud.
ORDER: dict[str, tuple[list[str], str]] = {
    # --- is the body parsed at DEF time? -----------------------------------
    # If `[ OK ]`, DEF stores the text and never looks at it; if ERR 2 AT 30,
    # DEF parses. This single row decides whether ex_deffn is a SCAN or a PARSE.
    "o.lazybody": (['DEF FNA(X)=X+*2'], '"OK"'),
    # ...and the arithmetic version: a fault that only a RUN of the body can see
    "o.lazydiv":  (['DEF FNA(X)=X/0'], '"OK"'),
    # --- which fault wins ---------------------------------------------------
    # wrong in TWO ways at once: no name AND an unclosed parameter list
    "o.twofault": (['DEF FN(X'], '"OK"'),
    # a name that cannot be one (leading digit) -- and no `=` either
    "o.badname":  (['DEF FN1(X)'], '"OK"'),
    # missing `=` alone
    "o.noeq":     (['DEF FNA(X) X+1'], '"OK"'),
    # --- undefined name vs wrong argument count ------------------------------
    # ERR 18 (undefined) or ERR 2 (syntax)? The name is undefined AND the call
    # shape is one no definition could match.
    "o.undefarg": ([], 'FNZ(1,2)'),
    # too MANY actuals for a defined function
    "o.toomany":  (['DEF FNA(X)=X+1'], 'FNA(1,2)'),
    # too FEW actuals
    "o.toofew":   (['DEF FNA(X,Y)=X+Y'], 'FNA(1)'),
    # actuals supplied to a NO-parameter function
    "o.argnoarg": (['DEF FNA=7'], 'FNA(1)'),
    # a bare name where the definition takes one
    "o.barecall": (['DEF FNA(X)=X+1'], 'FNA'),
    # --- type faults, and whether the formal survives one --------------------
    # string actual into a numeric formal: which ERR...
    "o.strnum":   (['X=5:DEF FNA(X)=X+1'], 'FNA("hi")'),
    # ...and IS X STILL 5 after it raised? (the trap prints X, so the answer
    # comes back inside the ERR face -- see the 900 line below)
    "o.strnumx":  (['X=5:DEF FNA(X)=X+1', 'ON ERROR GOTO 800', 'Y=FNA("hi")'],
                   'X;E', ['800 E=ERR:RESUME 60']),
    # numeric actual into a string formal
    "o.numstr":   (['DEF FNA$(X$)=X$+"!"'], 'FNA$(1)'),
    # 🎯 THE RESTORE-ON-ERROR ROW: the body itself raises. If X reads 5 the
    # restore is on the ERROR path too, which is a materially dearer design
    # (the unwind has to run) than a restore only on the normal return.
    "o.errrestore": (['X=5:DEF FNA(X)=X/0', 'ON ERROR GOTO 800', 'Y=FNA(2)'],
                     'X;E', ['800 E=ERR:RESUME 60']),
    # --- the parameter ceiling ----------------------------------------------
    "o.p3":       (['DEF FNA(A,B,C)=A'], 'FNA(1,2,3)'),
    "o.p5":       (['DEF FNA(A,B,C,D,E)=A'], 'FNA(1,2,3,4,5)'),
    "o.p8":       (['DEF FNA(A,B,C,D,E,F,G,H)=A'], 'FNA(1,2,3,4,5,6,7,8)'),
    "o.p12":      (['DEF FNA(A,B,C,D,E,F,G,H,I,J,K,L)=A'],
                   'FNA(1,2,3,4,5,6,7,8,9,1,2,3)'),
    "o.p16":      (['DEF FNA(A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P)=A'],
                   'FNA(1,2,3,4,5,6,7,8,9,1,2,3,4,5,6,7)'),
    # --- IF ... THEN --------------------------------------------------------
    "o.ifthen":   (['IF 1 THEN DEF FNA(X)=X+1'], 'FNA(2)'),
    # ...and the branch NOT taken: is the definition still absent? (ERR 18)
    "o.ifnot":    (['IF 0 THEN DEF FNA(X)=X+1'], 'FNA(2)'),
    # --- DEFINT / DEFSTR reach the formal? ----------------------------------
    # unsuffixed X is DOUBLE by default, so FNA(5) is 2.5; under DEFINT A-Z the
    # question is whether the FORMAL and the BODY see the integer default.
    "o.defint":   (['DEFINT A-Z', 'DEF FNA(X)=X/2'], 'FNA(5)'),
    # 🟢 the same expression with NO DEFINT -- the control that says the row
    # above is about DEFINT and not about `/`
    "o.defint.ctl": (['DEF FNA(X)=X/2'], 'FNA(5)'),
    # DEFSTR: an unsuffixed formal becomes a STRING name
    "o.defstr":   (['DEFSTR A-Z', 'DEF FNA(X)=X+"!"'], 'FNA("hi")'),
    # --- must the formal be a SIMPLE variable? ------------------------------
    "o.aryformal": (['DIM B(5)', 'DEF FNA(B(1))=B(1)+1'], 'FNA(2)'),
    # a formal with an explicit type suffix, and a function with one
    "o.sufformal": (['DEF FNA(X%)=X%+1'], 'FNA(2)'),
    "o.suffn":     (['DEF FNA%(X)=X+1'], 'FNA%(2)'),
    # --- evaluation order of the actual against the formal ------------------
    # 🎯 X is BOTH the formal and part of the actual. If the actual is evaluated
    # BEFORE the formal is overwritten, this is (5+1)*10 = 60.
    "o.actualfirst": (['X=5:DEF FNA(X)=X*10'], 'FNA(X+1)'),
    # nested: FNB's own formal must survive FNA's call (the stack-discipline row)
    "o.nestsame": (['DEF FNA(X)=X', 'DEF FNB(X)=FNA(X+1)+X'], 'FNB(3)'),
    # 🟢 CONTROL, same as round 3's: the fixture runs and the readout reads the
    # OUTPUT rather than the source.
    "o.ctl":      (['X=5'], 'X+1'),
}

# DIRECT-mode rows: `DEF FN` typed at the prompt, never stored. The whole point
# is that nothing is a program line, so run_behav's fixture cannot express it.
# 🔴 THE ECHO IS THE HAZARD AGAIN (round 3's eleven false agreements): each
# command's own text sits on the screen, so the capture is a `CLS` followed by
# the PRINT, and the fence wants a `[...]` the typed text does not contain.
DIRECT: dict[str, list[str]] = {
    # is DEF FN legal in direct mode at all? (MS BASIC's `Illegal direct`, ERR 12,
    # is the shape to look for; MSX may simply accept it)
    "d.def":     ['DEF FNA(X)=X+1', 'CLS:PRINT"[";FNA(2);"]"'],
    # ...and does a direct-mode definition survive into a RUN?
    "d.defrun":  ['DEF FNA(X)=X+1', '10 CLS:PRINT"[";FNA(2);"]"', 'RUN'],
    # 🟢 CONTROL: an ordinary direct-mode assignment through the same shape
    "d.ctl":     ['X=5', 'CLS:PRINT"[";X+1;"]"'],
}


# ===========================================================================
# ROUND 6 — THE SEPARATORS. Round 5 measured 30 rows, both references agreeing
# on every one, and four of its greens have a SECOND CAUSE that would lead to a
# different implementation. This round is the cases that separate them.
#
#   * `o.nestsame` = 7 proves the save/restore NESTS -- but a shadow parameter
#     stack nests just as well as a save/restore of a real variable cell. The
#     separator is a function whose body calls ANOTHER function that names the
#     OUTER one's formal: dynamic scope through the real table sees the actual,
#     a shadow does not.
#   * `o.errrestore` = `5 11` proves X survives a raising body -- but "X was
#     restored on the error path" and "X was never a real variable" look the
#     same. The row above settles that too.
#   * 🎯 AND THE ONE THAT DECIDES WHERE THE DEFINITION LIVES: if the definition
#     is kept in the VARIABLE TABLE (which is what a bit-7 name key would make
#     it here), then `CLEAR` must erase it. If it lives anywhere else, it will
#     survive. Nothing in rounds 1-5 asks this and the whole design turns on it.
#   * The ceiling is bracketed 8 legal / 12 ERR 5 and not located.
ORDER.update({
    # --- the ceiling, bisected ----------------------------------------------
    "o.p9":  (['DEF FNA(A,B,C,D,E,F,G,H,I)=A'], 'FNA(1,2,3,4,5,6,7,8,9)'),
    "o.p10": (['DEF FNA(A,B,C,D,E,F,G,H,I,J)=A'], 'FNA(1,2,3,4,5,6,7,8,9,1)'),
    "o.p11": (['DEF FNA(A,B,C,D,E,F,G,H,I,J,K)=A'], 'FNA(1,2,3,4,5,6,7,8,9,1,2)'),
    # --- is the body evaluated in the ORDINARY variable environment? --------
    # a non-formal global inside the body
    "o.global":   (['Y=3:DEF FNA(X)=X+Y'], 'FNA(2)'),
    # 🎯 THE DYNAMIC-SCOPE SEPARATOR. FNB names X, which is FNA's FORMAL and
    # nobody else's. Through the real variable table FNB reads the ACTUAL (2);
    # behind a shadow parameter stack it reads the caller's X (5).
    "o.dynscope": (['X=5', 'DEF FNB(Y)=X', 'DEF FNA(X)=FNB(0)'], 'FNA(2)'),
    # --- does CLEAR erase a definition? (i.e. does it live with variables?) --
    "o.clearwipe": (['DEF FNA(X)=X+1', 'CLEAR'], 'FNA(2)'),
    # 🟢 the control: the same fixture WITHOUT the CLEAR
    "o.clearwipe.ctl": (['DEF FNA(X)=X+1'], 'FNA(2)'),
    # --- is the FN name in the same namespace as a variable? ----------------
    # if `DEF FNA` overwrote the variable A, this prints something other than 9
    "o.namespace": (['A=9:DEF FNA(X)=X+1', 'Y=FNA(2)'], 'A;Y'),
    # --- is the RESULT coerced to the function's own type? ------------------
    # X/2 is 2.5; a `%`-suffixed FN would return 2 if the result is coerced
    "o.fnpct":    (['DEF FNA%(X)=X/2'], 'FNA%(5)'),
    # 🟢 the control that says the row above is about the SUFFIX and not about /
    "o.fnbang":   (['DEF FNA!(X)=X/2'], 'FNA!(5)'),
    # --- and does a FORMAL's own type come from the DEFtbl or the suffix? ---
    # under DEFINT the formal X is int, so X/2 inside the body is still 2.5 --
    # this asks whether it is the FORMAL or the RESULT that DEFINT reached in
    # round 5's o.defint
    "o.defintbang": (['DEFINT A-Z', 'DEF FNA!(X)=X/2'], 'FNA!(5)'),
})

DIRECT.update({
    # round 5's d.def / d.defrun both read <NO OUTPUT> with d.ctl green, so the
    # blank is about DEF FN in direct mode. These two ask what is ON THE SCREEN
    # instead -- run them with DEFFN_RAW=1.
    "d.deferr":  ['DEF FNA(X)=X+1', 'CLS:PRINT"[";FNA(2);"]"'],
})


# ===========================================================================
# ROUND 7 — 🔴 ROUND 6 REFUTED THE CLASSIC MODEL, so this round locates what
# actually happens.
#
# `o.dynscope` = **5**. The fixture is `X=5 : DEF FNB(Y)=X : DEF FNA(X)=FNB(0)`
# and `FNA(2)`. Under the classic MS-BASIC model -- save the FORMAL's cell,
# poke the actual into it, evaluate the body, restore -- FNB's body reads the
# live cell and the answer is **2**. It is 5. Meanwhile `o.actualfirst` = 60
# says FNA's OWN body does see the actual, and `o.nestsame` = 7 says the
# save/restore nests correctly when the inner formal has the SAME name.
#
# 🎯 The hypothesis those three rows leave standing: **the binding does not
# survive a nested FN call** -- i.e. calling any FN restores the outer formal
# before the inner body runs. `o.outerafter` is the row that says so without
# the inner function mentioning X at all, which is what makes it a separator
# rather than another case where two models coincide.
ORDER.update({
    # 🎯 THE SEPARATOR. FNB never mentions X. If merely CALLING an FN ends the
    # outer binding, `FNB(0)+X` reads 0+5 = 5; if the binding survives, 0+2 = 2.
    "o.outerafter": (['X=5', 'DEF FNB(Y)=Y', 'DEF FNA(X)=FNB(0)+X'], 'FNA(2)'),
    # ...and the same shape with the read BEFORE the nested call, so the two
    # halves of the body can be told apart
    "o.outerbefore": (['X=5', 'DEF FNB(Y)=Y', 'DEF FNA(X)=X+FNB(0)'], 'FNA(2)'),
    # 🟢 CONTROL: the identical body with the nested call REMOVED. If this is
    # not 2, the row above is not about nesting.
    "o.outer.ctl": (['X=5', 'DEF FNA(X)=0+X'], 'FNA(2)'),
    # does a nested call to a function taking NO parameter do it too?
    "o.outernoarg": (['X=5', 'DEF FNB=1', 'DEF FNA(X)=FNB+X'], 'FNA(2)'),
    # ...and does an ordinary function call (not FN) disturb it?
    "o.outerabs": (['X=5', 'DEF FNA(X)=ABS(0)+X'], 'FNA(2)'),
    # --- does the DEF-time scan respect a QUOTED colon? ---------------------
    # if `DEF` skips naively to the first ':' the definition text is truncated
    # and this cannot return `a:Q`
    "o.quotedcolon": (['DEF FNA$(X$)=X$+":Q"'], 'FNA$("a")'),
    # 🟢 and the same with a ':' STATEMENT separator after the definition, so
    # the scan is known to stop at a real one
    "o.stmtcolon": (['DEF FNA(X)=X+1:B=9'], 'FNA(2);B'),
    # --- CLEAR: round 6 read <NO OUTPUT> on BOTH references with its own
    # control green, so this is re-run for the RAW screen rather than scored.
    "o.clearwipe2": (['DEF FNA(X)=X+1', 'CLEAR'], 'FNA(2)'),
    # ...and NEW, which also clears variables AND the program
    "o.runtwice": (['DEF FNA(X)=X+1', 'Y=FNA(2)'], 'Y'),
})

BR = re.compile(r"\[([^\]]*)\]")
# 🔴 THE `^`-ANCHOR MADE THIS REGEX STRUCTURALLY UNABLE TO SEE ITS SUBJECT, and
# it failed by returning a VALUE. omsx_repl hands back the 24 screen rows
# CONCATENATED WITH NO NEWLINE, so `re.M`'s `^` can only ever match at offset 0
# -- an UNTRAPPED error message, which is never in row 0, was invisible. Three
# rows across rounds 5-7 read `<NO OUTPUT>` on BOTH references while the raw
# screen plainly said `Undefined user function in 60`, and only the round-5
# NOT-MEASURED guard (which refuses to score a blank) stopped two of them being
# written up as "DEF FN in direct mode produces nothing"
# [[readout-blind-to-its-own-subject]]. The anchor is gone and the message set
# is the one basic/interp.asm's err_msgtab actually prints.
ERRRE = re.compile(r"(Undefined user function|Illegal function call|"
                   r"Subscript out of range|Redimensioned array|Illegal direct|"
                   r"Out of memory|Type mismatch|Out of string space|"
                   r"String too long|Division by zero|Overflow|"
                   r"[A-Z][A-Za-z' ]{2,25} error)")



# ===========================================================================
# ROUND 8 — the two things rounds 6-7 left genuinely open, and the readout fix.
#
# 🔴 ROUND 7 REFUTED ITS OWN HYPOTHESIS. `o.outerafter` and `o.outerbefore` are
# BOTH 2, so a nested FN call does NOT end the outer binding -- yet
# `o.dynscope` is 5, i.e. an INNER function's body reading the OUTER
# function's formal name sees the GLOBAL. Those two cannot both be true of a
# single variable cell, so one more separator is needed, and it has to read the
# cell DIRECTLY rather than through another FN.
#
# 🎯 AND ROUND 7's RAW SCREENS ANSWERED TWO ROWS THE FACE COULD NOT:
#   * `CLEAR` -> `Undefined user function in 60`. **CLEAR ERASES THE
#     DEFINITION**, which is exactly what a definition kept in the VARIABLE
#     TABLE must do, and it is the strongest evidence for that model.
#     (It also wipes the ON ERROR trap, which is why the message came out
#     untrapped and the `[...]` fence never closed.)
#   * `DEF FN` in DIRECT mode raises NOTHING -- no `Illegal direct` -- and the
#     function is then UNDEFINED at the next command.
ORDER.update({
    # 🎯 THE DIRECT READ. Under DEFINT the formal is a 2-byte int, so
    # PEEK(VARPTR(X)) is the low byte of the cell ITSELF: 2 if the actual was
    # written into the real variable, 5 if the body sees a shadow.
    "o.varptr":     (['DEFINT A-Z', 'X=5:DEF FNA(X)=PEEK(VARPTR(X))'], 'FNA(2)'),
    # 🟢 the control: the same PEEK with no FN in the way must read 5
    "o.varptr.ctl": (['DEFINT A-Z', 'X=5'], 'PEEK(VARPTR(X))'),
    # both facts in ONE call, so a fixture fault cannot produce them separately:
    # FNA's own body reads X (x100) and FNB's body reads X. 205 = shadow,
    # 202 = one shared cell.
    "o.dynself":   (['X=5', 'DEF FNB(Y)=X', 'DEF FNA(X)=FNB(0)+X*100'], 'FNA(2)'),
    # ...and with the two definitions in the OTHER order, in case DEF-time
    # variable creation is what moves the answer
    "o.dynorder":  (['X=5', 'DEF FNA(X)=FNB(0)', 'DEF FNB(Y)=X'], 'FNA(2)'),
    # CLEAR again, now that the readout can see an untrapped message
    "o.clearwipe3": (['DEF FNA(X)=X+1', 'CLEAR'], 'FNA(2)'),
    # ...and does NEW-less RUN keep it? (a second call in the same run)
    "o.twocalls":  (['DEF FNA(X)=X+1', 'Y=FNA(2)+FNA(3)'], 'Y'),
})

DIRECT.update({
    # 🎯 is a direct-mode definition usable within the SAME direct line?
    "d.sameline": ['CLS:DEF FNA(X)=X+1:PRINT"[";FNA(2);"]"'],
    # ...and does `DEF FN` in direct mode raise anything at all?
    "d.defonly":  ['CLS:DEF FNA(X)=X+1:PRINT"[OK]"'],
})


# ===========================================================================
# ROUND 9 — 🔴 `o.varptr` AGREED FOR THE WRONG REASON, and this round is the
# case that separates what it could not.
#
# Round 8 read `DEF FNA(X)=PEEK(VARPTR(X))` -> 2 with its no-FN control at 5,
# and that was designed as "the real variable cell holds the actual". IT IS NOT.
# `VARPTR(X)` inside the body resolves X **exactly the way the body does**, so
# it reports the address of whatever cell X denotes there -- a shadow answers it
# just as happily as the real entry [[a-case-that-agrees-can-agree-for-the-wrong-
# reason]]. Meanwhile `o.dynself` = **205** says FNA's body reads X as 2 and
# FNB's body, called from inside it, reads X as 5, which one shared cell cannot
# do.
#
# 🎯 The separator has to take the address from OUTSIDE the body and read it
# from INSIDE, so the name is never resolved in the body's own scope:
#   `X=5 : P=VARPTR(X) : DEF FNA(X)=PEEK(P)` -- P is an ordinary global.
#   2 -> the real entry was written.   5 -> the body binds a shadow.
# and the address-identity form asks it without PEEK at all.
ORDER.update({
    # 🎯 THE SEPARATOR: the address is captured OUTSIDE, read INSIDE.
    "o.realcell":     (['DEFINT A-Z', 'X=5:P=VARPTR(X)', 'DEF FNA(X)=PEEK(P)'],
                       'FNA(2)'),
    # 🟢 CONTROL: the same PEEK(P) with no FN in the way must read 5
    "o.realcell.ctl": (['DEFINT A-Z', 'X=5:P=VARPTR(X)'], 'PEEK(P)'),
    # 🎯 the address-identity form: 0 iff the body's X IS the outer entry
    "o.sameaddr":     (['DEFINT A-Z', 'X=5:P=VARPTR(X)', 'DEF FNA(X)=VARPTR(X)-P'],
                       'FNA(2)'),
    # 🎯 and dynscope's exact shape, asked by ADDRESS instead of by NAME: if the
    # real entry holds the actual, the INNER function reads 2 even though the
    # same inner function reading it by NAME read 5.
    "o.dynaddr":      (['DEFINT A-Z', 'X=5:P=VARPTR(X)', 'DEF FNB(Y)=PEEK(P)',
                        'DEF FNA(X)=FNB(0)'], 'FNA(2)'),
    # --- DEF FN in direct mode is ERR 12: pin it to FN, not to DEF ----------
    "o.ctl2":         (['X=5'], 'X+1'),
})

DIRECT.update({
    # 🟢 THE CONTROL THAT PINS `Illegal direct` TO `DEF FN` AND NOT TO `DEF`:
    # DEF USR in the same position must be accepted.
    "d.defusr":  ['CLS:DEF USR=&HC000:PRINT"[OK]"'],
    # ...and an ordinary statement in the same position, for the third leg
    "d.let":     ['CLS:A=1:PRINT"[OK]"'],
})


# ===========================================================================
# ROUND 10 — where the shadow LIVES, which is the last thing the design needs.
#
# Round 9 settled WHAT: `o.sameaddr` = 30327, i.e. `VARPTR(X)` inside the body
# is a DIFFERENT ADDRESS from `VARPTR(X)` outside it, and `o.realcell` = 5 says
# the outer entry is never written. The formal is a SHADOW.
#
# What is left is whether that shadow is ONE fixed cell or a STACKED frame.
# `o.nestsame` = 7 already implies stacked (a single cell would read 8), but
# that is an inference from a value; these rows read the ADDRESSES.
ORDER.update({
    # the shadow's own address, absolute
    "z.addr":     (['DEFINT A-Z', 'DEF FNA(X)=VARPTR(X)'], 'FNA(2)'),
    # 🎯 the same address taken one level deeper: if the two differ, the frame
    # is stacked; if they are equal, it is one fixed cell (and `o.nestsame`
    # needs another explanation).
    "z.addr2":    (['DEFINT A-Z', 'DEF FNA(X)=VARPTR(X)',
                    'DEF FNB(X)=FNA(0)*0+VARPTR(X)'], 'FNB(2)'),
    # ...and the inner one on its own, for the difference to be readable
    "z.addr2i":   (['DEFINT A-Z', 'DEF FNA(X)=VARPTR(X)',
                    'DEF FNB(X)=FNA(0)'], 'FNB(2)'),
    # 🟢 CONTROL: an ordinary variable's VARPTR through the same fixture
    "z.addr.ctl": (['DEFINT A-Z', 'X=5'], 'VARPTR(X)'),
    # does the ceiling behave like a fixed 9-slot frame at the CALL? (ERR 5 was
    # AT 60, the call, not AT 20, the DEF -- this asks the DEF alone)
    "z.p10def":   (['DEF FNA(A,B,C,D,E,F,G,H,I,J)=A'], '"OK"'),
})

def face(cap):
    if cap is None:
        return "<NO CAPTURE>"
    m = BR.search("".join(cap))
    if m:
        return " ".join(m.group(1).split()) or "<empty>"
    e = ERRRE.search("".join(cap))
    return f"<{e.group(1).strip()}>" if e else "<NO OUTPUT>"


def run_behav(label) -> None:
    spec = BEHAV[label] if label in BEHAV else ORDER[label]
    lines, expr = spec[0], spec[1]
    extra = spec[2] if len(spec) > 2 else []      # ROUND 5: own handler lines
    body = ["10 ON ERROR GOTO 900"]
    body += [f"{20 + 10 * k} {ln}" for k, ln in enumerate(lines)]
    # 🔴 ROUND 3's CAPTURE LINE WAS ITSELF A SYNTAX ERROR ON TWO ROWS. It built
    # `60 V=<expr>`, and `b.param`'s expr is `Y;X` -- two values, which is PRINT
    # syntax and not an expression -- so both references reported ERR 2 AT 60 and
    # the row read as a divergence about DEF FN. It was a divergence about the
    # harness. The expression now goes straight into the PRINT, after the CLS
    # that removes the echoes, so any number of values is fine and nothing is
    # assigned on the way.
    body += [f'60 CLS:PRINT"[";{expr};"]":END']
    body += list(extra)
    body += ['900 CLS:PRINT"[ERR";ERR;"AT";ERL;"]":END']
    if len(lines) > 4:                            # 20,30,40,50 then 60 is taken
        raise SystemExit(f"{label}: {len(lines)} setup lines would collide with 60")
    row = {}
    for side, cfg in SIDES.items():
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
            batch=False, boot=cfg["boot"], step=8.0, cap_gap=10.0, timeout=300.0)
        row[side] = face(caps[0])
        print(f"  {side:7s} {label:11s} -> {row[side]!r}", flush=True)
        if os.environ.get("DEFFN_RAW"):
            print("      RAW " + repr(caps[0] or ""), flush=True)
    verdict(label, row)


def run_direct(label) -> None:
    """ROUND 5: commands typed at the PROMPT, never stored as a program.

    The row is exactly the DIRECT list plus each side's own reset; the last
    command is the CLS+PRINT so the fence sees the OUTPUT and not the echo of
    the typed text (round 3's eleven false agreements).
    """
    cmds = DIRECT[label]
    row = {}
    for side, cfg in SIDES.items():
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", list(cfg["reset"]) + list(cmds))],
            batch=False, boot=cfg["boot"], step=8.0, cap_gap=10.0, timeout=300.0)
        row[side] = face(caps[0])
        print(f"  {side:7s} {label:13s} -> {row[side]!r}", flush=True)
        if os.environ.get("DEFFN_RAW"):
            print("      RAW " + repr(caps[0] or ""), flush=True)
    verdict(label, row)


def verdict(label, row) -> None:
    """Score a row -- and REFUSE to score one that was never measured.

    🔴 A `<NO OUTPUT>` IS NOT A DIVERGENCE, IT IS A MISSING MEASUREMENT, and a
    readout that compares faces will happily call two of them equal. The ntwall
    scout lost two rows to exactly that in one session, so it is checked here
    rather than in the reader's head.
    """
    blank = [s for s, f in row.items() if f in ("<NO OUTPUT>", "<NO CAPTURE>")]
    if blank:
        print(f"  ROW {label:13s} NOT MEASURED  (blank on: {','.join(blank)})\n",
              flush=True)
        return
    if "vg8020" in row and "cf3300" in row:
        agree = "refs-agree" if row["vg8020"] == row["cf3300"] else "REFS DIFFER"
        zbm = ("zb=" + ("same" if row.get("zb") == row["vg8020"] else "DIFF")
               if "zb" in row else "zb=<not run>")
    else:
        agree, zbm = "one-ref-only", "no ref this round"
    print(f"  ROW {label:13s} {agree:12s} {zbm}\n", flush=True)


FENCE = re.compile(r"<([0-9A-Fa-f]{32})>")


def dump(cap):
    """Rows of hex, TRUNCATED at the end-of-program marker.

    🔴 THE UNTRUNCATED VERSION SCORED RAM GARBAGE AS A DIVERGENCE, and the proof
    is a control that changed verdict with its subject unchanged: `defusr.ctl`
    read BYTE-IDENTICAL on all three sides in round 1 and `REFS DIFFER` in
    round 3, on the same program. Nothing about DEF USR moved between those
    rounds -- what moved is that the dump began in direct mode, so the bytes
    AFTER the stored program (the direct-line buffer and uninitialised RAM)
    landed inside the compared window. A control that flips without its subject
    moving is a statement about the instrument.
    🎯 A stored MSX program ends at a line whose 2-byte LINK is $0000, so the
    program is everything up to and including the first `00 00` that follows a
    line's terminating `00`. Everything past it is not ours to compare.
    """
    if cap is None:
        return None
    txt = "".join(cap)
    rows = FENCE.findall(" ".join(txt.split()))
    if not rows:
        return None
    b = bytes.fromhex("".join(rows))
    end = len(b)
    i = 0
    while i + 1 < len(b):                       # walk the link chain
        link = b[i] | (b[i + 1] << 8)
        if link == 0:
            end = i + 2
            break
        nxt = i + (link - (b[0] | (b[1] << 8)) + 0)  # links are absolute
        # absolute links: convert by walking to the next 00-terminated line
        j = i + 4
        while j < len(b) and b[j] != 0:
            j += 1
        i = j + 1
    else:
        end = len(b)
    return [b[:end].hex().upper()]


def main() -> int:
    want = sys.argv[1:] or list(SUBJECTS) + list(BEHAV)
    if want == ["round5"]:
        want = list(ORDER) + list(DIRECT)
    if want == ["round10"]:
        want = ["z.addr", "z.addr2", "z.addr2i", "z.addr.ctl", "z.p10def", "o.ctl"]
    if want == ["round9"]:
        want = ["o.realcell", "o.realcell.ctl", "o.sameaddr", "o.dynaddr",
                "o.ctl2", "d.defusr", "d.let", "d.ctl"]
    if want == ["round8"]:
        want = ["o.varptr", "o.varptr.ctl", "o.dynself", "o.dynorder",
                "o.clearwipe3", "o.twocalls", "o.ctl",
                "d.sameline", "d.defonly", "d.def", "d.defrun", "d.ctl"]
    if want == ["round7"]:
        want = ["o.outerafter", "o.outerbefore", "o.outer.ctl", "o.outernoarg",
                "o.outerabs", "o.quotedcolon", "o.stmtcolon", "o.clearwipe2",
                "o.runtwice", "o.ctl", "d.deferr"]
    if want == ["round6"]:
        want = ["o.p9", "o.p10", "o.p11", "o.global", "o.dynscope", "o.clearwipe",
                "o.clearwipe.ctl", "o.namespace", "o.fnpct", "o.fnbang",
                "o.defintbang", "o.ctl", "d.deferr", "d.defrun", "d.ctl"]
    for label in want:
        if label in BEHAV or label in ORDER:
            run_behav(label)
            continue
        if label in DIRECT:
            run_direct(label)
            continue
        prog = SUBJECTS[label] + [DUMP_DIRECT]
        row = {}
        for side, cfg in SIDES.items():
            caps = omsx_repl.run_cases(
                cfg["machine"], [("direct", list(cfg["reset"]) + prog)],
                batch=False, boot=cfg["boot"], step=8.0, cap_gap=10.0, timeout=300.0)
            row[side] = dump(caps[0])
            print(f"  {side:7s} {label:12s} {row[side]}", flush=True)
            if os.environ.get("DEFFN_RAW"):
                print("      RAW " + repr((caps[0] or "")[-500:]), flush=True)
        if "vg8020" in row and "cf3300" in row:
            agree = "refs-agree" if row["vg8020"] == row["cf3300"] else "REFS DIFFER"
            zbm = ("zb=" + ("same" if row.get("zb") == row["vg8020"] else "DIFF")
                   if "zb" in row else "zb=<not run>")
        else:
            agree, zbm = "one-ref-only", "no ref this round"
        print(f"  ROW {label:12s} {agree:12s} {zbm}\n", flush=True)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
