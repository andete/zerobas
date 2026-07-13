#!/usr/bin/env python3

"""Float ARITHMETIC probe — characterise, then differentially prove, MSX-BASIC
arithmetic over int/single/double operands (Phase-3 float pack F2;
docs/spec-basic-float-core.md §1 F2 + D-C).

Each case types  PRINT "[";<expr>;"]"  in direct mode and captures the SCREEN 0
name table (same bracket technique as basic_probe_float_fmt.py). Two captures
per case:

- the bracket SPAN (text between the last '[' and the following ']') — the
  printed value, spaces exact;
- the screen TAIL (all rows between the echoed command line and the closing
  'Ok' prompt) — this additionally pins the ERROR surface: whether division by
  zero / runtime overflow prints a message, whether the statement aborts
  (no ']' ever prints) or continues with a substitute value, and what that
  value is.

The matrix covers: result-type promotion for + - * / (int op int -> int,
'/' always float, mixed -> wider, int overflow -> single), BCD rounding at
both precisions (including half-way ties), unary minus, parentheses, runtime
exponent walls (overflow/underflow), division by zero, MSX-signed \\ and MOD
(the D-C signed-int migration), float->int conversion in \\ / MOD / logical /
function-argument contexts (rounding mode + domain), and relationals over
floats (compound + mixed precision).

Characterisation mode (default): print the reference's exact output per case.
Differential mode (--zb-machine): also run zerobas (repack build) and assert
equality — TAIL-equal by default; cases in SPAN_ONLY compare just the bracket
span (zerobas prints its own lowercase error wording, a D-2-style divergence,
so message text is excluded there; the value/continuation shape is not).

Clean-room: observed outputs only; the reference ROM is a black box.
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))

import argparse

import omsx_repl  # typing-free KEYBUF-injection REPL driver (harness rework S2)

REF_MACHINE = "Philips_VG_8020"

# The F2 matrix. Each entry is an expression E, typed as  print "[";E;"]".
# Grouped by the contract facet it pins (spec §1 F2, §6 D-C).
EXPRS = [
    # int regression anchors (semantics unchanged by F2)
    "1+2", "10-4", "6*7", "7-9", "2=2", "2>3", "7<>7",
    # '/' becomes real division (retires the int-quotient divergence)
    "7/2", "10/2", "1/3", "2/3", "-7/2", "1/8",
    # '/' result-precision matrix + division rounding pins (1/512 = .001953125
    # is a half-way tie at 6 significant digits)
    "2!/3!", "2#/3", "2/3#", "2#/3#", "1!/512!", "1#/512#",
    "1!/3!*3", "1/3*3",
    # + - * over type combos (promotion visibility via digit count)
    "1+2.5", "1.5+1", "1+2.5#", "1.5!+1#", "2*3.5", "2.5*4", "2.5#*4",
    "2.5-1.5", ".3-.1", ".1+.2",
    # int overflow promotes to single (D-C)
    "32767+1", "-32768-1", "32767+32767", "32000+32000", "-32768-32768",
    "32767*2", "300*300", "3125*625", "32767*32767", "-32768*2", "-200*300",
    # BCD rounding pins: half-way ties + carry-out + general rounding
    "3125!*625!", "1.000005!+1", "1.000025!+1", "1000000!+1", "999999!+1",
    "123456!*654321!", "2.00001!-1.000005!", "12345678#*87654321#",
    "99999999999999#+1", "1.000000000000005#+1",
    # cross-precision arithmetic (single promoted into a double op)
    "2!/3!-2#/3#", "2#/3#*1!", "1!*2#/3#", "1!/3!+0#", "1e10+1",
    # unary minus + parentheses + precedence over floats
    "-1.5*2", "-(1.5+2.5)", "2--3.5", "(1+2)*3.5", "2+3*4.5",
    "1.5+2.5*3.5-4.5/2", "(1.5+2.5)*(3.5-1.5)",
    # runtime exponent walls (overflow / underflow surfaces)
    "1e62*9", "1e62*10", "1e40*1e40", "-1e40*1e40", "9e62+9e62",
    "1e-40*1e-32", "-1e-40*1e-32", "1e-40/1e30", "1d62*10", "1e62+0#",
    # zero forms
    "0*-1", "0!/5", "0/3!", "0.0+0",
    # division by zero (error surface, D-C oracle question)
    "1/0", "1!/0", "1#/0", "0/0", "1\\0", "1 mod 0",
    # MSX-signed \ and MOD (D-C: today's unsigned divergences retire)
    "7\\2", "-7\\2", "7\\-2", "-7\\-2", "7 mod 2", "-7 mod 2", "7 mod -2",
    "-7 mod -2", "32767\\-1", "-32768\\-1",
    # float operands into \ / MOD: int conversion (rounding mode + domain)
    "7.5\\2", "2.5\\1", "3.5\\1", "-2.5\\1", "7.9 mod 3",
    "40000!\\2", "40000 mod 7",
    # relationals over floats (+ compound forms, mixed precision)
    "1.5=1.5", "1.5>1.4", "1.5<1.4", "1.5<>1.5", "1.5>=1.5", "1.5<=1.4",
    "1=1.0", "-1.5<-1", ".1!=.1#", "2!/3!=2#/3#", "1!/2!=1#/2#",
    "2>1.5", "(1.5>1)+5",
    # logical ops over floats (int conversion + the -32768..65535 domain)
    "not 1.5", "not 2.5", "1.5 and 3", "1.5 or 4", "40000! and 65535",
    "100000! and 1",
    # int-context functions over float exprs (FACTYP-protocol pins; the F1
    # review lesson: always include a function-over-float case)
    "hex$(2.5*2)", "hex$(2.5)", "hex$(3.5)",
    # --- round-2 follow-ups (disambiguate the round-1 findings) -------------
    # float->int conversion mode: 2.5->2 / 3.5->3 fits BOTH truncation and
    # round-half-down; 2.9 decides (truncate -> 2, any rounding -> 3)
    "hex$(2.9)", "hex$(-2.5)", "hex$(40000.5)", "2.9\\1", "-2.9\\1",
    "7.5 mod 4", "7\\2.5", "7\\1.5",
    # single (+) single -> double? (round-1 add ties were confounded by
    # crunch-time rounding; these sums are exact only in double)
    "123456!+.5", "1000000!+1!",
    # multiplication overflow = PRE-normalisation exponent sum? (1e62*9
    # overflowed although 9e62 is representable: 63+1=64. 9e61*9 = 62+1=63
    # must then pass; 2e62*4 = 63+1=64 must then fail)
    "9e61*9", "2e62*4",
    # division exponent walls (pre-norm difference?)
    "1e40/1e-40", "1e62/.1", "2e62/.4",
    # rounding mode of the DOUBLE ops themselves (exact ties at digit 15)
    "1+5e-14", "3+5e-14", "1+6e-14", "1+4e-14", "1-1e-15",
    "1.0000000000003#/2", "2.5#*1.0000000000001#", "1/3*3-1",
    # relationals never int-convert their float side (no Overflow)
    "40000=40000!", "1e10>5",
    # --- round-3 edge pins ---------------------------------------------------
    # the address-domain conversion wraps >32767 into signed FIRST, then
    # truncates toward zero (hex$(40000.5) -> $9C41 = 40001, not $9C40)
    "hex$(40000.1)",
    # mul underflow boundary: exponent-sum pre-check vs post-normalise
    "1e-32*1e-32", "1e-33*1e-32",
    # division tie at digit 15 + rounding on magnitude (away from zero)
    "1.0000000000003#/4", "-2/3",
    # --- round-4: conversion-domain boundaries (exclusive bounds + the
    # >=32768 wrap threshold; spec §10.3) ------------------------------------
    "hex$(32767.5)", "hex$(65535.5)", "hex$(65536.)", "hex$(-32768.5)",
    "hex$(-32768.9)", "32767.5\\1", "-32768.5\\1",
    # --- round-5: subtraction guard-tie bug-compat (docs/spec-float-subtract-
    # tie-compat.md §3/§4). Effective-SUBTRACT (opposite-sign combine) exact
    # guard-digit ties round TOWARD ZERO on the reference; effective-ADD
    # (like-sign combine) ties stay AWAY FROM ZERO (half-up, unchanged) --
    # keyed on the effective op, not the surface +/- token.
    "2-5e-14", "5e-14-2", "8.5-5e-14", "200-5e-12",  # 200-: real large-mag tie
    # (NB: 100-5e-12 is NOT a tie -- 100's lead digit cancels, the guard is
    # absorbed by the leading-zero renormalise -> exact 99.999999999995; use a
    # lead-digit>=2 magnitude like 200 so k=0 keeps guard==5 reaching the nudge.)
    "2+(-5e-14)",               # '+' token, opposite signs -> effective subtract
    "-1-5e-14", "2-(-5e-14)",   # '-' token, like signs -> effective add (regression)
    "2-4e-14", "2-6e-14",       # near-tie both sides, unchanged on both machines
]

# Full-line cases (multi-item PRINT: pins that the accumulator type resets
# between PRINT items — a float item must not leak into the next int item;
# IF truthiness: a float condition is true iff nonzero — `IF .5 THEN` takes
# the TRUE branch, so the truncated int view of the condition must NOT be
# the judge).
RAW_LINES = [
    'print "[";1.5;2;"]"',
    'print "[";2;1.5;"]"',
    'if .5 then print "[y]" else print "[n]"',
    'if 1.5 then print "[y]" else print "[n]"',
    'if 1.5-1.5 then print "[y]" else print "[n]"',
]

# Bare-statement cases: pins the STATEMENT-level int-argument conversion
# (address domain, wrap-then-truncate, out-of-domain -> Overflow abort).
# Differential pass criterion: tail EMPTINESS matches (error wording is
# zerobas's own lowercase D-2-style text, so the text itself is excluded).
STMT_LINES = [
    "poke 100000,0",    # out of the -32768..65535 address domain -> Overflow
    "poke 40000.5,1",   # wrap-then-truncate -> address 40001, silent success
]

# Cases whose TAIL legitimately differs between reference and zerobas: an
# error message is printed and zerobas wording is its own lowercase D-2-style
# text. Differential mode compares only the bracket span (identical value /
# identical absence-of-']' = identical continuation shape).
SPAN_ONLY = {
    "1/0", "1!/0", "1#/0", "0/0", "1\\0", "1 mod 0",
    "1e62*9", "1e62*10", "1e40*1e40", "-1e40*1e40", "9e62+9e62", "1d62*10",
    "2e62*4", "1e40/1e-40", "1e62/.1", "2e62/.4",
    "40000!\\2", "40000 mod 7", "40000! and 65535", "100000! and 1",
    "hex$(65536.)",
}


# Delivery via the typing-free KEYBUF driver. All cases are direct-mode; a RAW
# line that exceeds the KEYBUF cap (the three IF/THEN/ELSE lines, no top-level
# ':') is delivered by the driver's chunked injection, so it stays direct-mode.
# The whole matrix ships in ONE boot (omsx_repl.run_cases, batched, CLS reset
# between cases -- no case here assigns a variable, so a screen clear is the
# only inter-case state that matters); --boot-per-case restores the historical
# one-boot-per-case isolation. result_span / screen_tail come from omsx_repl.
result_span = omsx_repl.result_span
screen_tail = omsx_repl.screen_tail


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
                    help="isolate each case in its own boot (slow) instead of the "
                         "default single-boot batch -- use to rule out inter-case "
                         "leakage when a batched case looks wrong")
    args = ap.parse_args()

    cases = [(e, f'print "[";{e};"]"', "expr") for e in EXPRS]
    cases += [(line, line, "raw") for line in RAW_LINES]
    cases += [(line, line, "stmt") for line in STMT_LINES]
    cases = [c for c in cases if not (args.only and args.only not in c[0])]
    specs = [("direct", [line]) for _, line, _ in cases]

    # Characterisation mode: reference only, no differential -> plain batch.
    if not args.zb_machine:
        for (expr, line, kind), raw in zip(cases, omsx_repl.run_cases(
                args.machine, specs, batch=not args.boot_per_case, reset=("CLS",))):
            ref_span, ref_tail = result_span(raw), screen_tail(raw, line)
            rs = f"[{ref_span}]" if ref_span is not None else "<no span>"
            extra = ""
            # show the tail whenever it holds more than the span line alone
            if ref_tail is not None and ref_tail.count("|") + 1 > 1:
                extra = f"   tail: {ref_tail!r}"
            elif ref_span is None:
                extra = f"   tail: {ref_tail!r}"
            print(f"{expr:<24} {rs}{extra}")
        return 0

    def compare(i, ref_raw, zb_raw):
        expr, line, kind = cases[i]
        ref_span, ref_tail = result_span(ref_raw), screen_tail(ref_raw, line)
        zb_span, zb_tail = result_span(zb_raw), screen_tail(zb_raw, line)
        if kind == "stmt":
            return ref_tail is not None and zb_tail is not None \
                and (ref_tail == "") == (zb_tail == "")
        if kind == "raw":
            # RAW lines can exceed one screen row (the echo wraps, so no single
            # row matches and the tail is unfindable on either side) — their pin
            # is the bracket SPAN, immune to the wrap. Require a span both sides.
            return ref_span is not None and ref_span == zb_span
        if expr in SPAN_ONLY:
            # tails must EXIST on both sides (a dead machine must not pass
            # vacuously on two absent spans); their TEXT differs legitimately.
            return ref_tail is not None and zb_tail is not None \
                and ref_span == zb_span
        return ref_tail is not None and ref_tail == zb_tail

    verdicts, ref_raws, zb_raws = omsx_repl.run_differential(
        args.machine, args.zb_machine, specs, compare,
        batch=not args.boot_per_case, reset=("CLS",))

    ok = True
    for (expr, line, kind), good, ref_raw, zb_raw in zip(
            cases, verdicts, ref_raws, zb_raws):
        ok = ok and good
        ref_span = result_span(ref_raw)
        rs = f"[{ref_span}]" if ref_span is not None else "<no span>"
        print(f"{'PASS' if good else 'FAIL'}  {expr:<24} ref: {rs}")
        if not good:
            zb_span, zb_tail = result_span(zb_raw), screen_tail(zb_raw, line)
            zs = f"[{zb_span}]" if zb_span is not None else "<no span>"
            print(f"{'':>32}ref tail: {screen_tail(ref_raw, line)!r}")
            print(f"{'':>32}zb  span: {zs}  tail: {zb_tail!r}")

    if args.zb_machine:
        print("\nALL PASS — float arithmetic is reference-identical" if ok
              else "\nSOME FAILED")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
