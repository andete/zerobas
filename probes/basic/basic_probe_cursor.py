#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Cursor / PRINT-positioning characterization — CSRLIN, POS, TAB( and SPC(.

WHY THIS EXISTS
===============
docs/decision-kwgaps-slicing.md §4.3 step 2: the cursor/PRINT cluster, four of
the eight SILENT-GAP words from the keyword sweep. All four currently parse as
something else and compute a wrong answer with no error:

    CSRLIN   parses as the variable `CS`      -> always 0
    POS(n)   parses as the ARRAY `POS`        -> 0, or Subscript out of range
    TAB(n)   parses as the ARRAY `TAB`        -> the trap that started the sweep:
             `PRINT TAB(99999)` raises ERR 6 on BOTH sides, for structurally
             different reasons, so a differential AGREED while TAB( was absent
    SPC(n)   parses as the ARRAY `SPC`        -> same shape

This probe measures what they actually do on the VG-8020, so the spec is
dictated rather than asserted.

TWO READOUTS, BECAUSE A VALUE AND A POSITION ARE DIFFERENT QUESTIONS
====================================================================
CSRLIN and POS return NUMBERS -> the `[...]` bracket convention reads them.

TAB( and SPC( produce WHITESPACE, and whitespace is invisible to a value
readout. They are measured by POSITION instead: every case starts with `CLS`, so
output begins at screen row 0 column 0 with the typed echo wiped, and the probe
reports the (row, col) where a marker character landed. That also catches the
answers a value readout structurally cannot -- whether an over-wide TAB( wraps to
the next row, and where it lands when the cursor is ALREADY past the target.

DELIBERATELY NOT MEASURED THROUGH POS()
=======================================
The tempting readout for TAB(/SPC( is `PRINT TAB(10);POS(0)` -- ask the ROM where
it put the cursor. That is circular: POS is one of the four unimplemented words
under test, so a wrong POS and a wrong TAB( could cancel and read as correct.
The screen grid is an INDEPENDENT instrument; POS is measured against it, not
with it.

CALIBRATION
===========
Rows that use none of the four (plain `PRINT`, `;`/`,` separators, the comma
zone width, the line-wrap column) run on BOTH machines and must agree. They fix
the instrument -- screen width, wrap column and comma-zone stride are properties
of the terminal, not of these four keywords, and if they disagree then every
column number below is measuring the wrong thing.

Clean-room: types lines, reads the screen. The reference ROM is never read as
code. See CONTRIBUTING.md.

USAGE
    python3 probes/basic/basic_probe_cursor.py
    ... --gate            # treat all four as implemented -> every row two-sided
    ... --only pos        # one battery: val | pos | err
    ... --boot-per-case
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
COLS, ROWS = 40, 24

# The four words under test. A case naming any of them is NOT calibration until
# --gate says they are implemented.
UNDER_TEST = ("CSRLIN", "POS", "TAB", "SPC")

# --- battery 1: VALUE rows (bracket readout) ---------------------------------
# Every row leads with CLS so the cursor starts at a known home position --
# otherwise CSRLIN just reports wherever the harness happened to leave it.
VALUE = [
    ("csrlin-home",    'PRINT "[";CSRLIN;"]"'),
    ("csrlin-nextrow", 'PRINT:PRINT "[";CSRLIN;"]"'),
    ("csrlin-3rows",   'PRINT:PRINT:PRINT "[";CSRLIN;"]"'),
    ("csrlin-assign",  'WIDTH 40:CLS:X=CSRLIN:PRINT "[";X;"]"'),
    ("csrlin-arith",   'PRINT "[";CSRLIN+10;"]"'),
    ("pos-home",       'PRINT "[";POS(0);"]"'),
    ("pos-after2",     'PRINT "AB";"[";POS(0);"]"'),
    ("pos-after5",     'PRINT "ABCDE";"[";POS(0);"]"'),
    ("pos-assign",     'WIDTH 40:CLS:X=POS(0):PRINT "[";X;"]"'),
    # the argument is documented as a dummy -- measure whether it is IGNORED
    ("pos-arg1",       'PRINT "[";POS(1);"]"'),
    ("pos-arg99",      'PRINT "[";POS(99);"]"'),
    ("pos-argneg",     'PRINT "[";POS(-1);"]"'),
    ("pos-argexpr",    'PRINT "[";POS(1+1);"]"'),
]

# --- battery 2: POSITION rows (screen-grid readout) --------------------------
# 'X' is the marker; the probe reports where it landed as row,col.
POSN = [
    # The marker is CHR$(35) -- '#' emitted, but the literal character never
    # appears in the TYPED LINE. That matters: an earlier version used a literal
    # "X" and, on a case that had lost its CLS, the grid search happily found the
    # X inside the ECHOED COMMAND and reported a confident, entirely wrong column.
    # A marker that cannot appear in the echo makes that failure impossible rather
    # than unlikely.
    ("tab-10",        'WIDTH 40:CLS:PRINT TAB(10);CHR$(35)'),
    ("tab-0",         'WIDTH 40:CLS:PRINT TAB(0);CHR$(35)'),
    ("tab-1",         'WIDTH 40:CLS:PRINT TAB(1);CHR$(35)'),
    ("tab-after2",    'WIDTH 40:CLS:PRINT "AB";TAB(10);CHR$(35)'),
    ("tab-past",      'WIDTH 40:CLS:PRINT "ABCDEFGHIJ";TAB(3);CHR$(35)'),
    ("tab-exact",     'WIDTH 40:CLS:PRINT "ABCDE";TAB(5);CHR$(35)'),
    ("tab-nosemi",    'WIDTH 40:CLS:PRINT TAB(10)CHR$(35)'),
    ("tab-comma",     'WIDTH 40:CLS:PRINT TAB(10),CHR$(35)'),
    ("tab-float",     'WIDTH 40:CLS:PRINT TAB(10.7);CHR$(35)'),
    ("tab-wide",      'WIDTH 40:CLS:PRINT TAB(39);CHR$(35)'),
    ("tab-verywide",  'WIDTH 40:CLS:PRINT TAB(45);CHR$(35)'),
    ("tab-twice",     'WIDTH 40:CLS:PRINT TAB(5);TAB(12);CHR$(35)'),
    ("spc-5",         'WIDTH 40:CLS:PRINT SPC(5);CHR$(35)'),
    ("spc-0",         'WIDTH 40:CLS:PRINT SPC(0);CHR$(35)'),
    ("spc-after2",    'WIDTH 40:CLS:PRINT "AB";SPC(5);CHR$(35)'),
    ("spc-float",     'WIDTH 40:CLS:PRINT SPC(5.7);CHR$(35)'),
    ("spc-wide",      'WIDTH 40:CLS:PRINT SPC(39);CHR$(35)'),
    ("spc-verywide",  'WIDTH 40:CLS:PRINT SPC(45);CHR$(35)'),
    ("spc-then-tab",  'WIDTH 40:CLS:PRINT SPC(5);TAB(12);CHR$(35)'),
    # calibration: the instrument itself. WIDTH 40 is PINNED on every row because
    # the two machines boot at DIFFERENT widths (reference 37, zerobas 39) -- a
    # real divergence, but a console one, and comparing absolute columns across
    # two different text widths would have measured that instead of TAB(/SPC(.
    ("cal-plain",     'WIDTH 40:CLS:PRINT CHR$(35)'),
    ("cal-lead2",     'WIDTH 40:CLS:PRINT "AB";CHR$(35)'),
    ("cal-comma",     'WIDTH 40:CLS:PRINT "A",CHR$(35)'),
    ("cal-comma2",    'WIDTH 40:CLS:PRINT "A","B",CHR$(35)'),
    ("cal-wrap",      'WIDTH 40:CLS:PRINT "0123456789012345678901234567890123456789";CHR$(35)'),
    ("cal-newline",   'WIDTH 40:CLS:PRINT "A":PRINT CHR$(35)'),
]

# --- battery 3: ERROR / scope rows (bracket or error readout) ----------------
# NOTE these rows deliberately do NOT lead with `WIDTH 40:CLS:` like the other
# two batteries. CLS wipes the typed echo, and screen_tail anchors the error text
# on that echo -- with CLS every row read `<no result>` and the whole battery
# measured nothing. Cursor position is irrelevant to an error row anyway.
ERRS = [
    # No `CLS:` here, unlike the other two batteries: CLS wipes the typed echo,
    # and the readout anchors the result text on that echo. With CLS every row
    # read `<no result>` and the battery measured nothing. Cursor position is
    # irrelevant to an error row anyway.
    ("tab-neg",        'PRINT TAB(-1);"Z"'),
    ("spc-neg",        'PRINT SPC(-1);"Z"'),
    ("tab-255",        'PRINT TAB(255);"Z"'),
    ("tab-256",        'PRINT TAB(256);"Z"'),
    ("spc-256",        'PRINT SPC(256);"Z"'),
    ("tab-huge",       'PRINT TAB(99999);"Z"'),
    ("spc-huge",       'PRINT SPC(99999);"Z"'),
    ("tab-bare",       'PRINT TAB(10)'),          # legal: pads, item list ends
    ("pos-noparen",    'PRINT "[";POS;"]"'),      # parens REQUIRED
    ("csrlin-paren",   'PRINT "[";CSRLIN(0);"]"'),# takes NO argument
    # TAB(/SPC( are PRINT-only -- anywhere else is a Syntax error on the
    # reference. Sentinel first: without it, `X=TAB(5)` leaving X at 0 and
    # `X=TAB(5)` erroring with X already 0 are the SAME reading.
    ("tab-outside",    'X=99:X=TAB(5)'),
    ("spc-outside",    'X=99:X=SPC(5)'),
    ("tab-in-if",      'IF TAB(5)=0 THEN Z=1'),
]

# --- battery 4: the PRINT comma-zone rule, across widths ---------------------
# Not one of the four words, but the routine SPC( is meant to share (`pcz_pad`),
# and the calibration battery caught it diverging. Measured at five widths to
# state the RULE rather than one data point.
# THREE items cannot discriminate the rule: zone 3 starts at 28 and 28+14=42
# exceeds every legal SCREEN 0 width, so the reference wraps at all of them and
# "the full zone must fit" and "the start must fit" predict the same thing. The
# TWO-item rows do discriminate -- zone 2 starts at 14, and 14+14=28 lands
# inside the legal width range, so the boundary is observable.
ZONES = [(f"zone3-w{w}", f'WIDTH {w}:CLS:PRINT "A","B",CHR$(35)') for w in
         (40, 32, 28)]
ZONES += [(f"zone2-w{w}", f'WIDTH {w}:CLS:PRINT "A",CHR$(35)') for w in
          (30, 29, 28, 27, 24, 20, 16)]


def rows_of(raw: str | None) -> list[str]:
    if raw is None:
        return []
    return [raw[i * COLS:(i + 1) * COLS] for i in range(ROWS)]


def marker(raw: str | None, ch: str = "#") -> str:
    """Where the marker landed, as 'r,c'. Searches the first few rows, which is
    where a CLS-led case puts its output. 'none' if it never appeared."""
    for r, row in enumerate(rows_of(raw)[:6]):
        c = row.find(ch)
        if c >= 0:
            return f"{r},{c}"
    return "none"


def value(raw: str | None, line: str) -> str:
    if raw is None:
        return "<no capture>"
    span = omsx_repl.result_span_after_echo(raw, line)
    if span is None:
        span = omsx_repl.result_span(raw)
    if span is not None:
        return " ".join(span.split())
    tail = omsx_repl.screen_tail(raw, line)
    if tail:
        tail = " ".join(tail.split())
        if tail:
            return f"ERR:{tail}"
    return "<no result>"


def agree(a: str, b: str) -> bool:
    """zerobas's lowercase error wording is a documented divergence, so error
    rows compare case-insensitively (the kwsweep layer-2 lesson)."""
    if a.startswith("ERR:") and b.startswith("ERR:"):
        return a.lower() == b.lower()
    return a == b


class Case:
    def __init__(self, battery, label, line, readout):
        self.battery = battery
        self.label = label
        self.line = line
        self.readout = readout          # "value" | "marker"
        words = set(re.findall(r"[A-Z]+", line))
        self.calib = not (words & (set(UNDER_TEST) - set(IMPLEMENTED)))
        self.ref = None
        self.zb = None

    def read(self, raw):
        if self.readout == "marker":
            return marker(raw)
        if self.readout == "tail":
            # whatever followed the echo -- an error message OR a printed value.
            # An err row must not go through the bracket readout: the ECHO itself
            # contains `[` and `]`, so a span search happily returns a slice of
            # the command that was typed (`";X;"`) and calls it the answer.
            t = omsx_repl.screen_tail(raw, self.line)
            return " ".join(t.split()) if t else "<no result>"
        return value(raw, self.line)


IMPLEMENTED: set[str] = set()


def main() -> int:
    global IMPLEMENTED
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE)
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--only", help="val | pos | err")
    ap.add_argument("--gate", action="store_true",
                    help="treat CSRLIN/POS/TAB(/SPC( as implemented -> every row "
                         "becomes a two-sided differential (the acceptance gate)")
    ap.add_argument("--boot-per-case", dest="boot_per_case", action="store_true")
    args = ap.parse_args()
    if args.gate:
        IMPLEMENTED = set(UNDER_TEST)

    bat = {
        "val": [Case("val", lb, ln, "value") for lb, ln in VALUE],
        "pos": [Case("pos", lb, ln, "marker") for lb, ln in POSN],
        "err": [Case("err", lb, ln, "tail") for lb, ln in ERRS],
        "zone": [Case("zone", lb, ln, "marker") for lb, ln in ZONES],
    }
    if args.only:
        if args.only not in bat:
            print(f"unknown battery {args.only!r}; pick one of {list(bat)}")
            return 2
        bat = {args.only: bat[args.only]}
    cases = [c for b in bat.values() for c in b]
    batch = not args.boot_per_case

    both = [c for c in cases if c.calib]
    refonly = [c for c in cases if not c.calib]

    if both:
        print(f"# {len(both)} two-sided -> {args.machine} + {args.zb_machine}")
        specs = [("direct", [c.line]) for c in both]
        _, rr, zz = omsx_repl.run_differential(
            args.machine, args.zb_machine, specs,
            lambda i, r, z: agree(both[i].read(r), both[i].read(z)),
            batch=batch, reset=("NEW", "CLS"))
        for c, r, z in zip(both, rr, zz):
            c.ref, c.zb = c.read(r), c.read(z)
    if refonly:
        print(f"# {len(refonly)} reference-only -> {args.machine}")
        raws = omsx_repl.run_cases(args.machine,
                                   [("direct", [c.line]) for c in refonly],
                                   batch=batch, reset=("NEW", "CLS"))
        for c, raw in zip(refonly, raws):
            c.ref = c.read(raw)

    ok = True
    if both:
        bad = 0
        print("\n=== CALIBRATION / GATE (must AGREE) ===")
        for c in both:
            good = agree(c.ref, c.zb)
            bad += not good
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} {c.battery:4} {c.label:14} "
                  f"{c.line[:38]:38} ref={c.ref:>14}  zb={c.zb:>14}")
        print(f"--- {len(both) - bad}/{len(both)} agree"
              + ("" if not bad else "   <-- red"))

    for name, title in (("val", "VALUES (CSRLIN / POS)"),
                        ("pos", "POSITIONS (row,col of the marker)"),
                        ("err", "ERRORS / SCOPE"),
                        ("zone", "PRINT COMMA-ZONE RULE, by width")):
        if name not in bat:
            continue
        print(f"\n=== {title} — the ROM dictates ===")
        for c in bat[name]:
            twin = f"   zb={c.zb}" if c.zb is not None else ""
            print(f"  {c.label:14} {c.line[:42]:42} -> {c.ref}{twin}")

    print("\n" + ("OK" if ok else "ATTENTION: see FAIL rows above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
