#!/usr/bin/env python3

"""Float VARIABLES probe — characterise, then differentially prove, MSX-BASIC
TYPED numeric variables (Phase-3 float pack F3 S3a + S3b;
docs/spec-basic-float-core.md §11.1/§11.2/§11.4). S3b adds the DEF statements
(DEFINT/DEFSNG/DEFDBL/DEFSTR) at the end of the matrix: they set a letter's
default type, consulted at every unsuffixed reference (an explicit suffix still
wins), with an orphan-on-redeclare case and the DEFSTR-numeric Type mismatch.

Each case types one or more `:`-separated statements ending in
`PRINT"[";<vars>;"]"` (or, for the Type-mismatch cases, a bare assignment that
must abort before any PRINT runs) in direct mode and captures the SCREEN 0 name
table, mirroring basic_probe_float_arith.py's bracket technique. Two captures
per case:

- the bracket SPAN (text between the last '[' and the following ']') — the
  printed value(s), spaces exact; None if the ']' never printed (the
  statement aborted before reaching the PRINT);
- the screen TAIL (rows between the echoed command and the closing prompt) —
  pins whether an error message printed and the statement aborted.

The matrix covers: suffix type resolution (`%`/`!`/`#`/unsuffixed-default-
double), the alias case (`A`/`A%`/`A!`/`A#` as up to 4 independent entries),
int-store truncation, single-store 6-digit half-up rounding (incl. carry
renormalise), double-store exactness, cross-type numeric<->string Type
mismatch, round-trip reassignment, the FOR/NEXT unsuffixed-default-double
interaction (D-D: the loop stays int16), a VARPTR-distinctness check, and a
function-over-a-typed-variable case (HEX$ over a single) plus a deliberately
uncertain int-store-domain edge (A%=40000) — the F1/F2 review lesson is that a
matrix asserting only the happy path misses real bugs, so a couple of cases
here are run WITHOUT a pre-baked "expect" and are only resolved by actually
querying the reference.

Characterisation mode (default): print the reference's exact output per case,
plus a self-check against the spec-documented value where one is pinned.
Differential mode (--zb-machine): also run zerobas (repack build) and assert
span/tail equality (REF_MACHINE Philips_VG_8020 vs the repack disk machine).

Clean-room: observed outputs only; the reference ROM is a black box.
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))

import argparse

import omsx_repl  # typing-free KEYBUF-injection REPL driver (harness rework S1)

REF_MACHINE = "Philips_VG_8020"

# Each case: (label, line, kind, expect)
#   kind "value": a normal PRINT — compare the bracket SPAN only (mirrors the
#                 arith probe's "raw" kind: immune to echo-line wrapping).
#   kind "abort": the statement must abort BEFORE any PRINT runs — both sides
#                 must show NO span and a NON-EMPTY tail (an error printed).
#                 Wording is NOT compared (D-2 convention: zerobas's error
#                 text is its own lowercase wording, never the reference's
#                 verbatim string — see e.g. the string-acceptance range-error
#                 case, "Illegal function call" vs "syntax error", both
#                 accepted as long as the ABORT SHAPE matches).
#   expect: the spec-documented value for a characterisation self-check, or
#           None when the case is intentionally open (its whole point is to
#           discover the reference's actual behaviour rather than assert a
#           pre-baked guess — the "false-EXPECTED" review lesson).
CASES = [
    # --- suffix type resolution (§11.1) -------------------------------------
    # Numbers print sign-position (space or '-') + digits + ONE trailing space
    # (spec §9.3, formatter contract) -- confirmed live for the plain int path
    # too (int.trunc.exact below), so every numeric "value" expect carries
    # that same leading/trailing spacing; string-function results (HEX$ etc.,
    # further down) do NOT.
    ("suffix.pct",  'A%=5:PRINT"[";A%;"]"',                      "value", " 5 "),
    ("suffix.bang", 'A!=5:PRINT"[";A!;"]"',                      "value", " 5 "),
    ("suffix.hash", 'A#=5:PRINT"[";A#;"]"',                      "value", " 5 "),
    ("suffix.none", 'A=5:PRINT"[";A;"]"',                        "value", " 5 "),
    # unsuffixed default is DOUBLE, not single: 1/3 unsuffixed must print the
    # full 14-digit double form, identical to the explicit A# case.
    ("suffix.none.dbl", 'A=1/3:PRINT"[";A;"]"',                  "value", " .33333333333333 "),
    ("suffix.hash.dbl", 'A#=1/3:PRINT"[";A#;"]"',                "value", " .33333333333333 "),

    # --- alias case: A/A%/A!/A# up to 4 independent entries (§11.1) ---------
    ("alias.a_bang_hash",
     'A=1:A!=2:A#=3:PRINT"[";A;A!;A#;"]"',                       "value", " 3  2  3 "),
    ("alias.all4",
     'A=1:A%=2:A!=3:A#=4:PRINT"[";A;A%;A!;A#;"]"',                "value", " 4  2  3  4 "),

    # --- int-store: TRUNCATE toward zero (§11.2, same rule as \/MOD) --------
    ("int.trunc.pos", 'A%=1.7:PRINT"[";A%;"]"',                  "value", " 1 "),
    ("int.trunc.neg", 'A%=-1.7:PRINT"[";A%;"]"',                 "value", "-1 "),
    ("int.trunc.exact", 'A%=5:PRINT"[";A%;"]"',                  "value", " 5 "),
    # inclusive strict-int16 boundary (own hypothesis: variable store uses the
    # STRICT domain, -32768..32767, like \/MOD/logical operands, NOT the
    # address domain POKE/HEX$ use — see var_store_fac's header comment,
    # basic/vars.asm).
    ("int.trunc.bound.max", 'A%=32767.9:PRINT"[";A%;"]"',        "value", " 32767 "),
    ("int.trunc.bound.min", 'A%=-32768.9:PRINT"[";A%;"]"',       "value", "-32768 "),

    # --- single-store: ROUND to 6 sig digits, half-up, carry renorm (§11.2) -
    ("sng.round.carry",  'A!=1234567:PRINT"[";A!;"]"',           "value", " 1234570 "),
    ("sng.round.plain",  'A!=123456.7:PRINT"[";A!;"]"',          "value", " 123457 "),
    ("sng.round.third",  'A!=2/3:PRINT"[";A!;"]"',               "value", " .666667 "),
    ("sng.round.allnine", 'A!=1.9999999:PRINT"[";A!;"]"',        "value", " 2 "),

    # --- double-store: exact (14 sig digits) --------------------------------
    ("dbl.exact.third", 'A#=1/3:PRINT"[";A#;"]"',                "value", " .33333333333333 "),
    ("dbl.exact.int",   'A=1234567:PRINT"[";A;"]"',              "value", " 1234567 "),

    # --- cross-type numeric<->string: Type mismatch, statement aborts ------
    ("mismatch.numeric_eq_string", 'A%="X":PRINT"[";A%;"]"',     "abort", None),
    ("mismatch.string_eq_numeric", 'A$=5:PRINT"[";A$;"]"',       "abort", None),

    # --- round-trip via reassignment ----------------------------------------
    ("roundtrip.int",    'A%=5:A%=A%+1:PRINT"[";A%;"]"',         "value", " 6 "),
    ("roundtrip.single", 'A!=1:A!=A!*3:PRINT"[";A!;"]"',         "value", " 3 "),
    ("roundtrip.double", 'A#=1:A#=A#/3:PRINT"[";A#;"]"',         "value", " .33333333333333 "),

    # --- D-D: unsuffixed FOR/NEXT loop var now defaults to double, but the
    # loop math itself stays int16 (documented divergence). MUST run as a
    # STORED program + RUN, not typed direct-mode: a re-entrant NEXT resumes
    # via RESUMEFLAG/RESUMEPTR/CURLINE (program.asm), which only the run_prog
    # line-walking loop consults -- direct-mode dispatch (repl -> dispatch_line
    # -> exec) never checks them, so a direct-mode multi-pass FOR/NEXT silently
    # never reaches its own trailing statements. Confirmed pre-existing on the
    # LEAN (pre-F3, int-only) build too via the host harness -- an existing
    # interpreter scope limit, not an F3 regression -- so this one case is
    # marked "stored" to route through store_line+RUN instead of direct typing.
    ("fornext.default_double", 'FOR I=1 TO 3:NEXT:PRINT"[";I;"]"', "stored", " 4 "),

    # --- VARPTR distinctness: A%/A!/A# are 3 INDEPENDENT entries (A itself is
    # an ALIAS of A#, same entry -- confirmed live on the reference: VARPTR(A)
    # == VARPTR(A#) after `A#=...:A=...`, since the unsuffixed name resolves
    # to the SAME double slot -- so distinctness is only asserted pairwise
    # across %/!/#, never against the bare unsuffixed name). The ADDRESS
    # VALUES themselves are an own-design storage layout (never expected to
    # match the reference's), so only the DISTINCTNESS relation is asserted.
    # (kept short -- LINEBUF is 96 bytes; the earlier single AND-chained line
    # combining all three pairs ran past that and got silently truncated by
    # the keyboard-injection layer, a probe-harness bug in its own right)
    ("varptr.distinct.pct_bang",
     'A%=1:A!=2:PRINT"[";VARPTR(A%)<>VARPTR(A!);"]"',              "value", "-1 "),
    ("varptr.distinct.bang_hash",
     'A!=2:A#=3:PRINT"[";VARPTR(A!)<>VARPTR(A#);"]"',              "value", "-1 "),
    ("varptr.alias_a_eq_hash",
     'A#=3:A=4:PRINT"[";VARPTR(A)=VARPTR(A#);"]"',                 "value", "-1 "),

    # --- function-over-typed: a function argument that is a TYPED variable
    # (not a literal) — the F1/F2 review lesson generalised to F3: always
    # include a function-over-a-variable case, not just function-over-literal
    # (ev_f_var must set FAC/FACTYP/DE exactly like ev_f_float does). HEX$
    # returns a STRING (no number-format padding). ---------------------------
    ("func.hex_over_single", 'A!=2.9:PRINT"[";HEX$(A!);"]"',      "value", "2"),
    ("func.hex_over_double", 'A#=-2.5:PRINT"[";HEX$(A#);"]"',     "value", "FFFE"),

    # --- deliberately OPEN cases (no pre-baked "expect"): the review lesson
    # is that a matrix which only asserts the happy path misses real bugs, so
    # these are resolved by actually querying the reference rather than
    # guessing. int.store.overflow tests var_store_fac's own domain CHOICE
    # (strict vs address) at a value that only the strict domain rejects. ---
    ("int.store.overflow", 'A%=40000:PRINT"[";A%;"]"',            "abort_or_value", None),
    ("int.store.overflow.neg", 'A%=-40000:PRINT"[";A%;"]"',       "abort_or_value", None),

    # --- Fable adversarial-review regressions (three matrix-invisible bugs
    # found 2026-07-12; each case below FAILED before its fix) ---------------
    # Bug A (var_alloc_or_find zero-init used B=0 -> zeroed 256 bytes, ploughing
    # through STRTAB $E240 and wiping earlier string vars' name0). A numeric
    # allocation AFTER a string assignment must leave the string intact.
    ("reg.A.strtab_integrity", 'B$="HI":A=1:PRINT"[";B$;"]"',     "value", "HI"),
    # Bug B (ex_let read the GLOBAL (VARTYPE) after eval, but every RHS variable
    # factor re-runs var_name_key and overwrites it -> cross-type store used the
    # RHS's type, not the LHS's). All four pin the LHS-type latch.
    ("reg.B.crosstype_hash_to_pct", 'A#=2:A%=A#:PRINT"[";A%;"]"', "value", " 2 "),
    ("reg.B.crosstype_pct_in_expr", 'B%=5:A#=B%+1:PRINT"[";A#;"]"', "value", " 6 "),
    ("reg.B.crosstype_unset_pct",  'A!=B%:PRINT"[";A!;"]"',       "value", " 0 "),
    ("reg.B.crosstype_len_fn",     'B$="ABC":A%=LEN(B$):PRINT"[";A%;"]"', "value", " 3 "),
    # Bug C (tok_skip didn't stride the float literals $1D/$1F, so a mantissa
    # $00 byte was mistaken for the line/stmt terminator by skip_to_eol /
    # if_skip_to_else / data_seek). The PRIMARY repro is a STORED program with a
    # float literal (skip_to_eol measures the line at RUN time) -- "stored"
    # kind routes through store_line+RUN.
    ("reg.C.stored_float_literal", 'A=1.5:PRINT"[";A;"]"',        "stored", " 1.5 "),
    # Direct-mode proxy for the same stride via if_skip_to_else: the false IF
    # must skip PAST the THEN clause's `A=1.5` (a $1D literal with $00 mantissa
    # bytes) to reach ELSE -- exercises tok_skip identically without needing a
    # stored program.
    ("reg.C.if_skip_over_float", 'IF 0 THEN A=1.5 ELSE PRINT"[";9;"]"', "value", " 9 "),

    # === F3 S3b: DEFINT / DEFSNG / DEFDBL / DEFSTR (§11.1) ===================
    # DEF<type> sets the DEFAULT resolved type for an UNSUFFIXED name whose
    # first letter falls in the given range(s). Each of the four IS its own
    # single-byte statement token ($AB DEFSTR / $AC DEFINT / $AD DEFSNG /
    # $AE DEFDBL, whole-word kwtable.inc rows), so no mnemonic text reaches the
    # handler: ex_deftype (basic/usr.asm) serves all four dispatch rows and
    # fills a 26-byte per-letter DEFTBL (sysvars.inc) that var_name_key /
    # var_str_type consult at every reference.
    # ⚠️ NOT THE MECHANISM THESE CASES WERE WRITTEN AGAINST. When F3 S3b
    # shipped (2026-07-12) the mnemonics were NOT keyword tokens — only "DEF"
    # was — so all four arrived as DEF_TOKEN + plain upcased ASCII
    # ("INT"/"SNG"/"DBL"/"STR") and a mnemonic parser in the then-ex_def_type
    # read them back. D-DEFINTTOK (2026-08-18) and D-DEFTYPETOK (2026-08-19)
    # replaced that with the tokens above and DELETED the parser. The cases
    # below are unchanged and still pass: they gate the DEFTBL semantics, which
    # neither fix touched.
    # --- single-letter default override, one per type -----------------------
    ("def.int.basic",  'DEFINT A:A=1.9:PRINT"[";A;"]"',            "value", " 1 "),
    ("def.sng.basic",  'DEFSNG A:A=1/3:PRINT"[";A;"]"',            "value", " .333333 "),
    ("def.dbl.basic",  'DEFDBL A:A=1/3:PRINT"[";A;"]"',            "value", " .33333333333333 "),
    ("def.str.basic",  'DEFSTR S:S="HI":PRINT"[";S;"]"',           "value", "HI"),
    # --- letter RANGE: an in-range first letter takes the type; out-of-range
    # keeps the double default (the two spec §11.1 cases verbatim) ------------
    ("def.int.range.in",  'DEFINT A-C:B=1.9:PRINT"[";B;"]"',       "value", " 1 "),
    ("def.int.range.out", 'DEFINT A-C:D=1.9:PRINT"[";D;"]"',       "value", " 1.9 "),
    # --- comma-separated item list ------------------------------------------
    ("def.int.list", 'DEFINT A,C:A=1.9:C=2.9:PRINT"[";A;C;"]"',    "value", " 1  2 "),
    # --- an EXPLICIT suffix always beats the DEF default (A# stays double
    # even though DEFINT A made the unsuffixed A an int) ---------------------
    ("def.suffix_overrides", 'DEFINT A:A#=1.5:PRINT"[";A#;"]"',    "value", " 1.5 "),
    # --- a DEFSTR unsuffixed name IS the same variable as A$ (one STRTAB
    # slot, keyed (name,0)) --------------------------------------------------
    ("def.str.alias_dollar", 'DEFSTR S:S$="X":PRINT"[";S;"]"',     "value", "X"),
    # --- the table is consulted at EACH reference: redeclaring a letter's
    # type ORPHANS any value held under the old type (§11.1 verbatim) --------
    ("def.orphan", 'A=7:DEFINT A:PRINT"[";A;"]"',                  "value", " 0 "),
    # --- the LAST DEF for a letter wins -------------------------------------
    ("def.redeclare_wins", 'DEFINT A:DEFDBL A:A=1/3:PRINT"[";A;"]"', "value", " .33333333333333 "),
    # --- DEFSTR then a NUMERIC RHS on the unsuffixed name -> Type mismatch,
    # the assignment aborts before storing (D-2 abort shape) -----------------
    ("def.str.numeric_rhs", 'DEFSTR S:S=5:PRINT"[";S;"]"',         "abort", None),
    # --- a malformed DEF mnemonic is a syntax error (aborts) ----------------
    ("def.bad.mnemonic", 'DEFZ A:PRINT"[";1;"]"',                  "abort", None),

    # === S3b Fable-review regressions (found 2026-07-12; each FAILED pre-fix) =
    # R1 (HIGH): the single-letter FOR/NEXT + READ shims (var_get/var_set)
    # hardcoded type-8, but S3b made unsuffixed references resolve via the
    # DEFtbl -- so a DEFINT loop/READ variable was STORED as double yet READ
    # BACK as int (a never-written int entry) = 0. Fixed by routing the shims
    # through deftbl_lookup so the stored and referenced types agree. STORED
    # (RUN) so the re-entrant NEXT resumes (see fornext.default_double).
    ("reg.S3b.fornext_defint",
     'DEFINT I:FOR I=1 TO 3:NEXT:PRINT"[";I;"]"',                 "stored", " 4 "),
    ("reg.S3b.fornext_defint_sum",
     'DEFINT I:A%=0:FOR I=1 TO 3:A%=A%+I:NEXT:PRINT"[";A%;"]"',   "stored", " 6 "),
    ("reg.S3b.read_defint",
     'DEFINT X:READ X:PRINT"[";X;"]":DATA 42',                    "stored", " 42 "),
    # R2 (robustness): var_str_type is now letter-keyed for the DEFtbl default;
    # ex_mid_stmt calls it on the RAW target, so a non-letter target (a MID$
    # string LITERAL) must reach a deterministic error, not a wild out-of-range
    # DEFtbl read -- guarded with is_letter.
    ("reg.S3b.mid_literal_target", 'MID$("AB",1)="X"',            "abort", None),

    # === D-DEFSTR: a DEFSTR'd UNSUFFIXED name in a NUMERIC position ===========
    # docs/spec-basic-deftbl-strcode.md. The DEFtbl's string code (namespace P,
    # sysvars.inc DEFTBL_STR) used to be 1, which is ALSO the variable chain's
    # own string type tag (namespace C) -- so three sites that fed a P code into
    # a C position were invisible. Both references answer every row below with
    # Type mismatch; these are the rows that said so.
    # ⚠️ ORACLE-LOCKED ON BOTH REFERENCES BEFORE zerobas ran on them, at
    # --repeat 2, and vg8020 and cf3300 agreed on all 18 rows of the scout (spec
    # §3). This probe's standing differential is vg8020-vs-zerobas, as the whole
    # matrix is; the CF-3300 half lives in the spec, not here.
    #
    # 🔴 THE TOP-LEVEL ROW IS GREEN AND WAS GREEN FOR THE WRONG REASON. `B=S` is
    # intercepted by ev_rel's own str_eval probe, which sits at the TOP of an
    # operand only -- so it never exercised ev_f_var at all. `B=1+S`, one `1+`
    # away, reached ev_f_var and silently read 0. Keep BOTH: the pair is what
    # tells the interception apart from the guard, and either alone misleads.
    ("def.str.rvalue",      'DEFSTR S:B=S:PRINT"[";B;"]"',          "abort", None),
    ("def.str.rvalue_arr",  'DEFSTR S:B=S(1):PRINT"[";B;"]"',       "abort", None),
    ("def.str.nested",      'DEFSTR S:B=1+S:PRINT"[";B;"]"',        "abort", None),
    ("def.str.nested_set",  'DEFSTR S:S="AB":B=1+S:PRINT"[";B;"]"', "abort", None),
    ("def.str.nested_arr",  'DEFSTR S:B=1+S(1):PRINT"[";B;"]"',     "abort", None),
    # The numeric CONTROLS: identical but for the DEF mnemonic, so the DEFtbl
    # byte is the only moving part. A fix that made everything abort would pass
    # every row above and fail these.
    ("def.int.nested",      'DEFINT S:B=1+S:PRINT"[";B;"]"',        "value", " 1 "),
    ("def.int.rvalue_arr",  'DEFINT S:B=S(1):PRINT"[";B;"]"',       "value", " 0 "),
    # 🔴 THE ROW THAT CATCHES A FIX AIMED AT THE NUMERIC LEAK BREAKING DEFSTR
    # ITSELF: a DEFSTR'd name used as the STRING it is must keep working.
    ("def.str.arr_store", 'DEFSTR S:S(1)="AB":PRINT"[";S(1);"]"',   "value", "AB"),
    # var_get/var_set: the pair that had NO string guard and so corrupted memory
    # (spec §3.2 -- one byte of FAC over a string descriptor's `len`, after which
    # PRINT dumped RAM). Stored, because NEXT is re-entrant.
    ("def.str.fornext",
     'DEFSTR I:FOR I=1 TO 3:NEXT:PRINT"[";I;"]"',           "stored_abort", None),
]

# ⚠️ NOT GATED, AND DELIBERATELY: `DEFSTR X:READ X:...:DATA 42` reads the STRING
# "42" on both references (`[42]`, no spaces -- the missing spaces ARE the tell)
# and `DATA AB` reads `[AB]`. zerobas has no string READ at all, so after
# D-DEFSTR both raise a clean ERR 13 instead of corrupting memory: strictly
# closer, still divergent. A row that can only ever be red is doc debt, not a
# gate -- it is filed in TODO.md instead. Recorded here so the omission is a
# decision on the record rather than a silent gap in this matrix.


def _is_type_mismatch(tail):
    """Is this tail a TYPE MISMATCH report? Matched on the lowercase STEM only:
    zerobas prints its own lowercase wording by design (D-2) and the reference
    appends a run-mode ` in 10` suffix, so neither the case nor the suffix is
    compared -- exactly the rule basic_probe_sysvarsweep.py's own `_has_error`
    uses for "Undefined line number". This is a shape test that a line of dumped RAM
    cannot satisfy, which is the whole point (see `stored_abort` in compare)."""
    return bool(tail) and "type mismatch" in tail.lower()


def spec_for(line, kind):
    """The (mode, lines) delivery spec for one case, plus a `stored` flag.

    Routing (unchanged from the boot-per-case capture it replaces):
      - "stored": run as a stored program (as_stored splits the :-joined body
        into <=39-char numbered lines) -- for a re-entrant NEXT whose resume
        only the run_prog line loop honours (RESUMEFLAG/RESUMEPTR/CURLINE).
      - "value": direct mode -- EXCEPT a value line past the KEYBUF direct cap
        (omsx_repl.MAX_DIRECT = 38: def.int.list, alias.all4, the 3 varptr.*
        cases) is run as a stored program, semantically identical for those (no
        re-entrant control flow).
      - "stored_abort": a stored program that must abort before printing (a
        re-entrant construct whose TYPE is rejected, e.g. a DEFSTR'd FOR).
      - "abort"/"abort_or_value": direct mode."""
    stored = (kind in ("stored", "stored_abort")
              or (kind == "value" and len(line) > omsx_repl.MAX_DIRECT))
    return (("stored", omsx_repl.as_stored(line)) if stored
            else ("direct", [line])), stored


def extract(raw, line, kind, stored):
    """(span, tail) from one raw capture, matching spec_for's routing. A stored
    case anchors on its own `RUN` echo; a direct abort case reads its span only
    AFTER the echo row so the echoed '[' is not misread as output.

    🔴 A STORED ROW USED TO BE READ WITH A BARE result_span, AND THAT CANNOT SEE
    AN ABORT. The screen still holds the echo of `20 PRINT"[";I;"]"`, so when RUN
    prints nothing the span silently falls back to the echoed literal — D-DEFSTR
    measured `'";I;"'` and `'42'` that way, both of which are the SOURCE line and
    both of which look like plausible values. Anchoring after the `RUN` echo
    makes "the program printed nothing" a reading instead of a fabrication, and
    gives stored rows a real tail (so `stored_abort`, below, can exist at all).
    Rows that DO print are unaffected: their output is after RUN either way."""
    if stored:
        return (omsx_repl.result_span_after_echo(raw, "RUN"),
                omsx_repl.screen_tail(raw, "RUN"))
    if kind == "value":
        return omsx_repl.result_span(raw), omsx_repl.screen_tail(raw, line)
    return omsx_repl.result_span_after_echo(raw, line), omsx_repl.screen_tail(raw, line)


# Full-run case count, asserted in main(). See the guard there.
EXPECT_CASES = 65


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE,
                    help=f"reference oracle machine (default {REF_MACHINE})")
    ap.add_argument("--zb-machine", dest="zb_machine",
                    help="differential mode: also run this repack machine and "
                         "assert span/tail equality")
    ap.add_argument("--only", help="substring filter on the case label")
    ap.add_argument("--boot-per-case", dest="boot_per_case", action="store_true",
                    help="isolate each case in its own boot (slow) instead of the "
                         "default single-boot batch")
    args = ap.parse_args()

    cases = [c for c in CASES if not (args.only and args.only not in c[0])]
    # These cases ASSIGN typed variables and set DEF-table defaults, so the
    # inter-case reset must clear both -- NEW resets variables + DEFtbl (fixed
    # 2026-07-12 5cde8a8, proven by basic_probe_var_reset), CLS clears the
    # screen. run_differential re-runs any disagreeing case boot-per-case, so a
    # leak the reset somehow missed can only ever slow the run, never mis-pass.
    specs, stored = zip(*(spec_for(line, kind) for _, line, kind, _ in cases))
    specs = list(specs)

    # Characterisation mode: reference only, no differential -> plain batch.
    if not args.zb_machine:
        raws = omsx_repl.run_cases(args.machine, specs,
                                   batch=not args.boot_per_case, reset=("NEW", "CLS"))
        for (label, line, kind, expect), raw, st in zip(cases, raws, stored):
            ref_span, ref_tail = extract(raw, line, kind, st)
            rs = f"[{ref_span}]" if ref_span is not None else "<no span>"
            note = ""
            if expect is not None:
                note = f"   expect {expect!r} -> " \
                       f"{'OK' if ref_span == expect else 'MISMATCH vs spec!'}"
            elif ref_span is None:
                note = f"   tail: {ref_tail!r}"
            print(f"{label:<24} {rs}{note}")
        return 0

    def compare(i, ref_raw, zb_raw):
        _, line, kind, _ = cases[i]
        ref_span, ref_tail = extract(ref_raw, line, kind, stored[i])
        zb_span, zb_tail = extract(zb_raw, line, kind, stored[i])
        if kind in ("value", "stored"):
            return ref_span is not None and ref_span == zb_span
        if kind == "stored_abort":
            # 🔴 "NO SPAN + A NON-EMPTY TAIL" IS VACUOUS FOR THIS ROW, AND THE
            # PRE-FIX BUILD PROVES IT. The memory corruption def.str.fornext
            # exists to catch ALSO produced no span and a non-empty tail -- the
            # tail was a line of dumped RAM (`#   $  4$ ! s$ '  9   N X]`), which
            # is indistinguishable from an error message under a mere bool()
            # test. So the row would have passed on the broken build: green while
            # measuring nothing. Require the abort to be a TYPE MISMATCH.
            return (ref_span is None and zb_span is None
                    and _is_type_mismatch(ref_tail) and _is_type_mismatch(zb_tail))
        if kind == "abort":
            return (ref_span is None and zb_span is None
                    and bool(ref_tail) and bool(zb_tail))
        # "abort_or_value": accept whichever shape the REFERENCE took, as long as
        # zerobas took the SAME shape (value vs abort) and, if a value, the value.
        if ref_span is None:
            return zb_span is None and bool(ref_tail) and bool(zb_tail)
        return zb_span is not None and ref_span == zb_span

    verdicts, ref_raws, zb_raws = omsx_repl.run_differential(
        args.machine, args.zb_machine, specs, compare,
        batch=not args.boot_per_case, reset=("NEW", "CLS"))

    ok = True
    for (label, line, kind, expect), good, ref_raw, zb_raw, st in zip(
            cases, verdicts, ref_raws, zb_raws, stored):
        ok = ok and good
        ref_span, _ = extract(ref_raw, line, kind, st)
        rs = f"[{ref_span}]" if ref_span is not None else "<no span>"
        print(f"{'PASS' if good else 'FAIL'}  {label:<24} ref: {rs}")
        if not good:
            zb_span, zb_tail = extract(zb_raw, line, kind, st)
            zs = f"[{zb_span}]" if zb_span is not None else "<no span>"
            _, ref_tail = extract(ref_raw, line, kind, st)
            print(f"{'':>32}ref tail: {ref_tail!r}")
            print(f"{'':>32}zb  span: {zs}  tail: {zb_tail!r}")

    if args.zb_machine:
        # 🔴 NAME THE DENOMINATOR, AND FLOOR IT (2026-09-05, TODO "float-acceptance
        # has no named expected-failure mechanism"). "ALL PASS" over a matrix that
        # silently SHRANK reads exactly like "ALL PASS" over the whole one -- the
        # 0/0-ALL-CONVERGED shape. `--only` legitimately narrows a run, so the pin
        # applies to a FULL run only.
        # 🔴 …AND AN EMPTY SELECTION IS THE SAME HOLE FROM THE OTHER SIDE.
        # Printing the count above exposed it immediately: `--only` with a
        # filter that matches nothing printed `ALL PASS (0 cases)` and exited
        # 0. A run that measured nothing must never read as a green one.
        if args.only and not cases:
            print(f"\n🔴 INSTRUMENT FAULT: --only {args.only!r} selected "
                  f"NO cases. An empty selection would print ALL PASS and "
                  f"exit 0 -- the 0/0-ALL-CONVERGED shape. Check the filter.")
            return 2
        if not args.only and len(cases) != EXPECT_CASES:
            print(f"\n🔴 INSTRUMENT FAULT: a full run built {len(cases)} case(s); "
                  f"this suite is pinned at {EXPECT_CASES}. Bump EXPECT_CASES in the "
                  f"same commit that changes the matrix -- never to make a run go "
                  f"green.")
            return 2
        print(f"\nALL PASS ({len(cases)} cases) — float variables (F3 S3a) reference-identical" if ok
              else "\nSOME FAILED")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
