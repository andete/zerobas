#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ROMSIZE step 1, S10.D's first measurement: which hook cells do RANDOM files'
verbs enter on the reference (CF-3300), and does each count scale per RECORD or
per OPERATION?

The eviction plan's step 10 moved OPEN / PRINT# / CLOSE into disk.rom (S10.B);
S10.D (GET / PUT) needs the reference's crossing points first -- D-CHANHOOK
measured OPEN/CLOSE, the byte cells and EOF/LOF only. Same instrument
(scratchpad/hookcount_probe.py: an entry counter on every published hook slot,
$FD9A..$FFE7, never reading a cell, never following a target, never stepping),
same controls (`quiet` baseline, `files` must move H_FILE $FE7B).
Cases pair 1 record with 40 (16-byte records), so a cell's delta separates
per RECORD (~ +39) from per OPERATION (equal).
PREDICTED, before the run: OPEN ... AS #1 LEN=16 enters $FE5D once as every OPEN
does; GET and PUT each enter ONE claimed cell per record (not per byte); FIELD
enters no claimed cell (it is pure BASIC bookkeeping).
"""
import os, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import hookcount_probe as HC                                  # noqa: E402
import loadrun_probe as LR                                    # noqa: E402

RAND = bytes((i % 26) + 65 for i in range(640))  # 40 records of 16 B


def main() -> int:
    tmpd = tempfile.mkdtemp(prefix="chanhook-")
    dsk = os.path.join(tmpd, "ch.dsk")
    LR.write_files(dsk, {"RAND    DAT": RAND})
    cases = [
        ("quiet", ["REM"]),
        ("files", ["FILES"]),
        ("openR", ['OPEN"RAND.DAT"AS#1 LEN=16:CLOSE']),
        ("field", ['OPEN"RAND.DAT"AS#1 LEN=16:FIELD#1,16 AS A$:CLOSE']),
        ("get1", ['OPEN"RAND.DAT"AS#1 LEN=16:FIELD#1,16 AS A$:GET#1,1:CLOSE']),
        ("get40", ['OPEN"RAND.DAT"AS#1 LEN=16:FIELD#1,16 AS A$:FOR I=1TO40:GET#1,I:NEXT:CLOSE']),
        ("put1", ['OPEN"P1.DAT"AS#1 LEN=16:FIELD#1,16 AS A$:LSET A$="X":PUT#1,1:CLOSE']),
        ("put40", ['OPEN"P40.DAT"AS#1 LEN=16:FIELD#1,16 AS A$:LSET A$="Y":FOR I=1TO40:PUT#1,I:NEXT:CLOSE']),
    ]
    got = {}
    for tag, lines in cases:
        got[tag] = HC.run(tag, lines, dsk)
        print(f"  {tag:9} {sum(got[tag].values()):7d} hit(s) over "
              f"{sum(1 for v in got[tag].values() if v):3d} cell(s)")
    if not got["quiet"]:
        sys.exit("REFUSING: the quiet baseline read NOTHING -- no breakpoint fired")
    base = got["quiet"]
    if got["files"].get(HC.H_FILE, 0) - base.get(HC.H_FILE, 0) < 1:
        sys.exit("REFUSING: FILES did not move H_FILE $FE7B -- the counter does "
                 "not discriminate, so every delta below would be noise")
    print("\n=== DELTA vs quiet (cells any case moved) ===")
    tags = [t for t, _ in cases if t != "quiet"]
    print("cell   " + " ".join(f"{t:>9}" for t in tags))
    for cell in HC.CELLS:
        vals = [got[t].get(cell, 0) - base.get(cell, 0) for t in tags]
        if any(vals):
            print(f"${cell:04X}  " + " ".join(f"{v:+9d}" for v in vals))
    for tag in ("get40", "put40"):
        cap = HC.CAPTURE.get(tag) or ""
        print(f"\n[{tag} screen tail] {cap[-120:]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
