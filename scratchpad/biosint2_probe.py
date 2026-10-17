#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSINT (2026-10-17), Loopy Laundry: what do the reference BIOS's internal
$2010 and $18E8 do when ENTERED BY A RET? Loopy Laundry's second BLOAD loads over
the stack and plants a return chain there -- $2010, $18E8, the hook cell $FED0,
$3002 -- which the `ret` at the end of the load follows (D-TAPELOAD).

Black-box, our own stub, interrupts off: the work area $F380-$FFFF is copied to
$D400, sixteen stack words at $D3E0-$D3FF are all set to L (our landing code), SP
= $D3F0, the registers loaded (IX $7788, IY $99AA, BC $1122, DE $3344, HL $5566,
A $5A, or the row's own), and the address entered by `jp` -- as a `ret` would
enter it, with no return address pushed. Whatever it pops or returns through
lands at L, which stores HL DE BC AF SP IX IY and copies the work area again to
$E080. SP on landing says how many stack words the entry consumed ($D3F2 = one,
a plain `ret`). BASIC prints the registers and every work-area cell that changed.
Registers and work-area RAM only -- no ROM byte is read.
Usage: biosint2_probe.py [case...] [--vg]
"""
import os, sys
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
VGONLY = "--vg" in sys.argv
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "probes", "lib"))
import omsx_repl

ORG = 0xD000


def w(v):
    return [v & 255, v >> 8]


def stub(addr, a=0x5A, bc=0x1122, de=0x3344, hl=0x5566):
    def head(L):
        return ([0xF3, 0xED, 0x73] + w(0xD1F0)                      # di / ld ($D1F0),sp
                + [0x21] + w(0xD3E0) + [0x06, 16]                   # ld hl,$D3E0 / ld b,16
                + [0x36, L & 255, 0x23, 0x36, L >> 8, 0x23, 0x10, 0xF8]   # fill with L
                + [0x21] + w(0xF380) + [0x11] + w(0xD400) + [0x01] + w(0x0C80) + [0xED, 0xB0]
                + [0x31] + w(0xD3F0)                                # ld sp,$D3F0
                + [0xDD, 0x21] + w(0x7788) + [0xFD, 0x21] + w(0x99AA)
                + [0x01] + w(bc) + [0x11] + w(de) + [0x21] + w(hl) + [0x3E, a]
                + [0xC3] + w(addr))                                 # jp addr
    L = ORG + len(head(0))
    land = ([0x22] + w(0xD100) + [0xED, 0x53] + w(0xD102) + [0xED, 0x43] + w(0xD104)
            + [0xED, 0x73] + w(0xD10A) + [0xDD, 0x22] + w(0xD10C) + [0xFD, 0x22] + w(0xD10E)
            + [0x31] + w(0xD3C0) + [0xF5, 0xE1, 0x22] + w(0xD106)
            + [0x21] + w(0xF380) + [0x11] + w(0xE080) + [0x01] + w(0x0C80) + [0xED, 0xB0]
            + [0xED, 0x7B] + w(0xD1F0) + [0xFB, 0xC9])
    return head(L) + land


def prog(addr, **regs):
    s = stub(addr, **regs)
    data = [s[i:i + 14] for i in range(0, len(s), 14)]
    return (["NEW", "10 CLEAR 200,&HCFFF",
             f"20 FOR I=0 TO {len(s) - 1}:READ X:POKE &HD000+I,X:NEXT:POKE &HD10B,0",
             "30 DEFUSR=&HD000:A=USR(0)",
             '40 S$="":FOR I=0 TO 7:S$=S$+" "+HEX$(PEEK(&HD101+2*I)*256+PEEK(&HD100+2*I)):NEXT',
             '50 PRINT"[R";S$;"]":N=0',
             "60 FOR I=0 TO &HC7F:B=PEEK(&HD400+I):C=PEEK(&HE080+I):IF B<>C THEN GOSUB 90",
             '70 NEXT:PRINT"[N";N;"]":END',
             '90 N=N+1:IF N<40 THEN PRINT HEX$(&HF380+I);":";HEX$(B);">";HEX$(C);" ";',
             "95 RETURN"]
            + [f"{100 + i} DATA " + ",".join(str(b) for b in d) for i, d in enumerate(data)]
            + ["RUN", "@WAIT150"])


# The [R line prints HL DE BC AF (unused) SP IX IY; a landing SP of 0 (high byte
# poked 0 before the run) means the stub never landed.
CASES = [("x2010", prog(0x2010)), ("x2010b", prog(0x2010, a=0xA5, bc=0x0201, de=0x0403, hl=0x0605)),
         ("x18e8", prog(0x18E8)), ("x18e8b", prog(0x18E8, a=0xA5, bc=0x0201, de=0x0403, hl=0x0605))]
# $2010's H: one register varied at a time (A $5A, BC $1122, DE $3344 fixed)
CASES += [(f"h{h:02x}{l:02x}", prog(0x2010, hl=h * 256 + l))
          for h, l in ((0x00, 0x66), (0x07, 0x66), (0x0C, 0x66), (0x0E, 0x66), (0x10, 0x66),
                       (0x55, 0x00), (0x55, 0xFF), (0x80, 0x66), (0xFF, 0x66))]
CASES += [("hde", prog(0x2010, de=0x0055)), ("hbc", prog(0x2010, bc=0x0055)), ("ha", prog(0x2010, a=0x00))]
# BASIC's $3002, the chain's last known word (after the RET at the hook cell $FED0)
CASES += [("x3002", prog(0x3002)), ("x3002b", prog(0x3002, a=0xA5, bc=0x0201, de=0x0403, hl=0x0605)),
          ("x3002c", prog(0x3002, a=0, bc=0x0001, de=0x0044, hl=0x0008))]   # $18E8's outputs
# which input of x2010b (A $A5, BC $0201, DE $0403, HL $0605) gave H = $06?
CASES += [("ba", prog(0x2010, a=0xA5)), ("bbc", prog(0x2010, bc=0x0201)),
          ("bde", prog(0x2010, de=0x0403)), ("bhl", prog(0x2010, hl=0x0605))]


def main():
    machines = ("Philips_VG_8020",) if VGONLY else ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
    for name, p in CASES:
        if ARGS and name not in ARGS:
            continue
        for m in machines:
            scr = omsx_repl.run_cases(m, [("direct", p)], batch=False,
                                      reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=40.0)[0]
            r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)] if scr else ["<NO OUTPUT>"]
            k = next((i for i, x in enumerate(r) if x.startswith("[R")), None)
            body = r[k:] if k is not None else r[-6:]
            print(f"{name:6} {m[:12]:12} " + " ".join(x.strip() for x in body if x.strip()), flush=True)


if __name__ == "__main__":
    main()
