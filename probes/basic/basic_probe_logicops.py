#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Logical-operator characterization — semantics, PRECEDENCE and associativity
of AND / OR / XOR / EQV / IMP (and unary NOT) on the VG-8020 reference.

WHY THIS EXISTS
===============
docs/decision-kwgaps-slicing.md §4.1 makes `EQV`/`IMP` the next slice, and it
attaches a condition to it:

    "MSX precedence is NOT > AND > OR > XOR > EQV > IMP, with IMP lowest.
     THAT ORDERING MUST BE CHARACTERISED AGAINST THE VG-8020 BEFORE IT IS
     ENCODED, not asserted from the manual -- the spec owes a differential row
     per adjacent pair."

That is this probe. It is spec INPUT: nothing here is implemented yet.

THE METHOD -- MODEL AS GENERATOR, ROM AS ORACLE
===============================================
The trap this probe is built to avoid is the one kwsweep already caught once:
a case that AGREES can agree for the WRONG REASON (`PRINT TAB(99999)` matched on
both sides and `TAB(` does not exist). The mirror trap here would be to *assume*
`EQV a b = NOT (a XOR b)` and `IMP a b = (NOT a) OR b`, derive a distinguishing
operand triple from that assumption, and then read the precedence off it. If the
assumed semantics are wrong, the derived triple is meaningless and the verdict is
confident nonsense.

So the hypothesis is used ONLY as a generator, exactly the way kwsweep uses its
candidate word list:

  * to SEARCH for an operand triple at which the two groupings should differ, and
  * for a side-by-side AGREES/DIVERGES column in battery 1.

Every verdict comes from measurement. For each operator pair the probe runs
THREE lines on the ROM -- the bare form and BOTH explicit parenthesisations --
and decides precedence by asking which control the bare form MATCHED:

    PRINT [x A y B z]      <- U, the question
    PRINT [(x A y) B z]    <- L, "A binds tighter"      } both MEASURED,
    PRINT [x A (y B z)]    <- R, "B binds tighter"      } never computed

  L == R          -> UNOBSERVABLE at this triple (the operators commute through
                     each other here; the pair's order is unconstrained by it)
  U == L != R     -> A binds tighter
  U == R != L     -> B binds tighter
  anything else   -> ANOMALY (reported, never silently resolved)

`L == R` is a REAL and expected outcome, not a probe failure: XOR and EQV are
mutually associative, so no triple built from those two alone can order them.
An unobservable pair is a genuine spec answer -- it says the implementation is
free to choose -- and it is reported as such rather than papered over.

CALIBRATION -- REPRODUCE A KNOWN RESULT FIRST
=============================================
AND / OR / XOR / NOT are already implemented in zerobas (basic/expr.asm
`ev_xor`/`ev_or`/`ev_and`/`ev_not`). Every case that uses only those four is run
on BOTH machines and required to AGREE. That battery is the harness's own gate:
if the calibration rows diverge, the measurement apparatus is what is broken,
and no EQV/IMP reading from the same run is trustworthy. (The standing lesson:
the whole apparatus is part of the measurement.)

Clean-room: this only types lines and reads the screen. The reference ROM is
never read as code. See CONTRIBUTING.md.

USAGE
    python3 probes/basic/basic_probe_logicops.py
    ... --only prec           # one battery: sem | prec | assoc | domain | mixed
    ... --ref-only            # skip the zerobas calibration side
    ... --boot-per-case       # isolation escape hatch
"""
from __future__ import annotations

import argparse
import itertools
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402  typing-free KEYBUF-injection REPL driver

REF_MACHINE = "Philips_VG_8020"    # reference: built-in MSX-BASIC, no cartridge
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

# --- the model: GENERATOR ONLY (see module docstring) ------------------------
MASK = 0xFFFF


def s16(v: int) -> int:
    """Wrap to the signed 16-bit domain MSX-BASIC logical operators live in."""
    v &= MASK
    return v - 0x10000 if v & 0x8000 else v


MODEL = {
    "AND": lambda a, b: a & b,
    "OR":  lambda a, b: a | b,
    "XOR": lambda a, b: a ^ b,
    "EQV": lambda a, b: ~(a ^ b),
    "IMP": lambda a, b: (~a) | b,
}
# Implemented in zerobas today -> a case built only from these is CALIBRATION
# (run on BOTH machines, required to agree). `--gate` adds EQV/IMP, which turns
# EVERY row into a two-sided differential -- that is the acceptance gate for the
# slice, and until it has been run the implementation has only been BUILT.
IMPLEMENTED = {"AND", "OR", "XOR", "NOT"}
BINOPS = ["AND", "OR", "XOR", "EQV", "IMP"]
ALL_OPS = set(BINOPS) | {"NOT"}

# Operand pool the triple search draws from: all-zeros / all-ones (the 1-bit
# truth table), single bits, and two multi-bit patterns that overlap partially.
POOL = [0, -1, 1, 2, 3, 5, 10, 12, -2]


def model(op: str, a: int, b: int) -> int:
    return s16(MODEL[op](a, b))


# --- case construction -------------------------------------------------------

class Case:
    """One typed direct-mode line and how to judge it."""

    def __init__(self, battery, label, expr, want=None, kind="value"):
        self.battery = battery
        self.label = label
        self.expr = expr
        self.want = want            # model prediction (may be None: no model)
        self.kind = kind            # "value" | "error"
        self.line = f'PRINT "[";{expr};"]"'
        # calibration iff every operator token is already implemented AND the row
        # is not a recorded divergence (a known-red row must never be able to
        # make the apparatus gate read "suspect"). Intersect with ALL_OPS first:
        # a bare [A-Z]+ scan also matches the 'E' of `1E10` and the 'HF' of
        # `&HF0F0`, which would silently drop the whole domain battery from the
        # gate -- a gate that quietly stops measuring its subject.
        words = set(re.findall(r"[A-Z]+", expr)) & ALL_OPS
        self.calib = words <= IMPLEMENTED and expr not in CALIB_EXEMPT
        self.ref = None
        self.zb = None


def build_semantics() -> list[Case]:
    """Battery 1 -- the operators' own truth tables, measured directly."""
    pairs = [(0, 0), (0, -1), (-1, 0), (-1, -1), (12, 10), (1, 0)]
    out = []
    for op in BINOPS:
        for a, b in pairs:
            out.append(Case("sem", f"{a} {op} {b}", f"{a} {op} {b}",
                            want=model(op, a, b)))
    for a in (0, -1, 1, 12):
        out.append(Case("sem", f"NOT {a}", f"NOT {a}", want=s16(~a)))
    return out


def find_triple(a_op: str, b_op: str):
    """Search POOL for (x,y,z) where the model says the two groupings of
    `x A y B z` DIFFER. Returns None when the model says the pair is
    unobservable -- which the probe then goes and CONFIRMS on the ROM."""
    for x, y, z in itertools.product(POOL, repeat=3):
        left = model(b_op, model(a_op, x, y), z)     # (x A y) B z
        right = model(a_op, x, model(b_op, y, z))    # x A (y B z)
        if left != right:
            return x, y, z
    return None


def build_precedence() -> tuple[list[Case], list[tuple]]:
    """Battery 2 -- every ORDERED pair of distinct binary operators, three
    measured lines each. Returns (cases, plan) where plan carries the indices
    the verdict is read from."""
    cases, plan = [], []
    for a_op, b_op in itertools.permutations(BINOPS, 2):
        t = find_triple(a_op, b_op)
        model_says = t is not None
        if t is None:
            t = (1, 0, 1)        # arbitrary: we still CONFIRM L == R on the ROM
        x, y, z = t
        tag = f"{a_op}/{b_op}"
        base = len(cases)
        cases.append(Case("prec", f"{tag} bare",  f"{x} {a_op} {y} {b_op} {z}"))
        cases.append(Case("prec", f"{tag} L",     f"({x} {a_op} {y}) {b_op} {z}"))
        cases.append(Case("prec", f"{tag} R",     f"{x} {a_op} ({y} {b_op} {z})"))
        plan.append((tag, a_op, b_op, (x, y, z), model_says, base))
    return cases, plan


def build_assoc() -> tuple[list[Case], list[tuple]]:
    """Battery 3 -- associativity of each operator with itself. IMP is the one
    that can actually answer (implication is not associative); the rest are
    expected UNOBSERVABLE and that is a result, not a gap."""
    cases, plan = [], []
    for op in BINOPS:
        t = find_triple(op, op)
        model_says = t is not None
        if t is None:
            t = (1, 0, 1)
        x, y, z = t
        base = len(cases)
        cases.append(Case("assoc", f"{op} bare", f"{x} {op} {y} {op} {z}"))
        cases.append(Case("assoc", f"{op} L",    f"({x} {op} {y}) {op} {z}"))
        cases.append(Case("assoc", f"{op} R",    f"{x} {op} ({y} {op} {z})"))
        plan.append((op, op, op, (x, y, z), model_says, base))
    return cases, plan


# Battery 4 -- the int16 domain. No model column: these are exactly the rows the
# spec needs DICTATED to it. `EQV x 0` is the readout of choice because it is
# injective (`EQV x 0 == NOT x`), so the printed value names the converted
# operand exactly -- `IMP x -1` is constant -1 and would have measured nothing.
DOMAIN = [
    # rounding: EQV n 0 prints -(n+1), so -4 means the operand became 3, -3 means 2
    ("round-2.7",        "2.7 EQV 0"),
    ("round-2.5",        "2.5 EQV 0"),
    ("round-3.5",        "3.5 EQV 0"),
    ("round-1.5",        "1.5 EQV 0"),
    ("round-2.2",        "2.2 EQV 0"),
    ("round-neg-2.7",    "-2.7 EQV 0"),
    ("round-neg-2.5",    "-2.5 EQV 0"),
    ("round-neg-2.2",    "-2.2 EQV 0"),
    # the domain edges, and whether ROUNDING can push an in-range float out
    ("hi-bound",         "32767 IMP 0"),
    ("over-bound",       "32768 IMP 0"),
    ("hi-frac-lo",       "32767.4 EQV 0"),
    ("hi-frac-hi",       "32767.6 EQV 0"),
    ("lo-bound",         "-32768 EQV 0"),
    ("under-bound",      "-32769 EQV 0"),
    ("huge",             "1E10 EQV 1"),
    ("string-lhs",       '"A" EQV 1'),
    ("string-rhs",       '1 EQV "A"'),
    ("hex",              "&HF0F0 IMP &H0FF0"),
]

# Battery 5 -- the boundaries with the layers ABOVE (relational, arithmetic) and
# BELOW (unary NOT) the logical block. Each row is (label, bare, L, R) and is
# judged by the same three-measured-values rule as battery 2 -- NOT the eyeball.
#
# Choosing the operands here is the whole difficulty. `NOT 0 EQV 0` looks like a
# NOT-vs-EQV test and is NOT one: EQV and XOR absorb a complement
# (`EQV (NOT a) b == NOT (EQV a b)`), so BOTH groupings print 0 and the row
# would "pass" while measuring nothing. That is the kwsweep `TAB(` trap wearing
# a different hat. The rows below were picked so L != R wherever the pair is
# observable at all, and the ones that stay unobservable are REPORTED as such.
MIXED = [
    ("rel-vs-imp",   "1 = 1 IMP 1 = 0",   "(1 = 1) IMP (1 = 0)",   "1 = (1 IMP 1) = 0"),
    ("arith-vs-imp", "1 IMP 2 + 3",       "1 IMP (2 + 3)",         "(1 IMP 2) + 3"),
    ("arith-vs-eqv", "1 EQV 2 + 3",       "1 EQV (2 + 3)",         "(1 EQV 2) + 3"),
    ("not-vs-imp",   "NOT 1 IMP 2",       "(NOT 1) IMP 2",         "NOT (1 IMP 2)"),
    ("not-vs-eqv",   "NOT 1 EQV 2",       "(NOT 1) EQV 2",         "NOT (1 EQV 2)"),
    # calibration twins: identical shapes over implemented operators only
    ("cal-rel-vs-xor",   "1 = 1 XOR 1 = 0", "(1 = 1) XOR (1 = 0)", "1 = (1 XOR 1) = 0"),
    ("cal-arith-vs-or",  "1 OR 2 + 3",      "1 OR (2 + 3)",        "(1 OR 2) + 3"),
    ("cal-not-vs-and",   "NOT 1 AND 3",     "(NOT 1) AND 3",       "NOT (1 AND 3)"),
    ("cal-not-vs-or",    "NOT 1 OR 2",      "(NOT 1) OR 2",        "NOT (1 OR 2)"),
    ("cal-not-vs-xor",   "NOT 1 XOR 2",     "(NOT 1) XOR 2",       "NOT (1 XOR 2)"),
]

# One whole-chain line exercising all five levels at once -- the end-to-end
# check on the table battery 2 derives. The operands are NOT arbitrary: the
# first attempt (`1 AND 1 OR 0 XOR 1 EQV 1 IMP 0`) measured NOTHING, because
# its full-left and full-right parenthesisations both evaluate to 1. These were
# searched for so the two groupings actually disagree.
CHAIN = ("0 AND 0 OR 0 XOR 0 EQV 0 IMP 1",
         "((((0 AND 0) OR 0) XOR 0) EQV 0) IMP 1",
         "0 AND (0 OR (0 XOR (0 EQV (0 IMP 1))))")

# Battery 6 -- CHAINED RELATIONALS. Not part of the EQV/IMP question; found by
# this probe's own calibration battery going red on `1 = (1 XOR 1) = 0`, and
# confirmed boot-per-case. MSX-BASIC chains relationals LEFT-ASSOCIATIVELY
# (`1 = 0 = 0` is `(1 = 0) = 0` = -1); zerobas's ev_rel handles exactly ONE
# relational operator (plus the <=/>=/<> two-token merge) and leaves the rest of
# the chain on the cursor, where PRINT resumes and emits a SECOND value.
#
# These rows are reported as a DIVERGENCE battery, deliberately NOT as
# calibration: a known-red row must not make the apparatus gate read "suspect",
# or the gate stops meaning anything.
RELCHAIN = [
    ("eq-eq-false",  "1 = 0 = 0"),
    ("eq-eq-true",   "1 = 1 = 1"),
    ("eq-eq-neg",    "3 = 3 = -1"),
    ("lt-eq",        "1 < 2 = -1"),
    ("via-xor",      "1 = (1 XOR 1) = 0"),
    ("via-imp",      "1 = (1 IMP 1) = 0"),
    ("triple",       "1 = 1 = 1 = 1"),
    ("with-parens",  "(1 = 0) = 0"),      # the control: one relop per layer
    # --- second recorded divergence: a STRING as the LEFT operand of a logical
    # operator. The reference raises Type mismatch; zerobas PRINTS the string and
    # then a value (`"A" AND 1` -> `A 0`), because ev_rel's str_eval probe
    # consumes the string operand and PRINT resumes on what is left.
    #
    # This is PRE-EXISTING, not EQV/IMP fallout: `"A" AND 1` and `"A" XOR 1`
    # behave identically and both predate this probe. Proving it is not a
    # regression is all that proves -- it stays RED and recorded, not quietly
    # dropped, and the AND/XOR rows are here so the record cannot be misread as
    # an EQV/IMP problem. Note the RIGHT operand is handled correctly
    # (`1 EQV "A"` -> type mismatch on both sides), which localises the defect.
    ("str-lhs-and",  '"A" AND 1'),
    ("str-lhs-xor",  '"A" XOR 1'),
    ("str-lhs-eqv",  '"A" EQV 1'),
    ("str-lhs-imp",  '"A" IMP 1'),
    ("str-rhs-and",  '1 AND "A"'),        # the control: RHS is rejected correctly
    ("str-rhs-eqv",  '1 EQV "A"'),
]
# Expressions exempt from the calibration gate (see above): they are MEASURED,
# RECORDED divergences, not an apparatus fault. A known-red row must never be
# able to make the apparatus gate read "suspect", or the gate stops meaning
# anything -- but it must still be REPORTED, which battery 6 does.
CALIB_EXEMPT = {expr for _, expr in RELCHAIN}


# --- reading the screen ------------------------------------------------------

def read(raw: str | None, line: str) -> str:
    """The printed value, or the error text when the PRINT never completed."""
    if raw is None:
        return "<no capture>"
    span = omsx_repl.result_span(raw)
    if span is not None:
        return " ".join(span.split())
    tail = omsx_repl.screen_tail(raw, line)
    if tail:
        tail = " ".join(tail.split())
        if tail:
            return f"ERR:{tail}"
    return "<no result>"


def agree(ref: str, zb: str) -> bool:
    """Ref-vs-zerobas agreement. Values must match exactly; ERROR rows are
    compared case-insensitively because zerobas's lowercase error wording is a
    DOCUMENTED divergence -- a raw text compare would flag every error row and
    classify none of them (the kwsweep layer-2 lesson)."""
    if ref.startswith("ERR:") and zb.startswith("ERR:"):
        return ref.lower() == zb.lower()
    return ref == zb


def as_int(txt: str):
    t = txt.strip()
    return int(t) if re.fullmatch(r"-?\d+", t) else None


def verdict(u, l, r, name_l, name_r):
    """Decide a grouping question from THREE measured values. `l == r` is a
    real answer (the groupings coincide -> the question is unconstrained),
    never a pass."""
    if "<" in u or "<" in l or "<" in r:
        return "ANOMALY", "capture failed"
    if l == r:
        return "UNOBSERVABLE", f"L == R == {l}"
    if u == l:
        return name_l, f"bare={u} matches L"
    if u == r:
        return name_r, f"bare={u} matches R"
    return "ANOMALY", f"bare={u} matches NEITHER L={l} nor R={r}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE,
                    help="reference machine (built-in MSX-BASIC oracle)")
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE,
                    help="zerobas machine (calibration rows only)")
    ap.add_argument("--only", help="run one battery: sem|prec|assoc|domain|mixed")
    ap.add_argument("--ref-only", action="store_true",
                    help="skip the zerobas calibration side")
    ap.add_argument("--boot-per-case", dest="boot_per_case", action="store_true",
                    help="isolate each case in its own boot")
    ap.add_argument("--gate", action="store_true",
                    help="treat EQV/IMP as implemented -> every row becomes a "
                         "two-sided differential (the slice's acceptance gate)")
    args = ap.parse_args()

    if args.gate:
        IMPLEMENTED.update({"EQV", "IMP"})

    sem = build_semantics()
    prec, prec_plan = build_precedence()
    assoc, assoc_plan = build_assoc()
    dom = [Case("domain", lb, ex) for lb, ex in DOMAIN]

    mix, mix_plan = [], []
    for label, bare, lc, rc in MIXED:
        base = len(mix)
        mix.append(Case("mixed", f"{label} bare", bare))
        mix.append(Case("mixed", f"{label} L", lc))
        mix.append(Case("mixed", f"{label} R", rc))
        mix_plan.append((label, "L: claimed order", "R: REFUTES claim",
                         None, True, base))
    mix_plan.append(("chain-all", "L: claimed order", "R: REFUTES claim",
                     None, True, len(mix)))
    for tag, ex in zip(("bare", "L", "R"), CHAIN):
        mix.append(Case("mixed", f"chain-all {tag}", ex))

    rel = [Case("relchain", lb, ex) for lb, ex in RELCHAIN]
    batteries_extra = rel

    batteries = {"sem": sem, "prec": prec, "assoc": assoc,
                 "domain": dom, "mixed": mix, "relchain": rel}
    if args.only:
        if args.only not in batteries:
            print(f"unknown battery {args.only!r}; pick one of {list(batteries)}")
            return 2
        batteries = {args.only: batteries[args.only]}
        prec_plan = prec_plan if args.only == "prec" else []
        assoc_plan = assoc_plan if args.only == "assoc" else []
        mix_plan = mix_plan if args.only == "mixed" else []

    cases = [c for b in batteries.values() for c in b]
    batch = not args.boot_per_case

    calib = [c for c in cases if c.calib]
    # the relchain battery needs BOTH sides too -- it is a divergence to pin,
    # so its zerobas answer is the point, it just must not gate the apparatus
    both = ([] if args.ref_only
            else calib + [c for c in cases if c.battery == "relchain"])
    bothset = set(id(c) for c in both)
    refonly = [c for c in cases if id(c) not in bothset]

    # Two-sided cases go through run_differential, NOT two run_cases calls: it
    # SELF-HEALS, re-running any case that disagrees boot-per-case on both
    # machines before believing the disagreement. Without that, one flaky
    # capture (an echo scraped as the value) reads exactly like a real
    # divergence -- which is how `(-1 XOR 0) AND 0` first showed up here.
    if both:
        print(f"# {len(both)} two-sided -> {args.machine} + {args.zb_machine}")
        specs = [("direct", [c.line]) for c in both]
        _, rr, zz = omsx_repl.run_differential(
            args.machine, args.zb_machine, specs,
            lambda i, r, z: agree(read(r, both[i].line), read(z, both[i].line)),
            batch=batch, reset=("CLS",))
        for c, r, z in zip(both, rr, zz):
            c.ref, c.zb = read(r, c.line), read(z, c.line)

    if refonly:
        print(f"# {len(refonly)} reference-only -> {args.machine}")
        raws = omsx_repl.run_cases(args.machine,
                                   [("direct", [c.line]) for c in refonly],
                                   batch=batch, reset=("CLS",))
        for c, raw in zip(refonly, raws):
            c.ref = read(raw, c.line)

    ok = True

    # --- calibration first: if this is red, nothing below is trustworthy -----
    if not args.ref_only and calib:
        print("\n=== CALIBRATION (implemented operators, ref vs zerobas must AGREE) ===")
        bad = 0
        for c in calib:
            good = agree(c.ref, c.zb)
            bad += not good
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} {c.battery:6} {c.expr:34} "
                  f"ref={c.ref:>8}  zb={c.zb:>8}")
        print(f"--- calibration: {len(calib) - bad}/{len(calib)} agree"
              + ("" if not bad else "   <-- APPARATUS SUSPECT, do not trust the rest"))

    if "sem" in batteries:
        print("\n=== BATTERY 1 -- SEMANTICS (ROM truth table; model is a column, not a judge) ===")
        for c in sem:
            got = as_int(c.ref)
            mark = "=" if got == c.want else "DIVERGES"
            print(f"  {c.expr:22} -> {c.ref:>8}   model {c.want:>8}  {mark}")

    for title, plan, pool in (
            ("BATTERY 2 -- PRECEDENCE", prec_plan, prec),
            ("BATTERY 3 -- ASSOCIATIVITY", assoc_plan, assoc),
            ("BATTERY 5 -- LAYER BOUNDARIES", mix_plan, mix)):
        if not plan:
            continue
        print(f"\n=== {title} (verdict from three MEASURED values) ===")
        for tag, name_l, name_r, triple, model_says, base in plan:
            u, l, r = (pool[base].ref, pool[base + 1].ref, pool[base + 2].ref)
            v, why = verdict(u, l, r, name_l, name_r)
            note = "" if model_says else "  (model predicted UNOBSERVABLE)"
            if v == "ANOMALY":
                ok = False
            tri = str(triple) if triple else pool[base].expr
            print(f"  {tag:14} {tri:34} bare={u:>7} L={l:>7} R={r:>7}"
                  f"   {v:18} {why}{note}")

    if "domain" in batteries:
        print("\n=== BATTERY 4 -- INT16 DOMAIN (the ROM dictates; no model) ===")
        for c in dom:
            print(f"  {c.label:16} {c.expr:24} -> {c.ref}")

    if "relchain" in batteries:
        print("\n=== BATTERY 6 -- RECORDED DIVERGENCES (chained relationals; "
              "string LHS) ===")
        for c in rel:
            same = c.zb is None or agree(c.ref, c.zb)
            print(f"  {'same' if same else 'DIVERGES':8} {c.label:14} {c.expr:22}"
                  f" ref={c.ref:>10}   zb={c.zb if c.zb is not None else '-':>10}")

    print("\n" + ("OK" if ok else "ATTENTION: see FAIL/ANOMALY rows above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
