#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/DSPFNK.md and CLS.md round 2 (2026-11-17): the XSCR supplement, after one test-writer review of each
page. Both reviews found inputs with ONE value (the cursor, the table bases, CNSDFG's "on", the garbage, the entry
flags) and outputs read only as sums that alias (2048 equal bytes keep only x mod 32 in a 16-bit sum). XSCR gives
each of those several values and reads bytes. ONE case list that GENERATES probes/bios/spec/xscr.asm's table and
DECODES its run:

    python3 probes/bios/spec/xscr_cases.py --gen
    python3 -u probes/bios/biosl_run.py probes/bios/spec/xscr.asm --row nodisk > scratchpad/XSCR_run2.out

The setup per case (no call under test is used):
  - the screen-table cells TXTNAM .. T32PAT := the published defaults, or (`nmv`) TXTNAM := $1000 / T32NAM := $1C00;
    CNSDFG := 0, CRTCNT := 24, LINL40 := LINL32 := the case's width; FORCLR / BAKCLR / BDRCLR := colour set `col`
    (0: 11 / 6 / 13, 1: $3A / $C5 / $F9, 2: $1B / $16 / $0D); then INITXT / INIT32 / INIGRP / INIMLT (mode 0..3);
  - LINL40 := LINL32 := 77; FNKSTR := label set `lab` (LABELS below); FNKFLG := `flg` x 10; CRTCNT := `crt`,
    CNSDFG := `cns`;
  - garbage, set `gset` (0 / 1): all of VRAM := $5A / $A5, then the name table's cell i := $80 | ((i + 64 x gset)
    AND $7F) -- never a space or a label character; LINTTB := $55 / $AA; CSRX / CSRY := the case's;
  - the call through a RAM `JP` with H / L := the case's and A / F := `ea` / `ef` (loaded by POP AF).
One 191-byte record (run 2): A, F, CNSDFG, CRTCNT, CSRX, CSRY, LINLEN, SCRMOD, LINL40, LINL32, LINTTB (24), sum16 of
the name table, 40 cells from the starts of rows 1, CRTCNT (clamped to 1..24 for the read) and 24, sum16 of
all 16 KB of VRAM, then in SCREEN 2 / 3 the 8 bytes from $0000, $1000, $2000 and $3000 ($EE x 32 in text modes),
and the sentinel $C3.
"""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ASM = os.path.join(HERE, "xscr.asm")
CLS, POSIT, FNKSB, ERAFNK, DSPFNK = 0xC3, 0xC6, 0xC9, 0xCC, 0xCF
NAMES = {CLS: "CLS", POSIT: "POSIT", FNKSB: "FNKSB", ERAFNK: "ERAFNK", DSPFNK: "DSPFNK"}
REC = 191              # run 2 (run 1: 209 B, LINTTB as a sum16, row 12 read; its cases are run 2's first 50)
SENT = 0xC3
COLOURS = [(11, 6, 13), (0x3A, 0xC5, 0xF9), (0x1B, 0x16, 0x0D)]


def _labels():
    def pad(lab):
        return (lab + bytes(16))[:16]
    key = [pad(b"key%d" % k) for k in range(10)]
    ctl = [pad(b"\tab"), pad(b"\x08cd"), pad(b"ef\x01"), pad(b"\x01\x61x"), pad(b"\x80\xff\x7f")] + \
          [pad(b"k%d" % k) for k in range(5, 10)]
    unterminated = [b"ABCDEFGHIJKLMNOP", pad(b"zz")] + key[2:]
    long15 = [pad(b"abcdefghijklmn%d" % k) for k in range(10)]
    return [key, None, ctl, unterminated, long15]      # set 1 (XKEY's odd set) is not used here


LABELS = _labels()


def _cases():
    raw = []

    def case(call, mode=0, width=None, cns=0, crt=24, csrx=7, csry=5, flg=0, lab=0, nmv=0, gset=0, col=0, ea=1,
             ef=0x40, h=99, l=99):                                       # noqa: E741
        width = width if width is not None else (40 if mode == 0 else 32)
        what = (f"{NAMES[call]} SCREEN {mode} w {width} CNSDFG {cns} CRTCNT {crt} cur {csrx},{csry}"
                + (f" FNKFLG {flg}" if flg else "") + (f" labels {lab}" if lab else "") + (" moved" if nmv else "")
                + (f" garbage {gset}" if gset else "") + (f" colours {col}" if col else "")
                + (f" A {ea:02X} F {ef:02X}" if (ea, ef) != (1, 0x40) else "")
                + (f" H {h} L {l}" if (h, l) != (99, 99) else ""))
        raw.append(NS(call=call, name=NAMES[call], mode=mode, width=width, cns=cns, crt=crt, csrx=csrx, csry=csry,
                      flg=flg, lab=lab, nmv=nmv, gset=gset, col=col, ea=ea, ef=ef, h=h, l=l,
                      fg=COLOURS[col][0], bg=COLOURS[col][1], bd=COLOURS[col][2], what=what))
    # the key-line calls (the DSPFNK review)
    case(DSPFNK, csrx=3, csry=24)
    case(DSPFNK, csrx=20, csry=23, gset=1)
    case(ERAFNK, cns=1, csrx=3, csry=24)
    case(ERAFNK, cns=1, csrx=20, csry=23, gset=1)
    case(FNKSB, cns=1, csrx=3, csry=24)
    case(DSPFNK, nmv=1)
    case(DSPFNK, mode=1, nmv=1)
    case(ERAFNK, cns=1, nmv=1)
    for call in (DSPFNK, ERAFNK, FNKSB):
        case(call, cns=0xFF)
    case(FNKSB, cns=2)
    case(FNKSB, cns=0x40)
    for w in (33, 38, 30):
        case(DSPFNK, width=w)
    case(DSPFNK, mode=1, width=28)
    case(DSPFNK, mode=1, width=29, crt=13)
    case(DSPFNK, width=37, crt=13)
    case(ERAFNK, mode=1, width=29, crt=13, cns=1)
    case(DSPFNK, lab=2)
    case(DSPFNK, width=37, lab=2)
    case(DSPFNK, lab=3)
    case(DSPFNK, flg=0xFF)
    case(ERAFNK, flg=0xFF, cns=1)
    case(DSPFNK, mode=2, gset=1, csrx=3, csry=9)
    case(ERAFNK, mode=2, gset=1, cns=1)
    # CLS (the CLS review): the gate, CNSDFG, a second garbage set, colours, H / L, moved tables, SCREEN 1 CRTCNT 13
    case(CLS, ea=0, ef=0x40)
    case(CLS, ea=1, ef=0x00)
    case(CLS, ea=1, ef=0x41)
    case(CLS, ea=0, ef=0x00)
    for cns in (2, 0x80, 0xFF):
        case(CLS, cns=cns)
    case(CLS, gset=1)
    case(CLS, gset=1, ea=1, ef=0x00)
    case(CLS, mode=2, col=2)
    case(CLS, mode=2, col=1, gset=1)
    case(CLS, h=3, l=9)
    case(CLS, nmv=1)
    case(CLS, mode=1, nmv=1)
    case(CLS, mode=1, width=29, crt=13, cns=1)
    case(CLS, cns=1, lab=4)
    case(CLS, mode=3)
    # POSIT
    case(POSIT, ea=0, ef=0x00, h=41, l=30)
    case(POSIT, cns=1, h=5, l=25)
    case(POSIT, cns=1, h=5, l=0)
    case(POSIT, mode=3, h=3, l=9)
    case(POSIT, mode=2, gset=1, csrx=11, csry=3, h=3, l=9)
    case(POSIT, gset=1, csrx=11, csry=3, h=5, l=6)
    # run 2: run 1 found POSIT's row limit CRTCNT + 1 with CNSDFG 1 (CRTCNT + CNSDFG?), and DSPFNK scrolling when the
    # cursor is on the key line's row -- CNSDFG's usual $FF, and the scroll at CRTCNT 13
    for l in (25, 24, 23, 0):                                               # noqa: E741
        case(POSIT, cns=0xFF, h=5, l=l)
    case(DSPFNK, crt=13, csrx=5, csry=13)
    return raw


CASES = _cases()


def caplen():
    return 2 + REC * len(CASES)


def table_asm():
    L = ["; ---- GENERATED by xscr_cases.py --gen: call, mode, width, cns, crt, csrx, csry, flg, lab, nmv, gset, col, "
         "ea, ef, h, l; $FF ends ----", "labels:"]
    for k, lset in enumerate(LABELS):
        L.append(f"; label set {k}" + (" (not used: zeros)" if lset is None else ""))
        for lab in (lset or [bytes(16)] * 10):
            L.append("                db      " + ", ".join(f"${x:02X}" for x in lab))
    L.append("cases:")
    for c in CASES:
        v = [c.call, c.mode, c.width, c.cns, c.crt, c.csrx, c.csry, c.flg, c.lab, c.nmv, c.gset, c.col, c.ea, c.ef,
             c.h, c.l]
        L.append("                db      " + ", ".join(f"${x:02X}" for x in v) + f"   ; {c.what}")
    L.append("                db      $FF")
    return "\n".join(L) + "\n"


def gen():
    s = open(ASM).read()
    s = s[:s.index("; ---- GENERATED by xscr_cases.py")] + table_asm()
    s = re.sub(r"; @caplen [0-9A-F]+", f"; @caplen {caplen():04X}", s)
    s = re.sub(r"CAPLEN  equ     \d+", f"CAPLEN  equ     {caplen()}", s)
    open(ASM, "w").write(s)
    print(f"{len(CASES)} cases, capture {caplen()} B")


def decode(block):
    """REFUSES an incomplete block or a record without its sentinel (docs/spec-method.md §3a)."""
    if block[1] != 0xA5:
        sys.exit("FAIL: the XSCR block is not complete")
    if len(block) < caplen():
        sys.exit(f"FAIL: the XSCR block is {len(block)} B, {caplen()} expected -- the last record has no sentinel")
    out = []
    for i, c in enumerate(CASES):
        b = list(block[2 + REC * i: 2 + REC * (i + 1)])
        if b[REC - 1] != SENT:
            sys.exit(f"FAIL: XSCR record {i} has no sentinel")
        w16 = lambda j: b[j] | (b[j + 1] << 8)                      # noqa: E731
        out.append(NS(**vars(c), idx=i, a=b[0], f=b[1], cnsdfg=b[2], crtcnt=b[3], csrx_out=b[4], csry_out=b[5],
                      linlen=b[6], scrmod=b[7], linl40=b[8], linl32=b[9], lt=b[10:34], namesum=w16(34),
                      row1=b[36:76], rowc=b[76:116], row24=b[116:156], vsum=w16(156), win=b[158:190]))
    return out


if __name__ == "__main__":
    if "--gen" in sys.argv:
        gen()
    else:
        print(f"{len(CASES)} cases, capture {caplen()} B")
