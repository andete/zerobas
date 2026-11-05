#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TRAPSTMT (gate: trapstmt-acceptance): an event trap is dispatched at a
STATEMENT boundary, not at the end of the line.

The VG-8020 checks its traps between statements; zerobas checked once per line
(fixed 2026-11-05: basic/traps.asm es_trap, the TRAPPEND test in exec_stmt). The
timing-free witness: an INTERVAL event latched while `INTERVAL STOP` holds it is
dispatched one statement after `INTERVAL ON` (D-TRAPLATCHWHEN), so the handler's
copy H of a marker A says which statement boundary it ran at, and B -- set by
the rest of the line after RETURN -- says the GOSUB frame resumed mid-line.
Line-level dispatch reads the LAST marker instead.

Our own programs, one per boot; typed BASIC in, the screen out. TIME is
work-area RAM.

    python3 -u probes/basic/basic_probe_trapstmt.py [--gate]

--gate: every row must read the same on both machines (exit 1 if not; exit 2
if a VG-8020 row gave no output -- an unread reference agrees with nothing).
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

# INTERVAL=50 held 120 frames by INTERVAL STOP: the event latches, and no fresh
# one can arrive within the line under test, so only the latch is measured (an
# INTERVAL=1 fixture read where the next interrupt fell instead)
# INTERVAL ON first: a never-enabled interval latches nothing on the VG-8020 (an
# earlier cut of this fixture read H=0, "the handler never ran", for that reason)
HEAD = ["10 ON INTERVAL=50 GOSUB 100:INTERVAL ON:INTERVAL STOP:T=TIME:H=-1",
        "20 IF TIME-T<120 THEN 20"]
TAIL = ['40 PRINT "<";H;B;">":END',
        "100 H=A:INTERVAL OFF:RETURN"]
CASES = {
    # one statement after INTERVAL ON, then the rest of the line after RETURN
    "on": "30 A=0:INTERVAL ON:A=1:A=2:A=3:B=A",
    # the boundary inside a THEN clause
    "then": "30 A=0:IF A=0 THEN INTERVAL ON:A=1:A=2:B=A",
    # the boundary after a FOR statement; the loop then runs to its end
    "for": "30 A=0:INTERVAL ON:FOR I=1 TO 3:A=A+1:NEXT:B=A",
    # INTERVAL ON as the line's last statement: the next line's first
    "eol": "30 A=0:INTERVAL ON\n35 A=1:A=2:B=A",
}
MACHINES = ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]


def main():
    gate = "--gate" in sys.argv
    got = {}
    for m in [a for a in sys.argv[1:] if a != "--gate"] or MACHINES:
        for name, body in CASES.items():
            lines = HEAD + body.split("\n") + TAIL + ["RUN"]
            scr = omsx_repl.run_cases(m, [("direct", lines)], batch=False, boot=14.0,
                                      reset=("SCREEN 0:WIDTH 40", "NEW"), step=4.0,
                                      run_gap=6.0)[0]
            rows = [scr[i:i + 40].rstrip() for i in range(0, len(scr or ""), 40)]
            if "RUN" in rows:
                k = len(rows) - 1 - rows[::-1].index("RUN")
                rows = rows[k + 1:]
            out = " | ".join(r for r in rows if r.strip() and r.strip() != "Ok"
                             and r.strip() != "ZB" and "color" not in r) or "<NO OUTPUT>"
            got[(m, name)] = out
            print(f"{m:30s} {name:5s} [{out}]", flush=True)
    print(__import__("probe_refcache").summary())
    if not gate:
        return 0
    ref, zb = MACHINES
    if any(got.get((ref, n)) == "<NO OUTPUT>" for n in CASES):
        print("BROKEN FIXTURE: a VG-8020 row gave no output")
        return 2
    bad = [n for n in CASES if got.get((ref, n)) != got.get((zb, n))]
    print(f"trapstmt: {len(CASES) - len(bad)}/{len(CASES)} rows agree" + (f"; DIVERGE {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
