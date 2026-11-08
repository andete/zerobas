#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ENTRYTIERS (step 5's next list): main BIOS calls the entry table counts NOT
MEASURED, called DIRECTLY -- VG-8020 against zerobas.

Reuses probes/basic/basic_probe_biosregs.py's stub (our own code: A / BC / DE / HL
loaded, the entry called, HL / DE / BC / A stored and printed; F not compared -- no
documented contract). A first batch of SAFE entries only: no tape, no format, no
slot switching, nothing that waits for input or loops. Graphics-cursor helpers run
in SCREEN 2 and print after SCREEN 0, the biosregs `S1` way.

    python3 -u scratchpad/biossweep_probe.py [ROW ...]
"""
import os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import basic_probe_biosregs as B   # noqa: E402  (prog, read, MACHINES)

S2 = dict(before="SCREEN 2", after="SCREEN 0")
ROWS = {
    "wrtvrm":  B.prog(0x004D, 0x5A, hl=0x3F10),
    "rdvrm":   B.prog(0x004A, 0, hl=0x3F10, before="VPOKE &H3F10,&H5A"),
    "setrd":   B.prog(0x0050, 0, hl=0x3F10),
    "setwrt":  B.prog(0x0053, 0, hl=0x3F10),
    "filvrm":  B.prog(0x0056, 0x33, bc=4, hl=0x3F20),
    "chgclr":  B.prog(0x0062, 0),
    "gtstck0": B.prog(0x00D5, 0),
    "gtstck1": B.prog(0x00D5, 1),
    "gttrig0": B.prog(0x00D8, 0),
    "gttrig1": B.prog(0x00D8, 1),
    "gtpdl1":  B.prog(0x00DE, 1),
    "gtpad0":  B.prog(0x00DB, 0),
    "rdpsg7":  B.prog(0x0096, 7),
    "chsns":   B.prog(0x009C, 0),
    "cnvchr":  B.prog(0x00AB, 0x41),
    "posit":   B.prog(0x00C6, 0, hl=0x0505),
    "snsmat0": B.prog(0x0141, 0),
    "snsmat8": B.prog(0x0141, 8),
    "rslreg":  B.prog(0x0138, 0),
    "rdvdp":   B.prog(0x013E, 0),
    "lptstt":  B.prog(0x00A8, 0),
    "kilbuf":  B.prog(0x0156, 0),
    "isflio":  B.prog(0x014A, 0),
    "breakx":  B.prog(0x00B7, 0),
    "scalxy":  B.prog(0x010E, 0, bc=300, de=200, **S2),
    "mapxyc":  B.prog(0x0111, 0, bc=10, de=10, **S2),
    "fetchc":  B.prog(0x0114, 0, **S2),
    "upc":     B.prog(0x0102, 0, **S2),
    "downc":   B.prog(0x0108, 0, **S2),
    "leftc":   B.prog(0x00FF, 0, **S2),
    "rightc":  B.prog(0x00FC, 0, **S2),
    "gtaspc":  B.prog(0x0126, 0, **S2),
    "readc":   B.prog(0x011D, 0, **S2),
    "setatr":  B.prog(0x011A, 5, **S2),
    # SCALXY's clipping, for the D-BIOSCONTRACT fix: in range, both negative, both over;
    # SCREEN 2 and SCREEN 3 (multicolour, 64 x 48)
    "sxy2in":  B.prog(0x010E, 0, bc=100, de=100, **S2),
    "sxy2neg": B.prog(0x010E, 0, bc=0xFFFB, de=0xFFFB, **S2),
    "sxy3over": B.prog(0x010E, 0, bc=300, de=200, before="SCREEN 3", after="SCREEN 0"),
    "sxy3in":  B.prog(0x010E, 0, bc=100, de=100, before="SCREEN 3", after="SCREEN 0"),
    "gtaspc0": B.prog(0x0126, 0),
    "sxy2xov": B.prog(0x010E, 0, bc=300, de=100, **S2),
    "sxy2yov": B.prog(0x010E, 0, bc=100, de=200, **S2),
    # the aspect cells GTASPC returns, read straight from RAM (HL = $F40B, DE = $F40D)
    "aspct":   B.prog(0x0000 + 0x0020, 0, de=0, hl=0, before="POKE &HD200,0",
                      after='PRINT "[ASP";HEX$(PEEK(&HF40B)+256*PEEK(&HF40C));HEX$(PEEK(&HF40D)+256*PEEK(&HF40E));"]"'),
}


def main():
    only = sys.argv[1:] or list(ROWS)
    bad, blind = [], []
    for name in only:
        got = {side: B.read(m, ROWS[name]) for side, m in B.MACHINES}
        if not got["VG"]:
            verdict = "NO-REFERENCE"
            blind.append(name)
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name:8} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    print(f"\n{len(only) - len(bad) - len(blind)} SAME, {len(bad)} DIVERGE"
          + (f" ({', '.join(bad)})" if bad else "")
          + (f", {len(blind)} no reference reading ({', '.join(blind)})" if blind else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
