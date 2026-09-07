#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-FIELDWRITE — the WRITE half of the FIELD alias, which corrupts the DISK.

D-FIELDALIAS measured the read half: `F$` on channel 1 returns channel 2's record
after a `GET #2`, because a FIELD variable is a window onto the ONE shared record
buffer. That is a wrong VALUE in a variable.

The write half is worse, and it needs no decision from anyone to measure. If
`LSET F$` and `LSET G$` write the same memory, then:

    50 LSET F$="11111111"     intended for #1
    60 LSET G$="22222222"     intended for #2   <- overwrites the same bytes
    70 PUT #1,1               writes 22222222 into #1's FILE

...and the wrong record is on the DISK, surviving the program. The row reads the
files back after CLOSE, so the reading is what is actually stored, not what a
variable happened to hold.

    expected, per-channel buffers   TFC=11111111  TFD=22222222
    expected, shared buffer         TFC=22222222  TFD=22222222

`w.seq` is the CONTROL: the same two writes done with only ONE channel open at a
time. It must read 11111111 / 22222222 on every machine — if it does not, LSET or
PUT is broken generally and the two-channel row would prove nothing about
aliasing [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
"""
from __future__ import annotations

import os
import re
import shutil
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

READBACK = ['200 OPEN"TFC.DAT"AS #1 LEN=8:FIELD #1,8 AS F$:GET #1,1:A$=F$:CLOSE',
            '210 OPEN"TFD.DAT"AS #1 LEN=8:FIELD #1,8 AS G$:GET #1,1:B$=G$:CLOSE',
            '220 PRINT"ZY";A$;",";B$;"YZ":END']

CASES = [
    ("w.two", ['10 MAXFILES=2',
               '20 OPEN"TFC.DAT"AS #1 LEN=8:FIELD #1,8 AS F$',
               '30 OPEN"TFD.DAT"AS #2 LEN=8:FIELD #2,8 AS G$',
               '50 LSET F$="11111111"',
               '60 LSET G$="22222222"',
               '70 PUT #1,1',
               '80 PUT #2,1',
               '90 CLOSE'] + READBACK,
     "TWO channels open, both FIELDed, then both written"),
    # 🔴 THE LINE NUMBERS ARE THE PROGRAM ORDER, AND THE FIRST CUT GOT IT
    # WRONG. Written 10/20/50/30/60 to mirror the two-channel row visually, it
    # SORTS to 10/20/30/50/60 -- so #1 was re-opened while still open and the
    # whole control read <NO READING>. The probe refused to score rather than
    # reporting the two-channel divergence without its control, which is the
    # only reason this was caught rather than published.
    ("w.seq", ['10 MAXFILES=2',
               '20 OPEN"TFC.DAT"AS #1 LEN=8:FIELD #1,8 AS F$',
               '30 LSET F$="11111111":PUT #1,1:CLOSE',
               '40 OPEN"TFD.DAT"AS #1 LEN=8:FIELD #1,8 AS G$',
               '50 LSET G$="22222222":PUT #1,1:CLOSE'] + READBACK,
     "CONTROL: one channel at a time -- must be 11111111 / 22222222"),
]


def run(side, tag, prog):
    machine, boot, reset = SIDES[side]
    dsk = probe_tmp.tmp(f"fieldwrite_{tag}_{side}.dsk")
    shutil.copyfile(FIXTURE, dsk)
    raw = "".join(omsx_repl.run_cases(
        machine, [("direct", list(reset) + prog + ["RUN"])], batch=False,
        reset=(), boot=boot, step=8.0, cap_gap=75.0, timeout=500.0,
        diska=dsk)[0] or "")
    # the fence is in the source too: LAST match, refuse source punctuation
    for g in reversed(re.findall(r"ZY([^,]*),([^Y]*)YZ", raw)):
        if any(ch in "".join(g) for ch in '"$;'):
            continue
        return [x.strip() or "<empty>" for x in g]
    return None


def main() -> int:
    rows = []
    for tag, prog, note in CASES:
        got = {s: run(s, tag, prog) for s in SIDES}
        rows.append((tag, note, got))
        print(f"  {tag:6s} " + "  ".join(
            f"{s}={('/'.join(got[s]) if got[s] else '<NO READING>'):>21s}"
            for s in SIDES), flush=True)

    if not all(g[s] for _t, _n, g in rows for s in SIDES):
        print("\n🔴 INSTRUMENT FAULT: a side produced no reading.")
        return 2
    print(f"\n{'row':6s} {'TFC / TFD  cf3300':>24s} {'zb':>21s}   verdict")
    dis = []
    for tag, note, g in rows:
        c, z = "/".join(g["cf3300"]), "/".join(g["zb"])
        v = "SAME" if c == z else "🔴 DIFF"
        if c != z:
            dis.append(tag)
        print(f"{tag:6s} {c:>24s} {z:>21s}   {v}")
        print(f"       {note}")
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
