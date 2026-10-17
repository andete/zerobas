#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSREGS (gate: biosregs-acceptance): what the BIOS sprite and VRAM helpers
leave in A / BC / DE / HL, VG-8020 against zerobas.

WHY THIS EXISTS. Demonia loaded on zerobas once its BASIC-ROM tape entries were
pinned (D-BASICINT2), and then played a different attract demo and RESET after
~3 minutes. Every one of its ~8000 calls into the BIOS was logged on both machines
with the registers going in and coming out (addresses and registers only), and the
two streams parted at four C-BIOS contracts, fixed in cbios-repack/calpat-de.patch
and cbios-repack/bios-regs.patch:
  CALATR ($0087)  the VG-8020 KEEPS A; C-BIOS returned 4*A -- Demonia reuses A as
                  its next sprite number, and wrote the wrong sprites
  CALPAT ($0084)  DE = the pattern offset; C-BIOS left PATBAS
  LDIRMV ($0059)  DE = the RAM end, BC = 0; C-BIOS: DE = the VRAM start, BC = $0098
                  -- a chunked VRAM -> RAM copy wrote every chunk to one place
  LDIRVM ($005C)  BC = 0; C-BIOS $0098
  DCOMPR ($0020)  A = H - D, or L - E when H = D; C-BIOS left H (or L)
  $0D12           (D-BIOSINT, 2026-10-17) the reference BIOS's internal keyboard
                  scan, which Buzz Off and Shark Hunter CALL; C-BIOS had its reset
                  there (cbios-repack/bios-keyscan.patch). It scans the matrix, then
                  returns A = low(PUTPNT) - low(GETPNT) (unwrapped), HL = GETPNT,
                  DE = KEYBUF, BC = $00FF, and keeps IX (scratchpad/biosint_probe.py
                  also has a held key, IY and the alternate set). The kscan rows set
                  GETPNT / PUTPNT under DI just before the call, print IX as well, and
                  empty the buffer afterwards so BASIC reads no stray characters.

Each row is OUR stub: BC/DE/HL/A loaded, the entry called, then HL/DE/BC/A stored
and printed. F is not compared: neither machine's flags after these calls are a
documented contract, and they differ (scratchpad/calatr_probe.out). The sprite
rows run in SCREEN 1 and print after SCREEN 0: in SCREEN 0 zerobas reads ATRBAS /
PATBAS as 0 where the VG-8020 keeps &H1B00 / &H3800 -- a separate divergence, filed.
The VG-8020's printed line is the oracle; no ROM byte is read.

    python3 -u probes/basic/basic_probe_biosregs.py [ROW ...]
Exit 0 all SAME; 1 a divergence; 2 the VG-8020 gave no reading.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))


def stub(addr, a, bc, de, hl, buf=None):
    # ld bc / ld de / ld hl / ld a / call addr / ld ($D100),hl / ld ($D102),de /
    # ld ($D104),bc / ld ($D106),a / ret
    body = [0x01, bc & 255, bc >> 8, 0x11, de & 255, de >> 8, 0x21, hl & 255, hl >> 8,
            0x3E, a, 0xCD, addr & 255, addr >> 8,
            0x22, 0x00, 0xD1, 0xED, 0x53, 0x02, 0xD1, 0xED, 0x43, 0x04, 0xD1,
            0x32, 0x06, 0xD1]
    if buf is None:
        return body + [0xC9]
    get, put = buf
    # di / GETPNT ($F3FA) and PUTPNT ($F3F8) set / ld ix,$7788 / <body> /
    # ld ($D108),ix / PUTPNT := GETPNT (the buffer emptied) / ei / ret
    return ([0xF3, 0x21, get & 255, get >> 8, 0x22, 0xFA, 0xF3,
             0x21, put & 255, put >> 8, 0x22, 0xF8, 0xF3, 0xDD, 0x21, 0x88, 0x77] + body
            + [0xDD, 0x22, 0x08, 0xD1, 0x2A, 0xFA, 0xF3, 0x22, 0xF8, 0xF3, 0xFB, 0xC9])


def prog(addr, a=0, bc=0x1122, de=0x3344, hl=0x5566, before="", after="", buf=None):
    s = stub(addr, a, bc, de, hl, buf)
    ix = ';" IX";HEX$(PEEK(&HD109)*256+PEEK(&HD108))' if buf else ""
    return ["NEW",
            "10 CLEAR 200,&HCFFF" + (":" + before if before else ""),
            f"20 FOR I=0 TO {len(s) - 1}:READ X:POKE &HD000+I,X:NEXT",
            "30 DEFUSR=&HD000:Q=USR(0)" + (":" + after if after else ""),
            '40 S$="":FOR I=0 TO 2:S$=S$+" "+HEX$(PEEK(&HD101+2*I)*256+PEEK(&HD100+2*I)):NEXT',
            '50 PRINT"[R";S$;" A";HEX$(PEEK(&HD106))' + ix + ';"]"',
            "60 DATA " + ",".join(str(b) for b in s[:40]),
            *(["70 DATA " + ",".join(str(b) for b in s[40:])] if len(s) > 40 else []),
            "RUN"]


S1 = dict(before="SCREEN 1", after="SCREEN 0")
ROWS = {
    "atr": prog(0x0087, 5, **S1),                                  # HL DE BC A
    "pat8": prog(0x0084, 5, **S1),
    "pat16": prog(0x0084, 5, before="SCREEN 1,2", after="SCREEN 0"),
    # VRAM work at &H3F00 (unused in SCREEN 0), RAM buffer at &HD200
    "ldirvm": prog(0x005C, 0, bc=4, de=0x3F00, hl=0xD200),
    "ldirmv": prog(0x0059, 0, bc=4, de=0xD200, hl=0x3F00),
    "dcmp_h": prog(0x0020, 0, de=0x1800, hl=0x1700),               # H != D: A = H - D
    "dcmp_l": prog(0x0020, 0, de=0x1834, hl=0x1812),               # H = D: A = L - E
    # $0D12 with Buzz Off's registers (A=$FE BC=$1002 DE=0 HL=$FBFE); GETPNT, PUTPNT:
    "kscan": prog(0x0D12, 0xFE, bc=0x1002, de=0, hl=0xFBFE, buf=(0xFBF6, 0xFBF6)),  # empty
    "kscan3": prog(0x0D12, 0xFE, bc=0x1002, de=0, hl=0xFBFE, buf=(0xFBF0, 0xFBF3)),
    "kscanw": prog(0x0D12, 0xFE, bc=0x1002, de=0, hl=0xFBFE, buf=(0xFC15, 0xFBF2)),  # wrapped
}


def read(machine, p):
    scr = omsx_repl.run_cases(machine, [("direct", p)], batch=False,
                              reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=20.0)[0]
    if not scr:
        return None
    r = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)]
    return " | ".join(x for x in r if x.startswith("[R") or "rror" in x) or None


def main():
    only = sys.argv[1:] or list(ROWS)
    bad, blind = [], []
    for name in only:
        got = {side: read(m, ROWS[name]) for side, m in MACHINES}
        if not got["VG"]:
            blind.append(name)
            verdict = "NO-REFERENCE"
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name:7} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the VG-8020 gave no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: BIOS helper registers "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
