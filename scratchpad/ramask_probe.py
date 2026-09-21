#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-LOC RAM ASK — is $EA40..$EA5F unclaimed by any LIVE writer on zerobas?

The map (tools/ram_map.py) shows CLR_SAVE at $EA3E (2 B) and the next
name at $EA9C (FN_PAREA); a delta between two names is NOT free space -- the
walker says so in its own banner -- so the band is ASKED of the machine: plant
a distinctive pattern at $EA40..$EA5F with POKE, run a workload that exercises
every neighbour a per-channel LOC table would sit beside (COLOR for CLR_SAVE, a
FOR nest and DEF FN for the control pool and FN_PAREA, a random PUT for the
GP_* cursors at $EA3A, string traffic for the pool, a KEY store for KEYARG),
then PEEK the band back. A byte that changed names a writer the map does not.
Run against the repack machine with the disk fixture (the PUT needs it).
"""
from __future__ import annotations
import os, sys, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)   # chokepoint ROOT rule: never a hardcoded path
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides, probe_tmp                       # noqa: E402

BASE, N = 0xEA40, 32
PROG = ["5 CLEAR 1000",                # the default pool is too small for line 40's 500 B of strings (Out of string space in 40, measured); CLEAR also exercises POOLSIZE/HIMEM
        "10 FOR I=0 TO 31:POKE &HEA40+I,(I*7+13) AND 255:NEXT",
        "20 COLOR 15,4,7:DEF FNA(X)=X*2+FNB(X):DEF FNB(X)=X+1",
        "30 FOR A=1 TO 3:FOR B=1 TO 3:FOR C=1 TO 3:Q=FNA(C):NEXT C,B,A",
        '40 A$=STRING$(100,"Z"):B$=A$+A$:C$=MID$(B$,50,100)',   # 200 B: A$+A$ at 200 each was String too long (255 max), measured
        '50 OPEN"RAMASK.DAT"AS #1 LEN=64:FIELD #1,64 AS F$:LSET F$="q":PUT #1,3:GET #1,3:X=LOF(1):CLOSE',
        '60 KEY 3,"ramask"',
        '70 PRINT"[R";"A":FOR I=0 TO 31:PRINT PEEK(&HEA40+I);:IF (I AND 7)=7 THEN PRINT',
        '75 NEXT:PRINT"R";"A]"',
        "RUN"]

def main() -> int:
    cfg = probe_sides.sides("zb")["zb"]
    dsk = probe_tmp.tmp("ramask.dsk"); shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
    cap = omsx_repl.run_cases(cfg["machine"], [("ramask", PROG)], batch=False, boot=cfg["boot"],
                              reset=cfg["reset"], diska=dsk, run_gap=60.0)[0] or ""
    i = cap.rfind("[RA"); j = cap.find("RA]", i + 3)   # the LAST: line 70's typed echo carries "[RA" too
    if i < 0 or j < 0:
        print("\U0001f534 no fence -- the program did not finish; read the glass:", cap[-160:]); return 2
    import re
    # \u26a0\ufe0f ROW-AWARE: the flat 40-column dump pads each row, so a number
    # that PRINT wrapped ("132" as "13" / "2") reads as two. Rebuild the rows,
    # strip each, join with nothing, then parse -- the first cut counted 34.
    rows = [cap[k:k + 40].rstrip() for k in range(0, len(cap), 40)]
    flat = "".join(rows)
    i2 = flat.rfind("[RA"); j2 = flat.find("RA]", i2 + 3)
    got = [int(x) for x in re.findall(r"\d+", flat[i2 + 3:j2])]
    want = [(k * 7 + 13) & 255 for k in range(N)]
    if len(got) != N:
        print(f"\U0001f534 {len(got)} values, not {N} -- the fenced text: {cap[i:j+3]!r}"); return 2
    changed = [k for k in range(N) if got[k] != want[k]]
    print(f"band ${BASE:04X}..${BASE+N-1:04X}: {N-len(changed)} of {N} bytes survived the workload")
    if changed:
        print("  CHANGED at offsets", changed, "-- a live writer the map does not name; the band is NOT free")
        return 1
    print("  no byte changed: no live writer touched the band under this workload (a reading, not a proof)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
