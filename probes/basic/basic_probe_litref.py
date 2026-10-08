#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""litref-acceptance (D-LITREF) -- a string LITERAL assigned in a program points
at the program text, as on the references: it charges the string space nothing.
D-READREF did it for READ; this is LET.

  aryl     DIM A$(9): A$(I)="<40 x A>" for 1..9 -> FRE("") stays 200 on the VG-8020
  scall    A$="<40 x A>" -> FRE("") (scalar)
  copyvar  READ B$ : A$=B$ -- B$ points into the text; does A$=B$ copy?
           SEPARATES "the bytes are in the program text" from "the RHS is a
           literal token"
  direct   A$="ABC" typed in DIRECT mode -- the literal lives in the line buffer,
           which is reused, so it must be copied (FRE 197)
  mid      A$="ABC" : MID$(A$,1,1)="Z" : RUN again -- the program text untouched
  concat   A$="AB"+"C" -- a computed result, copied as before

Fresh boot per row, the diskless VG-8020 against ours. Exit 0 all agree; 1 a
divergence; 2 a reference gave no reading.

    python3 -u probes/basic/basic_probe_litref.py [case ...]
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

REF, OURS = "Philips_VG_8020", os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
R40 = "A" * 40
CASES = {
    "aryl": [f'10 DIM A$(9):FOR I=1 TO 9:A$(I)="{R40}":NEXT', '20 PRINT"[OK";FRE("");"]":END', "RUN"],
    "scall": [f'10 A$="{R40}"', '20 PRINT"[OK";FRE("");LEN(A$);"]":END', "RUN"],
    "copyvar": ["10 READ B$:A$=B$", '20 PRINT"[OK";FRE("");A$;"]":END', "30 DATA ABCDE", "RUN"],
    "direct": ['A$="ABC":PRINT"[OK";FRE("");A$;"]"'],
    "mid": ['10 A$="ABC":MID$(A$,1,1)="Z"', '20 PRINT"[OK";A$;"]":END', "RUN", "LIST 10"],
    "concat": ['10 A$="AB"+"C"', '20 PRINT"[OK";FRE("");A$;"]":END', "RUN"],
}


def reading(machine, lines):
    raw = omsx_repl.run_cases(machine, [("d", ["NEW"] + lines)], batch=False, run_gap=12.0,
                              reset=("CLS",))[0] or ""
    if "load error" in raw.lower():
        return "load error"
    scr = re.sub(r"\s+", " ", raw)
    m = re.findall(r"\[OK[^\]]*\]|[A-Z][a-z][a-z ]* in \d+|10 A\$=\"[A-Z]+\"", scr)
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
    print(f"\n{'PASS' if not bad else 'FAIL'}: program literals point at the program text ({bad} divergence(s))")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
