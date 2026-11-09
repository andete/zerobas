#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ENTRYTIERS (step 5's next list): main BIOS calls the entry table counts NOT
MEASURED, called DIRECTLY -- VG-8020 against zerobas.

Reuses probes/basic/basic_probe_biosregs.py's stub (our own code: A / BC / DE / HL
loaded, the entry called, HL / DE / BC / A stored and printed; F not compared -- no
documented contract). A first batch of SAFE entries only: no tape, no format, no
slot switching, nothing that waits for input or loops. Graphics-cursor helpers run
in SCREEN 2 and print after SCREEN 0, the biosregs `S1` way.

    python3 -u scratchpad/biossweep_probe.py [ROW ...]
"""
import os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import basic_probe_biosregs as B   # noqa: E402  (prog, read, MACHINES)

S2 = dict(before="SCREEN 2", after="SCREEN 0")
ROWS = {
    "wrtvrm":  B.prog(0x004D, 0x5A, hl=0x3F10),
    "rdvrm":   B.prog(0x004A, 0, hl=0x3F10, before="VPOKE &H3F10,&H5A"),
    "setrd":   B.prog(0x0050, 0, hl=0x3F10),
    "setwrt":  B.prog(0x0053, 0, hl=0x3F10),
    "filvrm":  B.prog(0x0056, 0x33, bc=4, hl=0x3F20),
    "chgclr":  B.prog(0x0062, 0),
    "gtstck0": B.prog(0x00D5, 0),
    "gtstck1": B.prog(0x00D5, 1),
    "gttrig0": B.prog(0x00D8, 0),
    "gttrig1": B.prog(0x00D8, 1),
    "gtpdl1":  B.prog(0x00DE, 1),
    "gtpad0":  B.prog(0x00DB, 0),
    "rdpsg7":  B.prog(0x0096, 7),
    "chsns":   B.prog(0x009C, 0),
    "cnvchr":  B.prog(0x00AB, 0x41),
    "posit":   B.prog(0x00C6, 0, hl=0x0505),
    "snsmat0": B.prog(0x0141, 0),
    "snsmat8": B.prog(0x0141, 8),
    "rslreg":  B.prog(0x0138, 0),
    "rdvdp":   B.prog(0x013E, 0),
    "lptstt":  B.prog(0x00A8, 0),
    "kilbuf":  B.prog(0x0156, 0),
    "isflio":  B.prog(0x014A, 0),
    "breakx":  B.prog(0x00B7, 0),
    "scalxy":  B.prog(0x010E, 0, bc=300, de=200, **S2),
    "mapxyc":  B.prog(0x0111, 0, bc=10, de=10, **S2),
    "fetchc":  B.prog(0x0114, 0, **S2),
    "upc":     B.prog(0x0102, 0, **S2),
    "downc":   B.prog(0x0108, 0, **S2),
    "leftc":   B.prog(0x00FF, 0, **S2),
    "rightc":  B.prog(0x00FC, 0, **S2),
    "gtaspc":  B.prog(0x0126, 0, **S2),
    "readc":   B.prog(0x011D, 0, **S2),
    "setatr":  B.prog(0x011A, 5, **S2),
    # SCALXY's clipping, for the D-BIOSCONTRACT fix: in range, both negative, both over;
    # SCREEN 2 and SCREEN 3 (multicolour, 64 x 48)
    "sxy2in":  B.prog(0x010E, 0, bc=100, de=100, **S2),
    "sxy2neg": B.prog(0x010E, 0, bc=0xFFFB, de=0xFFFB, **S2),
    "sxy3over": B.prog(0x010E, 0, bc=300, de=200, before="SCREEN 3", after="SCREEN 0"),
    "sxy3in":  B.prog(0x010E, 0, bc=100, de=100, before="SCREEN 3", after="SCREEN 0"),
    "gtaspc0": B.prog(0x0126, 0),
    "sxy2xov": B.prog(0x010E, 0, bc=300, de=100, **S2),
    "sxy2yov": B.prog(0x010E, 0, bc=100, de=200, **S2),
    # the aspect cells GTASPC returns, read straight from RAM (HL = $F40B, DE = $F40D)
    "aspct":   B.prog(0x0000 + 0x0020, 0, de=0, hl=0, before="POKE &HD200,0",
                      after='PRINT "[ASP";HEX$(PEEK(&HF40B)+256*PEEK(&HF40C));HEX$(PEEK(&HF40D)+256*PEEK(&HF40E));"]"'),
}


# the cursor moves (D-BIOSCONTRACT): CLOC / CMASK set by POKE in SCREEN 2, the entry
# called, both cells printed after (the move's whole effect is on them, not on the
# registers). Starting points at the edges each move wraps over.
def cur(addr, cloc, cmask):
    setup = f"SCREEN 2:POKE &HF92A,{cloc & 255}:POKE &HF92B,{cloc >> 8}:POKE &HF92C,{cmask}"
    show = ('SCREEN 0:PRINT "[C";HEX$(PEEK(&HF92A)+256*PEEK(&HF92B));" ";HEX$(PEEK(&HF92C));"]"')
    return B.prog(addr, 0, before=setup, after=show)


CUR = {
    "rc_mid":  cur(0x00FC, 0x0108, 0x10),   # RIGHTC inside a byte
    "rc_wrap": cur(0x00FC, 0x0108, 0x01),   # RIGHTC off the byte's last pixel
    "lc_mid":  cur(0x00FF, 0x0108, 0x10),   # LEFTC inside a byte
    "lc_wrap": cur(0x00FF, 0x0108, 0x80),   # LEFTC off the first pixel
    "uc_mid":  cur(0x0102, 0x010B, 0x10),   # UPC inside a character cell (row 3)
    "uc_wrap": cur(0x0102, 0x0108, 0x10),   # UPC off the cell's top row
    "dc_mid":  cur(0x0108, 0x010B, 0x10),   # DOWNC inside a cell
    "dc_wrap": cur(0x0108, 0x010F, 0x10),   # DOWNC off the cell's bottom row
}
ROWS.update(CUR)


def read2(machine, p):
    import omsx_repl
    scr = omsx_repl.run_cases(machine, [("direct", p)], batch=False,
                              reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=20.0)[0]
    if not scr:
        return None
    r = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)]
    return " | ".join(x for x in r if x.startswith("[R") or x.startswith("[C") or "rror" in x) or None


B.read = read2


def prog_f(addr, a=0, bc=0x1122, de=0x3344, hl=0x5566, before="", after=""):
    """B.prog with F captured too: `push af` right after the call, popped after the
    register stores into $D10A (low byte = F), printed as [F..]."""
    body = [0x01, bc & 255, bc >> 8, 0x11, de & 255, de >> 8, 0x21, hl & 255, hl >> 8,
            0x3E, a, 0xCD, addr & 255, addr >> 8, 0xF5,
            0x22, 0x00, 0xD1, 0xED, 0x53, 0x02, 0xD1, 0xED, 0x43, 0x04, 0xD1,
            0x32, 0x06, 0xD1, 0xE1, 0x22, 0x0A, 0xD1, 0xC9]
    p = B.prog(addr, a, bc, de, hl, before=before, after=after)
    # replace the DATA lines with this stub's bytes and add the F print
    p = [l for l in p if not (l.startswith("60 DATA") or l.startswith("70 DATA"))]
    i = p.index("RUN")
    p[i:i] = ["60 DATA " + ",".join(str(b) for b in body[:40])]
    p = [l.replace("FOR I=0 TO " + l.split("FOR I=0 TO ")[1].split(":")[0], f"FOR I=0 TO {len(body) - 1}")
         if l.startswith("20 FOR") else l for l in p]
    p = [l.replace(';"]"', ';" F";HEX$(PEEK(&HD10A));"]"') if l.startswith("50 PRINT") else l for l in p]
    return p


def vram(before_extra, show):
    return f"SCREEN 2:{before_extra}", f"SCREEN 0:PRINT \"[C\";{show};\"]\""


SHOWC = 'HEX$(PEEK(&HF92A)+256*PEEK(&HF92B));" ";HEX$(PEEK(&HF92C))'
SHOWV = 'HEX$(VPEEK(&H108));" ";HEX$(VPEEK(&H2108))'
SET1 = "POKE &HF92A,8:POKE &HF92B,1:POKE &HF92C,16:VPOKE &H108,16:VPOKE &H2108,&H4F"
MORE = {
    "storec": B.prog(0x0117, 0x40, hl=0x1234, after=f'PRINT "[C";{SHOWC};"]"'),
    "setatr5": B.prog(0x011A, 5, after='PRINT "[C";HEX$(PEEK(&HF3F2));"]"'),
    "setatr16": prog_f(0x011A, 16, before="POKE &HF3F2,7", after='PRINT "[C";HEX$(PEEK(&HF3F2));"]"'),
    "readc_fg": B.prog(0x011D, 0, before="SCREEN 2:" + SET1, after="SCREEN 0"),
    "readc_bg": B.prog(0x011D, 0, before="SCREEN 2:" + SET1 + ":POKE &HF92C,32", after="SCREEN 0"),
    "setc_new": B.prog(0x0120, 0, before="SCREEN 2:" + SET1 + ":VPOKE &H108,0:POKE &HF3F2,6",
                       after=f'SCREEN 0:PRINT "[C";{SHOWV};"]"'),
    "setc_bg": B.prog(0x0120, 0, before="SCREEN 2:" + SET1 + ":POKE &HF3F2,15",
                      after=f'SCREEN 0:PRINT "[C";{SHOWV};"]"'),
    "setc_fg": B.prog(0x0120, 0, before="SCREEN 2:" + SET1 + ":VPOKE &H108,0:POKE &HF3F2,4",
                      after=f'SCREEN 0:PRINT "[C";{SHOWV};"]"'),
    "tupc_top": prog_f(0x0105, 0, before="SCREEN 2:POKE &HF92A,8:POKE &HF92B,0:POKE &HF92C,16",
                       after=f'SCREEN 0:PRINT "[C";{SHOWC};"]"'),
    "tupc_mid": prog_f(0x0105, 0, before="SCREEN 2:POKE &HF92A,11:POKE &HF92B,1:POKE &HF92C,16",
                       after=f'SCREEN 0:PRINT "[C";{SHOWC};"]"'),
    "tdownc_bot": prog_f(0x010B, 0, before="SCREEN 2:POKE &HF92A,&H0F:POKE &HF92B,&H17:POKE &HF92C,16",
                         after=f'SCREEN 0:PRINT "[C";{SHOWC};"]"'),
    "tdownc_mid": prog_f(0x010B, 0, before="SCREEN 2:POKE &HF92A,11:POKE &HF92B,1:POKE &HF92C,16",
                         after=f'SCREEN 0:PRINT "[C";{SHOWC};"]"'),
}
ROWS.update(MORE)
# SETC again, VRAM read BEFORE leaving SCREEN 2 (the first cut VPEEKed after SCREEN 0,
# which rebuilds the pattern table): pattern / colour byte of the cursor's cell
SHOW2 = 'P=VPEEK(&H108):C=VPEEK(&H2108):SCREEN 0:PRINT "[C";HEX$(P);" ";HEX$(C);"]"'
ROWS.update({
    "setc2_new": B.prog(0x0120, 0, before="SCREEN 2:" + SET1 + ":VPOKE &H108,0:POKE &HF3F2,6", after=SHOW2),
    "setc2_bg":  B.prog(0x0120, 0, before="SCREEN 2:" + SET1 + ":POKE &HF3F2,15", after=SHOW2),
    "setc2_fg":  B.prog(0x0120, 0, before="SCREEN 2:" + SET1 + ":VPOKE &H108,0:POKE &HF3F2,4", after=SHOW2),
    "setc2_set": B.prog(0x0120, 0, before="SCREEN 2:" + SET1 + ":POKE &HF3F2,6", after=SHOW2),
})

# MAPXYC (D-BIOSCONTRACT): CLOC / CMASK and GRPACX / GRPACY ($FCB7 / $FCB9, POKEd 0
# first) after the call, in SCREEN 2
SHOWM = ('SCREEN 0:PRINT "[C";' + SHOWC + ';" ";HEX$(PEEK(&HFCB7)+256*PEEK(&HFCB8));'
         '" ";HEX$(PEEK(&HFCB9)+256*PEEK(&HFCBA));"]"')
ZG = "SCREEN 2:POKE &HFCB7,0:POKE &HFCB8,0:POKE &HFCB9,0:POKE &HFCBA,0"
ROWS.update({
    "mxy_10":  B.prog(0x0111, 0, bc=10, de=10, before=ZG, after=SHOWM),
    "mxy_13":  B.prog(0x0111, 0, bc=13, de=21, before=ZG, after=SHOWM),
    "mxy_0":   B.prog(0x0111, 0, bc=0, de=0, before=ZG, after=SHOWM),
    "mxy_max": B.prog(0x0111, 0, bc=255, de=191, before=ZG, after=SHOWM),
})

# GRPPRT (C-BIOS's own, $008D) after MAPXYC's fix: 'A' at GRPACX 10 / GRPACY 13 (row 5
# of its cell, so the glyph straddles two cells), weighted sums of the two cells' bytes
GP = ('P=0:Q=0:FOR I=0 TO 7:P=P+VPEEK(&H108+I)*(I+1):Q=Q+VPEEK(&H208+I)*(I+1):NEXT:'
      'SCREEN 0:PRINT "[C";P;Q;"]"')
GPR = ('S$="":FOR I=0 TO 7:S$=S$+RIGHT$("0"+HEX$(VPEEK(&H108+I)),2):NEXT:'
       'T$="":FOR I=0 TO 7:T$=T$+RIGHT$("0"+HEX$(VPEEK(&H208+I)),2):NEXT:'
       'SCREEN 0:PRINT "[C";S$;" ";T$;"]"')
ROWS.update({
    "grpprt_raw": B.prog(0x008D, 0x41, before="SCREEN 2:POKE &HFCB7,10:POKE &HFCB8,0:"
                         "POKE &HFCB9,13:POKE &HFCBA,0", after=GPR),
    "grpprt": B.prog(0x008D, 0x41, before="SCREEN 2:POKE &HFCB7,10:POKE &HFCB8,0:"
                     "POKE &HFCB9,13:POKE &HFCBA,0", after=GP),
})

# TUPC / TDOWNC across a cell edge that is NOT the screen's (F unmeasured until now)
ROWS.update({
    "tupc_wrap": prog_f(0x0105, 0, before="SCREEN 2:POKE &HF92A,8:POKE &HF92B,1:POKE &HF92C,16",
                        after=f'SCREEN 0:PRINT "[C";{SHOWC};"]"'),
    "tdownc_wrap": prog_f(0x010B, 0, before="SCREEN 2:POKE &HF92A,15:POKE &HF92B,1:POKE &HF92C,16",
                          after=f'SCREEN 0:PRINT "[C";{SHOWC};"]"'),
})

# UPC / DOWNC across the cell edge with F (the wrap path's flags)
ROWS.update({
    "uc_wrapf": prog_f(0x0102, 0, before="SCREEN 2:POKE &HF92A,8:POKE &HF92B,1:POKE &HF92C,16",
                       after=f'SCREEN 0:PRINT "[C";{SHOWC};"]"'),
    "dc_wrapf": prog_f(0x0108, 0, before="SCREEN 2:POKE &HF92A,15:POKE &HF92B,1:POKE &HF92C,16",
                       after=f'SCREEN 0:PRINT "[C";{SHOWC};"]"'),
})

# NSETCX ($0123): HL pixels from CLOC / CMASK rightward in ATRBYT. Start: pixel 2 of the
# byte at $108 (CMASK $20); two adjacent bytes $108 / $110 and their colour bytes read
# while still in SCREEN 2, then CLOC / CMASK
def nsx(hl, atr, pat):
    setup = ("SCREEN 2:POKE &HF92A,8:POKE &HF92B,1:POKE &HF92C,32:"
             f"VPOKE &H108,{pat}:VPOKE &H110,{pat}:VPOKE &H2108,&H4F:VPOKE &H2110,&H4F:POKE &HF3F2,{atr}")
    show = ('P=VPEEK(&H108):Q=VPEEK(&H110):C=VPEEK(&H2108):D=VPEEK(&H2110):'
            'SCREEN 0:PRINT "[C";HEX$(P);" ";HEX$(Q);" ";HEX$(C);" ";HEX$(D);" ";' + SHOWC + ';"]"')
    return prog_f(0x0123, 0, hl=hl, before=setup, after=show)


ROWS.update({
    "nsx_new": nsx(12, 6, 0),      # a new colour across two bytes
    "nsx_bg":  nsx(12, 15, 255),   # the background colour: bits cleared?
    "nsx_fg":  nsx(12, 4, 0),      # the foreground already
    "nsx_one": nsx(1, 6, 0),
    "nsx_zero": nsx(0, 6, 0),
})

# D-ENTRYTIERS step 5, batch 5 (2026-11-09): the NOT MEASURED entries that are safe to
# call directly -- no input wait, no tape / disk / printer, no slot switch. A mode
# setter's effect is read from the VDP register copies RG0SAV..RG7SAV ($F3DF) and
# SCRMOD ($FCAF) BEFORE SCREEN 0 restores the text screen.
RGS = ('A$="":FOR I=0 TO 7:A$=A$+HEX$(PEEK(&HF3DF+I))+",":NEXT:M=PEEK(&HFCAF):'
       'SCREEN 0:PRINT "[C";A$;M;"]"')
CS = 'PRINT "[C";HEX$(PEEK(&HF3DE));"]"'
B5 = {
    "disscr":  B.prog(0x0041, 0, after=RGS),
    "enascr":  B.prog(0x0044, 0, before="DEFUSR1=&H41:Q=USR1(0)", after=RGS),
    "wrtvdp":  B.prog(0x0047, 0, bc=0xF407, after=RGS),
    "initxt":  B.prog(0x006C, 0, after=RGS),
    "init32":  B.prog(0x006F, 0, after=RGS),
    "inigrp":  B.prog(0x0072, 0, after=RGS),
    "inimlt":  B.prog(0x0075, 0, after=RGS),
    "settxt":  B.prog(0x0078, 0, after=RGS),
    "sett32":  B.prog(0x007B, 0, after=RGS),
    "setgrp":  B.prog(0x007E, 0, after=RGS),
    "setmlt":  B.prog(0x0081, 0, after=RGS),
    "clrspr":  B.prog(0x0069, 0, before="SCREEN 1:VPOKE &H1B00,5:VPOKE &H1B01,6",
                      after='P=VPEEK(&H1B00):Q=VPEEK(&H1B01):R=VPEEK(&H1B03):SCREEN 0:'
                            'PRINT "[C";HEX$(P);" ";HEX$(Q);" ";HEX$(R);"]"'),
    "gspsiz":  B.prog(0x008A, 0, before="SCREEN 1,2", after="SCREEN 0"),
    "wrtpsg":  B.prog(0x0093, 8, de=0x000A),
    "strtms":  B.prog(0x0099, 0),
    "chput":   B.prog(0x00A2, 0x41, after="PRINT"),
    "outdo":   B.prog(0x0018, 0x42, after="PRINT"),
    "chrgtr":  B.prog(0x0010, 0, hl=0xD1FF, before="POKE &HD200,32:POKE &HD201,53:POKE &HD202,0"),
    "getypr":  B.prog(0x0028, 0),
    "iscntc":  B.prog(0x00BA, 0),
    "ckcntc":  B.prog(0x00BD, 0),
    "beep":    B.prog(0x00C0, 0),
    "fnksb":   B.prog(0x00C9, 0, after=CS),
    "erafnk":  B.prog(0x00CC, 0, after=CS),
    "dspfnk":  B.prog(0x00CF, 0, before="KEY OFF", after=CS),
    "totext":  B.prog(0x00D2, 0, before="SCREEN 2", after=RGS),
    "stmotr":  B.prog(0x00F3, 0),
    "lftq":    B.prog(0x00F6, 0),
    "putq":    B.prog(0x00F9, 0, de=0x0041),
    "chgcap1": B.prog(0x0132, 1),
    "chgsnd1": B.prog(0x0135, 1),
    "getvcp":  B.prog(0x0150, 0, de=0, hl=0),
    "getvc2":  B.prog(0x0153, 0, hl=0),
    "inifnk":  B.prog(0x003E, 0, before="POKE &HF87F,0:POKE &HF880,0",
                      after='PRINT "[C";HEX$(PEEK(&HF87F));" ";HEX$(PEEK(&HF880));" ";HEX$(PEEK(&HF88F));"]"'),
    "initio":  B.prog(0x003B, 0),
}
ROWS.update(B5)

# ERAFNK / DSPFNK in full (2026-11-09): CNSDFG ($F3DE), CRTCNT ($F3B1), row 23's
# first characters (SCREEN 0, WIDTH 37 at boot: NAMBAS + 23*40 = $398), and in SCREEN 2
# the pattern byte at $398 (marked 7 first) -- read before SCREEN 0 repaints
FK0 = ('A=PEEK(&HF3DE):B=PEEK(&HF3B1):C=VPEEK(&H399):D=VPEEK(&H39A):E=VPEEK(&H39B):'
       'PRINT:PRINT "[C";HEX$(A);" ";HEX$(B);" ";HEX$(C);" ";HEX$(D);" ";HEX$(E);"]"')
FK2 = ('A=PEEK(&HF3DE):B=PEEK(&HF3B1):C=VPEEK(&H398):SCREEN 0:'
       'PRINT "[C";HEX$(A);" ";HEX$(B);" ";HEX$(C);"]"')
ROWS.update({
    "era0":  B.prog(0x00CC, 0, after=FK0),
    "dsp0":  B.prog(0x00CF, 0, before="KEY OFF", after=FK0),
    "era2":  B.prog(0x00CC, 0, before="SCREEN 2:VPOKE &H398,7", after=FK2),
    "dsp2":  B.prog(0x00CF, 0, before="KEY OFF:SCREEN 2:VPOKE &H398,7", after=FK2),
})

CRT = 'PRINT:PRINT "[C";HEX$(PEEK(&HF3B1));" ";HEX$(PEEK(&HF3DE));"]"'
ROWS.update({
    "crt_boot": B.prog(0x0028, 0, after=CRT),
    "crt_off":  B.prog(0x0028, 0, before="KEY OFF", after=CRT),
    "crt_on":   B.prog(0x0028, 0, before="KEY OFF:KEY ON", after=CRT),
})

# the TXT* base table ($F3B3 TXTNAM .. $F3BC), both machines, at the prompt
ROWS["txttab"] = B.prog(0x0028, 0, after='A$="":FOR I=0 TO 9:A$=A$+HEX$(PEEK(&HF3B3+I))+",":NEXT:PRINT "[C";A$;"]"')

# CLRSPR in full: sprites 0, 1, 31 -- all four attribute bytes ($1B00 in SCREEN 1),
# every byte pre-set to $5A, and the first pattern byte ($3800)
CSP = ('A$="":FOR S=0 TO 31 STEP 1:IF S=0 OR S=1 OR S=31 THEN FOR I=0 TO 3:'
       'A$=A$+HEX$(VPEEK(&H1B00+S*4+I))+",":NEXT:A$=A$+"/"'
       '\nNEXT')
ROWS.update({
    "clrspr8":  B.prog(0x0069, 0, before="SCREEN 1:FOR I=0 TO 127:VPOKE &H1B00+I,&H5A:NEXT:VPOKE &H3800,&H5A",
                       after='A$="":FOR S=0 TO 2:T=S-(S=2)*29:FOR I=0 TO 3:A$=A$+HEX$(VPEEK(&H1B00+T*4+I))+",":NEXT:NEXT:'
                             'P=VPEEK(&H3800):SCREEN 0:PRINT "[C";A$;HEX$(P);"]"'),
    "clrspr16": B.prog(0x0069, 0, before="SCREEN 1,2:FOR I=0 TO 127:VPOKE &H1B00+I,&H5A:NEXT:VPOKE &H3800,&H5A",
                       after='A$="":FOR S=0 TO 2:T=S-(S=2)*29:FOR I=0 TO 3:A$=A$+HEX$(VPEEK(&H1B00+T*4+I))+",":NEXT:NEXT:'
                             'P=VPEEK(&H3800):SCREEN 0:PRINT "[C";A$;HEX$(P);"]"'),
})

# what the mode inits leave in sprite 0's / 1's attributes ($1B00, pre-set $5A in SCREEN 1)
SPA = ('A$="":FOR I=0 TO 7:A$=A$+HEX$(VPEEK(&H1B00+I))+",":NEXT:SCREEN 0:PRINT "[C";A$;"]"')
PRE = "SCREEN 1:FOR I=0 TO 127:VPOKE &H1B00+I,&H5A:NEXT"
ROWS.update({
    "spa_inigrp": B.prog(0x0072, 0, before=PRE, after=SPA),
    "spa_init32": B.prog(0x006F, 0, before=PRE, after=SPA),
    "spa_scr2":   B.prog(0x0028, 0, before=PRE + ":SCREEN 2", after=SPA),
})

# ASPCT1 / ASPCT2 after numbers have been PRINTed and STR$'d (NUMBUF overwrote them)
ROWS["aspct_print"] = B.prog(0x0126, 0, before='PRINT 12345;-321;STR$(777)',
                             after='PRINT "[ASP";HEX$(PEEK(&HF40B)+256*PEEK(&HF40C));HEX$(PEEK(&HF40D)+256*PEEK(&HF40E));"]"')

# D-ENTRYTIERS step 5, batch 6 (2026-11-09): the rest that can be witnessed directly.
# Keys for the input waits are put in KEYBUF ($FBF0) with GETPNT / PUTPNT ($F3FA /
# $F3F8) around them, so the call returns at once.
def keys(txt):
    pk = ":".join(f"POKE &HFBF0+{i},{ord(c)}" for i, c in enumerate(txt))
    return (pk + f":POKE &HF3FA,&HF0:POKE &HF3FB,&HFB:POKE &HF3F8,{0xF0 + len(txt)}:POKE &HF3F9,&HFB")
AONLY = 'PRINT "[C";HEX$(PEEK(&HD106));"]":END'
BUFS = ('A$="":FOR I=0 TO 3:A$=A$+HEX$(PEEK(&HF55E+I))+",":NEXT:PRINT:PRINT "[C";A$;"]"')
B6 = {
    "sett32c":  B.prog(0x007B, 0, after=RGS),
    "setgrpc":  B.prog(0x007E, 0, after=RGS),
    "setmltc":  B.prog(0x0081, 0, after=RGS),
    "gtstck0a": B.prog(0x00D5, 0, after=AONLY),
    "gtstck1a": B.prog(0x00D5, 1, after=AONLY),
    "gtpad0a":  B.prog(0x00DB, 0, after=AONLY),
    "gtpdl1a":  B.prog(0x00DE, 1, after=AONLY),
    "chgclr7":  B.prog(0x0062, 0, before="POKE &HF3E9,4:POKE &HF3EA,1:POKE &HF3EB,6",
                       after='PRINT "[C";HEX$(PEEK(&HF3E6));"]"'),
    "chgcap0":  B.prog(0x0132, 0, after='PRINT "[C";HEX$(INP(&HAA) AND &H40);"]"'),
    "chgcap1":  B.prog(0x0132, 1, after='PRINT "[C";HEX$(INP(&HAA) AND &H40);"]"'),
    "chget":    B.prog(0x009F, 0, before=keys("Q")),
    "inlin":    B.prog(0x00B1, 0, before=keys("AB\r"), after=BUFS),
    "pinlin":   B.prog(0x00AE, 0, before=keys("AB\r"), after=BUFS),
    "qinlin":   B.prog(0x00B4, 0, before=keys("AB\r"), after=BUFS),
    "posit":    B.prog(0x00C6, 0, hl=0x0A05,
                       after='X=PEEK(&HF3DD):Y=PEEK(&HF3DC):PRINT:PRINT "[C";X;Y;"]"'),
    "fnksb_on": B.prog(0x00C9, 0, before="KEY ON",
                       after='A=PEEK(&HF3DE):C=VPEEK(&H399):PRINT:PRINT "[C";HEX$(A);" ";HEX$(C);"]":END'),
    "fnksb_off": B.prog(0x00C9, 0, before="KEY OFF",
                        after='A=PEEK(&HF3DE):C=VPEEK(&H399):PRINT:PRINT "[C";HEX$(A);" ";HEX$(C);"]":END'),
}
ROWS.update(B6)


def main():
    only = sys.argv[1:] or list(ROWS)
    bad, blind = [], []
    for name in only:
        got = {side: B.read(m, ROWS[name]) for side, m in B.MACHINES}
        if not got["VG"]:
            verdict = "NO-REFERENCE"
            blind.append(name)
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name:8} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    print(f"\n{len(only) - len(bad) - len(blind)} SAME, {len(bad)} DIVERGE"
          + (f" ({', '.join(bad)})" if bad else "")
          + (f", {len(blind)} no reference reading ({', '.join(blind)})" if blind else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
