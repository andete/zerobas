#!/usr/bin/env python3
"""D-SYNCHR's follow-up (2026-11-07): RST 28h GETYPR (a published BIOS entry) on the
VG-8020, the CF-3300 and zerobas. A USR routine (our own test code) does RST 28h and
stores F and VALTYP ($F663) at &HD110.. -- called with an integer, single, double and
string argument (USR passes the argument in DAC with VALTYP its type). Registers and
work-area RAM only.

    python3 -u scratchpad/getypr_probe.py
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides                               # noqa: E402

# rst 28h / push af / pop hl / ld (D110),hl / ld a,(F663) / ld (D112),a / ret
CODE = [0xEF, 0xF5, 0xE1, 0x22, 0x10, 0xD1, 0x3A, 0x63, 0xF6, 0x32, 0x12, 0xD1, 0xC9]
CASES = [("int", "1%"), ("sng", "1!"), ("dbl", "1#"), ("str", '"A"')]

def prog(tag, arg):
    data = ",".join(str(b) for b in CODE)
    return ["10 CLEAR 200,&HCFFF", f"20 FOR I=0 TO {len(CODE)-1}:READ B:POKE &HD000+I,B:NEXT",
            "28 ON ERROR GOTO 90",
            f"30 DEFUSR=&HD000:X=USR({arg})",
            '40 PRINT CHR$(91);"' + tag + '";" F=";HEX$(PEEK(&HD110));" VT=";PEEK(&HD112);"]":END',
            '90 PRINT CHR$(91);"' + tag + '";" ERR";ERR;"]":END',
            f"50 DATA {data}", "RUN"]

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
for tag, arg in CASES:
    row = []
    for side in sides:
        cap = omsx_repl.run_cases(cfg[side]["machine"], [(tag, prog(tag, arg))], batch=False,
                                  boot=cfg[side]["boot"], reset=cfg[side]["reset"], run_gap=8.0)[0]
        row.append(fence(tag, cap))
    print(f"{tag:4} vg8020={row[0]!r}  cf3300={row[1]!r}  zb={row[2]!r}", flush=True)
print(__import__("probe_refcache").summary())
