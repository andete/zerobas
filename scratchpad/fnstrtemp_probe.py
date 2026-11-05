#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FNALIAS build plan §7, the GC-root question (2026-11-05): does the reference
park a DEF FN call's string ACTUALS on its 10-deep temp-descriptor stack while
it evaluates them?

A nine-string-formal FN is called with every actual a temporary ("1"+""),
inside k pending `MID$("Z",1)+(` temporaries. Parked on the temp stack -> the
call fails (String formula too complex, 16) at a small k; not parked -> at k
near the no-FN limit (10 pending). Our own program, typed in; the screen read.

    python3 -u scratchpad/fnstrtemp_probe.py [MACHINE...]
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

ACT = ",".join(f'"{i}"+""' for i in range(1, 10))
DEF = "10 DEF FNA$(A$,B$,C$,D$,E$,F$,G$,H$,I$)=A$+I$"
MACHINES = ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]
RX = re.compile(r"<[^<>]*>")


def case(k, fn=True):
    inner = f"FNA$({ACT})" if fn else '"19"'
    expr = 'MID$("Z",1)+(' * k + inner + ")" * k
    return [DEF, "20 ON ERROR GOTO 90", f"30 X$={expr}",
            '40 PRINT "<";X$;">":END', '90 PRINT "<E";ERR;">":END']


def main():
    ks = [0, 1, 2, 5, 8, 9, 10]
    for m in sys.argv[1:] or MACHINES:
        for fn in (True, False):
            row = []
            for k in ks:
                raw = omsx_repl.run_cases(m, [("direct", ["NEW"] + case(k, fn) + ["RUN"])],
                                          batch=False, reset=("", "SCREEN 0:WIDTH 40"),
                                          run_gap=10.0)[0] or ""
                flat = raw.replace("\n", "")
                run = flat[flat.rfind("RUN") + 3:] if "RUN" in flat else flat
                hits = RX.findall(run)
                row.append(f"k{k}={hits[-1] if hits else 'NONE'}")
            print(f"{m[:12]:12s} {'FN ' if fn else 'ctl'} " + "  ".join(row), flush=True)
    print(__import__("probe_refcache").summary())


if __name__ == "__main__":
    main()
