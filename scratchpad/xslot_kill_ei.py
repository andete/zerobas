#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DISKVERB phase 2 -- is hk_kill's `ei` doing what its comment claims?

The comment says: without it, KILL would freeze TIME, PLAY and the traps for the
whole verb, because a hook handler is entered with interrupts OFF (D-XSLOTPRICE
0c measured ~1 s of work advancing TIME by 3 frames). That is a claim about
shipped code, so it is measured rather than asserted -- an unrun justification
beside a shipped line is exactly the thing that rots.

THE SUBJECT: `KILL "NOSUCH.XYZ"` against a real disk. The name matches nothing,
so the verb is a full directory search -- real I/O, real time -- ending in
ERR 53, which ON ERROR catches so the program can report TIME itself.

RUN IT TWICE, ONE LINE APART: once on the shipped build, once on a build with
the `ei` removed (scratchpad/xslot_noei.py). With the `ei` TIME must advance by
the verb's real duration; without it, barely at all.

⚠️ THE DISK IS COPIED FIRST. openMSX writes back to a .dsk, and KILL is a write
verb even when it finds nothing to delete.
"""
from __future__ import annotations
import os, re, shutil, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
SRC_DSK = os.path.join(REPO, "disk", "test720.dsk")

PROG = [
    "10 ON ERROR GOTO 100",
    '20 T=TIME:KILL "NOSUCH.XYZ"',
    '30 PRINT "[";TIME-T;"]":END',
    '100 PRINT "[";TIME-T;"]":END',
    "RUN",
]


def main() -> int:
    if not os.path.exists(SRC_DSK):
        print(f"INSTRUMENT FAULT: no test disk at {SRC_DSK}")
        return 2
    tmp = tempfile.mkstemp(suffix=".dsk")[1]
    shutil.copyfile(SRC_DSK, tmp)
    caps = omsx_repl.run_cases(ZB, [("kill.miss", PROG)], batch=False, reset=(),
                               boot=8.0, step=3.0, cap_gap=45.0, timeout=900.0,
                               diska=tmp)
    scr = caps[0] or ""
    m = re.search(r"\[\s*(-?\d+)\s*\]", scr)
    if not m:
        print("=== screen ===\n" + scr)
        print("\nINSTRUMENT FAULT (rc 2): the fence never printed.")
        return 2
    frames = int(m.group(1))
    print(f"KILL \"NOSUCH.XYZ\" (full directory search, then ERR 53): "
          f"TIME advanced {frames} frames")
    print()
    print("With hk_kill's `ei`, this is the verb's real duration. Without it the")
    print("clock is stopped for the whole verb and this reads near zero -- run the")
    print("same probe against a build with the `ei` removed to see the other side.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
