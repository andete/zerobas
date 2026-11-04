#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-NODISKERRTXT — `ERROR 60`..`72` prints a disk text only on a disk machine.

60.. are the disk ROM's error codes. MEASURED 2026-11-04: the Philips VG-8020
(no disk ROM) prints `Unprintable error` for every one of 60..73; the National
CF-3300 prints its disk texts (Bad FAT, Bad file mode, ...). zerobas's DISKLESS
build printed the CF-3300's 60..65 texts, because the sub ROM holds them for
both builds; 66.. already went through the disk ROM's H_ERRP hook.

Two PAIRS, each scored against its own reference:
  zbnd (NODISK) vs vg8020          -- the diskless answer
  zb   (DISK)   vs cf3300 (+disk)  -- the disk answer must not move
ROWS: `10 ERROR n` + RUN for n in 59 (a control both print), 60..66, 70; read
the text before ` in 10`.
Clean-room: the screen is read back only; both reference ROMs are black boxes.
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
    "cf3300": dict(machine="National_CF-3300", diska=True),
    "zb": dict(machine="C-BIOS_MSX1_EU_REPACK_DISK", diska=True),
    "zbnd": dict(machine="C-BIOS_MSX1_EU_REPACK_NODISK", diska=False),
}
PAIRS = (("zbnd", "vg8020"), ("zb", "cf3300"))
CODES = (59, 60, 61, 62, 63, 64, 65, 66, 70)


def reading(raw: str | None) -> str:
    if raw is None:
        return "<NO CAPTURE>"
    flat = " ".join(str(raw).split())
    k = flat.rfind("RUN")
    t = flat[k + 3:] if k >= 0 else ""
    if " in 10" not in t:
        return f"<UNREADABLE: {t[:30]}>" if t.strip() else "<NO OUTPUT>"
    return t.split(" in 10")[0].strip()


def run_side(side: str, codes) -> dict[int, str]:
    cfg = SIDES[side]
    out = {}
    for code in codes:
        kw = {}
        if cfg["diska"]:
            dsk = probe_tmp.tmp(f"zb_errtxt60_{side}_{code}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        caps = omsx_repl.run_cases(cfg["machine"],
                                   [("direct", ["SCREEN 0", "NEW",
                                                f"10 ERROR {code}", "RUN"])],
                                   batch=False, **kw)
        out[code] = reading(caps[0])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="D-NODISKERRTXT: disk error texts (errtxt60)")
    ap.add_argument("--gate", action="store_true")
    a = ap.parse_args()
    res = {s: run_side(s, CODES) for s in SIDES}
    for ref in ("vg8020", "cf3300"):
        if res[ref][59] != "File not OPEN":
            print(f"🔴 BROKEN FIXTURE: the {ref} control (ERROR 59) read {res[ref][59]!r}")
            return 2
    bad = 0
    for code in CODES:
        cells = []
        for zb, ref in PAIRS:
            ok = res[zb][code] == res[ref][code]
            bad += not ok
            cells.append(f"{'ok' if ok else 'DIFF'} {zb}={res[zb][code]!r} {ref}={res[ref][code]!r}")
        print(f"ERROR {code:2d}  " + "  |  ".join(cells))
    print(f"errtxt60: {bad} cell(s) diverge")
    print(__import__("probe_refcache").summary())
    return 1 if (a.gate and bad) else 0


if __name__ == "__main__":
    raise SystemExit(main())
