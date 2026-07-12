#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Oracle + differential probe -- string functions (string-functions S3).

HEX$ / OCT$ / SPACE$ / STRING$ / INSTR, per spec-basic-string-functions.md §5.

Two halves, modelled on basic_probe_str_cmp.py:

1. REFERENCE ORACLE (black-box, no disassembly). Types a direct-mode line into
   the real Philips VG-8020's built-in MSX-BASIC (no cartridge -- `cart=None`)
   that PRINTs one verb result, bracket-wrapped so the output is unambiguous.
   Asserts the reference's own output matches the value computed in Python from
   the public MSX-BASIC contract (spec §2) -- the expected value is DERIVED, not
   assumed, exactly like str_cmp's `expected_bits`.

2. ZEROBAS DIFFERENTIAL. Runs the IDENTICAL line on the repack machine
   (C-BIOS_MSX1_EU_REPACK_DISK -- the string engine is repack-only) and asserts
   zerobas's result equals the reference's.

One documented exception to "zerobas == reference": SPACE$/STRING$ clamp their
length to STRMAX=64 (repack build; basic/sysvars.inc:327) -- an OWN-DESIGN
divergence (spec §2/D-3), not present on real hardware (whose own ceiling is
255). For those two "clamp" cases the reference half still asserts the real,
UNCLAMPED result; the zerobas half asserts zerobas's own CLAMPED result
directly (not equality with the reference capture) and prints a "[divergence]"
note -- mirroring how the string-compare slice documented its two divergences
rather than asserting a false equality.

KNOWN ROM BUGS surfaced by this acceptance probe (S3; NOT fixed here -- this
probe is acceptance-only, no basic/*.asm touched; see the S3 report):

  * `PRINT STRING$(...)` as a bare PRINT item (STRING$.num / STRING$.str below)
    spuriously raises "type mismatch". Root cause: basic/print.asm's exp_loop
    item dispatcher special-cases a `$FF`-prefixed function (Group A) and a
    `$`-suffixed string variable, but has NO case for STRING_TOKEN ($E3, Group
    B) -- so it falls through to exp_num -> eval -> ev_rel (basic/expr.asm),
    whose LHS probe correctly recognises STRING$(...) as a string but then
    finds no relational operator following it and raises the D-2 "bare string,
    no relop" mismatch (confirmed via a live TMISMATCH=$01 readback at $E55F).
    `LET A$=STRING$(...)` is unaffected (ex_let_str calls str_eval directly);
    INSTR is unaffected (it returns a number, so exp_num's fallback is
    correct). These two cases are kept as literal, spec-mandated PRINT tests
    (not routed around) so the gate keeps surfacing this defect until fixed.

  * `SPACE$(n)` nested as another function's ARGUMENT (e.g. `LEN(SPACE$(n))`)
    also spuriously raises "type mismatch", via a DIFFERENT mechanism: a live
    readback showed TMISMATCH ($E55F) holding a stray $20 (space) byte, not
    $01 -- and the "or a / jp nz" check that gates the error treats ANY
    nonzero byte as a mismatch. The bytes from $E55D (STRCAT_R) onward were
    also all $20, consistent with SPACE$'s ring-temp fill smearing into the
    sysvars region that sysvars.inc documents as sitting immediately before
    the temp ring. Plain `PRINT SPACE$(n)` (no nesting) and
    `A$=SPACE$(n):PRINT LEN(A$)` are both unaffected -- only the nested-call
    shape trips it (HEX$/OCT$/STRING$ nested the same way do NOT reproduce
    it). Because of this, STRING$.clamp below is measured via
    `LEN(STRING$(...))` rather than a direct print (STRING$ nested in LEN is
    unaffected -- confirmed separately), and SPACE$.clamp is measured via a
    direct, non-nested `PRINT SPACE$(...)` to avoid this bug entirely while
    still exercising the real STRMAX clamp.

Clean-room: this only *observes* black-box behaviour (type a line, read the
screen). The reference ROM is never read as code. See CONTRIBUTING.md.

    python3 probes/basic/basic_probe_str_fn.py
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

# repack build's own-design length clamp (basic/sysvars.inc:327); real hardware
# has no such ceiling (its own limit, ~255, is well above every case tested here).
STRMAX = 64


# --- §2 contract, computed in Python (never assumed) -----------------------

def hex16(n: int) -> str:
    """HEX$(n): n viewed as unsigned-16, uppercase, no leading zeros, >=1 digit."""
    return format(n & 0xFFFF, "X")


def oct16(n: int) -> str:
    """OCT$(n): same, base 8."""
    return format(n & 0xFFFF, "o")


def space_of(n: int, clamp: int | None = None) -> str:
    """SPACE$(n): n spaces, optionally clamped (zerobas own-design only)."""
    if clamp is not None:
        n = min(n, clamp)
    return " " * n


def string_of(n: int, fillchar: str, clamp: int | None = None) -> str:
    """STRING$(n,c): n copies of a single fill char, optionally clamped."""
    if clamp is not None:
        n = min(n, clamp)
    return fillchar * n


def instr_at(a: str, b: str, p: int = 1) -> int:
    """INSTR([p,]a$,b$): 1-based position of b$ in a$ from p (default 1), 0 if
    not found; empty b$ -> p clamped into [1, len(a)+1]."""
    if b == "":
        return max(1, min(p, len(a) + 1))
    idx = a.find(b, max(0, p - 1))
    return idx + 1 if idx != -1 else 0


# --- battery -----------------------------------------------------------------
# (label, kind, line, expect_ref, expect_zb, note)
#   kind        'str' (bracket content compared verbatim, spaces significant)
#               or 'num' (bracket content parsed as an int, whitespace ignored)
#   expect_ref  the DERIVED value the reference's own PRINT must produce
#   expect_zb   None => zerobas must equal the CAPTURED reference value
#               (the normal "zerobas == reference" contract); otherwise
#               zerobas is asserted to equal this value directly (a documented
#               own-design divergence -- see module docstring)
#   note        None, or a short divergence explanation printed with the case
Case = namedtuple("Case", "label kind line expect_ref expect_zb note")

CASES = [
    # HEX$(n) -- {0, 255, 65535, -1} (D-2: unsigned-16 view, no clamp involved)
    Case("HEX$.zero",   "str", 'PRINT "[";HEX$(0);"]"',
         hex16(0), None, None),
    Case("HEX$.255",    "str", 'PRINT "[";HEX$(255);"]"',
         hex16(255), None, None),
    Case("HEX$.65535",  "str", 'PRINT "[";HEX$(65535);"]"',
         hex16(65535), None, None),
    Case("HEX$.neg1",   "str", 'PRINT "[";HEX$(-1);"]"',
         hex16(-1), None, None),

    # OCT$(n) -- {8, 0, -1}
    Case("OCT$.8",      "str", 'PRINT "[";OCT$(8);"]"',
         oct16(8), None, None),
    Case("OCT$.zero",   "str", 'PRINT "[";OCT$(0);"]"',
         oct16(0), None, None),
    Case("OCT$.neg1",   "str", 'PRINT "[";OCT$(-1);"]"',
         oct16(-1), None, None),

    # SPACE$(n) -- {0, 3}. The third battery item, STRMAX+overflow-clamp, wraps
    # across screen rows and is measured separately below (SPACE$.clamp is NOT
    # in this list -- see measure_space_clamp_length and its call in main()).
    Case("SPACE$.zero", "str", 'PRINT "[";SPACE$(0);"]"',
         space_of(0), None, None),
    Case("SPACE$.3",    "str", 'PRINT "[";SPACE$(3);"]"',
         space_of(3), None, None),

    # STRING$(n,c) -- {(3,65)->AAA, (3,"*")->***, clamp}
    Case("STRING$.num", "str", 'PRINT "[";STRING$(3,65);"]"',
         string_of(3, "A"), None, None),
    Case("STRING$.str", "str", 'PRINT "[";STRING$(3,"*");"]"',
         string_of(3, "*"), None, None),
    # clamp: measured via LEN(STRING$(...)) rather than printing the literal
    # 100-char result. Not just a wrapping workaround -- see the KNOWN BUGS
    # section of the module docstring: a bare `PRINT STRING$(...)` item hits a
    # real, separately-confirmed print.asm dispatch defect unrelated to STRMAX,
    # so a direct print of the clamp case would conflate two different
    # findings. LEN(...) isolates exactly the property under test (the clamped
    # COUNT) and is confirmed unaffected by that defect.
    Case("STRING$.clamp", "num", 'PRINT "[";LEN(STRING$(100,"Z"));"]"',
         100, STRMAX,
         f"own-design STRMAX={STRMAX} clamp (spec D-3): zerobas clamps to "
         f"{STRMAX}, real hardware doesn't -- documented divergence"),

    # INSTR([p,]a$,b$) -- {found, not-found->0, empty-needle, 3-arg p mid, p past end->0}
    Case("INSTR.found",    "num", 'PRINT "[";INSTR("HELLO","LL");"]"',
         instr_at("HELLO", "LL"), None, None),
    Case("INSTR.notfound", "num", 'PRINT "[";INSTR("HELLO","Z");"]"',
         instr_at("HELLO", "Z"), None, None),
    Case("INSTR.empty",    "num", 'PRINT "[";INSTR("HELLO","");"]"',
         instr_at("HELLO", ""), None, None),
    Case("INSTR.pmid",     "num", 'PRINT "[";INSTR(3,"ABCABC","B");"]"',
         instr_at("ABCABC", "B", 3), None, None),
    Case("INSTR.ppastend", "num", 'PRINT "[";INSTR(10,"HELLO","L");"]"',
         instr_at("HELLO", "L", 10), None, None),
]


def run_line(machine, cart, line, **_):
    """Inject one direct-mode line via omsx_repl (KEYBUF, typing-free) on
    `machine` (optionally with `cart`) and return the SCREEN 0 name table as one
    raw, row-major string of length NLEN (non-print bytes -> space). No per-row
    separator: the video RAM has no line-break byte, and _marker_positions /
    extract search this flat string directly (the marker arithmetic in
    measure_space_clamp_length needs the raw row-major layout to count wraps)."""
    return omsx_repl.run_case(machine, "direct", [line], cart=cart)


# --- SPACE$.clamp: length-by-marker-arithmetic (avoids the wrap-geometry trap) -
#
# SPACE$(100) (needed to exercise the STRMAX=64 overflow clamp, spec D-3) is
# LONGER than one screen row (~37-39 usable columns; the row width differs
# between machines and isn't a clean round number -- see below), so its
# printed brackets wrap across multiple physical VRAM rows. A naive
# concatenation of full 40-byte rows was tried and rejected: EVERY row (even
# the boot banner, unrelated to any PRINT) carries a constant per-machine
# left margin (2 columns on the reference, 1 on the repack machine), and rows
# that wrap mid-message also reserve one trailing "avoid a phantom blank
# line" column that's NEVER part of the printed content -- both artifacts are
# indistinguishable from genuine SPACE$ output (which is ALSO literal 0x20
# bytes), so counting space characters directly overcounts by the per-row
# overhead (confirmed empirically: naive reconstruction measured 102 spaces
# for a real, verified-100-space result).
#
# Fix: bracket the result with a UNIQUE non-space marker ('#') and measure
# the RAW (unstripped) row-major byte distance between '[' and '#'. That
# distance equals n + (rows_crossed * per-row-overhead) -- the overhead is a
# pure screen-geometry constant (same regardless of content), so it is
# calibrated once from a run of a KNOWN length chosen to force at least one
# wrap, then subtracted back out of the real (unknown-until-measured) run.
# Verified against the independently-known-correct STRMAX clamp (already
# proven via LEN(STRING$(100,"Z"))=64): this method reproduces exactly 100 on
# the reference and exactly 64 on the repack machine.
CALIB_N = 50  # comfortably forces >=1 wrap on both machines' row widths


def _marker_positions(raw):
    """Indices of the LAST '[', '#' in `raw` (the real result -- printed after
    the echoed source line, which also contains a literal '[' but no '#'),
    provided they're in '[' < '#' < ']' order. None if not found/malformed."""
    if raw is None:
        return None
    i_open = raw.rfind('[')
    i_hash = raw.rfind('#')
    i_close = raw.rfind(']')
    if not (0 <= i_open < i_hash < i_close):
        return None
    return i_open, i_hash


def measure_space_clamp_length(machine, cart, n, calib_n=CALIB_N, timeout=180):
    """The true printed length of SPACE$(n) via marker arithmetic (see above).
    Returns None if the capture or the wrap-geometry assumption fails (a
    non-integer overhead means the per-row-crossing model didn't hold --
    treated as a probe failure, never silently reported as 0)."""
    calib_pos = _marker_positions(
        run_line(machine, cart, f'PRINT "[";SPACE$({calib_n});"#";"]"', timeout=timeout))
    if calib_pos is None:
        return None
    c_open, c_hash = calib_pos
    crossings = c_hash // COLS - c_open // COLS
    if crossings == 0:
        return None                          # calib_n didn't wrap -- can't derive overhead
    overhead = (c_hash - c_open - 1 - calib_n) / crossings
    if overhead != int(overhead) or overhead < 0:
        return None
    overhead = int(overhead)

    pos = _marker_positions(
        run_line(machine, cart, f'PRINT "[";SPACE$({n});"#";"]"', timeout=timeout))
    if pos is None:
        return None
    o_open, o_hash = pos
    x = o_hash // COLS - o_open // COLS
    return (o_hash - o_open - 1) - x * overhead


def extract(raw_text, kind):
    """Pull the bracket contents out of the raw screen text. The echoed source
    line itself contains a literal `"["`/`"]"` pair (the PRINT statement's own
    bracket delimiters) BEFORE the real result's `[`/`]` pair is printed, so a
    naive first-match `\\[...\\]` search can find the echo instead of the
    result. The screen scrolls top-down in chronological order, so the actual
    result -- printed after the echo -- is always the LAST non-nested bracket
    pair in the raw (row-major) text; take that one.

    kind='str' -> the raw string content (leading/trailing spaces are
    significant, e.g. SPACE$/STRING$ results -- do not strip).
    kind='num' -> the content parsed as an int (surrounding blanks stripped;
    MSX PRINT pads a numeric item with sign/zone spaces)."""
    if raw_text is None:
        return None
    matches = re.findall(r"\[([^\[\]]*)\]", raw_text)
    if not matches:
        return None
    content = matches[-1]
    if kind == "num":
        s = content.strip()
        return int(s) if re.fullmatch(r"-?\d+", s) else None
    return content


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

    cases = [c for c in CASES if not args.only or args.only in c.label]
    want_clamp = not args.only or args.only in "SPACE$.clamp"
    if not cases and not want_clamp:
        print(f"no cases match --only {args.only!r}")
        return 1

    ok = True

    if cases:
        print(f"--- reference oracle lock ({args.machine}, §2 contract) ---")
        ref_captured = {}
        for c in cases:
            got = extract(run_line(args.machine, None, c.line, timeout=180), c.kind)
            ref_captured[c.label] = got
            good = got == c.expect_ref
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} {c.label:16} {c.line}")
            print(f"        got={got!r} want={c.expect_ref!r}")

    # SPACE$.clamp: not in CASES (it wraps across screen rows -- measured via
    # marker arithmetic, see measure_space_clamp_length above). Reference
    # expects the REAL, unclamped length; zerobas expects its own STRMAX-
    # clamped length (documented D-3 divergence, same convention as the other
    # clamp case, STRING$.clamp, above).
    if want_clamp:
        clamp_n = 100
        ref_len = measure_space_clamp_length(args.machine, None, clamp_n, timeout=180)
        good = ref_len == clamp_n
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':5} {'SPACE$.clamp':16} "
              f"PRINT SPACE$({clamp_n}) [ref, marker-measured]")
        print(f"        got={ref_len!r} want={clamp_n!r}")

    if not args.ref_only:
        if cases:
            print(f"\n--- zerobas == reference ({args.zb_machine}) ---")
            for c in cases:
                zb = extract(run_line(args.zb_machine, None, c.line, timeout=120), c.kind)
                if c.expect_zb is None:
                    ref = ref_captured.get(c.label)
                    good = ref is not None and zb is not None and zb == ref
                    ok = ok and good
                    print(f"{'PASS' if good else 'FAIL':5} {c.label:16} zb={zb!r} ref={ref!r}")
                else:
                    # documented own-design divergence: zerobas is checked against
                    # its OWN expected value, not the (deliberately different) real
                    # reference capture.
                    good = zb == c.expect_zb
                    ok = ok and good
                    print(f"{'PASS' if good else 'FAIL':5} {c.label:16} zb={zb!r} "
                          f"want_zb={c.expect_zb!r} (ref={ref_captured.get(c.label)!r}) "
                          f"[divergence: {c.note}]")

        if want_clamp:
            zb_len = measure_space_clamp_length(args.zb_machine, None, clamp_n, timeout=120)
            good = zb_len == STRMAX
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} {'SPACE$.clamp':16} "
                  f"zb={zb_len!r} want_zb={STRMAX!r} (ref={clamp_n!r}) "
                  f"[divergence: own-design STRMAX={STRMAX} clamp (spec D-3): "
                  f"zerobas clamps, real hardware doesn't]")

    print("\nALL PASS -- reference matches §2, zerobas matches reference "
          "(clamp cases match zerobas's own documented D-3 semantics)" if ok
          else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
