#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CHANHOOK -- STEP 10's first measurement: which hook cells do the CHANNEL
verbs enter on the reference, and does each count scale per BYTE, per SECTOR or
per OPERATION?

disk/docs/spec-diskcode-eviction.md's own open list says the hook cells for
PRINT# / INPUT# / CLOSE were never measured -- only $FE5D (OPEN's H.NULO). Step
10 moves OPEN and the channel I/O into disk.rom, and WHAT moves depends on where
the reference puts its crossings. Same instrument as D-HOOKCOUNT
(scratchpad/hookcount_probe.py: an entry counter on every published hook slot,
$FD9A..$FFE7, never reading a cell, never following a target, never stepping)
and the same controls: `quiet` for the baseline, `files` must move H_FILE $FE7B.

Cases pair a SMALL and a LARGE transfer, so a cell's delta separates:
  per BYTE       large - small ~ the byte difference (3960)
  per SECTOR     ~ the sector difference (4000 B = 8 sectors vs 1)
  per OPERATION  equal in both
PREDICTED, before the run: OPEN enters $FE5D once (as LOAD does); PRINT# and
INPUT$ enter a claimed cell per BYTE (MERGE's per-byte $FE8A is the precedent);
a per-sector cell ($FFCF, LOAD/SAVE's) moves ~+7 between small and large.
"""
import os, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import hookcount_probe as HC                                  # noqa: E402
import loadrun_probe as LR                                    # noqa: E402

SMALL = b"A" * 38 + b"\r\n"                     # 40 B, one sector
BIG = (b"B" * 98 + b"\r\n") * 40                # 4000 B, eight sectors


def main() -> int:
    tmpd = tempfile.mkdtemp(prefix="chanhook-")
    dsk = os.path.join(tmpd, "ch.dsk")
    LR.write_files(dsk, {"SMALL   TXT": SMALL, "BIG     TXT": BIG})
    cases = [
        ("quiet", ["REM"]),
        ("files", ["FILES"]),
        ("openclose", ['OPEN"W0.TXT"FOR OUTPUT AS#1:CLOSE']),
        ("writeS", ['OPEN"W1.TXT"FOR OUTPUT AS#1:PRINT#1,STRING$(38,65):CLOSE']),
        ("writeL", ['OPEN"W2.TXT"FOR OUTPUT AS#1:FOR I=1TO40:PRINT#1,STRING$(98,66):NEXT:CLOSE']),
        ("readS", ['OPEN"SMALL.TXT"FOR INPUT AS#1:A$=INPUT$(40,#1):CLOSE']),
        ("readL", ['OPEN"BIG.TXT"FOR INPUT AS#1:FOR I=1TO40:A$=INPUT$(100,#1):NEXT:CLOSE']),
        ("eoflof", ['OPEN"SMALL.TXT"FOR INPUT AS#1:A=EOF(1):B=LOF(1):CLOSE']),
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
    for tag in ("writeL", "readL"):
        cap = HC.CAPTURE.get(tag) or ""
        print(f"\n[{tag} screen tail] {cap[-120:]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
