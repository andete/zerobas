#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""BIN$ / FRE characterization -- the last two SILENT-GAP words.

WHY THIS EXISTS
===============
docs/decision-kwgaps-slicing.md §4.3 step 4: the final pair. After this the
SILENT-GAP class is EMPTY -- no MSX1 reserved word silently computes a wrong
answer. Today both parse as something else and answer without complaint:

    BIN$(n)  parses as the STRING ARRAY `BIN$`  -> "" (empty, no error)
    FRE(x)   parses as the ARRAY `FRE`          -> 0

THE TWO WORDS POSE OPPOSITE MEASUREMENT PROBLEMS
================================================
BIN$ is a PURE FUNCTION of its argument. Every answer is comparable across the
two machines, and it has a family already implemented on BOTH sides -- HEX$ and
OCT$ -- which share its argument domain. Those rows are the calibration: they
pin the family's coercion rule using code that is not under test, and any
divergence they turn up is a pre-existing bug found for free (which is how the
last two slices in this arc each found two).

FRE reports MEMORY, and the two machines do not have the same memory. Its
absolute value is NOT comparable and never will be -- a gate that asserts one is
asserting zerobas's memory map equals a VG-8020's. So FRE is measured almost
entirely through RELATIONS, which survive the difference:

    FRE(0)=FRE("")        do the two forms agree?      (yes/no, not a number)
    X=FRE(0):DIM..:X-FRE(0)   what did the allocation COST?  (a delta)
    CLEAR 500:FRE("")     <- the exception, and the important one

CLEAR PINS THE INSTRUMENT (cf. WIDTH 40 in the cursor slice)
============================================================
String space is not a property of the machine -- it is set by the program, with
CLEAR. After `CLEAR 500` both machines have been TOLD to have 500 bytes of
string pool, so `FRE("")` becomes an absolute that IS legitimately comparable.
That is the only absolute FRE row this probe gates, and it is the one that can
tell a real off-by-one from a memory-map difference. Everything measured before
a CLEAR is reference-only and recorded for the documentation, never compared.

Clean-room: types lines, reads the screen. The reference ROM is never read as
code. See CONTRIBUTING.md.

USAGE
    python3 probes/basic/basic_probe_binfre.py
    ... --gate              # treat BIN$/FRE as implemented -> every row two-sided
    ... --only bin          # one battery: cal | bin | binerr | layout | fre | depth | freabs
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

# A case naming either of these is NOT calibration until --gate says otherwise.
# Matched against the bare uppercase words of the line, so `BIN$` reads as BIN.
UNDER_TEST = ("BIN", "FRE")

# --- battery 1: the HEX$/OCT$ CALIBRATION -----------------------------------
# BIN$ is the third member of a family whose other two members are implemented
# on BOTH sides. These rows never mention BIN$, so they are two-sided from the
# start, and they answer the questions the spec actually needs answered about
# BIN$: what is the argument domain, how is a float coerced, what does a
# negative do, where does it stop being legal. Measuring those on HEX$/OCT$ is
# strictly better than measuring them on BIN$ -- the answers come with a
# working implementation attached, so a divergence here is a bug I already have.
CAL = [
    ("hex-5",        'PRINT "[";HEX$(5);"]"'),
    ("hex-0",        'PRINT "[";HEX$(0);"]"'),
    ("hex-255",      'PRINT "[";HEX$(255);"]"'),
    ("hex-65535",    'PRINT "[";HEX$(65535);"]"'),
    # the sign question: is the domain -32768..65535 folded into one unsigned
    # 16-bit view? HEX$(-1) says so if it answers FFFF.
    ("hex-neg1",     'PRINT "[";HEX$(-1);"]"'),
    ("hex-neg32768", 'PRINT "[";HEX$(-32768);"]"'),
    # float coercion: TRUNCATE toward zero, or ROUND? 5.7 discriminates; 5.2
    # does not, and .5 would not distinguish round-half-up from round-to-even.
    ("hex-float7",   'PRINT "[";HEX$(5.7);"]"'),
    ("hex-float2",   'PRINT "[";HEX$(5.2);"]"'),
    ("hex-floatneg", 'PRINT "[";HEX$(-5.7);"]"'),
    ("oct-8",        'PRINT "[";OCT$(8);"]"'),
    ("oct-0",        'PRINT "[";OCT$(0);"]"'),
    ("oct-65535",    'PRINT "[";OCT$(65535);"]"'),
    ("oct-neg1",     'PRINT "[";OCT$(-1);"]"'),
    # LEN is how the digit COUNT is read without trusting the screen columns --
    # and the count is what tells the implementation how big its buffer must be.
    ("hex-len",      'PRINT "[";LEN(HEX$(65535));"]"'),
    ("oct-len",      'PRINT "[";LEN(OCT$(65535));"]"'),
    ("hex-concat",   'PRINT "[";"<"+HEX$(10)+">";"]"'),
    ("hex-assign",   'A$=HEX$(255):PRINT "[";A$;"]"'),
]

# --- battery 2: BIN$ VALUES (reference-only until --gate) --------------------
BIN = [
    ("bin-5",        'PRINT "[";BIN$(5);"]"'),
    ("bin-0",        'PRINT "[";BIN$(0);"]"'),
    ("bin-1",        'PRINT "[";BIN$(1);"]"'),
    ("bin-2",        'PRINT "[";BIN$(2);"]"'),
    ("bin-255",      'PRINT "[";BIN$(255);"]"'),
    ("bin-256",      'PRINT "[";BIN$(256);"]"'),
    ("bin-32767",    'PRINT "[";BIN$(32767);"]"'),
    ("bin-32768",    'PRINT "[";BIN$(32768);"]"'),
    ("bin-65535",    'PRINT "[";BIN$(65535);"]"'),
    ("bin-neg1",     'PRINT "[";BIN$(-1);"]"'),
    ("bin-neg2",     'PRINT "[";BIN$(-2);"]"'),
    ("bin-neg32768", 'PRINT "[";BIN$(-32768);"]"'),
    ("bin-float7",   'PRINT "[";BIN$(5.7);"]"'),
    ("bin-floatneg", 'PRINT "[";BIN$(-5.7);"]"'),
    # THE BUFFER QUESTION. HEX$/OCT$ build their digits in NUMBUF, which is 8
    # bytes; a 16-bit BIN$ is up to SIXTEEN digits and cannot. Reading the
    # length here is what turns that from an assumption into a measurement.
    ("bin-len-max",  'PRINT "[";LEN(BIN$(65535));"]"'),
    ("bin-len-0",    'PRINT "[";LEN(BIN$(0));"]"'),
    ("bin-len-1",    'PRINT "[";LEN(BIN$(1));"]"'),
    ("bin-len-256",  'PRINT "[";LEN(BIN$(256));"]"'),
    ("bin-concat",   'PRINT "[";"<"+BIN$(5)+">";"]"'),
    ("bin-assign",   'A$=BIN$(5):PRINT "[";A$;"]"'),
    # nesting the two directions: does a 16-digit temp survive being an operand?
    ("bin-val",      'PRINT "[";LEN(BIN$(65535)+BIN$(65535));"]"'),
]

# --- battery 3: BIN$ / FRE ERROR + SCOPE rows -------------------------------
# NO leading CLS on this battery: the readout anchors on the typed echo and CLS
# erases it, which reads as <no result> for every row (the cursor slice lost a
# whole battery to exactly this).
ERRS = [
    ("bin-65536",    'PRINT BIN$(65536)'),
    ("bin-neg32769", 'PRINT BIN$(-32769)'),
    ("bin-noparen",  'PRINT BIN$'),
    ("bin-empty",    'PRINT BIN$()'),
    ("bin-str",      'PRINT BIN$("A")'),
    ("bin-nodollar", 'PRINT BIN(5)'),
    ("fre-noparen",  'PRINT FRE'),
    ("fre-empty",    'PRINT FRE()'),
    ("fre-twoarg",   'PRINT FRE(0,0)'),
    # CALIBRATION for every BIN$ row above it. These are the SAME five questions
    # asked of the family member that is already implemented on both sides, so
    # BIN$'s entire error contract gets pinned by code that is not under test --
    # and a divergence here is a pre-existing bug, found for free.
    ("hexc-65536",   'PRINT HEX$(65536)'),
    ("hexc-neg32769",'PRINT HEX$(-32769)'),
    ("hexc-noparen", 'PRINT HEX$'),
    ("hexc-empty",   'PRINT HEX$()'),
    ("hexc-str",     'PRINT HEX$("A")'),
    ("octc-65536",   'PRINT OCT$(65536)'),
]

# --- battery 4b: THE VARIABLE / ARRAY TABLE LAYOUT, via VARPTR --------------
# D-BF-B was signed off as "gate all the allocation-cost deltas", which asserts
# zerobas's variable and array table layout matches the VG-8020 byte for byte.
# That is a real claim, and it can be CHECKED BEFORE A LINE OF FRE IS WRITTEN:
# VARPTR is implemented on both sides, and the stride between two consecutive
# entries IS the entry size the deltas are made of. If these agree, the FRE
# deltas will agree for the right reason; if they disagree, the FRE slice has
# discovered a layout divergence and D-BF-B needs re-asking with evidence
# instead of being implemented toward blindly.
#
# Strides, not addresses -- an absolute VARPTR is a memory-map fact and no more
# comparable than an absolute FRE.
LAYOUT = [
    ("lay-scalar",   'X=0:Y=0:PRINT "[";VARPTR(Y)-VARPTR(X);"]"'),
    ("lay-scalar2",  'A=0:B=0:PRINT "[";VARPTR(B)-VARPTR(A);"]"'),
    ("lay-scalar3",  'X=0:Y=0:Z=0:PRINT "[";VARPTR(Z)-VARPTR(X);"]"'),
    ("lay-str",      'A$="":B$="":PRINT "[";VARPTR(B$)-VARPTR(A$);"]"'),
    ("lay-mixed",    'X=0:A$="":PRINT "[";VARPTR(A$)-VARPTR(X);"]"'),
    # array stride = elements*elemsize + header; two identical DIMs isolate it
    ("lay-ary10",    'DIM A(10),B(10):PRINT "[";VARPTR(B(0))-VARPTR(A(0));"]"'),
    ("lay-ary100",   'DIM A(100),B(10):PRINT "[";VARPTR(B(0))-VARPTR(A(0));"]"'),
    ("lay-ary0",     'DIM A(0),B(10):PRINT "[";VARPTR(B(0))-VARPTR(A(0));"]"'),
    # element size on its own -- no header term at all
    ("lay-elem",     'DIM A(10):PRINT "[";VARPTR(A(1))-VARPTR(A(0));"]"'),
    ("lay-elem2",    'DIM A(10):PRINT "[";VARPTR(A(5))-VARPTR(A(0));"]"'),
]

# --- battery 5: IS THE NUMERIC ARGUMENT A DUMMY, OR NOT? --------------------
# The main FRE battery says FRE(0)=FRE("") is FALSE (two pools -- expected) but
# also that FRE(0)=FRE(1) is FALSE, which reads as "the numeric argument
# selects something". That reading has a confound big enough to drive the whole
# spec the wrong way: the two calls in `FRE(0)=FRE(1)` sit at DIFFERENT
# evaluation depths, and if FRE(0) measures down to the stack pointer then the
# deeper call answers differently for a reason that has nothing to do with its
# argument. The `Q=1` row costing 23 where two variable entries account for 20
# is the same hint.
#
# The discriminator is a row where the ARGUMENTS ARE IDENTICAL and only the
# depth differs. If `FRE(0)-FRE(0)` is non-zero, the function is impure and the
# argument was never the variable -- no argument-sensitivity row can be trusted
# until that is settled. The paired rows then re-ask the original question at
# EQUAL depth, with both variables pre-created so that no allocation happens
# between the two calls (the trap that makes the naive `X=FRE(0):Y=FRE(0)`
# differ by the cost of creating Y).
DEPTH = [
    # THE DISCRIMINATOR: same argument, two depths. Non-zero => impure.
    ("dep-same-num", 'PRINT "[";FRE(0)-FRE(0);"]"'),
    ("dep-diff-num", 'PRINT "[";FRE(0)-FRE(1);"]"'),
    ("dep-same-str", 'PRINT "[";FRE("")-FRE("");"]"'),
    # deeper nesting on one side only -- if depth is the variable, more parens
    # should move it further.
    ("dep-paren",    'PRINT "[";FRE(0)-(FRE(0));"]"'),
    ("dep-paren2",   'PRINT "[";FRE(0)-((FRE(0)));"]"'),
    # EQUAL DEPTH, both variables pre-created so nothing is allocated between
    # the two calls. This is the original question, asked so it can be answered.
    ("eq-control",   'X=0:Y=0:X=FRE(0):Y=FRE(0):PRINT "[";X-Y;"]"'),
    ("eq-argdiff",   'X=0:Y=0:X=FRE(0):Y=FRE(1):PRINT "[";X-Y;"]"'),
    ("eq-argrev",    'X=0:Y=0:X=FRE(1):Y=FRE(0):PRINT "[";X-Y;"]"'),
    ("eq-arghuge",   'X=0:Y=0:X=FRE(0):Y=FRE(255):PRINT "[";X-Y;"]"'),
    ("eq-argstr",    'X=0:Y=0:X=FRE(""):Y=FRE("ABCDE"):PRINT "[";X-Y;"]"'),
]

# --- battery 4: FRE, measured as RELATIONS ----------------------------------
# Every row here answers with -1/0 or a small delta, never with a memory
# address. That is what makes them comparable across two different machines.
#
# EVERY numeric-form row here reads its two endpoints at the SAME evaluation
# depth, via pre-created variables. That is not a style choice. The `depth`
# battery below measures FRE(0) counting down to the STACK POINTER at 6 bytes
# per nesting level, so the natural `X=FRE(0): <allocate> :PRINT X-FRE(0)`
# straddles two depths and folds the evaluator's own frame size into the
# answer. Gating that number would demand zerobas's expression evaluator have a
# VG-8020-sized stack frame -- an internal, not a language contract, and the
# measurement's own cost masquerading as the thing measured (the T4 lesson).
# The equal-depth form cancels the frame term and leaves the allocation cost.
FRE = [
    # shape: is there a plausible amount of memory at all, and is the value
    # signed (i.e. does a >32767 pool read as negative)?
    ("fre-pos",      'PRINT "[";FRE(0)>1000;"]"'),
    ("fre-signed",   'PRINT "[";FRE(0)<0;"]"'),
    # do the numeric and string forms report the SAME pool or two pools? This
    # single row decides the whole shape of the implementation. Safe to read at
    # mixed depth: the two pools differ by far more than any frame term.
    ("fre-same",     'PRINT "[";FRE(0)=FRE("");"]"'),
    # is the numeric argument a dummy, like POS's turned out to be? At EQUAL
    # depth this answers the question; at mixed depth it answers a different one
    # and looks like a resounding "no".
    ("fre-argdummy", 'X=0:Y=0:X=FRE(0):Y=FRE(1):PRINT "[";X=Y;"]"'),
    ("fre-argneg",   'X=0:Y=0:X=FRE(0):Y=FRE(-1):PRINT "[";X=Y;"]"'),
    ("fre-arg255",   'X=0:Y=0:X=FRE(0):Y=FRE(255):PRINT "[";X=Y;"]"'),
    # does the string argument's CONTENT matter, or only its TYPE? The string
    # form is depth-immune (dep-same-str = 0), so these read at any depth.
    ("fre-strtype",  'PRINT "[";FRE("")=FRE("ABCDE");"]"'),
    ("fre-strvar",   'A$="ABC":PRINT "[";FRE("")=FRE(A$);"]"'),
    # does allocating actually move it, and BY HOW MUCH? The delta is a
    # property of the variable layout, not of the memory map, so it is
    # comparable -- and if it diverges it is telling me about DIM, not FRE.
    ("fre-dim-drops",'X=FRE(0):DIM A(100):PRINT "[";FRE(0)<X;"]"'),
    ("fre-dim-cost", 'X=0:Y=0:X=FRE(0):DIM A(100):Y=FRE(0):PRINT "[";X-Y;"]"'),
    ("fre-dim-cost2",'X=0:Y=0:X=FRE(0):DIM A(10):Y=FRE(0):PRINT "[";X-Y;"]"'),
    ("fre-var-cost", 'X=0:Y=0:X=FRE(0):Q=1:Y=FRE(0):PRINT "[";X-Y;"]"'),
    # THE POOL-SEPARATION TEST. If the numeric form counts string space too,
    # allocating a string moves it; if the pools are separate, it does not.
    # Every row that allocates a string leads with its OWN `CLEAR 500` rather
    # than relying on the batch reset: --boot-per-case IGNORES reset, so a row
    # that depended on it would read differently in the two delivery modes --
    # and cross-checking the two modes is exactly how an inter-case leak is
    # supposed to be caught. A row that reads the same either way cannot lie
    # about which mode it was run in.
    ("fre-str-num",  'CLEAR 500:X=0:Y=0:X=FRE(0):A$=STRING$(100,"A"):Y=FRE(0):PRINT "[";X-Y;"]"'),
    ("fre-str-str",  'CLEAR 500:X=0:Y=0:X=FRE(""):A$=STRING$(100,"A"):Y=FRE(""):PRINT "[";X-Y;"]"'),
    # GARBAGE COLLECTION. FRE("") is documented to compact the string heap.
    # Make garbage, then ask twice: if the first call collects, the second sees
    # the same number, and the pool is back to where it started.
    ("fre-gc-stable",'CLEAR 500:A$=STRING$(100,"A"):A$="":PRINT "[";FRE("")=FRE("");"]"'),
    ("fre-gc-recov", 'CLEAR 500:X=FRE(""):A$=STRING$(100,"A"):A$="":PRINT "[";FRE("")=X;"]"'),
    # CLEAR PINS THE POOL -> these absolutes ARE comparable. See the header.
    ("fre-clear500", 'CLEAR 500:PRINT "[";FRE("");"]"'),
    ("fre-clear200", 'CLEAR 200:PRINT "[";FRE("");"]"'),
    ("fre-clear100", 'CLEAR 100:PRINT "[";FRE("");"]"'),
    ("fre-clear-use",'CLEAR 500:A$=STRING$(100,"A"):PRINT "[";FRE("");"]"'),
    ("fre-clear-2",  'CLEAR 500:A$=STRING$(100,"A"):B$=STRING$(50,"B"):PRINT "[";FRE("");"]"'),
]

# --- battery 5: FRE ABSOLUTES -- reference-only, RECORDED, never gated ------
# These cannot agree and must not be asserted. They exist so the documentation
# can state what a real VG-8020 reports at boot, which is the only way to judge
# later whether a zerobas number is plausible.
FREABS = [
    ("abs-num",      'PRINT "[";FRE(0);"]"'),
    ("abs-str",      'PRINT "[";FRE("");"]"'),
    ("abs-after",    'DIM A(100):PRINT "[";FRE(0);"]"'),
]

# Rows that are RECORDED but must never be asserted, for two distinct reasons.
#
#   FREABS       -- two machines, two memory maps. Asserting an absolute FRE(0)
#                   asserts the maps are identical.
#   the NUMERIC  -- these measure the VG-8020 expression evaluator's stack frame
#   depth rows      (6 bytes per nesting level), which is an internal of that
#                   ROM, not a property of the language. zerobas is free to have
#                   a different frame, or to measure against a fixed boundary
#                   and answer 0. Gating them would freeze an implementation
#                   detail of a ROM this project deliberately does not copy.
#
# The `eq-*` rows and `dep-same-str` are NOT here: they are depth-neutral by
# construction and do state real contracts (the argument is a dummy; the string
# form is pure). A permanently red row also makes the failure banner permanent,
# and a banner that is always on is one nobody reads.
NEVER_GATED = ({ln for _, ln in FREABS}
               | {ln for lb, ln in DEPTH if lb.startswith("dep-")
                  and lb != "dep-same-str"})


def rows_of(raw: str | None) -> list[str]:
    if raw is None:
        return []
    return [raw[i * COLS:(i + 1) * COLS] for i in range(ROWS)]


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
    """zerobas's lowercase error wording is a documented divergence, so anything
    that looks like an error message compares case-insensitively (the kwsweep
    layer-2 lesson). Keying on an "ERR:" prefix instead reported five CORRECT
    rows as FAIL in the cursor probe -- the tail readout carries no prefix."""
    if a.lower() == b.lower():
        return True
    return a == b


class Case:
    def __init__(self, battery, label, line, readout):
        self.battery = battery
        self.label = label
        self.line = line
        self.readout = readout          # "value" | "tail"
        words = set(re.findall(r"[A-Z]+", line))
        self.calib = (not (words & (set(UNDER_TEST) - set(IMPLEMENTED)))
                      and line not in NEVER_GATED)
        self.never_gated = line in NEVER_GATED
        self.ref = None
        self.zb = None

    def read(self, raw):
        if self.readout == "tail":
            # whatever followed the echo -- an error message OR a printed value.
            # An error row must NOT go through the bracket readout: the echo
            # itself contains `[` and `]`, so a span search happily returns a
            # slice of the command that was typed and calls it the answer.
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
    ap.add_argument("--only", help="cal | bin | binerr | layout | fre | depth | freabs")
    ap.add_argument("--gate", action="store_true",
                    help="treat BIN$/FRE as implemented -> every row becomes a "
                         "two-sided differential (the acceptance gate)")
    ap.add_argument("--boot-per-case", dest="boot_per_case", action="store_true")
    args = ap.parse_args()
    if args.gate:
        IMPLEMENTED = set(UNDER_TEST)

    bat = {
        "cal": [Case("cal", lb, ln, "value") for lb, ln in CAL],
        "bin": [Case("bin", lb, ln, "value") for lb, ln in BIN],
        "binerr": [Case("err", lb, ln, "tail") for lb, ln in ERRS],
        "fre": [Case("fre", lb, ln, "value") for lb, ln in FRE],
        "layout": [Case("lay", lb, ln, "value") for lb, ln in LAYOUT],
        "depth": [Case("dep", lb, ln, "value") for lb, ln in DEPTH],
        "freabs": [Case("abs", lb, ln, "value") for lb, ln in FREABS],
    }
    if args.only:
        if args.only not in bat:
            print(f"unknown battery {args.only!r}; pick one of {list(bat)}")
            return 2
        bat = {args.only: bat[args.only]}
    cases = [c for b in bat.values() for c in b]
    batch = not args.boot_per_case

    both = [c for c in cases if c.calib or c.never_gated]
    refonly = [c for c in cases if not (c.calib or c.never_gated)]

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
            if c.never_gated:               # reported below, never gated
                continue
            bad += not good
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} {c.battery:4} {c.label:14} "
                  f"{c.line[:40]:40} ref={c.ref:>18}  zb={c.zb:>18}")
        gated = len(both) - sum(1 for c in both if c.never_gated)
        print(f"--- {gated - bad}/{gated} agree" + ("" if not bad else "   <-- red"))

    for name, title in (("cal", "HEX$/OCT$ — the family's argument domain"),
                        ("bin", "BIN$ VALUES — the ROM dictates"),
                        ("binerr", "ERRORS / SCOPE"),
                        ("layout", "VARIABLE / ARRAY LAYOUT via VARPTR (D-BF-B)"),
                        ("fre", "FRE — relations, not addresses"),
                        ("depth", "FRE — argument, or evaluation DEPTH?")):
        if name not in bat:
            continue
        print(f"\n=== {title} ===")
        for c in bat[name]:
            twin = f"   zb={c.zb}" if c.zb is not None else ""
            print(f"  {c.label:14} {c.line[:46]:46} -> {c.ref}{twin}")

    abs_rows = [c for c in cases if c.never_gated]
    if abs_rows:
        print("\n=== RECORDED, NEVER GATED ===")
        print("  abs-*: two machines, two memory maps -- asserting an absolute "
              "FRE would assert the maps are identical.")
        print("  dep-*: the VG-8020 evaluator's own 6-byte-per-level stack "
              "frame -- a ROM internal, not a language contract.")
        for c in abs_rows:
            twin = f"  zb={c.zb}" if c.zb is not None else ""
            print(f"  {c.label:14} {c.line[:34]:34} ref={c.ref}{twin}")

    print("\n" + ("OK" if ok else "ATTENTION: see FAIL rows above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
