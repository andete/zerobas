#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-PENDERR — first-error-wins is a property of the WRITE, not a rule the
readers re-implement.

D-TMFP established the rule for ONE pair of faults (a type fault vs a numeric
one) by refusing to arm the separate `TMISMATCH` flag when `FPERR` was already
set. That fix lived in `type_mismatch_set`, the type fault's single writer.

🎯 THIS SLICE OBSERVES THAT `TMISMATCH` WAS NEVER A SECOND CONCEPT. It was a
boolean shorthand for one `FPERR` value -- `sfr_argok` (basic/str-engine.asm)
already promoted it by hand with `ld a,10 / ld (FPERR),a`, and fperr_to_err's
entry 10 is the same ERR 13 `type_mismatch_error` raises. So the two cells
collapse into one PENDING-ERROR CODE cell, fourteen readers collapse to one
test, and the D-TMFP guard becomes an ordinary set-if-empty write.

⚠️ AND THAT IS THE PART THAT COSTS SOMETHING, WHICH IS WHY THIS PROBE EXISTS.
While the type fault lived in a cell of its own it was STRUCTURALLY IMMUNE to
the twenty other bare `ld (FPERR),a` clobbers in the tree -- every reader tested
its cell first. In one cell it is not immune, and `WIDTH (A$<5)+0*(1/0)` would
lose its ERR 13 to fp_div's `ld a,2`. The merge is only sound if EVERY writer is
set-if-empty, so all twenty-one main-ROM writers plus the three in the sub-ROM
now go through `penderr_set` (basic/str-engine.asm) -- 3 bytes for the 3 the
bare store cost.

WHAT IS NEW HERE, AND IS NOT IN `make tmfp-acceptance`:

  o.nn.*   NUMERIC-vs-NUMERIC first-error-wins. D-TMFP measured the rule across
           a type/numeric pair only. The same two numeric faults concatenated
           both ways must report the FIRST one, and the three codes (11 from
           `1/0`, 5 from `SQR(-1)`, 6 from an overflow) make that a statement
           about ORDER rather than about any rank between fault kinds.
  o.sub.*  The two SUB-ROM tenants (`EXP`, `^`) raise into the same cell from
           page-1 tenant code. They reach `penderr_set` through the resident
           ABI (tools/gen_resident_abi.py), so these rows are the only thing
           that can tell a working merge from one that holds everywhere EXCEPT
           `x^y` and `EXP(x)`.
  r.*      D-TMFP's DEFERRED `r.hex` row and its family. `str_arg_empty`'s
           unconditional `ld a,4 / ld (FPERR),a` was D-TMFP §8's "defect 2",
           priced at +6 B for a standalone guard; routing it through
           `penderr_set` fixes it for nothing. ⚠️ "Defect 1" -- the cursor not
           landing on the closing `)` after a string-compare mismatch -- is
           UNTOUCHED, so these rows measure how far the write-side fix gets on
           its own.
  w.*      The three readers that branched on the fault KIND and are now
           WIDENED to any pending code: fch_check (files.asm, all 12 file
           verbs), eval_chan (float-arith.asm), ev_ff_ckpdl (expr.asm).

TWO READINGS, ONE GRAMMAR (D-ROWSHAPE): `o.*`/`n.*`/`r.*`/`w.*` rows are TRAPPED
and read `[ ERR ]` from inside the handler; `u.*` rows are UNTRAPPED and read
the clipped `screen_tail` of `RUN` -- the message TEXT, its line, whether it
printed ONCE, and whether the next line ran.

⚠️ Every row is a STORED program driven by `RUN`. In direct mode an abort on one
line does not stop the next.

Clean-room: observed screen output only; both reference ROMs are black boxes.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_repl                                                 # noqa: E402
import probe_report                                              # noqa: E402

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE",
                            "C-BIOS_MSX1_EU_REPACK_DISK")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
TEST_DSK = os.path.join(REPO, "disk", "test720.dsk")

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW", "CLS"), diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW", "CLS"), diska=True),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW", "CLS"), diska=True),
}

TRAP_PROG = [
    "10 ON ERROR GOTO 100",
    "20 {stmt}",
    "30 E=0",
    '40 PRINT"[";E;"]":END',
    "100 E=ERR:RESUME 40",
]
UNTRAP_PROG = [
    "10 {stmt}",
    '20 PRINT"[RANON]"',
]

# 🎯 THE FAULT SEEDS. Each contributes 0 to the expression it sits in and sets
# the pending-error cell to a DISTINCT code, so any two can be concatenated in
# either order to put two faults up with a known winner.
#   FP   division by zero          -> 11
#   FP5  SQR of a negative         ->  5   (illegal function call)
#   FPOV a float overflow          ->  6
#   FPEX an overflow raised INSIDE the sub-ROM EXP tenant        ->  6
#   FPPW an overflow raised INSIDE the sub-ROM pow tenant        ->  6
#   TM   a string compared to a number: the TYPE fault           -> 13
FP = "0*(1/0)"
FP5 = "0*SQR(-1)"
FPOV = "0*(1E38*1E38)"
FPEX = "0*EXP(1000)"
FPPW = "0*(2^10000)"
TM = "(Q$<5)"

CLS = "CLS:"

# (label, kind, statement)   kind: "t" trapped / "u" untrapped
CASES = [
    # === o.nn.* NUMERIC vs NUMERIC — the generalisation D-TMFP did not make ==
    # Same two faults, both orders. A tree that ranks fault KINDS answers each
    # pair identically; a tree that reports the FIRST one does not. Three codes
    # so the answer cannot be read as "division by zero is special".
    ("o.nn.dz5",   "t", CLS + f"WIDTH {FP}+{FP5}"),
    ("o.nn.5dz",   "t", CLS + f"WIDTH {FP5}+{FP}"),
    ("o.nn.dzov",  "t", CLS + f"WIDTH {FP}+{FPOV}"),
    ("o.nn.ovdz",  "t", CLS + f"WIDTH {FPOV}+{FP}"),
    ("o.nn.5ov",   "t", CLS + f"WIDTH {FP5}+{FPOV}"),
    ("o.nn.ov5",   "t", CLS + f"WIDTH {FPOV}+{FP5}"),
    # ...at a driver with stack cleanup (ex_let / check_expr_errors_popbc)
    ("o.nn.let",   "t", CLS + f"V={FP}+{FP5}"),
    ("o.nn.tel",   "t", CLS + f"V={FP5}+{FP}"),
    # ...and at the array lvalue (a THIRD frame shape: [OFFSET] + [TYPE])
    ("o.nn.ary",   "t", CLS + f"W(0)={FP}+{FP5}"),
    ("o.nn.yra",   "t", CLS + f"W(0)={FP5}+{FP}"),
    # ...and at PRINT
    ("o.nn.pr",    "t", CLS + f"PRINT {FP}+{FP5}"),
    ("o.nn.rp",    "t", CLS + f"PRINT {FP5}+{FP}"),

    # === o.sub.* THE SUB-ROM TENANTS raise into the SAME cell ================
    # 🔴 These are the only rows that can see the resident-ABI half of the fix.
    # EXP's and pow's overflow stores live in sub/fp_exp.asm and sub/fp_pow.asm,
    # page-1 tenant code that reaches penderr_set by absolute address through
    # tools/gen_resident_abi.py. A merge that converted only the main-ROM
    # writers would answer every OTHER row in this probe correctly.
    ("o.sub.dzex", "t", CLS + f"WIDTH {FP}+{FPEX}"),
    ("o.sub.exdz", "t", CLS + f"WIDTH {FPEX}+{FP}"),
    ("o.sub.dzpw", "t", CLS + f"WIDTH {FP}+{FPPW}"),
    ("o.sub.pwdz", "t", CLS + f"WIDTH {FPPW}+{FP}"),
    ("o.sub.5ex",  "t", CLS + f"WIDTH {FP5}+{FPEX}"),

    # === o.tm.* THE TYPE/NUMERIC PAIR, which the merge must not regress ======
    # These restate `make tmfp-acceptance`'s core rows in THIS probe, because
    # they are the rows the merge is most likely to break: the type code now
    # sits in the same cell every numeric writer stores into.
    # 🔴 `o.tm.tmfp` is D-EVALCHK §5.1's `dfe-tmfp` -- the row that refuted
    # D-TMFP's briefed design, and the single best detector for a missed writer.
    ("o.tm.tmfp",  "t", CLS + f"WIDTH {TM}+{FP}"),
    ("o.tm.fptm",  "t", CLS + f"WIDTH {FP}+{TM}"),
    ("o.tm.tm5",   "t", CLS + f"WIDTH {TM}+{FP5}"),
    ("o.tm.5tm",   "t", CLS + f"WIDTH {FP5}+{TM}"),
    ("o.tm.tmov",  "t", CLS + f"WIDTH {TM}+{FPOV}"),
    ("o.tm.ovtm",  "t", CLS + f"WIDTH {FPOV}+{TM}"),
    ("o.tm.tmex",  "t", CLS + f"WIDTH {TM}+{FPEX}"),
    ("o.tm.let",   "t", CLS + f"V={TM}+{FP}"),
    ("o.tm.ary",   "t", CLS + f"W(0)={TM}+{FP}"),

    # === o.pt.* A PARSE-TIME deferred code vs an EARLIER runtime fault =======
    # ev_f_defer (expr.asm) was one of only two writers that already honoured
    # first-error-wins; str_arg_empty (str-engine.asm) was not. Both are
    # penderr_set calls now, so these two families must answer the same way.
    ("o.pt.sin",   "t", CLS + "V=SIN(1/0,2)"),
    ("o.pt.sqr",   "t", CLS + "V=0*(1/0)+SQR()"),
    ("o.pt.left",  "t", CLS + 'Q2$=LEFT$(0*(1/0)+1)'),

    # === r.* THE r.hex FAMILY — D-TMFP's deferred row and its relatives ======
    # str_arg_empty's clobber (D-TMFP §8 defect 2) is fixed by construction.
    # Defect 1 (the cursor) is NOT, so these rows measure how far that gets.
    ("r.hex",      "t", CLS + f"Q2$=HEX$({FP}+{TM})"),
    ("r.oct",      "t", CLS + f"Q2$=OCT$({FP}+{TM})"),
    ("r.str",      "t", CLS + f"Q2$=STR$({FP}+{TM})"),
    ("r.hexp",     "t", CLS + f"PRINT HEX$({FP}+{TM})"),
    ("r.hex.tm",   "t", CLS + f"Q2$=HEX$({TM}+{FP})"),
    ("r.hex.nn",   "t", CLS + f"Q2$=HEX$({FP}+{FP5})"),

    # === w.* THE THREE WIDENED READERS ======================================
    # Each used to branch on the fault KIND (TMISMATCH) and now branches on ANY
    # pending code. The widening is free in bytes; these rows are what says
    # whether it is free in behaviour.
    ("w.lof.dz",   "t", CLS + f"V=LOF({FP}+1)"),      # files.asm fch_check
    ("w.lof.5",    "t", CLS + f"V=LOF({FP5}+1)"),
    ("w.eof.dz",   "t", CLS + f"V=EOF({FP}+1)"),
    ("w.chan.dz",  "t", CLS + f'PRINT #{FP}+1,"X"'),  # float-arith eval_chan
    ("w.pdl.dz",   "t", CLS + f"V=PDL({FP}+1)"),      # expr.asm ev_ff_ckpdl
    ("w.pdl.5",    "t", CLS + f"V=PDL({FP5}+1)"),

    # === n.* NEGATIVE CONTROLS: ONE fault, at every reader ==================
    # Rows that must not move. Each already agrees for a reason INDEPENDENT of
    # first-error-wins: there is only one fault, so there is no order to get
    # right and no clobber to refuse.
    ("n.dz.w",     "t", CLS + f"WIDTH {FP}+1"),
    ("n.5.w",      "t", CLS + f"WIDTH {FP5}+1"),
    ("n.ov.w",     "t", CLS + f"WIDTH {FPOV}+1"),
    ("n.ex.w",     "t", CLS + f"WIDTH {FPEX}+1"),
    ("n.pw.w",     "t", CLS + f"WIDTH {FPPW}+1"),
    ("n.tm.w",     "t", CLS + f"WIDTH {TM}"),
    ("n.tm.loc",   "t", CLS + 'LOCATE "5",3'),
    ("n.tm.pdl",   "t", CLS + "V=PDL(Q$)"),
    ("n.tm.rnd",   "t", CLS + "V=RND(Q$)"),
    ("n.tm.hex",   "t", CLS + 'PRINT HEX$("A")'),
    ("n.tm.lof",   "t", CLS + "V=LOF(Q$)"),
    ("n.tm.chan",  "t", CLS + 'PRINT #Q$,"X"'),
    ("n.ok.w",     "t", CLS + "WIDTH 30"),
    ("n.ok.pdl",   "t", CLS + "V=PDL(1)"),

    # === u.* THE UNTRAPPED FACE: the TEXT, the line, printed ONCE ===========
    ("u.dz.w",     "u", f"WIDTH {FP}+1"),
    ("u.nn.dz5",   "u", f"WIDTH {FP}+{FP5}"),
    ("u.nn.5dz",   "u", f"WIDTH {FP5}+{FP}"),
    ("u.sub.dzex", "u", f"WIDTH {FP}+{FPEX}"),
    ("u.tm.tmfp",  "u", f"WIDTH {TM}+{FP}"),
    ("u.tm.loc",   "u", 'LOCATE "5",3'),
]

# 🟢 POSITIVE CONTROLS, two per reading. 🔴 EVERY ONE IS A SINGLE-FAULT OR
# NO-FAULT ROW, i.e. one that agrees for a reason INDEPENDENT of this slice's
# claim -- D-TMFP's first control set named a both-flags SUBJECT row and would
# have exited 2 on a sound run (spec-basic-tmfp.md §9, docs/tmfp-msx1-
# characterization.md §3).
CONTROLS = ("n.tm.loc", "n.dz.w", "u.tm.loc", "u.dz.w")

CONTROL_WANT = {
    "n.tm.loc": " 13 ",
    "n.dz.w":   " 11 ",
    "u.tm.loc": "Type mismatch in 10",
    "u.dz.w":   "Division by zero in 10",
}

NEGATIVE = {
    "n.dz.w":    "NEGATIVE CONTROL — one numeric fault, no order to get right",
    "n.5.w":     "NEGATIVE CONTROL — the SQR code alone",
    "n.ov.w":    "NEGATIVE CONTROL — the overflow code alone",
    "n.ex.w":    "NEGATIVE CONTROL — the sub-ROM EXP tenant's code alone",
    "n.pw.w":    "NEGATIVE CONTROL — the sub-ROM pow tenant's code alone",
    "n.tm.w":    "NEGATIVE CONTROL — a type fault alone is still 13",
    "n.tm.pdl":  "NEGATIVE CONTROL — ev_ff_ckpdl, widened but single-fault",
    "n.tm.rnd":  "NEGATIVE CONTROL — ev_mc_arg_checked's collapsed test",
    "n.tm.hex":  "NEGATIVE CONTROL — sfr_argok's deleted promotion, same answer",
    "n.tm.lof":  "NEGATIVE CONTROL — fch_check, widened but single-fault",
    "n.tm.chan": "NEGATIVE CONTROL — eval_chan, widened but single-fault",
    "n.ok.w":    "NEGATIVE CONTROL — NO fault at all: penderr_set must not "
                 "invent one",
    "n.ok.pdl":  "NEGATIVE CONTROL — a clean PDL still runs its domain check",
}
LABEL_W = 11

DEFERRED: dict[str, str] = {}

SENTINELS = ("<NO CAPTURE>", "<NO ECHO>")


def clip_at_prompt(tail: str) -> str:
    """Drop everything from the first row that BEGINS with a prompt token.

    zerobas emits `ZB` with no trailing newline, so the prompt shares a row with
    the next echoed line and `omsx_repl.screen_tail`'s own prompt terminator
    never fires on zb (D-ONERR0, docs/onerr0-msx1-characterization.md §3.1)."""
    out = []
    for row in tail.split("|"):
        if any(row.startswith(p) for p in omsx_repl.PROMPTS):
            break
        out.append(row)
    return "|".join(out)


def program(kind: str, stmt: str) -> list[str]:
    tpl = TRAP_PROG if kind == "t" else UNTRAP_PROG
    return [ln.format(stmt=stmt) for ln in tpl]


def read_case(kind: str, raw: str | None) -> str:
    if raw is None:
        return "<NO CAPTURE>"
    if kind == "t":
        v = omsx_repl.result_span(raw)
        return "<NO CAPTURE>" if v is None else v
    t = omsx_repl.screen_tail(raw, "RUN")
    return "<NO ECHO>" if t is None else clip_at_prompt(t)


def run_side(side: str, only: list[str]) -> dict:
    cfg = SIDES[side]
    out = {}
    for label, kind, stmt in CASES:
        if only and label not in only:
            continue
        kw = {}
        if cfg["diska"]:
            dsk = os.path.join(tempfile.gettempdir(),
                               f"zb_pend_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        lines = list(cfg["reset"]) + program(kind, stmt) + ["RUN"]
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", lines)],
            batch=False, boot=cfg["boot"], step=cfg["step"], **kw)
        out[label] = read_case(kind, caps[0])
    return out


DENOMINATOR = (
    "(WHICH WRITER of the pending-error cell reaches it first: the tree has "
    "TWENTY-FOUR stores into FPERR -- twenty-one in the main ROM (float-arith "
    "fp_div / check_preexp_bounds / fac_to_int_go / cpow's div0 and "
    "illegal-fn arms / sdivmod_zerocheck, str-engine's five heap-OOM and "
    "too-complex arms plus str_arg_empty and str_heap_oom_error, expr's "
    "ev_f_defer and evmc_sqr/log/exp error tails, arrays' ary_engine_call "
    "map, and type_mismatch_set) and THREE in sub-ROM page-1 tenants "
    "(fp_pow x2, fp_exp), plus exec_stmt's per-statement CLEAR -- which "
    "D-STMTPEND has since turned into the statement-boundary READER, so the "
    "cell is now cleared by record_errline on the way out of a raise rather "
    "than at the top of every statement (docs/spec-basic-stmtpend.md §3); the "
    "one-lifetime-per-statement invariant this denominator rests on is "
    "unchanged, and is now proved by that test instead of imposed by a store. "
    "Reachable-in-one-statement pairs "
    "are what this probe samples: div0, SQR-domain, overflow, the two "
    "tenant-raised overflows, a parse-time deferred syntax error, and the "
    "type fault) x (the ORDER the two faults occur in -- the SAME pair "
    "concatenated both ways, which is the whole axis) x (WHICH READER "
    "surfaces it: eval_int16_checked via WIDTH, ex_let via "
    "check_expr_errors_popbc, ex_let_arr, exp_num, eval_chan, fch_check, "
    "ev_ff_ckpdl, ev_mc_arg_checked -- the fourteen that used to test two "
    "cells and now test one) x (TRAPPED vs UNTRAPPED, the second reading the "
    "message TEXT, its line, and whether it printed ONCE). The type/numeric "
    "pair itself is NOT re-derived here beyond the o.tm.* regression rows: "
    "that is `make tmfp-acceptance` (50 rows), which together with "
    "`make width-acceptance` (94, holding dfe-tmfp) and "
    "`make locarg-acceptance` (45) is this slice's green control set."
)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-PENDERR: first-error-wins as a property of the write")
    ap.add_argument("--sides", default="vg8020,cf3300,zb")
    ap.add_argument("--only", default="")
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless every row agrees across sides")
    a = ap.parse_args()

    sides = [s for s in a.sides.split(",") if s]
    only = [o for o in a.only.split(",") if o]
    for s in sides:
        if s not in SIDES:
            sys.stderr.write(f"unknown side {s!r}\n")
            return 2

    results = {s: run_side(s, only) for s in sides}
    present = [lab for lab, _, _ in CASES
               if any(lab in results[s] for s in sides)]

    print("D-PENDERR — first-error-wins is a property of the WRITE          "
          f"sides: {', '.join(sides)}")
    print("=" * 78)

    bad = []
    for ctl in CONTROLS:
        if ctl not in present:
            continue
        for s in sides:
            got = results[s].get(ctl)
            if got != CONTROL_WANT[ctl]:
                bad.append((ctl, s, got))
    if bad:
        for lab, s, got in bad:
            print(probe_report.row("FAIL", lab, LABEL_W, {s: got},
                                   "   [POSITIVE CONTROL]"))
            print(f"        wanted {CONTROL_WANT[lab]!r}")
        print("\n*** A POSITIVE CONTROL FAILED, so nothing below it was "
              "measured.\n"
              "    n.tm.loc = the TRAPPED reading itself, on an ordinary type "
              "fault (13).\n"
              "    n.dz.w   = an ordinary numeric fault reports its OWN code "
              "(11).\n"
              "    u.tm.loc = the UNTRAPPED reading -- ONE message, naming its "
              "line.\n"
              "    u.dz.w   = an untrapped numeric fault, the OTHER message.\n"
              "    🔴 Every control is a SINGLE-fault row, so a control failure "
              "cannot be\n"
              "    this slice's claim being wrong -- it is the apparatus.\n"
              "    🔴 CLASSIFY BY WHICH SIDE FAILED: red on a REFERENCE is a "
              "broken fixture\n"
              "    (report it, score nothing); red on zb is an ordinary "
              "divergence that\n"
              "    belongs in the row set, not in the control set.\n"
              "    Check build/*.rom, `make repack-machine` and `make "
              "latch-check`, THEN\n"
              "    re-read the rows. Exit 2 (not 1) = the instrument was "
              "broken.")
        for lab in present:
            vals = {s: results[s][lab] for s in sides if lab in results[s]}
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   "   (not scored)"))
        print(probe_report.footer(len(bad) + len(present), 0,
                                  "NOT MEASURED (a positive control failed)"))
        return 2

    if len(sides) < 2:
        n = 0
        for lab in present:
            for s in sides:
                if lab in results[s]:
                    print(probe_report.row("--", lab, LABEL_W,
                                           {s: results[s][lab]}))
                    n += 1
        print(probe_report.footer(n, 0, "CHARACTERIZATION (one side)"))
        print("=" * 78)
        print(f"{n} row(s) on {sides[0]} — no agreement verdict from one side")
        return 0

    agree = dis = refsplit = deferred = 0
    for lab in present:
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        ok = len(set(vals.values())) == 1 and len(vals) > 1
        if any(v in SENTINELS for v in vals.values()):
            ok = False
        refs = {vals[s] for s in ("vg8020", "cf3300") if s in vals}
        if lab in DEFERRED:
            deferred += 1
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   f"   [{DEFERRED[lab]}]"))
            continue
        agree += ok
        dis += not ok
        note = "   [POSITIVE CONTROL]" if lab in CONTROLS else ""
        if lab in NEGATIVE:
            note = f"   [{NEGATIVE[lab]}]"
        if len(refs) > 1:
            refsplit += 1
            note += "   [REFERENCES DISAGREE — no oracle for this row]"
        print(probe_report.row("ok" if ok else "DIFF", lab, LABEL_W, vals, note))

    print(probe_report.footer(len(present), len(present) - deferred,
                              f"{agree} agree, {dis} diverge, "
                              f"{deferred} deferred (not scored)"))
    print("=" * 78)
    print(f"{agree}/{agree + dis} readings agree "
          f"({len(CASES)} cases, {len(CONTROLS)} positive controls, "
          f"{len(NEGATIVE)} negative controls, "
          f"{refsplit} row(s) with no oracle, "
          f"{len(DEFERRED)} DEFERRED row(s) measured but not scored)")
    print("SIDES: vg8020,cf3300,zb — ON ERROR, ERR, WIDTH, LOCATE, PRINT, PDL, "
          "RND, SQR, EXP, `^` and HEX$/OCT$/STR$ are core MSX-BASIC, present on "
          "every MSX1, so BOTH references are legitimate oracles for those "
          "rows; the LOF/EOF rows depend on a file system and are expected to "
          "be measured, not necessarily oracled, on a cassette-only reference")
    print("DENOMINATOR: " + DENOMINATOR)
    if a.gate and dis:
        sys.stderr.write(f"penderr: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
