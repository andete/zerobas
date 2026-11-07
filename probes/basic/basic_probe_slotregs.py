#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""slotregs-acceptance -- D-SDSBOOT (2026-11-07): the EXIT registers of the published
slot entries RDSLT ($000C), WRSLT ($0014) and ENASLT ($0024), zerobas against the
CF-3300. A USR routine (our own test code, page 3) loads A / HL (BC = $1234, DE =
$5678 as markers, or E = the byte for WRSLT), calls the entry and stores AF BC DE HL;
BASIC prints them. Registers and RAM only -- the black-box contract, nothing read
from a ROM. Slots are computed in BASIC from $A8, EXPTBL and $FFFF.

On both references (scratchpad/slotregs_run2.out, scratchpad/slotregs_wr.out -- the
VG-8020 agrees wherever it has the case; it has no expanded slot) RDSLT and WRSLT
leave D = the primary slot register at entry, E = the byte, and for a primary slot
B = the slot shifted to the page, C = the page's mask; for an expanded slot B = the
primary slot register, C = the slot shifted to page 3. WRSLT's A = the primary slot
register. C-BIOS kept BC and returned D = the slot ID (fixed by
cbios-repack/rdslt-regs.patch). A disk's boot code reads them (SDSNAT1C).

--gate: on every row zerobas's F, B, C, D and HL equal the CF-3300's, and A / E too
where they are not a byte of memory the two machines hold differently (`byte` rows).
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides                               # noqa: E402


def code(entry, hl, restore=False, de=0x5678):
    c = [0x3E, 0x00, 0x21, hl & 0xFF, hl >> 8, 0x01, 0x34, 0x12, 0x11, de & 0xFF, de >> 8,
         0xCD, entry & 0xFF, entry >> 8,
         0xED, 0x43, 0x12, 0xD1, 0xED, 0x53, 0x14, 0xD1, 0x22, 0x16, 0xD1,
         0xF5, 0xE1, 0x22, 0x10, 0xD1]
    if restore:     # ENASLT(<@D040>, HL): page 1 back before returning to BASIC
        c += [0x3A, 0x40, 0xD0, 0x21, hl & 0xFF, hl >> 8, 0xCD, 0x24, 0x00]
    return c + [0xC9]


SLOTCALC = ["21 P=INP(&HA8):X=255-PEEK(&HFFFF)",
            "22 S2=(P\\16) AND 3:IF PEEK(&HFCC1+S2)>127 THEN S2=S2+128+((X\\16) AND 3)*4",
            "23 SR=(P\\64) AND 3:IF PEEK(&HFCC1+SR)>127 THEN SR=SR+128+((X\\64) AND 3)*4",
            "24 S0=0:IF PEEK(&HFCC1)>127 THEN S0=128+(X AND 3)*4"]
# tag, entry, HL, slot, A/E are memory (byte), ENASLT-restore, DE in
CASES = [("rd6", 0x000C, 0x0006, "S0", False), ("rdram", 0x000C, 0xF380, "SR", False),
         ("rdr1", 0x000C, 0x4000, "SR", False), ("rdr0", 0x000C, 0x0100, "SR", False),
         ("rdr2", 0x000C, 0x8000, "SR", True), ("rdb1", 0x000C, 0x4000, "S0", True),
         ("ena2", 0x0024, 0x8000, "S2", False), ("enar1", 0x0024, 0x4000, "SR", False, True),
         ("wr3", 0x0014, 0xD200, "SR", False, False, 0x565A),
         ("wr2", 0x0014, 0xA000, "SR", False, False, 0x56A5)]


def prog(tag, entry, hl, slot, restore, de):
    c = code(entry, hl, restore, de)
    w = lambda a: f'PEEK(&H{a:04X})+256*PEEK(&H{a + 1:04X})'
    return (["10 CLEAR 200,&HCFFF", f"20 FOR I=0 TO {len(c)-1}:READ B:POKE &HD000+I,B:NEXT"]
            + SLOTCALC + [f"27 POKE &HD001,{slot}:POKE &HD040,S0", "30 DEFUSR=&HD000:X=USR(0)",
            f'40 PRINT CHR$(91);"{tag}";{w(0xD110)};{w(0xD112)};{w(0xD114)};{w(0xD116)};CHR$(93):END',
            f"50 DATA {','.join(str(b) for b in c)}", "RUN"])


def fence(tag, cap):
    """The PRINTED `[tag n n n n]`, never the typed line (it carries `";`)."""
    c = cap or ""; k = len(c)
    while True:
        i = c.rfind("[" + tag, 0, k)
        if i < 0:
            return None
        j = c.find("]", i + 1)
        if j > 0 and '";' not in c[i:j]:
            v = c[i + len(tag) + 1:j].split()
            return [int(x) for x in v] if len(v) == 4 and all(x.lstrip("-").isdigit() for x in v) else None
        k = i


def main():
    gate = "--gate" in sys.argv
    only = [a for a in sys.argv[1:] if a != "--gate"]
    cfg = probe_sides.sides("cf3300", "zb")
    bad, n = [], 0
    for case in CASES:
        tag, entry, hl, slot, byte = case[:5]
        restore = len(case) > 5 and case[5]
        de = case[6] if len(case) > 6 else 0x5678
        if only and tag not in only:
            continue
        n += 1
        got = {}
        for side in ("cf3300", "zb"):
            cap = omsx_repl.run_cases(cfg[side]["machine"], [(tag, prog(tag, entry, hl, slot, restore, de))],
                                      batch=False, boot=cfg[side]["boot"], reset=cfg[side]["reset"],
                                      run_gap=8.0)[0]
            got[side] = fence(tag, cap)
            v = got[side]
            print(f"== {tag:6s} {side:7s} " + ("<none>" if v is None else
                  "AF=%04X BC=%04X DE=%04X HL=%04X" % tuple(x & 0xFFFF for x in v)), flush=True)
        r, z = got["cf3300"], got["zb"]
        if r is None:
            bad.append(f"{tag}: the CF-3300 printed no reading")
            continue
        if z is None:
            bad.append(f"{tag}: zerobas printed no reading")
            continue
        r = [x & 0xFFFF for x in r]; z = [x & 0xFFFF for x in z]
        # AF: F always, A unless a memory byte; DE: D always, E unless a memory byte
        mf, md = (0x00FF, 0xFF00) if byte else (0xFFFF, 0xFFFF)
        if (r[0] & mf, r[1], r[2] & md, r[3]) != (z[0] & mf, z[1], z[2] & md, z[3]):
            bad.append(f"{tag}: zerobas AF={z[0]:04X} BC={z[1]:04X} DE={z[2]:04X} HL={z[3]:04X}, "
                       f"CF-3300 AF={r[0]:04X} BC={r[1]:04X} DE={r[2]:04X} HL={r[3]:04X}")
    if gate:
        print(f"slotregs: {n - len(bad)}/{n} rows agree" + ("" if not bad else "; " + "; ".join(bad)))
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
