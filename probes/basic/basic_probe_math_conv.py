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


# --- EXP/LOG truth oracles (math pack slice 2b, docs/spec-basic-mathpack-
# slice2.md §12.7): the SAME "the oracle is mathematical truth, not the
# reference" framework as SQR/ATN. Python's `decimal` has native .exp()/.ln()
# (unlike atan), so these are plain high-precision Decimal calls -- still an
# INDEPENDENT computation from zerobas's own table-reduction+minimax-Horner
# chain, used only as the host truth oracle for the gate. truth_exp14 also
# applies the SAME MAXV/MINV engine-boundary disposal tools/sim_math_chain.py's
# own exp_truth() does, so it represents what a perfect 14-digit engine's
# OWN defined overflow("Overflow")/underflow(0) behaviour looks like -- not
# raw unbounded math -- which lets the three underflow-to-0 dispositions
# (EXP(-147.4)/(-200)/(-1000), §12.7) flow through the ordinary pure-call
# truth assertion with no special-casing (LOG never overflows/underflows its
# own FPNUM range for any x in its stub-guaranteed positive domain, so
# truth_log14 needs no such floor).
_EXP_MAXV = D("9.9999999999999E+62")   # FPNUM magnitude ceiling (dexp +63)
_EXP_MINV = D("1E-64")                 # smallest positive normal (dexp -63)


def _round14(val: "decimal.Decimal") -> "decimal.Decimal":
    """Correctly-rounded (half-up) 14-significant-digit re-quantization of an
    already-high-precision Decimal -- the same quantize shape truth_sqrt14/
    truth_atan14 each use."""
    digits = val.as_tuple().digits
    exp = val.as_tuple().exponent
    if len(digits) <= 14:
        return val
    quant_exp = exp + (len(digits) - 14)
    quantum = D(1).scaleb(quant_exp)
    with decimal.localcontext() as ctx:
        ctx.prec = 60
        ctx.rounding = decimal.ROUND_HALF_UP
        return val.quantize(quantum)


def truth_exp14(x) -> "decimal.Decimal | str":
    """Host-computed, correctly-rounded 14-significant-digit exp(x), WITH the
    engine's own MAXV/MINV boundary disposal (see module comment above)."""
    x = D(x)
    with decimal.localcontext() as ctx:
        ctx.prec = 50
        val = x.exp()
    rounded = _round14(val)
    if rounded > _EXP_MAXV:
        return "Overflow"
    if rounded != 0 and abs(rounded) < _EXP_MINV:
        return D(0)
    return rounded


def truth_log14(x) -> "decimal.Decimal":
    """Host-computed, correctly-rounded 14-significant-digit ln(x) (x>0)."""
    x = D(x)
    with decimal.localcontext() as ctx:
        ctx.prec = 50
        val = x.ln()
    return _round14(val)


# EXP/LOG documented-deviation bounds (§12.1/§12.7, pre-proven by
# tools/sim_math_chain.py BEFORE this asm/probe was written -- the §11.10
# lesson applied forward): worst-case ulp measured by the sim over its own
# ~4000-input batteries, PLUS a margin for EXP (the sim's own no-sticky-digit
# modelling limit, see sim_math_chain.py's module comment). Per-input never-
# worse-than-reference is NOT asserted (§12.1: the reference is itself 3-45
# ulp (EXP) / 1-5 ulp (LOG) off truth, so that invariant would be vacuous).
EXP_MAX_ULP = 2
LOG_MAX_ULP = 4
# Battery-wide correctly-rounded floors (drift tripwires, ATN_EXACT_FLOOR
# precedent): fail if fewer than this many pure EXP/LOG inputs are exactly
# == truth, catching a uniform ulp degradation the per-input bound alone
# would miss. MEASURED on THIS probe's own (smaller) hardware battery
# 2026-07-13 (VG-8020 reference / C-BIOS_MSX1_EU_REPACK_DISK zerobas):
# EXP 24/32 correctly-rounded (worst 1 ulp); LOG 26/35 correctly-rounded
# (worst 2 ulp) -- both comfortably inside their §12.1 sim-predicted
# envelopes (92.0%/87.3% on the sim's own much larger ~4000-input battery).
# Floor set to (measured-1) to leave a 1-count margin for a benign last-ulp
# shift, same rationale as ATN_EXACT_FLOOR.
EXP_EXACT_FLOOR = 23
LOG_EXACT_FLOOR = 25


def ulp_dist(val, truth) -> "decimal.Decimal | None":
    """Distance |val - truth| in units of the 14th significant digit of truth."""
    if val is None or truth is None:
        return None
    if truth == 0:
        return abs(val)            # atan(0)=0 exact path; any nonzero is a gross fail
    scale = D(10) ** (truth.adjusted() - 13)
    return (abs(val - truth) / scale)


# --- POW (`^`) truth oracle (math pack slice 2c, docs/spec-basic-mathpack-
# slice2.md §13.6): mirrors tools/sim_math_chain.py's pow_truth -- an
# INDEPENDENT high-precision computation (plain Decimal `**`/`.ln()`/`.exp()`),
# used only as the host truth oracle for the truth-bound rows below (neg-y,
# frac, the "-2^.5" grammar outlier). The int-path's OWN claim (§13.2:
# "positive-y integer path: REFERENCE-IDENTICAL BIT-FOR-BIT") is instead
# checked by plain reference differential (the ordinary EXPRS path) -- no
# truth oracle involved there.
def truth_pow14(x, y) -> "decimal.Decimal":
    """Host-computed, correctly-rounded 14-significant-digit x**y (integer or
    fractional y; x may be negative only for integer y). Same quantize shape
    as truth_sqrt14/truth_atan14/truth_exp14/truth_log14 above."""
    x, y = D(x), D(y)
    if y == y.to_integral_value():
        with decimal.localcontext() as ctx:
            ctx.prec = 80
            val = x ** int(y)
    else:
        with decimal.localcontext() as ctx:
            ctx.prec = 60
            val = (y * x.ln()).exp()
    digits = val.as_tuple().digits
    exp = val.as_tuple().exponent
    if len(digits) <= 14:
        return val
    quant_exp = exp + (len(digits) - 14)
    quantum = D(1).scaleb(quant_exp)
    with decimal.localcontext() as ctx:
        ctx.prec = 80
        ctx.rounding = decimal.ROUND_HALF_UP
        return val.quantize(quantum)


# Per-row caps (§13.2, sim-proven tools/sim_math_chain.py POW_INT_ROW_K/
# POW_FRAC_T_K/POW_FRAC_T_C -- same constants, independently re-asserted
# here): the int path (incl. negative y, which adds one correctly-rounded
# fp_div) inherits the square-and-multiply structure's OWN error-doubling
# per squaring, cap = POW_INT_ROW_K * 2^bitlen(n); the frac path's deviation
# scales with |t| = |y*log x|, cap = POW_FRAC_T_K*max(1,|t|) + POW_FRAC_T_C.
POW_INT_ROW_K = 3
POW_FRAC_T_K = 12
POW_FRAC_T_C = 10


def pow_int_cap(n) -> "decimal.Decimal":
    return D(POW_INT_ROW_K * (1 << int(abs(n)).bit_length()))


def pow_frac_cap(x, y) -> "decimal.Decimal":
    x, y = D(x), D(y)
    with decimal.localcontext() as ctx:
        ctx.prec = 30
        t = abs(y * x.ln())
    return D(POW_FRAC_T_K) * max(D(1), t) + POW_FRAC_T_C


# --- SIN/COS/TAN truth oracles (math pack slice 2d, docs/spec-basic-
# mathpack-slice2.md §14.8): the SAME "the oracle is mathematical truth, not
# the reference" framework as SQR/ATN/EXP/LOG/POW. Independent high-precision
# quadrant reduction (Decimal prec~60, k=round-half-even(x/(pi/2)),
# r=x-k*(pi/2), Taylor series for sin(r)/cos(r) -- NOT zerobas's own
# Cody-Waite-style round-then-truncate reduction or its own minimax Horner
# polys) -- the SAME reduction shape as scratchpad/char_trig.py's own
# truth() (the slice's black-box characterization tool) and
# tools/sim_math_chain.py's sincos_truth, promoted here to the same
# 14-significant-digit correctly-rounded quantize every other truth_*14
# oracle in this file uses.
_TRIG_PI = D("3.14159265358979323846264338327950288419716939937510582097494")


def _trig_series_sin(r: "decimal.Decimal") -> "decimal.Decimal":
    acc = D(0); term = r; t2 = r * r; k = 1; sg = 1
    for _ in range(60):
        acc += sg * term
        term = term * t2 / ((k + 1) * (k + 2))
        k += 2
        sg = -sg
    return acc


def _trig_series_cos(r: "decimal.Decimal") -> "decimal.Decimal":
    acc = D(0); term = D(1); t2 = r * r; k = 0; sg = 1
    for _ in range(60):
        acc += sg * term
        term = term * t2 / ((k + 1) * (k + 2))
        k += 2
        sg = -sg
    return acc


def _trig_reduce(x: "decimal.Decimal"):
    """-> (sin(x), cos(x)) at ~60 working digits, independent quadrant
    reduction (round-half-even k, matching char_trig.py's truth())."""
    with decimal.localcontext() as ctx:
        ctx.prec = 60
        k = (x / (_TRIG_PI / 2)).to_integral_value(rounding=decimal.ROUND_HALF_EVEN)
        r = x - k * (_TRIG_PI / 2)
        sv = _trig_series_sin(r)
        cv = _trig_series_cos(r)
        q = int(k) % 4
        sin_v = {0: sv, 1: cv, 2: -sv, 3: -cv}[q]
        cos_v = {0: cv, 1: -sv, 2: -cv, 3: sv}[q]
    return sin_v, cos_v


def truth_sin14(x) -> "decimal.Decimal":
    """Host-computed, correctly-rounded 14-significant-digit sin(x) --
    mathematical truth, not the reference ROM (same framework as
    truth_sqrt14/truth_atan14/truth_exp14/truth_log14/truth_pow14)."""
    sv, _ = _trig_reduce(D(x))
    return _round14(sv)


def truth_cos14(x) -> "decimal.Decimal":
    """Host-computed, correctly-rounded 14-significant-digit cos(x)."""
    _, cv = _trig_reduce(D(x))
    return _round14(cv)


def truth_tan14(x):
    """Host-computed 14-significant-digit tan(x) = truth_sin14(x)/
    truth_cos14(x) -- the SAME two-step 'round sin/cos to 14 digits THEN
    divide' model tools/sim_math_chain.py's own tan_truth uses (not a raw
    high-precision tan/(x)) -- TAN_MAX_ULP below is calibrated against that
    model, the same 14-digit sinv/cosv-then-fp_div chain sub/fp_sin.asm's
    own fp_tan computes. Returns the 'Overflow' sentinel (mirrors
    truth_exp14's own non-Decimal sentinel convention) if cos rounds to
    exactly 0 at 14 digits."""
    s = truth_sin14(x)
    c = truth_cos14(x)
    if c == 0:
        return "Overflow"
    with decimal.localcontext() as ctx:
        ctx.prec = 40
        val = s / c
    return _round14(val)


# SIN/COS/TAN documented-deviation bounds (§14.2, pre-proven by
# tools/sim_math_chain.py BEFORE this asm/probe was written -- the §12.9/
# §11.10 lesson applied forward): SIN/COS are bounded in [-1,1], so ABSOLUTE
# error is the uniform metric (relative ulp blows up near the result-zeros,
# inherent to every reduction incl. the reference's own catastrophic
# near-pi/2 COS, §1.1); TAN uses relative ulp in the well-conditioned band
# 0.1<=|tan|<=10 (bounded away from both TAN's zeros and poles). Sim-measured
# 2026-07-14: SIN/COS worst abs 1.0E-14, 100% correctly-rounded (|val|>=.1);
# TAN worst 11 ulp @ x~=950 (band edge).
SIN_ABS_TOL = D("3E-14")          # abs-error bound over the moderate battery
                                  # (|x|<=~1000 -- the sim's own scoping)
SIN_CR_FLOOR = 27                 # correctly-rounded (abs<=1 ulp) floor over
COS_CR_FLOOR = 30                 # |val|>=.1 inputs -- drift tripwire
                                  # (ATN_EXACT_FLOOR "measured-1" precedent):
                                  # measured on THIS probe's own hardware
                                  # battery 2026-07-14, SIN 28/28 (100%), COS
                                  # 31/31 (100%) correctly-rounded, both
                                  # comfortably matching §14.2's sim-predicted
                                  # 100% envelope; floor = measured-1
TAN_MAX_ULP = 16                  # rel-ulp bound, 0.1<=|tan|<=10 (sim worst
                                  # 11 @ x~=950, ~1.5x margin)


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
    ("EXP",  "a=exp(1)",  0x8B),
    ("LOG",  "a=log(1)",  0x8A),
    ("SIN",  "a=sin(1)",  0x89),
    ("COS",  "a=cos(1)",  0x8C),
    ("TAN",  "a=tan(1)",  0x8D),
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


# --- POW token capture (math pack slice 2c, §13.6): `^` is a PLAIN single- --
# byte operator token (POW_TOKEN=$F5), NOT $FF-prefixed like the seven
# functions in TOKENS above -- so it needs its own crunch check (no $FF
# byte to key off). Also verifies the LIST round-trip (detok renders `^`
# back to the source char), which the $FF-prefixed functions above never
# exercised for a NEW single-char operator (they reuse the generic keyword
# detok path; `^` is the first slice-2c change to touch tokenise.inc/
# detok.inc at all).
def check_pow_token(machine: str) -> bool:
    ok = True
    print("\n--- POW token capture (`^` crunch + LIST round-trip) ---")

    crunch_raws = omsx_repl.run_cases(machine, [("direct", ["1 a=2^3"])],
                                      batch=True, reset=("NEW",),
                                      capture=("stored_line", C.TXTTAB))
    ref = C.tokens(crunch_raws[0])
    got = bool(ref) and 0xF5 in ref
    ok = ok and got
    s = " ".join(f"{b:02X}" for b in ref) if ref else "<not stored>"
    print(f"{'OK' if got else 'FAIL want F5'} crunch  a=2^3 -> {s}")

    list_raws = omsx_repl.run_cases(machine, [("direct", ["1 a=2^3", "list"])],
                                    batch=True, reset=("NEW", "CLS"))
    raw_screen = list_raws[0] or ""
    list_ok = "2^3" in raw_screen
    ok = ok and list_ok
    print(f"{'OK' if list_ok else 'FAIL'} LIST round-trip renders '2^3'")
    print("POW token capture: ALL OK" if ok else "POW token capture: MISMATCH")
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

# --- EXP value battery (math pack slice 2b, §12.7): the oracle is
# MATHEMATICAL TRUTH (truth_exp14 above), same framework as SQR/ATN -- every
# entry is a PURE `exp(x)` call (matched by _EXP_PURE_RE below) so its
# assertion routes to truth_exp14(x), never to the reference span. Covers:
# the zero/tiny/mid-range/decimal-shape characterization anchors, the
# r~=0 stress points (ln10 multiples, where the n8 reduction lands exactly
# on a decade), the n8-boundary straddle (both sides of a table-index flip),
# and the two FINITE range straddles (145.062/-147.3, still in-range,
# value-asserted) plus the three deep-underflow-to-0 dispositions (these
# flow through the SAME truth assertion -- truth_exp14's own MAXV/MINV floor
# gives exactly 0, matching the tenant's own silent-underflow behaviour, so
# no special-casing is needed here; contrast the THREE OVERFLOW dispositions
# below, which abort with no value and so must be excluded from this pure-
# call routing via SPAN_ONLY).
EXP_BROAD_XS = [
    "0",
    "1e-13", "-1e-13", "1e-9", "-1e-9", "0.001", "-0.001", "0.5", "-0.5",
    "1", "-1", "2", "-2", "10", "-10", "20", "-20",
    "88", "100", "142.7",
    # --- r~=0 stress points (ln10 multiples -- n8 reduction lands exactly
    # on a decade boundary) --------------------------------------------------
    "2.3025850929940", "-2.3025850929940", "4.6051701859881",
    "23.025850929940",
    # --- n8-boundary straddle (both sides of a table-index flip) -----------
    "0.14391156831213", "0.14391156831214", "-0.14391156831213",
    # --- finite range straddles (still in-range, value-asserted) ----------
    "145.062", "-147.3",
    # --- deep underflow-to-0 (truth_exp14's own MINV floor gives 0) --------
    "-147.4", "-200", "-1000",
]
EXPRS = EXPRS + [f"exp({_x})" for _x in EXP_BROAD_XS]

# --- LOG value battery (§12.7): same truth-oracle framework. Covers: the
# near-1 ladder (both the j-scan and the e'=-1/e'=0 boundary), mid-range/
# decimal-shape anchors, the extreme decades (including the MAXV/MINV
# corners), the j=8 FOLD zone (x in [0.866,1), the >2-ulp-worst region per
# §12.1), breakpoint straddles (both scan outcomes, LOG_BP[1]/[4]/[8] +-1
# ulp), and the two exact K-hat hits (s=0 rails, POW8_TBL[1]/[6]).
LOG_BROAD_XS = [
    "1",
    # --- 1 +- 10^-k ladder (near-1 accuracy / j-scan+e' boundary) ----------
    "1.1", "0.9", "1.00001", "0.99999", "1.000000001", "0.999999999",
    "1.0000000000001", "0.9999999999999",
    "0.99", "2", "3", "7", "2.7182818284590", "0.5", "0.25", "0.1",
    "0.001", "1000",
    # --- extreme decades (incl. MAXV/MINV corners) -------------------------
    "1E10", "1E-10", "1E62", "1E-64", "9.9999999999999E62",
    # --- j=8 fold zone (x in [0.866,1), the >2-ulp-worst region, §12.1) ----
    "0.87", "0.9245459892507", "0.95",
    # --- breakpoint straddles (both scan outcomes; LOG_BP[1]/[4]/[8] +-1
    # ulp as 14-sig literals) -----------------------------------------------
    "1.1547819846894", "1.1547819846896",
    "2.7384196342643", "2.7384196342645",
    "8.6596432336006", "8.6596432336008",
    # --- exact K-hat hits (s=0 rails: POW8_TBL[1]/[6]) ---------------------
    "1.3335214321633", "5.6234132519035",
]
EXPRS = EXPRS + [f"log({_x})" for _x in LOG_BROAD_XS]

# --- EXP/LOG FACTYP-leak (§12.7): function-over-float (result must stay
# DOUBLE), single-vs-double literal input widen path, function-over-PEEK.
# EXP's PEEK case uses `\100` (integer division, still FACTYP=2 into EXP) --
# a bare `exp(peek(0))` was found LIVE to overflow (this machine's PEEK(0)
# is 243, well past EXP's ~146 ceiling), an accidental domain hit ATN's own
# TOTAL-function precedent (`atn(peek(0))`) never has to dodge; `\100`
# guarantees a small in-range int operand regardless of the actual byte at
# address 0. LOG's PEEK case adds 1 to keep the operand positive -- LOG's
# domain check would otherwise turn a stray PEEK(0)==0 into an unrelated
# error.
EXPRS = EXPRS + ["exp(1)+0.5", "exp(0.5!)", "exp(0.5#)", "exp(peek(0)\\100)",
                 "log(10)+0.5", "log(2!)", "log(2#)", "log(peek(0)+1)"]

# --- EXP/LOG FACTYP-leak rows route to a TRUTH-based check, NOT the ---------
# reference (departs from the ATN precedent, where the identically-shaped
# `atn(1)+0.5` etc. compare cleanly against the reference span). Found LIVE
# (this probe's own characterization run, --skip-tokens --only "exp("/"log("):
# EXP/LOG's own reference is markedly less accurate than ATN's near-
# correctly-rounded one (§12.1: only ~15%/~30% exact) and, unlike ATN's
# `atn(1)+0.5` (whose 0.785->1.285 digit-COUNT shift happens to absorb a
# last-digit slip), these particular compounds do NOT get that masking
# shift: `exp(1)+0.5` printed 3.2182818284588 on the reference vs zerobas's
# truth-exact 3.2182818284590 (2 ulp, matching EXP's own -3-ulp-mean
# characterization), and `log(2!)`/`log(2#)` likewise (reference
# .69314718055993 vs truth .69314718055995). A raw reference-tail compare
# would fail these NOT because of a zerobas bug but because the reference
# itself is imprecise here -- so each routes to its own truth-based
# expected value (still exercising the SAME FACTYP-leak/widen-path
# plumbing) with a generous ulp allowance that comfortably absorbs the
# compound operation's own final re-rounding while still catching a real
# FACTYP-narrowing bug (which would be many thousands of ulp off, not a
# handful).
_MATH_FACTYP_LEAK_TRUTH = {
    "exp(1)+0.5":        lambda: truth_exp14("1") + D("0.5"),
    "exp(0.5!)":         lambda: truth_exp14("0.5"),
    "exp(0.5#)":         lambda: truth_exp14("0.5"),
    "exp(peek(0)\\100)": lambda: truth_exp14("2"),   # this machine's PEEK(0)=243
    "log(10)+0.5":       lambda: truth_log14("10") + D("0.5"),
    "log(2!)":           lambda: truth_log14("2"),
    "log(2#)":           lambda: truth_log14("2"),
    "log(peek(0)+1)":    lambda: truth_log14("244"),  # PEEK(0)+1 = 243+1
    # POW FACTYP-leak (§13.6): a#=2^.5 stores the frac-path result into a
    # DOUBLE var, then a#*a# squares it -- same "the reference's own
    # imprecision, not ours, would fail a raw tail compare" reasoning as the
    # EXP/LOG rows above (confirmed live: ref prints 1.9999999999997,
    # zerobas prints exactly 2 -- the reference's 1-ulp-off-truth 2^.5,
    # squared, visibly amplifies to 3 ulp; zerobas's truth-exact 2^.5
    # squares back to 2 within the print's own 14-digit rounding).
    'a#=2^.5:print"[";a#*a#;"]"': lambda: truth_pow14("2", "0.5") ** 2,
}
_MATH_FACTYP_LEAK_ULP = 6

# --- EXP/LOG domain/disposition rows (§12.7, per-machine wording) ---------
# LOG(0)/LOG(-1): "illegal function call" (SPAN_ONLY below, evmc_sqr_err's
# shape verbatim -- own lowercase D-2 wording vs the reference's). EXP's
# THREE overflow paths each exercise a DIFFERENT disposition point: EXP(146)
# is round_and_finalize's own true-magnitude bound (the tenant's step-8
# scale multiply); EXP(200) is the tenant's own internal n8-bound (n8>552,
# §12.4 step 3); EXP(1000) is evmc_exp's own coarse stub pre-check
# (dexp>=4). All three abort with NO printed value (SPAN_ONLY, same as the
# CINT-Overflow precedent) -- contrast the underflow trio above, which DOES
# print a value (0) and so flows through the ordinary truth assertion.
EXPRS = EXPRS + ["log(0)", "log(-1)", "exp(146)", "exp(200)", "exp(1000)"]

# =============================================================================
# POW (`^`) battery (math pack slice 2c, docs/spec-basic-mathpack-slice2.md
# §13.6). Four row kinds, matching §13.2's OWN precisely-scoped claim:
#   * grammar (differential, exact-match reference-identical) -- the §13.1
#     precedence pins, EXCEPT "-2^.5" (see the CONTRACT FINDING below).
#   * int-path (differential, BIT-IDENTITY vs reference) -- POW_REF_ANCHORS
#     (the SAME 32-row table as tools/sim_math_chain.py, black-box captured
#     char_pow rounds 1-5 2026-07-14; copied here rather than imported, the
#     same "each probe keeps its own independent oracle" convention as
#     truth_sqrt14/truth_atan14/truth_exp14/truth_log14 above) + 15 fresh
#     POSITIVE-y random pairs. §13.2's claim is scoped to "the positive-y
#     integer path" specifically -- negative-y int cases add one correctly-
#     rounded fp_div and so are truth-bound, not reference-exact (folded
#     into the neg-y battery below): a live differential run (this probe's
#     own characterization pass) confirms random negative-y pairs DO
#     deviate from the reference by up to 1 ulp (e.g. `1.5^-44` prints
#     `1.7864242338402E-08` on the reference vs `1.7864242338403E-08` here),
#     so only POSITIVE-y random draws belong in the strict-differential set.
#   * neg-y + frac (truth-bound, ATN shape): the documented bounded
#     deviation, per-row caps from §13.2/truth_pow14 above.
#
# CONTRACT FINDING (flagged, not hidden -- the §12.9-precedent class of
# live-implementer-caught contract gap): §13.6 lists "-2^.5" among the
# grammar battery's "differential, EXACT-match both machines" rows. A live
# VG-8020 differential run (this probe's own characterization pass) shows
# it does NOT match: the reference prints `-1.414213562373` (13 significant
# digits) vs zerobas's `-1.4142135623731` (14) -- `-2^.5` = -(2^0.5) takes
# the SAME frac-path EXP(0.5*LOG(2)) computation that (unsurprisingly)
# lands on the exact value SQR(2) already does, and `sqr(2)` independently
# reproduces the identical reference-vs-truth 1-ulp deviation ALREADY
# documented and accepted (math-pack §10.3.1's own SQR framework -- the
# reference's SQR(2) is off from truth by exactly this last digit, and
# `2^.5`/`2^0.5`/`sqr(2)` were confirmed live to all print the SAME
# 13-digit reference value). So the §13.1 characterization pass that
# pinned this one row as "exact-match" was mistaken (an oversight in that
# characterization, not a zerobas defect); it is asserted here via the SAME
# truth-bound frac-path cap as the rest of the documented-deviation
# battery, not a literal reference-tail comparison.
# =============================================================================

# --- grammar battery (differential, exact-match both machines) -------------
POW_GRAMMAR_XS = [
    "2^3^2", "2^2^3", "-2^2", "2^-3", "-2^-2", "2^-3^2", "2^-2^-2",
    "2*3^2", "7\\2^2", "(2^3)^2", "2^-3*4",
]
EXPRS = EXPRS + POW_GRAMMAR_XS
# "-2^.5" is the CONTRACT FINDING above: truth-bound, not exact-differential.
EXPRS = EXPRS + ["-2^.5"]

# --- int-path anchors (differential vs reference; BIT-IDENTITY per §13.2) --
# The captured reference outputs (char_pow rounds 1-5, VG-8020 2026-07-14),
# copied verbatim from tools/sim_math_chain.py's POW_REF_ANCHORS. Sentinel
# strings: "OVERFLOW" -> Overflow (SPAN_ONLY, wording differs); "IFC" ->
# Illegal function call (SPAN_ONLY, wording differs); anything else is the
# exact reference-printed value, asserted via the ordinary differential path.
POW_REF_ANCHORS = [
    ("2",      40,     "1099511627776"),
    ("3",      20,     "3486784401"),
    ("2",      50,     "1.1258999068426E+15"),
    ("3",      33,     "5.5590605665554E+15"),
    ("7",      19,     "1.1398895185373E+16"),
    ("1.1",    20,     "6.7274999493256"),
    ("1.01",   100,    "2.7048138294216"),
    ("5",      27,     "7.4505805969238E+18"),
    ("5",      88,     "3.2311742677853E+61"),
    ("2",      127,    "1.7014118346047E+38"),
    ("2",      207,    "2.0568806966517E+62"),
    ("10",     31,     "1E+31"),
    ("10",     32,     "1E+32"),
    ("10",     47,     "1E+47"),
    ("0.1",    63,     "1E-63"),
    ("-2",     3,      "-8"),
    ("-2",     10,     "1024"),
    ("-1",     32767,  "-1"),
    ("-1",     32768,  "IFC"),
    ("10",     62,     "OVERFLOW"),
    ("10",     63,     "OVERFLOW"),
    ("2",      210,    "OVERFLOW"),
    ("-10",    63,     "OVERFLOW"),
    ("1E62",   1,      "OVERFLOW"),
    ("1E31",   3,      "OVERFLOW"),
    ("1E12",   5,      "1E+60"),
    ("0.5",    2000,   "0"),
    ("0.5",    -2000,  "OVERFLOW"),
    ("2",      -32768, "OVERFLOW"),
    ("10",     -63,    "OVERFLOW"),
    ("10",     -31,    "1E-31"),
    ("10",     -32,    "1E-32"),
]
POW_ANCHOR_EXPRS = [f"({x})^{n}" for x, n, _ in POW_REF_ANCHORS]
POW_ANCHOR_ERROR_EXPRS = {e for e, (_, _, w) in zip(POW_ANCHOR_EXPRS, POW_REF_ANCHORS)
                          if w in ("OVERFLOW", "IFC")}
EXPRS = EXPRS + POW_ANCHOR_EXPRS

# --- int-path random battery (15 fresh POSITIVE-y pairs, differential; -----
# frozen by seed 0xF00D, confirmed exact-match live against the VG-8020
# reference this session -- see the module docstring's "§13.2 scoped to
# positive-y" note for why negative-y draws are excluded here).
POW_INT_RANDOM = [
    ("1.01", 58), ("5", 60), ("10", -37), ("10", -39), ("5", 44),
    ("0.9", 46), ("10", -14), ("1.1", -46), ("1.0000001", 55), ("5", 15),
]
POW_INT_RANDOM_EXPRS = [f"({x})^{n}" for x, n in POW_INT_RANDOM]
EXPRS = EXPRS + POW_INT_RANDOM_EXPRS

# --- neg-y battery (truth-bound, ATN shape; §13.2's int-path structural ----
# cap `POW_INT_ROW_K*2^bitlen(n)`) + one informational-differential
# Overflow row (`.1^-63`, where BOTH sides genuinely overflow so the
# ordinary reference-tail compare -- SPAN_ONLY, wording differs -- holds).
POW_NEG_Y = [("3", -5), ("2", -40), ("2", -10), ("7", -10)]
POW_NEG_Y_EXPRS = [f"({x})^{n}" for x, n in POW_NEG_Y]
EXPRS = EXPRS + POW_NEG_Y_EXPRS
EXPRS = EXPRS + [".1^-63"]

# --- frac battery (truth-bound, ATN shape; §13.2's `12*max(1,|t|)+10` -----
# t-scaled cap): ~20 (x,y) pairs spanning |t|=|y*log x| from ~0.35 to ~129,
# confirmed live within cap against the VG-8020 reference this session.
POW_FRAC_XS = [
    ("2", "0.5"), ("7", "2.5"), ("10", "-2.5"), ("123.456", "7.89"),
    ("1.0000000000001", "1234.5"), ("0.5", "-100.25"), ("3", "3.3"),
    ("0.1", "5.5"), ("50", "1.7"), ("2", "10.5"), ("0.001", "3.5"),
    ("5.5", "-4.5"), ("1000", "5.5"), ("2.71828", "12.3"), ("0.9", "-25.5"),
    ("17", "6.7"), ("10", "-10.5"), ("4", "20.2"), ("100", "20.5"),
    ("13619.720868867", "-13.52985080"),
]
POW_FRAC_EXPRS = [f"({x})^({y})" for x, y in POW_FRAC_XS]
EXPRS = EXPRS + POW_FRAC_EXPRS

# --- frac-path §13.1 rule-4 domain rows -------------------------------------
# (-2)^2.5 -> Illegal function call (negative base, fractional exponent,
# SPAN_ONLY); 10^62.5 -> a finite value (truth-bound, same frac cap);
# 10^63.5 -> Overflow BOTH sides (SPAN_ONLY); 10^-70.5 -> the documented
# §12.9-bug deviation row: OURS correctly gives 0 (our EXP's own -147.36
# underflow floor), the REFERENCE throws its own buggy "Overflow" (a real
# disposition bug in the reference's EXP(-162.3), already documented at
# §12.9/§13.1 rule 4) -- asserted OURS=0 only, reference captured
# informationally, never asserted against (the two sides deliberately
# differ here, by design).
EXPRS = EXPRS + ["(-2)^2.5", "10^63.5"]
POW_DOMAIN_IFC = {"(-2)^2.5"}
POW_DOMAIN_OVERFLOW_BOTH = {"10^63.5"}
POW_FRAC_XS = POW_FRAC_XS + [("10", "62.5")]
POW_FRAC_EXPRS = POW_FRAC_EXPRS + ["(10)^(62.5)"]
EXPRS = EXPRS + ["(10)^(62.5)"]
POW_ZERO_VS_REF_OVERFLOW = {"10^-70.5"}
EXPRS = EXPRS + ["10^-70.5"]

# --- zero/one/type rows (§13.6) ---------------------------------------------
EXPRS = EXPRS + ["0^0", "0^2", "0^.5", "0^-1", "0^-.5", "5^0",
                 "1^123456789", "2!^3!"]
POW_DIVZERO = {"0^-1", "0^-.5"}

POW_ERROR_EXPRS = (POW_ANCHOR_ERROR_EXPRS | POW_DOMAIN_IFC
                   | POW_DOMAIN_OVERFLOW_BOTH | POW_DIVZERO)

# --- POW truth-bound row table: expr -> (x, y, cap, negate) -----------------
# Built from the neg-y/frac batteries above + the "-2^.5" grammar outlier
# (negate=True: the printed value is -truth_pow14(x,y), since a leading '-'
# negates the whole pow-chain, §13.1). compare()/the reporting section below
# route any expr found here through truth_pow14 + ulp_dist <= cap, never a
# reference-tail comparison (same ATN-shape framework as SQR/ATN/EXP/LOG).
POW_TRUTH_ROWS: dict[str, tuple[str, str, "decimal.Decimal", bool]] = {}
for _px, _pn in POW_NEG_Y:
    POW_TRUTH_ROWS[f"({_px})^{_pn}"] = (_px, str(_pn), pow_int_cap(_pn), False)
for _px, _py in POW_FRAC_XS:
    POW_TRUTH_ROWS[f"({_px})^({_py})"] = (_px, _py, pow_frac_cap(_px, _py), False)
POW_TRUTH_ROWS["-2^.5"] = ("2", "0.5", pow_frac_cap("2", "0.5"), True)

# =============================================================================
# SIN / COS / TAN battery (math pack slice 2d, docs/spec-basic-mathpack-
# slice2.md §14.8). Four row kinds:
#   * SIN_BROAD_XS/COS_BROAD_XS (~40 each, SHARED list -- both functions need
#     the same domain coverage): 0, small angles, the quadrant boundaries
#     (pi/4, pi/2, pi, 3pi/2, 2pi as 14-sig literals) and +-1 ulp straddles,
#     negatives (oddness/evenness rows), 100, 628.318...(=200*pi), 1000, plus
#     the §14.1 anchors -- asserted |zb-truth| <= SIN_ABS_TOL (absolute) +
#     the correctly-rounded floor (SIN_CR_FLOOR/COS_CR_FLOOR, |val|>=0.1).
#   * TAN_BAND_XS (~25): x giving 0.1<=|tan|<=10 -- asserted relative ulp
#     <= TAN_MAX_ULP.
#   * TAN_NEARPI2_XS / large-|x| rows (1.5707, 1.57079, 1000, 1E5, 1E8, 1E13,
#     §14.8): pinned to CAPTURED-ZEROBAS (TAN_KNOWN map), NOT truth -- the
#     near-pi/2 pole and the large-x reduction-accuracy falloff are
#     documented deviations (the SQR_KNOWN_FLOOR precedent), captured live
#     against the repack build (this probe's own characterization pass,
#     2026-07-14) rather than asserted against an independent truth oracle
#     that would need its own (unverified) modelling choices at these
#     magnitudes.
#   * FACTYP-leak rows (function-over-float/PEEK, single-vs-double literal
#     widen path): routed through the SAME truth-bound _MATH_FACTYP_LEAK_TRUTH
#     dict EXP/LOG/POW's own compound rows use (NOT the ATN precedent of a
#     direct reference-tail compare) -- SIN/COS/TAN's own reference is a weak
#     ~13-digit-pi 1980s poly (§1.1/§14.1), so a raw reference-tail compare on
#     a compound expression would fail on the REFERENCE's own imprecision,
#     not a zerobas bug, exactly the EXP/LOG finding this dict's own header
#     documents.
# =============================================================================
TRIG_BROAD_XS = [
    "0",
    "0.0001", "0.001", "0.01", "0.1",
    "0.5", "-0.5", "1", "-1", "1.5", "-1.5", "2", "-2", "3", "-3",
    ".7853981633974", "-.7853981633974",              # +-pi/4
    "1.5707963267949", "-1.5707963267949",             # +-pi/2
    "1.5707963267948", "1.5707963267950",              # pi/2 +-1 ulp
    "3.1415926535898", "-3.1415926535898",             # +-pi
    "3.1415926535897", "3.1415926535899",              # pi +-1 ulp
    "4.7123889803847", "-4.7123889803847",             # +-3pi/2
    "6.2831853071796",                                  # 2pi
    "10", "50", "100", "-100",
    "628.31853071796",                                  # 200*pi
    "1000", "-1000",
    "1.23456789", "12.3456789", "123.456789",
    "0.123456789",
]
SIN_BROAD_XS = TRIG_BROAD_XS
COS_BROAD_XS = TRIG_BROAD_XS
EXPRS = EXPRS + [f"sin({_x})" for _x in SIN_BROAD_XS]
EXPRS = EXPRS + [f"cos({_x})" for _x in COS_BROAD_XS]

# --- TAN band battery (~25, 0.1<=|tan|<=10, the well-conditioned band away
# from both TAN's zeros k*pi and poles pi/2+k*pi -- asserted relative ulp) --
TAN_BAND_XS = [
    "0.1", "-0.1", "0.5", "-0.5", ".7853981633974", "-.7853981633974",
    "0.9", "-0.9", "1", "-1", "1.1", "-1.1", "1.2", "-1.2", "1.4", "-1.4",
    "2", "-2", "2.5", "-2.5", "3", "-3",
    "100", "-100", "12345.678", "-12345.678", "1000000",
]
EXPRS = EXPRS + [f"tan({_x})" for _x in TAN_BAND_XS]

# --- TAN near-pi/2 + large-|x| rows (§14.8): pinned to captured-zerobas, NOT
# truth (the documented near-pole/large-x deviation, SQR_KNOWN_FLOOR shape).
TAN_NEARPI2_XS = ["1.5707", "1.57079", "1000", "1E5", "1E8", "1E13"]
# --- SIN/COS/TAN reduction-FLOOR rows (§14.5 sck_floor, dexp'>=15, |x| >=
# ~1.57E14): the kernel bails to the DESIGNED floor sv=0/cv=1 (SIN=0, COS=1,
# TAN=0) -- x is meaningless there (its own 14-sig ULP >= ~10 rad), so these
# are pinned to the DESIGNED floor values, NOT truth (which is garbage) and
# NOT the reference (which returns its own 0). Added 2026-07-14 after the
# slice-2d adversarial review flagged that NOTHING exercised this path (no
# gate/sim/unit row) -- exactly the project's matrix-invisible hiding spot.
TRIG_FLOOR_XS = ["1E15", "-1E15", "2E14"]
TRIG_FLOOR_KNOWN = {}
for _x in TRIG_FLOOR_XS:
    for _fn, _v in (("sin", "0"), ("cos", "1"), ("tan", "0")):
        TRIG_FLOOR_KNOWN[f"{_fn}({_x})"] = _v
        EXPRS = EXPRS + [f"{_fn}({_x})"]
EXPRS = EXPRS + [f"tan({_x})" for _x in TAN_NEARPI2_XS]
# Filled from this probe's own --zb-machine characterization run against the
# repack build (2026-07-14) -- captured-zerobas values, asserted verbatim
# (never re-derived, never asserted against the reference or a truth
# oracle): a regression pin, not a correctness proof, per §14.8's own
# framing ("pin to captured-zerobas ... NOT truth").
TAN_KNOWN = {
    "tan(1.5707)":  "10381.327417571",
    "tan(1.57079)": "158057.91341853",
    "tan(1000)":    "1.4703241557027",
    "tan(1E5)":     "-.035771662952895",
    "tan(1E8)":     "-2.5637789067217",
    "tan(1E13)":    "-.032273197819333",
}

# --- SIN/COS/TAN FACTYP-leak (§14.8): function-over-float (result must stay
# DOUBLE), single-vs-double literal input widen path, function-over-PEEK.
# Routed through _MATH_FACTYP_LEAK_TRUTH below (the EXP/LOG/POW precedent),
# NOT a direct reference-tail compare (see this section's header comment).
EXPRS = EXPRS + ["sin(1)+0.5", "cos(1)+0.5", "tan(1)+0.5",
                 "sin(0.5!)", "cos(0.5#)", "tan(peek(0))"]
_MATH_FACTYP_LEAK_TRUTH["sin(1)+0.5"] = lambda: truth_sin14("1") + D("0.5")
_MATH_FACTYP_LEAK_TRUTH["cos(1)+0.5"] = lambda: truth_cos14("1") + D("0.5")
_MATH_FACTYP_LEAK_TRUTH["tan(1)+0.5"] = lambda: truth_tan14("1") + D("0.5")
_MATH_FACTYP_LEAK_TRUTH["sin(0.5!)"] = lambda: truth_sin14("0.5")
_MATH_FACTYP_LEAK_TRUTH["cos(0.5#)"] = lambda: truth_cos14("0.5")
_MATH_FACTYP_LEAK_TRUTH["tan(peek(0))"] = lambda: truth_tan14("243")  # this
                                          # machine's PEEK(0)=243, §12.7

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
             "sqr(-1)", "sqr(-1e-9)", "sqr(-4)",
             "log(0)", "log(-1)", "exp(146)", "exp(200)", "exp(1000)"} \
            | POW_ERROR_EXPRS | {".1^-63"}

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

# --- EXP/LOG pure-call matchers: same shape/rationale as _SQR_PURE_RE/ ------
# _ATN_PURE_RE above -- route a plain `exp(x)`/`log(x)` call to the truth
# assertion, never the reference; the FACTYP-leak compounds (`exp(1)+0.5`,
# `log(2!)`, `exp(peek(0))`, ...) and the SPAN_ONLY domain/overflow rows
# never match (the latter excluded explicitly in compare(), same as sqr/atn).
_EXP_PURE_RE = re.compile(r"^exp\((-?[0-9.eEdD+-]+)\)$")
_LOG_PURE_RE = re.compile(r"^log\((-?[0-9.eEdD+-]+)\)$")


def _exp_arg(expr: str):
    """Return the Decimal argument if `expr` is a pure `exp(x)` call
    (x a bare numeric literal), else None."""
    m = _EXP_PURE_RE.match(expr)
    if not m:
        return None
    lit = m.group(1).replace("D", "E").replace("d", "e")
    try:
        return D(lit)
    except decimal.InvalidOperation:
        return None


def _log_arg(expr: str):
    """Return the Decimal argument if `expr` is a pure `log(x)` call
    (x a bare numeric literal), else None."""
    m = _LOG_PURE_RE.match(expr)
    if not m:
        return None
    lit = m.group(1).replace("D", "E").replace("d", "e")
    try:
        return D(lit)
    except decimal.InvalidOperation:
        return None

# --- SIN/COS/TAN pure-call matchers: same shape/rationale as _sqr_arg/ ------
# _atn_arg/_exp_arg/_log_arg above -- route a plain `sin(x)`/`cos(x)`/
# `tan(x)` call to the truth/band assertion, never the reference; the
# FACTYP-leak compounds (`sin(1)+0.5`, `tan(peek(0))`, ...) never match.
_SIN_PURE_RE = re.compile(r"^sin\((-?[0-9.eEdD+-]+)\)$")
_COS_PURE_RE = re.compile(r"^cos\((-?[0-9.eEdD+-]+)\)$")
_TAN_PURE_RE = re.compile(r"^tan\((-?[0-9.eEdD+-]+)\)$")


def _sin_arg(expr: str):
    """Return the Decimal argument if `expr` is a pure `sin(x)` call
    (x a bare numeric literal), else None."""
    m = _SIN_PURE_RE.match(expr)
    if not m:
        return None
    lit = m.group(1).replace("D", "E").replace("d", "e")
    try:
        return D(lit)
    except decimal.InvalidOperation:
        return None


def _cos_arg(expr: str):
    """Return the Decimal argument if `expr` is a pure `cos(x)` call
    (x a bare numeric literal), else None."""
    m = _COS_PURE_RE.match(expr)
    if not m:
        return None
    lit = m.group(1).replace("D", "E").replace("d", "e")
    try:
        return D(lit)
    except decimal.InvalidOperation:
        return None


def _tan_arg(expr: str):
    """Return the Decimal argument if `expr` is a pure `tan(x)` call
    (x a bare numeric literal), else None."""
    m = _TAN_PURE_RE.match(expr)
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
    # EXP/LOG FACTYP-leak into a typed INT var (§12.7): A%=EXP(1) truncates
    # 2.718... to 2, A%=LOG(100) truncates 4.605... to 4 -- both sides agree
    # trivially at this coarse an integer regardless of the 14th-digit
    # accuracy difference between zerobas and the reference (same reasoning
    # as the SQR/ATN rows above).
    'a%=exp(1):print"[";a%;"]"',
    'a%=log(100):print"[";a%;"]"',
    # POW FACTYP-leak (§13.6): int^int stored in typed int vars (A%=2:B%=3:
    # A%^B% round-trips through the int-store path), a double result
    # truncated into an int var (2^3=8 exactly, no rounding ambiguity), and
    # the a#*a# compound above (routed via _MATH_FACTYP_LEAK_TRUTH, not a
    # raw reference compare -- see that dict's own comment).
    'a%=2:b%=3:print"[";a%^b%;"]"',
    'a%=2^3:print"[";a%;"]"',
    'a#=2^.5:print"[";a#*a#;"]"',
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
        ok = check_pow_token(args.machine) and ok
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
        if expr in _MATH_FACTYP_LEAK_TRUTH:
            zb_val = parse_basic_number(zb_span)
            if zb_val is None:
                return False
            d = ulp_dist(zb_val, _MATH_FACTYP_LEAK_TRUTH[expr]())
            return d is not None and d <= _MATH_FACTYP_LEAK_ULP
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
        exp_x = _exp_arg(expr) if expr not in SPAN_ONLY else None
        if exp_x is not None:
            # §12.1/§12.7 (documented bounded deviation, same shape as ATN):
            # the oracle is mathematical truth, asserted to a BOUND
            # (<= EXP_MAX_ULP) rather than == truth.
            zb_val = parse_basic_number(zb_span)
            if zb_val is None:
                return False
            truth = truth_exp14(exp_x)
            if not isinstance(truth, D):
                return False    # defensive -- the battery excludes overflow
            d = ulp_dist(zb_val, truth)
            return d is not None and d <= EXP_MAX_ULP
        log_x = _log_arg(expr) if expr not in SPAN_ONLY else None
        if log_x is not None:
            zb_val = parse_basic_number(zb_span)
            if zb_val is None:
                return False
            d = ulp_dist(zb_val, truth_log14(log_x))
            return d is not None and d <= LOG_MAX_ULP
        if expr in POW_ZERO_VS_REF_OVERFLOW:
            # §13.1 rule 4's documented §12.9-bug deviation row: OURS must
            # be exactly 0 (our EXP's own underflow floor); the reference's
            # own "Overflow" here is ITS disposition bug (captured
            # informationally below, never asserted against).
            zb_val = parse_basic_number(zb_span)
            return zb_val is not None and zb_val == 0
        if expr in POW_TRUTH_ROWS:
            # neg-y / frac / the "-2^.5" grammar outlier (documented bounded
            # deviation, §13.2 -- truth-bound, NOT reference-compared).
            px, py, cap, negate = POW_TRUTH_ROWS[expr]
            zb_val = parse_basic_number(zb_span)
            if zb_val is None:
                return False
            truth = truth_pow14(px, py)
            if negate:
                truth = -truth
            d = ulp_dist(zb_val, truth)
            return d is not None and d <= cap
        if expr in TRIG_FLOOR_KNOWN:
            # §14.5 sck_floor: pinned to the DESIGNED floor value (0/1/0), not
            # truth or reference (both meaningless at |x| >= ~1.57E14).
            zb_val = parse_basic_number(zb_span)
            return zb_val is not None \
                and zb_val == parse_basic_number(TRIG_FLOOR_KNOWN[expr])
        sin_x = _sin_arg(expr) if expr not in SPAN_ONLY else None
        if sin_x is not None:
            # §14.2/§14.8 (documented bounded deviation, ATN/EXP/LOG shape):
            # SIN is bounded in [-1,1], so the assertion is an ABSOLUTE-error
            # bound vs mathematical truth, not a ulp bound (relative ulp
            # blows up near SIN's own zeros -- inherent, not a defect).
            zb_val = parse_basic_number(zb_span)
            if zb_val is None:
                return False
            return abs(zb_val - truth_sin14(sin_x)) <= SIN_ABS_TOL
        cos_x = _cos_arg(expr) if expr not in SPAN_ONLY else None
        if cos_x is not None:
            zb_val = parse_basic_number(zb_span)
            if zb_val is None:
                return False
            return abs(zb_val - truth_cos14(cos_x)) <= SIN_ABS_TOL
        tan_x = _tan_arg(expr) if expr not in SPAN_ONLY else None
        if tan_x is not None:
            zb_val = parse_basic_number(zb_span)
            if zb_val is None:
                return False
            if expr in TAN_KNOWN:
                # §14.8: near-pi/2 pole + large-|x| reduction falloff --
                # pinned to captured-zerobas, NOT truth (this battery's own
                # header comment; the SQR_KNOWN_FLOOR precedent).
                return zb_val == parse_basic_number(TAN_KNOWN[expr])
            truth = truth_tan14(tan_x)
            if not isinstance(truth, D):
                return False    # defensive -- the band battery excludes the
                                # exact-pole case
            d = ulp_dist(zb_val, truth)
            return d is not None and d <= TAN_MAX_ULP
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
    exp_ref_deviations = []  # same, for EXP (§12.7's documented-deviation report)
    log_ref_deviations = []  # same, for LOG
    exp_zb_by_x = {}         # Decimal(x) -> zb_val, for the accuracy summary below
    log_zb_by_x = {}
    pow_worst = D(0); pow_exact = 0; pow_total = 0   # POW accuracy summary
    pow_ref_deviations = []  # (expr, x, y, ref_val, truth) -- informational
    sin_zb_by_x = {}         # Decimal(x) -> zb_val, for the accuracy summary
    cos_zb_by_x = {}         # + oddness/evenness cross-check below
    sin_ref_deviations = []  # (expr, x, ref_val, truth) -- informational
    cos_ref_deviations = []
    tan_worst = D(0); tan_exact = 0; tan_total = 0   # TAN band accuracy summary
    tan_ref_deviations = []
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
        exp_x = _exp_arg(expr) if expr not in SPAN_ONLY else None
        if exp_x is not None:
            zb_val = parse_basic_number(result_span(zb_raw))
            if zb_val is not None:
                exp_zb_by_x[exp_x] = zb_val
            ref_val = parse_basic_number(ref_span)
            truth = truth_exp14(exp_x)
            if ref_val is not None and isinstance(truth, D) and ref_val != truth:
                exp_ref_deviations.append((expr, exp_x, ref_val, truth))
        log_x = _log_arg(expr) if expr not in SPAN_ONLY else None
        if log_x is not None:
            zb_val = parse_basic_number(result_span(zb_raw))
            if zb_val is not None:
                log_zb_by_x[log_x] = zb_val
            ref_val = parse_basic_number(ref_span)
            truth = truth_log14(log_x)
            if ref_val is not None and ref_val != truth:
                log_ref_deviations.append((expr, log_x, ref_val, truth))
        if expr in POW_TRUTH_ROWS:
            px, py, _cap, negate = POW_TRUTH_ROWS[expr]
            zb_val = parse_basic_number(result_span(zb_raw))
            truth = truth_pow14(px, py)
            if negate:
                truth = -truth
            if zb_val is not None:
                d = ulp_dist(zb_val, truth)
                if d is not None:
                    pow_total += 1
                    if d == 0:
                        pow_exact += 1
                    if d > pow_worst:
                        pow_worst = d
            ref_val = parse_basic_number(ref_span)
            if ref_val is not None and ref_val != truth:
                pow_ref_deviations.append((expr, px, py, ref_val, truth))
        sin_x = _sin_arg(expr) if expr not in SPAN_ONLY else None
        if sin_x is not None:
            zb_val = parse_basic_number(result_span(zb_raw))
            if zb_val is not None:
                sin_zb_by_x[sin_x] = zb_val
            ref_val = parse_basic_number(ref_span)
            truth = truth_sin14(sin_x)
            if ref_val is not None and ref_val != truth:
                sin_ref_deviations.append((expr, sin_x, ref_val, truth))
        cos_x = _cos_arg(expr) if expr not in SPAN_ONLY else None
        if cos_x is not None:
            zb_val = parse_basic_number(result_span(zb_raw))
            if zb_val is not None:
                cos_zb_by_x[cos_x] = zb_val
            ref_val = parse_basic_number(ref_span)
            truth = truth_cos14(cos_x)
            if ref_val is not None and ref_val != truth:
                cos_ref_deviations.append((expr, cos_x, ref_val, truth))
        tan_x = _tan_arg(expr) if expr not in SPAN_ONLY and expr not in TAN_KNOWN else None
        if tan_x is not None:
            zb_val = parse_basic_number(result_span(zb_raw))
            truth = truth_tan14(tan_x)
            if zb_val is not None and isinstance(truth, D):
                d = ulp_dist(zb_val, truth)
                if d is not None:
                    tan_total += 1
                    if d == 0:
                        tan_exact += 1
                    if d > tan_worst:
                        tan_worst = d
            ref_val = parse_basic_number(ref_span)
            if ref_val is not None and isinstance(truth, D) and ref_val != truth:
                tan_ref_deviations.append((expr, tan_x, ref_val, truth))

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

    # --- EXP documented bounded-deviation summary (§12.1/§12.7, same shape
    # as ATN's above): zerobas EXP is asserted to <= EXP_MAX_ULP of truth,
    # plus a battery-wide correctly-rounded floor (drift tripwire).
    exp_worst = D(0); exp_exact = 0; exp_total = 0
    for x, zb_val in exp_zb_by_x.items():
        truth = truth_exp14(x)
        if not isinstance(truth, D):
            continue
        d = ulp_dist(zb_val, truth)
        if d is None:
            continue
        exp_total += 1
        if d == 0:
            exp_exact += 1
        if d > exp_worst:
            exp_worst = d
    if exp_total:
        print(f"\n--- EXP accuracy vs mathematical truth ({exp_total} pure exp "
              f"inputs) -- bound = {EXP_MAX_ULP} ulp (§12.1) ---")
        print(f"  correctly-rounded (== truth): {exp_exact}/{exp_total}; "
              f"worst deviation: {exp_worst} ulp (bound {EXP_MAX_ULP}).")
        if exp_exact < EXP_EXACT_FLOOR:
            print(f"FAIL  EXP correctly-rounded count {exp_exact} < floor "
                  f"{EXP_EXACT_FLOOR} -- uniform accuracy regression (all still "
                  "within bound but the exact-count collapsed).")
            ok = False
        print("  DOCUMENTED bounded deviation (§12.1, same framework as ATN's "
              "§11.10): the 14-digit table-reduction+Horner chain is not "
              "strictly correctly-rounded; per-input never-worse-than-"
              "reference is NOT asserted (the reference is itself 3-45 ulp "
              "off truth here, per the characterization).")

    if exp_ref_deviations:
        print(f"\n--- EXP reference-deviation report ({len(exp_ref_deviations)}/"
              f"{len(EXP_BROAD_XS)}) -- INFORMATIONAL ---")
        print("(inputs where the reference ROM's own EXP misses mathematical "
              "truth; the reference is a low-accuracy 1980s poly, mean -3 ulp, "
              "worst -45 @x=88 per §1.1/§12.1. Never asserted against.)")
        for expr, x, ref_val, truth in exp_ref_deviations:
            print(f"  {expr:<26} reference={ref_val!s:<20} truth={truth!s}")

    # --- LOG documented bounded-deviation summary (§12.1/§12.7) -------------
    log_worst = D(0); log_exact = 0; log_total = 0
    for x, zb_val in log_zb_by_x.items():
        d = ulp_dist(zb_val, truth_log14(x))
        if d is None:
            continue
        log_total += 1
        if d == 0:
            log_exact += 1
        if d > log_worst:
            log_worst = d
    if log_total:
        print(f"\n--- LOG accuracy vs mathematical truth ({log_total} pure log "
              f"inputs) -- bound = {LOG_MAX_ULP} ulp (§12.1) ---")
        print(f"  correctly-rounded (== truth): {log_exact}/{log_total}; "
              f"worst deviation: {log_worst} ulp (bound {LOG_MAX_ULP}).")
        if log_exact < LOG_EXACT_FLOOR:
            print(f"FAIL  LOG correctly-rounded count {log_exact} < floor "
                  f"{LOG_EXACT_FLOOR} -- uniform accuracy regression (all still "
                  "within bound but the exact-count collapsed).")
            ok = False
        print("  DOCUMENTED bounded deviation (§12.1): every >2-ulp case is in "
              "the j=8 FOLD path (x in [0.866,1)) where den=m'+1 inherently "
              "spans 15 digits and d(r)/d(s)=2 doubles the division's own "
              "rounding -- the same extended-precision wall as the division "
              "deviation/SQR floor. Per-input never-worse-than-reference is "
              "NOT asserted (the reference is itself 1-5 ulp off truth here).")

    if log_ref_deviations:
        print(f"\n--- LOG reference-deviation report ({len(log_ref_deviations)}/"
              f"{len(LOG_BROAD_XS)}) -- INFORMATIONAL ---")
        print("(inputs where the reference ROM's own LOG misses mathematical "
              "truth; mean -0.45 ulp, worst -5 per §1.1/§12.1. Never asserted "
              "against.)")
        for expr, x, ref_val, truth in log_ref_deviations:
            print(f"  {expr:<26} reference={ref_val!s:<20} truth={truth!s}")

    # --- POW documented bounded-deviation summary (§13.2/§13.6, same shape --
    # as ATN/EXP/LOG's above): the neg-y/frac/"-2^.5" truth-bound rows are
    # asserted to their OWN per-row cap (POW_INT_ROW_K*2^bitlen(n) or
    # POW_FRAC_T_K*max(1,|t|)+POW_FRAC_T_C), not a single flat bound -- this
    # summary reports the aggregate worst/exact-count across all of them.
    if pow_total:
        print(f"\n--- POW accuracy vs mathematical truth ({pow_total} "
              "truth-bound neg-y/frac/grammar-outlier inputs) -- §13.2 "
              "per-row caps (not a flat bound) ---")
        print(f"  correctly-rounded (== truth): {pow_exact}/{pow_total}; "
              f"worst deviation: {pow_worst} ulp (each row's own cap held "
              "independently -- see per-row PASS/FAIL above).")
        print("  DOCUMENTED bounded deviation (§13.2): the int path's own "
              "squaring-amplification error (structural, the reference's "
              "own, not ours to fix) and the frac path's EXP(y*LOG(x)) "
              "chain deviation (scales with |t|=|y*log x|). Per-input "
              "never-worse-than-reference is NOT asserted (§2 relaxation, "
              "the ATN/EXP/LOG precedent).")
    if pow_ref_deviations:
        print(f"\n--- POW reference-deviation report ({len(pow_ref_deviations)}) "
              "-- INFORMATIONAL ---")
        print("(inputs where the reference ROM's own POW misses mathematical "
              "truth, incl. the `10^-70.5` row where the reference's own "
              "EXP(-162.3) throws a disposition-bug Overflow that zerobas "
              "correctly avoids -- §12.9. Never asserted against.)")
        for expr, x, y, ref_val, truth in pow_ref_deviations:
            print(f"  {expr:<26} x={x:<18} y={y:<12} "
                  f"reference={ref_val!s:<20} truth={truth!s}")

    # --- SIN/COS documented bounded-deviation summary (§14.2/§14.8, ABSOLUTE
    # error -- SIN/COS are bounded in [-1,1]): worst abs error + correctly-
    # rounded (abs<=1 ulp, |val|>=.1) floor, same drift-tripwire shape as
    # ATN_EXACT_FLOOR/EXP_EXACT_FLOOR/LOG_EXACT_FLOOR.
    for name, zb_by_x, truth_fn, tol, floor in (
            ("SIN", sin_zb_by_x, truth_sin14, SIN_ABS_TOL, SIN_CR_FLOOR),
            ("COS", cos_zb_by_x, truth_cos14, SIN_ABS_TOL, COS_CR_FLOOR)):
        worst_abs = D(0); worst_x = None; cr = 0; tot = 0
        for x, zb_val in zb_by_x.items():
            truth = truth_fn(x)
            ae = abs(zb_val - truth)
            if ae > worst_abs:
                worst_abs, worst_x = ae, x
            if abs(truth) >= D("0.1"):
                tot += 1
                d = ulp_dist(zb_val, truth)
                if d is None or d <= 1:
                    cr += 1
        if tot:
            pct = 100.0 * cr / tot
            print(f"\n--- {name} accuracy vs mathematical truth "
                  f"({len(zb_by_x)} pure {name.lower()} inputs) -- bound = "
                  f"abs<={tol} (§14.2) ---")
            print(f"  worst abs error {worst_abs:.2e} @ x={worst_x}; "
                  f"correctly-rounded (abs<=1 ulp, |val|>=.1) {cr}/{tot} "
                  f"({pct:.1f}%).")
            if cr < floor:
                print(f"FAIL  {name} correctly-rounded count {cr} < floor "
                      f"{floor} -- uniform accuracy regression (all still "
                      "within the abs bound but the exact-count collapsed).")
                ok = False
            print(f"  DOCUMENTED bounded deviation (§14.2, same framework as "
                  "ATN/EXP/LOG's own): the reduction+minimax-Horner chain is "
                  "not strictly correctly-rounded everywhere; per-input "
                  "never-worse-than-reference is NOT asserted (academic here "
                  "-- the reference is 3-6 orders worse everywhere it "
                  "matters, §14.1).")

    # --- SIN/COS oddness/evenness cross-check (§14.2): SIN(-x)=-SIN(x) /
    # COS(-x)=COS(x) for every x in the broad battery whose negative mirror
    # is ALSO present -- verified from the already-collected zb values (no
    # extra machine round-trip), same shape as ATN's own oddness check above.
    # By construction sincos_kernel computes on a=|x| and the wrappers apply
    # the sign last (sub/fp_sin.asm §14.5/§14.6), so this should hold EXACTLY.
    sin_odd_checked = 0
    for x, zb_val in list(sin_zb_by_x.items()):
        if -x in sin_zb_by_x:
            sin_odd_checked += 1
            if sin_zb_by_x[-x] != -zb_val:
                print(f"FAIL  oddness: sin({x}) = {zb_val}  but  "
                      f"sin({-x}) = {sin_zb_by_x[-x]}  (expected {-zb_val})")
                ok = False
    if sin_odd_checked:
        print(f"\nSIN oddness cross-check: {sin_odd_checked // 2} mirrored "
              "pair(s) verified sin(-x) == -sin(x)")
    cos_even_checked = 0
    for x, zb_val in list(cos_zb_by_x.items()):
        if -x in cos_zb_by_x:
            cos_even_checked += 1
            if cos_zb_by_x[-x] != zb_val:
                print(f"FAIL  evenness: cos({x}) = {zb_val}  but  "
                      f"cos({-x}) = {cos_zb_by_x[-x]}  (expected {zb_val})")
                ok = False
    if cos_even_checked:
        print(f"COS evenness cross-check: {cos_even_checked // 2} mirrored "
              "pair(s) verified cos(-x) == cos(x)")

    if sin_ref_deviations:
        print(f"\n--- SIN reference-deviation report ({len(sin_ref_deviations)}/"
              f"{len(SIN_BROAD_XS)}) -- INFORMATIONAL ---")
        print("(inputs where the reference ROM's own SIN misses mathematical "
              "truth; the reference has a weak ~13-digit stored pi, §1.1/"
              "§14.1. Never asserted against.)")
        for expr, x, ref_val, truth in sin_ref_deviations:
            print(f"  {expr:<26} reference={ref_val!s:<20} truth={truth!s}")
    if cos_ref_deviations:
        print(f"\n--- COS reference-deviation report ({len(cos_ref_deviations)}/"
              f"{len(COS_BROAD_XS)}) -- INFORMATIONAL ---")
        print("(inputs where the reference ROM's own COS misses mathematical "
              "truth; catastrophic near pi/2, §1.1/§14.1. Never asserted "
              "against.)")
        for expr, x, ref_val, truth in cos_ref_deviations:
            print(f"  {expr:<26} reference={ref_val!s:<20} truth={truth!s}")

    # --- TAN documented bounded-deviation summary (§14.2/§14.8, relative ulp,
    # 0.1<=|tan|<=10 band only -- the near-pi/2/large-|x| rows are pinned to
    # captured-zerobas above, NOT included here).
    if tan_total:
        print(f"\n--- TAN accuracy vs mathematical truth ({tan_total} "
              "band inputs, 0.1<=|tan|<=10) -- bound = "
              f"{TAN_MAX_ULP} ulp (§14.2) ---")
        print(f"  correctly-rounded (== truth): {tan_exact}/{tan_total}; "
              f"worst deviation: {tan_worst} ulp (bound {TAN_MAX_ULP}).")
        print("  DOCUMENTED bounded deviation (§14.2): TAN(x)=SIN(x)/COS(x) "
              "bit-for-bit (§1.2); the band bound reflects the one "
              "correctly-rounded fp_div on top of SIN/COS's own abs-error "
              "envelope, amplified near the band edges (|sin| or |cos| "
              "~=0.1). Per-input never-worse-than-reference is NOT asserted "
              "(academic -- the reference is 4+ orders worse here, §14.1).")
    if tan_ref_deviations:
        print(f"\n--- TAN reference-deviation report ({len(tan_ref_deviations)}/"
              f"{len(TAN_BAND_XS)}) -- INFORMATIONAL ---")
        print("(inputs where the reference ROM's own TAN misses mathematical "
              "truth; up to 4e4+ ulp off truth in this project's own "
              "characterization, §14.1. Never asserted against.)")
        for expr, x, ref_val, truth in tan_ref_deviations:
            print(f"  {expr:<26} reference={ref_val!s:<20} truth={truth!s}")

    print("\nALL PASS — SQR is correctly-rounded (== mathematical truth) over "
          "the broad battery except the pinned near-tie precision floor "
          f"({', '.join(SQR_KNOWN_FLOOR)}, where zerobas ties the reference, "
          f"never worse); ATN is within {ATN_MAX_ULP} ulp of truth over its "
          "broad battery (documented bounded deviation, user sign-off -- ATN's "
          "reference is the one ~correctly-rounded case, and our 14-digit chain "
          "matches its <=2-ulp envelope), oddness holds exactly; EXP is within "
          f"{EXP_MAX_ULP} ulp and LOG within {LOG_MAX_ULP} ulp of truth over "
          "their own broad batteries (documented bounded deviation, §12.1 -- "
          "both references are low-accuracy on these functions, so our chain "
          "beats them in aggregate even where a per-input tie isn't asserted); "
          "POW's positive-y integer path is REFERENCE-IDENTICAL BIT-FOR-BIT "
          "(§13.2), and its neg-y/frac/grammar-outlier rows hold their own "
          f"per-row truth-bound caps (documented bounded deviation, §13.2); "
          f"SIN/COS are within {SIN_ABS_TOL} absolute of truth over their "
          "broad battery and TAN within "
          f"{TAN_MAX_ULP} ulp over its well-conditioned band (documented "
          "bounded deviation, §14.2 -- the reference is 3-6 orders worse "
          "here via its own weak stored pi), oddness/evenness hold exactly, "
          "and the near-pi/2/large-|x| rows are pinned to captured-zerobas "
          "(§14.8); "
          "every reference ROM's own bias is documented above, never asserted "
          "against" if ok
          else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
