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


def stub(addr, a, bc, de, hl, buf=None, ix=None):
    # ld bc / ld de / ld hl / ld a / call addr / ld ($D100),hl / ld ($D102),de /
    # ld ($D104),bc / ld ($D106),a / ret  (ix: `ld ix,nn` first -- CALBAS's target)
    pre = [0xDD, 0x21, ix & 255, ix >> 8] if ix is not None else []
    body = pre + [0x01, bc & 255, bc >> 8, 0x11, de & 255, de >> 8, 0x21, hl & 255, hl >> 8,
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


def prog(addr, a=0, bc=0x1122, de=0x3344, hl=0x5566, before="", after="", buf=None, ix=None):
    s = stub(addr, a, bc, de, hl, buf) if ix is None else stub(addr, a, bc, de, hl, buf, ix=ix)
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


def prog_f(addr, a=0, bc=0x1122, de=0x3344, hl=0x5566, before="", after=""):
    """prog() with F captured too: `push af` right after the call, popped after the
    register stores into $D10A (low byte = F), printed as F.. inside the [R ..] line."""
    body = [0x01, bc & 255, bc >> 8, 0x11, de & 255, de >> 8, 0x21, hl & 255, hl >> 8,
            0x3E, a, 0xCD, addr & 255, addr >> 8, 0xF5,
            0x22, 0x00, 0xD1, 0xED, 0x53, 0x02, 0xD1, 0xED, 0x43, 0x04, 0xD1,
            0x32, 0x06, 0xD1, 0xE1, 0x22, 0x0A, 0xD1, 0xC9]
    p = [l for l in prog(addr, a, bc, de, hl, before=before, after=after)
         if not (l.startswith("60 DATA") or l.startswith("70 DATA"))]
    p.insert(p.index("RUN"), "60 DATA " + ",".join(str(b) for b in body))
    p = [f"20 FOR I=0 TO {len(body) - 1}:READ X:POKE &HD000+I,X:NEXT" if l.startswith("20 FOR") else l
         for l in p]
    return [l.replace(';"]"', ';" F";HEX$(PEEK(&HD10A));"]"') if l.startswith("50 PRINT") else l
            for l in p]


def cur(addr, cloc, cmask):
    """D-BIOSCONTRACT: a graphics-cursor move -- CLOC / CMASK POKEd in SCREEN 2, the
    entry called, both cells printed after (its whole effect is on them)."""
    setup = f"SCREEN 2:POKE &HF92A,{cloc & 255}:POKE &HF92B,{cloc >> 8}:POKE &HF92C,{cmask}"
    show = 'SCREEN 0:PRINT "[C";HEX$(PEEK(&HF92A)+256*PEEK(&HF92B));" ";HEX$(PEEK(&HF92C));"]"'
    return prog(addr, 0, before=setup, after=show)
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
    # D-BIOSCONTRACT (2026-11-08, cbios-repack/graphics-cursor.patch): SCALXY clips X to
    # 0..255 and Y to 0..191 (negatives to 0), divides both by 4 in SCREEN 3, A = $80
    # only when nothing was clipped; C-BIOS returned GRPACX / GRPACY untouched.
    "sxy2over": prog(0x010E, 0, bc=300, de=200, before="SCREEN 2", after="SCREEN 0"),
    "sxy2in": prog(0x010E, 0, bc=100, de=100, before="SCREEN 2", after="SCREEN 0"),
    "sxy2neg": prog(0x010E, 0, bc=0xFFFB, de=0xFFFB, before="SCREEN 2", after="SCREEN 0"),
    "sxy2xov": prog(0x010E, 0, bc=300, de=100, before="SCREEN 2", after="SCREEN 0"),
    "sxy3over": prog(0x010E, 0, bc=300, de=200, before="SCREEN 3", after="SCREEN 0"),
    # D-BIOSCONTRACT (2026-11-08): RIGHTC / LEFTC / UPC / DOWNC in SCREEN 2, inside a
    # byte or cell and across its edge -- CMASK rotated / CLOC +-8, CLOC +-1 / +-$F9
    # (scratchpad/biossweep_cur2.out); C-BIOS's were print_debug stubs.
    "rc_mid": cur(0x00FC, 0x0108, 0x10),
    "rc_wrap": cur(0x00FC, 0x0108, 0x01),
    "lc_wrap": cur(0x00FF, 0x0108, 0x80),
    "uc_mid": cur(0x0102, 0x010B, 0x10),
    "uc_wrap": cur(0x0102, 0x0108, 0x10),
    "dc_wrap": cur(0x0108, 0x010F, 0x10),
    # STOREC (CLOC := HL, CMASK := A), SETATR (ATRBYT := A), READC (the pixel's colour:
    # the colour byte's foreground nibble when the pattern bit is set, else background)
    "storec": prog(0x0117, 0x40, hl=0x1234,
                   after='PRINT "[C";HEX$(PEEK(&HF92A)+256*PEEK(&HF92B));" ";HEX$(PEEK(&HF92C));"]"'),
    "setatr": prog(0x011A, 5, after='PRINT "[C";HEX$(PEEK(&HF3F2));"]"'),
    "readc_fg": prog(0x011D, 0, before="SCREEN 2:POKE &HF92A,8:POKE &HF92B,1:POKE &HF92C,16:"
                     "VPOKE &H108,16:VPOKE &H2108,&H4F", after="SCREEN 0"),
    "readc_bg": prog(0x011D, 0, before="SCREEN 2:POKE &HF92A,8:POKE &HF92B,1:POKE &HF92C,32:"
                     "VPOKE &H108,16:VPOKE &H2108,&H4F", after="SCREEN 0"),
    # SETC (scratchpad/biossweep_setc.out): ATRBYT the background -> the bit cleared;
    # else set, the colour byte ATRBYT << 4 | background unless ATRBYT is the
    # foreground already; A = the colour byte when written, else the pattern byte.
    # Pattern / colour read while still in SCREEN 2 (SCREEN 0 rebuilds VRAM).
    **{n: prog(0x0120, 0, before="SCREEN 2:POKE &HF92A,8:POKE &HF92B,1:POKE &HF92C,16:"
                f"VPOKE &H108,{pat}:VPOKE &H2108,&H4F:POKE &HF3F2,{atr}",
               after='P=VPEEK(&H108):C=VPEEK(&H2108):SCREEN 0:PRINT "[C";HEX$(P);" ";HEX$(C);"]"')
       for n, pat, atr in (("setc_new", 0, 6), ("setc_bg", 16, 15), ("setc_fg", 0, 4),
                           ("setc_set", 16, 6))},
    # MAPXYC (scratchpad/biossweep_mxy.out): CLOC = (Y AND $F8) * 32 + (Y AND 7) +
    # (X AND $F8), CMASK = $80 >> (X AND 7); A = CLOC's low byte, D = X; C-BIOS left
    # out Y AND 7, set every bit rightward and stored GRPACX / GRPACY
    **{n: prog(0x0111, 0, bc=x, de=y, before="SCREEN 2:POKE &HFCB7,0:POKE &HFCB8,0",
               after='SCREEN 0:PRINT "[C";HEX$(PEEK(&HF92A)+256*PEEK(&HF92B));" ";'
                     'HEX$(PEEK(&HF92C));" ";HEX$(PEEK(&HFCB7)+256*PEEK(&HFCB8));"]"')
       for n, x, y in (("mxy_13", 13, 21), ("mxy_max", 255, 191))},
    # TUPC / TDOWNC (scratchpad/biossweep_tud2.out), F captured: on the screen's top /
    # bottom pixel row no move, A = 0, F = $45 (Cy); across an inner cell edge as UPC /
    # DOWNC, F = $54 -- C-BIOS's were print_debug stubs
    **{n: prog_f(addr, 0, before=f"SCREEN 2:POKE &HF92A,{lo}:POKE &HF92B,{hi}:POKE &HF92C,16",
                 after='SCREEN 0:PRINT "[C";HEX$(PEEK(&HF92A)+256*PEEK(&HF92B));" ";'
                       'HEX$(PEEK(&HF92C));"]"')
       for n, addr, lo, hi in (("tupc_top", 0x0105, 8, 0), ("tupc_wrap", 0x0105, 8, 1),
                               ("tdownc_bot", 0x010B, 15, 0x17), ("tdownc_wrap", 0x010B, 15, 1),
                               ("tdownc_h18", 0x010B, 15, 0x18))},   # past the bottom (gap 10)
    # NSETCX (scratchpad/biossweep_nsx2.out): HL pixels from pixel 2 of $108 across two
    # bytes, as SETC sets / clears them, CLOC / CMASK back where they started. The
    # registers it leaves are NOT compared (`END` before the [R] print): the VG-8020
    # keeps none of them, and ours differ -- filed under D-BIOSCONTRACT.
    **{n: prog(0x0123, 0, hl=12,
               before="SCREEN 2:POKE &HF92A,8:POKE &HF92B,1:POKE &HF92C,32:"
                      f"VPOKE &H108,{pat}:VPOKE &H110,{pat}:VPOKE &H2108,&H4F:VPOKE &H2110,&H4F:"
                      f"POKE &HF3F2,{atr}",
               after='P=VPEEK(&H108):Q=VPEEK(&H110):C=VPEEK(&H2108):D=VPEEK(&H2110):SCREEN 0:'
                     'PRINT "[C";HEX$(P);" ";HEX$(Q);" ";HEX$(C);" ";HEX$(D);" ";'
                     'HEX$(PEEK(&HF92A)+256*PEEK(&HF92B));" ";HEX$(PEEK(&HF92C));"]":END')
       for n, atr, pat in (("nsx_new", 6, 0), ("nsx_bg", 15, 255), ("nsx_fg", 4, 0))},
    # D-BIOSCONTRACT2 gap 10 (2026-11-14): the same entries in SCREEN 3 (multicolour), which
    # only SCREEN 2 had compared. CMASK is a NIBBLE there ($F0 the left block, $0F the right);
    # READC / SETC / NSETCX read and write a pattern byte's nibble as a colour.
    **{n: prog(addr, 0, before=f"SCREEN 3:POKE &HF92A,{lo}:POKE &HF92B,{hi}:POKE &HF92C,{m}",
               after='SCREEN 0:PRINT "[C";HEX$(PEEK(&HF92A)+256*PEEK(&HF92B));" ";'
                     'HEX$(PEEK(&HF92C));"]"')
       for n, addr, lo, hi, m in (("rc3_mid", 0x00FC, 8, 1, 0xF0), ("rc3_wrap", 0x00FC, 8, 1, 0x0F),
                                  ("lc3_mid", 0x00FF, 8, 1, 0x0F), ("lc3_wrap", 0x00FF, 8, 1, 0xF0),
                                  ("uc3_mid", 0x0102, 11, 1, 0xF0), ("uc3_wrap", 0x0102, 8, 1, 0xF0),
                                  ("dc3_mid", 0x0108, 11, 1, 0xF0), ("dc3_wrap", 0x0108, 15, 1, 0xF0))},
    **{n: prog_f(addr, 0, before=f"SCREEN 3:POKE &HF92A,{lo}:POKE &HF92B,{hi}:POKE &HF92C,&HF0",
                 after='SCREEN 0:PRINT "[C";HEX$(PEEK(&HF92A)+256*PEEK(&HF92B));" ";'
                       'HEX$(PEEK(&HF92C));"]"')
       for n, addr, lo, hi in (("tupc3_top", 0x0105, 8, 0), ("tupc3_wrap", 0x0105, 8, 1),
                               ("tdownc3_bot", 0x010B, 15, 0x17), ("tdownc3_wrap", 0x010B, 15, 1),
                               ("tdownc3_b5", 0x010B, 15, 5),     # SCREEN 3's real last cell row
                               ("tdownc3_h8", 0x010B, 15, 8), ("tdownc3_h16", 0x010B, 15, 0x16))},
    **{n: prog(0x0111, 0, bc=x, de=y, before="SCREEN 3:POKE &HFCB7,0:POKE &HFCB8,0",
               after='SCREEN 0:PRINT "[C";HEX$(PEEK(&HF92A)+256*PEEK(&HF92B));" ";'
                     'HEX$(PEEK(&HF92C));" ";HEX$(PEEK(&HFCB7)+256*PEEK(&HFCB8));"]"')
       for n, x, y in (("mxy3_13", 13, 21), ("mxy3_max", 63, 47))},
    **{n: prog(0x011D, 0, before=f"SCREEN 3:POKE &HF92A,8:POKE &HF92B,1:POKE &HF92C,{m}:"
                "VPOKE &H108,&H4F", after="SCREEN 0")
       for n, m in (("readc3_hi", 0xF0), ("readc3_lo", 0x0F))},
    **{n: prog(0x0120, 0, before=f"SCREEN 3:POKE &HF92A,8:POKE &HF92B,1:POKE &HF92C,{m}:"
                "VPOKE &H108,&H4F:POKE &HF3F2,6",
               after='P=VPEEK(&H108):SCREEN 0:PRINT "[C";HEX$(P);"]"')
       for n, m in (("setc3_hi", 0xF0), ("setc3_lo", 0x0F))},
    "nsx3": prog(0x0123, 0, hl=5,
                 before="SCREEN 3:POKE &HF92A,8:POKE &HF92B,1:POKE &HF92C,&H0F:"
                        "VPOKE &H108,&H44:VPOKE &H110,&H44:VPOKE &H118,&H44:POKE &HF3F2,6",
                 after='P=VPEEK(&H108):Q=VPEEK(&H110):R=VPEEK(&H118):SCREEN 0:'
                       'PRINT "[C";HEX$(P);" ";HEX$(Q);" ";HEX$(R);" ";'
                       'HEX$(PEEK(&HF92A)+256*PEEK(&HF92B));" ";HEX$(PEEK(&HF92C));"]":END'),
    # ERAFNK / DSPFNK (D-BIOSCONTRACT, basic/biosfnk.asm; scratchpad/biossweep_fnk2.out):
    # CNSDFG and the key row's first characters (SCREEN 0) or the VRAM byte under it
    # (SCREEN 2, untouched). Cells only (`END` before the [R] print): DE / A are side
    # values, and DSPFNK's CRTCNT is 23 where the VG-8020 keeps 24 (filed).
    "era0": prog(0x00CC, 0, after='A=PEEK(&HF3DE):C=VPEEK(&H399):D=VPEEK(&H39A):PRINT:'
                                  'PRINT "[C";HEX$(A);" ";HEX$(C);" ";HEX$(D);"]":END'),
    "dsp0": prog(0x00CF, 0, before="KEY OFF",
                 after='A=PEEK(&HF3DE):C=VPEEK(&H399):D=VPEEK(&H39A):PRINT:'
                       'PRINT "[C";HEX$(A);" ";HEX$(C);" ";HEX$(D);"]":END'),
    "era2": prog(0x00CC, 0, before="SCREEN 2:VPOKE &H398,7",
                 after='A=PEEK(&HF3DE):B=PEEK(&HF3B1):C=VPEEK(&H398):SCREEN 0:'
                       'PRINT "[C";HEX$(A);" ";HEX$(B);" ";HEX$(C);"]"'),
    "dsp2": prog(0x00CF, 0, before="KEY OFF:SCREEN 2:VPOKE &H398,7",
                 after='A=PEEK(&HF3DE):C=VPEEK(&H398):SCREEN 0:'
                       'PRINT "[C";HEX$(A);" ";HEX$(C);"]":END'),
    # INIFNK (basic/biosfnk.asm): slots 1 and 10 zeroed, INIFNK, then a position-
    # weighted sum over all 160 bytes of FNKSTR ($F87F) -- the defaults restored.
    # Cells only: the VG-8020's HL / BC / A after it are side values.
    "inifnk": prog(0x003E, 0, before="FOR I=0 TO 15:POKE &HF87F+I,0:POKE &HF90F+I,0:NEXT",
                   after='S=0:FOR I=0 TO 159:S=S+PEEK(&HF87F+I)*(I+1):NEXT:'
                         'PRINT "[C";S;"]":END'),
    # the screen-mode setters (D-BIOSCONTRACT (c), cbios-repack/graphics-cursor.patch's
    # settxt): RG0SAV..RG7SAV and SCRMOD read before SCREEN 0 restores. SCREEN 0 holds
    # RG3 / RG5 / RG6 = 0 as on the VG-8020 (C-BIOS kept the previous mode's).
    # DISSCR / ENASCR / WRTVDP whole; the mode setters' HL / DE are side values (`END`).
    **{n: prog(a, 0, bc=bc, before=bf,
               after='A$="":FOR I=0 TO 7:A$=A$+HEX$(PEEK(&HF3DF+I))+",":NEXT:M=PEEK(&HFCAF):'
                     'SCREEN 0:PRINT "[C";A$;M;"]"' + end)
       for n, a, bc, bf, end in (("disscr", 0x0041, 0x1122, "", ""),
                                 ("enascr", 0x0044, 0x1122, "DEFUSR1=&H41:Q=USR1(0)", ""),
                                 ("wrtvdp", 0x0047, 0xF407, "", ""),
                                 ("initxt", 0x006C, 0x1122, "", ":END"),
                                 ("settxt", 0x0078, 0x1122, "", ":END"),
                                 ("totext", 0x00D2, 0x1122, "SCREEN 2", ":END"),
                                 ("init32", 0x006F, 0x1122, "", ":END"),
                                 ("inigrp", 0x0072, 0x1122, "", ":END"),
                                 ("inimlt", 0x0075, 0x1122, "", ":END"))},
    # CLRSPR / INIT32 / INIGRP and sprite attributes (D-BIOSCONTRACT (d), cbios-repack's
    # clrspr_attr): every attribute byte pre-set $5A in SCREEN 1; after the call each
    # sprite's X is KEPT (Y $D1, pattern = its number -- x4 at size 16 --, colour =
    # FORCLR), patterns cleared. Cells only: DE is a side value (the VG-8020 keeps D).
    **{n: prog(a, 0, before=f"SCREEN 1{sz}:FOR I=0 TO 127:VPOKE &H1B00+I,&H5A:NEXT:VPOKE &H3800,&H5A",
               after='A$="":FOR S=0 TO 2:T=S-(S=2)*29:FOR I=0 TO 3:A$=A$+HEX$(VPEEK(&H1B00+T*4+I))+",":'
                     'NEXT:NEXT:P=VPEEK(&H3800):SCREEN 0:PRINT "[C";A$;HEX$(P);"]":END')
       for n, a, sz in (("clrspr8", 0x0069, ""), ("clrspr16", 0x0069, ",2"),
                        ("spa_inigrp", 0x0072, ""), ("spa_init32", 0x006F, ""))},
    # GTASPC (D-NUMBUFASPCT): DE / HL = ASPCT1 / ASPCT2 = $100 / $100 from the prompt
    # on -- and still after numbers were PRINTed and STR$'d (our integer formatter
    # wrote over them until NUMBUF moved to FOUTBUF; scratchpad/biossweep_asp.out)
    "gtaspc": prog(0x0126, 0, before="SCREEN 2", after="SCREEN 0"),
    "gtaspc_print": prog(0x0126, 0, before='PRINT 12345;-321;STR$(777);HEX$(255)'),
    # batch 6 (D-ENTRYTIERS step 5 / D-BIOSCONTRACT, 2026-11-09; scratchpad/
    # biossweep_b6.out, biossweep_inlin.out): the input waits with keys put in KEYBUF
    # first; cells and contract values only (`END`) where side registers differ.
    # INLIN / PINLIN / QINLIN never returned on C-BIOS (basic/biosfnk.asm): BUF "AB",0,
    # HL = BUF - 1, A = $0D. CHGCAP: port C bit 6 set for A <> 0 on BOTH references.
    **{n: prog(a, 0, before=":".join(f"POKE &HFBF0+{i},{ord(c)}" for i, c in enumerate("AB\r"))
                     + ":POKE &HF3FA,&HF0:POKE &HF3FB,&HFB:POKE &HF3F8,&HF3:POKE &HF3F9,&HFB",
               after='A$="":FOR I=0 TO 3:A$=A$+HEX$(PEEK(&HF55E+I))+",":NEXT:PRINT:'
                     'PRINT "[C";A$;HEX$(PEEK(&HD100)+256*PEEK(&HD101));" ";HEX$(PEEK(&HD106));"]":END')
       for n, a in (("inlin", 0x00B1), ("pinlin", 0x00AE), ("qinlin", 0x00B4))},
    "chget": prog(0x009F, 0, before="POKE &HFBF0,81:POKE &HF3FA,&HF0:POKE &HF3FB,&HFB:"
                                    "POKE &HF3F8,&HF1:POKE &HF3F9,&HFB"),
    **{n: prog(0x0132, a, after='PRINT "[C";HEX$(INP(&HAA) AND &H40);"]":END')
       for n, a in (("chgcap0", 0), ("chgcap1", 1))},
    # D-BIOSCONTRACT2 (2026-11-14, scratchpad/bios_contract_inventory.md gap 3): STMOTR's and
    # CHGSND's whole answer is a port C ($AA) bit -- bit 4 the cassette motor (0 = on), bit 7
    # the 1-bit sound output -- and only their registers were diffed. A = $FF is STMOTR's
    # "toggle"; the motor is off at power-on on both machines, so $FF reads as "on" there.
    **{n: prog(0x00F3, a, after='PRINT "[C";HEX$(INP(&HAA) AND &H10);"]":END')
       for n, a in (("stmotr0b", 0), ("stmotr1b", 1), ("stmotrffb", 0xFF))},
    **{n: prog(0x0135, a, after='PRINT "[C";HEX$(INP(&HAA) AND &H80);"]":END')
       for n, a in (("chgsnd0b", 0), ("chgsnd1b", 1))},
    **{n: prog(a, r, after='PRINT "[C";HEX$(PEEK(&HD106));"]":END')
       for n, a, r in (("gtstck0a", 0x00D5, 0), ("gtstck1a", 0x00D5, 1),
                       ("gtpad0a", 0x00DB, 0), ("gtpdl1a", 0x00DE, 1))},
    "chgclr7": prog(0x0062, 0, before="POKE &HF3E9,4:POKE &HF3EA,1:POKE &HF3EB,6",
                    after='PRINT "[C";HEX$(PEEK(&HF3E6));"]":END'),
    "posit": prog(0x00C6, 0, hl=0x0A05,
                  after='X=PEEK(&HF3DD):Y=PEEK(&HF3DC):PRINT:PRINT "[C";X;Y;"]":END'),
    **{n: prog(0x00C9, 0, before=b,
               after='A=PEEK(&HF3DE):C=VPEEK(&H399):PRINT:PRINT "[C";HEX$(A);" ";HEX$(C);"]":END')
       for n, b in (("fnksb_on", "KEY ON"), ("fnksb_off", "KEY OFF"),
                    # D-BIOSRUNG (2026-11-12): the two above agreed with C-BIOS's STUB --
                    # KEY ON / OFF had already done the work. CNSDFG changed BEHIND
                    # BASIC's back separates them: $FF -> FNKSB paints the row, 0 -> it
                    # leaves it (scratchpad/fnksb_run*.out). Registers are "all" in the
                    # published contract and not compared (the END before [R]).
                    ("fnksb_off_ff", "KEY OFF:POKE &HF3DE,255"),
                    ("fnksb_on_00", "KEY ON:POKE &HF3DE,0"))},
    **{n: prog(a, 0, after='A$="":FOR I=0 TO 7:A$=A$+HEX$(PEEK(&HF3DF+I))+",":NEXT:M=PEEK(&HFCAF):'
                           'SCREEN 0:PRINT "[C";A$;M;"]":END')
       for n, a in (("sett32", 0x007B), ("setgrp", 0x007E), ("setmlt", 0x0081))},
    # D-ENTRYTIERS step 5 (2026-11-09): every BIOS entry the sweeps found SAME as the
    # VG-8020 (scratchpad/biossweep_1108.out, biossweep_b5.out, biossweep_b5b.out),
    # called directly -- a witness each in the entry table. ISCNTC / CKCNTC / BREAKX /
    # ISFLIO agree with nothing pending (no STOP, no file I/O): that state only.
    "wrtvrm": prog(0x004D, 0x5A, hl=0x3F10),
    "rdvrm": prog(0x004A, 0, hl=0x3F10, before="VPOKE &H3F10,&H5A"),
    "setrd": prog(0x0050, 0, hl=0x3F10),
    "setwrt": prog(0x0053, 0, hl=0x3F10),
    "filvrm": prog(0x0056, 0x33, bc=4, hl=0x3F20),
    "gttrig0": prog(0x00D8, 0),
    "rdpsg7": prog(0x0096, 7),
    "chsns": prog(0x009C, 0),
    "cnvchr": prog(0x00AB, 0x41),
    "rslreg": prog(0x0138, 0),
    "rdvdp": prog(0x013E, 0),
    "lptstt": prog(0x00A8, 0),
    "kilbuf": prog(0x0156, 0),
    "isflio": prog(0x014A, 0),
    "breakx": prog(0x00B7, 0),
    "fetchc": prog(0x0114, 0, before="SCREEN 2", after="SCREEN 0"),
    "gspsiz": prog(0x008A, 0, before="SCREEN 1,2", after="SCREEN 0"),
    "wrtpsg": prog(0x0093, 8, de=0x000A),
    "chrgtr": prog(0x0010, 0, hl=0xD1FF, before="POKE &HD200,32:POKE &HD201,53:POKE &HD202,0"),
    "getypr": prog(0x0028, 0),
    "iscntc": prog(0x00BA, 0),
    "ckcntc": prog(0x00BD, 0),
    "stmotr": prog(0x00F3, 0),
    "lftq": prog(0x00F6, 0),
    "chgsnd1": prog(0x0135, 1),
    "getvcp": prog(0x0150, 0, de=0, hl=0),
    "getvc2": prog(0x0153, 0, hl=0),
    "chput": prog(0x00A2, 0x41, after="PRINT"),
    # D-BIOSRUNG (2026-11-12): CALBAS ($0159) -- C-BIOS's printed "ERROR:CALLED NON
    # EXISTING BASIC." and stopped. IX = $004D (WRTVRM, the same entry in both ROMs):
    # the cell written and HL / DE / BC / A back (scratchpad/calbas_run.out).
    "calbas": prog(0x0159, 0x5A, hl=0x3F10, ix=0x004D, before="VPOKE &H3F10,0",
                   after='PRINT:PRINT "[C";HEX$(VPEEK(&H3F10));"]"'),
    "outdo": prog(0x0018, 0x42, after="PRINT"),
}
# GRPPRT ($008D), D-BIOSRUNG 2026-11-12: the BIOS entry draws in EVERY mode with the pitch
# from SCRMOD's bit 0 (SCREEN 1 and 3: 4x4 blocks, advance and CR 32; SCREEN 2: 8) -- the
# cursor's move and the registers only: the glyph itself is the font's, and the font is
# C-BIOS's on zerobas (scratchpad/grpprt3_run5.out).
_GXY = ('X=PEEK(&HFCB7)+256*PEEK(&HFCB8):Y=PEEK(&HFCB9)+256*PEEK(&HFCBA):'
        'SCREEN 0:PRINT:PRINT "[C";X;Y;"]"')


def _grp(scr, ch):
    return prog(0x008D, ch, before=f"SCREEN {scr}:POKE &HFCB7,10:POKE &HFCB8,0:"
                                   "POKE &HFCB9,13:POKE &HFCBA,0", after=_GXY)


ROWS.update({
    "grpprt2":    _grp(2, 0x41),
    "grpprt3":    _grp(3, 0x41),
    "grpprt3_cr": _grp(3, 13),
    "grpprt1":    _grp(1, 0x41),
})


def read(machine, p):
    scr = omsx_repl.run_cases(machine, [("direct", p)], batch=False,
                              reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=20.0)[0]
    if not scr:
        return None
    r = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)]
    return " | ".join(x for x in r if x.startswith("[R") or x.startswith("[C") or "rror" in x) or None


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
