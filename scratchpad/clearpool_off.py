#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Assemble the `CLEARPOOL = 0` arm — which the filed item says never has been.

`FPERR_MISSOP` is equated inside `IF CLEARPOOL` in `basic/sysvars.inc` (12 with,
11 without) because `fperr_to_err` is a DENSE table whose next free index moves
with the switch. Getting it wrong is SILENT: the raise reads a neighbouring table
byte and reports some other error.

`make switch-build-check` cannot cover it -- its scope claim is *"no switch is
read outside `basic/`"* and CLEARPOOL is read from `sub/arrays.asm` and
`sub/strheap.asm`, so adding it to SWITCHES trips the tool's own
`scope_holds()`. So this assembles BOTH ROMs, which is what that scope needs.

🎯 AND ASSEMBLING IS ONLY HALF. The failure mode is an off-by-one that still
BUILDS, so the run also reads the byte back out: `fperr_to_err[FPERR_MISSOP]`
must be **24** in each arm, or the table and the equate have drifted apart. That
is the check the item is actually asking for.

⚠️ RESTORE IS CONTENT **AND** MTIME. `basic/sysvars.inc` goes back byte-identical
(asserted) and its mtime is put back too -- `check_switch_builds.py` learned that
the hard way: a bumped mtime makes `make -q` report the shipping ROM STALE, and
`latch-check`'s preflight then REFUSES on every gate after it.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "probes" / "lib"))
import probe_tmp                                                  # noqa: E402

SYSVARS = ROOT / "basic" / "sysvars.inc"
OUT = Path(probe_tmp.tmp("clearpool-off"))
PASMO = os.environ.get("PASMO", "pasmo")
BUILDS = [("main", ROOT / "basic" / "main.asm", []),
          ("sub", ROOT / "sub" / "sub.asm", ["-I", "sub"])]


def assemble(tag, src, extra):
    OUT.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([PASMO, *extra, "--bin", str(src),
                        str(OUT / f"{tag}.rom"), str(OUT / f"{tag}.sym")],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode == 0:
        return 0, ""
    txt = (r.stdout + r.stderr).strip().splitlines()
    return r.returncode, next((l for l in txt if "ERROR" in l.upper()),
                              txt[-1] if txt else "<no diagnostic>").strip()


def sym(tag, name):
    for line in open(OUT / f"{tag}.sym"):
        m = re.match(rf"^{re.escape(name)}\s+EQU\s+([0-9A-Fa-f]+)H", line)
        if m:
            return int(m.group(1), 16)
    return None


def table_entry(tag, base_sym, index, org):
    """fperr_to_err[index], read out of the assembled image."""
    rom = (OUT / f"{tag}.rom").read_bytes()
    base = sym(tag, base_sym)
    if base is None:
        return None
    off = base - org + (index - 1)          # FPERR codes are 1-based
    return rom[off] if 0 <= off < len(rom) else None


def arm(label, value):
    orig = SYSVARS.read_text()
    stat = SYSVARS.stat()
    try:
        SYSVARS.write_text(re.sub(r"^(CLEARPOOL\s+equ\s+)\d+",
                                  rf"\g<1>{value}", orig, count=1, flags=re.M))
        assert f"CLEARPOOL       equ     {value}" in SYSVARS.read_text(), \
            "the flip did not take -- the arm would test the wrong build"
        out = {}
        for tag, src, extra in BUILDS:
            rc, err = assemble(f"{label}-{tag}", src, extra)
            out[tag] = (rc, err)
        missop = None
        if out["main"][0] == 0:
            missop = sym(f"{label}-main", "FPERR_MISSOP")
            # 🔴 THE ORG IS `BASIC_ORG` = $2812, NOT A GUESS. The first cut fell
            # back to 0x4000 when it could not find a `MAIN_ORG` symbol (there is
            # none) and read bytes 32 and 67 out of the middle of the code -- a
            # FALSE red on a tree that is fine. An offset computed from a default
            # is not a reading.
            org = sym(f"{label}-main", "BASIC_ORG")
            assert org is not None, "BASIC_ORG missing from the sym file"
            entry = table_entry(f"{label}-main", "fperr_to_err", missop, org)
        else:
            entry = None
        return out, missop, entry
    finally:
        SYSVARS.write_text(orig)
        assert SYSVARS.read_text() == orig, "basic/sysvars.inc was NOT restored!"
        os.utime(SYSVARS, (stat.st_atime, stat.st_mtime))


def main():
    rows = []
    for label, value in (("on", 1), ("off", 0)):
        rows.append((label, value) + arm(label, value))
    print(f"{'arm':6s} {'main':>18s} {'sub':>18s} {'FPERR_MISSOP':>13s} "
          f"{'table[MISSOP]':>14s}")
    bad = 0
    for label, value, out, missop, entry in rows:
        m = "assembles" if out["main"][0] == 0 else f"FAIL {out['main'][1][:40]}"
        s = "assembles" if out["sub"][0] == 0 else f"FAIL {out['sub'][1][:40]}"
        print(f"CLEARPOOL={value}  {m:>18s} {s:>18s} {str(missop):>13s} "
              f"{str(entry):>14s}")
        if out["main"][0] or out["sub"][0]:
            bad += 1
        elif entry != 24:
            bad += 1
    if bad:
        print(f"\n🔴 {bad} arm(s) failed to assemble, or their "
              f"fperr_to_err[FPERR_MISSOP] is not 24 -- a raise there would "
              f"report SOME OTHER ERROR, silently.")
        return 1
    print("\n✅ both arms assemble (main AND sub), and in each the dense table's "
          "FPERR_MISSOP slot holds 24 -- the equate and the table agree on both "
          "sides of the switch.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
