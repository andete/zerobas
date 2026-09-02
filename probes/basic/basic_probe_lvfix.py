#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-LVFIX — an array element as the lvalue target of `MID$(…)=` and `INPUT #n`.

docs/spec-basic-lvsites.md. The measurement this acts on is
docs/lvsites-msx1-characterization.md, which found that ALL FOUR of the lvalue
parse sites D-ARYLV never checked diverge on an array element. The carve scout
(spec §6) prices all four and ships TWO:

  ex_mid_stmt   basic/str-engine.asm   `MID$(<target>,n,m) = <expr>`   -- LOW region
  inp_readvar   basic/files.asm        `INPUT #n` / `LINE INPUT #n`    -- page 1

and DECLINED the other two WITH NUMBERS (spec §7): `FIELD` and `LSET`/`RSET`
need a FLD_TAB identity change AND a third site nobody had listed -- the
FIELDed-READ hook, which lives on `str_eval_arr` and did not exist. Their two
rows rode here as DEFERRED so a declined half stayed visible in a GATE and not
only in a document.

✅ AND THAT IS WHY THEY ARE SCORED NOW. D-FLDARY (docs/spec-basic-fldary.md,
2026-08-08) re-priced the decline against a design and shipped it: `d.ary` and
`s.fldary` are promoted in place, with `d.ctl` / `s.fld` added beside them as a
control PER ARM. The full denominator of that half -- element identity, RANK, the
error faces, RSET -- is basic_probe_fldary.py; these four are what THIS probe
measured while the half was declined, kept so the promotion is visible here too.

🔴 THE ORACLE IS NOT UNIFORM AND THIS PROBE REFUSES TO PRETEND IT IS. The `MID$`
rows need no disk and have TWO references. `INPUT #n`, `FIELD` and `LSET` are
Disk BASIC: a diskless Philips VG-8020 answers `Syntax error` to those words, so
it cannot express the question and recording its answer would manufacture an
agreement out of an absent disk controller. Those rows rest on the National
CF-3300 alone (NO_DISK_SIDES, the same disposition basic_probe_dskmsg.py and
basic_probe_lvsites.py carry). Every row prints its reference count.

🎯 `m.arydrift` AND `m.ctldrift` EXIST BECAUSE A KNIFE WAS DRAFTED FIRST.
`ex_mid_stmt` does not STORE through its target: it stashes the target's
descriptor address in MIDS_DEST and then parses n, m and the whole RHS before
using it. Any of those three evaluations can run `VARPTR(<new var>)`, which
arrays slice-4b §13a names as the ONLY eval-time scalar allocator and which
shifts the whole array region up. §13a's site audit EXEMPTED ex_mid_stmt in as
many words -- "targets a SCALAR string in the fixed STRTAB pool" -- and that
exemption is a statement about the TARGET, which this slice changes. So the fix
carries an ARYTAB-delta correction; and asking "which row moves if I cut it?"
answered NONE on the row set that existed, because every other row allocates
nothing mid-statement. The row was added because the knife was written first
([[draft-the-knives-before-freezing-the-row-set]]).

⚠️ `m.ctldrift` IS ITS SCALAR TWIN AND MAY BE A PRE-EXISTING RED. The scalar arm
is deliberately left uncorrected (spec §5.2): a scalar-chain insert shifts only
the entries ABOVE the insertion point, so the ARYTAB delta is the wrong
correction for it. Whether it is stale TODAY is a question §13a's audit could not
have answered -- arrays slice-4c unified string scalars into the contiguous
chain AFTER that audit was written, so its premise ("the fixed STRTAB pool") no
longer describes the tree. If `m.ctldrift` reads red it is a FINDING about a
pre-existing defect, scored as an ordinary divergence and filed -- and it does
NOT disqualify `m.arydrift`, whose own arm IS corrected. That is the 2x2 the
LSET site forced one document earlier, applied forward.

🔴 A CONTROL FAILING ON A REFERENCE AND ON ZEROBAS ARE DIFFERENT EVENTS
([[classify-a-control-failure-by-which-side-failed-it]]):

  * control fails on a REFERENCE -> the fixture is broken (a disk that did not
    mount, a file that was never written). Exit 2, score nothing. Only a
    reference can tell you the apparatus is wrong, because only it is supposed
    to be right.
  * control fails on ZEROBAS     -> an ordinary divergence, scored like any
    other row, which additionally SCOPES ITS OWN ARM.

⚠️ EACH ROW GETS A FRESH COPY OF THE TEST IMAGE -- the `INPUT #n` rows CREATE a
file, so a shared image would let one row's leftovers decide another's reading
([[test-disk-mutation-gotcha]]).

Clean-room: observed screen output only; both reference ROMs are black boxes.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_repl                                                 # noqa: E402
import probe_report                                              # noqa: E402
import probe_tmp                                                 # noqa: E402

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE",
                            "C-BIOS_MSX1_EU_REPACK_DISK")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
TEST_DSK = os.path.join(REPO, "disk", "test720.dsk")

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW",), diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW"), diska=True),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW",), diska=True),
}
NO_DISK_SIDES = ("vg8020",)

# The sequential file every `f.*` row reads back. Written by the row itself, on
# its own fresh image, so no row can inherit another's bytes.
def wr(payload: str) -> list[str]:
    return ['OPEN"LV.TXT"FOR OUTPUT AS #1', f'PRINT#1,"{payload}"', 'CLOSE#1',
            'OPEN"LV.TXT"FOR INPUT AS #1']


# (label, needs_disk, [program lines])
CASES = [
    # --- MID$(...)= : no fixture at all, so these are the TWO-reference rows --
    ("m.ctl",      False, ['A$="HELLO"', 'MID$(A$,1,2)="XY"',
                           'PRINT"[";A$;"]"']),
    ("m.ary",      False, ['DIM A$(3)', 'A$(1)="HELLO"',
                           'MID$(A$(1),1,2)="XY"', 'PRINT"[";A$(1);"]"']),
    ("m.aryvar",   False, ['DIM A$(3)', 'A$(1)="HELLO"', 'I=1',
                           'MID$(A$(I),1,2)="XY"', 'PRINT"[";A$(1);"]"']),
    ("m.aryexpr",  False, ['DIM A$(3)', 'A$(1)="HELLO"',
                           'MID$(A$(2-1),1,2)="XY"', 'PRINT"[";A$(1);"]"']),
    ("m.ary2d",    False, ['DIM A$(2,2)', 'A$(1,1)="HELLO"',
                           'MID$(A$(1,1),1,2)="XY"', 'PRINT"[";A$(1,1);"]"']),
    ("m.aryoor",   False, ['DIM A$(3)', 'MID$(A$(9),1,2)="XY"']),
    # VARPTR(Q) allocates Q *during* the argument parse -- the §13a shift. The
    # `*0+1` keeps the VALUE machine-independent (an address is not oracle-able)
    # while keeping the ALLOCATION, which is the whole point of the row.
    ("m.ctldrift", False, ['A$="HELLO"', 'MID$(A$,VARPTR(Q)*0+1,2)="XY"',
                           'PRINT"[";A$;"]"']),
    ("m.arydrift", False, ['DIM A$(3)', 'A$(1)="HELLO"',
                           'MID$(A$(1),VARPTR(Q)*0+1,2)="XY"',
                           'PRINT"[";A$(1);"]"']),
    # --- INPUT #n / LINE INPUT #n : Disk BASIC, ONE reference ----------------
    ("f.ctl",      True,  wr("HI") + ['INPUT#1,A$', 'CLOSE#1',
                                      'PRINT"[";A$;"]"']),
    ("f.ary",      True,  wr("HI") + ['DIM A$(3)', 'INPUT#1,A$(1)', 'CLOSE#1',
                                      'PRINT"[";A$(1);"]"']),
    ("f.aryvar",   True,  wr("HI") + ['DIM A$(3)', 'I=1', 'INPUT#1,A$(I)',
                                      'CLOSE#1', 'PRINT"[";A$(1);"]"']),
    ("f.ary2d",    True,  wr("HI") + ['DIM A$(2,2)', 'INPUT#1,A$(1,1)',
                                      'CLOSE#1', 'PRINT"[";A$(1,1);"]"']),
    ("f.aryoor",   True,  wr("HI") + ['DIM A$(3)', 'INPUT#1,A$(9)']),
    # 🎯 THE ROW THAT MAKES THE RESOLVE-ABORT OBSERVABLE. f.aryoor cannot see it:
    # `Subscript out of range` is produced on TWO paths -- the abort, and
    # check_expr_errors re-raising the still-set FPERR after the store has
    # already run -- so cutting the abort leaves the MESSAGE identical
    # ([[rule-gated-structurally-has-no-knife]]). What the abort actually
    # prevents is a STORE through an address the resolve never produced: with it
    # cut, tgt_store_str takes the SCALAR arm on a stale (TGT_ADDR) and writes
    # the field into the scalar A$. Trapping the error and printing that scalar
    # is what turns an invisible side effect into a row.
    ("f.aryoortrap", True, wr("HI") + ['DIM A$(3)', 'ON ERROR GOTO 90',
                                       'INPUT#1,A$(9)', 'END',
                                       'PRINT"[";A$;"]"']),
    # POSITION: the array element as a CONTINUATION item -- and its own SCALAR
    # control, because the row has two candidate causes and the first draft of
    # this probe had only the array half ([[row-with-two-candidate-causes]]).
    ("f.mixctl",   True,  wr("HI,LO") + ['INPUT#1,A$,B$', 'CLOSE#1',
                                         'PRINT"[";A$;B$;"]"']),
    ("f.arymix",   True,  wr("HI,LO") + ['DIM B$(3)', 'INPUT#1,A$,B$(1)',
                                         'CLOSE#1',
                                         'PRINT"[";A$;B$(1);"]"']),
    ("f.linectl",  True,  wr("HI") + ['LINE INPUT#1,A$', 'CLOSE#1',
                                      'PRINT"[";A$;"]"']),
    ("f.lineary",  True,  wr("HI") + ['DIM A$(3)', 'LINE INPUT#1,A$(1)',
                                      'CLOSE#1', 'PRINT"[";A$(1);"]"']),
    # --- WAS DECLINED (spec §7), SHIPPED 2026-08-08 by D-FLDARY --------------
    # These two rode here as DEFERRED for one slice, which is exactly what a
    # priced decline in a GATE is for: they are promoted in place, with a
    # control PER ARM added beside them (docs/spec-basic-fldary.md). The full
    # denominator of that half -- element identity, RANK, the error faces, RSET
    # -- is basic_probe_fldary.py; these two are the rows THIS probe measured
    # while the half was declined, and they now have to stay green here too.
    ("d.ctl",      True,  ['OPEN"LV.DAT"AS #1', 'FIELD#1,10 AS A$', 'CLOSE#1',
                           'PRINT"[OK]"']),
    ("d.ary",      True,  ['DIM A$(3)', 'OPEN"LV.DAT"AS #1',
                           'FIELD#1,10 AS A$(1)', 'CLOSE#1', 'PRINT"[OK]"']),
    ("s.fld",      True,  ['OPEN"LV.DAT"AS #1', 'FIELD#1,10 AS A$',
                           'LSET A$="HI"', 'PRINT"[";A$;"]"']),
    ("s.fldary",   True,  ['DIM A$(3)', 'OPEN"LV.DAT"AS #1',
                           'FIELD#1,10 AS A$(1)', 'LSET A$(1)="HI"',
                           'PRINT"[";A$(1);"]"']),
]

CONTROLS = ("m.ctl", "f.ctl", "f.linectl", "d.ctl", "s.fld")
# f.mixctl is a control for f.arymix but NOT a member of CONTROLS: it is a
# DEFERRED row (see below), so it must never exit 2 — it is a known-red scalar
# twin whose job is to say WHICH defect its array partner is blocked on.
CONTROL_WANT = {"m.ctl": "XYLLO", "f.ctl": "HI", "f.linectl": "HI",
                "f.mixctl": "HILO", "d.ctl": "OK", "s.fld": "HI        "}
# Which control scopes which row. `LINE INPUT #n` has its own arm, so a red
# `INPUT #n` control must not be allowed to explain away `f.lineary` (the
# lvsites LSET site is where that lesson was measured).
SITE_CONTROL = {
    "m.ary": "m.ctl", "m.aryvar": "m.ctl", "m.aryexpr": "m.ctl",
    "m.ary2d": "m.ctl", "m.aryoor": "m.ctl", "m.ctldrift": "m.ctl",
    "m.arydrift": "m.ctl",
    "f.ary": "f.ctl", "f.aryvar": "f.ctl", "f.ary2d": "f.ctl",
    "f.aryoor": "f.ctl", "f.aryoortrap": "f.ctl",
    "f.arymix": "f.mixctl",             # NOT f.ctl — see DEFERRED below
    "f.lineary": "f.linectl",
    # The FIELD/LSET half has TWO ARMS and gets a control per arm: a red `d.ctl`
    # must not be allowed to explain away `s.fldary`, whose own control is the
    # FIELDed scalar `s.fld` (docs/lvsites-msx1-characterization.md §3).
    "d.ary": "d.ctl", "s.fldary": "s.fld",
}

# --- DEFERRED rows: measured, printed, NEVER scored -------------------------
# ⚠️ "A row that can only ever be red is doc debt, not a gate."
#
# ✅ d.ary / s.fldary WERE HERE AND ARE NOT ANY MORE (2026-08-08, D-FLDARY,
# docs/spec-basic-fldary.md). They are now SCORED, with d.ctl / s.fld beside them
# as a control per arm. This is what carrying a priced decline in a gate is for:
# the two rows stayed visible for exactly one slice, and the re-pricing found
# that THREE of the four reasons for the decline did not survive a design --
# FLD_TAB does not grow (the discriminator IS the key, and the two key spaces are
# disjoint by construction), the price was +38 B not ~+80, and a carve WAS
# available (lrset_store -> a page-0 tenant, +57 B). What survived is that 38
# does not fit 18, which is why that slice is funded rather than free.
#
# ✅ f.mixctl / f.arymix WERE DEFERRED, AND D-INPLIST (2026-08-19) CLOSED WHAT
# BLOCKED THEM. Both are SCORED now and both read `HILO`, the CF-3300's own
# answer. The history is kept because it is the reason this probe has a scalar
# control at all: the spec predicted `f.arymix` GREEN (HILO) on the POSITION
# axis, it measured `Syntax error`, and so did its SCALAR twin `f.mixctl`
# (`INPUT#1,A$,B$`, no subscript anywhere). `inp_readvar` had no variable-LIST
# loop -- it parsed ONE target and fell into `jp exec_stmt`, so the leftover `,`
# was what errored. That was a defect about the LIST, not about the SUBSCRIPT.
# Without `f.mixctl` this probe would have scored `f.arymix` as an array failure
# and D-LVFIX would have been blamed for a gap it did not own
# ([[row-with-two-candidate-causes]], [[one-row-cannot-separate-two-rules]]).
# 🎯 AND THE CONTROL IS WHAT MAKES THE FIX READABLE TOO: `f.arymix` going green
# says the ARRAY-element target works in a continuation position, which is the
# POSITION axis D-LVFIX shipped and could not demonstrate here until now. The
# gate covers POSITION for `INPUT #n` from this slice on -- it is no longer an
# exclusion in the denominator below.
#
# ✅ m.ctldrift / m.arydrift WERE DEFERRED TOO, AND D-VPTRDOM (2026-08-19)
# CLOSED THAT BLOCK AS WELL. Both references answer `Illegal function call` to
# `VARPTR(<unset var>)` -- isolated away from MID$ entirely: `X=VARPTR(Q)` with
# Q unset is IFC on the VG-8020 AND the CF-3300, and USED TO BE `OK` here,
# because ev_f_varptr allocated the variable. It FINDS now (var_find_typed) and
# defers FPERR=3, so all three sides answer IFC and both rows are SCORED.
# 🔴 AND THAT COST THIS PROBE A DETECTOR -- SAID PLAINLY, NOT ABSORBED. arrays
# slice-4b §13a names VARPTR as THE ONLY eval-time scalar allocator. While
# zerobas accepted the wider domain, `m.arydrift` was the LIVE detector for
# K-LV5 (the knife that deletes the §13a correction moved that row and nothing
# else). Now that zerobas agrees with the references, no program ANY of the
# three sides accepts can shift ARYTAB mid-statement -- so the §13a guards
# (ex_let_arr's ary_snapshot_offset/ary_apply_offset and D-LVFIX's tgt_desc
# correction) are UNREACHABLE FROM BASIC rather than wrong. They still run; they
# can simply never see a nonzero offset.
# ⚠️ THE GUARDS ARE DELIBERATELY NOT DELETED. The argument for them is static and
# they are cheap, and a future eval-time allocator needs them back. What is gone
# is the ABILITY TO TEST THEM from a program, which is a loss of COVERAGE and not
# of correctness -- exactly the trade the residual warned about before the fix
# was priced ("anyone narrowing VARPTR's domain should price what that makes
# dead"). K-LV5 has no live detector from this slice on, and that is recorded
# here rather than discovered later ([[a-pinned-divergence-is-a-live-detector]]).
# f.mixctl / f.arymix graduated 2026-08-19 (D-INPLIST); m.ctldrift / m.arydrift
# the same day (D-VPTRDOM). A graduation is a DELETION FROM THIS LITERAL, never
# prose about one -- so the literal is empty, and this gate now scores every row
# it prints.
DEFERRED = {}

LABEL_W = 10
SENTINELS = ("<NO CAPTURE>", "<NO OUTPUT>", "<NO DISK ON THIS SIDE>")

ERRORS = ("Syntax error", "Type mismatch", "Subscript out of range",
          "Illegal function call", "Out of memory", "Out of string space",
          "Overflow", "Bad file number", "File not found", "FIELD overflow",
          "Bad file name", "Disk offline", "File already open",
          "Redimensioned array")


def bracket(raw: str | None) -> str:
    """The `[...]` span the RUN printed, or a sentinel naming what came instead."""
    if raw is None:
        return "<NO CAPTURE>"
    txt = " ".join(str(omsx_repl.screen_tail(raw, "RUN") or "").split("\n"))
    i = txt.find("[")
    j = txt.find("]", i + 1)
    if i >= 0 and j > i:
        return txt[i + 1:j]
    for e in ERRORS:
        if e in txt:
            return f"<{e}>"
    return "<NO OUTPUT>"


def run_side(side: str, only: list[str]) -> dict:
    cfg = SIDES[side]
    out = {}
    for label, needs_disk, lines in CASES:
        if only and label not in only:
            continue
        if needs_disk and side in NO_DISK_SIDES:
            # NOT a reading: a diskless machine cannot express the question.
            out[label] = "<NO DISK ON THIS SIDE>"
            continue
        kw = {}
        if cfg["diska"]:
            dsk = probe_tmp.tmp(f"zb_lvfix_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        body = [f"{10 * (k + 1)} {ln}" for k, ln in enumerate(lines)]
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
            batch=False, reset=(), boot=cfg["boot"], step=cfg["step"], **kw)
        out[label] = bracket(caps[0])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-LVFIX: an array element as a MID$= / INPUT#n target")
    ap.add_argument("--sides", default="vg8020,cf3300,zb")
    ap.add_argument("--only", default="")
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless every scored row agrees with its oracle")
    a = ap.parse_args()

    sides = [s for s in a.sides.split(",") if s]
    only = [o for o in a.only.split(",") if o]
    for s in sides:
        if s not in SIDES:
            sys.stderr.write(f"unknown side {s!r}\n")
            return 2

    results = {s: run_side(s, only) for s in sides}
    present = [lab for lab, _, _ in CASES if any(lab in results[s]
                                                 for s in sides)]

    print("D-LVFIX — an ARRAY ELEMENT as a MID$(…)= / INPUT #n target   "
          f"sides: {', '.join(sides)}")
    print("=" * 78)

    # 🔴 ONLY A REFERENCE CAN SAY THE APPARATUS IS BROKEN (see the docstring).
    bad = []
    for ctl in CONTROLS:
        if ctl not in present:
            continue
        for s in sides:
            if s == "zb":
                continue                # a zerobas miss is a RESULT, not a break
            got = results[s].get(ctl)
            if got in (None, "<NO DISK ON THIS SIDE>"):
                continue                # not a reading, not a failure
            if got != CONTROL_WANT[ctl]:
                bad.append((ctl, s, got))
    if bad:
        for lab, s, got in bad:
            print(probe_report.row("FAIL", lab, LABEL_W, {s: got},
                                   "   [POSITIVE CONTROL]"))
            print(f"        wanted {CONTROL_WANT[lab]!r}")
        print("\n*** A POSITIVE CONTROL FAILED ON A REFERENCE, so nothing was "
              "measured.\n"
              "    Each control is the SCALAR form of its own site's statement, "
              "on the same\n"
              "    fixture. A REFERENCE failing it means the fixture is broken "
              "-- a disk that\n"
              "    did not mount, a file that was never written, a channel that "
              "never opened.\n"
              "    (A control failing on `zb` is NOT this: that is an ordinary "
              "divergence and\n"
              "    is scored, because only a reference is supposed to be right.)"
              " Exit 2 (not 1)\n"
              "    = the instrument was broken, NOT a regression.")
        for lab in present:
            vals = {s: results[s][lab] for s in sides if lab in results[s]}
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   "   (not scored)"))
        print(probe_report.footer(len(bad) + len(present), 0,
                                  "NOT MEASURED (a positive control failed)"))
        return 2

    def ctl_red_on_zb(ctl: str) -> bool:
        got = results.get("zb", {}).get(ctl)
        return (got not in (None, "<NO DISK ON THIS SIDE>")
                and got != CONTROL_WANT.get(ctl))

    agree = dis = noref = onlyone = deferred = 0
    for lab in present:
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        if lab in DEFERRED:
            # Printed, not scored -- in EITHER direction. A deferred row that
            # started agreeing would be a finding, so it still shows its reading.
            deferred += 1
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   f"   [{DEFERRED[lab]}]"))
            continue
        refs = {s: v for s, v in vals.items()
                if s in ("vg8020", "cf3300") and v not in SENTINELS}
        note = "   [POSITIVE CONTROL]" if lab in CONTROLS else ""
        own = SITE_CONTROL.get(lab)
        if own and own in present and ctl_red_on_zb(own):
            note += ("   [ITS OWN SCALAR CONTROL IS RED ON zb — this row is "
                     "NOT evidence about the SUBSCRIPT]")
        if not refs:
            noref += 1
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   "   [NO REFERENCE ON ANY REQUESTED SIDE]"))
            continue
        if len(set(refs.values())) > 1:
            dis += 1
            print(probe_report.row("DIFF", lab, LABEL_W, vals,
                                   note + "   [REFERENCES DISAGREE — no oracle]"))
            continue
        if len(refs) == 1:
            onlyone += 1
            note += f"   [ONE REFERENCE ONLY ({list(refs)[0]})]"
        oracle = list(refs.values())[0]
        zb = vals.get("zb")
        ok = zb == oracle and zb not in SENTINELS
        agree += ok
        dis += not ok
        print(probe_report.row("ok" if ok else "DIFF", lab, LABEL_W, vals, note))

    print(probe_report.footer(len(present), len(present) - noref - deferred,
                              f"{agree} agree, {dis} diverge, "
                              f"{deferred} deferred (not scored), "
                              f"{noref} without a reference"))
    print("=" * 78)
    print(f"{agree}/{agree + dis} readings match their reference "
          f"({len(CASES)} cases, {len(CONTROLS)} positive controls, "
          f"{onlyone} row(s) with ONE reference only, "
          f"{len(DEFERRED)} DEFERRED row(s) measured but not scored)")
    print("🔴 ORACLE STRENGTH IS NOT UNIFORM: only the MID$ rows have TWO "
          "references. INPUT #n / FIELD / LSET are Disk BASIC, which a diskless "
          "VG-8020 cannot express — so those rows rest on the CF-3300 alone, a "
          "weaker claim than every row D-ARYLV rested on.")
    print("DENOMINATOR: (subscript FORM: literal / variable / expression) x "
          "(RANK: 1-D / 2-D) x (POSITION: list head / continuation) x (VERB: "
          "MID$= / INPUT #n / LINE INPUT #n), plus the out-of-range row at EACH "
          "site (whose oracle is an ERROR, not a value), plus the "
          "mid-statement-allocation PAIR that arrays §13a forces on ex_mid_stmt "
          "— and the FIELD/LSET pair this probe carried DEFERRED while that half "
          "was declined, now SCORED with a control per arm (D-FLDARY). "
          "POSITION for `INPUT #n` is covered from D-INPLIST (2026-08-19): "
          "f.mixctl/f.arymix were DEFERRED behind a LIST defect at inp_readvar "
          "and are scored now, so the continuation position is measured for "
          "that verb and not only for MID$=.")
    print("NOT COVERED, named rather than implied: the arrays-§13a "
          "mid-statement ARYTAB shift — and it is now unreachable on ALL THREE "
          "sides, not just the two references (D-VPTRDOM made zerobas refuse "
          "VARPTR(<unset>) too, and VARPTR was the only eval-time scalar "
          "allocator), so the §13a guards are untestable from BASIC and K-LV5 "
          "has no live detector; "
          "the FIELD/LSET half's own DENOMINATOR — element identity, RANK, the "
          "error faces, RSET — which is basic_probe_fldary.py, not this probe; "
          "numeric `INPUT #n` (rejected before any target parse); and a "
          "subscript that is itself an array element.")
    if a.gate and dis:
        sys.stderr.write(f"lvfix: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
