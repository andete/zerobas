#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSINT (2026-10-17): what does the reference BIOS's internal $0D12 do?
Buzz Off and Shark Hunter CALL it (in A=$FE BC=$1002 DE=0 HL=$FBFE); on zerobas
that address is C-BIOS's reset.

Black-box, our own stub, interrupts off: copy the work area $F380-$FFFF to
$D200, load the registers, CALL the address, store HL / DE / BC / AF at $D100,
copy the work area again to $DE80, EI, return. BASIC then prints the registers
and every work-area cell that changed (address:before>after). Work-area RAM and
registers only -- no ROM byte is read. The VG-8020's lines are the oracle.
Registers print as HL DE BC AF IX IY HL' DE' BC' AF' (in: IX $7788, IY $99AA,
HL' $E1E2, DE' $D1D2, BC' $B1B2, AF' $A55A).
Usage: biosint_probe.py [case...] [--vg]   (--vg: the VG-8020 only)
"""
import os, sys
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
VGONLY = "--vg" in sys.argv
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "probes", "lib"))
import omsx_repl


def w(v):
    return [v & 255, v >> 8]


def stub(addr, a, bc, de, hl, pre=()):
    return ([0xF3] + list(pre) + [0x21] + w(0xF380) + [0x11] + w(0xD200) + [0x01] + w(0x0C80)
            + [0xED, 0xB0]
            # IX $7788, IY $99AA, BC' $B1B2, DE' $D1D2, HL' $E1E2, AF' $A55A
            + [0xDD, 0x21] + w(0x7788) + [0xFD, 0x21] + w(0x99AA)
            + [0xD9, 0x01] + w(0xB1B2) + [0x11] + w(0xD1D2) + [0x21] + w(0xE1E2) + [0xD9]
            + [0x21] + w(0xA55A) + [0xE5, 0xF1, 0x08]
            + [0x01] + w(bc) + [0x11] + w(de) + [0x21] + w(hl) + [0x3E, a, 0xCD] + w(addr)
            + [0x22] + w(0xD100) + [0xED, 0x53] + w(0xD102) + [0xED, 0x43] + w(0xD104)
            + [0xF5, 0xE1, 0x22] + w(0xD106)
            + [0xDD, 0x22] + w(0xD108) + [0xFD, 0x22] + w(0xD10A)
            + [0xD9, 0x22] + w(0xD10C) + [0xED, 0x53] + w(0xD10E) + [0xED, 0x43] + w(0xD110) + [0xD9]
            + [0x08, 0xF5, 0xE1, 0x22] + w(0xD112) + [0x08]
            + [0x21] + w(0xF380) + [0x11] + w(0xDE80) + [0x01] + w(0x0C80) + [0xED, 0xB0]
            + [0xFB, 0xC9])


def prog(addr, a=0xFE, bc=0x1002, de=0, hl=0xFBFE, pre=(), keywait=None):
    s = stub(addr, a, bc, de, hl, pre)
    data = [s[i:i + 14] for i in range(0, len(s), 14)]
    kw = [f"25 IF PEEK(&H{0xFBE5 + keywait[0]:X}) AND {keywait[1]} THEN 25"] if keywait else []
    return (["NEW", "10 CLEAR 200,&HCFFF"] + kw + [
             f"20 FOR I=0 TO {len(s) - 1}:READ X:POKE &HD000+I,X:NEXT",
             "30 DEFUSR=&HD000:A=USR(0)",
             '40 S$="":FOR I=0 TO 9:S$=S$+" "+HEX$(PEEK(&HD101+2*I)*256+PEEK(&HD100+2*I)):NEXT',
             '50 PRINT"[R";S$;"]":N=0',
             "60 FOR I=0 TO &HC7F:B=PEEK(&HD200+I):C=PEEK(&HDE80+I):IF B<>C THEN GOSUB 90",
             '70 NEXT:PRINT"[N";N;"]"',
             '72 PRINT"[P";HEX$(PEEK(&HD279)*256+PEEK(&HD278));HEX$(PEEK(&HD27B)*256+PEEK(&HD27A));"]"',
             '74 FOR I=0 TO 39:B=PEEK(&HDA70+I):PRINT RIGHT$("0"+HEX$(B),2);:NEXT:END',
             '90 N=N+1:IF N<40 THEN PRINT HEX$(&HF380+I);":";HEX$(B);">";HEX$(C);" ";',
             "95 RETURN"]
            + [f"{100 + i} DATA " + ",".join(str(b) for b in d) for i, d in enumerate(data)]
            + (["RUN"] if keywait else ["RUN", "@WAIT150"]))


CASES = [("game", prog(0x0D12)),
         ("a00", prog(0x0D12, a=0)), ("aff", prog(0x0D12, a=0xFF)),
         ("b01", prog(0x0D12, bc=0x0102)), ("c00", prog(0x0D12, bc=0x1000)),
         ("de", prog(0x0D12, de=0x1234)), ("hl", prog(0x0D12, hl=0xD300)),
         # 'A' (row 2 bit 6) held; OLDKEY row 2 set to "up" and the buffer emptied
         # (GETPNT = PUTPNT) just before the call, so a scan would see a NEW key
         ("keyA", prog(0x0D12, keywait=(2, 0x40),
                       pre=[0x3E, 0xFF, 0x32] + w(0xFBDC) + [0x2A] + w(0xF3F8) + [0x22] + w(0xF3FA)),
          (2, 0x40)),
         # the same, OLDKEY left as the interrupt scan wrote it (the key already seen)
         ("keyAold", prog(0x0D12, keywait=(2, 0x40), pre=[0x2A] + w(0xF3F8) + [0x22] + w(0xF3FA)),
          (2, 0x40))]
# no key held, the buffer holding characters: GETPNT ($F3FA) / PUTPNT ($F3F8) set just
# before the call (the contents are whatever KEYBUF holds)
def bufpre(get, put):
    return [0x21] + w(get) + [0x22] + w(0xF3FA) + [0x21] + w(put) + [0x22] + w(0xF3F8)


CASES += [("buf3", prog(0x0D12, pre=bufpre(0xFBF0, 0xFBF3))),
          ("bufwrap", prog(0x0D12, pre=bufpre(0xFC15, 0xFBF2))),
          ("buffull", prog(0x0D12, pre=bufpre(0xFBF5, 0xFBF4)))]
CASES = [c if len(c) == 3 else c + (None,) for c in CASES]


def main():
    machines = ("Philips_VG_8020",) if VGONLY else ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
    for name, p, hold in CASES:
        if ARGS and name not in ARGS:
            continue
        for m in machines:
            scr = omsx_repl.run_cases(m, [("direct", p)], batch=False,
                                      reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=40.0,
                                      **({"holds": [hold], "hold_secs": 150.0} if hold else {}))[0]
            r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)] if scr else ["<NO OUTPUT>"]
            k = next((i for i, x in enumerate(r) if x.startswith("[R")), None)
            body = r[k:] if k is not None else r[-8:]
            print(f"{name:5} {m[:12]:12} " + " ".join(x.strip() for x in body if x.strip()), flush=True)


if __name__ == "__main__":
    main()
