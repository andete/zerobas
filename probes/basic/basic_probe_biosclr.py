#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-BIOSCONTRACT2: what INITXT / INIT32 / INIGRP / INIMLT ($006C / $006F / $0072 / $0075)
and CLS ($00C3, in each of SCREEN 0..3) leave in VRAM -- the VG-8020 against zerobas.

biosmode / biosvdp compare these entries' work area and VDP registers; the VRAM they clear or
fill was never read. Each row: our code fills ALL 16 KB of VRAM with $55 (FILVRM), calls the
entry, and the program then loops, so BASIC's prompt cannot touch VRAM before the capture of
all 16 KB. Compared: every byte except the FONT the text modes load (SCREEN 0: $0800-$0FFF,
SCREEN 1: $0000-$07FF) -- the C-BIOS font is not the VG-8020's, by design.
FORCLR / BAKCLR / BDRCLR are set first (4 / 1 / 6), so the colour table is deterministic.
Black box: VRAM through the debugger, no ROM byte.

    python3 -u probes/basic/basic_probe_biosclr.py [ROW ...]      (`make biosclr-acceptance`)
Exit 0 all SAME; 1 a divergence; 2 the VG-8020 gave no reading.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))
FILVRM = 0x0056
# name -> (entry, the font range excluded or None)
ROWS = {"initxt": (0x006C, (0x0800, 0x1000)), "init32": (0x006F, (0x0000, 0x0800)),
        "inigrp": (0x0072, None), "inimlt": (0x0075, None)}
# CLS ($00C3, Z set) in each mode: the mode's INIT entry FIRST, then the $55 fill, then CLS --
# what CLS itself clears (D-BIOSCONTRACT2, 2026-11-16: only the text modes were compared)
CLS = 0x00C3
CLS_ROWS = {"cls0": (0x006C, (0x0800, 0x1000)), "cls1": (0x006F, (0x0000, 0x0800)),
            "cls2": (0x0072, None), "cls3": (0x0075, None)}
COLORS = "POKE &HF3E9,4:POKE &HF3EA,1:POKE &HF3EB,6"
# GRPPRT ($008D) after INIGRP / INIMLT, GRPACX / GRPACY ($FCB7 / $FCB9) set first. ONLY
# characters whose 8 font bytes are IDENTICAL in both machines' fonts (read back from VRAM
# after INITXT: scratchpad/GP_font.out, 44 non-blank), so the glyph source cannot split.
GRPPRT, GRPACX, GRPACY = 0x008D, 0xFCB7, 0xFCB9
GRP_ROWS = {"gp2_plus": (0x0072, 0x2B, 10, 13), "gp2_edge": (0x0072, 0xDB, 250, 190),
            "gp2_c5": (0x0072, 0xC5, 100, 96), "gp3_plus": (0x0075, 0x2B, 10, 13)}


def grp_code(init, ch, x, y):
    # the $55 fill FIRST, as every other row: INIMLT leaves $0600.. alone, so without it the
    # machines' leftover VRAM showed through (scratchpad/GP_run1.out's gp3_plus)
    fill = [0x21, 0, 0, 0x01, 0x00, 0x40, 0x3E, 0x55, 0xCD, FILVRM & 255, FILVRM >> 8]
    return (fill + [0xCD, init & 255, init >> 8,
             0x21, x & 255, x >> 8, 0x22, GRPACX & 255, GRPACX >> 8,
             0x21, y & 255, y >> 8, 0x22, GRPACY & 255, GRPACY >> 8,
             0x3E, ch, 0xCD, GRPPRT & 255, GRPPRT >> 8, 0xC9])


def code(entry, cls=False):
    # [call ENTRY] / ld hl,0 / ld bc,$4000 / ld a,$55 / call FILVRM / call ENTRY |
    # (xor a / call CLS) / ret
    fill = [0x21, 0, 0, 0x01, 0x00, 0x40, 0x3E, 0x55, 0xCD, FILVRM & 255, FILVRM >> 8]
    if cls:
        return [0xCD, entry & 255, entry >> 8] + fill + [0xAF, 0xCD, CLS & 255, CLS >> 8, 0xC9]
    return fill + [0xCD, entry & 255, entry >> 8, 0xC9]


def read(machine, entry, cls=False, c=None):
    c = c or code(entry, cls)
    prog = ["NEW", "10 CLEAR 200,&HCFFF:" + COLORS,
            f"20 FOR I=0 TO {len(c) - 1}:READ X:POKE &HD000+I,X:NEXT",
            "30 DEFUSR=&HD000:Q=USR(0)", "40 GOTO 40",
            "50 DATA " + ",".join(str(b) for b in c), "RUN"]
    h = omsx_repl.run_cases(machine, [("direct", prog)], batch=False, capture=("vram", 0, 16384),
                            reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=10.0)[0]
    return bytes.fromhex(h) if h and len(h) == 32768 else None


def runs(diff):
    """Contiguous runs of differing addresses, as `$aaaa-$bbbb`."""
    out, start, prev = [], None, None
    for a in diff:
        if start is None:
            start = prev = a
        elif a == prev + 1:
            prev = a
        else:
            out.append((start, prev))
            start = prev = a
    if start is not None:
        out.append((start, prev))
    return out


def main():
    only = sys.argv[1:] or list(ROWS) + list(CLS_ROWS) + list(GRP_ROWS)
    bad = blind = 0
    for name in only:
        if name in GRP_ROWS:
            font = None
            gc = grp_code(*GRP_ROWS[name])
            got = {side: read(m, 0, c=gc) for side, m in MACHINES}
        else:
            entry, font = ROWS.get(name) or CLS_ROWS[name]
            got = {side: read(m, entry, name in CLS_ROWS) for side, m in MACHINES}
        if got["VG"] is None or got["ZB"] is None:
            blind += 1
            print(f"ROW {name:7} NO-READING", flush=True)
            continue
        skip = range(*font) if font else range(0)
        diff = [a for a in range(16384) if a not in skip and got["VG"][a] != got["ZB"][a]]
        if diff:
            bad += 1
            rs = runs(diff)
            shown = ", ".join(f"${a:04X}-${b:04X} VG {got['VG'][a]:02X} ZB {got['ZB'][a]:02X}"
                              for a, b in rs[:6])
            print(f"ROW {name:7} DIVERGES: {len(diff)} B in {len(rs)} run(s): {shown}"
                  f"{' ...' if len(rs) > 6 else ''}", flush=True)
        else:
            print(f"ROW {name:7} SAME ({16384 - len(skip)} B compared)", flush=True)
    if blind:
        print("INSTRUMENT FAULT: a side gave no reading")
        return 2
    print(f"{'PASS' if not bad else 'FAIL'}: the VRAM the mode entries leave ({len(only) - bad}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
