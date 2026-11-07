#!/usr/bin/env python3
"""D-SDSBOOT (2026-11-07): the registers BDOS ($F37D, Disk BASIC's entry) RETURNS, CF-3300
against zerobas -- SDSNAT1C's boot code reads values the spec leaves undefined
(scratchpad/sdsboot_bootcode_*.out). A BASIC program POKEs a routine at &HD000 that loads
A / BC / DE / HL, calls $F37D, stores AF BC DE HL IX IY back at &HD100.. and PRINTs them.
Our own test code, run on both machines; only registers and RAM are read.

    python3 -u scratchpad/bdosregs_probe.py
"""
import os, sys, shutil
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides, probe_tmp                     # noqa: E402
FIXTURE = os.path.join(REPO, "disk", "test720.dsk")

# ld a,n / ld bc,nn / ld de,nn / ld hl,nn / call $F37D / ld (D102),bc / ld (D104),de /
# ld (D106),hl / ld (D108),ix / ld (D10A),iy / push af / pop hl / ld (D100),hl / ret
def routine(a, bc, de, hl, dta=None):
    w = lambda v: [v & 0xFF, v >> 8]
    pre = [] if dta is None else [0x0E, 0x1A, 0x11] + w(dta) + [0xCD, 0x7D, 0xF3]   # SETDTA first
    return pre + ([0x3E, a, 0x01] + w(bc) + [0x11] + w(de) + [0x21] + w(hl) + [0xCD, 0x7D, 0xF3,
            0xED, 0x43, 0x02, 0xD1, 0xED, 0x53, 0x04, 0xD1, 0x22, 0x06, 0xD1,
            0xDD, 0x22, 0x08, 0xD1, 0xFD, 0x22, 0x0A, 0xD1, 0xF5, 0xE1, 0x22, 0x00, 0xD1, 0xC9])

CASES = [  # tag, A, BC (C = the function), DE, HL -- the boot code's own inputs first
    ("setdta",  0x00, 0x001A, 0xC200, 0xF323),
    ("setdta2", 0x55, 0x001A, 0xD200, 0x1234),
    ("rdabs",   0x08, 0x582F, 0x0001, 0x0100),   # DE = sector 1, H = 1 sector, L = drive A
    ("rdabs0",  0x00, 0x002F, 0x0000, 0x0100),
    ("rdabsd",  0x08, 0x582F, 0x0001, 0x0100, 0xD200),   # the same, after SETDTA $D200
    ("rdabs5",  0x08, 0x582F, 0x059A, 0x0100, 0xD200),   # the boot code's own sector
    ("conout",  0x00, 0x0002, 0x0041, 0x0000),   # E = 'A'
]

def prog(tag, a, bc, de, hl, dta=None):
    code = routine(a, bc, de, hl, dta)
    data = ",".join(str(b) for b in code)
    return ["10 CLEAR 200,&HCFFF", f"20 FOR I=0 TO {len(code)-1}:READ B:POKE &HD000+I,B:NEXT",
            "30 DEFUSR=&HD000:X=USR(0)",
            '40 PRINT CHR$(91);"' + tag + '";:FOR I=0 TO 11 STEP 2:PRINT " ";HEX$(PEEK(&HD100+I)+256*PEEK(&HD101+I));:NEXT:PRINT"]"',
            f"50 DATA {data}", "RUN"]

def fence(tag, cap):
    c = cap or ""; k = len(c)
    while True:
        i = c.rfind("[" + tag, 0, k)
        if i < 0: return None
        j = c.find("]", i + 1)
        if j > 0 and '";' not in c[i:j]: return " ".join(c[i + len(tag) + 1:j].split())
        k = i

def main():
    cfg = probe_sides.sides("cf3300", "zb")
    print("tag       AF   BC   DE   HL   IX   IY")
    only = sys.argv[1:]
    for case in CASES:
        tag, a, bc, de, hl = case[:5]; dta = case[5] if len(case) > 5 else None
        if only and tag not in only: continue
        row = []
        for side in ("cf3300", "zb"):
            dsk = probe_tmp.tmp(f"bdosregs_{tag}_{side}.dsk"); shutil.copyfile(FIXTURE, dsk)
            cap = omsx_repl.run_cases(cfg[side]["machine"], [(tag, prog(tag, a, bc, de, hl, dta))], batch=False,
                                      boot=cfg[side]["boot"], reset=cfg[side]["reset"],
                                      diska=probe_sides.diska(side, dsk), run_gap=20.0)[0]
            row.append(fence(tag, cap))
        mark = "SAME" if row[0] == row[1] else "DIFF"
        print(f"{tag:8} in  A={a:02X} BC={bc:04X} DE={de:04X} HL={hl:04X}\n   cf3300 {row[0]}\n   zb     {row[1]}   {mark}", flush=True)

if __name__ == "__main__":
    main()
