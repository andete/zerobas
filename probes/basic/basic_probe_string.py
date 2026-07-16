#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional string-engine probe (string-engine arc S5).

Boots the merged repack build (relocated BASIC + string engine) as a real MSX main
ROM and drives its live REPL, asserting the eight string verbs and `+` concatenation
produce the right *screen* output end-to-end -- the behavioural complement to the
byte-level crunch differential (basic_probe_crunch.py --zb-machine). Where the crunch
probe proves the keywords tokenise like a real MSX ROM, this proves they EXECUTE
correctly on the relocated build.

Each case prints its result wrapped in brackets -- `PRINT "[";<expr>;"]"` -- so the
output token (e.g. `[HEL]`) is unambiguous even when the result is a substring of the
echoed source (LEFT$("HELLO",3) -> HEL, a prefix of the echoed "HELLO"). Cases are
typed in small batches that fit the 40x24 screen, then the VRAM text is scanned once.

Repack-only by construction: the lean 16 KB basic.rom emits these keywords as verbatim
ASCII and has no engine, so this runs against C-BIOS_MSX1_EU_REPACK_DISK (installed by
`make repack-machine`); override with --machine / $ZEROBAS_BASIC_MACHINE.

    python3 probes/basic/basic_probe_string.py
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402  typing-free KEYBUF-injection REPL driver

# The repack acceptance target (merged main ROM + zerobas-disk); same machine the
# repack crunch differential and diskbasic-acceptance-repack boot. $ZEROBAS_BASIC_MACHINE
# lets the Makefile point the whole string gate at one machine.
MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
COLS, ROWS = 40, 24
NLEN = COLS * ROWS

# (label, line-to-type, expected-regex-on-screen). Every result is bracketed so it
# can't collide with the echoed source. Numeric results carry MSX's sign/trailing
# spaces (`PRINT 5` -> " 5 "), so those patterns allow surrounding blanks; STR$ keeps
# only its own leading sign-space (it is a *string*, no trailing space).
CASES = [
    # `+` concatenation -- the arc's flagship. Literal-lead, var-lead, and a 3-operand
    # chain; the literal-lead forms exercise the S5 PRINT concat fix (print.asm).
    ("concat.chain",  'PRINT "[";"AB"+"CD"+"EF";"]"',          r"\[ABCDEF\]"),
    ("concat.var",    'A$="AB":B$="CD":PRINT "[";A$+B$;"]"',   r"\[ABCD\]"),
    ("concat.litfn",  'PRINT "[";"N="+STR$(7);"]"',            r"\[N= 7\]"),
    # STRCAT_R nested-concat cases (arrays slice-4a §7, the retired
    # spec-basic-string-concat-nesting-fix.md): a concat operand whose OWN
    # evaluation is a function-with-a-nested-concat used to corrupt the global
    # accumulator ("A"+MID$("XY"+"Z",1,2)+"B" -> "XYZXYB"). The accumulator is
    # now a per-expression temp, so these are correct by construction.
    ("concat.fn-mid", 'PRINT "[";"A"+MID$("XY"+"Z",1,2)+"B";"]"', r"\[AXYB\]"),
    ("concat.fn-last",'PRINT "[";"A"+LEFT$("PQ"+"RS",3);"]"',   r"\[APQR\]"),
    ("concat.fn-var", 'A$="XY":B$="Z":PRINT "[";"A"+MID$(A$+B$,1,2)+"B";"]"', r"\[AXYB\]"),
    ("concat.fn-rt",  'PRINT "[";STR$(1)+"-"+STR$(2);"]"',      r"\[ 1- 2\]"),
    # MID$-statement with a function (HEX$) RHS -- slice-4a moved HEX$/OCT$
    # digit-building into NUMBUF sub-side, which used to alias MIDS_DEST (S8);
    # re-homed, so A$'s stashed dest survives the RHS eval.
    ("mid.stmt.hex",  'A$="ZZ":MID$(A$,1)=HEX$(255):PRINT "[";A$;"]"', r"\[FF\]"),
    # string -> string verbs
    ("LEFT$",         'PRINT "[";LEFT$("HELLO",3);"]"',        r"\[HEL\]"),
    ("RIGHT$",        'PRINT "[";RIGHT$("HELLO",2);"]"',       r"\[LO\]"),
    ("MID$",          'PRINT "[";MID$("HELLO",2,3);"]"',       r"\[ELL\]"),
    ("MID$.tail",     'PRINT "[";MID$("HELLO",4);"]"',         r"\[LO\]"),
    ("CHR$",          'PRINT "[";CHR$(66);"]"',                r"\[B\]"),
    # number -> string / string -> number
    ("STR$",          'PRINT "[";STR$(42);"]"',                r"\[ 42\]"),
    ("STR$.neg",      'PRINT "[";STR$(-3);"]"',                r"\[-3\]"),
    ("LEN",           'PRINT "[";LEN("ABCDE");"]"',            r"\[\s*5\s*\]"),
    ("ASC",           'PRINT "[";ASC("Z");"]"',                r"\[\s*90\s*\]"),
    ("VAL",           'PRINT "[";VAL("34")+1;"]"',             r"\[\s*35\s*\]"),
    # verb wrapping a concat (spec nest `LEFT$(A$+B$,3)`)
    ("nest",          'PRINT "[";LEFT$("XY"+"ZW",3);"]"',      r"\[XYZ\]"),
    # string-functions slice (spec-basic-string-functions.md §5) -- HEX$/OCT$/
    # SPACE$/STRING$/INSTR live on the repack build.
    ("HEX$",          'PRINT "[";HEX$(255);"]"',               r"\[FF\]"),
    ("OCT$",          'PRINT "[";OCT$(8);"]"',                 r"\[10\]"),
    ("SPACE$",        'PRINT "[";SPACE$(3);"]"',                r"\[   \]"),
    ("STRING$",       'PRINT "[";STRING$(3,"*");"]"',           r"\[\*\*\*\]"),
    ("INSTR",         'PRINT "[";INSTR("HELLO","LL");"]"',      r"\[\s*3\s*\]"),
]

def _rows(raw: str | None) -> str | None:
    """Reshape an omsx_repl flat SCREEN-0 capture into 24 newline-joined
    40-column rows (each right-stripped, as the former VRAM scraper produced).
    None passes through (capture failure)."""
    if raw is None:
        return None
    return "\n".join(raw[i * COLS:(i + 1) * COLS].rstrip() for i in range(ROWS))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=MACHINE,
                    help="repack machine (default $ZEROBAS_BASIC_MACHINE or "
                         "C-BIOS_MSX1_EU_REPACK_DISK)")
    ap.add_argument("--only", help="run only cases whose label contains this substring")
    ap.add_argument("--boot-per-case", dest="boot_per_case", action="store_true",
                    help="isolate each case in its own boot instead of the default "
                         "single-boot batch (to rule out inter-case leakage)")
    args = ap.parse_args()

    cases = [c for c in CASES if not args.only or args.only in c[0]]
    if not cases:
        print(f"no cases match --only {args.only!r}")
        return 1

    # Every case is an independent direct-mode PRINT (a few set A$/B$ first), so
    # the whole matrix shares ONE boot with a ("NEW","CLS") reset between cases
    # (NEW drops any string var; CLS clears the screen so each capture holds only
    # its own case). Typing-free KEYBUF injection -- no keyboard-matrix race, so
    # the former one-line-per-boot discipline is no longer needed.
    specs = [("direct", [line]) for _, line, _ in cases]
    screens = omsx_repl.run_cases(args.machine, specs, batch=not args.boot_per_case,
                                  reset=("NEW", "CLS"), capture="screen")

    ok = True
    for (label, line, pat), raw in zip(cases, screens):
        scr = _rows(raw)
        good = scr is not None and re.search(pat, scr) is not None
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':5} {label:14} {line}")
        if not good:
            print(f"        want /{pat}/  in screen:")
            for row in (scr.splitlines() if scr else []):
                if row:
                    print(f"        | {row}")

    print("\nALL PASS -- string engine executes correctly on the repack build"
          if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
