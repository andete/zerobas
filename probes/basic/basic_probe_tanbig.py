#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TANBIG — SIN / COS / TAN reduce the angle the VG-8020's way.

Until 2026-11-04 zerobas reduced angles with a more accurate Cody-Waite split of
pi/2; Joost then ruled to adopt the reference's own reduction, which is
black-box (scratchpad/tanbig_model.py, 19/19 measured rows): turns
t = round14(|x| * round14(1/2pi)); SIN = sin(2pi*frac t); COS =
sin(2pi*frac round14(0.25 - t)); TAN = SIN/COS, a COS of exactly 0 Overflow.

ROWS, each a direct `PRINT "[";<exprs>;"]"` (the brackets prove the PRINT ran;
an error prints its message instead). Every row below agrees to the LAST digit
on the reference and gave a different answer under the old reduction -- so a
reduction change in either direction turns one red. Rows whose last digit is
the polynomial's (SIN(1E10), SIN(1)) are deliberately absent.
  ctrl   SIN(0)                   -> [ 0 ]  (exit 2 if the reference misses it)
  q*/c*  quantised huge angles    t*  TAN Overflow    o*  ordinary angles

Sides: vg8020 (the reference), zbnd (zerobas NODISK; the tenants are the
same sub-ROM on the disk build). Clean-room: the screen is read back only.
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
    ("ctrl", "SIN(0)"),
    ("q13", "SIN(1E13);COS(1E13)"),
    ("q50", "SIN(5E13);COS(5E13)"),
    ("c70", "SIN(7E13);COS(7E13)"),
    ("t70", "TAN(7E13)"),
    ("t38", "TAN(1E38)"),
    ("tm38", "TAN(-1E38)"),
    ("td30", "TAN(1D30)"),
    ("m3e12", "COS(-3E12);TAN(-3E12)"),
    ("o1k", "SIN(1000);COS(1000)"),
    ("ohp", "COS(1.5707963267949#)"),
    ("thp", "TAN(1.5707963267949#)"),
    ("oh5", "SIN(.5);COS(.5);TAN(.5)"),
    ("oc12", "COS(12345.678#)"),
    ("om12", "COS(-12345.678#)"),
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
            dsk = probe_tmp.tmp(f"zb_tanbig_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        line = f'PRINT "[";{lit};"]"'
        caps = omsx_repl.run_cases(cfg["machine"],
                                   [("direct", ["SCREEN 0", "NEW", line])],
                                   batch=False, **kw)
        out[label] = reading(caps[0], line)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="D-TANBIG: the reference's trig reduction")
    ap.add_argument("--sides", default="vg8020,zbnd")
    ap.add_argument("--only", default="")
    ap.add_argument("--gate", action="store_true")
    a = ap.parse_args()
    sides = [s for s in a.sides.split(",") if s]
    only = [o for o in a.only.split(",") if o]
    res = {s: run_side(s, only) for s in sides}
    if REF in res and res[REF].get("ctrl", "[0]") != "[0]":
        print(f"🔴 BROKEN FIXTURE: the {REF} control read {res[REF]['ctrl']!r}")
        return 2
    # A row both sides fail to READ agrees for the wrong reason (a wrapped
    # echo did exactly that here once): every reference reading must be a value
    # or a named error.
    blind = [k for k, v in res.get(REF, {}).items() if v.startswith(("<NO", "<UNREAD"))]
    if blind:
        print(f"🔴 BROKEN FIXTURE: the {REF} rows {blind} were not read")
        return 2
    bad = 0
    for label, lit in CASES:
        if label not in res.get(sides[0], {}):
            continue
        ref = res.get(REF, {}).get(label)
        cells = "  ".join(f"{s}={res[s][label]!r}" for s in sides)
        diff = any(res[s][label] != ref for s in sides if s != REF) if ref else False
        bad += diff
        print(f"{'DIFF' if diff else 'ok  '} {label:5s} {lit:34s} {cells}")
    print(f"tanbig: {bad} row(s) diverge from the {REF}")
    print(__import__("probe_refcache").summary())
    return 1 if (a.gate and bad) else 0


if __name__ == "__main__":
    raise SystemExit(main())
