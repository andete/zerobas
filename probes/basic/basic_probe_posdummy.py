#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-POSDUMMY — POS(n) / LPOS(n) take a dummy argument of EITHER type.

MEASURED 2026-11-04 on the Philips VG-8020: the argument is evaluated -- an
error inside it still raises (`POS(1/0)` Division by zero, `POS(CHR$(300))`
Illegal function call) -- but its type is not checked: `POS("A")`, `POS(A$)`,
`POS(""+"")` and `LPOS("A")` answer like `POS(0)`. zerobas said Type mismatch
for every string form until D-POSDUMMY.

ROWS, each a direct `PRINT "[";<expr>;"]"`:
  ctrl   POS(0)       positive control (exit 2 if the reference misses it)
  s1..s5 the string forms   -> a value on the VG-8020
  e1, e2 errors INSIDE the argument -> still raised
  n1     POS(-1)      a numeric dummy outside any domain -> a value
Sides: vg8020, zb (DISK, blank disk), zbnd (NODISK). Clean-room: screen only.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_repl                                                 # noqa: E402
import probe_tmp                                                 # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
TEST_DSK = os.path.join(REPO, "disk", "test720.dsk")

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", diska=False),
    "zb": dict(machine="C-BIOS_MSX1_EU_REPACK_DISK", diska=True),
    "zbnd": dict(machine="C-BIOS_MSX1_EU_REPACK_NODISK", diska=False),
}
REF = "vg8020"

CASES = [
    ("ctrl", "POS(0)"),
    ("s1", 'POS("A")'),
    ("s2", 'LPOS("A")'),
    ("s3", "POS(A$)"),
    ("s4", 'POS(""+"")'),
    ("s5", 'LPOS(A$+"B")'),
    ("e1", "POS(1/0)"),
    ("e2", "POS(CHR$(300))"),
    ("n1", "POS(-1)"),
]
ERRORS = ("Division by zero", "Illegal function call", "Type mismatch", "Syntax error")


def reading(raw: str | None, line: str) -> str:
    if raw is None:
        return "<NO CAPTURE>"
    # anchor on the WHOLE echoed line (screen_tail anchors on a line, not a
    # substring), and read what follows it
    flat = " ".join(str(raw).split())
    k = flat.rfind(line)
    txt = flat[k + len(line):] if k >= 0 else ""
    i, j = txt.find("["), txt.find("]")
    if 0 <= i < j:
        return "[" + txt[i + 1:j].strip() + "]"
    for e in ERRORS:
        if e in txt:
            return f"<{e}>"
    return f"<UNREADABLE: {txt[:40]}>" if txt.replace("Ok", "").strip() else "<NO OUTPUT>"


def run_side(side: str, only: list[str]) -> dict[str, str]:
    cfg = SIDES[side]
    out = {}
    for label, lit in CASES:
        if only and label not in only:
            continue
        kw = {}
        if cfg["diska"]:
            dsk = probe_tmp.tmp(f"zb_posdummy_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        line = f'PRINT "[";{lit};"]"'
        caps = omsx_repl.run_cases(cfg["machine"],
                                   [("direct", ["SCREEN 0", "NEW", line])],
                                   batch=False, **kw)
        out[label] = reading(caps[0], line)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="D-POSDUMMY: POS / LPOS dummy argument")
    ap.add_argument("--sides", default="vg8020,zb,zbnd")
    ap.add_argument("--only", default="")
    ap.add_argument("--gate", action="store_true")
    a = ap.parse_args()
    sides = [s for s in a.sides.split(",") if s]
    only = [o for o in a.only.split(",") if o]
    res = {s: run_side(s, only) for s in sides}
    if REF in res and not res[REF].get("ctrl", "[").startswith("["):
        print(f"🔴 BROKEN FIXTURE: the {REF} control read {res[REF]['ctrl']!r}")
        return 2
    bad = 0
    for label, lit in CASES:
        if label not in res.get(sides[0], {}):
            continue
        ref = res.get(REF, {}).get(label)
        cells = "  ".join(f"{s}={res[s][label]!r}" for s in sides)
        diff = any(res[s][label] != ref for s in sides if s != REF) if ref else False
        bad += diff
        print(f"{'DIFF' if diff else 'ok  '} {label:5s} {lit:10s} {cells}")
    print(f"posdummy: {bad} row(s) diverge from the {REF}")
    print(__import__("probe_refcache").summary())
    return 1 if (a.gate and bad) else 0


if __name__ == "__main__":
    raise SystemExit(main())
