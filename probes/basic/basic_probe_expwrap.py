#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EXPWRAP — a numeric literal whose exponent digits run past 9999.

The tokeniser accumulates an exponent's digits as DE = DE*10 + digit and clamps
at 9999 (which then reads as Overflow, or 0 for a negative exponent beyond the
range). The multiply is 16-bit, so until 2026-11-04 a running 6554..9999 WRAPPED
below the clamp: `1E65540` crunched as 1E4, `1E65536` as 1E0 and `1E-65540` as
1E-4 (sub/tkfloat.asm tke_dloop).

MEASURED 2026-11-04 on the Philips VG-8020: every one of those is `Overflow`,
like any exponent past the range (`1E64`, `1E99999`, `1E-99`); `1E-65` is 0.
zerobas agreed everywhere except the wrap rows.

ROWS, each a direct `PRINT "[";<literal>;"]"` (the brackets prove the PRINT
ran; an error prints its message instead):
  ctrl     1E5        -> [ 100000 ]   positive control: a reference that misses
                                      it is a broken fixture (exit 2)
  w1..w5   the wrap cases           -> Overflow on the VG-8020
  b1..b4   the edges that already agreed (the rows that keep a fix honest)

Sides: vg8020 (the reference Joost prefers when they differ), zb (zerobas
DISK machine, with a blank disk so Disk BASIC boots), zbnd (zerobas NODISK).
Clean-room: the screen is read back only; the reference ROM is a black box.
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
    ("ctrl", "1E5"),
    ("w1", "1E65540"),
    ("w2", "1E65536"),
    ("w3", "1E-65540"),
    ("w4", "1D65540"),
    ("w5", "-1E65540"),
    ("b1", "1E64"),
    ("b2", "1E99999"),
    ("b3", "1E-65"),
    ("b4", "1E-99"),
]


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
    if "Overflow" in txt:
        return "<Overflow>"
    return f"<UNREADABLE: {txt[:40]}>" if txt.replace("Ok", "").strip() else "<NO OUTPUT>"


def run_side(side: str, only: list[str]) -> dict[str, str]:
    cfg = SIDES[side]
    out = {}
    for label, lit in CASES:
        if only and label not in only:
            continue
        kw = {}
        if cfg["diska"]:
            dsk = probe_tmp.tmp(f"zb_expwrap_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        line = f'PRINT "[";{lit};"]"'
        caps = omsx_repl.run_cases(cfg["machine"],
                                   [("direct", ["SCREEN 0", "NEW", line])],
                                   batch=False, **kw)
        out[label] = reading(caps[0], line)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="D-EXPWRAP: exponent digits past 9999")
    ap.add_argument("--sides", default="vg8020,zb,zbnd")
    ap.add_argument("--only", default="")
    ap.add_argument("--gate", action="store_true")
    a = ap.parse_args()
    sides = [s for s in a.sides.split(",") if s]
    only = [o for o in a.only.split(",") if o]
    res = {s: run_side(s, only) for s in sides}
    if REF in res and res[REF].get("ctrl", "[100000]") != "[100000]":
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
    print(f"expwrap: {bad} row(s) diverge from the {REF}")
    print(__import__("probe_refcache").summary())
    return 1 if (a.gate and bad) else 0


if __name__ == "__main__":
    raise SystemExit(main())
