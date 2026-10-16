#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CALATR (2026-10-16, Demonia's sprites): which registers do the BIOS sprite
helpers CALATR ($0087), CALPAT ($0084) and GSPSIZ ($008A) keep? Demonia's title
screen places sprites with CALATR + WRTVRM, and zerobas's sprite Y/X bytes came
out different from the VG-8020's while every other VRAM and game-RAM byte agreed
(scratchpad/tapes, D-BASICINT2 triage). C-BIOS's CALATR loads DE itself.

Black-box, our own stub: BC=$1122 DE=$3344 HL=$5566, A = the sprite number, call
the entry, store HL / DE / BC / AF, print them. The VG-8020's printed line is the
oracle (no ROM byte is read).
  atr    CALATR, A=5
  pat8   CALPAT, A=5, 8x8 sprites (SCREEN 0)
  pat16  CALPAT, A=5, 16x16 sprites (SCREEN 0,2)
  siz    GSPSIZ with 16x16 sprites
  rdvrm .. calatr2  every other BIOS entry Demonia calls, with safe arguments
Each line prints HL DE BC AF. ⚠️ Its DIFF verdict includes F (AF's low byte), which
no row matches and neither machine documents: read the first three fields. The
gate, probes/basic/basic_probe_biosregs.py, compares A / BC / DE / HL only, and
runs the sprite rows in SCREEN 1 -- in SCREEN 0 zerobas's ATRBAS / PATBAS read 0
(the HL here: $14 against $1B14), filed as D-SPRBASE0.
"""
import os, sys
ONLY = sys.argv[1:]
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "probes", "lib"))
import omsx_repl


def stub(addr, a, bc=0x1122, de=0x3344, hl=0x5566):
    return [0x01, bc & 255, bc >> 8, 0x11, de & 255, de >> 8, 0x21, hl & 255, hl >> 8, 0x3E, a,
            0xCD, addr & 255, addr >> 8,
            0x22, 0x00, 0xD1, 0xED, 0x53, 0x02, 0xD1, 0xED, 0x43, 0x04, 0xD1,
            0xF5, 0xE1, 0x22, 0x06, 0xD1, 0xC9]


def prog(addr, a, scr="SCREEN 0", **regs):
    s = stub(addr, a, **regs)
    data = ",".join(str(b) for b in s)
    return ["NEW",
            "10 CLEAR 200,&HCFFF:" + scr,
            f"20 FOR I=0 TO {len(s) - 1}:READ X:POKE &HD000+I,X:NEXT",
            "30 DEFUSR=&HD000:A=USR(0)",
            '40 S$="":FOR I=0 TO 3:S$=S$+" "+HEX$(PEEK(&HD101+2*I)*256+PEEK(&HD100+2*I)):NEXT',
            '50 PRINT"[R";S$;"]"',
            f"60 DATA {data}",
            "RUN"]


CASES = [("atr", prog(0x0087, 5)), ("pat8", prog(0x0084, 5)),
         ("pat16", prog(0x0084, 5, "SCREEN 0,2")), ("siz", prog(0x008A, 5, "SCREEN 0,2")),
         # the other BIOS entries Demonia calls (D-BASICINT2 triage), safe arguments:
         # VRAM work at $3F00 (unused in SCREEN 0), RAM buffer at $D200
         ("rdvrm", prog(0x004A, 0, hl=0x3F00)), ("wrtvrm", prog(0x004D, 0x5A, hl=0x3F00)),
         ("filvrm", prog(0x0056, 0x5A, bc=4, hl=0x3F00)),
         ("ldirvm", prog(0x005C, 0, bc=4, de=0x3F00, hl=0xD200)),
         ("ldirmv", prog(0x0059, 0, bc=4, de=0xD200, hl=0x3F00)),
         ("snsmat", prog(0x0141, 8)), ("gttrig", prog(0x00D8, 0)), ("gttrig1", prog(0x00D8, 1)),
         ("gtstck", prog(0x00D5, 0)), ("wrtpsg", prog(0x0093, 8, de=0)),
         ("dcompr", prog(0x0020, 0)), ("disscr", prog(0x0041, 0)), ("enascr", prog(0x0044, 0)),
         ("clrspr", prog(0x0069, 0, "SCREEN 1")), ("calatr2", prog(0x0087, 5, "SCREEN 2:SCREEN 0"))]


def main():
    for name, p in CASES:
        if ONLY and name not in ONLY:
            continue
        out = {}
        for m in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"):
            scr = omsx_repl.run_cases(m, [("direct", p)], batch=False,
                                      reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=20.0)[0]
            r = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)] if scr else ["<NO OUTPUT>"]
            out[m] = " | ".join(x for x in r if x.startswith("[R") or "rror" in x) or "<nothing matched>"
        vg, zb = out.values()
        print(f"{name:6} VG {vg:34} ZB {zb:34} {'SAME' if vg == zb else 'DIFF'}", flush=True)


if __name__ == "__main__":
    main()
