#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-TXTCEIL: the row that pins the REAL defect -- a store PAST HIMEM.

D-HIMEMRES split the `TXTMAX` item in two. `crf-oomsay` / `crf-oomlst` compare
`FRE(0)` against machines that reserve **267 B per file channel** where zerobas
reserves **50** (`FCH_CTXSZ equ FCH_STATESZ ; block = state ONLY (no buffer)`),
so those rows can never agree and are the wrong instrument for the defect.

🎯 THE DEFECT IS A SELF-CONSISTENCY VIOLATION AND NEEDS NO ORACLE AT ALL. The
line store compares against the CONSTANT `TXTMAX` (`$DB00`), so `CLEAR n,himem`
never reaches it and the program is free to grow **past HIMEM, into the string
and variable area**. The invariant that must hold on any machine, whatever it
reserves per channel:

        PRGEND  <=  HIMEM - POOLSIZE          (the string pool's floor)

⚠️ THAT IS WHY THIS ROW EXISTS RATHER THAN A SHARPER ONE. The obvious observable
-- assign a long string, overrun into it, print it back mangled -- CANNOT be
driven from the REPL: editing a program line clears variables, so the string is
gone before the lines that would corrupt it are typed. The address invariant is
what survives the apparatus.

⚠️ AND THE GAP IS SMALL ON PURPOSE. With the shipped `TXTMAX` at `$DB00` and
HIMEM around `$83E9`, reaching the constant would need ~22 KB of typed program.
`CLEAR 300,TXTTAB+400` puts the pool floor 100 bytes above the text base, so six
`REM` lines cross it.

🔴 ZEROBAS ONLY, AND ROUND 1 OF THIS PROBE RAN ALL THREE AND PRINTED THE
REFERENCES' NUMBERS AS IF THEY MEANT SOMETHING. `PRGEND` ($E026) and `POOLSIZE`
($E232) are ZEROBAS's OWN sysvars; on a VG-8020 those addresses are unrelated
bytes, and the row duly reported `PRGEND 0 / POOLSIZE 0 / headroom 62336 🟢` for
the VG-8020 and `STORED 74119 B PAST THE FLOOR` for the CF-3300. Neither is a
reading. A self-consistency invariant is a claim about ONE machine's map, and
running it on machines with a different map manufactures both a pass and a
failure [[a-case-that-agrees-can-agree-for-the-wrong-reason]].

🔴 AND ROUND 1 ALSO REPORTED ZEROBAS GREEN ON A FIXTURE THAT NEVER TOOK.
`CLEAR 300,TXTTAB+400` leaves HIMEM at its default `$F380` -- the CLEAR is
refused, silently as far as this probe could see -- so the "🟢 inside the pool
floor" verdict was about a machine that had never been set up. `c.clear` below is
the control that makes the rest a reading: HIMEM must EQUAL `TXTTAB+GAP` or the
run is refused.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {"zb": (ZB, 8.0, ("NEW",))}      # see the docstring: zerobas-only
POOLSZ, GAP = 300, 1000                  # 400 is refused; 1000 is measured to take
NLINES = 25                              # ~36 stored bytes each -> ~900 B
PRGEND, HIMEM, POOL = 0xE026, 0xFC4A, 0xE232
BODY = "REM " + "A" * 30                 # ~36 stored bytes per line
LINES = [f"{10 * (k + 1)} {BODY}" for k in range(NLINES)]


def peek16(addr):
    return f"PEEK(&H{addr:04X})+256*PEEK(&H{addr + 1:04X})"


def run(side):
    machine, boot, reset = SIDES[side]
    prog = ([f"A=PEEK(&HF676)+256*PEEK(&HF677)", f"CLEAR {POOLSZ},A+{GAP}"]
            + LINES
            + [f'PRINT"[E";{peek16(PRGEND)};"]"',
               f'PRINT"[H";{peek16(HIMEM)};"]"',
               f'PRINT"[P";{peek16(POOL)};"]"',
               # c.clear: TXTTAB is re-read AFTER the lines, so the control
               # compares HIMEM against the base the store actually used.
               f'PRINT"[T";PEEK(&HF676)+256*PEEK(&HF677);"]"'])
    raw = "".join(omsx_repl.run_cases(
        machine, [("direct", list(reset) + prog)], batch=False, reset=(),
        boot=boot, step=6.0, cap_gap=12.0, timeout=400.0)[0] or "")
    rows = [raw[i * 40:(i + 1) * 40].strip() for i in range(24)]
    out = {}
    for key in "EHPT":
        # only rows that BEGIN with the fence: the echo of the PRINT line
        # contains it too, and reading that reports the typed text as a value.
        m = [mm for r in rows if r.startswith(f"[{key}")
             for mm in re.findall(rf"^\[{key}\s*(-?\d+)\s*\]", r)]
        out[key] = int(m[-1]) if m else None
    out["screen"] = rows
    return out


def main() -> int:
    print(f"\n{'side':8s} {'TXTTAB':>7s} {'PRGEND':>8s} {'HIMEM':>8s} "
          f"{'POOL':>6s} {'floor=H-P':>10s} {'headroom':>9s}   verdict")
    bad = 0
    for side in ("zb",):
        r = run(side)
        if any(r[k] is None for k in "EHPT"):
            print(f"{side:8s}  <NO READING>  — the run did not reach the "
                  f"sentinels; that is the probe, not an answer.")
            bad += 1
            continue
        # \U0001f534 c.clear FIRST: a green invariant on a machine whose CLEAR never
        # took is what round 1 printed.
        if r["H"] != r["T"] + GAP or r["P"] != POOLSZ:
            print(f"{side:8s} \U0001f534 THE CLEAR DID NOT TAKE: HIMEM={r['H']} but "
                  f"TXTTAB+GAP={r['T'] + GAP}, POOLSIZE={r['P']} want {POOLSZ}. "
                  f"Every other number here would be about an un-set-up machine. "
                  f"Refused.")
            bad += 1
            continue
        floor = r["H"] - r["P"]
        head = floor - r["E"]
        verdict = ("\U0001f7e2 inside the pool floor" if head >= 0
                   else f"\U0001f534 STORED {-head} B PAST THE FLOOR")
        print(f"{side:8s} {r['T']:>7d} {r['E']:>8d} {r['H']:>8d} {r['P']:>6d} "
              f"{floor:>10d} {head:>9d}   {verdict}")
    if bad:
        print("\n\U0001f534 INSTRUMENT FAULT: a side produced no reading. Refused.")
        return 2
    print(f"\n\U0001f3af `PRGEND <= HIMEM - POOLSIZE` is a SELF-CONSISTENCY invariant "
          f"about ZEROBAS's\n   own map: it needs no oracle, and it holds whatever "
          f"a machine reserves per\n   file channel — which is exactly what "
          f"`crf-oom*` cannot say (D-HIMEMRES:\n   267 B/channel there vs 50 here). "
          f"{NLINES} lines x ~36 B are typed to cross a\n   floor {GAP - POOLSZ} B "
          f"above the text base.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
