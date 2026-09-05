#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-FSPECCHAR -- WHICH bytes does a filespec refuse? The domain, swept.

Filed 2026-09-05 by D-FILESINP: `FILES` with a filespec built from CONTROL BYTES
answers `Bad file name` on the CF-3300 and `File not found` here, so
`build_83_name` validates neither the character SET nor control bytes and the
reference evidently does. The fix cannot be scoped before the domain is known --
"which bytes" was unswept in BOTH directions.

This sweeps it. One row per candidate byte: `FILES CHR$(n)+"BC.TXT"`, so the
byte sits in the NAME's first position and everything after it is a legal 8.3
name. The filespec is an expression (D-FNEXPR2), so `CHR$` reaches it directly
and nothing has to be typed as a literal control character.

⚠️ THE CONTROLS ARE PART OF THE SWEEP, NOT DECORATION. `$41` ("A") must be
ACCEPTED on both sides or the row shape itself is refusing things, and `$2A`
("*") must be accepted because it is the wildcard every `FILES` row already uses.
Without them a column of `Bad file name` reads the same whether the reference is
strict or the shape is broken.

⚠️ AND `.` ($2E) IS EXPECTED TO DIFFER FROM THE REST for a reason that is not
about the character set: it is the 8.3 SEPARATOR, so `CHR$(46)+"BC.TXT"` is a
name with two dots, which D-FSPEC (2026-09-04) already settled. It is in the
sweep as a KNOWN-SHAPE anchor, not as a finding.

    python3 scratchpad/fspecchar_probe.py
"""
from __future__ import annotations

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import omsx_repl                                                   # noqa: E402
import probe_tmp                                                   # noqa: E402
from basic_probe_namspc import SIDES, errface, TEST_DSK            # noqa: E402

# byte -> why it is in the sweep
BYTES = [
    (0x41, "A  -- CONTROL: a plain letter must be ACCEPTED"),
    (0x2A, "*  -- CONTROL: the wildcard every FILES row uses"),
    (0x00, "NUL"), (0x01, "SOH"), (0x04, "the byte D-FILESINP hit"),
    (0x09, "TAB"), (0x0D, "CR"), (0x1F, "US -- last control"),
    (0x20, "space"),
    (0x21, "!"), (0x23, "#"), (0x26, "&"), (0x28, "("), (0x2B, "+"),
    (0x2C, ","), (0x2D, "-"), (0x2E, ".  -- the 8.3 SEPARATOR, known shape"),
    (0x2F, "/"), (0x3A, ":"), (0x3B, ";"), (0x3C, "<"), (0x3D, "="),
    (0x3F, "?  -- the single-char wildcard"),
    (0x5B, "["), (0x5C, "\\"), (0x5D, "]"), (0x7C, "|"), (0x7E, "~"),
    (0x61, "a  -- lowercase"), (0x80, "high bit"), (0xFF, "$FF"),
    # --- round 2: the printable specials round 1 left out, so the accepted set
    # --- is a MEASURED domain rather than a sample with holes in it.
    (0x10, "DLE -- mid-range control, does the whole $01-$1F band behave alike?"),
    (0x22, '"'), (0x24, "$"), (0x25, "%"), (0x27, "'"), (0x29, ")"),
    (0x3E, ">  -- the partner of the accepted '<'"),
    (0x40, "@"), (0x5E, "^"), (0x5F, "_"), (0x60, "`"),
    (0x7B, "{"), (0x7D, "}"), (0x7F, "DEL"),
]


def run(side, n):
    cfg = SIDES[side]
    kw = {}
    if cfg["diska"]:
        dsk = probe_tmp.tmp(f"zb_fspecchar_{side}_{n:02X}.dsk")
        shutil.copy(TEST_DSK, dsk)
        kw["diska"] = dsk
    body = [f'10 FILES CHR$({n})+"BC.TXT"', '20 PRINT"[OK]"']
    caps = omsx_repl.run_cases(
        cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
        batch=False, reset=(), boot=cfg["boot"], step=cfg["step"], **kw)
    return errface(caps[0])


def main():
    # `--only 22,3E` re-runs a subset without re-spending the whole sweep.
    sel = None
    for i, a in enumerate(sys.argv):
        if a == "--only" and i + 1 < len(sys.argv):
            sel = {int(x, 16) for x in sys.argv[i + 1].split(",")}
    global BYTES
    if sel is not None:
        BYTES = [(n, w) for n, w in BYTES if n in sel]
    print("=== D-FSPECCHAR: which bytes does a filespec refuse? ===\n")
    print(f"  {'byte':6} {'why':44} {'cf3300':22} {'zb':22}")
    diffs, faults = [], []
    for n, why in BYTES:
        r, z = run("cf3300", n), run("zb", n)
        flag = ""
        if r != z:
            flag = "  🔴 DIFF"
            diffs.append((n, why, r, z))
        print(f"  ${n:02X}   {why:44} {str(r):22} {str(z):22}{flag}")
        if n in (0x41, 0x2A) and ("Bad file name" in str(r) or "Bad file name" in str(z)):
            faults.append(n)
    print()
    if faults:
        print(f"🔴 INSTRUMENT FAULT: the control byte(s) {[hex(f) for f in faults]} "
              f"were REFUSED — the row shape is rejecting things, so a column of "
              f"refusals says nothing about the character set.")
        return 2
    print(f"{len(diffs)} byte(s) diverge of {len(BYTES)} swept "
          f"(2 of them controls that must not).")
    for n, why, r, z in diffs:
        print(f"   ${n:02X} {why:44} cf3300={r!s:22} zb={z!s}")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
