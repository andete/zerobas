#!/usr/bin/env python3
"""synchr-acceptance -- D-SYNCHR (2026-11-07): what RST $08 (SYNCHR, a published BIOS entry) does, on the
VG-8020, the CF-3300 and zerobas. A DEFUSR routine (our own test code) points HL at
&HD100 = "," "5" and does RST 8 / DB <c>, then stores HL, A and F at &HD110.. and
returns; BASIC prints them. `match` expects ",", `miss` expects ";" (a mismatch should
be Syntax error), `space` puts " ," at &HD100 (does SYNCHR skip a space BEFORE the
compare? the handbook says no). Registers and RAM only.

    python3 -u probes/basic/basic_probe_synchr.py [--gate]
--gate: every zerobas row must equal BOTH references' (which must agree and answer).
The rows also pin RST 10h CHRGTR's flags to the reference's bit (F = $23 on a digit).
"""
import os, sys, shutil
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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

# RST 28h GETYPR (same date, D-SYNCHR's follow-up): a USR routine does RST 28h and
# stores F and VALTYP ($F663); called with an int / single / double argument (a string
# argument to USR is Type mismatch on all three, so it is a row too).
GCODE = [0xEF, 0xF5, 0xE1, 0x22, 0x10, 0xD1, 0x3A, 0x63, 0xF6, 0x32, 0x12, 0xD1, 0xC9]
GCASES = [("g.int", "1%"), ("g.sng", "1!"), ("g.dbl", "1#"), ("g.str", '"A"')]


def gprog(tag, arg):
    data = ",".join(str(b) for b in GCODE)
    return ["10 CLEAR 200,&HCFFF", f"20 FOR I=0 TO {len(GCODE)-1}:READ B:POKE &HD000+I,B:NEXT",
            "28 ON ERROR GOTO 90", f"30 DEFUSR=&HD000:X=USR({arg})",
            '40 PRINT CHR$(91);"' + tag + '";" F=";HEX$(PEEK(&HD110));" VT=";PEEK(&HD112);"]":END',
            '90 PRINT CHR$(91);"' + tag + '";" ERR";ERR;"]":END', f"50 DATA {data}", "RUN"]


def fence(tag, cap):
    c = cap or ""; k = len(c)
    while True:
        i = c.rfind("[" + tag, 0, k)
        if i < 0: return None
        j = c.find("]", i + 1)
        if j > 0 and '";' not in c[i:j]: return " ".join(c[i + len(tag) + 1:j].split())
        k = i

def main():
    gate = "--gate" in sys.argv
    sides = ("vg8020", "cf3300", "zb")
    cfg = probe_sides.sides(*sides)
    bad = []
    rows = [(tag, prog(tag, c, text)) for tag, c, text in CASES] + [(t, gprog(t, a)) for t, a in GCASES]
    for tag, lines in rows:
        row = []
        for side in sides:
            cap = omsx_repl.run_cases(cfg[side]["machine"], [(tag, lines)], batch=False,
                                      boot=cfg[side]["boot"], reset=cfg[side]["reset"], run_gap=8.0)[0]
            row.append(fence(tag, cap))
        print(f"{tag:8} vg8020={row[0]!r}  cf3300={row[1]!r}  zb={row[2]!r}", flush=True)
        if row[0] is None or row[1] is None or row[0] != row[1]:
            bad.append(f"{tag}: the references give no single answer ({row[0]!r} / {row[1]!r})")
        elif row[2] != row[0]:
            bad.append(f"{tag}: zerobas {row[2]!r}, references {row[0]!r}")
    print(__import__("probe_refcache").summary())
    if gate:
        print(f"synchr: {len(rows) - len(bad)}/{len(rows)} rows agree" + ("" if not bad else "; " + "; ".join(bad)))
        return 1 if bad else 0
    return 0

if __name__ == "__main__":
    sys.exit(main())
