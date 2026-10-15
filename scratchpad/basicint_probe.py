#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BASICINT: characterise undocumented BASIC-ROM internals BLACK-BOX (oracle).

Joost ruled 2026-10-15 to support the internals games call ($73AC, $6CF3, $3297).
The VG-8020 is the oracle: OUR OWN machine code on OUR OWN tape, run by
`BLOAD"CAS:",R` exactly as the games run theirs (so the stack holds the same
`,R` return chain), jumps to the address with controlled inputs; the screen and
PEEKs of published cells are the output. No ROM byte is read, nothing is stepped.

Cases (name: routine, typed lines):
  run_vt  `ld hl,(VARTAB) / jp $73AC`     (Loopy Laundry's entry state)
  run_0   `ld hl,0 / jp $73AC`            (Punch & Judy's)
  ret     `ret`                           (the control: BLOAD,R's normal return)
  cont    `pop hl / jp $6CF3`             (Harry Fox: drop ,R's return, jump to it)

    python3 -u scratchpad/basicint_probe.py [case ...]
"""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
from cas_encode import build_cas                    # noqa: E402

VARTAB = 0xF6C2
CODE = {
    "run_vt": bytes([0x2A, VARTAB & 0xFF, VARTAB >> 8, 0xC3, 0xAC, 0x73]),
    "run_0": bytes([0x21, 0x00, 0x00, 0xC3, 0xAC, 0x73]),
    "ret": bytes([0xC9]),
    "cont": bytes([0xE1, 0xC3, 0xF3, 0x6C]),
    # VARTAB += 64, then $73AC: does it trust VARTAB as the program's end?
    "run_vt64": bytes([0x2A, 0xC2, 0xF6, 0x11, 64, 0, 0x19, 0x22, 0xC2, 0xF6, 0xC3, 0xAC, 0x73]),
    # garble line 10's link, then $73AC: does it relink the lines?
    "run_link": bytes([0x2A, 0x76, 0xF6, 0x36, 0xFF, 0x23, 0x36, 0xFF, 0xC3, 0xAC, 0x73]),
    # DATA read in direct mode first, then $73AC: is the DATA pointer reset?
    "run_data": bytes([0xC3, 0xAC, 0x73]),
    # $3297 against the PUBLISHED FIN at $3299 (MSX2 TH App. 2: HL = string,
    # A = its first char, DAC = the number). Outputs saved to $D180.. / DAC to $D190.
    "fin": b'!\x00\xd1~\xcd\x992"\x80\xd1\xedC\x82\xd1\xedS\x84\xd1\xf5\xe1"\x86\xd1!\xf6\xf7\x11\x90\xd1\x01\x08\x00\xed\xb0:c\xf62\x98\xd1\xc9',
    "fin_noa": b'!\x00\xd1\xcd\x992"\x80\xd1\xedC\x82\xd1\xedS\x84\xd1\xf5\xe1"\x86\xd1!\xf6\xf7\x11\x90\xd1\x01\x08\x00\xed\xb0:c\xf62\x98\xd1\xc9',
    "f3297": b'!\x00\xd1\xcd\x972"\x80\xd1\xedC\x82\xd1\xedS\x84\xd1\xf5\xe1"\x86\xd1!\xf6\xf7\x11\x90\xd1\x01\x08\x00\xed\xb0:c\xf62\x98\xd1\xc9',
    # push a continuation ($D020) and a marker ($ABCD), BC/DE known, jp $3297:
    # if it is `pop hl / ret`, $D020 runs with HL = $ABCD, BC / DE untouched.
    "f3297pop": b'! \xd0\xe5!\xcd\xab\xe5!\x00\x00\x11\x11\x11\x01""\xc3\x972\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"\x80\xd1\xedC\x82\xd1\xedS\x84\xd1\xf5\xe1"\x86\xd1\xc9',
    "f3297a": b'!\x00\xd1~\xcd\x972"\x80\xd1\xedC\x82\xd1\xedS\x84\xd1\xf5\xe1"\x86\xd1!\xf6\xf7\x11\x90\xd1\x01\x08\x00\xed\xb0:c\xf62\x98\xd1\xc9',
}
_FINPROG = ["NEW", '10 S$="123.5"+CHR$(0):FOR I=1 TO LEN(S$):POKE &HD0FF+I,ASC(MID$(S$,I,1)):NEXT',
            '20 BLOAD"CAS:",R',
            '30 P$="[":FOR I=&HD180 TO &HD187:P$=P$+RIGHT$("0"+HEX$(PEEK(I)),2):NEXT:PRINT P$',
            '40 P$="[":FOR I=&HD190 TO &HD198:P$=P$+RIGHT$("0"+HEX$(PEEK(I)),2):NEXT:PRINT P$:END']
PROGS = {
    "fin": _FINPROG, "fin_noa": _FINPROG, "f3297pop": _FINPROG, "f3297": _FINPROG, "f3297a": _FINPROG,
    "run_vt64": ["NEW", '10 V=PEEK(&HF6C2)+256*PEEK(&HF6C3):R=PEEK(&HF6C4)+256*PEEK(&HF6C5)',
                 '20 S=PEEK(&HF6C6)+256*PEEK(&HF6C7):PRINT"[";R-V;S-V;FRE(0);"]":END'],
    "run_data": ["NEW", '10 READ X:PRINT"[";X;"]":END', "20 DATA 5,6"],
}
DIRECTS = {
    "fin": "RUN", "fin_noa": "RUN", "f3297pop": "RUN", "f3297": "RUN", "f3297a": "RUN",
    "run_data": 'READ Q:BLOAD"CAS:",R:PRINT"[TAIL]"',
    "run_vt64": 'BLOAD"CAS:",R:PRINT"[TAIL]"',
}
PROG = ["NEW", '10 PRINT"[1]";A;', '20 PRINT"[2]":END', '30 PRINT"[3]"']
DIRECT = {
    "run_vt": 'A=7:BLOAD"CAS:",R:PRINT"[TAIL]"',
    "run_0": 'A=7:BLOAD"CAS:",R:PRINT"[TAIL]"',
    "ret": 'A=7:BLOAD"CAS:",R:PRINT"[TAIL]"',
    "cont": 'A=7:BLOAD"CAS:",R:PRINT"[TAIL]"',
}
MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    keep = [x.strip() for x in r if (x.strip().startswith("[") or "rror" in x)]
    return " | ".join(keep)


def main():
    only = sys.argv[1:] or list(CODE)
    tmp = tempfile.mkdtemp(prefix="basicint_")
    for name in only:
        path = os.path.join(tmp, f"{name}.cas")
        open(path, "wb").write(build_cas("T", 0xD000, 0xD000, CODE[name]))
        got = {}
        for side, m in MACHINES:
            lines = PROGS.get(name, PROG) + [DIRECTS.get(name) or DIRECT.get(name, 'A=7:BLOAD"CAS:",R:PRINT"[TAIL]"')]
            got[side] = rows(omsx_repl.run_cases(m, [("direct", lines)], batch=False,
                                                 reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                                 run_gap=30.0, cassette=path)[0])
        print(f"ROW {name} VG=[{got['VG']}] ZB=[{got['ZB']}] "
              f"{'SAME' if got['VG'] == got['ZB'] else 'DIVERGES'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
