#!/usr/bin/env python3
"""D-SYNCHR's last follow-up (2026-11-07): RST 30h CALLF (a published BIOS entry, the
inline inter-slot call `RST 30h / DB slot / DW address`) on the VG-8020, the CF-3300
and zerobas. Our own test code: a USR routine at &HD000 loads A / BC / DE / HL and does
RST 30h into a routine of ours at &HD200 (page 3, the RAM slot computed from $A8 / EXPTBL / $FFFF in
BASIC, patched in at run time -- RAMAD3 is a disk-ROM cell, unset on the diskless VG-8020); that routine records what ARRIVED at &HD120.. and returns its own values,
and the caller records what CAME BACK at &HD110... Registers and RAM only.

    python3 -u scratchpad/callf_probe.py
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides                               # noqa: E402

# caller @D000: ld a,$12 / ld bc,$3456 / ld de,$789A / ld hl,$BCDE / rst 30h / db SLOT /
# dw $D200 / push af / pop hl? -- keep HL: ld (D116),hl first
CALLER = [0x3E, 0x12, 0x01, 0x56, 0x34, 0x11, 0x9A, 0x78, 0x21, 0xDE, 0xBC,
          0xF7, 0x00, 0x00, 0xD2,                      # rst 30h / db slot (patched) / dw D200
          0x22, 0x16, 0xD1,                            # ld (D116),hl
          0xED, 0x43, 0x12, 0xD1,                      # ld (D112),bc
          0xED, 0x53, 0x14, 0xD1,                      # ld (D114),de
          0xF5, 0xE1, 0x22, 0x10, 0xD1,                # push af / pop hl / ld (D110),hl
          0xC9]
SLOT_AT = 12                                           # the db's offset in CALLER
# target @D200: ld (D126),hl / ld (D122),bc / ld (D124),de / push af / pop hl /
# ld (D120),hl / ld a,$A5 / ld bc,$1111 / ld de,$2222 / ld hl,$3333 / scf / ret
TARGET = [0x22, 0x26, 0xD1, 0xED, 0x43, 0x22, 0xD1, 0xED, 0x53, 0x24, 0xD1,
          0xF5, 0xE1, 0x22, 0x20, 0xD1, 0x3E, 0xA5, 0x01, 0x11, 0x11, 0x11, 0x22, 0x22,
          0x21, 0x33, 0x33, 0x37, 0xC9]

def prog():
    c = ",".join(str(b) for b in CALLER); t = ",".join(str(b) for b in TARGET)
    w = lambda a: f'HEX$(PEEK(&H{a:04X})+256*PEEK(&H{a + 1:04X}))'
    return ["10 CLEAR 200,&HCFFF",
            f"20 FOR I=0 TO {len(CALLER)-1}:READ B:POKE &HD000+I,B:NEXT",
            f"25 FOR I=0 TO {len(TARGET)-1}:READ B:POKE &HD200+I,B:NEXT",
            "26 S=INP(&HA8)\\64:IF PEEK(&HFCC1+S)>127 THEN S=S+128+(((255-PEEK(&HFFFF))\\64) AND 3)*4",
            f"27 POKE &HD000+{SLOT_AT},S",
            "28 ON ERROR GOTO 90",
            "30 DEFUSR=&HD000:X=USR(0)",
            f'40 PRINT CHR$(91);"cf in";" ";{w(0xD120)};" ";{w(0xD122)};" ";{w(0xD124)};" ";{w(0xD126)};"]"',
            f'45 PRINT CHR$(91);"cf out";" ";{w(0xD110)};" ";{w(0xD112)};" ";{w(0xD114)};" ";{w(0xD116)};"]":END',
            '90 PRINT CHR$(91);"cf ERR";ERR;"]":END',
            f"50 DATA {c}", f"60 DATA {t}", "RUN"]

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
for side in sides:
    cap = omsx_repl.run_cases(cfg[side]["machine"], [("cf", prog())], batch=False,
                              boot=cfg[side]["boot"], reset=cfg[side]["reset"], run_gap=8.0)[0]
    print(f"{side:7} in(AF BC DE HL)=[{fence('cf in', cap)}]  out=[{fence('cf out', cap)}]  err=[{fence('cf ERR', cap)}]", flush=True)
print(__import__("probe_refcache").summary())
