#!/usr/bin/env python3
"""D-SYNCHR (2026-11-07): what RST $08 (SYNCHR, a published BIOS entry) does, on the
VG-8020, the CF-3300 and zerobas. A DEFUSR routine (our own test code) points HL at
&HD100 = "," "5" and does RST 8 / DB <c>, then stores HL, A and F at &HD110.. and
returns; BASIC prints them. `match` expects ",", `miss` expects ";" (a mismatch should
be Syntax error), `space` puts " ," at &HD100 (does SYNCHR skip a space BEFORE the
compare? the handbook says no). Registers and RAM only.

    python3 -u scratchpad/synchr_probe.py
"""
import os, sys, shutil
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides                               # noqa: E402

def routine(c):
    # ld hl,D100 / rst 8 / db c / ld (D110),hl / ld (D112),a / push af / pop hl /
    # ld (D114),hl / ret
    return [0x21, 0x00, 0xD1, 0xCF, c, 0x22, 0x10, 0xD1, 0x32, 0x12, 0xD1,
            0xF5, 0xE1, 0x22, 0x14, 0xD1, 0xC9]

CASES = [("match", ord(","), ",5"), ("miss", ord(";"), ",5"), ("space", ord(","), " ,5"),
         ("matchsp", ord(","), ", 5")]

def prog(tag, c, text):
    code = routine(c)
    data = ",".join(str(b) for b in code)
    txt = ",".join(str(ord(ch)) for ch in text) + ",0"
    return ["10 CLEAR 200,&HCFFF", f"20 FOR I=0 TO {len(code)-1}:READ B:POKE &HD000+I,B:NEXT",
            f"25 FOR I=0 TO {len(text)}:READ B:POKE &HD100+I,B:NEXT",
            "28 ON ERROR GOTO 90",
            "30 DEFUSR=&HD000:X=USR(0)",
            '40 PRINT CHR$(91);"' + tag + '";" HL=";HEX$(PEEK(&HD110)+256*PEEK(&HD111));" A=";PEEK(&HD112);" F=";HEX$(PEEK(&HD114));"]":END',
            '90 PRINT CHR$(91);"' + tag + '";" ERR";ERR;"]":END',
            f"50 DATA {data}", f"60 DATA {txt}", "RUN"]

def fence(tag, cap):
    c = cap or ""; k = len(c)
    while True:
        i = c.rfind("[" + tag, 0, k)
        if i < 0: return None
        j = c.find("]", i + 1)
        if j > 0 and '";' not in c[i:j]: return " ".join(c[i + len(tag) + 1:j].split())
        k = i

def main():
    sides = ("vg8020", "cf3300", "zb")
    cfg = probe_sides.sides(*sides)
    for tag, c, text in CASES:
        row = []
        for side in sides:
            cap = omsx_repl.run_cases(cfg[side]["machine"], [(tag, prog(tag, c, text))], batch=False,
                                      boot=cfg[side]["boot"], reset=cfg[side]["reset"], run_gap=8.0)[0]
            row.append(fence(tag, cap))
        print(f"{tag:8} vg8020={row[0]!r}  cf3300={row[1]!r}  zb={row[2]!r}", flush=True)
    print(__import__("probe_refcache").summary())

if __name__ == "__main__":
    main()
