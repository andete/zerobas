#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Oracle + differential probe -- string comparison (string-compare S2), PLUS the
unparenthesized-PRINT-lead follow-on slice (spec-basic-print-unparen-compare.md).

Two halves, per spec-basic-string-compare.md §5:

1. REFERENCE ORACLE (black-box, no disassembly). Types a direct-mode line into
   the real Philips VG-8020's built-in MSX-BASIC (no cartridge -- `cart=None`,
   same technique as basic_probe_crunch.py / basic_probe_print.py) that assigns
   two string operands and PRINTs all SIX relational results, bracket-wrapped so
   the output is unambiguous. Asserts the reference's own -1/0 results match the
   §2 contract (unsigned byte-by-byte, shorter-is-less, case-sensitive) -- the
   expected values are DERIVED from the contract, not assumed; this locks the
   real hardware's behaviour in before any zerobas comparison.

2. ZEROBAS DIFFERENTIAL. Runs the IDENTICAL line on the repack machine
   (C-BIOS_MSX1_EU_REPACK_DISK -- the string engine is repack-only, spec §1) and
   asserts zerobas's six results equal the reference's.

Battery: equal, prefix-shorter (both directions), case, first-diff-byte (both
directions), and empty-string pairs -- the §2 D-3 cases -- each exercising all
six operators (`=` `<>` `<` `>` `<=` `>=`) in one PRINT line via the compound-form
merge zerobas reuses from the numeric ev_rel (spec §3).

A THIRD section (spec-basic-print-unparen-compare.md §4 D-4, §6) extends this same
reference-lock + zerobas==reference discipline to the **bare, unparenthesized**
`PRINT` item -- `PRINT A$="YES"` rather than `PRINT (A$="YES")` -- across all
three string leads (`$`-variable, string literal, string function) plus a concat
chain, and the `PRINT A$<5` type-mismatch abort (D-2: the line aborts, printing
NOTHING for the item -- confirmed against real hardware's own `Type mismatch`
message, case-divergent from zerobas's lowercase `type mismatch`, same documented
divergence as the parenthesized form). Each case types SHORT direct-mode lines
(one assignment per line, then the PRINT) rather than one long compound line --
openMSX's typed Enter can land mid-typing on a long line and silently drop it
(probe gotcha from the MID$-statement slice, basic_probe_mid_stmt.py).

Clean-room: this only *observes* black-box behaviour (type a line, read the
screen). The reference ROM is never read as code. See CONTRIBUTING.md.

    python3 probes/basic/basic_probe_str_cmp.py
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import namedtuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402  typing-free KEYBUF-injection REPL driver

REF_MACHINE = "Philips_VG_8020"    # reference: built-in MSX-BASIC, no cartridge
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
COLS, ROWS = 40, 24
NLEN = COLS * ROWS


def _rows(raw: str | None) -> str | None:
    """Reshape an omsx_repl flat SCREEN-0 capture (SCR_LEN chars, non-print ->
    space) into the 24 newline-joined 40-column rows the extract_* helpers read.
    None passes through (capture failure)."""
    if raw is None:
        return None
    return "\n".join(raw[r * COLS:(r + 1) * COLS] for r in range(ROWS))

# (label, lhs, rhs) -- the §2 D-3 battery: equal, prefix-shorter (both
# directions), case, first-diff-byte (both directions covered by re-running with
# operands swapped is unnecessary -- the six operators already probe both
# directions of a single ordered pair), empty string (both against a non-empty
# string and against itself).
CASES = [
    ("equal",            "AB",  "AB"),
    ("prefix-shorter",   "AB",  "ABC"),
    ("case",              "A",   "a"),
    ("first-diff-byte",  "ABD", "ABC"),
    ("empty-lhs",          "",   "A"),
    ("empty-both",         "",    ""),
]

OPS = ["=", "<>", "<", ">", "<=", ">="]


def expected_bits(lhs: str, rhs: str):
    """The §2 contract's -1/0 result for each of the six operators, computed from
    plain Python string ordering (ASCII, unsigned-byte-equivalent for our operand
    set) -- the expected values, not an assumption about any implementation."""
    eq, ne = lhs == rhs, lhs != rhs
    lt, gt = lhs < rhs, lhs > rhs
    le, ge = lhs <= rhs, lhs >= rhs
    return tuple(-1 if v else 0 for v in (eq, ne, lt, gt, le, ge))


def build_line(lhs: str, rhs: str) -> str:
    return (f'A$="{lhs}":B$="{rhs}":'
            'PRINT"[";(A$=B$);(A$<>B$);(A$<B$);(A$>B$);(A$<=B$);(A$>=B$);"]"')


def extract_bits(screen_text):
    """Pull the six ints out of the bracketed `[...]` PRINT OUTPUT row. The
    echoed command text itself contains a literal `"["`/`"]"` (the PRINT
    statement's own bracket delimiters), so a naive `[^\\]]*` search can span
    from the echoed opening bracket all the way to the echoed closing one,
    swallowing the BASIC syntax in between -- restrict the bracket contents to
    digits/spaces/minus (what a numeric PRINT item actually emits) so only the
    real result row matches. Returns None if not found or not exactly six ints."""
    if screen_text is None:
        return None
    m = re.search(r"\[([ \d-]+)\]", screen_text)
    if not m:
        return None
    nums = [int(x) for x in re.findall(r"-?\d+", m.group(1))]
    return tuple(nums) if len(nums) == 6 else None


# ===========================================================================
# unparenthesized PRINT-lead comparisons (spec-basic-print-unparen-compare.md)
# ===========================================================================

# (label, setup lines, the PRINT line itself, lhs value, op, rhs value) -- the
# §1 table's three leads (var/literal/function) + a concat chain, all six
# operators represented across the battery, ordering, and a compound form.
# `lhs`/`op`/`rhs` are the ACTUAL string values compared (for computing the
# expected -1/0 in Python -- never assumed); for the concat case `lhs` is the
# already-concatenated value.
PrintCase = namedtuple("PrintCase", "label setup print_line lhs op rhs")

OP_EXPECT = {
    "=":  lambda a, b: a == b,
    "<>": lambda a, b: a != b,
    "<":  lambda a, b: a < b,
    ">":  lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
}

PRINT_CASES = [
    PrintCase("var-eq-true",     ['A$="YES"'],
              'PRINT A$="YES"', "YES", "=", "YES"),
    PrintCase("var-eq-false",    ['A$="YES"'],
              'PRINT A$="NO"',  "YES", "=", "NO"),
    PrintCase("var-lt-ordering", ['A$="AB"', 'B$="ABC"'],
              "PRINT A$<B$",    "AB",  "<", "ABC"),
    PrintCase("var-le-compound", ['A$="AB"', 'B$="AB"'],
              "PRINT A$<=B$",   "AB",  "<=", "AB"),
    PrintCase("literal-lead",    ['A$="YES"'],
              'PRINT "YES"=A$', "YES", "=", "YES"),
    PrintCase("function-lead",   ['A$="HELLO"'],
              'PRINT LEFT$(A$,1)="H"', "H", "=", "H"),
    PrintCase("concat-lead",     ['A$="HE"', 'B$="LLO"'],
              'PRINT A$+B$="HELLO"', "HELLO", "=", "HELLO"),
]

ABORT_SETUP = ['A$="HI"']
ABORT_LINE = "PRINT A$<5"


def extract_result(screen_text, print_line):
    """The single integer printed on the row directly below the echoed
    `print_line` (direct-mode: typed input echoes, then the item prints on the
    next row -- confirmed live on both the reference and zerobas builds).
    Returns None if the echo isn't found or the following row isn't exactly
    one int (leading/trailing spaces from the MSX number format are fine --
    re.findall strips them)."""
    if screen_text is None:
        return None
    lines = screen_text.split("\n")
    for i, ln in enumerate(lines):
        if print_line in ln:
            if i + 1 >= len(lines):
                return None
            nums = re.findall(r"-?\d+", lines[i + 1])
            return int(nums[0]) if len(nums) == 1 else None
    return None


def extract_next_row(screen_text, print_line):
    """The raw row directly below the echoed `print_line` (whatever it holds --
    an error message for the abort case). None if the echo isn't found."""
    if screen_text is None:
        return None
    lines = screen_text.split("\n")
    for i, ln in enumerate(lines):
        if print_line in ln:
            return lines[i + 1] if i + 1 < len(lines) else None
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE, help="reference machine (built-in BASIC oracle)")
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE,
                    help="zerobas repack machine (string engine is repack-only)")
    ap.add_argument("--only", help="run only cases whose label contains this substring")
    ap.add_argument("--ref-only", action="store_true",
                    help="skip the zerobas side (oracle-lock only)")
    ap.add_argument("--boot-per-case", dest="boot_per_case", action="store_true",
                    help="isolate each case in its own boot instead of the default "
                         "single-boot batch (to rule out inter-case leakage)")
    args = ap.parse_args()

    cases = [c for c in CASES if not args.only or args.only in c[0]]
    printcases = [c for c in PRINT_CASES if not args.only or args.only in c.label]
    want_abort = not args.only or args.only in "abort-mismatch"
    if not cases and not printcases and not want_abort:
        print(f"no cases match --only {args.only!r}")
        return 1

    ok = True
    batch = not args.boot_per_case

    # All three batteries share ONE boot per side: the bit-battery (one compound
    # direct line each), the PRINT-lead cases (setup + PRINT), and the abort case
    # -- each an independent direct-mode case with a ("NEW","CLS") reset between
    # (NEW clears A$/B$, CLS the screen so each capture holds only its own case).
    specs = [("direct", [build_line(lhs, rhs)]) for _, lhs, rhs in cases]
    specs += [("direct", c.setup + [c.print_line]) for c in printcases]
    if want_abort:
        specs.append(("direct", ABORT_SETUP + [ABORT_LINE]))
    ref_raws = omsx_repl.run_cases(args.machine, specs, batch=batch, reset=("NEW", "CLS"))
    zb_raws = (omsx_repl.run_cases(args.zb_machine, specs, batch=batch, reset=("NEW", "CLS"))
               if not args.ref_only else [None] * len(specs))
    n1, n2 = len(cases), len(printcases)

    if cases:
        print(f"--- reference oracle lock ({args.machine}, §2 contract) ---")
        ref_bits = {}
        for (label, lhs, rhs), ref_raw in zip(cases, ref_raws[:n1]):
            want = expected_bits(lhs, rhs)
            got = extract_bits(_rows(ref_raw))
            ref_bits[label] = got
            good = got == want
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} {label:16} {lhs!r:6} vs {rhs!r:6} "
                  f"ops{OPS} got={got} want={want}")

        if not args.ref_only:
            print(f"\n--- zerobas == reference ({args.zb_machine}) ---")
            for (label, lhs, rhs), zb_raw in zip(cases, zb_raws[:n1]):
                ref = ref_bits.get(label)
                zb = extract_bits(_rows(zb_raw))
                good = ref is not None and zb is not None and zb == ref
                ok = ok and good
                print(f"{'PASS' if good else 'FAIL':5} {label:16} zb={zb} ref={ref}")

    # --- unparenthesized PRINT-lead comparisons (print-unparen-compare.md) ---
    if printcases:
        print(f"\n--- reference oracle lock: unparenthesized PRINT-lead "
              f"comparisons ({args.machine}) ---")
        ref_print = {}
        for c, ref_raw in zip(printcases, ref_raws[n1:n1 + n2]):
            want = -1 if OP_EXPECT[c.op](c.lhs, c.rhs) else 0
            got = extract_result(_rows(ref_raw), c.print_line)
            ref_print[c.label] = got
            good = got == want
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} {c.label:16} {c.print_line!r:28} "
                  f"got={got} want={want}")

        if not args.ref_only:
            print(f"\n--- zerobas == reference: unparenthesized PRINT-lead "
                  f"comparisons ({args.zb_machine}) ---")
            for c, zb_raw in zip(printcases, zb_raws[n1:n1 + n2]):
                got = extract_result(_rows(zb_raw), c.print_line)
                ref = ref_print.get(c.label)
                good = ref is not None and got is not None and got == ref
                ok = ok and good
                print(f"{'PASS' if good else 'FAIL':5} {c.label:16} zb={got} ref={ref}")

    # --- D-2: PRINT A$<5 (bare) aborts, printing NOTHING for the item -------
    # Divergence (inherited from the parenthesized form): the reference's own
    # wording is 'Type mismatch', zerobas's is lowercase 'type mismatch' -- both
    # asserted per-machine (substring, case-insensitive) rather than as string
    # equality, same convention basic_probe_mid_stmt.py uses for its range-error
    # wording divergence. The key claim either way: the row right after the
    # echoed PRINT holds an error, not a printed value (no digits).
    if want_abort:
        print(f"\n--- reference oracle lock: unparenthesized type-mismatch "
              f"abort ({args.machine}) ---")
        ref_row = extract_next_row(_rows(ref_raws[n1 + n2]), ABORT_LINE)
        ref_err = ref_row is not None and "type mismatch" in ref_row.lower()
        ref_noval = ref_row is not None and not re.search(r"-?\d", ref_row)
        good = ref_err and ref_noval
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':5} abort-mismatch  ref row={ref_row!r} "
              f"'Type mismatch'={ref_err} no-value={ref_noval}")

        if not args.ref_only:
            print(f"\n--- zerobas: unparenthesized type-mismatch abort "
                  f"({args.zb_machine}) ---")
            zb_row = extract_next_row(_rows(zb_raws[n1 + n2]), ABORT_LINE)
            zb_err = zb_row is not None and "type mismatch" in zb_row.lower()
            zb_noval = zb_row is not None and not re.search(r"-?\d", zb_row)
            good = zb_err and zb_noval
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} abort-mismatch  zb row={zb_row!r} "
                  f"'Type mismatch'={zb_err} no-value={zb_noval}")

    print("\nALL PASS -- reference matches §2/§1, zerobas matches reference "
          "(the type-mismatch message text is now IDENTICAL on both sides: "
          "`Type mismatch`, D-MSGEXACT withdrew the case-wording divergence "
          "this line used to report)" if ok
          else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
