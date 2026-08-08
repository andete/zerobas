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

and DECLINES the other two WITH NUMBERS (spec §7): `FIELD` and `LSET`/`RSET`
need a FLD_TAB identity change AND a third site nobody had listed -- the
FIELDed-READ hook, which lives on `str_eval_arr` and does not exist. Their two
rows are carried here as DEFERRED: printed every run, scored in neither
direction, so a declined half stays visible in a GATE and not only in a document.

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
    # --- DECLINED, spec §7: carried so the declined half stays in a GATE -----
    ("d.ary",      True,  ['DIM A$(3)', 'OPEN"LV.DAT"AS #1',
                           'FIELD#1,10 AS A$(1)', 'CLOSE#1', 'PRINT"[OK]"']),
    ("s.fldary",   True,  ['DIM A$(3)', 'OPEN"LV.DAT"AS #1',
                           'FIELD#1,10 AS A$(1)', 'LSET A$(1)="HI"',
                           'PRINT"[";A$(1);"]"']),
]

CONTROLS = ("m.ctl", "f.ctl", "f.linectl")
# f.mixctl is a control for f.arymix but NOT a member of CONTROLS: it is a
# DEFERRED row (see below), so it must never exit 2 — it is a known-red scalar
# twin whose job is to say WHICH defect its array partner is blocked on.
CONTROL_WANT = {"m.ctl": "XYLLO", "f.ctl": "HI", "f.linectl": "HI",
                "f.mixctl": "HILO"}
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
}

# --- DEFERRED rows: measured, printed, NEVER scored -------------------------
# ⚠️ "A row that can only ever be red is doc debt, not a gate." These two belong
# to the DECLINED half (spec §7) and are red for a reason this slice priced and
# did not take: FIELD/LSET need FLD_TAB to identify an ELEMENT (entry 6 -> 8 B,
# which does not fit the 96-byte table without cutting FLD_SLOTS 16 -> 12) AND a
# FIELDed-read hook on str_eval_arr, which is a third site and lives in the LOW
# region. They stay MEASURED and PRINTED -- a deferral has to carry its evidence
# -- and are excluded from the tally in both directions.
#
# 🔴 f.mixctl / f.arymix ARE DEFERRED FOR A DIFFERENT REASON, AND ONLY A CONTROL
# COULD HAVE TOLD THE TWO APART. The spec predicted `f.arymix` GREEN (HILO) on
# the POSITION axis. It measured `Syntax error` -- and so does its SCALAR twin
# `f.mixctl` (`INPUT#1,A$,B$`, no subscript anywhere). `inp_readvar` has no
# variable-LIST loop at all: it parses ONE target and falls into `jp exec_stmt`,
# so the leftover `,` is what errors. That is a defect about the LIST, not about
# the SUBSCRIPT, and it is filed as its own residual. Without `f.mixctl` this
# probe would have scored `f.arymix` as an array failure and this slice would
# have been blamed for a gap it does not own ([[row-with-two-candidate-causes]],
# [[one-row-cannot-separate-two-rules]]). ⚠️ POSITION is therefore NOT covered
# for `INPUT #n` by this gate -- named in the denominator rather than implied.
#
# 🔴 AND m.ctldrift / m.arydrift ARE DEFERRED FOR A THIRD REASON, WHICH THE
# MEASUREMENT FOUND AND THE SPEC HAD PREDICTED GREEN. Both references answer
# `Illegal function call` to `VARPTR(<unset var>)` -- isolated on its own, away
# from MID$ entirely: `X=VARPTR(Q)` with Q unset is IFC on the VG-8020 and `OK`
# here. So the statement these two rows run is REFUSED by the oracle, and their
# zerobas reading cannot be scored against it.
# 🎯 THE CONSEQUENCE IS BIGGER THAN THESE TWO ROWS. arrays slice-4b §13a names
# VARPTR as THE ONLY eval-time scalar allocator -- so on the REFERENCE the whole
# §13a corruption class is not expressible at all, and it exists here only
# because zerobas's VARPTR accepts a domain the reference rejects. The
# correction this slice carries is therefore RIGHT and REACHABLE (a zerobas
# program reaches it today) but NOT ORACLE-ABLE: no program both references
# accept can shift ARYTAB mid-statement. Filed as its own residual.
# ⚠️ The rows STAY, printed with their readings, because they are still the live
# detector for K-LV5 -- the knife that deletes the correction moves `m.arydrift`
# and nothing else in the zb column. A deferral has to carry its evidence
# ([[a-pinned-divergence-is-a-live-detector]]).
DEFERRED = {
    "d.ary": "DEFERRED — FIELD: declined with numbers, spec §7",
    "s.fldary": "DEFERRED — LSET on a FIELDed array element, spec §7",
    "f.mixctl": "DEFERRED — `INPUT #n` parses only ONE target; a LIST defect, "
                "not an array one",
    "f.arymix": "DEFERRED — blocked by f.mixctl: the same LIST defect, so this "
                "row cannot speak about the SUBSCRIPT",
    "m.ctldrift": "DEFERRED — blocked by VARPTR(<unset>): IFC on BOTH "
                  "references, accepted here. A VARPTR DOMAIN defect",
    "m.arydrift": "DEFERRED — same block; kept as the LIVE DETECTOR for K-LV5, "
                  "the arrays-§13a correction knife",
}

LABEL_W = 10
SENTINELS = ("<NO CAPTURE>", "<NO OUTPUT>", "<NO DISK ON THIS SIDE>")

ERRORS = ("Syntax error", "Type mismatch", "Subscript out of range",
          "Illegal function call", "Out of memory", "Out of string space",
          "Overflow", "Bad file number", "File not found", "Field overflow",
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
            dsk = os.path.join(tempfile.gettempdir(),
                               f"zb_lvfix_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        body = [f"{10 * (k + 1)} {ln}" for k, ln in enumerate(lines)]
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
            batch=False, boot=cfg["boot"], step=cfg["step"], **kw)
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
          "— and the DEFERRED rows of the DECLINED FIELD/LSET half, carried so "
          "a priced decline stays visible in a gate.")
    print("NOT COVERED, named rather than implied: POSITION for `INPUT #n` "
          "(f.mixctl shows the site parses only ONE target — a LIST defect, "
          "filed separately); the arrays-§13a mid-statement ARYTAB shift "
          "(m.ctldrift/m.arydrift — NOT oracle-able: the only eval-time scalar "
          "allocator is VARPTR, which both references REFUSE on an unset "
          "variable, so no program they accept can shift ARYTAB mid-statement); "
          "FIELD / LSET / RSET (spec §7); numeric `INPUT #n` (rejected before "
          "any target parse); and a subscript that is itself an array element.")
    if a.gate and dis:
        sys.stderr.write(f"lvfix: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
