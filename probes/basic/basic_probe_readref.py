#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""readref-acceptance (D-READREF) -- a string READ from DATA POINTS AT THE
PROGRAM TEXT, as on the references: it charges the string space nothing, and a
write into it (MID$ / LSET) writes into the program.

Joost ruled the design 2026-09-27 ("YES -- POINT AT PROGRAM TEXT"); re-tiered
TIER 1 on 2026-10-07 when Vleermuis -- an unmodified 1989 type-in -- stopped
with `Out of string space` at its fifth READ of a 40-character DATA row on
ours, where the VG-8020 reads all 120.

  ary    9 x 40-char DATA rows READ into A$(1..9), default string space
  scal   the same 9 rows READ into ONE scalar, then FRE("")
  mid    READ A$ : MID$(A$,1,1)="Z" : RESTORE : READ B$ -- does the second READ
         see the Z (the write went into the program text)?
  list   the same write, witnessed by LIST of the DATA line
         🎯 predicted the write to land in the program -- MISSED: on the
         VG-8020 the re-READ is ABC and LIST shows `30 DATA ABC`. MID$ copies a
         string out of the program text before writing into it.
  lset   LSET A$="Z" on a READ string (a non-FIELD LSET writes in place)
  rset   the same with RSET
  midoom the MID$ write's copy-out with the string space already full
  edit   RUN (READ A$), then a program LINE is typed, then PRINT A$: an edit
         clears the variables on MSX -- the hazard a pointer into the program
         text needs to be absent

Fresh boot per row, the diskless VG-8020 against ours. `load error` on the
screen is its own reading. Exit 0 all agree; 1 a divergence; 2 a reference gave
no reading.

    python3 -u probes/basic/basic_probe_readref.py [case ...]
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

REF, OURS = "Philips_VG_8020", os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
ROW = "A" * 40
DATA9 = [f"{100 + i} DATA {ROW}" for i in range(9)]
CASES = {
    "ary": ["10 DIM A$(9):FOR I=1 TO 9:READ A$(I):NEXT", '20 PRINT"[OK";FRE("");LEN(A$(9));"]":END']
           + DATA9 + ["RUN"],
    "scal": ["10 FOR I=1 TO 9:READ B$:NEXT", '20 PRINT"[OK";FRE("");LEN(B$);"]":END'] + DATA9 + ["RUN"],
    "mid": ['10 READ A$:MID$(A$,1,1)="Z":RESTORE:READ B$', '20 PRINT"[OK";B$;"]":END',
            "30 DATA ABC", "RUN"],
    "list": ['10 READ A$:MID$(A$,1,1)="Z":END', "30 DATA ABC", "RUN", "LIST 30"],
    "lset": ['10 READ A$:LSET A$="Z":RESTORE:READ B$', '20 PRINT"[OK";B$;"/";A$;"]":END',
             "30 DATA ABC", "RUN"],
    "rset": ['10 READ A$:RSET A$="Z":RESTORE:READ B$', '20 PRINT"[OK";B$;"/";A$;"]":END',
             "30 DATA ABC", "RUN"],
    # one statement per line: on one line both machines said `in 10` for
    # DIFFERENT statements (ours ran out at the STRING$, the reference at the MID$)
    "midoom": ['10 CLEAR 10:READ A$', '15 B$=STRING$(10,"X")', '16 MID$(A$,1,1)="Z"',
               '20 PRINT"[OK";A$;"]":END',
               "30 DATA ABCDE", "RUN"],
    "edit": ['10 READ A$:PRINT"[R";A$;"]":END', "30 DATA ABC", "RUN", "40 REM",
             'PRINT"[OK";A$;"]"'],
}


def reading(machine, lines):
    raw = omsx_repl.run_cases(machine, [("d", ["NEW"] + lines)], batch=False, run_gap=12.0,
                              reset=("CLS",))[0] or ""
    if "load error" in raw.lower():
        return "load error"
    scr = re.sub(r"\s+", " ", raw)
    m = re.findall(r"\[OK[^\]]*\]|[A-Z][a-z][a-z ]* in \d+|30 DATA [A-Z]+", scr)
    return " | ".join(" ".join(x.split()) for x in m[-2:]) if m else None


def main():
    bad = 0
    only = sys.argv[1:]
    for case, lines in CASES.items():
        if only and case not in only:
            continue
        r, z = reading(REF, lines), reading(OURS, lines)
        if r is None:
            print(f"INSTRUMENT FAULT: {REF} gave no reading for {case}")
            return 2
        bad += r != z
        print(f"{'ok  ' if r == z else 'DIFF'} {case:5} {r!r:30} ours {z!r}", flush=True)
    print(f"\n{'PASS' if not bad else 'FAIL'}: READ strings point at the program text ({bad} divergence(s))")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
