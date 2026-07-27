#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""DIRECT-MODE control flow (`FOR`/`NEXT`, `GOSUB`/`RETURN`) differential.

WHY THIS PROBE EXISTS -- the gap it closes:
zerobas's FOR/NEXT and GOSUB/RETURN have always been gated through STORED
programs (basic_probe_loops.py types numbered lines and `RUN`s them; every
trap/graphics acceptance case has the same shape). Nothing exercised the SAME
statements typed at the prompt. On 2026-07-26 a direct-mode `FOR I=1 TO 7:NEXT`
was found to raise "out of memory" on the repack build while the VG-8020 runs it
-- a whole execution MODE with zero coverage, in verbs that had 100% gate marks.

MECHANISM (measured, not inferred): `GSP` ($E041) and `FSP` ($E043), the GOSUB
and FOR control-stack pointers, are initialised in exactly ONE place --
`run_program` (basic/program.asm). Cold boot never touches them, so before the
first `RUN` they hold power-on RAM garbage; openMSX leaves $FFFF there, which is
above both `GOSUB_STK_END` and `FOR_STK_END`, so the very first direct `FOR` or
`GOSUB` takes the depth-overflow arm and raises ERR 7. Read them at the prompt:

    PRINT PEEK(&HE043)+256*PEEK(&HE044)   -> 65535 at boot, 57456 after any RUN

⚠️ THIS MATRIX IS BOOT-PER-CASE BY DEFAULT AND MUST STAY THAT WAY.
The defect is a COLD-BOOT-STATE defect. In a batched run the first case that
`RUN`s a stored program initialises FSP/GSP for the whole boot, and every later
direct-mode case then passes -- a green gate over a live bug. `--batch` exists
for a quick look only and prints a warning; the Makefile target never uses it.
(Same family as the apparatus traps in [[traps-t2-strig-slice]] /
[[traps-t3-key-slice]]: the delivery granularity is part of the measurement.)

GROUPS
  direct  -- FOR/NEXT and GOSUB/RETURN typed at the prompt (the defect).
  cross   -- does a control frame SURVIVE the end of a direct line? This is what
             decides whether the fix is "initialise at cold boot" or "reset at
             every command-level entry"; the reference answers it.
  stored  -- the stored-program controls (green today) + `CONT` resuming INTO a
             live FOR frame, which is the case that forbids a blanket
             reset-per-direct-line.

Clean-room: observed outputs only; the reference ROM is a black box.
"""
from __future__ import annotations
import argparse, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import omsx_repl  # noqa: E402
from omsx_repl import PROMPTS  # both machines' prompt strings

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

M = "CHR$(35)"          # '#' marker -- runtime output only, never the line echo

# --- group `direct`: the defect surface ------------------------------------
# (label, [lines])  -- every line is typed at the prompt; nothing is RUN.
DIRECT = [
    ("sum",       [f"A=0:FORI=1TO7:A=A+I:NEXT:PRINT{M};A;{M}"]),
    ("exitvar",   [f"FORI=1TO7:NEXT:PRINT{M};I;{M}"]),
    ("body",      [f"FORI=1TO3:PRINT{M};I;{M};:NEXT"]),
    ("tail",      [f"FORI=1TO7:NEXT:PRINT{M};1;{M}"]),
    ("head",      [f"FORI=1TO7:PRINT{M};1;{M};:NEXT"]),
    ("bare",      ["FORI=1TO7:NEXT"]),
    ("step3",     [f"A=0:FORI=1TO9STEP3:A=A+I:NEXT:PRINT{M};A;{M}"]),
    ("stepneg",   [f"A=0:FORI=3TO1STEP-1:A=A+I:NEXT:PRINT{M};A;{M}"]),
    ("zerotrip",  [f"A=0:FORI=2TO1:A=A+1:NEXT:PRINT{M};A;I;{M}"]),
    ("nest",      [f"A=0:FORB=1TO2:FORC=1TO3:A=A+1:NEXT:NEXT:PRINT{M};A;{M}"]),
    ("nestnamed", [f"A=0:FORB=1TO2:FORC=1TO3:A=A+1:NEXTC:NEXTB:PRINT{M};A;{M}"]),
    ("gosub",     ["10 A=A+5:RETURN", f"A=0:GOSUB10:PRINT{M};A;{M}"]),
    ("gosub2",    ["10 A=A+5:RETURN", f"A=0:GOSUB10:GOSUB10:PRINT{M};A;{M}"]),
    ("gosubmid",  ["10 A=9:RETURN", f"GOSUB10:PRINT{M};A;{M}"]),
    ("gosubnest", ["10 GOSUB20:A=A+1:RETURN", "20 A=A+5:RETURN",
                   f"A=0:GOSUB10:PRINT{M};A;{M}"]),
    ("forgosub",  ["10 A=A+I:RETURN",
                   f"A=0:FORI=1TO3:GOSUB10:NEXT:PRINT{M};A;{M}"]),
]

# --- group `cross`: does a frame outlive the direct line that made it? ------
CROSS = [
    ("for_then_next", ["FORI=1TO3", f"NEXT:PRINT{M};I;{M}"]),
    ("next_alone",    [f"NEXT:PRINT{M};1;{M}"]),
    ("return_alone",  [f"RETURN:PRINT{M};1;{M}"]),
    ("gosub_noret",   ["10 A=7", f"GOSUB10", f"PRINT{M};A;{M}"]),
]

# --- group `stored`: the controls that are green today, + CONT -------------
STORED = [
    ("run_for",   [f"10 A=0:FORI=1TO7:A=A+I:NEXT:PRINT{M};A;{M}", "RUN"]),
    ("run_gosub", ["10 A=0:GOSUB30", f"20 PRINT{M};A;{M}:END", "30 A=5:RETURN",
                   "RUN"]),
    ("run_then_direct",
                  [f"10 PRINT{M};1;{M}", "RUN",
                   f"A=0:FORI=1TO7:A=A+I:NEXT:PRINT{M};A;{M}"]),
    ("cont_in_for",
                  ["10 A=0", "20 FORI=1TO3", "30 A=A+I",
                   "40 IF I=2 THEN STOP", "50 NEXT", f"60 PRINT{M};A;{M}",
                   "RUN", "CONT"]),
]

# --- group `xfer`: control TRANSFER out of a typed line --------------------
# The other half of the same defect. `exec` walks statements; every transfer is
# a FLAG the loop AROUND it services, so before this slice a typed GOTO / IF-
# THEN-<line> / ON-GOTO set its flag, returned to the prompt, and the branch was
# SILENTLY DROPPED -- no output, no error, nothing to notice. `run_stmt` is the
# control: `RUN` was the one transfer that worked, because it is an editor
# command handled before the crunch, not a statement.
XFER = [
    ("goto",       [f"10 PRINT{M};7;{M}", "GOTO10"]),
    ("if_then",    [f"10 PRINT{M};7;{M}", "IF 1 THEN 10"]),
    ("on_goto",    [f"10 PRINT{M};7;{M}", "ON 1 GOTO 10"]),
    ("run_stmt",   [f"10 PRINT{M};7;{M}", "RUN"]),
    ("goto_chain", [f"10 PRINT{M};1;{M}", f"20 PRINT{M};2;{M}", "GOTO10"]),
    ("gosub_rest", ["10 A=A+5:RETURN", f"A=0:GOSUB10:A=A+1:PRINT{M};A;{M}"]),
]

# --- group `break`: what a typed line REPORTS when it stops -----------------
# Routing direct mode through the run loop means the loop's break/error
# reporting now fires at the prompt for the first time, and it names a line
# there. Each of these pins one such report:
#   stop_direct / stop_run   -- "Break" vs "Break in 20"
#   stop_cont                -- a direct break leaves NO CONT resume point
#   err_in_line / err_after_ret -- direct mode is a property of the line being
#     run, not of how the line was reached: a typed GOSUB into a broken line 10
#     says "in 10", and the return into the rest of the typed line says nothing.
BREAK = [
    ("stop_direct",  [f"PRINT{M};1;{M}:STOP:PRINT{M};2;{M}"]),
    ("stop_cont",    [f"PRINT{M};1;{M}:STOP:PRINT{M};2;{M}", "CONT"]),
    ("end_direct",   [f"PRINT{M};1;{M}:END:PRINT{M};2;{M}"]),
    ("stop_run",     [f"10 PRINT{M};1;{M}", "20 STOP", f"30 PRINT{M};2;{M}",
                      "RUN", "CONT"]),
    ("err_in_line",  [f"10 PRINT{M};1;{M}:FNORD 3", "GOTO10"]),
    ("err_after_ret",["10 A=7:RETURN", "GOSUB10:FNORD 3"]),
]

# --- group `reset`: which commands empty the control stacks -----------------
# The other half of the cold-boot defect: the frame stacks had exactly ONE
# initialisation site (run_prog). These pin the full set the reference resets
# on -- and `gosub_survives` pins the one that must NOT reset, which is why the
# fix is a reset hook rather than a wipe at every prompt.
RESET = [
    ("new_clears",     ["FORI=1TO3", "NEW", f"NEXT:PRINT{M};1;{M}"]),
    ("clear_clears",   ["FORI=1TO3", "CLEAR", f"NEXT:PRINT{M};1;{M}"]),
    ("run_clears",     ["10 A=1", "RUN", f"NEXT:PRINT{M};1;{M}"]),
    ("gosub_survives", ["10 A=1", "GOSUB10", f"RETURN:PRINT{M};1;{M}"]),
]

GROUPS = {"direct": DIRECT, "cross": CROSS, "stored": STORED,
          "xfer": XFER, "break": BREAK, "reset": RESET}


COLS = 40
FKEY_ROW = re.compile(r"color\s+auto\s+goto\s+list\s+run", re.I)


def _rows(raw: str) -> list[str]:
    """Screen rows with the VG-8020's SCREEN-0 FUNCTION-KEY BAR removed.

    Load-bearing: the reference paints `color auto goto list run` on the bottom
    row and zerobas does not. Left in, it becomes the "last text on screen" for
    every case that prints no marker, so THREE different reference errors
    (`Syntax error`, `NEXT without FOR`, `RETURN without GOSUB`) all reduced to
    the same F-key string -- the comparison would have been blind to exactly the
    error-identity distinction the `cross` group exists to make."""
    rows = [raw[i:i + COLS] for i in range(0, len(raw), COLS)]
    return [r for r in rows if not FKEY_ROW.search(r)]


def _spans(raw: str) -> list[str]:
    return re.findall(r"#([^#]*)#", raw)


# Rows that are a BREAK/ERROR REPORT rather than program output. Captured with
# whatever follows on the row, because the whole point is the ` in <line>` SUFFIX:
# `break` vs `break in 20`, `syntax error` vs `syntax error in 10`.
REPORT_ROW = re.compile(r"(break|syntax error|can't continue).*", re.I)


def _strip_prompt(row: str) -> str:
    """Drop a LEADING prompt from a row.

    ⚠️ zerobas's prompt opens a fresh line (basic/repl.asm, 2026-07-27), but it is
    still followed ON THAT ROW by the echo of whatever the user typed -- that is
    what a prompt IS. "Always starts a line" is not "always alone on a line", and
    conflating the two turned the `bare` case's reference `fori=1to7:next` into
    zerobas's `ZBfori=1to7:next`. The reference's `Ok` is genuinely alone on its
    row, so only zerobas's needs stripping, but both are handled for symmetry."""
    for p in PROMPTS:
        if row.startswith(p):
            return row[len(p):]
    return row


def _reports(raw: str) -> list[str]:
    out = []
    for row in _rows(raw):
        m = REPORT_ROW.search(_strip_prompt(row))
        if m:
            out.append(re.sub(r"\s+", " ", m.group(0)).strip().lower())
    return out


def _norm(raw: str | None, with_report: bool = False) -> str:
    """One comparable observation per case, case-folded.

    `with_report` ADDS the break/error report rows to the observation instead of
    letting the marker spans stand alone. Load-bearing for the `break` group, and
    the reason it exists: that group's stated purpose is the ` in <line>` suffix
    (`Break` at the prompt vs `Break in 20` in a run), but every one of its cases
    also prints a marker -- so under the marker-first rule below the suffix fell
    into the unreachable fallback arm and NOTHING in this probe ever compared it.
    All six cases were green while the distinction they name went unmeasured; the
    slice's suffix gate could have been deleted outright without turning one red.

    A case either prints a marker span (the value) or it does not (it errored).
    When no span printed, fall back to the LAST MEANINGFUL SCREEN ROW so the two
    sides' ERROR TEXTS are compared -- an "out of memory" on one side and a "next
    without for" on the other must NOT both reduce to "no value". Case-folded
    because the two ROMs capitalise their messages differently (`NEXT without
    FOR` vs `next without for`), a cosmetic divergence this probe is not about.

    A ROW, not a character window off the flattened screen: the first version cut
    the last 40 chars, and since the two ROMs' prompts then differed in SHAPE
    ("Ok" on its own row vs a `zb>` PREFIX glued to the echo) the window started
    at a different point in the echo on each side. That reported `err_after_ret`
    as a divergence when both machines had in fact printed exactly "syntax error"
    with no line suffix. (Since 2026-07-27 zerobas's prompt is `ZB` and always
    opens a fresh line, so the two shapes now match -- but the row-based read is
    kept, because it is right for a reason that does not depend on that.)"""
    if raw is None:
        return "<no capture>"
    body = "".join(_rows(raw))
    hits = [re.sub(r"\s+", " ", s).strip() for s in _spans(body)]
    hits = [h for h in hits if h]
    if with_report:
        hits += ["!" + r for r in _reports(raw)]
    if hits:
        return "|".join(hits)
    meaningful = []
    for row in _rows(raw):
        row = _strip_prompt(row.strip()).strip()
        if row and row not in PROMPTS:             # drop either machine's prompt
            meaningful.append(row.lower())
    return "!" + (meaningful[-1] if meaningful else "<blank>")


# Cases whose OUTCOME IS DANGLING-POINTER GARBAGE, not semantics. A control frame
# made by a typed line survives that line on the reference (measured), but its
# resume pointer then addresses a buffer the NEXT typed line has overwritten. Both
# ROMs resume into whatever their own buffer now holds, so the exact aftermath is
# an artifact of buffer layout -- unreproducible clean-room and not worth
# reproducing. What IS semantic, and what these cases assert, is that the frame was
# still there: neither side may report "next without for" / "return without gosub".
# `for_then_next` is judged this way even though the two sides happen to agree
# exactly -- an agreement reached for the wrong reason is not evidence.
DANGLING = {"for_then_next", "gosub_survives"}
EMPTY_STACK = re.compile(r"without (for|gosub)", re.I)

# Cases judged on their REPORT TEXT as well as their output -- the whole `break`
# group, whose subject IS the ` in <line>` suffix. See _norm(with_report=).
REPORT = {label for label, _ in BREAK}


def run_group(machine: str, cases, batch: bool, **kw):
    specs = [("direct", lines) for _, lines in cases]
    raws = omsx_repl.run_cases(machine, specs, batch=batch,
                               reset=("NEW", "CLS"), **kw)
    return [_norm(r, label in REPORT) for (label, _), r in zip(cases, raws)], raws


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("differential", "characterize"),
                    default="differential",
                    help="characterize = reference only (no zerobas run)")
    ap.add_argument("--groups", default="direct,cross,stored,xfer,break,reset")
    ap.add_argument("--ref-machine", default=REF_MACHINE)
    ap.add_argument("--zb-machine", default=ZB_MACHINE)
    ap.add_argument("--batch", action="store_true",
                    help="UNSOUND for this matrix (see docstring); quick look only")
    ap.add_argument("--raw", action="store_true", help="dump the raw screens too")
    args = ap.parse_args()

    if args.batch:
        print("WARNING: --batch lets an earlier RUN initialise FSP/GSP for the "
              "whole boot,\n         which HIDES the cold-boot defect this probe "
              "exists to catch.\n")

    total = fails = 0
    for gname in args.groups.split(","):
        gname = gname.strip()
        cases = GROUPS[gname]
        print(f"=== group {gname} ({len(cases)} cases) ===")
        ref, ref_raw = run_group(args.ref_machine, cases, args.batch)
        if args.mode == "characterize":
            for (label, lines), r in zip(cases, ref):
                print(f"  {label:<16} ref={r}")
                if args.raw:
                    print(f"      lines={lines}")
            continue
        zb, zb_raw = run_group(args.zb_machine, cases, args.batch)
        for (label, lines), r, z in zip(cases, ref, zb):
            if label in DANGLING:       # judged on frame survival, not exact text
                ok = not (EMPTY_STACK.search(r) or EMPTY_STACK.search(z))
                tag = "ok*" if ok else "FAIL"
            else:
                ok = (r == z)
                tag = "ok " if ok else "FAIL"
            total += 1
            fails += 0 if ok else 1
            print(f"  [{tag}] {label:<16} ref={r!r:<28} zb={z!r}")
            if not ok:
                print(f"        lines={lines}")
    if args.mode == "differential":
        print(f"\n{total - fails}/{total} agree")
        return 0 if fails == 0 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
