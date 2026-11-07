#!/usr/bin/env python3
"""D-SDSBOOT (Joost 2026-11-07: "if it does no harm, why not?"): the EXIT registers of
the published slot entries RDSLT ($000C) and ENASLT ($0024) on the VG-8020, the
CF-3300 and zerobas (C-BIOS). A USR routine (our own test code, page 3) loads A and HL
for the call, BC = $1234 and DE = $5678 as markers, calls the entry, and stores AF BC DE
HL IX IY at &HD110... Registers and RAM only. Slots are computed in BASIC from $A8,
EXPTBL and $FFFF (RAMAD* is unset on the diskless VG-8020).

    python3 -u scratchpad/slotregs_probe.py [case...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides                               # noqa: E402

def code(entry, hl, restore=False, de=0x5678):
    # ld a,<patched> / ld hl,hl / ld bc,1234 / ld de,5678 / call entry / store / ret;
    # restore: then ENASLT(<patched @D040>, HL) to put page 1 back before returning to BASIC
    c = [0x3E, 0x00, 0x21, hl & 0xFF, hl >> 8, 0x01, 0x34, 0x12, 0x11, de & 0xFF, de >> 8,
         0xCD, entry & 0xFF, entry >> 8,
         0xED, 0x43, 0x12, 0xD1, 0xED, 0x53, 0x14, 0xD1, 0x22, 0x16, 0xD1,
         0xDD, 0x22, 0x18, 0xD1, 0xFD, 0x22, 0x1A, 0xD1,
         0xF5, 0xE1, 0x22, 0x10, 0xD1]
    if restore:
        c += [0x3A, 0x40, 0xD0, 0x21, hl & 0xFF, hl >> 8, 0xCD, 0x24, 0x00]
    return c + [0xC9]

# slot expressions, computed in BASIC: S0 = slot 0 (expanded? then subslot of page 0),
# SR = page 3's RAM slot, S2 = page 2's slot
SLOTCALC = ["21 P=INP(&HA8):X=255-PEEK(&HFFFF)",
            "22 S2=(P\\16) AND 3:IF PEEK(&HFCC1+S2)>127 THEN S2=S2+128+((X\\16) AND 3)*4",
            "23 SR=(P\\64) AND 3:IF PEEK(&HFCC1+SR)>127 THEN SR=SR+128+((X\\64) AND 3)*4",
            "24 S0=0:IF PEEK(&HFCC1)>127 THEN S0=128+(X AND 3)*4"]
CASES = [("rd6", 0x000C, 0x0006, "S0"), ("rd7", 0x000C, 0x0007, "S0"),
         ("rdram", 0x000C, 0xF380, "SR"), ("rdr2", 0x000C, 0x8000, "SR"),
         ("rdr1", 0x000C, 0x4000, "SR"), ("rdr0", 0x000C, 0x0100, "SR"),
         ("rdb1", 0x000C, 0x4000, "S0"),
         ("ena2", 0x0024, 0x8000, "S2"), ("ena1", 0x0024, 0x4000, "S0"),
         ("enar2", 0x0024, 0x8000, "SR"), ("enar1", 0x0024, 0x4000, "SR", True),
         ("wr3", 0x0014, 0xD200, "SR", False, 0x565A), ("wr2", 0x0014, 0xA000, "SR", False, 0x56A5)]

def prog(tag, entry, hl, slot, restore=False, de=0x5678):
    c = code(entry, hl, restore, de)
    data = ",".join(str(b) for b in c)
    w = lambda a: f'HEX$(PEEK(&H{a:04X})+256*PEEK(&H{a + 1:04X}))'
    return (["10 CLEAR 200,&HCFFF", f"20 FOR I=0 TO {len(c)-1}:READ B:POKE &HD000+I,B:NEXT"]
            + SLOTCALC + [f"27 POKE &HD001,{slot}:POKE &HD040,S0", "28 ON ERROR GOTO 90",
            "30 DEFUSR=&HD000:X=USR(0)",
            f'40 PRINT CHR$(91);"{tag}";" a8=";HEX$(P);" s=";HEX$({slot});" ";{w(0xD110)};" ";{w(0xD112)};" ";{w(0xD114)};',
            f'41 PRINT " ";{w(0xD116)};" ";{w(0xD118)};" ";{w(0xD11A)};"]":END',
            f'90 PRINT CHR$(91);"{tag}";" ERR";ERR;"]":END', f"50 DATA {data}", "RUN"])

def fence(tag, cap):
    c = cap or ""; k = len(c)
    while True:
        i = c.rfind("[" + tag, 0, k)
        if i < 0: return None
        j = c.find("]", i + 1)
        if j > 0 and '";' not in c[i:j]: return " ".join(c[i + len(tag) + 1:j].split())
        k = i

sides = ("vg8020", "cf3300", "zb")
cfg = probe_sides.sides(*sides)
only = sys.argv[1:]
print("case   a8 slot AF BC DE HL IX IY  (in: BC 1234, DE 5678; IX/IY = BASIC's own, ignore)")
for case in CASES:
    tag, entry, hl, slot = case[:4]; restore = len(case) > 4 and case[4]; de = case[5] if len(case) > 5 else 0x5678
    if only and tag not in only:
        continue
    row = []
    for side in sides:
        cap = omsx_repl.run_cases(cfg[side]["machine"], [(tag, prog(tag, entry, hl, slot, restore, de))], batch=False,
                                  boot=cfg[side]["boot"], reset=cfg[side]["reset"], run_gap=8.0)[0]
        row.append(fence(tag, cap))
    print(f"{tag:6} vg8020=[{row[0]}]\n       cf3300=[{row[1]}]\n       zb    =[{row[2]}]", flush=True)
print(__import__("probe_refcache").summary())
