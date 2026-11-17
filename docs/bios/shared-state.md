<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# The BIOS shared-state map — which call touches which cell, register and port

> **Status:** DRAFT (2026-11-17), compiled from the PUBLISHED interface only (the sources below,
> rated in [allowed-sources.md](../allowed-sources.md)) plus this project's own measurements. It is
> the base for the per-call pages: a call's page LINKS its row here rather than restating it, and a
> per-call measurement that contradicts a row corrects the row. Read the base page first:
> [The BIOS](../concepts/bios.md).
>
> ⚠️ **Not verified against the scan:** the source is a scan without a text layer, read through OCR,
> and five addresses were unreadable there. They were reconstructed from the book's own layout
> (5-byte hook slots, consecutive table cells): H.ISFL $FEDF, H.OUTD $FEE4, H.PHYD $FFA7,
> H.FORM $FFAC, and the screen-table / colour cells $F3B3–$F3EB. Treat them as leads until a page
> measures them or someone checks the scan.

What each of the 108 MSX1 BIOS entries reads and writes outside its registers: work-area cells,
VDP registers / VRAM, I/O devices and ports, CPU interrupt state. Taken from the published
interface only, plus this repo's own black-box measurements.

**Sources (all rated admissible in docs/allowed-sources.md):**
- **TDB** = *MSX Technical Data Book* (ASCII / Microsoft; B / Scoped). Sections used: §2.2.1 BIOS
  Entry List (Function / Entry / Returns / Modifies), §2.2.2 Work Area (cell addresses and the
  book's own one-line descriptions; the hook table's "Location" lines), §2.2.3 Slot Control,
  §2.2.4 Cassette I/O Mechanism, §1.3.3 Interrupts, §1.7.3–1.7.12 I/O map and PPI / PSG bit
  assignments, §5.4, §6 Notes for Developers, and the MSX-DOS memory-map note in ch. 3.
- **TH** = *MSX2 Technical Handbook* (Konamiman's translation; B / Scoped), ch. 2 §4.5 only.
  The local copy has chapters 1–4 only. **Its Appendix (the BIOS listing and the work-area
  listing) is not available locally, so it was not used.**
- **repo** = this project's own measurements (file named per row).

**How to read a cell:**
- *named* = the entry's own text names it.
- *by description* = the entry's text names the function ("the keyboard buffer"). The cell is the
  one whose TDB §2.2.2 description matches. The book does not link the two. **Treat these as
  leads, not facts.**
- *port per §1.7* = the entry names a device ("the PSG", "the CAP lamp"). The port or bit comes
  from the TDB hardware map. TDB §1.7.10 says software must not rely on those ports (BIOS may be
  rewritten for other hardware). So the port is the standard machine's, not part of the entry's
  contract. The VDP is the exception: its ports are published at ROM $0006 / $0007.
- **Confidence:** *stated*: the cells or devices touched are all named. *partly*: some are named,
  or are only by description or by port map. *not stated*: the published text names no state.

Cell addresses are from TDB §2.2.2. Hook names are TDB's, with the routine each one is "at the
beginning of".

## 1. Per-entry table

| addr | name | region | reads | writes | source | confidence |
|---|---|---|---|---|---|---|
| $0000 | CHKRAM | system | — | slot selection ("sets slot for command area"): primary slot register (PPI port A, port per §1.7.11 / §2.2.3) | TDB §2.2.1; §2.2.3 | partly |
| $0008 | SYNCHR | interpreter | BASIC text at (HL); no cell named | — (error path "Syntax error"; error state not stated) | TDB §2.2.1 | not stated |
| $000C | RDSLT | slots | target slot's memory at HL; slot registers | primary slot register (PPI port A) + secondary slot register ($FFFF), restored; CPU interrupts left disabled. EXPTBL $FCC1 / SLTTBL $FCC5 are the system's record of the expansion registers (§2.2.3), but which entries use them is not stated | TDB §2.2.1; §2.2.3; repo: probes/bios/biosl/b6slots.asm | partly |
| $0010 | CHRGTR | interpreter | BASIC text at (HL); no cell named | — | TDB §2.2.1 | not stated |
| $0014 | WRSLT | slots | slot registers | target slot's memory at HL; slot registers as RDSLT; interrupts left disabled | TDB §2.2.1; §2.2.3 | partly |
| $0018 | OUTDO | devices | **PTRFIL $F864, PRTFLG $F416** (named as Entry); hook **H.OUTD $FEE4** | the current device (screen / printer / file, by PTRFIL / PRTFLG) | TDB §2.2.1; §2.2.2 hooks | stated |
| $001C | CALSLT | slots | IY slot ID, IX address | slot registers switched for the call; interrupts left disabled; alternate registers / IX / IY not usable for arguments | TDB §2.2.1; §2.2.3 | partly |
| $0020 | DCOMPR | interpreter | — | — | TDB §2.2.1 | not stated (registers only) |
| $0024 | ENASLT | slots | — | slot registers, **permanently** (primary PPI port A; secondary $FFFF) for HL's page; interrupts left disabled | TDB §2.2.1; §2.2.3; repo: b6slots.asm (interrupt state after ENASLT measured) | partly |
| $0028 | GETYPR | interpreter | **"FAC"** (named; DAC $F7F6 in §2.2.2). The type cell is not named | — | TDB §2.2.1 | partly |
| $0030 | CALLF | slots | inline slot / address after RST 30h | as CALSLT | TDB §2.2.1 | partly |
| $0038 | KEYINT | system | VDP interrupt (§1.3.3); hooks **H.KEYI $FD9A** (start of the interrupt handler) and **H.TIMI $FD9F** (timer handler); repo: VDP status into STATFL $F3E7, SCNCNT $F3F6 gates the key scan | key input (TH §4.5); TIME (JIFFY $FC9E) advances per VDP interrupt (TDB §5.4, repo); STATFL (repo) | TDB §1.3.3, §2.2.2 hooks, §5.4; TH ch.2 §4.5; repo: docs/concepts/interrupts-and-traps.md, probes/bios/biosl/b3int.asm | partly |
| $003B | INITIO | system | — | "device initialization"; devices not named | TDB §2.2.1 | not stated |
| $003E | INIFNK | text | — | function-key strings: FNKSTR $F87F (*by description*: "function key string save area") | TDB §2.2.1, §2.2.2 | partly |
| $0041 | DISSCR | vdp | — | VDP display enable (register not named); RG1SAV $F3E0 holds R#1's current contents (§6 note 6) | TDB §2.2.1; §6 | partly |
| $0044 | ENASCR | vdp | — | as DISSCR | TDB §2.2.1; §6 | partly |
| $0047 | WRTVDP | vdp | — | **VDP register C := B** (named); shadow RG0SAV–RG7SAV $F3DF–$F3E6 ("save area for the VDP registers"; §6 note 6 for R#0 / R#1); repo: RG7SAV follows a WRTVDP R#7 | TDB §2.2.1, §2.2.2, §6; repo: probes/bios/biosl/b2vdp.asm | partly |
| $004A | RDVRM | vdp | **VRAM at HL**; VDP ports (ROM $0006 / $0007; 98H / 99H §1.7.4) | VDP address latch | TDB §2.2.1; §1.7.4; §6 | stated |
| $004D | WRTVRM | vdp | — | **VRAM at HL**; VDP address latch | TDB §2.2.1 | stated |
| $0050 | SETRD | vdp | — | **VDP address latch (read setup)** | TDB §2.2.1 | stated |
| $0053 | SETWRT | vdp | — | **VDP address latch (write setup)** | TDB §2.2.1 | stated |
| $0056 | FILVRM | vdp | — | **VRAM HL..HL+BC−1** | TDB §2.2.1 | stated |
| $0059 | LDIRMV | vdp | **VRAM block** | RAM at DE | TDB §2.2.1 | stated |
| $005C | LDIRVM | vdp | RAM at HL | **VRAM block** | TDB §2.2.1 | stated |
| $005F | CHGMOD | vdp | **SCRMOD $FCAF** (named Entry, 0..3) | VDP mode (registers / tables not named) | TDB §2.2.1 | partly |
| $0062 | CHGCLR | vdp | **FORCLR $F3E9, BAKCLR $F3EA, BDRCLR $F3EB** (named) | screen colours (VDP register not named; repo: RG7SAV changes) | TDB §2.2.1; repo: b2vdp.asm | partly |
| $0066 | NMI | system | hook **H.NMI $FDD6** ("MSX ROM only provides a RAM hook", §1.3.3) | — | TDB §2.2.1, §1.3.3, §2.2.2 | stated |
| $0069 | CLRSPR | vdp | **SCRMOD** (named Entry); foreground colour (FORCLR *by description*) | **sprite pattern table (nulls), sprite attribute table (name = plane, colour = foreground, Y = 209)**; table cells not named | TDB §2.2.1 | partly |
| $006C | INITXT | text | **TXTNAM $F3B3, TXTCGP $F3B7** (named); measured: also TXTCOL / TXTATR / TXTPAT, LINL40, CNSDFG, CRTCNT (the key line's row), FORCLR / BAKCLR, FNKSTR, RG0SAV bit 0 and RG1SAV bits 0–2 | screen initialised (VRAM) + VDP set for 40×24; measured: RG0SAV–RG7SAV, LINLEN, SCRMOD, OLDSCR, CSRX / CSRY, LINTTB, CNSDFG; NOT CRTCNT | TDB §2.2.1; [INITXT.md](INITXT.md) | partly (TDB) + measured |
| $006F | INIT32 | text | **T32NAM $F3BD, T32CGP $F3C1, T32COL $F3BF, T32ATR $F3C3, T32PAT $F3C5**; measured: also LINL32, CNSDFG, CRTCNT, FORCLR / BAKCLR / BDRCLR, FNKSTR, RG0SAV / RG1SAV bits | screen (VRAM) + VDP for 32×24; measured: as INITXT, plus the colour table and the sprite attribute table | TDB §2.2.1; [INITXT.md](INITXT.md) | partly (TDB) + measured |
| $0072 | INIGRP | vdp | **GRPNAM $F3C7, GRPCGP $F3CB, GRPCOL $F3C9, GRPATR $F3CD, GRPPAT $F3CF** | screen (VRAM) + VDP, high-res | TDB §2.2.1 | partly |
| $0075 | INIMLT | vdp | **MLTNAM $F3D1, MLTCGP $F3D5, MLTCOL $F3D3, MLTATR $F3D7, MLTPAT $F3D9** | screen (VRAM) + VDP, multicolour | TDB §2.2.1 | partly |
| $0078 | SETTXT | vdp | **TXTNAM, TXTCGP** | VDP set for 40×24 | TDB §2.2.1 | partly |
| $007B | SETT32 | vdp | **T32NAM..T32PAT** (5 cells) | VDP set for 32×24 | TDB §2.2.1 | partly |
| $007E | SETGRP | vdp | **GRPNAM..GRPPAT** (5 cells) | VDP set for high-res | TDB §2.2.1 | partly |
| $0081 | SETMLT | vdp | **MLTNAM..MLTPAT** (5 cells) | VDP set for multicolour | TDB §2.2.1 | partly |
| $0084 | CALPAT | vdp | current sprite pattern table base (PATBAS $F926 *by description*) | — | TDB §2.2.1, §2.2.2 | partly |
| $0087 | CALATR | vdp | current sprite attribute table base (ATRBAS $F928 *by description*) | — | TDB §2.2.1, §2.2.2 | partly |
| $008A | GSPSIZ | vdp | "current sprite size" (cell not named); repo: follows R#1 bit 1 as written by WRTVDP | — | TDB §2.2.1; repo: b2vdp.asm step 4 | partly |
| $008D | GRPPRT | graphics | — | character on the graphic screen (VRAM); position cells not named | TDB §2.2.1 | partly |
| $0090 | GICINI | sound | — | **PSG initialised**; PLAY static data: TDB §2.2.2 says the area **MUSICF $FB3F … VCBC end ($FBAF)** "is cleared every time GICINI is called" (MUSICF, PLYCNT $FB40, VCBA/VCBB/VCBC $FB41/$FB66/$FB8B) | TDB §2.2.1, §2.2.2; repo: bios_levels.py (queues / MUSICF / PLYCNT compared) | stated |
| $0093 | WRTPSG | sound | — | **PSG register A := E** (A0H / A1H per §1.7.5) | TDB §2.2.1; §1.7.5 | stated |
| $0096 | RDPSG | sound | **PSG register A** (A0H / A2H) | PSG address latch | TDB §2.2.1; §1.7.5 | stated |
| $0099 | STRTMS | sound | PLAY background-task state (PLYCNT "number of play statements queued for background task", MUSICF "music interrupt flag": *by description*) | starts background PLAY | TDB §2.2.1, §2.2.2 | partly |
| $009C | CHSNS | text | keyboard buffer (KEYBUF $FBF0, PUTPNT $F3F8, GETPNT $F3FA: *by description*) | — | TDB §2.2.1, §2.2.2 | partly |
| $009F | CHGET | text | hook **H.CHGE $FDC2**; keyboard buffer (*by description*) | keyboard buffer (consumes a code) | TDB §2.2.1, §2.2.2 hooks | partly |
| $00A2 | CHPUT | text | hook **H.CHPU $FDA4** (TDB); repo: CSRX $F3DD, CSRY $F3DC, LINLEN $F3B0, the function-key line state (CNSDFG $F3DE: the last text row is 23 when the key line is shown), LINTTB $FBB2, name-table VRAM | repo: CSRX, CSRY, LINTTB, CSRSW $FCA9 and CSTYLE $FCAA (ESC x / y), name-table VRAM | TDB §2.2.2 hooks; repo: docs/bios/CHPUT.md (FINAL), docs/concepts/screen-editor.md | partly (TDB) + measured |
| $00A5 | LPTOUT | devices | hook **H.LPTO $FFB6**; printer busy (90H bit 1, §1.7.3) | printer data / strobe (91H, 90H bit 0) | TDB §2.2.1, §2.2.2 hooks, §1.7.3 | partly |
| $00A8 | LPTSTT | devices | hook **H.LPTS $FFBB**; printer status (90H) | — | TDB §2.2.1, §2.2.2 hooks, §1.7.3 | partly |
| $00AB | CNVCHR | text | graphic-header state (GRPHED $FCA6 "flag for graphic character output", *by description*) | the same, *by description* | TDB §2.2.1, §2.2.2 | partly |
| $00AE | PINLIN | text | hook **H.PINL $FDDB**; console input | line buffer (returns "buffer top−1"; BUF $F55E *by description*; repo: BUF compared) | TDB §2.2.1, §2.2.2; repo: bios_levels.py | partly |
| $00B1 | INLIN | text | hook **H.INLI $FDE5**; **AUTFLG $F6AA** (named) | line buffer (as PINLIN) | TDB §2.2.1, §2.2.2 | partly |
| $00B4 | QINLIN | text | hook **H.QINL $FDE0**; then as INLIN (AUTFLG) | console ('? ' output); line buffer | TDB §2.2.1, §2.2.2 | partly |
| $00B7 | BREAKX | input | CTRL+STOP key state, read so that it works **with interrupts disabled** (mechanism not stated) | — | TDB §2.2.1 | partly |
| $00BA | ISCNTC | input | STOP-key status (cells not named) | not stated | TDB §2.2.1 | not stated |
| $00BD | CKCNTC | input | as ISCNTC | not stated | TDB §2.2.1 | not stated |
| $00C0 | BEEP | sound | — | "the buzzer" (device not named); repo: PSG registers 0..13 changed right after BEEP | TDB §2.2.1; repo: probes/bios/biosl/b5sound.asm | partly (measured) |
| $00C3 | CLS | text | — ; measured: the Z flag (clear: nothing), SCRMOD, CNSDFG, CRTCNT, LINLEN, FNKSTR, BAKCLR (SCREEN 2) | the screen (VRAM; mode-dependent); measured: SCREEN 0 / 1 the name table only, CSRX / CSRY, LINTTB, CNSDFG; SCREEN 2 the pattern and colour tables only | TDB §2.2.1; [CLS.md](CLS.md) | partly (TDB) + measured |
| $00C6 | POSIT | text | — ; measured: H, L, LINLEN and CRTCNT (the clamps), SCRMOD | cursor position: CSRX / CSRY (measured; nothing in SCREEN 2) | TDB §2.2.1; [CLS.md](CLS.md) | partly (TDB) + measured |
| $00C9 | FNKSB | text | **FNKFLG $FBCE** (named Entry, as printed); measured: FNKFLG makes NO difference, CNSDFG decides (non-zero: as DSPFNK; 0: nothing) | key-line display (screen); measured: as DSPFNK | TDB §2.2.1; [DSPFNK.md](DSPFNK.md) | partly (TDB) + measured |
| $00CC | ERAFNK | text | hook **H.ERAF $FDB8**; measured: CRTCNT (the row), LINLEN (the span), SCRMOD | key-line erased (screen); measured: CNSDFG := 0, row CRTCNT's span := spaces | TDB §2.2.1, §2.2.2; [DSPFNK.md](DSPFNK.md) | partly (TDB) + measured |
| $00CF | DSPFNK | text | hook **H.DSPF $FDB3**; key strings (FNKSTR *by description*); measured: FNKSTR keys 1–5, CRTCNT (the row), LINLEN (the span and slots), SCRMOD | key-line display (screen); measured: CNSDFG := 255, row CRTCNT's span; NOT the cursor, CRTCNT | TDB §2.2.1, §2.2.2; [DSPFNK.md](DSPFNK.md) | partly (TDB) + measured |
| $00D2 | TOTEXT | text | hook **H.TOTE $FDBD** | screen forced to text mode (VDP; SCRMOD not named) | TDB §2.2.1, §2.2.2 | partly |
| $00D5 | GTSTCK | input | joystick (PSG R#14 bits 0–3, R#15 bit 6 port select per §1.7.12); repo: ID 0 = cursor keys | PSG R#15 select (per §1.7.12, not stated by the entry) | TDB §2.2.1, §1.7.12; repo: bios_levels.py | partly |
| $00D8 | GTTRIG | input | trigger (PSG R#14 bits 4–5 per §1.7.12); repo: ID 0 = SPACE | as GTSTCK | TDB §2.2.1, §1.7.12; repo | partly |
| $00DB | GTPAD | input | touch pad (PSG ports per §1.7.12); PADX $FC9D / PADY $FC9C exist in §2.2.2 (no description) | not stated | TDB §2.2.1, §2.2.2 | partly |
| $00DE | GTPDL | input | paddle (PSG ports per §1.7.12) | not stated | TDB §2.2.1 | partly |
| $00E1 | TAPION | tape | tape input (PSG R#14 bit 7 CSAR, §1.7.12); interrupts must be **disabled** (§2.2.4) | **motor on** (PPI port C bit 4 CASON, §1.7.11); LOWLIM $FCA4 / WINWID $FCA5 ("used when reading cassette", *by description*; repo: measured after TAPION) | TDB §2.2.1, §2.2.4, §1.7.11–12; repo: docs/concepts/cassette.md | partly |
| $00E4 | TAPIN | tape | tape input (CSAR); LOWLIM / WINWID (*by description*) | — | TDB §2.2.1, §2.2.4 | partly |
| $00E7 | TAPIOF | tape | — | stops reading (motor not named) | TDB §2.2.1 | not stated |
| $00EA | TAPOON | tape | header length / baud: HEADER $F40A, LOW $F406, HIGH $F408 (*by description*: cassette parameters) | **motor on**; tape output (PPI port C bit 5 CASW) | TDB §2.2.1, §2.2.2, §2.2.4, §1.7.11 | partly |
| $00ED | TAPOUT | tape | LOW / HIGH (*by description*) | tape output (CASW) | TDB §2.2.1, §2.2.4 | partly |
| $00F0 | TAPOOF | tape | — | stops writing (motor not named) | TDB §2.2.1 | not stated |
| $00F3 | STMOTR | tape | — | **cassette motor** (PPI port C bit 4, §1.7.11) | TDB §2.2.1, §1.7.11 | partly |
| $00F6 | LFTQ | sound | a queue (QUEUES $F3F3 → QUETAB $F959, *by description*); Entry / Returns blank in TDB | — | TDB §2.2.1, §2.2.2 | partly |
| $00F9 | PUTQ | sound | as LFTQ | a queue (+ voice queues VOICAQ.. $F975.., *by description*) | TDB §2.2.1, §2.2.2 | partly |
| $00FC | RIGHTC | graphics | current pixel (physical address + mask: FETCHC / STOREC's state; CLOC $F92A / CMASK $F92C *by description*) | the same | TDB §2.2.1 | partly |
| $00FF | LEFTC | graphics | as RIGHTC | as RIGHTC | TDB §2.2.1 | partly |
| $0102 | UPC | graphics | as RIGHTC | as RIGHTC | TDB §2.2.1 | partly |
| $0105 | TUPC | graphics | as RIGHTC | as RIGHTC | TDB §2.2.1 | partly |
| $0108 | DOWNC | graphics | as RIGHTC | as RIGHTC | TDB §2.2.1 | partly |
| $010B | TDOWNC | graphics | as RIGHTC | as RIGHTC | TDB §2.2.1 | partly |
| $010E | SCALXY | graphics | not stated | not stated | TDB §2.2.1 | not stated |
| $0111 | MAPXYC | graphics | — | current physical address (+ mask) | TDB §2.2.1 | partly |
| $0114 | FETCHC | graphics | **current physical address and mask pattern** | — | TDB §2.2.1 | partly (cells not named) |
| $0117 | STOREC | graphics | — | **current physical address and mask pattern** | TDB §2.2.1 | partly (cells not named) |
| $011A | SETATR | graphics | — | attribute byte (ATRBYT $F3F2 "attribute byte", by name) | TDB §2.2.1, §2.2.2 | partly |
| $011D | READC | graphics | current pixel's attribute (VRAM at the current address) | — | TDB §2.2.1 | partly |
| $0120 | SETC | graphics | the attribute (ATRBYT, *by description*); current address | current pixel (VRAM) | TDB §2.2.1 | partly |
| $0123 | NSETCX | graphics | as SETC | pixels horizontally (VRAM) | TDB §2.2.1 | partly |
| $0126 | GTASPC | graphics | aspect ratio (ASPCT1 $F40B / ASPCT2 $F40D by name) | — | TDB §2.2.1, §2.2.2 | partly |
| $0129 | PNTINI | graphics | not stated (§2.2.2 "For PAINT" cells $F949–$F955, BRDATR $FCB2: none linked) | not stated | TDB §2.2.1 | not stated |
| $012C | SCANR | graphics | VRAM (scans pixels); cells not stated | not stated | TDB §2.2.1 | partly |
| $012F | SCANL | graphics | as SCANR | not stated | TDB §2.2.1 | partly |
| $0132 | CHGCAP | input | — | **CAP lamp** (PPI port C bit 6, §1.7.11). CAPST $FCAB is not written by the entry's text (TH List 2.4 keeps CAPST in the program) | TDB §2.2.1, §1.7.11; TH ch.2 §4.5 List 2.4 | partly |
| $0135 | CHGSND | sound | — | **1-bit sound port** (PPI port C bit 7, §1.7.11 / §1.3.6) | TDB §2.2.1, §1.7.11 | partly |
| $0138 | RSLREG | slots | **primary slot register** (PPI port A, §2.2.3 / §1.7.6) | — | TDB §2.2.1, §2.2.3 | stated |
| $013B | WSLREG | slots | — | **primary slot register** | TDB §2.2.1, §2.2.3 | stated |
| $013E | RDVDP | vdp | **VDP status register** (99H read) | — | TDB §2.2.1, §1.7.4 | stated |
| $0141 | SNSMAT | input | **keyboard matrix row A** (PPI port C bits 0–3 select, port B return, §1.7.11) | PPI port C row bits (per §1.7.11) | TDB §2.2.1, §1.7.11, §6 note 8 | partly |
| $0144 | PHYDIO | disk | hook **H.PHYD $FFA7** ("in the minimum configuration, only a hook is provided"); repo: the disk ROM installs H.PHYD | — | TDB §2.2.1, §2.2.2; repo: docs/concepts/disk.md | stated |
| $0147 | FORMAT | disk | hook **H.FORM $FFAC** (same note) | — | TDB §2.2.1, §2.2.2 | stated |
| $014A | ISFLIO | devices | hook **H.ISFL $FEDF**; "device I/O being done" (PTRFIL *by description*) | — | TDB §2.2.1, §2.2.2 | partly |
| $014D | OUTDLP | devices | printer (as LPTOUT); non-MSX printer flag (NTMSXP $F417, *by description*); head position for TAB (LPTPOS $F415, *by description*) | printer; LPTPOS (*by description*); Device I/O error on abort | TDB §2.2.1, §2.2.2 | partly |
| $0150 | GETVCP | sound | voice static data (VCBA.. *by description*); repo: returns a pointer into a voice block | — | TDB §2.2.1; repo: bios_levels.py | partly |
| $0153 | GETVC2 | sound | as GETVCP | — | TDB §2.2.1; repo | partly |
| $0156 | KILBUF | input | — | keyboard buffer cleared (PUTPNT / GETPNT / KEYBUF *by description*) | TDB §2.2.1, §2.2.2 | partly |
| $0159 | CALBAS | slots | IX address; the BASIC interpreter's slot | slot registers for the call (as CALSLT) | TDB §2.2.1 | partly |

**Tally (all 108):** stated 17, partly 81, not stated 10. "Stated" means every cell / device
the entry touches is named. Those rows are mostly single-device entries: VRAM, PSG, slot
register, hook-only.

## 2. Couplings (state touched by entries of more than one region)

1. **PPI port C ($AA): tape × input × sound (× system).** Bit 4 is the motor (STMOTR, TAPION,
   TAPOON; tape), bit 5 tape out (TAPOON / TAPOUT), bit 6 the CAP lamp (CHGCAP; input), bit 7
   1-bit sound (CHGSND; sound), bits 0–3 the keyboard row (SNSMAT; input). KEYINT does the key
   input (TH §4.5; system), so it uses the same bits. Four regions share one byte, so each
   write has to keep the other regions' bits (TDB §1.7.11).
2. **PSG R#14 / R#15: sound × input × tape.** WRTPSG / RDPSG / GICINI reach every register
   (BEEP too, repo). GTSTCK / GTTRIG / GTPAD / GTPDL read R#14 with R#15 bit 6 selecting the
   port. TAPION / TAPIN read R#14 bit 7 (CSAR) (TDB §1.7.12). The repo's b5sound already treats
   R#14 / R#15 as "the joystick port, not sound state".
3. **Keyboard matrix + keyboard buffer: system × input × text.** KEYINT scans the keyboard and
   fills the buffer (TH §4.5). SNSMAT / BREAKX read the matrix directly. KILBUF (input) clears the
   buffer and CHSNS / CHGET (text) read it: KEYBUF $FBF0, PUTPNT $F3F8, GETPNT $F3FA (*by
   description*). SCNCNT $F3F6 gates the scan (repo).
4. **Slot registers (PPI port A $A8, secondary $FFFF; EXPTBL $FCC1 / SLTTBL $FCC5): slots ×
   system × disk.** RDSLT / WRSLT / CALSLT / CALLF / ENASLT / RSLREG / WSLREG / CALBAS (slots) and
   CHKRAM (system). TDB ch. 3 notes that an interrupt during an inter-slot call may find page 1
   switched, "because some manufacturers are using the timer interrupt hook to stop the [disk]
   motor". So H.TIMI (KEYINT, system) couples to the disk region (PHYDIO).
5. **VDP registers and their shadows RG0SAV–RG7SAV $F3DF–$F3E6: vdp × text × system.**
   WRTVDP, DISSCR / ENASCR, CHGMOD, CHGCLR, INIGRP / INIMLT, SETxxx, GSPSIZ (repo: reads R#1's
   size bit) are vdp. INITXT, INIT32, TOTEXT are text. KEYINT depends on the VDP interrupt
   (§1.3.3), and the repo measured that clearing R#1's interrupt bit stops TIME and the
   keyboard. RG1SAV ties DISSCR / ENASCR / WRTVDP / GSPSIZ / mode changes together (TDB §6
   note 6).
6. **VDP status register: vdp × system.** RDVDP reads it. KEYINT is driven by it and leaves its
   copy in STATFL $F3E7 (repo b3int).
7. **VDP ports / address latch / VRAM: vdp × text × graphics (× system).** RDVRM ... LDIRVM,
   CLRSPR, INIxxx (vdp). CHPUT, CLS, DSPFNK / ERAFNK, INITXT / INIT32 (text). GRPPRT, READC, SETC,
   NSETCX, SCANR / L (graphics). KEYINT's status read uses the same port pair (99H). Programs may
   use the ports directly via ROM $0006 / $0007 (TDB §6).
8. **Screen-mode table cells: text × vdp.** TXTNAM $F3B3 / TXTCGP $F3B7 are read by INITXT
   (text; measured: TXTCOL / TXTATR / TXTPAT too, into R3 / R5 / R6) and SETTXT (vdp). T32NAM..T32PAT $F3BD–$F3C5 are read by INIT32 (text) and SETT32 (vdp).
9. **CPU interrupt-enable state: slots × tape × input × system.** The slot entries leave
   interrupts disabled ("never enabled by this routine"). The tape entries "must be entered with
   interrupts disabled" (§2.2.4). BREAKX exists for the interrupts-off case. KEYINT (JIFFY, key
   scan, PLAY background) runs only with interrupts on.
10. **PLAY state: sound × system (*by description*).** GICINI clears MUSICF..VCBC (stated).
    STRTMS / PUTQ / LFTQ / GETVCP / GETVC2 use the queues and voice blocks. MUSICF is the "music
    interrupt flag" and GETVCP is "used only to play music in the background", which points to
    KEYINT. The interrupt side is not stated.
11. **SCRMOD $FCAF: vdp (CHGMOD, CLRSPR; named) × text (TOTEXT, *not named*).** This is a likely
    coupling, but only the vdp side is published.
12. **Console output path: devices × text.** OUTDO (devices) sends to "the current device" by
    PTRFIL / PRTFLG, which includes the screen (CHPUT, text). OUTDLP (devices) and CNVCHR (text)
    both convert graphic characters (*by description*). This is a call path, not a shared cell.

Within one region only (no cross-region coupling found): FORCLR / BAKCLR / BDRCLR (vdp),
the graphics current-pixel state and ATRBYT (graphics), the function-key cells FNKSTR / FNKFLG /
CNSDFG (text), the cursor CSRX / CSRY / LINTTB (text, repo), the printer cells and ports
(devices), the cassette parameters LOW / HIGH / HEADER / LOWLIM / WINWID (tape). AUTFLG (INLIN)
couples text to the BASIC interpreter, which is not a BIOS region.

## 3. Gaps (the published interface states no state at all)

- **Not stated (10):** SYNCHR, CHRGTR, DCOMPR (registers / text pointer only), INITIO,
  ISCNTC, CKCNTC, TAPIOF, TAPOOF, SCALXY, PNTINI.
- **Entry / Returns left blank in TDB §2.2.1**, so the function line is all there is: LFTQ,
  PUTQ, RIGHTC, LEFTC, UPC, TUPC, DOWNC, TDOWNC, SCALXY, MAPXYC, SETATR, READC, SETC, NSETCX,
  PNTINI, SCANR, SCANL, PHYDIO, FORMAT, GETVCP, GETVC2. Their "partly" rows rest on *by
  description* links.
- **Hooks with no published link to an entry:** H.DSPC, H.ERAC, H.INIP, H.KEYC, H.KYEA. Their
  routines (DSPCSR, ERACSR, INIPAT, KEYCOD, KYEASY) are not BIOS entries. Whether CHPUT / the
  INIxxx entries reach them is not stated.
- **Not covered here:** the MSX2 Technical Handbook appendix (BIOS and work-area listings) and
  the MSX Datapack are not available locally. They might settle several *by description* rows.
