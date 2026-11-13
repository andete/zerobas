#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ENTRYTIERS step 3: BIOS entries that answer in VRAM (or, for LDIRMV, in RAM), compared
there -- the VG-8020 against zerobas.

Each row runs in SCREEN 1 (BASIC's own SCREEN 1 first, so both start alike), sets VRAM
window W to a known pattern with OUR OWN port code, calls the entry, then reads W back with
OUR OWN port code (address to $99, then IN $98) -- never through an entry under test -- into
RAM, and BASIC prints it after SCREEN 0. Compared byte for byte.

  filvrm   HL $1000, BC 16, A $5A          W = $0FFC..$1013 (the run and both edges)
  wrtvrm   HL $1004, A $A5                 W = $1000..$100F
  ldirvm   RAM $C000 (16 B pattern) -> DE $1002, BC 16     W = $1000..$1017
  ldirmv   VRAM $1000.. -> RAM DE $C100, BC 16  (the RAM is read, not VRAM)
  clrspr   sprite attribute table (ATRBAS) and the first 32 B of the patterns (PATBAS)
  chgclr   FORCLR 6 / BAKCLR 1 / BDRCLR 13 POKEd, then CHGCLR: the colour table $2000..$201F

Black box: VRAM / RAM read through the ports and memory; registers not compared.

    python3 -u probes/basic/basic_probe_biosvram.py [ROW ...]      (`make biosvram-acceptance`)
Exit 0 all SAME; 1 a divergence; 2 the VG-8020 gave no reading.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))
FILVRM, WRTVRM, LDIRVM, LDIRMV, CLRSPR, CHGCLR = 0x0056, 0x004D, 0x005C, 0x0059, 0x0069, 0x0062


def vfill(addr, n, val):
    """OUR OWN: VRAM[addr..addr+n) := val (address with the write bit, then OUT $98)."""
    return [0xF3, 0x3E, addr & 255, 0xD3, 0x99, 0x3E, ((addr >> 8) & 0x3F) | 0x40, 0xD3, 0x99,
            0x06, n, 0x3E, val, 0xD3, 0x98, 0x10, 0xFC, 0xFB]


def vread(addr, n, dst):
    """OUR OWN: RAM[dst..] := VRAM[addr..addr+n) (address, then IN $98)."""
    return [0xF3, 0x3E, addr & 255, 0xD3, 0x99, 0x3E, (addr >> 8) & 0x3F, 0xD3, 0x99,
            0x21, dst & 255, dst >> 8, 0x06, n, 0xDB, 0x98, 0x77, 0x23, 0x10, 0xFA, 0xFB]


def call(a, regs=()):
    c = []
    for r, v in regs:
        c += {"a": [0x3E, v], "bc": [0x01, v & 255, v >> 8], "de": [0x11, v & 255, v >> 8],
              "hl": [0x21, v & 255, v >> 8]}[r]
    return c + [0xCD, a & 255, a >> 8]


# name: (setup, the call, windows to read [(vram addr, n)], RAM windows [(addr, n)], BASIC before)
ROWS = {
    "filvrm": (vfill(0x0FF8, 32, 0x11), call(FILVRM, [("hl", 0x1000), ("bc", 16), ("a", 0x5A)]),
               [(0x0FFC, 24)], [], ""),
    "wrtvrm": (vfill(0x1000, 16, 0x22), call(WRTVRM, [("hl", 0x1004), ("a", 0xA5)]),
               [(0x1000, 16)], [], ""),
    "ldirvm": (vfill(0x1000, 24, 0x33), call(LDIRVM, [("hl", 0xC000), ("de", 0x1002), ("bc", 16)]),
               [(0x1000, 24)], [], "FOR I=0 TO 15:POKE &HC000+I,(I*17+3) AND 255:NEXT"),
    "ldirmv": (vfill(0x1000, 16, 0x44), call(LDIRMV, [("hl", 0x1000), ("de", 0xC100), ("bc", 16)]),
               [], [(0xC0FE, 20)], "FOR I=0 TO 19:POKE &HC0FE+I,255:NEXT"),
    "clrspr": (vfill(0x1B00, 32, 0x55) + vfill(0x3800, 32, 0x66), call(CLRSPR),
               [(0x1B00, 32), (0x1B7C, 4), (0x3800, 32)], [], ""),
    "chgclr": ([], call(CHGCLR), [(0x2000, 32)], [], "POKE &HF3E9,6:POKE &HF3EA,1:POKE &HF3EB,13"),
}


def code(row):
    setup, the_call, vwin, rwin, _ = row
    c = list(setup) + list(the_call)
    dst = 0xD100
    for a, n in vwin:
        c += vread(a, n, dst)
        dst += n
    for a, n in rwin:                                   # ld hl,a / ld de,dst / ld bc,n / ldir
        c += [0x21, a & 255, a >> 8, 0x11, dst & 255, dst >> 8, 0x01, n, 0, 0xED, 0xB0]
        dst += n
    return c + [0xC9], dst - 0xD100


def prog(row):
    c, total = code(row)
    before = row[4]
    return (["NEW", "10 SCREEN 1:CLEAR 200,&HBFFF",
             f"20 FOR I=0 TO {len(c) - 1}:READ X:POKE &HD000+I,X:NEXT"]
            + [f"25 {before}"] * bool(before)
            + ["30 DEFUSR=&HD000:Q=USR(0):SCREEN 0:WIDTH 40",
               f'40 FOR J=0 TO {total - 1} STEP 16:S$="":FOR I=J TO J+15:IF I<{total} THEN '
               'S$=S$+RIGHT$("0"+HEX$(PEEK(&HD100+I)),2)',
               '50 NEXT:PRINT "[V";J;S$;"]":NEXT']
            + [f"{60 + k} DATA " + ",".join(str(b) for b in c[i:i + 40])
               for k, i in enumerate(range(0, len(c), 40))] + ["RUN"]), total


def read(machine, row):
    p, total = prog(row)
    raw = omsx_repl.run_cases(machine, [("direct", p)], batch=False, reset=("", "SCREEN 0"),
                              step=3.0, run_gap=10.0)[0] or ""
    parts = {int(j): bytes.fromhex(h) for j, h in
             re.findall(r"\[V\s*(\d+)\s+([0-9A-F]+)\s*\]", re.sub(r"\s+", " ", raw))}
    data = b"".join(parts[k] for k in sorted(parts))
    return data if len(data) == total else None


def main():
    only = sys.argv[1:] or list(ROWS)
    bad = blind = 0
    for name in only:
        got = {side: read(m, ROWS[name]) for side, m in MACHINES}
        if got["VG"] is None:
            blind += 1
            print(f"ROW {name:7} NO-REFERENCE", flush=True)
            continue
        same = got["ZB"] == got["VG"]
        bad += not same
        print(f"ROW {name:7} {'SAME' if same else 'DIVERGES'}  VG {got['VG'].hex()}"
              + ("" if same else f"\n{'':12}ZB {got['ZB'].hex() if got['ZB'] else None}"), flush=True)
    if blind:
        print("INSTRUMENT FAULT: the VG-8020 gave no reading")
        return 2
    print(f"{'PASS' if not bad else 'FAIL'}: VRAM-answering BIOS entries ({len(only) - bad}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
