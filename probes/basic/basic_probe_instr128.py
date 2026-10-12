#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-INSTR128 gate (`make instr128-acceptance`): INSTR over long strings, the
VG-8020 against both builds. Promoted from scratchpad/instr128_probe.py, whose
before/after outputs are the fix's evidence.

sh_instr_search (sub/strheap.asm) computed max_start = len_a - len_b + 1 in a
byte and tested it with `jp m`, so every value from 128 up read as negative:
"no room", 0. Each row prints INSTR's answer; the VG-8020 is the reference.
Clean room: typed BASIC and the screen.

  aN       haystack of N "6"s with an "F" at position 3        (N = 127 128 200 255)
  late     255 long, "F" at 250
  start    INSTR(130,S$,"F"), 200 long, "F" at 140
  start2   INSTR(200,S$,"F"), 255 long, "F" at 254
  none255  255 long, no "F" at all  (the loop must END: start wraps past 255)
  needle   a 128-long needle at 50 in a 255-long haystack
  needle2  a 200-long needle at 2 in a 255-long haystack
  short    "F" in a 3-long string                               (control)

Before the fix zerobas read 0 on every row whose len_a - len_b + 1 is 128 or
more (7 of 11, scratchpad/instr128_before.out); after, 11/11.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK", "C-BIOS_MSX1_EU_REPACK_DISK")


def hay(n, at):
    return f'S$=STRING$({n},"6"):MID$(S$,{at},1)="F"'


CASES = {
    "a127": [hay(127, 3), 'PRINT"<";INSTR(S$,"F");">"'],
    "a128": [hay(128, 3), 'PRINT"<";INSTR(S$,"F");">"'],
    "a200": [hay(200, 3), 'PRINT"<";INSTR(S$,"F");">"'],
    "a255": [hay(255, 3), 'PRINT"<";INSTR(S$,"F");">"'],
    "late": [hay(255, 250), 'PRINT"<";INSTR(S$,"F");">"'],
    "start": [hay(200, 140), 'PRINT"<";INSTR(130,S$,"F");">"'],
    "start2": [hay(255, 254), 'PRINT"<";INSTR(200,S$,"F");">"'],
    "none255": ['S$=STRING$(255,"6")', 'PRINT"<";INSTR(S$,"F");">"'],
    "needle": ['S$=STRING$(255,"6"):N$=STRING$(128,"F"):MID$(S$,50,128)=N$',
               'PRINT"<";INSTR(S$,N$);">"'],
    "needle2": ['S$=STRING$(255,"6"):N$=STRING$(200,"F"):MID$(S$,2,200)=N$',
                'PRINT"<";INSTR(S$,N$);">"'],
    "short": ['PRINT"<";INSTR("66F","F");">"'],
}


def read(m, body):
    lines = ["NEW", "10 CLEAR 2000"] + [f"{20 + 10 * i} {b}" for i, b in enumerate(body)] + ["RUN"]
    raw = omsx_repl.run_cases(m, [("direct", lines)], batch=False,
                              reset=("", "SCREEN 0"), run_gap=20.0)[0] or ""
    flat = raw.replace("\n", "")
    run = flat[flat.rfind("RUN") + 3:] if "RUN" in flat else flat
    hits = re.findall(r"<[^<>]*>", run)
    return re.sub(" +", " ", hits[-1]) if hits else None


def main():
    bad = 0
    for name, body in CASES.items():
        got = [read(m, body) for m in MACHINES]
        if got[0] is None:
            print(f"{name:8s} INSTRUMENT FAULT: no VG-8020 reading")
            return 2
        same = got[1] == got[0] and got[2] == got[0]
        bad += not same
        print(f"{name:8s} VG {got[0]:8s} nodisk {str(got[1]):8s} disk {str(got[2]):8s} "
              f"{'SAME' if same else 'DIVERGES'}", flush=True)
    print(f"\n{'PASS' if not bad else 'FAIL'}: {len(CASES) - bad}/{len(CASES)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
