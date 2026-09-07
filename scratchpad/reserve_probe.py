#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-RESERVE — does the reference reserve its per-channel buffer UP FRONT for
MAXFILES, or ALLOCATE IT AS CHANNELS ARE OPENED? And is it sized by LEN=?

Joost, 2026-09-07. The question decides which fix shape zerobas should take for
the FIELD alias, so it is worth measuring rather than assuming.

D-HIMEMRES already read `R = 293 + 267*MAXFILES` on both references — but that
sweep varied MAXFILES, so it establishes only that the reservation SCALES with
the maximum. It cannot tell "reserved at MAXFILES time" from "allocated at OPEN
time", because in that sweep no file was ever opened.

    f.base    FRE(0) with MAXFILES=2, nothing open
    f.open1   ...after OPEN #1
    f.open2   ...after OPEN #2 as well
    f.closed  ...after CLOSE

    all four equal            -> RESERVED UP FRONT for MAXFILES
    drops at each OPEN        -> ALLOCATED AS USED

`f.len` repeats the pair with LEN=256 instead of LEN=8. If the allocation is
sized by the record length, the two differ by ~248 per channel; if it is a fixed
block, they do not. That third answer is the one that would matter most here —
it would mean zerobas could charge only `reclen` per OPEN channel instead of a
flat 256.

⚠️ The VG-8020 is DISKLESS, so it cannot open a disk channel at all. It is kept
as a column only for `f.base`, where MAXFILES alone is the subject; its OPEN rows
are expected to be errors and are NOT readings.
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


def prog(ln):
    return ['10 ON ERROR GOTO 90',
            '20 MAXFILES=2',
            '30 A=FRE(0)',
            f'40 OPEN"TFA.DAT"AS #1 LEN={ln}',
            '50 B=FRE(0)',
            f'60 OPEN"TFB.DAT"AS #2 LEN={ln}',
            '70 C=FRE(0)',
            '80 CLOSE:D=FRE(0)',
            '85 PRINT"ZF";A;",";B;",";C;",";D;"FZ":END',
            '90 PRINT"ZFERR";ERR;"FZ":END']


CASES = [("f.len8", prog(8), "LEN=8 — the record is tiny"),
         ("f.len256", prog(256), "LEN=256 — the record is the maximum")]


def run(side, tag, p):
    machine, boot, reset = SIDES[side]
    dsk = probe_tmp.tmp(f"reserve_{tag}_{side}.dsk")
    shutil.copyfile(FIXTURE, dsk)
    raw = "".join(omsx_repl.run_cases(
        machine, [("direct", list(reset) + p + ["RUN"])], batch=False,
        reset=(), boot=boot, step=8.0, cap_gap=60.0, timeout=400.0,
        diska=dsk)[0] or "")
    # 🔴 BOTH FENCES ARE IN THE SOURCE THE MACHINE ECHOES, and the first cut
    # guarded only ONE. `re.search("ZFERR")` matched the ECHO of line 90 and
    # short-circuited before the data fence was even tried, so all four rows
    # reported "ERR" with no number -- from a program that had run fine. Third
    # time this trap has fired today [[trapsvc-echo-fence]]; the lesson is that
    # guarding the fence you expect is not the same as guarding every fence.
    def real(pat, n):
        for g in reversed(re.findall(pat, raw)):
            g = g if isinstance(g, tuple) else (g,)
            if any(ch in "".join(g) for ch in '"$;'):
                continue                      # that is the echo
            return [int(x) for x in g]
        return None
    data = real(r"ZF([^,\"$;]*),([^,\"$;]*),([^,\"$;]*),([^F\"$;]*)FZ", 4)
    if data:
        return data
    err = real(r"ZFERR\s*(-?\d+)\s*FZ", 1)
    if err:
        return f"ERR {err[0]}"
    return None


def main() -> int:
    out = {}
    for tag, p, note in CASES:
        for s in SIDES:
            v = run(s, tag, p)
            out[(tag, s)] = v
            print(f"  {tag:9s} {s:7s} {v}", flush=True)

    print(f"\n{'case':9s} {'side':7s} {'base':>7s} {'+open1':>7s} "
          f"{'+open2':>7s} {'closed':>7s}   what it says")
    for tag, p, note in CASES:
        for s in SIDES:
            v = out[(tag, s)]
            if not isinstance(v, list):
                print(f"{tag:9s} {s:7s} {str(v):>31s}   not a reading")
                continue
            a, b, c, d = v
            if a == b == c:
                verdict = "RESERVED UP FRONT (open costs nothing)"
            elif b < a and c < b:
                verdict = f"ALLOCATED AS USED (-{a-b} then -{b-c})"
            else:
                verdict = "neither shape — read the numbers"
            print(f"{tag:9s} {s:7s} {a:>7d} {b:>7d} {c:>7d} {d:>7d}   {verdict}")
    # does LEN change the cost?
    for s in SIDES:
        v8, v256 = out[("f.len8", s)], out[("f.len256", s)]
        if isinstance(v8, list) and isinstance(v256, list):
            d8, d256 = v8[0] - v8[2], v256[0] - v256[2]
            print(f"\n{s}: two channels cost {d8} B at LEN=8 and {d256} B at "
                  f"LEN=256 -> "
                  + ("SIZED BY LEN" if d8 != d256 else "a FIXED block"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
