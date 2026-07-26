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

GROUPS = {"direct": DIRECT, "cross": CROSS, "stored": STORED}


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


def _norm(raw: str | None) -> str:
    """One comparable observation per case, case-folded.

    A case either prints a marker span (the value) or it does not (it errored).
    When no span printed, fall back to the trailing screen text so the two sides'
    ERROR TEXTS are compared -- an "out of memory" on one side and a "next without
    for" on the other must NOT both reduce to "no value". Case-folded because the
    two ROMs capitalise their messages differently (`NEXT without FOR` vs
    `next without for`), a cosmetic divergence this probe is not about."""
    if raw is None:
        return "<no capture>"
    body = "".join(_rows(raw))
    hits = [re.sub(r"\s+", " ", s).strip() for s in _spans(body)]
    hits = [h for h in hits if h]
    if hits:
        return "|".join(hits)
    flat = re.sub(r"\s+", " ", body).strip()
    # no marker: report the last non-prompt text on screen (the error message)
    tail = [t.strip() for t in re.split(r"\bOk\b|zb>", flat) if t.strip()]
    return "!" + (tail[-1][-40:] if tail else flat[-40:]).lower()


def run_group(machine: str, cases, batch: bool, **kw):
    specs = [("direct", lines) for _, lines in cases]
    raws = omsx_repl.run_cases(machine, specs, batch=batch,
                               reset=("NEW", "CLS"), **kw)
    return [_norm(r) for r in raws], raws


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("differential", "characterize"),
                    default="differential",
                    help="characterize = reference only (no zerobas run)")
    ap.add_argument("--groups", default="direct,cross,stored")
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
            ok = (r == z)
            total += 1
            fails += 0 if ok else 1
            print(f"  [{'ok ' if ok else 'FAIL'}] {label:<16} ref={r!r:<28} zb={z!r}")
            if not ok:
                print(f"        lines={lines}")
    if args.mode == "differential":
        print(f"\n{total - fails}/{total} agree")
        return 0 if fails == 0 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
