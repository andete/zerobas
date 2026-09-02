#!/usr/bin/env python3
r"""D-DUPOPEN — WHERE does the reference check "same file on two channels"?

Uncovered 2026-09-02 by D-OPEN2FIX, which removed the spurious `Syntax error`
that was killing every two-channel OPEN before this could be reached. The one
remaining DIFF of 18:

    MAXFILES=2 : OPEN"TS.DAT"AS #1 : OPEN"TS.DAT"AS #2
        cf3300 -> File already open        zb -> OK

The FACE is known (ERR 54, and the message already ships). What is unmeasured is
what the check is KEYED ON, and the candidates make different predictions:

  (a) the RAW NAME STRING as typed        -> `ts.dat` after `TS.DAT` is ALLOWED
  (b) the PARSED 8.3 name (upcased)       -> `ts.dat` is REFUSED
  (c) the DIRECTORY ENTRY it resolves to  -> a file that does not exist yet
                                             cannot collide, so opening a NEW
                                             name twice is ALLOWED

🔴 PREDICTIONS:
  P1  `s.case` is REFUSED -- (b). MSX 8.3 names are upcased at parse, so the
      channel table should hold `TS      DAT` either way.
  P2  `s.newtwice` is REFUSED -- (b)/(c) separator. If the reference refuses a
      name that does not exist on disk, the check cannot be reading the
      directory; it is comparing against the other channels' stored names.
  P3  `s.modes` is REFUSED -- the check is about the FILE, not the access mode.
  P4  zerobas reads OK on every one of them (no check exists at all).

⚠️ FIXTURE: `MAXFILES=n` DISARMS `ON ERROR` on both machines (D-PUT3's list), so
nothing here uses a handler -- these are direct-mode lines and the untrapped
message IS the reading.
"""
from __future__ import annotations
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import basic_probe_fldwidth as F                                  # noqa: E402

OK = 'PRINT"[";"OK";"]"'
M  = 'MAXFILES=2'
R1 = 'OPEN"TS.DAT"AS #1 LEN=128'

CASES = [
    # --- 🟢 CONTROLS ---------------------------------------------------------
    ("c.diff",     "dsk", [M, R1, 'OPEN"TS2.DAT"AS #2 LEN=128', OK]),
    ("c.closed",   "dsk", [M, R1, 'CLOSE', 'OPEN"TS.DAT"AS #2 LEN=128', OK]),
    # --- the subject, as filed ----------------------------------------------
    ("s.same",     "dsk", [M, R1, 'OPEN"TS.DAT"AS #2 LEN=128', OK]),
    # --- (a) raw string vs (b) parsed 8.3 name ------------------------------
    ("s.case",     "dsk", [M, R1, 'OPEN"ts.dat"AS #2 LEN=128', OK]),
    ("s.space",    "dsk", [M, R1, 'OPEN"TS.DAT "AS #2 LEN=128', OK]),
    # --- (b) channel table vs (c) directory entry ---------------------------
    # a name that does NOT exist on the disk: (c) cannot collide, (b) can.
    ("s.newtwice", "dsk", [M, 'OPEN"NEW1.DAT"AS #1 LEN=128',
                              'OPEN"NEW1.DAT"AS #2 LEN=128', OK]),
    # --- does the ACCESS MODE matter? ---------------------------------------
    ("s.modes",    "dsk", [M, R1, 'OPEN"TS.DAT"FOR INPUT AS #2', OK]),
    ("s.seqsame",  "dsk", [M, 'OPEN"A.TXT"FOR OUTPUT AS #1',
                              'OPEN"A.TXT"FOR OUTPUT AS #2', OK]),
    # --- 🎯 DOES THE REFUSAL LEAVE #2 CLAIMED? Direct mode continues after an
    # --- error, so the next line asks whether channel 2 is usable afterwards.
    # --- If the reference checks BEFORE claiming, this second open succeeds.
    ("s.reclaim",  "dsk", [M, R1, 'OPEN"TS.DAT"AS #2 LEN=128',
                                  'OPEN"TS2.DAT"AS #2 LEN=128', OK]),
    # --- 🎯 WHICH IMPLEMENTATION ROUTE? Two candidates reproduce every row
    # --- above, and they differ on ONE fact: does MSX upcase a filename before
    # --- it reaches the directory?
    #   * compare the stored NAME per channel (case-sensitive) -- needs new RAM,
    #     there is no FCH_NAMES array, only modes and reclens.
    #   * compare (FWR_DIRSEC, FWR_DIROFF) -- the dir-entry LOCATION, which is
    #     ALREADY in the 50-byte per-channel context block. Zero new RAM.
    # If MSX upcases, `ts.dat` and `TS.DAT` are ONE directory entry, so the
    # dirent route would REFUSE s.case -- and the reference ALLOWS it, which
    # would kill that route. If it does not upcase, they are two entries and
    # both routes agree. FILES says which.
    # (FILES was tried first and its listing overran the readout's 48-char
    # carry cap -- a single-VALUE row answers the same question.)
    # Create lower-case, then look it up UPPER-case. `File not found` means the
    # name is stored and matched case-SENSITIVELY, so `ts.dat` and `TS.DAT` are
    # two distinct directory entries and the dirent-comparison route survives.
    # `OK` means they are ONE entry -- and then the dirent route would refuse
    # s.case, which the reference allows, killing it.
    ("q.upcase",   "dsk", [M, 'OPEN"zz2.dat"AS #1 LEN=128', 'CLOSE',
                              'OPEN"ZZ2.DAT"FOR INPUT AS #1', OK]),
    # the same lookup in the case it was created with -- the control that says
    # the file was created at all.
    ("q.samecase", "dsk", [M, 'OPEN"zz3.dat"AS #1 LEN=128', 'CLOSE',
                              'OPEN"zz3.dat"FOR INPUT AS #1', OK]),
]

F.CASES = CASES
sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
res = {s: F.run_side(s, []) for s in sides}
w = max(len(l) for l, _, _ in CASES)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>24}" for s in sides) + "   verdict")
diff = []
for label, _, _ in CASES:
    vals = [str(res[s].get(label)) for s in sides]
    same = len(set(vals)) == 1
    if not same: diff.append(label)
    print(f"{label:<{w}}  " + "  ".join(f"{v:>24}" for v in vals)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF: {len(diff)}/{len(CASES)}  " + " ".join(diff))
