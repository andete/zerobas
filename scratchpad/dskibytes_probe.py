#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DSKIBYTES — the sector really is at $EB00, confirmed byte for byte.

D-DSKIWHERE checksummed every page of $C000..$FFFF around two `DSKI$` reads and
found exactly ONE page tracking the sector number: page $2B, i.e. **$EB00**. That
is a differential argument — "something here changed when the sector changed" —
and it is one step short of the claim it invites.

🎯 THIS ROW READS THE BYTES AND COMPARES THEM TO THE IMAGE FILE ON DISK. The
fixture is zerobas's own `disk/test720.dsk`, inspectable directly (it is not a
reference ROM), and its first eight bytes are known:

    sector  0   EB FE 90 5A 45 52 4F 42     (the FAT12 jump, then the OEM name)
    sector  1   F9 FF FF 03 F0 FF FF FF     (the FAT's media byte and chain)

The rows print and compare DECIMAL, because `HEX$` is string work and string work
is what broke the first cut (see `program`).

If `$EB00..$EB07` holds those bytes after `DSKI$(0,0)` and the OTHER set after
`DSKI$(0,1)`, the landing address is established rather than inferred, and the
two rows cannot both be right by coincidence.

⚠️ THE 512-vs-256 QUESTION IS OPEN AND `w.half2` IS WHY. Only ONE page moved in
the scan, but a sector is 512 bytes and would span two. That is NOT evidence of a
256-byte transfer: sectors 0 and 1 are both mostly zero in their second halves,
so a stride-16 sample of $EC00 would look identical either way
[[a-case-that-agrees-can-agree-for-the-wrong-reason]]. Sector 14 DOES differ from
sector 0 in its second half (checked against the image), so `w.half2` reads
$EC00 after `DSKI$(0,14)` and compares with that sector's bytes 256..263.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

DSK = os.path.join(ROOT, "disk", "test720.dsk")
CF = "National_CF-3300"
IMG = open(DSK, "rb").read()


def expect(sector, off, n=8):
    return " ".join(str(b) for b in IMG[sector * 512 + off:sector * 512 + off + n])


def program(sector, base):
    """Capture the eight bytes into NUMERIC variables BEFORE any string work.

    🔴 THE FIRST CUT BUILT A HEX STRING IN THE READ LOOP and every byte came
    back 0 (and 1 at the other address) -- constant, which no real sector is.
    MSX string space lives at the TOP of memory, exactly where the buffer under
    test is, so `D$=D$+HEX$(...)` was overwriting the thing it was reading. The
    page scan never saw this because it built its string only AFTER both
    checksums.
    """
    peeks = ":".join(f"B{i}=PEEK({base}+{i})" for i in range(8))
    return [
        '10 ON ERROR GOTO 900',
        f'20 A$=DSKI$(0,{sector})',
        f'25 {peeks}',
        '30 PRINT"ZQ";B0;B1;B2;B3;B4;B5;B6;B7;"QZ":END',
        '900 PRINT"ZQ";"E";ERR;"QZ":END',
    ]


# &HEB00 / &HEC00 are NEGATIVE in MSX BASIC's signed 16-bit &H notation; PEEK
# takes them, and writing them as the negative makes that explicit rather than
# relying on the reader knowing.
CASES = [
    ("w.sec0",  program(0, "&HEB00"), 0, 0,
     "after DSKI$(0,0): $EB00..$EB07 must be sector 0's first eight bytes"),
    ("w.sec1",  program(1, "&HEB00"), 1, 0,
     "after DSKI$(0,1): the SAME window must now hold sector 1's -- the row that "
     "makes w.sec0 more than a coincidence"),
    ("w.half2", program(14, "&HEC00"), 14, 256,
     "after DSKI$(0,14): $EC00..$EC07 vs that sector's bytes 256..263 -- is the "
     "transfer 512 bytes or 256?"),
]


def value(scr):
    if scr is None:
        return None
    for g in reversed(re.findall(r"ZQ\s*([0-9 ]*?)\s*QZ", scr)):
        if any(ch in g for ch in '"$;'):
            continue
        return " ".join(g.split())
    return None


def main() -> int:
    ok = True
    bad = 0
    for label, prog, sector, off, note in CASES:
        raw = "".join(omsx_repl.run_cases(
            CF, [("direct", ["NEW"] + prog + ["RUN"])], batch=False,
            reset=("", "SCREEN 0", "NEW"), boot=14.0, step=5.0,
            run_gap=30.0, cap_gap=5.0, timeout=600.0, diska=DSK)[0] or "")
        got, want = value(raw), expect(sector, off)
        match = "MATCH" if got == want else "\U0001f534 NO"
        if got != want:
            ok = False
            bad += 1
        print(f"\n{label}: {note}")
        print(f"    image wants: {want}")
        print(f"    machine has: {got}")
        print(f"    -> {match}")

    # `DIFF: n/m` is the summary line `filed_row_sweep.py` already parses. Without
    # it this probe SCORES (it returns 1 on a mismatch) but reports in a format the
    # sweep cannot read, so it landed in "NOTHING PARSED" beside probes that have
    # no verdict at all -- and a rotted instrument hid in that same bucket.
    print(f"DIFF: {sum(1 for _ in ()) + bad}/{len(CASES)}")
    print("\n" + ("\U0001f3af THE LANDING ADDRESS IS ESTABLISHED, NOT INFERRED."
                  if ok else
                  "\U0001f534 AT LEAST ONE ROW DID NOT MATCH -- read the rows above; "
                  "a mismatch on w.half2 alone is a 256-byte transfer, a mismatch "
                  "on w.sec0/w.sec1 means the address is wrong."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
