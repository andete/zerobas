#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-MAXFTAIL — `MAXFILES=1 ZZ` wipes the variables and the error cannot be trapped.

Found by D-TAILJUNK, the sloppy-accept sweep: of 24 complete statements given a
trailing `ZZ`, every one agreed across all three machines except `MAXFILES`, where
zerobas gave NO reading at all. A blank is an absence, so the screen was read
rather than the fence -- and it says `Syntax error in 20`, UNTRAPPED, escaping an
`ON ERROR GOTO` that both references honour.

\U0001f3af THE MECHANISM IS ESTABLISHED, NOT GUESSED. `MAXFILES` performs a `CLEAR`
(D-FCH §3.2: unconditionally, even when the value does not change), and `CLEAR`
disarms the error trap. So on zerobas the order is: execute MAXFILES -> CLEAR
wipes variables AND the handler -> only THEN does the tail raise Syntax error,
with nothing left to catch it.

`t.survive` proves the references do it the other way round. `A` is set to 42
before the statement; if the reference had executed MAXFILES, its CLEAR would have
zeroed A.

    side      A , ERR
    vg8020    42 , 2      the statement was REJECTED before executing
    cf3300    42 , 2      same
    zb         0 , --     executed, CLEAR ran, error untrappable

\U0001f534 SO THERE ARE TWO DEFECTS, AND THE SECOND IS THE WORSE ONE: a typo after
`MAXFILES=` silently DESTROYS the user's variables on zerobas and does not on
either reference. The untrappable error is the visible half.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": ("Philips_VG_8020", 8.0, ("NEW",)),
    "cf3300": ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW")),
    "zb": (ZB, 10.0, ("NEW",)),
}
# A survives => the CLEAR inside MAXFILES never ran => rejected before executing.
PROG = ['10 ON ERROR GOTO 900', '20 A=42', '30 MAXFILES=1 ZZ',
        '900 PRINT"ZQ";A;",";ERR;"QZ":END']
# ...and on the side that does NOT trap, ask in DIRECT mode whether A survived.
# 🔴 A SEPARATE FENCE, AND THE FIRST CUT DID NOT HAVE ONE. Both lines used
# ZQ...QZ, so the LAST-match rule read the DIRECT line every time and the ERR
# column printed the tail's literal 0 on all three machines -- a column that
# looked like a reading and was a constant [[readout-blind-to-its-own-subject]].
TAIL = ['PRINT"ZR";A;"RZ"']


def main() -> int:
    print("  row t.survive -- A before the statement is 42; ERR is the trapped code\n")
    out = {}
    for side, (mach, boot, reset) in SIDES.items():
        raw = "".join(omsx_repl.run_cases(
            mach, [("direct", list(reset) + PROG + ["RUN"] + TAIL)],
            batch=False, reset=(), boot=boot, step=4.0, run_gap=15.0,
            cap_gap=4.0, timeout=420.0)[0] or "")
        trapped = [g for g in re.findall(r"ZQ\s*([0-9]+)\s*,\s*([0-9]+)\s*QZ", raw)
                   if not any(c in "".join(g) for c in '"$;')]
        after = [g for g in re.findall(r"ZR\s*([0-9]+)\s*RZ", raw)
                 if not any(c in g for c in '"$;')]
        out[side] = (trapped[-1] if trapped else None, after[-1] if after else None)
        t, af = out[side]
        print(f"  {side:8s} handler: {'A=%s ERR=%s' % t if t else 'NEVER RAN':16s}"
              f"   A afterwards: {af or '<none>'}")

    print("\n  42 -> rejected BEFORE executing: no CLEAR, variables intact, error"
          "\n        trappable.   0 -> MAXFILES ran, its CLEAR wiped the variables,"
          "\n        and the trap it also disarmed could not catch what came next.")
    refs = [out.get("vg8020", (None, None))[0], out.get("cf3300", (None, None))[0]]
    if any(r is None or r[0] != "42" or r[1] != "2" for r in refs):
        print(f"\n\U0001f534 A REFERENCE DID NOT TRAP WITH A=42,ERR=2 ({refs}) -- "
              f"the premise of this probe is wrong and nothing here is a reading.")
        return 2
    zb = out.get("zb", (None, None))
    if zb[0] is None and zb[1] == "0":
        print("\n\U0001f534 CONFIRMED: zerobas's handler NEVER RAN (the error was "
              "untrappable) and A came back 0 -- the variables were wiped, where "
              "neither reference wipes them.")
        return 1
    print("\n\U0001f7e2 zerobas now matches the references.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
