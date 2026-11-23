<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# The MSX2 / MSX2+ BIOS — inventory

**References:** Sony HB-F900 (openMSX `msx2`), Philips NMS 8250 (`msx2_eu`), Panasonic FS-A1WSX (`msx2plus`) — Joost's ruling, 2026-11-23.
**Subject:** C-BIOS's MSX2 and MSX2+ builds.
**Method:** [docs/spec-method.md](../spec-method.md) — one page per call, `docs/msx2/main/<NAME>.md` or `docs/msx2/sub/<NAME>.md`; shared facts in [concepts/](concepts/).

Every entry the MSX2 and MSX2+ add to the main ROM's jump table, and every sub-ROM entry. Sources
for the list: the MSX2 Technical Handbook, Konamiman's English translation — Appendix 1 (**TH App. 1**,
the BIOS listing incl. the sub-ROM) and Appendix 3 (**TH App. 3**, the block-transfer calls); and the
MSX Assembly Page's compiled BIOS lists (`map.grauw.nl/resources/msxbios.php`, `subrom.php`; **MAP**,
rated C / scoped in [allowed-sources.md](../allowed-sources.md): names and addresses only, corroborate
against the handbook). The MSX2+ adds RDRES / WRRES to the main ROM and, per MAP, no new sub-ROM
entry; its changes to existing sub-ROM entries (SCREEN 10-12) are on those entries' pages.

The **C-BIOS** column is read from C-BIOS's jump tables (`main.asm` $015C-$0189, `sub.asm`) and the
body each entry jumps to: **implemented**; **partial** (part of the body prints a debug message and
returns); **stub** (the whole body prints a debug message and returns); **missing** (no jump at the
address). It says nothing about whether an implemented body matches the references.

**Counts.** Main ROM: 12 entries, 10 MSX2 + 2 MSX2+; C-BIOS has all 12 (RDRES / WRRES in its MSX2+
build only). Sub-ROM: 88 addresses, all MSX2 (none added by the MSX2+) — 67 BIOS calls, 20 BASIC
statement internals and 1 reserved entry. Of the 67 calls, 43 are in the handbook (36 in App. 1, 7 in
App. 3) and 24 only in MAP. C-BIOS: 46 implemented, 2 partial, 13 stub, 6 missing (DSPFNK, DELLNO,
INSLNO, PUTVRM, KYKLOK, PUTCHR); the 20 BASIC internals and RESVI are missing too. Turbo R entries
(CHGCPU, GETCPU, PCMPLY, PCMREC): out of scope.

| address | name | ROM | standard | C-BIOS | listed in | page | note |
|---|---|---|---|---|---|---|---|
| $015C | SUBROM | main | MSX2 | implemented | TH App. 1 | [main/SUBROM.md](main/SUBROM.md) |  |
| $015F | EXTROM | main | MSX2 | implemented | TH App. 1 | [main/EXTROM.md](main/EXTROM.md) |  |
| $0162 | CHKSLZ | main | MSX2 | implemented | MAP only | [main/CHKSLZ.md](main/CHKSLZ.md) | not in the handbook's listing |
| $0165 | CHKNEW | main | MSX2 | implemented | MAP only | [main/CHKNEW.md](main/CHKNEW.md) | not in the handbook's listing |
| $0168 | EOL | main | MSX2 | implemented | TH App. 1 | [main/EOL.md](main/EOL.md) |  |
| $016B | BIGFIL | main | MSX2 | implemented | TH App. 1 | [main/BIGFIL.md](main/BIGFIL.md) |  |
| $016E | NSETRD | main | MSX2 | implemented | TH App. 1 | [main/NSETRD.md](main/NSETRD.md) |  |
| $0171 | NSETWR | main | MSX2 | implemented | TH App. 1 | [main/NSETWR.md](main/NSETWR.md) | the handbook spells it NSTWRT |
| $0174 | NRDVRM | main | MSX2 | implemented | TH App. 1 | [main/NRDVRM.md](main/NRDVRM.md) |  |
| $0177 | NWRVRM | main | MSX2 | implemented | TH App. 1 | [main/NWRVRM.md](main/NWRVRM.md) |  |
| $017A | RDRES | main | MSX2+ | implemented (MSX2+ build only) | MAP only | [main/RDRES.md](main/RDRES.md) | reads I/O port $F4 |
| $017D | WRRES | main | MSX2+ | implemented (MSX2+ build only) | MAP only | [main/WRRES.md](main/WRRES.md) | writes I/O port $F4 |
| $0180 | CHGCPU | main | turbo R | missing | MAP only | [../turbor/main/CHGCPU.md](../turbor/main/CHGCPU.md) | the turbo R pages: [../turbor/index.md](../turbor/index.md) |
| $0183 | GETCPU | main | turbo R | missing | MAP only | [../turbor/main/GETCPU.md](../turbor/main/GETCPU.md) | the turbo R pages: [../turbor/index.md](../turbor/index.md) |
| $0186 | PCMPLY | main | turbo R | missing | MAP only | [../turbor/main/PCMPLY.md](../turbor/main/PCMPLY.md) | the turbo R pages: [../turbor/index.md](../turbor/index.md) |
| $0189 | PCMREC | main | turbo R | missing | MAP only | [../turbor/main/PCMREC.md](../turbor/main/PCMREC.md) | the turbo R pages: [../turbor/index.md](../turbor/index.md) |
| $0069 | PAINT | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $006D | PSET | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $0071 | ATRSCN | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $0075 | GLINE | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $0079 | DOBOXF | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $007D | DOLINE | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $0081 | BOXLIN | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $0085 | DOGRPH | sub | MSX2 | stub | MAP only | [sub/DOGRPH.md](sub/DOGRPH.md) | hook H.DOGR names it (handbook App. 4) |
| $0089 | GRPPRT | sub | MSX2 | implemented | TH App. 1 | [sub/GRPPRT.md](sub/GRPPRT.md) | the handbook spells it GRPRT |
| $008D | SCALXY | sub | MSX2 | implemented | MAP only | [sub/SCALXY.md](sub/SCALXY.md) |  |
| $0091 | MAPXYC | sub | MSX2 | implemented | MAP only | [sub/MAPXYC.md](sub/MAPXYC.md) |  |
| $0095 | READC | sub | MSX2 | implemented | MAP only | [sub/READC.md](sub/READC.md) |  |
| $0099 | SETATR | sub | MSX2 | implemented | MAP only | [sub/SETATR.md](sub/SETATR.md) |  |
| $009D | SETC | sub | MSX2 | implemented | MAP only | [sub/SETC.md](sub/SETC.md) |  |
| $00A1 | TRIGHT | sub | MSX2 | stub | MAP only | [sub/TRIGHT.md](sub/TRIGHT.md) |  |
| $00A5 | RIGHTC | sub | MSX2 | implemented | MAP only | [sub/RIGHTC.md](sub/RIGHTC.md) |  |
| $00A9 | TLEFTC | sub | MSX2 | stub | MAP only | [sub/TLEFTC.md](sub/TLEFTC.md) |  |
| $00AD | LEFTC | sub | MSX2 | implemented | MAP only | [sub/LEFTC.md](sub/LEFTC.md) |  |
| $00B1 | TDOWNC | sub | MSX2 | implemented | MAP only | [sub/TDOWNC.md](sub/TDOWNC.md) |  |
| $00B5 | DOWNC | sub | MSX2 | implemented | MAP only | [sub/DOWNC.md](sub/DOWNC.md) |  |
| $00B9 | TUPC | sub | MSX2 | implemented | MAP only | [sub/TUPC.md](sub/TUPC.md) |  |
| $00BD | UPC | sub | MSX2 | implemented | MAP only | [sub/UPC.md](sub/UPC.md) |  |
| $00C1 | SCANR | sub | MSX2 | partial | MAP only | [sub/SCANR.md](sub/SCANR.md) | C-BIOS: SCREEN 5-8 stubbed |
| $00C5 | SCANL | sub | MSX2 | partial | MAP only | [sub/SCANL.md](sub/SCANL.md) | C-BIOS: SCREEN 5-8 stubbed |
| $00C9 | NVBXLN | sub | MSX2 | implemented | TH App. 1 | [sub/NVBXLN.md](sub/NVBXLN.md) |  |
| $00CD | NVBXFL | sub | MSX2 | implemented | TH App. 1 | [sub/NVBXFL.md](sub/NVBXFL.md) |  |
| $00D1 | CHGMOD | sub | MSX2 | implemented | TH App. 1 | [sub/CHGMOD.md](sub/CHGMOD.md) |  |
| $00D5 | INITXT | sub | MSX2 | implemented | TH App. 1 | [sub/INITXT.md](sub/INITXT.md) |  |
| $00D9 | INIT32 | sub | MSX2 | implemented | TH App. 1 | [sub/INIT32.md](sub/INIT32.md) |  |
| $00DD | INIGRP | sub | MSX2 | implemented | TH App. 1 | [sub/INIGRP.md](sub/INIGRP.md) |  |
| $00E1 | INIMLT | sub | MSX2 | implemented | TH App. 1 | [sub/INIMLT.md](sub/INIMLT.md) |  |
| $00E5 | SETTXT | sub | MSX2 | implemented | TH App. 1 | [sub/SETTXT.md](sub/SETTXT.md) |  |
| $00E9 | SETT32 | sub | MSX2 | implemented | TH App. 1 | [sub/SETT32.md](sub/SETT32.md) |  |
| $00ED | SETGRP | sub | MSX2 | implemented | TH App. 1 | [sub/SETGRP.md](sub/SETGRP.md) |  |
| $00F1 | SETMLT | sub | MSX2 | implemented | TH App. 1 | [sub/SETMLT.md](sub/SETMLT.md) |  |
| $00F5 | CLRSPR | sub | MSX2 | implemented | TH App. 1 | [sub/CLRSPR.md](sub/CLRSPR.md) |  |
| $00F9 | CALPAT | sub | MSX2 | implemented | TH App. 1 | [sub/CALPAT.md](sub/CALPAT.md) |  |
| $00FD | CALATR | sub | MSX2 | implemented | TH App. 1 | [sub/CALATR.md](sub/CALATR.md) |  |
| $0101 | GSPSIZ | sub | MSX2 | implemented | TH App. 1 | [sub/GSPSIZ.md](sub/GSPSIZ.md) |  |
| $0105 | GETPAT | sub | MSX2 | implemented | TH App. 1 | [sub/GETPAT.md](sub/GETPAT.md) |  |
| $0109 | NWRVRM | sub | MSX2 | implemented | TH App. 1 | [sub/NWRVRM.md](sub/NWRVRM.md) | the handbook calls it WRTVRM (MAP: WTRVRM) |
| $010D | NRDVRM | sub | MSX2 | implemented | TH App. 1 | [sub/NRDVRM.md](sub/NRDVRM.md) | the handbook calls it RDVRM |
| $0111 | CHGCLR | sub | MSX2 | implemented | TH App. 1 | [sub/CHGCLR.md](sub/CHGCLR.md) |  |
| $0115 | CLS | sub | MSX2 | implemented | TH App. 1 | [sub/CLS.md](sub/CLS.md) | the handbook spells it CLSSUB |
| $0119 | CLRTXT | sub | MSX2 | stub | MAP only | [sub/CLRTXT.md](sub/CLRTXT.md) | C-BIOS: debug message, then CLS |
| $011D | DSPFNK | sub | MSX2 | missing | TH App. 1 | [sub/DSPFNK.md](sub/DSPFNK.md) |  |
| $0121 | DELLNO | sub | MSX2 | missing | MAP only | [sub/DELLNO.md](sub/DELLNO.md) |  |
| $0125 | INSLNO | sub | MSX2 | missing | MAP only | [sub/INSLNO.md](sub/INSLNO.md) |  |
| $0129 | PUTVRM | sub | MSX2 | missing | MAP only | [sub/PUTVRM.md](sub/PUTVRM.md) |  |
| $012D | WRTVDP | sub | MSX2 | implemented | TH App. 1 | [sub/WRTVDP.md](sub/WRTVDP.md) |  |
| $0131 | VDPSTA | sub | MSX2 | implemented | TH App. 1 | [sub/VDPSTA.md](sub/VDPSTA.md) |  |
| $0135 | KYKLOK | sub | MSX2 | missing | MAP only | [sub/KYKLOK.md](sub/KYKLOK.md) |  |
| $0139 | PUTCHR | sub | MSX2 | missing | MAP only | [sub/PUTCHR.md](sub/PUTCHR.md) |  |
| $013D | SETPAG | sub | MSX2 | implemented | TH App. 1 | [sub/SETPAG.md](sub/SETPAG.md) |  |
| $0141 | INIPLT | sub | MSX2 | implemented | TH App. 1 | [sub/INIPLT.md](sub/INIPLT.md) |  |
| $0145 | RSTPLT | sub | MSX2 | implemented | TH App. 1 | [sub/RSTPLT.md](sub/RSTPLT.md) |  |
| $0149 | GETPLT | sub | MSX2 | implemented | TH App. 1 | [sub/GETPLT.md](sub/GETPLT.md) |  |
| $014D | SETPLT | sub | MSX2 | implemented | TH App. 1 | [sub/SETPLT.md](sub/SETPLT.md) |  |
| $0151 | PUTSPRT | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $0155 | COLOR | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $0159 | SCREEN | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $015D | WIDTHS | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $0161 | VDP | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $0165 | VDPF | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $0169 | BASE | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $016D | BASEF | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $0171 | VPOKE | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $0175 | VPEEK | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $0179 | SETS | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $017D | BEEP | sub | MSX2 | stub | TH App. 1 | [sub/BEEP.md](sub/BEEP.md) | the main ROM's BEEP ($00C0) is marked "always calls the sub-ROM" (TH App. 1); that it calls this entry is unmeasured |
| $0181 | PROMPT | sub | MSX2 | stub | TH App. 1 | [sub/PROMPT.md](sub/PROMPT.md) |  |
| $0185 | SDFSCR | sub | MSX2 | stub | MAP only | [sub/SDFSCR.md](sub/SDFSCR.md) |  |
| $0189 | SETSCR | sub | MSX2 | stub | MAP only | [sub/SETSCR.md](sub/SETSCR.md) |  |
| $018D | SCOPY | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $0191 | BLTVV | sub | MSX2 | implemented | TH App. 3 | [sub/BLTVV.md](sub/BLTVV.md) |  |
| $0195 | BLTVM | sub | MSX2 | implemented | TH App. 3 | [sub/BLTVM.md](sub/BLTVM.md) |  |
| $0199 | BLTMV | sub | MSX2 | implemented | TH App. 3 | [sub/BLTMV.md](sub/BLTMV.md) |  |
| $019D | BLTVD | sub | MSX2 | stub | TH App. 3 | [sub/BLTVD.md](sub/BLTVD.md) |  |
| $01A1 | BLTDV | sub | MSX2 | stub | TH App. 3 | [sub/BLTDV.md](sub/BLTDV.md) |  |
| $01A5 | BLTMD | sub | MSX2 | stub | TH App. 3 | [sub/BLTMD.md](sub/BLTMD.md) |  |
| $01A9 | BLTDM | sub | MSX2 | stub | TH App. 3 | [sub/BLTDM.md](sub/BLTDM.md) |  |
| $01AD | NEWPAD | sub | MSX2 | implemented | TH App. 1 | [sub/NEWPAD.md](sub/NEWPAD.md) |  |
| $01B1 | GETPUT | sub | MSX2 | missing | MAP only | — BASIC statement internal, not a BIOS call | HL = BASIC text pointer |
| $01B5 | CHGMDP | sub | MSX2 | implemented | TH App. 1 | [sub/CHGMDP.md](sub/CHGMDP.md) |  |
| $01B9 | RESVI | sub | MSX2 | missing | MAP only | — reserved, no function | |
| $01BD | KNJPRT | sub | MSX2 | stub | TH App. 1 | [sub/KNJPRT.md](sub/KNJPRT.md) |  |
| $01F5 | REDCLK | sub | MSX2 | implemented | TH App. 1 | [sub/REDCLK.md](sub/REDCLK.md) |  |
| $01F9 | WRTCLK | sub | MSX2 | implemented | TH App. 1 | [sub/WRTCLK.md](sub/WRTCLK.md) |  |
