#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-GRPHEDCLS: which BIOS entries end a pending graphic header -- GRPHED ($FCA6, CNVCHR's
state after a $01) -- the VG-8020 against zerobas.

Each row: our code sets GRPHED := 1, calls the entry directly, stores GRPHED, clears it, and
BASIC prints the stored value. On the VG-8020 the TEXT-mode clear ends a pending header
(INITXT, INIT32, CHGMOD 0 / 1, a text CLS -> 0) and nothing else does (INIGRP, INIMLT,
TOTEXT, SETTXT, SETT32, ERAFNK, KILBUF -> 1; scratchpad/CV_grphed2.out). C-BIOS kept it,
so after a CNVCHR header the next character BASIC printed was taken as graphic. Black box:
one work-area cell.

    python3 -u probes/basic/basic_probe_grphed.py [ROW ...]      (`make grphed-acceptance`)
Exit 0 all SAME; 1 a divergence; 2 the VG-8020 gave no reading.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))
GRPHED = 0xFCA6
# name -> (entry, A input or None, "z" = enter with Z set (CLS's input))
ROWS = {"initxt": (0x006C, None), "init32": (0x006F, None), "inigrp": (0x0072, None),
        "inimlt": (0x0075, None), "chgmod0": (0x005F, 0), "chgmod1": (0x005F, 1),
        "totext": (0x00D2, None), "settxt": (0x0078, None), "sett32": (0x007B, None),
        "cls": (0x00C3, "z"), "erafnk": (0x00CC, None), "kilbuf": (0x0156, None)}


def code(entry, arg):
    c = [0x3E, 1, 0x32, GRPHED & 255, GRPHED >> 8]          # GRPHED := 1
    if arg == "z":
        c += [0xAF]                                          # xor a: Z set
    elif arg is not None:
        c += [0x3E, arg]
    return c + [0xCD, entry & 255, entry >> 8,
                0x3A, GRPHED & 255, GRPHED >> 8, 0x32, 0x00, 0xD1,   # ($D100) := GRPHED
                0xAF, 0x32, GRPHED & 255, GRPHED >> 8, 0xC9]       # GRPHED := 0, ret


def read(machine, c):
    prog = ["NEW", "10 CLEAR 200,&HCFFF",
            f"20 FOR I=0 TO {len(c) - 1}:READ X:POKE &HD000+I,X:NEXT",
            '30 DEFUSR=&HD000:Q=USR(0):SCREEN 0:PRINT "[G";PEEK(&HD100);"]"',
            "50 DATA " + ",".join(str(b) for b in c), "RUN"]
    raw = omsx_repl.run_cases(machine, [("direct", prog)], batch=False, reset=("", "SCREEN 0"),
                              step=3.0, run_gap=8.0)[0] or ""
    m = re.findall(r"\[G\s*(\d+)\s*\]", re.sub(r"\s+", " ", raw))
    return int(m[-1]) if m else None


def main():
    only = sys.argv[1:] or list(ROWS)
    bad = blind = 0
    for name in only:
        got = {side: read(m, code(*ROWS[name])) for side, m in MACHINES}
        if got["VG"] is None:
            verdict, blind = "NO-REFERENCE", blind + 1
        else:
            verdict = "SAME" if got["ZB"] == got["VG"] else "DIVERGES"
            bad += verdict == "DIVERGES"
        print(f"ROW {name:8} VG={got['VG']} ZB={got['ZB']} {verdict}", flush=True)
    if blind:
        print("INSTRUMENT FAULT: the VG-8020 gave no reading")
        return 2
    print(f"{'PASS' if not bad else 'FAIL'}: GRPHED after the screen entries ({len(only) - bad}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
