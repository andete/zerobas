#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Error-handling acceptance — S1 foundation gate (docs/spec-basic-error-handling.md).

Two families, both driven through the typing-free KEYBUF-injection REPL driver
(probes/lib/omsx_repl.py), differential against the reference oracle Philips VG-8020.

FAMILY A -- untrapped-error ABORT semantics (the D-1 fix; §1/§3/§6 of the spec).
  Observable-variable design, robust (no screen marker-vs-echo disambiguation):

      10 A=1
      20 <error trigger>          <- a FATAL runtime error
      30 A=2
      RUN
      PRINT"R<";A;">"             <- direct-mode read AFTER the run

  On real MSX every untrapped runtime error ABORTS the run and returns to Ok, so
  line 30 never runs and A stays 1. If the run wrongly CONTINUES past the error
  (zerobas's pre-S1 D-1 bug) line 30 sets A=2. So A==1 <=> aborted, A==2 <=>
  continued. UNIFORM: all ten reachable error types are fatal -- including
  division-by-zero and integer overflow (spec §9.2 correction, 2026-07-18; the
  earlier "non-fatal" claim was a misread of zerobas's own bug). The reference
  oracle-lock asserts A==1 for every case; the differential asserts zerobas == ref.
  Pre-S1 zerobas returns A==2 for all -> the differential is RED by design.

FAMILY B -- run-mode " in <line>" reporting (the D-2 fix). Wording stays house-style
  (we don't copy MSX's verbatim text -- so we DON'T compare the message string to the
  reference), but the *structure* is asserted on BOTH machines: a run-mode error's
  message carries " in <erroring-line>", a direct-mode error's does not. Screen-scrape.

Batched by default (one boot per machine drives the whole matrix; ("NEW","CLS") resets
each case). Exit 0 iff every enabled assertion passes.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import namedtuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl  # noqa: E402

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

# --- Family A: abort semantics -------------------------------------------------
# (label, MSX ERR code, the program lines that error at line 20). Every trigger is
# a FATAL error; the erroring line is 20 (or the last line before 30) in all cases.
AbortCase = namedtuple("AbortCase", "label err lines")

ABORT_CASES = [
    AbortCase("illegal_fn",    5,  ['20 B=SQR(-1)']),
    AbortCase("subscript",     9,  ['15 DIM Q(2)', '20 Q(9)=1']),
    AbortCase("next_nofor",    1,  ['20 NEXT']),
    AbortCase("ret_nogosub",   3,  ['20 RETURN']),
    AbortCase("redim",         10, ['15 DIM Q(2)', '20 DIM Q(2)']),
    AbortCase("type_mismatch", 13, ['15 C$="x"', '20 B=C$']),
    AbortCase("out_of_data",   4,  ['20 READ X']),
    AbortCase("undef_line",    8,  ['20 GOTO 999']),
    AbortCase("divzero",       11, ['20 B=1/0']),
    AbortCase("int_overflow",  6,  ['20 C%=99999']),
]


def abort_spec(c: AbortCase):
    return ("direct", ['10 A=1'] + c.lines + ['30 A=2', 'RUN', 'PRINT"R<";A;">"'])


def read_A(raw):
    """The value printed by `PRINT"R<";A;">"` -> "1" (aborted) or "2" (continued)."""
    if not raw:
        return None
    m = re.findall(r"R<([^<>]*)>", raw)
    return m[-1].strip() if m else None


# --- Family B: " in <line>" structure -----------------------------------------
# Run-mode: an error at line 20 must report " in 20". Direct-mode: no " in <n>".
INMODE_RUN = ("run", ['10 B=SQR(-1)', 'RUN'], "20?no")   # error at line 10, expect " in 10"
INMODE_RUN2 = ("run_l30", ['30 B=SQR(-1)', 'RUN'], None)  # expect " in 30"
INMODE_DIRECT = ("direct", ['PRINT SQR(-1)'], None)       # expect NO " in <n>"


def in_line_number(raw):
    """The <n> from an error message's ' in <n>' suffix, or None if absent."""
    if not raw:
        return None
    # The echoed source lines never contain the word "in"; the only " in <n>" on
    # screen is the error-message suffix. Take the last (lowest on the scrolling
    # screen == most recent).
    m = re.findall(r"\bin (\d+)\b", raw)
    return m[-1] if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE, help="reference oracle machine")
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE,
                    help="zerobas repack machine")
    ap.add_argument("--only", help="run only cases whose label contains this substring")
    ap.add_argument("--ref-only", action="store_true", help="oracle-lock only")
    ap.add_argument("--boot-per-case", dest="boot_per_case", action="store_true")
    args = ap.parse_args()
    batch = not args.boot_per_case
    ok = True

    # ---------------- Family A ----------------
    acases = [c for c in ABORT_CASES if not args.only or args.only in c.label]
    if acases:
        specs = [abort_spec(c) for c in acases]
        ref = omsx_repl.run_cases(args.machine, specs, batch=batch, reset=("NEW", "CLS"))
        zb = (omsx_repl.run_cases(args.zb_machine, specs, batch=batch, reset=("NEW", "CLS"))
              if not args.ref_only else [None] * len(specs))

        print(f"--- FAMILY A: abort oracle-lock ({args.machine}) — every error aborts (A==1) ---")
        ref_A = {}
        for c, r in zip(acases, ref):
            got = read_A(r)
            ref_A[c.label] = got
            good = got == "1"
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} {c.label:14} err={c.err:<3} A={got!r} (want '1'=aborted)")

        if not args.ref_only:
            print(f"\n--- FAMILY A: zerobas == reference ({args.zb_machine}) ---")
            for c, r in zip(acases, zb):
                got = read_A(r)
                want = ref_A.get(c.label)
                good = got is not None and got == want
                ok = ok and good
                flag = "" if good else ("  <- ZB CONTINUES PAST ERROR (D-1)" if got == "2" else "")
                print(f"{'PASS' if good else 'FAIL':5} {c.label:14} zb={got!r} ref={want!r}{flag}")

    # ---------------- Family B ----------------
    if not args.only or "in_line" in (args.only or ""):
        print(f"\n--- FAMILY B: ' in <line>' structure ---")
        bspecs = [("direct", INMODE_RUN[1]), ("direct", INMODE_RUN2[1]),
                  ("direct", INMODE_DIRECT[1])]
        want = ["10", "30", None]  # run@10 -> "in 10"; run@30 -> "in 30"; direct -> none
        labels = ["run@10", "run@30", "direct"]
        for machine, tag in ([(args.machine, "ref")] +
                             ([(args.zb_machine, "zb")] if not args.ref_only else [])):
            raws = omsx_repl.run_cases(machine, bspecs, batch=batch, reset=("NEW", "CLS"))
            for lbl, w, r in zip(labels, want, raws):
                got = in_line_number(r)
                good = got == w
                ok = ok and good
                print(f"{'PASS' if good else 'FAIL':5} [{tag}] {lbl:8} in-line={got!r} (want {w!r})")

    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
