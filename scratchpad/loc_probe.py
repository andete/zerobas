#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-LOCSEM — what does `LOC(#n)` actually DO on the reference?

TODO.md defers LOC with a reason: *"CF-3300 `LOC(1)` returns 26 (file size) both
before and after a read; sequential-file semantics unclear, so not
cargo-culted."* 26 is HI.TXT's size, so that observation was taken on a
SEQUENTIAL file — and MSX Disk BASIC's LOC is only well defined on a RANDOM one,
where it is the last record number read or written.

So the deferral may rest on the one case where the answer is least legible. This
does not implement anything: implementing a Disk BASIC function whose semantics
the filing calls unclear is a scope call and not mine. It replaces the unrun
justification with a measurement, so the call can be made on evidence.

  s.*   SEQUENTIAL, reproducing the filed observation and then extending it:
        LOC before any read, after 5 bytes, after 10. If it really is constant at
        the file size, three identical numbers say so; if it counts 128-byte
        blocks (the documented sequential meaning) it steps.
  r.*   RANDOM, where LOC is defined: GET record 3, then record 7. If LOC tracks
        the record number the readings are 0,3,7.
  w.*   the WRITE side: PUT record 4 and read LOC back.

⚠️ zerobas has NO `LOC` — it is absent from basic/kwtable.inc's 152 words, so
`LOC(1)` parses as an ARRAY reference and auto-dims. Its column is included
precisely to show what the gap looks like from BASIC, not as a comparison.
⚠️ The VG-8020 is DISKLESS and cannot run any of this; the CF-3300 is the only
oracle here, so no row can be cross-checked between two references
[[a-case-that-agrees-can-agree-for-the-wrong-reason]] does not even apply -- there
is nothing to agree with.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_tmp                                                  # noqa: E402

FIXTURE = os.path.join(ROOT, "disk", "test720.dsk")

SIDES = {
    "cf3300": ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW")),
    "zb": (os.environ.get("ZEROBAS_BASIC_MACHINE",
                          "C-BIOS_MSX1_EU_REPACK_DISK"), 8.0, ("NEW",)),
}

CASES = [
    ("s.seq", ['10 ON ERROR GOTO 90',
               '20 OPEN"HI.TXT"FOR INPUT AS #1',
               '30 A=LOC(1)',
               '40 X$=INPUT$(5,#1):B=LOC(1)',
               '50 X$=INPUT$(5,#1):C=LOC(1)',
               '60 CLOSE',
               '70 PRINT"ZQ";A;",";B;",";C;"QZ":END',
               '90 PRINT"ZQERR";ERR;"QZ":END'],
     "SEQUENTIAL: the filed observation, extended to two reads"),
    ("r.get", ['10 ON ERROR GOTO 90',
               '20 OPEN"TEST.BIN"AS #1 LEN=128',
               '30 A=LOC(1)',
               '40 GET #1,3:B=LOC(1)',
               '50 GET #1,7:C=LOC(1)',
               '60 CLOSE',
               '70 PRINT"ZQ";A;",";B;",";C;"QZ":END',
               '90 PRINT"ZQERR";ERR;"QZ":END'],
     "RANDOM: where LOC is DEFINED -- expect 0,3,7 if it is the record number"),
    ("w.put", ['10 ON ERROR GOTO 90',
               '20 OPEN"LOCW.DAT"AS #1 LEN=32',
               '30 FIELD #1,32 AS F$',
               '40 LSET F$="x":PUT #1,4:B=LOC(1)',
               '50 CLOSE',
               '60 PRINT"ZQ";0;",";B;",";0;"QZ":END',
               '90 PRINT"ZQERR";ERR;"QZ":END'],
     "the WRITE side: PUT record 4, then read LOC back"),
]


def run(side, tag, prog):
    """🔴 A PRIVATE COPY OF THE IMAGE PER (case, side). `w.put` CREATES a file,
    and boot-per-case reboots the machine while mounting the SAME path -- so a
    shared fixture would carry LOCW.DAT into every later row and into every other
    probe that mounts test720.dsk. The read-only rows get their own copy too:
    "it only reads" is an assumption about the emulator, not a guarantee."""
    import shutil
    machine, boot, reset = SIDES[side]
    dsk = probe_tmp.tmp(f"loc_{tag}_{side}.dsk")
    shutil.copyfile(FIXTURE, dsk)
    raw = "".join(omsx_repl.run_cases(
        machine, [("direct", list(reset) + prog + ["RUN"])], batch=False,
        reset=(), boot=boot, step=5.0, cap_gap=12.0, timeout=300.0,
        diska=dsk)[0] or "")
    m = re.search(r"ZQERR\s*(-?\d+)\s*QZ", raw)
    if m:
        return f"ERR {int(m.group(1))}"
    m = re.search(r"ZQ\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*QZ", raw)
    if m:
        return ",".join(str(int(g)) for g in m.groups())
    return "<NO READING>"


def main() -> int:
    print(f"{'row':7s} {'cf3300':>14s} {'zb':>14s}   what it means")
    for tag, prog, note in CASES:
        got = {s: run(s, tag, prog) for s in SIDES}
        print(f"{tag:7s} {got['cf3300']:>14s} {got['zb']:>14s}   {note}",
              flush=True)
    print("\n⚠️  NO VERDICT COLUMN ON PURPOSE. zerobas has no LOC, so this is not "
          "a differential — it is a CHARACTERISATION of the reference, so that "
          "the deferral in TODO.md rests on a measurement instead of on one "
          "sequential-file reading.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
