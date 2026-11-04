#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-CURGEO — which name table the line editor's block cursor is drawn in.

sub/cursor.asm draws the cursor as character 255 in the cell at CSRY/CSRX. The
question this probe answers is WHICH name table that cell is in when the
published table-base cell (TXTNAM in SCREEN 0, T32NAM in SCREEN 1) has been
POKEd without a SCREEN statement, so that it no longer names the table on
screen (NAMBAS, which only SCREEN / INITXT / INIT32 rewrite).

MEASURED 2026-11-04 on the Philips VG-8020 and the National CF-3300: both draw
the cursor -- and PRINT -- in the NAMBAS table, the one on screen, and leave the
POKEd table untouched. zerobas drew the cursor at TXTNAM/T32NAM + offset until
D-CURGEO: no visible cursor, and a stray $FF in a table nobody displays.

ROWS (per screen mode): `ctrl` (no POKE) and `poke` (the POKE, then LOCATE/PRINT
on the SAME line) and `poke2` (the POKE on its own line, so a whole prompt
cycle runs between the POKE and the read). Each reads, as VRAM only:
  * QZ@n     -- where `PRINT CHR$(81);CHR$(90)` landed in the VISIBLE table (a
               positive control that the case ran, and the PRINT half of the
               measurement);
  * vis[...] -- cells holding $FF in the visible table (the cursor, if drawn
               there: one cell, the row below `Ok`);
  * alt[...] -- cells holding $FF in the POKEd table's window ($1000 / $1400,
               unused VRAM in both modes).
The `ctrl` rows read alt[] at the same address, so a stray write there is
visible in the control too.

🔴 A CONTROL FAILING ON A REFERENCE IS A BROKEN FIXTURE, NOT A RESULT
([[classify-a-control-failure-by-which-side-failed-it]]). The CF-3300 boots
into Disk BASIC and needs a blank FAT12 disk in drive A, or its first typed
lines are lost and the case runs in the wrong mode (seen while measuring). If a
reference's `ctrl` row lacks the QZ or the cursor, exit 2 and score nothing.

Clean-room: VRAM read back only; both reference ROMs are black boxes.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_repl                                                 # noqa: E402
import probe_report                                              # noqa: E402
import probe_tmp                                                 # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
TEST_DSK = os.path.join(REPO, "disk", "test720.dsk")

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, pre=(), diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, pre=("",),
                   diska=True),
    "zb":     dict(machine="C-BIOS_MSX1_EU_REPACK_DISK", boot=10.0,
                   pre=("",), diska=True),
    "zbnd":   dict(machine="C-BIOS_MSX1_EU_REPACK_NODISK", boot=10.0,
                   pre=(), diska=False),
}
REFS = ("vg8020", "cf3300")

MK = "CHR$(81);CHR$(90);"        # 'QZ' printed, never typed (the echo has no QZ)
# label -> (visible table, POKEd window, pitch-mode lines)
S0 = ("SCREEN 0:WIDTH 40",)
S1 = ("SCREEN 1:WIDTH 32",)
CASES = [
    ("s0.ctrl",  0x0000, 0x1000, S0 + (f"LOCATE 5,10:PRINT {MK}",)),
    ("s0.poke",  0x0000, 0x1000,
     S0 + (f"POKE &HF3B3,0:POKE &HF3B4,&H10:LOCATE 5,10:PRINT {MK}",)),
    ("s0.poke2", 0x0000, 0x1000,
     S0 + ("POKE &HF3B3,0:POKE &HF3B4,&H10", f"LOCATE 5,10:PRINT {MK}")),
    ("s1.ctrl",  0x1800, 0x1400, S1 + (f"LOCATE 5,10:PRINT {MK}",)),
    ("s1.poke",  0x1800, 0x1400,
     S1 + (f"POKE &HF3BD,0:POKE &HF3BE,&H14:LOCATE 5,10:PRINT {MK}",)),
    ("s1.poke2", 0x1800, 0x1400,
     S1 + ("POKE &HF3BD,0:POKE &HF3BE,&H14", f"LOCATE 5,10:PRINT {MK}")),
]
CONTROLS = ("s0.ctrl", "s1.ctrl")
WIN = 960                       # a SCREEN 0 table's used bytes (>= SCREEN 1's 768)
LABEL_W = 9
SENTINELS = ("<NO CAPTURE>",)


def reading(raw: str | None) -> str:
    if not raw:
        return "<NO CAPTURE>"
    b = bytes.fromhex(raw)
    vis, alt = b[:WIN], b[WIN:2 * WIN]
    qz = [i for i in range(WIN - 1) if vis[i] == 81 and vis[i + 1] == 90]
    ff = lambda t: [i for i in range(WIN) if t[i] == 0xFF]
    return (f"QZ@{','.join(map(str, qz)) or '-'} vis{ff(vis)} alt{ff(alt)}")


def run_side(side: str, only: list[str]) -> dict:
    cfg = SIDES[side]
    out = {}
    for label, vis, alt, lines in CASES:
        if only and label not in only:
            continue
        kw = {}
        if cfg["diska"]:
            # A fresh copy per case: nothing is written, but no case may
            # inherit another's image ([[test-disk-mutation-gotcha]]).
            dsk = probe_tmp.tmp(f"zb_curgeo_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", list(cfg["pre"]) + list(lines))],
            batch=False, reset=(), boot=cfg["boot"],
            capture=("vram_segs", [(vis, WIN), (alt, WIN)]),
            verify_delivery=False, **kw)
        out[label] = reading(caps[0])
    return out


def control_ok(v: str | None) -> bool:
    # the case ran (QZ printed) and a cursor is up somewhere visible
    return bool(v) and not v.startswith("QZ@-") and "vis[]" not in v \
        and v not in SENTINELS


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-CURGEO: the block cursor's name table after a POKEd "
                    "TXTNAM / T32NAM")
    ap.add_argument("--sides", default="vg8020,cf3300,zb,zbnd")
    ap.add_argument("--only", default="")
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless every zerobas row matches the references")
    a = ap.parse_args()
    sides = [s for s in a.sides.split(",") if s]
    only = [o for o in a.only.split(",") if o]
    for s in sides:
        if s not in SIDES:
            sys.stderr.write(f"unknown side {s!r}\n")
            return 2

    results = {s: run_side(s, only) for s in sides}
    present = [lab for lab, _, _, _ in CASES
               if any(lab in results[s] for s in sides)]
    print("D-CURGEO — the block cursor's name table (VRAM: QZ = the PRINT, "
          f"vis/alt = $FF cells)   sides: {', '.join(sides)}")
    print("=" * 78)

    bad = [(c, s, results[s].get(c)) for c in CONTROLS if c in present
           for s in sides if s in REFS and not control_ok(results[s].get(c))]
    if bad:
        for lab, s, got in bad:
            print(probe_report.row("FAIL", lab, LABEL_W, {s: got},
                                   "   [POSITIVE CONTROL]"))
        print("\n*** A REFERENCE's control row has no PRINT or no cursor: the "
              "fixture is broken\n    (a CF-3300 without its disk loses the "
              "first lines). Exit 2 = NOT MEASURED.")
        print(probe_report.footer(len(present), 0,
                                  "NOT MEASURED (a positive control failed)"))
        return 2

    agree = dis = noref = 0
    zbs = [s for s in sides if s not in REFS]
    for lab in present:
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        refs = {s: v for s, v in vals.items()
                if s in REFS and v not in SENTINELS}
        note = "   [POSITIVE CONTROL]" if lab in CONTROLS else ""
        if not refs:
            noref += 1
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   "   [NO REFERENCE ON ANY REQUESTED SIDE]"))
            continue
        if len(set(refs.values())) > 1:
            dis += 1
            print(probe_report.row("DIFF", lab, LABEL_W, vals,
                                   note + "   [REFERENCES DISAGREE — no oracle]"))
            continue
        oracle = next(iter(refs.values()))
        ok = all(vals.get(z) == oracle for z in zbs) and bool(zbs)
        agree += ok
        dis += not ok
        print(probe_report.row("ok" if ok else "DIFF", lab, LABEL_W, vals, note))

    print(probe_report.footer(len(present), len(present) - noref,
                              f"{agree} agree, {dis} diverge, "
                              f"{noref} without a reference"))
    print("=" * 78)
    print("DENOMINATOR: (mode: SCREEN 0 / SCREEN 1) x (POKE: none / same line / "
          "own line), each read as PRINT position + $FF cells in the visible and "
          "the POKEd table, on both references and both zerobas builds.")
    print("NOT COVERED, named rather than implied: a POKEd TXTCGP/T32CGP (the "
          "cursor's PATTERN half), a POKEd NAMBAS itself, and WIDTH other than "
          "40 / 32.")
    if a.gate and dis:
        sys.stderr.write(f"curgeo: {dis} row(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
