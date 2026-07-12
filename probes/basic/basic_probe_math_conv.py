#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Math pack slice 1a probe — ABS/SGN/INT/FIX/CINT/CSNG/CDBL
(docs/spec-basic-math-pack.md §9.4).

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
   zerobas (repack build) and asserts equality.

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

import basic_probe_crunch as C  # noqa: E402  (reuse MACHINE/TXTTAB/tokens)
import omsx_repl                # noqa: E402  (typing-free KEYBUF REPL driver)

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
]

# Cases whose TAIL legitimately differs (zerobas's own lowercase D-2-style
# Overflow wording vs the reference's) -- compare only the bracket span
# (both sides must still have SOME tail, i.e. genuinely aborted).
# cint(...) Overflow cases: TAIL differs by wording (zerobas's own lowercase
# D-2-style message); span (the value/continuation shape) still must match.
SPAN_ONLY = {"cint(32768)", "cint(-32769)", "cint(40000.5)", "cint(32768.1)"}

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
        if kind == "raw":
            return ref_span is not None and ref_span == zb_span
        if expr in SPAN_ONLY:
            return ref_tail is not None and zb_tail is not None \
                and ref_span == zb_span
        return ref_tail is not None and ref_tail == zb_tail

    verdicts, ref_raws, zb_raws = omsx_repl.run_differential(
        args.machine, args.zb_machine, specs, compare,
        batch=not args.boot_per_case, reset=("NEW", "CLS"))

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

    print("\nALL PASS — math pack slice 1a is reference-identical" if ok
          else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
