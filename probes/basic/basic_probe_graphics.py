#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Graphics G2 acceptance — the load-bearing VG-8020 DIFFERENTIAL for PSET /
PRESET / POINT (docs/spec-basic-graphics-g2.md §8).

Two phases, each run on BOTH the Philips VG-8020 reference and the merged zerobas
machine (C-BIOS_MSX1_EU_REPACK_DISK), asserting byte/text-identical results:

  PHASE A -- pixel plane differential (the colour clash lives here). Each case runs
    `COLOR 15,4,7 : SCREEN 2` (the §11.3 pinned post-CLS state: every colour byte
    $04 = fg 0 | bg BAKCLR 4), then the PSET/PRESET ops, then spins in a GOTO-self
    loop so the SCREEN-2 "Ok" prompt never rewrites the top-left cells. We read the
    pattern byte AND the colour byte back from VRAM (debug read_block VRAM) mid-loop
    and assert both machines wrote identical bytes. Reading the COLOUR plane is the
    whole point (spec §8 teeth): a PSET that sets the right pattern bit but the wrong
    attribute nibble passes a pattern-only check while being wrong. (No VPOKE for the
    pre-state: a VPOKE leaves the VDP mid-write and perturbs the tenant's very next
    read -- COLOR/SCREEN gives the same known state without that hazard.)

  PHASE B -- behavioural differential (clip / errors / POINT / STEP). Cases print a
    tagged outcome to the SCREEN-0 text plane (ON ERROR traps the raisers); we
    compare the tag + its numeric answer (trailing prompt text ignored).

Boot-per-case in phase A (the GOTO-self loop blocks KEYBUF, so batching can't
advance). Needs the merged machine installed (make repack-machine) + openMSX.

    make graphics-acceptance      # or: python3 probes/basic/basic_probe_graphics.py
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

INIT = "COLOR15,4,7:SCREEN2"          # §11.3 state: colour plane = $04 (fg0|bg4)


def paddr(x: int, y: int) -> int:
    return (y >> 3) * 256 + (x >> 3) * 8 + (y & 7)


def prog(stmts: list[str]) -> list[str]:
    """Append a GOTO-self loop so the case holds SCREEN 2 (the prompt never
    corrupts the test cell). The loop line's number = 10*(len+1)."""
    return stmts + [f"GOTO {10 * (len(stmts) + 1)}"]


# label, ops (one line), pixel read back, expected pattern byte, expected colour byte
DRAW_CASES = [
    ("pset_single",   "PSET(0,0),15",                        (0, 0), "80", "f4"),
    ("pset_clash",    "PSET(0,0),15:PSET(1,0),6",            (0, 0), "c0", "64"),
    ("pset_clear_bg", "PSET(0,0),15:PSET(1,0),4",            (0, 0), "80", "f4"),
    ("preset_erase",  "PSET(0,0),15:PRESET(0,0)",            (0, 0), "00", "f4"),
    ("preset_color",  "PRESET(0,0),6",                       (0, 0), "80", "64"),
    ("pset_step",     "PSET(0,0),15:PSET STEP(1,0),9",       (0, 0), "c0", "94"),
    ("pset_mid",      "PSET(100,50),9",                      (100, 50), "08", "94"),
    ("pset_default",  "PSET(0,0)",                           (0, 0), "80", "f4"),  # c=FORCLR=15
    ("clip_noop",     "PSET(300,100):PSET(0,192):PSET(-1,0)",(0, 0), "00", "04"),
]


def phase_a() -> int:
    fails = 0
    print("=== PHASE A: pixel + colour plane differential (VG-8020 vs zerobas) ===")
    for label, ops, (x, y), ep, ec in DRAW_CASES:
        pa = paddr(x, y)
        segs = [(pa, 1), (pa + 0x2000, 1)]
        specs = [("stored", prog([INIT, ops]))]
        ref = omsx_repl.run_cases(REF, specs, batch=False, capture=("vram_segs", segs))[0]
        zb = omsx_repl.run_cases(ZB, specs, batch=False, capture=("vram_segs", segs))[0]
        ok = ref is not None and ref == zb
        note = "" if (zb and zb[:2] == ep and zb[2:4] == ec) else f"  [oracle {ep}{ec}]"
        fails += not ok
        rp = f"{ref[:2]}/{ref[2:4]}" if ref else "None"
        zp = f"{zb[:2]}/{zb[2:4]}" if zb else "None"
        print(f"  {'PASS' if ok else 'FAIL'} {label:14} ref={rp} zb={zp}{note}")
    return fails


# label, program lines, tag whose numeric answer we compare
BEHAV_CASES = [
    ("pset_scr0_err", ["ON ERROR GOTO 40", "SCREEN0:PSET(0,0)",
                       'PRINT"OK":END', 'PRINT"E";ERR:END'], "E"),
    ("pset_ovf_err",  ["ON ERROR GOTO 40", "SCREEN2:PSET(32768,0)",
                       'PRINT"OK":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    ("pset_offscr_ok",["ON ERROR GOTO 40", "SCREEN2:PSET(300,100)",
                       'SCREEN0:PRINT"OK":END', 'PRINT"E";ERR:END'], "OK"),
    ("point_vals",    ["SCREEN2:COLOR15,4:PSET(50,50),9",
                       "A=POINT(50,50):B=POINT(51,50):C=POINT(300,300)",
                       'SCREEN0:PRINT"P";A;B;C'], "P"),
    ("point_step",    ["SCREEN2:COLOR15,4:PSET(50,50),9", "D=POINT STEP(0,0)",
                       'SCREEN0:PRINT"S";D'], "S"),
]


def _answer(raw: str | None, tag: str) -> str | None:
    """Extract `tag` and the numeric answer following it (digits/spaces/minus),
    stopping at the first other letter -- so the trailing BASIC prompt / 'Ok' /
    'No RESUME' text (which differs per machine) is ignored."""
    if not raw:
        return None
    txt = " ".join("".join(raw).split())
    m = re.search(re.escape(tag) + r"[ \d\-]*", txt)
    return re.sub(r"\s+", " ", m.group(0)).strip() if m else None


def phase_b() -> int:
    fails = 0
    print("=== PHASE B: behavioural differential (clip / errors / POINT / STEP) ===")
    specs = [("stored", body) for _, body, _ in BEHAV_CASES]
    ref = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW", "CLS"))
    zb = omsx_repl.run_cases(ZB, specs, batch=True, reset=("NEW", "CLS"))
    for (label, _, tag), r, z in zip(BEHAV_CASES, ref, zb):
        ra, za = _answer(r, tag), _answer(z, tag)
        ok = ra is not None and ra == za
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {label:16} ref={ra!r} zb={za!r}")
    return fails


def main() -> int:
    fails = phase_a() + phase_b()
    print("-------------------")
    print("graphics-acceptance:", "PASS" if fails == 0 else f"FAIL ({fails})")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
