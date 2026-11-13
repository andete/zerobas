#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ENTRYTIERS step 3: the screen-mode BIOS entries answer in the WORK AREA -- compared
there, the VG-8020 against zerobas. INITXT / INIT32 / INIGRP / INIMLT, SETTXT / SETT32 /
SETGRP / SETMLT and CHGMOD (A = 0..3) leave their result in RAM: SCRMOD, the VDP register
shadows RG0SAV..RG7SAV, NAMBAS / CGPBAS / PATBAS / ATRBAS and the per-mode table
addresses. biosregs-acceptance reads registers only.

Our code calls the entry from SCREEN 0 (BASIC's own `SCREEN 0` first, so every row starts
from the same state) and copies the ranges below BEFORE the call and again after it,
before returning to BASIC. A row DIVERGES on a byte either machine's call changed whose
value after differs; bytes neither call touched but that already differ are listed apart
(the starting state, not the entry's answer):
  $F3B0..$F3E6 (55 B: LINL40, LINL32, LINLEN, CRTCNT, CLMLST, TXTNAM .. GRPATR, CLIKSW,
               CSRY, CSRX, CNSDFG, RG0SAV .. RG7SAV)
  $F922..$F92B (10 B: NAMBAS, CGPBAS, PATBAS, ATRBAS, CLOC)   -- CLOC/CMASK left out below
  $FCAF..$FCB0 (2 B: SCRMOD, OLDSCR)
to $D100.., then BASIC returns to SCREEN 0 and prints them in hex. Compared byte by byte;
the differing addresses are named. Black box: work-area RAM only.

    python3 -u probes/basic/basic_probe_biosmode.py [ROW ...]      (`make biosmode-acceptance`)
Exit 0 all SAME; 1 a divergence; 2 the VG-8020 gave no reading.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))
RANGES = [(0xF3B0, 55), (0xF922, 8), (0xFCAF, 2)]
ADDRS = [a + i for a, n in RANGES for i in range(n)]
ENTRIES = {"initxt": (0x006C, 0), "init32": (0x006F, 0), "inigrp": (0x0072, 0),
           "inimlt": (0x0075, 0), "settxt": (0x0078, 0), "sett32": (0x007B, 0),
           "setgrp": (0x007E, 0), "setmlt": (0x0081, 0),
           "chgmod0": (0x005F, 0), "chgmod1": (0x005F, 1), "chgmod2": (0x005F, 2),
           "chgmod3": (0x005F, 3)}


def _copy(dst):
    c = []
    for src, n in RANGES:                       # ld hl,src / ld de,dst / ld bc,n / ldir
        c += [0x21, src & 255, src >> 8, 0x11, dst & 255, dst >> 8, 0x01, n, 0, 0xED, 0xB0]
        dst += n
    return c


def code(entry, a):
    # the work area BEFORE the call -> $D180.., after -> $D100..
    return _copy(0xD180) + [0x3E, a, 0xCD, entry & 255, entry >> 8] + _copy(0xD100) + [0xC9]


def prog(c):
    n = len(ADDRS)
    return ["NEW", "10 SCREEN 0:CLEAR 200,&HCFFF",
            f"20 FOR I=0 TO {len(c) - 1}:READ X:POKE &HD000+I,X:NEXT",
            "30 DEFUSR=&HD000:Q=USR(0):SCREEN 0:WIDTH 40",
            f'40 FOR B=0 TO 128 STEP 128:FOR J=0 TO {n - 1} STEP 20:S$="":FOR I=J TO J+19:IF I<{n} THEN '
            'S$=S$+RIGHT$("0"+HEX$(PEEK(&HD100+B+I)),2)',
            '50 NEXT:PRINT "[M";B+J;S$;"]":NEXT:NEXT',
            "60 DATA " + ",".join(str(b) for b in c), "RUN"]


def read(machine, c):
    raw = omsx_repl.run_cases(machine, [("direct", prog(c))], batch=False,
                              reset=("", "SCREEN 0"), step=3.0, run_gap=10.0)[0] or ""
    t = re.sub(r"\s+", " ", raw)
    parts = {}
    for j, hx in re.findall(r"\[M\s*(\d+)\s+([0-9A-F]+)\s*\]", t):
        parts[int(j)] = bytes.fromhex(hx)
    after = b"".join(parts[k] for k in sorted(parts) if k < 128)
    before = b"".join(parts[k] for k in sorted(parts) if k >= 128)
    n = len(ADDRS)
    return (before, after) if len(after) == n and len(before) == n else None


def main():
    only = sys.argv[1:] or list(ENTRIES)
    bad = blind = 0
    for name in only:
        entry, a = ENTRIES[name]
        got = {side: read(m, code(entry, a)) for side, m in MACHINES}
        if got["VG"] is None:
            blind += 1
            print(f"ROW {name:8} NO-REFERENCE (ZB {'read' if got['ZB'] else 'none'})", flush=True)
            continue
        if got["ZB"] is None:
            bad += 1
            print(f"ROW {name:8} DIVERGES (zerobas gave no reading)", flush=True)
            continue
        (vb, va), (zb, za) = got["VG"], got["ZB"]
        # the CALL's answer: every byte either machine's call changed -- they must agree on
        # the value after. A byte neither call touched is the starting state, reported apart.
        call = [(ADDRS[i], va[i], za[i]) for i in range(len(ADDRS))
                if (va[i] != vb[i] or za[i] != zb[i]) and va[i] != za[i]]
        state = [(ADDRS[i], va[i], za[i]) for i in range(len(ADDRS))
                 if va[i] == vb[i] and za[i] == zb[i] and va[i] != za[i]]
        bad += bool(call)
        print(f"ROW {name:8} {'SAME' if not call else 'DIVERGES'} "
              + " ".join(f"${a:04X}:VG{v:02X}/ZB{z:02X}" for a, v, z in call)
              + ("   (untouched, already apart: " + " ".join(f"${a:04X}:VG{v:02X}/ZB{z:02X}"
                                                         for a, v, z in state) + ")" if state else ""),
              flush=True)
    if blind:
        print("INSTRUMENT FAULT: the VG-8020 gave no reading")
        return 2
    print(f"{'PASS' if not bad else 'FAIL'}: the screen-mode entries' work area "
          f"({len(only) - bad}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
