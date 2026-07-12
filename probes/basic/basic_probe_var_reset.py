#!/usr/bin/env python3

"""Variable-reset probe — characterise, then differentially prove, that NEW and
a bare CLEAR wipe ALL variables (VARTAB + the string table + the per-letter
DEFtbl), matching MS-BASIC / MSX-BASIC. This is the divergence the acceptance-
harness rework surfaced (docs/spec-acceptance-harness-rework.md, self-test
2026-07-12): zerobas's NEW/CLEAR reset the program pointer and string space but
NOT the variable table, so a direct-mode variable leaked across NEW and CLEAR.
Because the current acceptance probes boot openMSX once PER CASE, every other
probe gets power-on-fresh state and the leak stays invisible — this probe is the
only gate that pins the reset semantics, so it deliberately drives MULTIPLE REPL
submissions in ONE boot (assign, then NEW/CLEAR, then read back).

Each case is a list of REPL lines injected in sequence into a single boot; the
LAST line prints the read-back value with the `[...]` bracket convention
(mirrors basic_probe_float_vars.py). Only the bracket SPAN is compared. The
value must come back as if the variable were never assigned — 0 for a fresh
numeric, the default (all-double) DEFtbl type after NEW/CLEAR.

Differential mode (--zb-machine): also run zerobas (repack build) and assert
span equality (REF_MACHINE Philips_VG_8020 vs the repack disk machine).

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

# Each case: (label, lines, expect)
#   lines : REPL submissions injected in order into ONE boot; the last prints a
#           `[...]`-bracketed value. NEW is an EDITOR command, so it MUST be its
#           own submission (it is not a `:`-joinable statement); bare CLEAR is a
#           statement and may be `:`-joined.
#   expect: the spec-documented reference value for the characterisation self-
#           check (differential mode compares the two machines regardless).
#
# Numeric PRINT spacing (spec §9.3): a non-negative value prints as
# <space-sign><digits><trailing space>, so a fresh 0 is " 0 " and 1.9 is " 1.9 ".
CASES = [
    # --- bare CLEAR wipes an integer variable -------------------------------
    ("clear.int",
     ['B%=5:CLEAR:PRINT"[";B%;"]"'],
     " 0 "),
    # --- bare CLEAR wipes an unsuffixed (double) variable -------------------
    ("clear.dbl",
     ['A=5:CLEAR:PRINT"[";A;"]"'],
     " 0 "),
    # --- bare CLEAR wipes a string variable (empty string -> no chars) ------
    ("clear.str",
     ['A$="HI":CLEAR:PRINT"[";A$;"]"'],
     ""),
    # --- NEW wipes an integer variable (NEW on its own line) ----------------
    ("new.int",
     ["B%=7", "NEW", 'PRINT"[";B%;"]"'],
     " 0 "),
    # --- NEW wipes an unsuffixed (double) variable --------------------------
    ("new.dbl",
     ["A=7", "NEW", 'PRINT"[";A;"]"'],
     " 0 "),
    # --- NEW wipes a string variable ----------------------------------------
    ("new.str",
     ['A$="HI"', "NEW", 'PRINT"[";A$;"]"'],
     ""),
    # --- NEW resets the DEFtbl: DEFINT Z then NEW -> Z defaults to DOUBLE, so
    #     Z=1.9 keeps its fraction (an int Z would truncate to 1). ------------
    ("new.deftbl",
     ["DEFINT Z:Z=1.9", "NEW", 'Z=1.9:PRINT"[";Z;"]"'],
     " 1.9 "),
    # --- CLEAR resets the DEFtbl too ----------------------------------------
    ("clear.deftbl",
     ["DEFINT Z:Z=1.9", "CLEAR", 'Z=1.9:PRINT"[";Z;"]"'],
     " 1.9 "),
]


def capture(machine, lines):
    """Return the bracket SPAN for one multi-line case on one machine. All lines
    fit the KEYBUF direct cap, so drive them as sequential direct submissions in
    a single boot; read the printed value from the final screen."""
    raw = omsx_repl.run_case(machine, "direct", list(lines))
    return omsx_repl.result_span(raw)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE,
                    help=f"reference oracle machine (default {REF_MACHINE})")
    ap.add_argument("--zb-machine", dest="zb_machine",
                    help="differential mode: also run this repack machine and "
                         "assert span equality")
    ap.add_argument("--only", help="substring filter on the case label")
    args = ap.parse_args()

    ok = True
    for label, lines, expect in CASES:
        if args.only and args.only not in label:
            continue
        ref_span = capture(args.machine, lines)
        rs = f"[{ref_span}]" if ref_span is not None else "<no span>"

        if args.zb_machine:
            zb_span = capture(args.zb_machine, lines)
            zs = f"[{zb_span}]" if zb_span is not None else "<no span>"
            same = ref_span is not None and ref_span == zb_span
            ok = ok and same
            print(f"{'PASS' if same else 'FAIL'}  {label:<16} ref: {rs}")
            if not same:
                print(f"{'':>24}zb span: {zs}")
        else:
            match = "OK" if ref_span == expect else "MISMATCH vs spec!"
            print(f"{label:<16} {rs}   expect {expect!r} -> {match}")

    if args.zb_machine:
        print("\nALL PASS — variable reset (NEW/CLEAR) reference-identical" if ok
              else "\nSOME FAILED")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
