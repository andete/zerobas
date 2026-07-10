#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Oracle + differential probe -- string comparison (string-compare S2).

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

Clean-room: this only *observes* black-box behaviour (type a line, read the
screen). The reference ROM is never read as code. See CONTRIBUTING.md.

    python3 probes/basic/basic_probe_str_cmp.py
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OMSX_RUN = os.path.join(REPO, "probes", "lib", "omsx_run.py")

REF_MACHINE = "Philips_VG_8020"    # reference: built-in MSX-BASIC, no cartridge
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
COLS, ROWS = 40, 24
NLEN = COLS * ROWS

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


def run_line(machine, cart, line, base=8.0, tail=8.0, timeout=120):
    """Type one direct-mode line (+ a separately-timed Enter) on `machine`, with
    or without `cart`, then capture the SCREEN 0 name table (same technique as
    basic_probe_print.py / basic_probe_string.py)."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="strcmp_cap_")
    os.close(out_fd)
    cmd = [sys.executable, OMSX_RUN, "--machine", machine]
    if cart:
        cmd += ["--cart", cart]
    cmd += ["--type", line, "--type-delay", str(base),
            "--type", "\r", "--type-delay", str(base + 3),
            "--time", str(base + 3 + tail),
            "--mem", f"VRAM:0x0000:{NLEN}",
            "--out", out_path, "--timeout", str(timeout)]
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cap = ""
    if os.path.exists(out_path):
        with open(out_path) as f:
            cap = f.read()
        os.unlink(out_path)
    m = re.search(rf"mem\.VRAM:0x0000:{NLEN}=([0-9a-f]+)", cap)
    if not m:
        return None
    data = bytes.fromhex(m.group(1))
    rows = ["".join(chr(c) if 32 <= c < 127 else " " for c in
                     data[r * COLS:(r + 1) * COLS]) for r in range(ROWS)]
    return "\n".join(rows)


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE, help="reference machine (built-in BASIC oracle)")
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE,
                    help="zerobas repack machine (string engine is repack-only)")
    ap.add_argument("--only", help="run only cases whose label contains this substring")
    ap.add_argument("--ref-only", action="store_true",
                    help="skip the zerobas side (oracle-lock only)")
    args = ap.parse_args()

    cases = [c for c in CASES if not args.only or args.only in c[0]]
    if not cases:
        print(f"no cases match --only {args.only!r}")
        return 1

    ok = True

    print(f"--- reference oracle lock ({args.machine}, §2 contract) ---")
    ref_bits = {}
    for label, lhs, rhs in cases:
        line = build_line(lhs, rhs)
        want = expected_bits(lhs, rhs)
        got = extract_bits(run_line(args.machine, None, line, timeout=180))
        ref_bits[label] = got
        good = got == want
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':5} {label:16} {lhs!r:6} vs {rhs!r:6} "
              f"ops{OPS} got={got} want={want}")

    if not args.ref_only:
        print(f"\n--- zerobas == reference ({args.zb_machine}) ---")
        for label, lhs, rhs in cases:
            line = build_line(lhs, rhs)
            ref = ref_bits.get(label)
            zb = extract_bits(run_line(args.zb_machine, None, line, timeout=120))
            good = ref is not None and zb is not None and zb == ref
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} {label:16} zb={zb} ref={ref}")

    print("\nALL PASS -- reference matches §2, zerobas matches reference" if ok
          else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
