#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""usrstr-acceptance (D-USRSTR): USR takes a string argument.

Found by the program ladder's L4_machine: `USR1("X")` was Type mismatch here
and works on the VG-8020. Measured (scratchpad/usrstr_measure.out): the
routine gets DAC+2 = the string's [len][ptr] descriptor -- for a variable its
OWN one, `USR(S$)=VARPTR(S$)` -- with VALTYP 3; temporaries are live during the
call (`PEEK(USR(MID$(S$,2)))` is 4); a routine that leaves VALTYP 3 in a
numeric place is 13. One program, scratchpad/usrstr_probe.bas; both zerobas
targets against the VG-8020. A STRING RESULT (`PRINT USR1("ABC")` prints ABC
there) is not covered: D-USRSTRRES.

Clean-room: typed keys and a tape in; the printer port out. The machine code
is the program's own six bytes.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

PROG = "scratchpad/usrstr_probe.bas"
ROWS = 9


def main():
    text = open(os.path.join(REPO, PROG)).read()
    ref = run_programs.run(run_programs.REF, "usrstr", text)
    rl = ref[1].replace("\r", "").splitlines()
    print(f"{run_programs.REF:30} {ref[0]}  {len(rl)} rows")
    bad = 0
    for m in run_programs.ZB:
        zb = run_programs.run(m, "usrstr", text)
        zl = zb[1].replace("\r", "").splitlines()
        diff = [(a, b) for a, b in zip(rl, zl) if a != b]
        ok = len(rl) == ROWS and zl == rl
        bad += not ok
        print(f"{m:30} {zb[0]}  {len(diff)} differ  {'SAME' if ok else 'DIVERGES'}")
        for a, b in diff:
            print(f"      ref {a!r}  zb {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: USR takes a string argument as on "
          f"the VG-8020")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
