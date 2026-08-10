#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-STMTPEND — a fault that ALREADY HAPPENED outranks everything the statement
does afterwards, including finishing.

WHERE THIS CAME FROM. D-TMFP filed "defect 1": after a string-compare mismatch
the token cursor does not land on the closing `)`, so `str_fn_radix` bails
through `str_arg_empty`. D-PENDERR then fixed the OTHER defect and made the
symptom disappear -- `r.hex` and its family went green on three sides -- while
leaving defect 1 untouched. This probe is the denominator that was supposed to
show the cursor was unobservable. It shows the opposite.

🎯 THE CURSOR IS REAL AND IT IS MEASURED, but it is not the rule. Freezing
zerobas at `type_mismatch_set` and reading IX out of the token buffer puts the
cursor on the RHS OPERAND -- `Q$` and `<` consumed, `5` not -- and freezing at
`penderr_set` shows the first pending code written after `HEX$((Q$<5)+0*(1/0))`
is 4 (`str_arg_empty`), never 2 (`fp_div`). So the rest of the expression is not
merely fault-free after a deferred type fault: IT IS NEVER EVALUATED. That
answers the question `spec-basic-penderr.md` §3.2 explicitly declined to answer,
and the screen cannot answer it. See `docs/stmtpend-msx1-characterization.md` §3.

🔴 AND THE STRANDED CURSOR IS ONLY ONE ROUTE INTO A HOLE THAT NEEDS NO STRING AT
ALL. `SCREEN 0*(1/0)` and `DEFUSR=0*(1/0)` print NO ERROR on zerobas and
`Division by zero` on both references. `exec_stmt` clears the pending-error cell
unconditionally at the top of every statement, so a fault raised by a statement
whose driver never calls `check_expr_errors` is simply forgotten. A stranded
cursor gets you there by making the statement END early; a plain `1/0` gets you
there because nobody looked.

THE TWO MECHANISMS, WHICH THIS PROBE KEEPS APART BY NAME:

  s.*  THE STATEMENT-BOUNDARY DROP. The statement runs to completion (or to what
       its driver thinks is completion), `jp exec_stmt`, and the pending code is
       cleared before anyone reads it. Reported: nothing at all.
  e.*  THE EAGER SYNTAX ERROR. The statement's own delimiter check fails and
       jumps to `stmt_error`, which raises ERR 2 over the top of a live pending
       code. Reported: `Syntax error` where the reference reports the fault.
  c.*  THE CURSOR ROWS -- e.*/s.* reached specifically by a string compare
       stranding the cursor mid-expression. Same two mechanisms, string entry.
  g.*  THE MASKED CLASS: contexts whose driver DOES check, where the pending
       code already wins. These must not move; they are what D-PENDERR shipped.
  n.*  NEGATIVE CONTROLS, each agreeing for a reason INDEPENDENT of the claim:
       a genuine syntax error with NO fault pending (must stay ERR 2), a clean
       statement (must stay silent), a single fault at a reader that checks.
  u.*  THE UNTRAPPED FACE: message TEXT, its line, printed ONCE, and whether the
       following line ran.

TWO READINGS, ONE GRAMMAR (D-ROWSHAPE): `s.*`/`e.*`/`c.*`/`g.*`/`n.*` are
TRAPPED and read `[ ERR ]` from inside the handler; `u.*` rows are UNTRAPPED and
read the clipped `screen_tail` of `RUN`.

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

# 🔴 THE SEED LINE IS PART OF EVERY PROGRAM, TRAPPED OR NOT. `Q$` must hold a
# string for the comparison rows to be a TYPE fault rather than an empty-variable
# one, and the untrapped template needs it too -- which is why the fault is on
# line 30 there, not line 10, and every u.* expectation names line 30.
TRAP_PROG = [
    "10 ON ERROR GOTO 100",
    '20 Q$="A"',
    "30 {stmt}",
    "40 E=0",
    '50 PRINT"[";E;"]":END',
    "100 E=ERR:RESUME 50",
]
UNTRAP_PROG = [
    '10 Q$="A"',
    "20 {stmt}",
    '30 PRINT"[RANON]"',
]

# THE FAULT SEEDS. Each contributes 0 to the expression it sits in and leaves a
# DISTINCT pending code, so the row says WHICH fault survived, not merely that
# one did.
#   DZ  division by zero      -> 11        S5  SQR of a negative ->  5
#   OV  a float overflow      ->  6        TM  string < number   -> 13
#   MT  number < string       -> 13   (the OTHER mismatch site, evr_mismatch)
DZ = "0*(1/0)"
S5 = "0*SQR(-1)"
OV = "0*(1E38*1E38)"
TM = "(Q$<5)"
MT = "(5<Q$)"

CLS = "CLS:"

# (label, kind, statement)   kind: "t" trapped / "u" untrapped
CASES = [
    # === s.* THE STATEMENT-BOUNDARY DROP — no string anywhere ===============
    # The statement PARSES cleanly and runs to `jp exec_stmt`; the pending code
    # is cleared there before any reader sees it. zerobas reports NOTHING.
    # 🔴 These are the rows that say the defect is not about strings.
    ("s.for.dz",   "t", CLS + f"FOR I={DZ} TO 3:NEXT"),
    ("s.for.ov",   "t", CLS + f"FOR I={OV} TO 3:NEXT"),
    ("s.for.5",    "t", CLS + f"FOR I={S5} TO 3:NEXT"),
    ("s.forlim",   "t", CLS + f"FOR I=1 TO {DZ}:NEXT"),
    ("s.scr.dz",   "t", CLS + f"SCREEN {DZ}"),
    ("s.usr.dz",   "t", CLS + f"DEFUSR={DZ}"),
    ("s.usr.ov",   "t", CLS + f"DEFUSR={OV}"),

    # === e.* THE EAGER SYNTAX ERROR over a live pending code ================
    # `stmt_error` raises ERR 2 without consulting the cell. Same statement, one
    # delimiter removed, so the ONLY difference from the s.* rows above is which
    # of the two mechanisms is reached.
    ("e.for.dz",   "t", CLS + f"FOR I={DZ} STEP 2:NEXT"),
    ("e.for.ov",   "t", CLS + f"FOR I={OV} STEP 2:NEXT"),
    ("e.for.5",    "t", CLS + f"FOR I={S5} STEP 2:NEXT"),

    # === c.* THE CURSOR ROWS — the same two holes, entered by a string =====
    # A string-compare mismatch strands the cursor on the RHS operand, so the
    # statement's next delimiter check reads a token that is not there yet.
    # BOTH mismatch sites: ers_rhs_mismatch (`Q$<5`) and evr_mismatch (`5<Q$`).
    ("c.for.tm",   "t", CLS + f"FOR I={TM} TO 3:NEXT"),
    ("c.for.mt",   "t", CLS + f"FOR I={MT} TO 3:NEXT"),
    ("c.forlim",   "t", CLS + f"FOR I=1 TO {TM} STEP 1:NEXT"),
    ("c.scr.tm",   "t", CLS + f"SCREEN {TM}"),
    ("c.usr.tm",   "t", CLS + f"DEFUSR={TM}"),
    ("c.usr.mt",   "t", CLS + f"DEFUSR={MT}"),
    ("c.poke.tm",  "t", CLS + f"POKE {TM},0"),
    ("c.line.tm",  "t", CLS + f"LINE (0,0)-({TM},1)"),

    # === g.* THE MASKED CLASS — drivers that DO check, and must not move ====
    # This is what D-PENDERR shipped. Every one of these already agrees; they
    # are here because the fix touches the statement boundary they all cross.
    ("g.hex",      "t", CLS + f"Q2$=HEX$({DZ}+{TM})"),
    ("g.hex.tm",   "t", CLS + f"Q2$=HEX$({TM}+{DZ})"),
    ("g.oct",      "t", CLS + f"Q2$=OCT$({DZ}+{TM})"),
    ("g.wid",      "t", CLS + f"WIDTH {TM}+{DZ}"),
    ("g.wid.dz",   "t", CLS + f"WIDTH {DZ}+{TM}"),
    ("g.loc",      "t", CLS + f"LOCATE {TM},3"),
    ("g.prt",      "t", CLS + f"PRINT {TM};1"),
    ("g.if",       "t", CLS + f"IF {TM} THEN 50"),
    ("g.dim",      "t", CLS + f"DIM Z({TM})"),
    ("g.ary",      "t", CLS + f"W({TM})=1"),
    ("g.let",      "t", CLS + f"V={TM}+{DZ}"),
    ("g.mid",      "t", CLS + f'Z$=MID$("ABC",{TM},1)'),
    ("g.strng",    "t", CLS + f"Z$=STRING$({TM},65)"),
    ("g.open",     "t", CLS + f'OPEN"X" AS #{TM}'),
    ("g.next",     "t", CLS + f"FOR I=1 TO 1:NEXT W({TM})"),
    ("g.snd",      "t", CLS + f"SOUND {TM},1"),
    ("g.on",       "t", CLS + f"ON {TM} GOTO 50"),
    ("g.poke.dz",  "t", CLS + f"POKE {DZ},0"),
    ("g.snd.dz",   "t", CLS + f"SOUND {DZ},1"),

    # === n.* NEGATIVE CONTROLS ==============================================
    # 🔴 A GENUINE SYNTAX ERROR WITH NOTHING PENDING MUST STAY ERR 2. These are
    # the rows a fix that simply stopped raising ERR 2 would redden, and they
    # agree today for a reason that has nothing to do with pending codes.
    ("n.syn.for",  "t", CLS + "FOR I=1 STEP 2:NEXT"),
    ("n.syn.zork", "t", CLS + "ZORK 1,2"),
    ("n.syn.swap", "t", CLS + "SWAP 1,V"),
    # ...and a clean statement must stay silent.
    ("n.ok.for",   "t", CLS + "FOR I=1 TO 3:NEXT"),
    ("n.ok.usr",   "t", CLS + "DEFUSR=&HC000"),
    ("n.ok.poke",  "t", CLS + "POKE &HC000,0"),
    ("n.ok.scr",   "t", CLS + "SCREEN 0"),
    ("n.ok.chain", "t", CLS + "V=1:W=2:V=V+W"),
    # ...and a single fault at a reader that already checks keeps its own code.
    ("n.dz.w",     "t", CLS + f"WIDTH {DZ}+1"),
    ("n.5.w",      "t", CLS + f"WIDTH {S5}+1"),
    ("n.ov.w",     "t", CLS + f"WIDTH {OV}+1"),
    ("n.tm.w",     "t", CLS + f"WIDTH {TM}"),
    ("n.tm.loc",   "t", CLS + 'LOCATE "5",3'),
    # ...and the TRAP itself must still work after a newly-raised error: every
    # s.*/e.* row above runs its handler and RESUMEs, which is only readable
    # because this row proves the handler/RESUME path is sound on its own.
    ("n.trap.res", "t", CLS + "V=1/0"),

    # === u.* THE UNTRAPPED FACE ============================================
    ("u.for.dz",   "u", f"FOR I={DZ} TO 3:NEXT"),
    ("u.for.tm",   "u", f"FOR I={TM} TO 3:NEXT"),
    ("u.scr.dz",   "u", f"SCREEN {DZ}"),
    ("u.usr.tm",   "u", f"DEFUSR={TM}"),
    ("u.syn.for",  "u", "FOR I=1 STEP 2:NEXT"),
    ("u.dz.w",     "u", f"WIDTH {DZ}+1"),
    ("u.tm.loc",   "u", 'LOCATE "5",3'),
]

# 🟢 POSITIVE CONTROLS, two per reading. 🔴 EVERY ONE IS A ROW WHOSE ANSWER IS
# FIXED BY SOMETHING OTHER THAN THIS SLICE'S CLAIM: a genuine syntax error with
# no pending code, an ordinary single fault at a reader that already checked
# before this slice existed, and the same pair on the untrapped reading.
CONTROLS = ("n.syn.zork", "n.dz.w", "u.syn.for", "u.dz.w")

CONTROL_WANT = {
    "n.syn.zork": " 2 ",
    "n.dz.w":     " 11 ",
    "u.syn.for":  "Syntax error in 20",
    "u.dz.w":     "Division by zero in 20",
}

NEGATIVE = {
    "n.syn.for":  "NEGATIVE CONTROL — a syntax error with NOTHING pending",
    "n.syn.zork": "NEGATIVE CONTROL — an unknown statement, nothing pending",
    "n.syn.swap": "NEGATIVE CONTROL — a malformed SWAP, nothing pending",
    "n.ok.for":   "NEGATIVE CONTROL — a clean loop must stay silent",
    "n.ok.usr":   "NEGATIVE CONTROL — a clean DEFUSR must stay silent",
    "n.ok.poke":  "NEGATIVE CONTROL — a clean POKE must stay silent",
    "n.ok.scr":   "NEGATIVE CONTROL — a clean SCREEN must stay silent",
    "n.ok.chain": "NEGATIVE CONTROL — ':'-chained statements still chain",
    "n.dz.w":     "NEGATIVE CONTROL — one numeric fault at a checking reader",
    "n.5.w":      "NEGATIVE CONTROL — the SQR code alone",
    "n.ov.w":     "NEGATIVE CONTROL — the overflow code alone",
    "n.tm.w":     "NEGATIVE CONTROL — a type fault alone is still 13",
    "n.tm.loc":   "NEGATIVE CONTROL — the trapped reading itself",
    "n.trap.res": "NEGATIVE CONTROL — the handler + RESUME path is sound",
}
LABEL_W = 11

DEFERRED = {
    # Measured, not scored, each with the reason it is out of this slice's reach.
    "c.line.tm":
        "DEFERRED — LINE raises its OWN Illegal function call eagerly from "
        "inside its coordinate parse, so it reaches NEITHER of this slice's "
        "two writers; ERR 5 here vs 13 on both references. A per-driver fix "
        "in graphics.asm",
    # 🎯 `u.scr.dz` WAS DEFERRED HERE AND IS NOW SCORED. D-SCRERR (2026-08-10,
    # docs/spec-basic-screenerr.md) closed it: SCREEN's mode is a checked byte
    # and the check runs BEFORE CHGMOD, so the mode is never applied and the
    # `RUN` echo this reading anchors on survives. The statement boundary is
    # still by construction too late for a driver with a side effect -- what
    # changed is that ex_screen no longer relies on it.
}

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
                               f"zb_stpd_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        lines = list(cfg["reset"]) + program(kind, stmt) + ["RUN"]
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", lines)],
            batch=False, boot=cfg["boot"], step=cfg["step"], **kw)
        out[label] = read_case(kind, caps[0])
    return out


DENOMINATOR = (
    "(WHERE a pending error code can be LOST between the fault and a reader) x "
    "(WHICH statement is the loser). The tree has FIFTY-SIX `call`/`jp eval` / "
    "`ev_logic` sites; SEVEN of them reach `check_expr_errors`/"
    "`check_fperr_only` within eight lines and SIX reach `stmt_error` before "
    "any check, so a static scan alone cannot classify the remaining 43 -- "
    "every one of them ends at `jp exec_stmt`, whose unconditional "
    "`ld (FPERR),a` is the SINGLE point at which a live code is discarded, and "
    "`stmt_error` is the single point at which one is outranked. That is why "
    "this probe samples STATEMENTS rather than call sites: two writers to "
    "close, and a statement is the only thing that can tell you whether a "
    "given driver reaches them. Sampled: FOR (three argument positions), "
    "SCREEN, DEF USR, POKE, LINE (drivers with no check) x the four fault "
    "codes 11/6/5/13 x the two ways to arrive (the statement ENDS with a live "
    "code, or its own delimiter check fails over one) x the two string-compare "
    "mismatch SITES (ers_rhs_mismatch `Q$<5`, evr_mismatch `5<Q$`) x TRAPPED "
    "vs UNTRAPPED. The g.* rows re-measure the drivers that DO check, which is "
    "the population `make penderr-acceptance` (61) and `make tmfp-acceptance` "
    "(50) own; those two, plus `make width-acceptance` (94) and "
    "`make locarg-acceptance` (45), are this slice's green control set. NOT "
    "swept: the cursor POSITION itself, which no screen row can witness -- it "
    "is measured by freezing the machine and reading IX, "
    "docs/stmtpend-msx1-characterization.md §3."
)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-STMTPEND: a fault that already happened outranks the "
                    "rest of the statement")
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

    print("D-STMTPEND — a fault that already happened outranks the rest of "
          f"the statement    sides: {', '.join(sides)}")
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
              "    n.syn.zork = a syntax error with NO pending code is still "
              "ERR 2.\n"
              "    n.dz.w     = an ordinary numeric fault reports its OWN code "
              "(11).\n"
              "    u.syn.for  = the UNTRAPPED reading -- ONE message, naming "
              "its line.\n"
              "    u.dz.w     = an untrapped numeric fault, the OTHER "
              "message.\n"
              "    🔴 Neither pair can fail because this slice's claim is "
              "wrong: one has\n"
              "    nothing pending to outrank, the other has nothing to be "
              "outranked BY.\n"
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
    print("SIDES: vg8020,cf3300,zb — ON ERROR, ERR, RESUME, FOR/NEXT, SCREEN, "
          "DEF USR, POKE, LINE, WIDTH, LOCATE, PRINT, SOUND, ON..GOTO, DIM and "
          "HEX$/OCT$/STRING$/MID$ are core MSX-BASIC, present on every MSX1, so "
          "BOTH references are legitimate oracles for every row here")
    print("DENOMINATOR: " + DENOMINATOR)
    if a.gate and dis:
        sys.stderr.write(f"stmtpend: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
