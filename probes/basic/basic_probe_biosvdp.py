#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSCONTRACT2 gap 5: the VDP's OWN registers after the BIOS's mode / screen entries,
the VG-8020 against zerobas.

biosregs / biosmode compare those entries through their RAM shadows (RG0SAV..RG7SAV) only;
a shadow can be right while the chip is not (scratchpad/bios_contract_inventory.md). Each
row calls one entry through biosregs' USR stub and then LOOPS (`GOTO`), so BASIC's prompt
cannot reset the mode before the capture; the capture is the VDP's R0..R7 through openMSX's
`vdpreg` (the emulated chip's state -- no ROM byte read).

    python3 -u probes/basic/basic_probe_biosvdp.py [ROW ...]   (`make biosvdp-acceptance`)
Exit 0 SAME; 1 a divergence; 2 the VG-8020 gave no reading.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import omsx_repl  # noqa: E402
from basic_probe_biosregs import stub  # noqa: E402  (the same USR caller)

MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))
# name -> (entry, A, BC, a BASIC prelude). FORCLR / BAKCLR / BDRCLR = $F3E9..$F3EB.
COLORS = "POKE &HF3E9,4:POKE &HF3EA,1:POKE &HF3EB,6"
ROWS = {
    "disscr":  (0x0041, 0, 0x1122, ""),
    "enascr":  (0x0044, 0, 0x1122, "SCREEN 1"),
    "wrtvdp7": (0x0047, 0, 0x5A07, ""),              # B = $5A -> R7 (C = 7): NOT R7's
                                                     # default ($F4), so a WRTVDP that did
                                                     # nothing would read differently
    "chgmod0": (0x005F, 0, 0x1122, ""),
    "chgmod1": (0x005F, 1, 0x1122, ""),
    "chgmod2": (0x005F, 2, 0x1122, ""),
    "chgmod3": (0x005F, 3, 0x1122, ""),
    "initxt":  (0x006C, 0, 0x1122, COLORS),
    "init32":  (0x006F, 0, 0x1122, COLORS),
    "inigrp":  (0x0072, 0, 0x1122, COLORS),
    "inimlt":  (0x0075, 0, 0x1122, COLORS),
    "settxt":  (0x0078, 0, 0x1122, ""),
    "sett32":  (0x007B, 0, 0x1122, ""),
    "setgrp":  (0x007E, 0, 0x1122, ""),
    "setmlt":  (0x0081, 0, 0x1122, ""),
    "totext":  (0x00D2, 0, 0x1122, "SCREEN 2"),
    "chgclr":  (0x0062, 0, 0x1122, COLORS),
}


def prog(addr, a, bc, before):
    s = stub(addr, a, bc, 0x3344, 0x5566)
    return ["NEW",
            "10 CLEAR 200,&HCFFF" + (":" + before if before else ""),
            f"20 FOR I=0 TO {len(s) - 1}:READ X:POKE &HD000+I,X:NEXT",
            "30 DEFUSR=&HD000:Q=USR(0)",
            "40 GOTO 40",
            "60 DATA " + ",".join(str(b) for b in s),
            "RUN"]


def read(machine, p):
    return omsx_repl.run_cases(machine, [("direct", p)], batch=False, capture=("vdpregs",),
                               reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=8.0)[0]


def main():
    only = sys.argv[1:] or list(ROWS)
    bad, blind = [], []
    for name in only:
        got = {side: read(m, prog(*ROWS[name])) for side, m in MACHINES}
        if not got["VG"]:
            blind.append(name)
            verdict = "NO-REFERENCE"
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print(f"\nNO READING on the VG-8020: {' '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: the VDP registers after the BIOS mode / screen "
          f"entries ({len(only) - len(bad)}/{len(only)}){'; differ: ' + ' '.join(bad) if bad else ''}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
