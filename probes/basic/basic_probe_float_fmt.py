#!/usr/bin/env python3

"""Float PRINT-format probe — characterise, then differentially prove, the MSX
number OUTPUT format for float values (Phase-3 float pack F1;
docs/spec-basic-float-core.md §3d).

Each case types  PRINT "[";<lit>;"]"  in direct mode and captures the SCREEN 0
name table (same bracket technique as basic_probe_str_fn.py; every result here
fits on one visual row, so the last '['..']' span in the raw row-major text IS
the printed number, spaces exact). No arithmetic is exercised — F1 is
parse/store/print only (unary minus IS included: the reference applies it at
runtime, and zerobas F1 ships the trivial sign flip so negative display is
provable).

Characterisation mode (default): print the reference's exact output per case.
Differential mode (--zb-machine): also run zerobas (repack build) and assert
byte-equal spans.

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

# Formatter matrix (spec §3d — sign position, trailing space, significant
# digits, trailing-zero suppression, leading '.', E/D scientific thresholds,
# integer-valued floats). Typed as  PRINT "[";<lit>;"]".
LITERALS = [
    # int regression anchors
    "0", "5", "-5", "32767", "-32768",
    # simple singles + sign
    "1.5", "-1.5", ".5", "-.5", "0.1",
    # trailing-zero suppression / integer-valued floats
    "1.0", "1.50", "2!", "100000!", "1e5",
    # single significant-digit wall + display rounding
    "3.14159", "3.141592", "1234567!", "9999995!", "999999!", "1000000!",
    # single E-notation thresholds, both ends
    "1e6", "9999990!", ".01", ".001", ".0001", "1e-3", "6.023e23", "1e-9",
    "-1e10", "2.5e-10",
    # doubles: 14 digits, D-notation
    "1#", "1.5#", "0.1#", "1.23456789#", "1.2345678901234#",
    "123456789012345678", "1d16", "1.5d-3", "1e10#", "-1.23456789012345#",
    # extremes (exponent walls)
    "1e62", "1e-64", "1d62", "1d-64",
    # fixed<->E walls: high side per precision, low side, and low-side shape
    "1e13", "1e14", "1e15", "9.9e13", "1d13", "1d14", "1d15",
    "1d-2", "1d-3", ".0123", ".00123", "99999999999999#",
    # zero forms
    "0!", "0#", ".0",
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE,
                    help=f"reference oracle machine (default {REF_MACHINE})")
    ap.add_argument("--zb-machine", dest="zb_machine",
                    help="differential mode: also run this repack machine and "
                         "assert span equality")
    ap.add_argument("--only", help="substring filter on the literal")
    ap.add_argument("--boot-per-case", dest="boot_per_case", action="store_true",
                    help="isolate each case in its own boot (slow) instead of the "
                         "default single-boot batch")
    args = ap.parse_args()

    lits = [l for l in LITERALS if not (args.only and args.only not in l)]

    # Every LITERALS line is a short direct-mode PRINT (<=38 chars). CLS reset --
    # no case assigns a variable. The printed number is the last '['..']' span.
    specs = [("direct", [f'print "[";{lit};"]"']) for lit in lits]
    # 1e10# is an exponent-then-suffix combo the tokeniser rejects, leaving a
    # stray token that spins the interpreter -- run it boot-per-case so it never
    # poisons the shared batch (run_differential's `isolate`); the self-heal would
    # rescue its followers anyway, but isolating it keeps the batch full-speed.
    WEDGERS = {"1e10#"}
    isolate = frozenset(i for i, lit in enumerate(lits) if lit in WEDGERS)

    # Characterisation mode: reference only, no differential -> plain batch.
    if not args.zb_machine:
        for lit, raw in zip(lits, omsx_repl.run_cases(
                args.machine, specs, batch=not args.boot_per_case, reset=("CLS",))):
            span = omsx_repl.result_span(raw)
            print(f"{lit:<22} {f'[{span}]' if span is not None else '<no capture>'}")
        return 0

    def compare(i, ref_raw, zb_raw):
        ref, zb = omsx_repl.result_span(ref_raw), omsx_repl.result_span(zb_raw)
        # pre-authorised: a crunch-time rejection on BOTH sides is a pass (e.g.
        # 1e10# -- an exponent-then-suffix combo neither side's tokeniser accepts
        # as a single literal, so the trailing suffix char is left in the token
        # stream and derails the expression evaluator identically on both sides;
        # see basic/float.asm tkf_try_exponent's header). run_differential re-runs
        # such a case boot-per-case so its shared-boot derail can't poison others.
        if ref is None and zb is None:
            return True
        return ref is not None and zb is not None and ref == zb

    verdicts, ref_raws, zb_raws = omsx_repl.run_differential(
        args.machine, args.zb_machine, specs, compare,
        batch=not args.boot_per_case, reset=("CLS",), isolate=isolate)

    ok = True
    for lit, good, ref_raw, zb_raw in zip(lits, verdicts, ref_raws, zb_raws):
        ok = ok and good
        ref, zb = omsx_repl.result_span(ref_raw), omsx_repl.result_span(zb_raw)
        rs = f"[{ref}]" if ref is not None else "<no capture>"
        if good and ref is None and zb is None:
            print(f"PASS  {lit:<22} ref: {rs}  [both rejected]")
            continue
        print(f"{'PASS' if good else 'FAIL'}  {lit:<22} ref: {rs}")
        if not good:
            print(f"{'':>30}zb : {f'[{zb}]' if zb is not None else '<no capture>'}")

    if args.zb_machine:
        print("\nALL PASS — float output format is reference-identical" if ok
              else "\nSOME FAILED")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
