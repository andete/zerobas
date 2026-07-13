#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Math pack slice 1a+1b probe — ABS/SGN/INT/FIX/CINT/CSNG/CDBL/SQR
(docs/spec-basic-math-pack.md §9.4/§10.6).

SQR (slice 1b, §10.3.1/§10.6 FINAL, REVISED 2026-07-13): correctly-rounded
Heron+Newton over our OWN fp_div/fp_mul/fp_sub/fp_add (sub/fp_sqrt.asm --
migrated to the sub-ROM page-1 tenant 2026-07-13, docs/spec-basic-subrom-
mathpack.md; algorithm unchanged, only its home moved) -- intentionally NOT
a bit-exact fit of the reference. A time-boxed
black-box campaign proved the reference's own division is low-biased by 1
ulp in a way that is not clean-room recoverable (the distinguishing rule
lives in the 15th digit of an intermediate remainder, which 14-digit PRINT
structurally hides). Decision: keep our correctly-rounded div (more
accurate) and ship SQR correctly-rounded too, so it is always >= as accurate
as the reference. The SQR value oracle below is therefore MATHEMATICAL TRUTH
(host `Decimal`, correctly-rounded 14 significant digits), not the
reference -- this is what actually guarantees "correctly-rounded" (a narrow
reference-matching battery could hide a boundary the correction still
misses). The reference ROM's own ~1-ulp-off-truth cases are captured
separately as an INFORMATIONAL deviation report (never asserted against).

Two independent checks, both against the Philips VG-8020 black-box oracle:

1. TOKEN capture (reference-only, always run): each keyword is crunched as a
   stored line (`1 a=<call>`) and its $FF-suffix byte read back from TXTTAB,
   the same "stored_line" technique basic_probe_str_tokens.py uses for the
   string-engine keywords. Confirms the sysvars.inc equates (ABS_TOKEN=$86,
   SGN_TOKEN=$84, INT_TOKEN=$85, FIX_TOKEN=$A1, CINT_TOKEN=$9E, CSNG_TOKEN=$9F,
   CDBL_TOKEN=$A0 — MSX2 TH Table 2.20 targets) against the real crunch. If a
   capture disagrees with the target, the CAPTURE wins (project rule) — this
   check exists to catch exactly that.

2. VALUE differential: each case types `PRINT "[";<expr>;"]"` (or a `:`-joined
   RAW line for a stateful case) and captures the SCREEN 0 bracket span + the
   tail (same technique as basic_probe_float_arith.py). Characterisation mode
   (default) prints the reference's exact output; --zb-machine also runs
   zerobas (repack build) and asserts equality -- EXCEPT every pure `sqr(x)`
   call (SQR_BROAD_XS, ~100 inputs: the 72-input characterization battery +
   ~30 fresh draws spanning every magnitude/decimal shape), which asserts
   zerobas == truth_sqrt14(x) instead of zerobas == reference.

The matrix deliberately includes every trap the spec calls out as
matrix-invisible: INT vs FIX on negatives, CINT rounding direction + the
domain-overflow edges (both boundaries), FACTYP-leak (function-over-float,
function-over-PEEK, a typed-var store from CINT), and the ABS(-32768%)
int-domain escape (spec §9.1 / float-core §10.4's -32768\\-1 quirk).

Clean-room: observed outputs only; the reference ROM is a black box.
"""
from __future__ import annotations

import os as _os
import sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _HERE)
_sys.path.insert(0, _os.path.join(_os.path.dirname(_HERE), "lib"))

import argparse
import decimal
import re

import basic_probe_crunch as C  # noqa: E402  (reuse MACHINE/TXTTAB/tokens)
import omsx_repl                # noqa: E402  (typing-free KEYBUF REPL driver)

D = decimal.Decimal


def truth_sqrt14(x) -> "decimal.Decimal":
    """Host-computed, correctly-rounded 14-significant-digit sqrt(x)
    (docs/spec-basic-math-pack.md §10.3.1/§10.6 FINAL: the SQR oracle is
    mathematical truth, not the reference ROM). Decimal, prec>=30 internally,
    ROUND_HALF_UP to 14 significant digits -- the same rounding rule as
    round_and_finalize's own guard-digit half-up (basic/float-arith.asm)."""
    x = D(x)
    if x == 0:
        return D(0)
    with decimal.localcontext() as ctx:
        ctx.prec = 40
        root = x.sqrt()
    digits = root.as_tuple().digits
    exp = root.as_tuple().exponent
    if len(digits) <= 14:
        return root
    quant_exp = exp + (len(digits) - 14)
    quantum = D(1).scaleb(quant_exp)
    with decimal.localcontext() as ctx:
        ctx.prec = 40
        ctx.rounding = decimal.ROUND_HALF_UP
        return root.quantize(quantum)


# --- ATN truth oracle (math pack slice 2a, docs/spec-basic-mathpack-slice2.md
# §11.7): the SAME "the oracle is mathematical truth, not the reference"
# framework as SQR's truth_sqrt14 above. Python's `decimal` has no native
# atan, so this is our OWN independent-precision (50+ working digits, far
# above zerobas's 14) reference implementation -- sign-fold + reciprocal
# reduction (x>1) + repeated half-angle reduction + a Taylor series. This is
# NOT zerobas's own algorithm (different reduction depth, different series
# length, Python Decimal vs Z80 BCD) -- an independent computation used only
# as the host truth oracle for the gate.
_PI60 = D("3.14159265358979323846264338327950288419716939937510582097494")


def _atan_dec(x: "decimal.Decimal", prec: int = 50) -> "decimal.Decimal":
    with decimal.localcontext() as ctx:
        ctx.prec = prec + 15
        x = D(x)
        if x == 0:
            return D(0)
        sign = 1
        if x < 0:
            sign, x = -1, -x
        big = x > 1
        if big:
            x = 1 / x
        halvings = 0
        while x > D("0.01"):
            x = x / (1 + (1 + x * x).sqrt())
            halvings += 1
        x2 = x * x
        term = x
        total = x
        k = 1
        while True:
            term *= -x2
            add = term / (2 * k + 1)
            total += add
            if abs(add) < D(1).scaleb(-(prec + 10)):
                break
            k += 1
        total *= D(2) ** halvings
        if big:
            total = _PI60 / 2 - total
        return -total if sign < 0 else total


def truth_atan14(x) -> "decimal.Decimal":
    """Host-computed, correctly-rounded 14-significant-digit atan(x)
    (docs/spec-basic-mathpack-slice2.md §11.7: mathematical truth, not the
    reference ROM -- same framework as SQR's truth_sqrt14)."""
    x = D(x)
    if x == 0:
        return D(0)
    with decimal.localcontext() as ctx:
        ctx.prec = 60
        root = _atan_dec(x, prec=50)
    digits = root.as_tuple().digits
    exp = root.as_tuple().exponent
    if len(digits) <= 14:
        return root
    quant_exp = exp + (len(digits) - 14)
    quantum = D(1).scaleb(quant_exp)
    with decimal.localcontext() as ctx:
        ctx.prec = 60
        ctx.rounding = decimal.ROUND_HALF_UP
        return root.quantize(quantum)


# ATN documented-deviation bound (§11.7 REVISED, user sign-off 2026-07-13):
# ATN is NOT strictly correctly-rounded -- its 14-digit reduction+16-step
# Horner+reconstruction chain accumulates rounding to ~2 ulp (reaching truly
# correctly-rounded needs 3 internal guard digits, i.e. an extended-precision
# layer the resident 14-digit BCD primitives don't provide -- the same
# clean-room wall as the division deviation and the SQR precision floor). The
# user chose DOCUMENTED BOUNDED DEVIATION over building that layer: ATN is the
# ONLY slice-2 function whose reference is accurate enough (~correctly-rounded)
# for our chain to lose; the other five (LOG/SIN/TAN/EXP/COS) beat the 4-20+ ulp
# reference trivially at 14 digits. So the gate asserts a BOUND vs mathematical
# truth (<= the reference's OWN worst envelope), not == truth and not the
# strict never-worse-than-reference invariant (relaxed per §2 resolution).
ATN_MAX_ULP = 2
# Battery-wide correctly-rounded floor (drift tripwire, Fable review finding #2):
# fail if fewer than this many pure-atn inputs are exactly == truth, catching a
# uniform 1-2-ulp degradation that the per-input <=2-ulp bound would miss.
# Current is 44/61 correctly-rounded; 40 leaves benign-shift margin.
ATN_EXACT_FLOOR = 40


def ulp_dist(val, truth) -> "decimal.Decimal | None":
    """Distance |val - truth| in units of the 14th significant digit of truth."""
    if val is None or truth is None:
        return None
    if truth == 0:
        return abs(val)            # atan(0)=0 exact path; any nonzero is a gross fail
    scale = D(10) ** (truth.adjusted() - 13)
    return (abs(val - truth) / scale)


_NUM_RE = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)([eEdD][+-]?\d+)?")


def parse_basic_number(span: "str | None"):
    """Parse a captured PRINT bracket span (e.g. ' 3.7416573867739 ' or
    ' 1E+15 ') into a Decimal, comparing by VALUE rather than by exact
    printed string -- avoids needing to reimplement flt_out's own fixed-vs-E
    notation/trailing-zero-stripping rules just to check a numeric result.
    Returns None if the span isn't a bare number (e.g. an error message)."""
    if span is None:
        return None
    s = span.strip().replace("D", "E").replace("d", "e")
    m = _NUM_RE.fullmatch(s)
    if not m:
        return None
    try:
        return D(s)
    except decimal.InvalidOperation:
        return None

REF_MACHINE = "Philips_VG_8020"

# --- 1. token capture (reference-only sanity check) -------------------------
# (keyword, a stored-line body that crunches it, expected $FF-suffix byte).
# Targets: MSX2 TH Table 2.20 (docs/spec-basic-math-pack.md §6/§9.3), the SAME
# equate values basic/sysvars.inc defines (ABS_TOKEN etc.).
TOKENS = [
    ("ABS",  "a=abs(1)",  0x86),
    ("SGN",  "a=sgn(1)",  0x84),
    ("INT",  "a=int(1)",  0x85),
    ("FIX",  "a=fix(1)",  0xA1),
    ("CINT", "a=cint(1)", 0x9E),
    ("CSNG", "a=csng(1)", 0x9F),
    ("CDBL", "a=cdbl(1)", 0xA0),
    ("SQR",  "a=sqr(1)",  0x87),
    ("ATN",  "a=atn(1)",  0x8E),
]


def check_tokens(machine: str) -> bool:
    specs = [("direct", [f"1 {body}"]) for _, body, _ in TOKENS]
    raws = omsx_repl.run_cases(machine, specs, batch=True, reset=("NEW",),
                               capture=("stored_line", C.TXTTAB))
    ok = True
    print("--- token capture (VG-8020 crunch vs MSX2 TH Table 2.20) ---")
    for (name, body, want), raw in zip(TOKENS, raws):
        ref = C.tokens(raw)
        got = None
        if ref and 0xFF in ref:
            i = ref.index(0xFF)
            got = ref[i + 1] if i + 1 < len(ref) else None
        good = got == want
        ok = ok and good
        s = " ".join(f"{b:02X}" for b in ref) if ref else "<not stored>"
        tag = "OK" if good else f"FAIL want FF {want:02X}"
        print(f"{tag:14} {name:5} {body:12} -> {s}")
    print("token capture: ALL OK" if ok else "token capture: MISMATCH")
    return ok


# --- 2. value matrix ---------------------------------------------------------
# Grouped by the contract facet it pins (spec §9.1/§9.2/§9.4).
EXPRS = [
    # --- ABS: |x|, same FACTYP as x; -32768 int-domain escape is a RAW case
    # below (needs a typed-var store to reach an actual int16 -32768).
    "abs(-1.5)", "abs(1.5)", "abs(-1.5#)", "abs(1.5!)", "abs(0)", "abs(-0.0)",
    "abs(-32767)", "abs(32767)",
    # --- SGN: -1/0/+1, always int (FACTYP-leak: +0.5 must promote to float) -
    "sgn(2.5)", "sgn(-2.5)", "sgn(0)", "sgn(0.0)", "sgn(5)", "sgn(-5)",
    "sgn(2.5)+0.5", "sgn(-1)+sgn(1)",
    # --- INT: floor toward -infinity, same FACTYP as x --------------------
    "int(-1.5)", "int(1.9)", "int(-1)", "int(0)", "int(-0.5)", "int(1e9)",
    "int(123456.789)", "int(2.5)", "int(-2.5)", "int(-1.9)",
    # --- FIX: truncate toward 0, same FACTYP as x (differs from INT only on
    # a negative non-integer) ------------------------------------------------
    "fix(-1.5)", "fix(1.9)", "fix(-1)", "fix(0)", "fix(-1e9)", "fix(-0.5)",
    "fix(2.5)", "fix(-2.5)", "fix(-1.9)",
    # --- INT/FIX cross-check: identical for x>=0 or integral x, INT=FIX-1
    # for a negative non-integer -------------------------------------------
    "int(-1.5)-fix(-1.5)", "int(1.5)-fix(1.5)", "int(-2)-fix(-2)",
    # --- INT/FIX result-TYPE preservation over DOUBLE operands (review F2,
    # 2026-07-12). The negative-non-integer cases above all crunch to SINGLE
    # literals, so the evmc_sub1 DOUBLE branch and the single re-narrow were
    # never distinguished, and the result FACTYP was observationally invisible
    # (a wrong narrow-to-single reprints as E-notation / 6 digits). These
    # DOUBLE operands with >6 integer digits make the result type observable:
    # a mis-narrowed 12345678 would print 1.23457E+07. Oracle-confirmed values
    # (this probe's triage capture): 12345678, -10000000, -12345679, -1, -3.
    "int(12345678.9#)", "int(-9999999.5#)", "int(-12345678.9#)",
    "fix(12345678.9#)", "fix(-12345678.9#)",
    "int(-2.5#)", "fix(-2.5#)",
    # --- CINT: int16 conversion, domain -32768..32767 else Overflow. --------
    # ORACLE CORRECTION (this probe, 2026-07-12): CINT does NOT round -- it
    # TRUNCATES toward 0, identical to the strict \\/MOD/AND/OR/XOR/NOT
    # domain conversion (float-core §10.3). cint(2.9)=2, cint(1.5000001#)=1,
    # cint(32767.6)=32767 (IN range, not Overflow) all confirm truncation;
    # the spec's "rounds (half-up)" text was an unverified assumption -- this
    # matrix pins the corrected (truncating) contract and the true Overflow
    # boundary (the INTEGER part itself must exceed the domain).
    "cint(2.5)", "cint(-2.5)", "cint(0.5)", "cint(-0.5)", "cint(3.7)",
    "cint(-3.7)", "cint(2.1)", "cint(2.9)", "cint(-2.1)", "cint(-2.9)",
    "cint(32767.4)", "cint(-32768.4)", "cint(32767.6)", "cint(-32768.6)",
    "cint(32767.999999#)", "cint(-32768.999999#)",
    "cint(32768)",          # -> Overflow (SPAN_ONLY): integer part alone out
    "cint(-32769)",         # -> Overflow (SPAN_ONLY)
    "cint(40000.5)",        # -> Overflow (SPAN_ONLY): truncated value still >32767
    "cint(32768.1)",        # -> Overflow (SPAN_ONLY)
    # --- CSNG: narrow to single (round half-up) ----------------------------
    "csng(1.2345678#)", "csng(2/3)", "csng(5)", "csng(-1.9999999#)",
    # --- CDBL: widen to double (exact) --------------------------------------
    "cdbl(1.5!)", "cdbl(5)", "cdbl(1.1)", "cdbl(-3)",
    # --- function-over-PEEK (a DIFFERENT $FF chain feeding FACTYP=2 into
    # ours -- the F1 review's standing "function-over-float/int" lesson) ----
    "abs(peek(0))", "sgn(peek(0))", "int(peek(0)+.5)", "cint(peek(0))",
    # --- nested / composed calls (ARGA/ARGB reuse across calls) ------------
    "abs(int(-1.5))", "int(-1.5)+int(-2.5)", "cint(abs(-2.5))",
    # --- SQR: FACTYP-leak (function-over-float; result must stay DOUBLE, --
    # per §10.2 -- an int/single leak would reprint 4+.5 as an int add or
    # round 6.25's sqrt to 6 sig digits) + single-vs-double literal input --
    # (6.25 -> 2.5 exactly, an EXACT perfect square so reference-identical
    # regardless of the truth-vs-reference SQR split below; this pins the
    # widen path, not correctness). Still reference-compared (kept OUT of
    # SQR_BROAD_XS below, which drives the truth assertion): these test the
    # dispatch/store plumbing around SQR, not SQR's own rounding.
    "sqr(4)+0.5", "sqr(6.25!)", "sqr(6.25#)",
    # --- SQR: domain error, x<0 -> "illegal function call" (own lowercase --
    # wording, D-F2-1 disposition idiom; TAIL differs from the reference's
    # verbatim "Illegal function call", so these are SPAN_ONLY below, same
    # shape as the CINT Overflow cases).
    "sqr(-1)", "sqr(-1e-9)", "sqr(-4)",
]

# --- SQR value battery (§10.3.1/§10.6 FINAL): the oracle is MATHEMATICAL
# TRUTH, not the reference ROM (a plain Heron fixed-point over our correctly-
# rounded fp_div is NOT bit-exact with the reference's own low-biased
# division -- §10.3.1's black-box campaign proved that divergence is not
# clean-room recoverable). Every value here is a PURE `sqr(x)` call (matched
# by the regex in compare(), below) so its assertion routes to
# truth_sqrt14(x), never to the reference span -- this is what actually
# guarantees "correctly-rounded": a narrow battery could miss a boundary a
# fitted correction still misses. The 72 entries are this slice's own black-
# box characterization campaign (VG-8020, 2026-07-12/13, the same battery
# `sqr_bulkfit.py`/`sqr_oracle.json` captured); the rest are fresh draws
# added for this broad-battery requirement (mixed magnitude, sub-1, large,
# non-square integers, decimals, incl. near-perfect-square boundary stress
# like 11833599.999919 -- found live to matter: the Newton step alone can
# land exactly 1 ulp off truth at these boundaries, which the final decision
# step (sub/fp_sqrt.asm fsq_stop) exists specifically to correct).
SQR_BROAD_XS = [
    # --- the 72-input characterization battery -----------------------------
    "2", "3", "5", "6", "7", "8", "10", "11", "12", "13", "14", "15", "17",
    "18", "19", "20", "21", "22", "23", "24", "26", "27", "28", "29", "30",
    "31", "33", "37", "41", "43", "47", "50", "53", "59", "61", "67", "71",
    "73", "79", "83", "89", "97", "99", "101", "999",
    "4", "9", "16", "25", "36", "49", "64", "81", "100", "10000",
    ".25", ".04", ".01", "2.25", "6.25", ".5", "1.5", "2.5", "3.7",
    "123.456", ".1", ".001", "12345.6789",
    "1.0000000000001", "99.999999999999", "0.99999999999999",
    "1.23456789012345",
    # --- ~30 fresh draws: broader magnitude/decimal-shape coverage ---------
    "0", "1", "8", "42", "1000001", "88888888888888", "19999999999999",
    "1.999999999999", "2.000000000001", "1.41421356237", "7.5", ".0009",
    "55555.55555", "333333333.3333", "9.87654321098", "1234567.891234",
    "3.14159265358", "2.71828182845", "1e-20", "1e15", "1e-30", "1e10",
    "1e30", "4e10", "31622.7766017", "0.30102999566398", "123456789.12345",
    "7.389056098931", "2.71828182846e10", "4.44444444444",
    "11833599.999919",
    "99.99998",   # KNOWN PRECISION FLOOR -- see SQR_KNOWN_FLOOR below
]
EXPRS = EXPRS + [f"sqr({_x})" for _x in SQR_BROAD_XS]

# --- ATN value battery (math pack slice 2a, §11.7): the oracle is MATHEMATICAL
# TRUTH (truth_atan14 above), same "the oracle is truth" framework as SQR --
# every entry is a PURE `atn(x)` call (matched by _ATN_PURE_RE below) so its
# assertion routes to truth_atan14(x), never to the reference span. ATN is
# already ~correctly-rounded on the reference (§1.1: 15/20 exact, worst 2 ulp
# -- the best-behaved transcendental), so this battery is a broader stress
# test than the characterization campaign, deliberately covering: near-
# BREAK=2-sqrt(3)~=0.26794919243112 from both sides (where reduction-2
# switches on), near a=1 from both sides (where reduction-1 switches on),
# values requiring BOTH reductions (1<x<2+sqrt(3)~=3.732), huge saturating
# arguments (->+-pi/2), tiny arguments, negative mirrors (oddness, checked
# separately below via a value-map pairing, not a new BASIC line), and
# general mid-range/decimal-shape coverage.
ATN_BROAD_XS = [
    # --- zero fast path (exercises fp_atan's hand-rolled x==0 exit) -------
    "0",
    # --- tiny -----------------------------------------------------------
    "1e-20", "1e-9", "0.0001", "0.001", "0.01",
    # --- near BREAK=0.26794919243112 (both sides) -----------------------
    "0.2", "0.25", "0.26", "0.267", "0.2679", "0.26794", "0.267949",
    "0.2679491924311", "0.268", "0.27", "0.28", "0.3",
    # --- mid-range --------------------------------------------------------
    "0.4", "0.5", "0.6", "0.7", "0.75", "0.8", "0.9", "0.95", "0.99", "1.7",
    # --- near a=1 (reduction-1 boundary, both sides) -----------------------
    "0.9999999", "0.99999999999", "1", "1.00000000001", "1.0001", "1.5",
    # --- >1, needs reciprocal reduction (some also cross BREAK again) ------
    "2", "3", "3.7", "3.732", "3.8", "5", "10", "50", "100", "1000",
    # --- huge, saturating toward +-pi/2 ------------------------------------
    "1e6", "1e15", "1e30", "1e38",
    # --- negative mirrors (direct truth match; oddness cross-check below) --
    "-0.5", "-1", "-1.7", "-2", "-3.7", "-10", "-100", "-1e-9", "-1e38",
    # --- general decimal-shape coverage -------------------------------------
    "1.23456789", "12.3456789", "123.456789", "0.123456789",
]
EXPRS = EXPRS + [f"atn({_x})" for _x in ATN_BROAD_XS]

# --- ATN FACTYP-leak (§11.7): function-over-float (result must stay DOUBLE),
# single-vs-double literal input widen path, function-over-PEEK.
EXPRS = EXPRS + ["atn(1)+0.5", "atn(0.5!)", "atn(0.5#)", "atn(peek(0))"]

# --- empty-argument / empty parenthesised expression -> "syntax error" -------
# (spec-basic-empty-expr-syntax-error.md, D-F2-3, 2026-07-13). The reference
# raises "Syntax error"; zerobas raises its OWN lowercase "syntax error" (the D-2
# wording idiom), same statement-abort shape. The contract this pins: both sides
# ABORT (no value span) AND print an error tail -- which guards against BOTH the
# original value-leak (`SQR()` -> 0, `PEEK()` -> garbage) and the string-function
# runaway (`LEFT$()` spinning 0s forever). A factor can never begin with ')' or
# ',', so the ev_f / ev_str_arg / str_fn_* gates catch every empty-argument
# intrinsic, bare/nested/trailing-operator parens, and the string functions.
# NOTE (out of scope): a trailing operator at END-OF-STATEMENT (`5+`) is the
# reference's SEPARATE "Missing operand" error, which zerobas does not implement
# -- deliberately NOT in this battery.
EMPTY_ARG = [
    "sqr()", "abs()", "int()", "cint()", "sgn()", "fix()", "csng()", "cdbl()",
    "atn()", "peek()", "sqr(())", "()", "(5+)", "-()", "(,)",
    "len()", "asc()", "val()",
    "chr$()", "str$()", "left$()", "right$()", "mid$()", "hex$()",
    "space$()", "string$()", "instr()",
]
# regression guards: valid parenthesised exprs that must STILL print their value
# (sqr(4) routes to the truth assertion via _sqr_arg; the others compare normally).
EMPTY_ARG_OK = ["(5)", "(5+6)"]
EMPTY_ARG_SET = set(EMPTY_ARG)
EXPRS = EXPRS + EMPTY_ARG + EMPTY_ARG_OK

# Known precision-floor inputs: SQR is correctly-rounded EXCEPT a handful of
# razor-thin near-ties (within ~1e-7 ulp of a 14-digit rounding boundary) that
# a 14+guard-digit method fundamentally cannot resolve (docs/spec-basic-math-
# pack.md §10.4 "precision floor"). There zerobas lands 1 ulp off TRUTH -- but
# the reference ROM shares the exact same limitation and returns the IDENTICAL
# value, so zerobas is never LESS accurate than the reference (adversarial
# review 2026-07-13: ~1180 near-tie-biased cases, 0 where zb is worse than ref;
# only observed floor instance is 99.99998). Pinned here (asserted against the
# KNOWN zb value, NOT truth) so the value cannot silently drift; adding it to
# the plain truth battery above would (correctly) fail.
SQR_KNOWN_FLOOR = {
    # arg string : expected zb value  (truth 9.9999989999999; reference ties = same)
    "99.99998": "9.9999990000000",
}

# ATN documented-deviation catalog (informational; §11.10). The gate does NOT
# pin these -- compare() asserts the ATN_MAX_ULP bound vs truth for EVERY input,
# so this dict launders nothing. It records the inputs (from the slice's
# adversarial pass, cross-checked vs an independent 14-digit op-chain sim) where
# the 14-digit chain lands off truth, split by whether zerobas ties/beats the
# reference or is 1-2 ulp WORSE than it -- the honest picture of the bounded
# deviation the user accepted (§2 resolution). All are within ATN_MAX_ULP.
ATN_DEVIATION_TIE_OR_BETTER = [        # zb off truth but <= reference (near-ties)
    "0.25", "0.268", "0.3", "0.4", "0.6", "0.7", "1.5", "3.732", "1.23456789",
]
ATN_DEVIATION_WORSE_THAN_REF = [       # zb 1-2 ulp off where the reference is exact
    "0.01", "0.75", "0.95", "0.99999999999", "1", "1.00000000001", "-1",
    "0.123456789",
]

# Cases whose TAIL legitimately differs (zerobas's own lowercase D-2-style
# Overflow wording vs the reference's) -- compare only the bracket span
# (both sides must still have SOME tail, i.e. genuinely aborted).
# cint(...) Overflow cases: TAIL differs by wording (zerobas's own lowercase
# D-2-style message); span (the value/continuation shape) still must match.
# sqr(x<0): same idiom -- zerobas's "illegal function call" vs the
# reference's "Illegal function call" (§10.2/§3.4 disposition wording).
SPAN_ONLY = {"cint(32768)", "cint(-32769)", "cint(40000.5)", "cint(32768.1)",
             "sqr(-1)", "sqr(-1e-9)", "sqr(-4)"}

# --- SQR pure-call matcher: routes a plain `sqr(x)` expression to the -------
# truth assertion (compare(), below) instead of the reference. Deliberately
# narrow (bare numeric literal argument only, optional leading '-') so the
# FACTYP-leak/domain-error compound expressions above (`sqr(4)+0.5`,
# `sqr(6.25!)`, `sqr(-1)`, ...) never match -- those stay reference-compared.
_SQR_PURE_RE = re.compile(r"^sqr\((-?[0-9.eEdD+-]+)\)$")


def _sqr_arg(expr: str):
    """Return the Decimal argument if `expr` is a pure `sqr(x)` call
    (x a bare numeric literal), else None."""
    m = _SQR_PURE_RE.match(expr)
    if not m:
        return None
    lit = m.group(1).replace("D", "E").replace("d", "e")
    try:
        return D(lit)
    except decimal.InvalidOperation:
        return None

# --- ATN pure-call matcher: same shape/rationale as _SQR_PURE_RE above -- ---
# routes a plain `atn(x)` call to the truth assertion, never the reference;
# the FACTYP-leak compounds (`atn(1)+0.5`, `atn(0.5!)`, `atn(peek(0))`, ...)
# never match, so they stay reference-compared.
_ATN_PURE_RE = re.compile(r"^atn\((-?[0-9.eEdD+-]+)\)$")


def _atn_arg(expr: str):
    """Return the Decimal argument if `expr` is a pure `atn(x)` call
    (x a bare numeric literal), else None."""
    m = _ATN_PURE_RE.match(expr)
    if not m:
        return None
    lit = m.group(1).replace("D", "E").replace("d", "e")
    try:
        return D(lit)
    except decimal.InvalidOperation:
        return None

# RAW `:`-joined stateful cases: the ABS(-32768%) int-domain escape needs an
# actual int16 -32768 value, which only exists after a TYPED-VAR store
# truncates the single literal -32768.0 into A% (spec §9.1's "ABS(-32768%)
# int-domain per §10 float core", float-core §10.4's -32768\\-1 quirk); a
# store-from-CINT round-trip (FACTYP-leak into a typed variable, §9.4).
RAW_LINES = [
    'a%=-32768:print"[";abs(a%);"]"',
    'a%=cint(3.7):print"[";a%;"]"',
    'a%=cint(-3.7):print"[";a%;"]"',
    # 14-sig-digit double preservation through ABS. Deliberately "raw" (span-
    # only) rather than "expr": its full command line lands exactly on the
    # 40-column screen-wrap boundary, and the two machines' differing prompt
    # widths ("Ok" vs "zb>") shift where the SAME line wraps, flaking the
    # tail's row-echo match even though the printed VALUE is identical (found
    # live in this probe's first differential run) -- the span is the pin.
    'print "[";abs(-1.23456789012345#);"]"',
    # INT/FIX over a TYPED double VARIABLE (review F2: literals only, before) --
    # the var load must carry FACTYP=8 into the function so the result stays
    # double (a wrong narrow reprints 12345678 as 1.23457E+07).
    'a#=12345678.9:print"[";int(a#);"]"',
    'a#=-9999999.5:print"[";int(a#);"]"',
    'a!=-2.5:print"[";fix(a!);"]"',
    # FIX drops a tiny fraction just below -1 -> -1 (double, truncate toward 0).
    # RAW/span-only: the 15-sig-digit arg makes the echoed line cross the 40-col
    # wrap boundary, which the two prompts ("Ok"/"zb>") shift -- same flake as
    # the abs(-1.234...) case above; the printed VALUE is the pin.
    'print"[";fix(-1.00000000000001#);"]"',
    # SQR FACTYP-leak into a typed INT var (§10.6): A%=SQR(9) must round-trip
    # through the int16 store cleanly (9 is a perfect square, no rounding
    # ambiguity -- this pins the store path, not the sqrt itself).
    'a%=sqr(9):print"[";a%;"]"',
    # ATN FACTYP-leak into a typed INT var (§11.7): A%=ATN(1) truncates the
    # double 0.785... to 0 on both sides regardless of the 14th-digit
    # accuracy difference between zerobas and the reference -- this pins the
    # int-store path, not atan's own rounding (that's the truth battery's job).
    'a%=atn(1):print"[";a%;"]"',
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE,
                    help=f"reference oracle machine (default {REF_MACHINE})")
    ap.add_argument("--zb-machine", dest="zb_machine",
                    help="differential mode: also run this repack machine and "
                         "assert span/tail equality")
    ap.add_argument("--only", help="substring filter on the expression")
    ap.add_argument("--boot-per-case", dest="boot_per_case", action="store_true",
                    help="isolate each case in its own boot (slow) instead of "
                         "the default single-boot batch")
    ap.add_argument("--skip-tokens", action="store_true",
                    help="skip the token-capture check (value matrix only)")
    args = ap.parse_args()

    ok = True
    if not args.skip_tokens:
        ok = check_tokens(args.machine) and ok
        print()

    cases = [(e, f'print "[";{e};"]"', "expr") for e in EXPRS]
    cases += [(line, line, "raw") for line in RAW_LINES]
    cases = [c for c in cases if not (args.only and args.only not in c[0])]
    specs = [("direct", [line]) for _, line, _ in cases]

    result_span = omsx_repl.result_span
    screen_tail = omsx_repl.screen_tail

    if not args.zb_machine:
        for (expr, line, kind), raw in zip(cases, omsx_repl.run_cases(
                args.machine, specs, batch=not args.boot_per_case,
                reset=("NEW", "CLS"))):
            ref_span, ref_tail = result_span(raw), screen_tail(raw, line)
            rs = f"[{ref_span}]" if ref_span is not None else "<no span>"
            extra = ""
            if ref_tail is not None and ref_tail.count("|") + 1 > 1:
                extra = f"   tail: {ref_tail!r}"
            elif ref_span is None:
                extra = f"   tail: {ref_tail!r}"
            print(f"{expr:<26} {rs}{extra}")
        return 0 if ok else 1

    def compare(i, ref_raw, zb_raw):
        expr, line, kind = cases[i]
        ref_span, ref_tail = result_span(ref_raw), screen_tail(ref_raw, line)
        zb_span, zb_tail = result_span(zb_raw), screen_tail(zb_raw, line)
        if expr in EMPTY_ARG_SET:
            # D-F2-3: BOTH abort with an error tail and print NO value span.
            # "error" in the tail rules out a runaway (LEFT$() spinning 0s ->
            # a long digit tail, no "error") as well as a value leak.
            return (ref_span is None and zb_span is None
                    and bool(zb_tail) and "error" in zb_tail.lower()
                    and bool(ref_tail) and "error" in ref_tail.lower())
        sqr_x = _sqr_arg(expr) if expr not in SPAN_ONLY else None
        if sqr_x is not None:
            # §10.3.1/§10.6 FINAL: the oracle is mathematical truth, NOT the
            # reference (its own division is 1 ulp low on ~15/72 -- see the
            # reference-deviation report below, informational only). This is
            # what actually guarantees "correctly-rounded": comparing zb to
            # the reference would just re-certify the reference's own bias.
            # (SPAN_ONLY excluded first: sqr(x<0) is a domain error, not a
            # value to truth-check -- it must fall through to the ordinary
            # tail-comparison path below.)
            zb_val = parse_basic_number(zb_span)
            arg = _SQR_PURE_RE.match(expr).group(1)
            if arg in SQR_KNOWN_FLOOR:      # precision floor: pin to known zb, not truth
                return zb_val is not None \
                    and zb_val == parse_basic_number(SQR_KNOWN_FLOOR[arg])
            return zb_val is not None and zb_val == truth_sqrt14(sqr_x)
        atn_x = _atn_arg(expr) if expr not in SPAN_ONLY else None
        if atn_x is not None:
            # §11.7 REVISED (documented bounded deviation, user 2026-07-13):
            # the oracle is mathematical truth, but ATN is asserted to a BOUND
            # (<= ATN_MAX_ULP of the 14-sig truth) rather than == truth. ATN's
            # chained 14-digit evaluation is not strictly correctly-rounded and
            # reaching that needs an extended-precision layer we chose not to
            # build (see ATN_MAX_ULP's header). The specific per-input
            # deviations (incl. the handful worse than the reference) are
            # catalogued in the informational report below, not laundered.
            zb_val = parse_basic_number(zb_span)
            if zb_val is None:
                return False
            d = ulp_dist(zb_val, truth_atan14(atn_x))
            return d is not None and d <= ATN_MAX_ULP
        if kind == "raw":
            return ref_span is not None and ref_span == zb_span
        if expr in SPAN_ONLY:
            return ref_tail is not None and zb_tail is not None \
                and ref_span == zb_span
        return ref_tail is not None and ref_tail == zb_tail

    verdicts, ref_raws, zb_raws = omsx_repl.run_differential(
        args.machine, args.zb_machine, specs, compare,
        batch=not args.boot_per_case, reset=("NEW", "CLS"))

    ref_deviations = []     # (expr, x, reference_val, truth) -- reference != truth (informational)
    atn_ref_deviations = []  # same, for ATN (§11.7's documented-deviation report)
    atn_zb_by_x = {}         # Decimal(x) -> zb_val, for the oddness cross-check below
    for (expr, line, kind), good, ref_raw, zb_raw in zip(
            cases, verdicts, ref_raws, zb_raws):
        ok = ok and good
        ref_span = result_span(ref_raw)
        rs = f"[{ref_span}]" if ref_span is not None else "<no span>"
        print(f"{'PASS' if good else 'FAIL'}  {expr:<26} ref: {rs}")
        if not good:
            zb_span, zb_tail = result_span(zb_raw), screen_tail(zb_raw, line)
            zs = f"[{zb_span}]" if zb_span is not None else "<no span>"
            print(f"{'':>34}ref tail: {screen_tail(ref_raw, line)!r}")
            print(f"{'':>34}zb  span: {zs}  tail: {zb_tail!r}")
        sqr_x = _sqr_arg(expr) if expr not in SPAN_ONLY else None
        if sqr_x is not None:
            ref_val = parse_basic_number(ref_span)
            truth = truth_sqrt14(sqr_x)
            if ref_val is not None and ref_val != truth:
                ref_deviations.append((expr, sqr_x, ref_val, truth))
        atn_x = _atn_arg(expr) if expr not in SPAN_ONLY else None
        if atn_x is not None:
            zb_val = parse_basic_number(result_span(zb_raw))
            if zb_val is not None:
                atn_zb_by_x[atn_x] = zb_val
            ref_val = parse_basic_number(ref_span)
            truth = truth_atan14(atn_x)
            if ref_val is not None and ref_val != truth:
                atn_ref_deviations.append((expr, atn_x, ref_val, truth))

    if ref_deviations:
        print(f"\n--- SQR reference-deviation report ({len(ref_deviations)}/"
              f"{len(SQR_BROAD_XS)}) -- INFORMATIONAL, does not affect "
              "pass/fail (§10.3.1/§10.6) ---")
        print("(the reference ROM's own SQR is ~1 ulp off mathematical "
              "truth on these inputs -- its division is low-biased; "
              "zerobas is correct here. Never asserted against.)")
        for expr, x, ref_val, truth in ref_deviations:
            print(f"  {expr:<26} reference={ref_val!s:<20} truth={truth!s}")

    # --- ATN documented bounded-deviation summary (§11.10, user 2026-07-13):
    # zerobas ATN is asserted to <= ATN_MAX_ULP of truth (not == truth, not
    # never-worse). Print zb's own worst deviation from truth + the honest
    # split (ties/beats reference vs 1-2 ulp worse than it). This is the
    # accepted deviation, catalogued -- not laundered (the bound decides
    # pass/fail independently in compare()).
    atn_worst = D(0); atn_exact = 0; atn_total = 0
    atn_worse_seen = []
    for x, zb_val in atn_zb_by_x.items():
        d = ulp_dist(zb_val, truth_atan14(x))
        if d is None:
            continue
        atn_total += 1
        if d == 0:
            atn_exact += 1
        if d > atn_worst:
            atn_worst = d
    if atn_total:
        print(f"\n--- ATN accuracy vs mathematical truth ({atn_total} pure atn "
              f"inputs) -- bound = {ATN_MAX_ULP} ulp (§11.7 REVISED) ---")
        print(f"  correctly-rounded (== truth): {atn_exact}/{atn_total}; "
              f"worst deviation: {atn_worst} ulp (bound {ATN_MAX_ULP}).")
        # Drift tripwire (Fable review finding #2): the <=2-ulp bound alone
        # would let a UNIFORM 1-2-ulp degradation (e.g. a coeff-regen bug or a
        # dropped final widen) pass silently -- every input still within bound.
        # Assert a battery-wide correctly-rounded FLOOR so such a regression
        # fails the gate. NOT a per-value pin (compatible with the ratified
        # bounded-deviation resolution): current is 44/61; floor 40 leaves
        # margin for benign last-ulp shifts while catching a gross uniform drop.
        if atn_exact < ATN_EXACT_FLOOR:
            print(f"FAIL  ATN correctly-rounded count {atn_exact} < floor "
                  f"{ATN_EXACT_FLOOR} -- uniform accuracy regression (all still "
                  "within bound but the exact-count collapsed).")
            ok = False
        print(f"  DOCUMENTED bounded deviation (user sign-off): ATN's 14-digit "
              "chain is not strictly correctly-rounded; reaching that needs an "
              "extended-precision layer (not built -- §2/§11 resolution). "
              "Within the reference's own <=2-ulp envelope.")
        print(f"  tie/beat reference: {', '.join(ATN_DEVIATION_TIE_OR_BETTER)}")
        print(f"  1-2 ulp WORSE than reference (accepted): "
              f"{', '.join(ATN_DEVIATION_WORSE_THAN_REF)}")

    if atn_ref_deviations:
        print(f"\n--- ATN reference-deviation report ({len(atn_ref_deviations)}/"
              f"{len(ATN_BROAD_XS)}) -- INFORMATIONAL ---")
        print("(inputs where the reference ROM's own ATN misses mathematical "
              "truth; ~correctly-rounded overall per §1.1. Never asserted against.)")
        for expr, x, ref_val, truth in atn_ref_deviations:
            print(f"  {expr:<26} reference={ref_val!s:<20} truth={truth!s}")

    # --- ATN oddness cross-check (§11.7): atn(-x) == -atn(x) for every x in
    # the broad battery whose negative mirror is ALSO present -- verified
    # from the already-collected zb values (no extra machine round-trip).
    # By construction fp_atan computes a positive magnitude and applies the
    # sign last (sub/fp_atan.asm step 5), so this should hold EXACTLY (zero
    # rounding slack -- a+(-a) is exact cancellation, not a rounding event).
    odd_checked = 0
    for x, zb_val in list(atn_zb_by_x.items()):
        if -x in atn_zb_by_x:
            odd_checked += 1
            if atn_zb_by_x[-x] != -zb_val:
                print(f"FAIL  oddness: atn({x}) = {zb_val}  but  "
                      f"atn({-x}) = {atn_zb_by_x[-x]}  (expected {-zb_val})")
                ok = False
    if odd_checked:
        print(f"\nATN oddness cross-check: {odd_checked // 2} mirrored pair(s) "
              "verified atn(-x) == -atn(x)")

    print("\nALL PASS — SQR is correctly-rounded (== mathematical truth) over "
          "the broad battery except the pinned near-tie precision floor "
          f"({', '.join(SQR_KNOWN_FLOOR)}, where zerobas ties the reference, "
          f"never worse); ATN is within {ATN_MAX_ULP} ulp of truth over its "
          "broad battery (documented bounded deviation, user sign-off -- ATN's "
          "reference is the one ~correctly-rounded case, and our 14-digit chain "
          "matches its <=2-ulp envelope), oddness holds exactly; both reference "
          "ROMs' own biases are documented above, never asserted against" if ok
          else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
