#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-GETSTRADDLE — does the reference REFUSE a record that straddles EOF, or PAD it?

WHY THIS IS THE DESIGN INPUT AND NOT A CURIOSITY. D-GETREC filed the EOF bound as
needing a comparison against `FAT_FILESIZE` and a new tenant error contract.
Reading `basic/randio-body.inc` says otherwise on both counts: `fat_rand_get`
ALREADY detects the condition -- `frnd_locate` returns Cy beyond EOF and the code
branches to `frg_eoffill`, *"beyond EOF -> spaces"* -- and the randio tenant
ALREADY writes `DISKOP_STATUS` (0 ok / nonzero error, `sub/randio.asm`). So the
work is to REPORT instead of PAD, not to detect.

\U0001f534 WHICH MAKES ONE UNMEASURED QUESTION LOAD-BEARING. `frg_eoffill` fires per
PASS, and a record can straddle the end of the file: start inside it and finish
past it. Refusing the whole record and padding the tail are BOTH consistent with
every row D-GETREC has, because all of its out-of-range records start at or
beyond EOF. Ship the wrong one and the rule is encoded permanently
[[two-rules-that-coincide-on-every-row-you-have]].

THE FIXTURE IS THE MEASUREMENT. Write a SEQUENTIAL file of 14 bytes, reopen it
RANDOM with `LEN=10`, then:

    g.in       GET#1,1   bytes  0..9   entirely inside      -> expect 0
    g.straddle GET#1,2   bytes 10..19  starts in, ends past -> THE QUESTION
    g.past     GET#1,3   bytes 20..29  entirely past        -> expect 55

`g.in` and `g.past` are the controls that make the middle row readable: without
them a `0` on the subject could be "padding is fine" or "the file was longer than
I thought".

⚠️ NEEDS-DISK: the VG-8020 has no drive, so the CF-3300 is the only oracle and
the VG is not scored. Each side gets its OWN copy of the fixture, because the
setup writes to it.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_sides                                                # noqa: E402

probe_sides.require_disk("cf3300", "zb")
SIDES = probe_sides.sides("cf3300", "zb")
FIXTURE = os.path.join(ROOT, "disk", "test720.dsk")

CASES = [
    ("g.in",       "1", "bytes 0..9 -- entirely inside a 14-byte file"),
    ("g.straddle", "2", "bytes 10..19 -- STARTS inside, ENDS past EOF"),
    ("g.past",     "3", "bytes 20..29 -- entirely past EOF"),
]


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="getstraddle-")
    out = {}
    for tag, rec, note in CASES:
        row = {}
        for side, c in SIDES.items():
            img = os.path.join(tmp, f"{tag}-{side}.dsk")
            shutil.copyfile(FIXTURE, img)
            p = ["10 ON ERROR GOTO 900",
                 # 12 characters + the CRLF PRINT# appends = a 14-byte file,
                 # which is NOT a multiple of the 10-byte record length -- that
                 # is the whole point of the fixture.
                 '20 OPEN"A:S.DAT"FOR OUTPUT AS#1',
                 '30 PRINT#1,"123456789012"',
                 "40 CLOSE#1",
                 '50 OPEN"A:S.DAT"AS#1 LEN=10',
                 "60 FIELD#1,10 AS A$",
                 "70 E=0",
                 f"80 GET#1,{rec}",
                 "90 GOTO 300",
                 "900 E=ERR:RESUME 300",
                 '300 CLOSE#1:PRINT"ZQ";E;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=16.0,
                cap_gap=4.0, timeout=420.0, diska=img)[0] or "")
            v = [g for g in re.findall(r'ZQ\s*([0-9]+)\s*QZ', raw)
                 if '"' not in g and ';' not in g]
            row[side] = v[-1] if v else None
        out[tag] = row
        f = {s: ("<none>" if row[s] is None else f"ERR={row[s]}") for s in SIDES}
        same = f["cf3300"] == f["zb"]
        print(f"  {tag:11s} GET#1,{rec}  cf={f['cf3300']:9s} zb={f['zb']:9s}"
              f"{'' if same else '   \U0001f534 DIFF'}   {note}", flush=True)

    if any(v is None for r in out.values() for v in r.values()):
        print("\n  \U0001f534 A ROW HAS NO READING -- nothing is concluded.")
        return 2
    if out["g.in"]["cf3300"] != "0" or out["g.past"]["cf3300"] != "55":
        print(f"\n  \U0001f534 A CONTROL MOVED (in={out['g.in']['cf3300']}, "
              f"past={out['g.past']['cf3300']}) -- the fixture is not the file this "
              f"probe thinks it built, so the subject row says nothing.")
        return 2

    s = out["g.straddle"]["cf3300"]
    print()
    if s == "0":
        print("  \U0001f7e2 THE REFERENCE PADS A STRADDLING RECORD. So the EOF refusal is "
              "per-RECORD-START, not per-pass: `fat_rand_get` must report only when "
              "the FIRST pass is beyond EOF, and keep frg_eoffill for the tail.")
    elif s == "55":
        print("  \U0001f7e2 THE REFERENCE REFUSES A STRADDLING RECORD. So any pass beyond "
              "EOF is an error and frg_eoffill goes away entirely -- the simpler "
              "fix, and it would have been the wrong guess without this row.")
    else:
        print(f"  \U0001f534 A THIRD ANSWER: ERR {s}. Neither reading fits; read the raw "
              f"screen before designing anything on it.")
    print(f"  zerobas answers {out['g.straddle']['zb']} on the same row.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
