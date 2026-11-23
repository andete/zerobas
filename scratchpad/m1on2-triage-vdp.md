# D-MSX1ON2 triage -- VDP / text-screen probes on MSX2 and MSX2+ (2026-11-23)

Machines: VG-8020 (MSX1 reference, committed run) · **F900** = Sony HB-F900 (MSX2 JP) · **8250** = Philips NMS 8250
(MSX2 EU) · **WSX** = Panasonic FS-A1WSX (MSX2+ JP) · **C-BIOS** = C-BIOS's own MSX2 / MSX2+ build of each.
Source: the per-probe file in scratchpad/AE_m1on2/ via `scratchpad/m1on2_cmp.py --bytes NAME`; offsets below are capture offsets
(the tool's `+OFF`), `cN+f` = case N, record field f. Clean room: captures, probe sources and spec pages only; nothing was
run.

## Summary

### GEN findings (rule broken on the MSX1 page; MSX2 = F900 + 8250, MSX2+ = WSX)

1. **RG1SAV / R#1 bit 7 (4/16K) is cleared** by INITXT, INIT32, INIGRP, INIMLT and CHGMOD (E0→60, F0→70, E2→62, EA→6A).
   This breaks R-IG-VDP / R-IM-VDP and the INITXT / INIT32 register rules. Holds on MSX2 and MSX2+ (b1text, b2vdp, xinig,
   xinit, xtot, xtot2, xscank).
2. **RG0SAV is masked, not rebuilt.** On the VG-8020, INITXT / INIT32 / INIMLT give RG0SAV AND 1 and INIGRP gives
   RG0SAV OR 2. On the MSX2 / MSX2+ the result is (RG0SAV AND $F1) OR the mode bits ($A5→$A1 / $A3), so **bit 4 (IE1,
   the line interrupt) and bit 6 (DG) of a garbage RG0SAV reach R#0**. This is the likely cause of the xinit3 / xinit4
   deaths (APPARATUS 1). Holds on MSX2 and MSX2+.
3. **INITXT does not write R#3 / R#5 / R#6, and INIMLT does not write R#3** (shadows keep $A5 or the earlier
   value). The VG-8020 writes them ($00, $36, $07, or from the cells). This breaks the INITXT page's VDP rule and
   R-IM-VDP. Holds on MSX2 and MSX2+ (xinit, xinig, b2vdp R3 = $FF, xtot, xtot2).
4. **INITXT with LINL40 > 40** (41, 80, 255) **selects the 80-column TEXT2 mode** (RG0SAV $A5, RG2 $03, RG3 $27,
   RG4 $02). On the VG-8020 it stays 40-column. Holds on MSX2 and MSX2+ (xinit c16-21).
5. **INITXT / INIT32 with width 0 and the key line on**: the VG-8020 draws garbage on the last row; the MSX2 draws
   spaces (xinit c1, c23). Holds on MSX2 and MSX2+.
6. **Interrupts are not enabled.** INIGRP, INIMLT, CHGMOD and INITXT return with the entry IFF (DI stays DI). This
   breaks R-IG-EI, R-IM-EI and the INITXT rule. CHGMOD with an invalid A returns with EI. Holds on MSX2 and MSX2+
   (xinig +12).
7. **FORCLR / BAKCLR / BDRCLR are masked to 4 bits** ($1A→$0A, $F0→$00) by INIGRP / INIMLT, which breaks
   R-IG-CELLS / R-IM-CELLS. RG7SAV in INITXT gets fg AND $0F (xinit c47-48), and so does the CLS SCREEN 2 colour byte
   (xscr c36-37). Holds on MSX2 and MSX2+.
8. **CHGMOD A ≥ 4**: A = 4 sets SCREEN 4. A = $7F / $80 / $81 / $FE / $FF does nothing (SCRMOD, shadows and VRAM are
   kept); the VG-8020 aliases these values to modes 0-3. This breaks R-CM-MODE. **TOTEXT** with OLDSCR $5A / $7F /
   $80 / $81 / $FF likewise does nothing, where the VG-8020 gives SCREEN 3 or SCREEN 0 (TOTEXT page). Holds on MSX2
   and MSX2+ (xinig, xtot, xtot2).
9. **Table addresses are not ANDed with $3FFF / do not wrap at $3FFF** (128 KB VRAM). Affected: R-IG-VRAM,
   R-IM-VRAM (cell sets 2 / 3 / 4), R-CS-VRAM (ATRBAS $5B00 / $9B00, PATBAS $3C00 wrap) and R-CC-VRAM (T32COL $FFFF).
   CLRSPR also ignores RG1SAV bit 7 (R-CS-VRAM's 16K condition, c55). Holds on MSX2 and MSX2+. On the WSX, CHGCLR with
   T32COL $FFFF writes somewhere else again.
10. **CLRSPR with SCRMOD ≥ 4** ($04, $77, $81) uses sprite mode 2 tables. Holds on MSX2 and MSX2+ (xclr c11, c42,
    c53, c54).
11. **The registers a call returns differ.** INIGRP / INIMLT / CHGMOD (R-IG-REGS, R-IM-REGS): A $00, F $40, B = the
    new RG1SAV. CLRSPR (R-CS-REGS): A $40, F $00. CHGCLR in SCREEN 1 (R-CC-REGS): F $42. INIFNK: A $00, other BC /
    DE / HL. DSPFNK / FNKSB / CLS-with-key-line (R-K-AF, R-CP-AF): A = the last label character drawn, not $00. FILVRM:
    **F is not kept** ($43, or $42 in c23), which breaks R-FV-F. WRTVDP to R#0 with B $FF / $A5: A $00, F $44, B
    kept. Holds on MSX2 and MSX2+.
12. **WRTVDP C = 8..15** writes the V9938 extended registers. On the VG-8020 it aliases R#(C AND 7) and writes
    $F3E7+ (STATFL..MAXUPD). Holds on MSX2 and MSX2+, and it killed xvdpreg (APPARATUS 2).
13. **INIFNK leaves FNKSTR's last byte ($F91E) unwritten.** The garbage stays, where the VG-8020 writes $00. Holds
    on MSX2 and MSX2+ (xfnk2, xfnk3).
14. **MSX2+ only (WSX):**
    - INITIO returns F = $10, not $54 (R-IO-REGS).
    - WRTVDP returns F = $00 / $0C / $44, not $A0 / $A4.
    - CHGCLR's SCREEN 0 path returns F = $00, not $A4.
    - **CLRSPR in SCREEN 0 writes no VRAM** and returns other BC / A / F (c4, c29, c40).

### C-BIOS MSX2 findings

- **Keeps MSX1 behaviour where the MSX2 changed it:**
  - FILVRM's F (C-BIOS also gives $43).
  - INIMLT still writes RG3SAV = 0 (b2vdp, xtot c18-19, xtot2 c12).
  - EI after INIGRP / INIMLT / CHGMOD.
  - No colour masking.
  - The $3FFF wrap in INIGRP / INIMLT / CLRSPR / CHGCLR.
  - INIFNK writes all 160 bytes.
  - The MSX2+ build keeps MSX1 INITIO F $54, WRTVDP F, CHGCLR F and CLRSPR-in-SCREEN-0 VRAM writes.
- **Matches neither reference:**
  - The exit registers of INIGRP / INIMLT / CHGMOD, CLRSPR (A 01-0F, F $93), CHGCLR (DE / HL / F), DSPFNK / ERAFNK / CLS
    / POSIT (A $CF, F $42), INIFNK and WRTVDP C ≥ 8 (A kept, F $A8).
  - Out-of-range CHGMOD leaves DI.
  - **80-column INITXT leaves RG3SAV $A5** (the references give $27) and its VRAM sums differ.
  - **INITXT / INIT32 at width 0 with the key line on gives the pattern / colour / tail sums $0000** (xinit c1, c23).
  - CLRSPR with ATRBAS ≥ $4000 (xclr c43-44) and INIGRP / INIMLT with every cell $FFFF (xinig c36, c39) write VRAM
    neither reference writes.
- **CONFIG only:**
  - The JP builds keep LINL40 37 and the key-6 string "color 15,4,4" (the references give 39 and border 7).
  - Its machine configs have an AY-type PSG (8-bit readback).
  - There is no BASIC (MAXUPD $00).
  - Its own font.

### APPARATUS fixes

1. **xinit3 / xinit4: NO READING on all six machines.** On the references, all RAM (JIFFY $0000, NEWKEY $00, the
   capture) holds a 14-byte repeating frame that contains $5A: a runaway stack. xinit3 case 0 sets RG0SAV := $5A and
   xinit4 case 4 sets $FE. Given GEN 2, this puts IE1 into R#0, and the BIOS never acknowledges that line interrupt.
   **Fix:** on the MSX2 rows, give `rgg` values with bits 4 and 6 clear ($A5 / $A7 / $01 / $04 / $20 / $80 / $AF), or
   restore R#0 after each case. Run the IE1 values as one separate, final case. Confirm by reading R#0 (@vdpsnap)
   after an INITXT with RG0SAV $10.
2. **xvdpreg: NO READING.** Cases 32-39 write R#8-R#15 (GEN 12): R#14 := $A5 (VRAM page 5) and R#15 := $A5 (status
   pointer 5). After that the BIOS and the probe's frame poll read S#5, not S#0, and the run stalls around cases
   42-48. **Fix:** after every C ≥ 8 case, restore R#8-R#15 to their boot values (at least R#14 := 0, R#15 := 0,
   R#9 / R#8), or move those cases to the end.
3. **xsetw: no `@caplen`.** Bytes from +$19 on are unwritten power-on RAM (F900 $FF, C-BIOS cleared). **Fix:** add
   `; @caplen 19`.
4. **xscank:** the +LEN is only trailing-zero trimming. Its "+1" header offset reads one cell low (`$F3DB` = CSRY);
   the work-area offsets below are corrected.
5. **xinit (minor):** in TEXT2 cases (c16-21) and wherever RG3SAV / RG5SAV is not written (GEN 3), the probe's 40-column
   geometry and RG3SAV×$40 / RG5SAV×$80 table addresses read the wrong spans. Record R#0-R#7 (@vdpsnap) before
   reading those sums.

### UNKNOWNs (and the measurement that settles them)

- **FILVRM F, carry bit.** c23 (HL $5234) gives $42 on all three references; every other case gives $43. Measure F
  over HL in $4000-$7FFF and $8000-$FFFF with other A / BC values.
- **All-VRAM sum after TOTEXT → INITXT / INIT32 from SCREEN 2 / 3** (xtot c12-15 and c18-21, xtot2 c0 / c2-8). The
  8250 differs from the VG-8020 although its font matches, and xtot2 c11 differs by $21. Measure xinig-style 1 KB
  block sums after the same calls.
- **WSX "load\"" for F7** (the others give "cload\""). This could be MSX2+ generation or the machine; a second MSX2+
  reference (another maker) would tell.

---

## Per probe

Columns: VG | F900 | 8250 | WSX | C-BIOS (F900 / 8250 / WSX build when they differ).

### b1text (34 B)
| off / field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| +1 CSRY at INIT | 0F | 01 | 01 | 01 | 0A | CONFIG | boot-screen state before cartridge INIT, not a call; C-BIOS has its own logo |
| +3 LINL40 at INIT | 25 | 27 | 25 | 27 | 25 | CONFIG | JP default width 39; C-BIOS JP builds keep 37 (C-BIOS CONFIG finding) |
| +31 RG1SAV at INIT, +32 after INITXT | E0 / F0 | 60 / 70 | = | = | 60 / 70 | GEN 1 | 4/16K bit; C-BIOS = MSX2 |

### b2vdp (96 B)
| off / field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| +1, +33, +52, +70 RG1SAV (SCREEN 1 / 2 / 3 / 1) | E0 E2 EA E2 | 60 62 6A 62 | = | = | = | GEN 1 | |
| +7 RG7SAV after CHGMOD 1 | 04 | 07 | 04 | 07 | = ref | CONFIG | JP default BDRCLR 7 |
| +54 RG3SAV after CHGMOD 3 | 00 | FF | FF | FF | 00 | GEN 3 | MSX2 INIMLT leaves R#3; **C-BIOS = VG-8020** |

### xvram (2834 B, 48-B records from +1)
| off / field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| c20-25, 45-48, 57-58 +1 F (FILVRM) | entry F (00 / FF / A5 / 5A / 01 / 04) | 43 | 43 | 43 | 43 | GEN 11 (R-FV-F) | C-BIOS = MSX2 here |
| c23 +1 F | 00 | 42 | 42 | 42 | 43 | GEN 11 + UNKNOWN / C-BIOS | carry clear on the references for HL $5234 only; C-BIOS always $43 |

### xcls (6203 B): no differing byte on any machine.

### xinig (5250 B, 128-B records; 41 cases)
| field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| +0..+7 A F B C D E H L (all cases) | A = RG1SAV, F A4, BC 0001, DE 7F03 / 0000, HL F3D1 / F3DB | A 00, F 40, B = RG1SAV, C 01, DE 000F / C00F ..., HL 1B80 / 3C00 ... | = | = | A = RG1SAV (MSX1 rule), F A0 / 44 / 42, DE 8800, HL FFF7 | GEN 11 | C-BIOS neither |
| +12 interrupts after (c0, 3, 4, 6, 9, 10, 12, 13, 18, 22, 25, 26, 29, 35, 36, 39) | 01 | 00 | 00 | 00 | 01 | GEN 6 | **C-BIOS = VG-8020** |
| +12 (c17, 33, 34: CHGMOD invalid A) | 01 | 01 | 01 | 01 | 00 | C-BIOS | C-BIOS leaves DI |
| +13 RG0SAV | A7 (GRP) / 01 (MLT, TXT) | A3 / A1 / A5 | = | = | = ref | GEN 2 | |
| +14, +26 RG1SAV, R#1 | E0 / E2 / E8 / F0 | 60 / 62 / 68 / 70 | = | = | = ref | GEN 1 | |
| +16 / +28 RG3SAV, R#3 (INIMLT c6-11, 13, 22-24, 29; INITXT c14, 20, 25) | 00 / 49 | A5 (kept) | = | = | MLT 00, TXT A5 | GEN 3 | **C-BIOS INIMLT = VG-8020** |
| +18-+20 RG5-7SAV (c14, 20, 25) | 00 / F4 | A5 | = | = | A5 | GEN 3 | |
| c16 (CHGMOD 4) +15..+21, +27..+31, sums, windows | SCRMOD 3 | SCREEN 4 (06 FF 03 3F, SCRMOD 04) | = | = | = ref | GEN 8 | |
| c17, 31-34 (CHGMOD $FF / $7F / $80 / $81 / $FE) shadows, SCRMOD, sums, OLDSCR, PATBAS / ATRBAS | aliased mode 0 / 3 | untouched (A5, SCRMOD 01, VRAM preset) | = | = | = ref | GEN 8 | |
| +22 / +23 FORCLR / BAKCLR (c2, 8, 18, 19, 22, 23, 27-30, 35-40), W3 colour bytes c18, 23, 35 | 1A 25 55 F4 F0 | 0A 05 05 04 00 | = | = | = VG | GEN 7 | **C-BIOS = VG-8020** |
| +25, +27, +29-+32 R#0, R#2, R#4-R#7 (debugger) | 01 / 03 / 0F / 07 | 20 / 22 / 3F / 1F / FF | = | = | = | CONFIG | V9938 register widths (R#0 bits 1-6, R#2 7 bits, R#4 6 bits) |
| c28, 29, 36-40 VRAM sums / W1-W3 (cell sets 2 / 3 / 4) | wrapped at $3FFF | written past $3FFF (windows keep preset) | = | = | c28, 29, 40 = VG; c36, 39 neither | GEN 9 | C-BIOS: MSX1 wrap, with a set-3 oddity |
| c14, 15, 20, 21, 25 sums / W (INITXT / INIT32 font) | VG font | JP font | = VG | JP font | own font | CONFIG | character set |

### xinit (8064 B, 130-B records from +4; 62 cases)
| field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| +0 RG0SAV | 01 | A1 (A5 in c16-21) | = | = | = ref | GEN 2 / 4 | |
| +1 RG1SAV | F5 / E5 | 75 / 65 | = | = | = | GEN 1 | |
| +2, +3, +4 RG2-4SAV c16-21 (width 41 / 80 / 255) | 00 00 01 | 03 27 02 | = | = | 03 **A5** 02 | GEN 4 | C-BIOS misses RG3SAV $27 |
| +3, +5, +6 RG3 / 5 / 6SAV (40-column INITXT) | 00 (48 / 68 / 07 moved) | A5 | = | = | A5 | GEN 3 | |
| +7 RG7SAV c47-48 (fg $3A) | E5 | A5 | = | = | E5 | GEN 7 | **C-BIOS = VG-8020** |
| +39..+48 sums, +49..+128 rows, c16-21 | 40-column | TEXT2 layout, preset $5A where read | = | = | sums differ (C6 / 70, 12 / 25) | GEN 4 (+ APPARATUS 5) | |
| c1, c23 rows / sums (width 0, key on) | garbage row (00 00 FF FF ..) | spaces, sums normal | = | = | sums $0000 | GEN 5 / **C-BIOS** | C-BIOS font / colour not loaded |
| +41 / +42 pattern sum (all cases) | 8F7A | D233 | 8F7A | AA37 | 497D / 695C | CONFIG | fonts |
| +43 / +44 / +48 colour / attribute sums | 0004 / 10 | 400B / 2D | = | = | = | GEN 3 consequence | read at RG3SAV×$40 / RG5SAV×$80, which MSX2 leaves at $A5 |
| header +0..+3 | -- | -- | -- | -- | -- | -- | no difference |

### xinit3 (5779 B) and xinit4 (9475 B): NO READING on all six machines (APPARATUS 1)
| field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| whole block | complete | 14-B stack frame repeated ($84 FC 03 03 FC D5 00 5A 0C 38 00 00 00 94; WSX 84 DE 7C 80 ...) | = F900 | own frame | never finished, other garbage (DONE $F0 / $EB) | APPARATUS (cause GEN 2) | RAM overrun by nested interrupts; R#1 at the dump $12 (IE0 off) fits IE1 as the source; xinit4's +LEN is the same failure |

### xinitio … xinitio7 (INITIO)
| field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| F after (xinitio +1, xinitio2-5 +9, +55, +101) | 54 | 54 | 54 | **10** | 54 | GEN 14 (MSX2+ only, R-IO-REGS) | **C-BIOS MSX2+ = VG-8020** |
| PSG R1 / R3 / R5 / R6 / R13 readback | 8-bit | 4 / 5-bit | 8-bit | 4 / 5-bit | 8-bit | CONFIG | PSG type (YM2149-like masking on the JP machines); C-BIOS machine configs differ |
| PSG R14 (port A input) | BF | BF | BF | FF | BF | CONFIG | bit 6 keyboard-layout line on the WSX |
| xinitio5 c0 +37 port $AA | 3A | 35 | 35 | 35 | 35 | TIMING | the VG-8020 run took an interrupt in the window (R-IO-REGS5 note) |
| xinitio5 c2 +37 port $AA | C3 | C3 | C3 | C3 | CA (JP builds) | TIMING | C-BIOS JIFFY moved D6→D7 in the window |
| JIFFY before / after (xinitio5 +224 / +226, xinitio6 +0 / +2, xinitio7 +0 / +2), xinitio7 +4 tries | -- | -- | -- | -- | -- | TIMING | boot length |
| xinitio (8250) | -- | -- | 0 diffs | -- | -- | -- | 8250 identical to the VG-8020 in xinitio-4 |

### xfnk / xfnk2 / xfnk3 (INIFNK)
| field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| key 6 char 11 ("color 15,4,_") | 4 | 7 | 4 | 7 | 4 | CONFIG | JP default border; C-BIOS JP builds keep 4 |
| key 7 ("cload\"" vs "load\"") | cload | cload | cload | load | cload | CONFIG / UNKNOWN | MSX2+ or machine? |
| xfnk2 +161, xfnk3 c1-2 +159: FNKSTR's last byte | 00 | 5A (kept) | = | = | 00 | GEN 13 | **C-BIOS = VG-8020** |
| xfnk2 +164 / +165, xfnk3 +160..+168: A F B C D E H L | A kept, F E9 / 00, BC 00F9, DE 1F14, HL 49.. | A 00, F 6C / 0A, BC 14 0B, DE F9 1F | = | = (WS E 0A) | A 00, F 42 / 00, other BC / DE / HL | GEN 11 | C-BIOS neither (A = MSX2) |
| xfnk3 c1-2 +172 LD A,I flags | 41 | 40 | = | = | 40 | GEN 11 consequence | carry of the exit F |

### xscr / xscr3 / xscr4 / xscr5 (DSPFNK, ERAFNK, FNKSB, CLS, POSIT)
| field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| +0 A after DSPFNK / FNKSB / CLS with key line | 00 | last label character (43, 59, 41, 53, 5E, 5A) | = | = | CF | GEN 11 (R-K-AF / R-CP-AF) | C-BIOS neither |
| +1 F, DSPFNK w 33 / 28, SCREEN 1 w 29 (xscr c13, c16, xscr5 c10) | 44 | 40 | = | = | 42 | GEN 11 | |
| +1 F, CLS SCREEN 2 (xscr c36-37) | 44 | 42 | = | = | 42 | GEN 11 | |
| +0 / +1 ERAFNK, CLS without key line, POSIT, CLS SCREEN 3 | ref values | = VG | = | = | differ (18, FF, 03, 1D ... / 9B, 02, 04, AC, 00 ...) | **C-BIOS** | rule holds on MSX2; C-BIOS MSX2 does not keep it |
| xscr c36-37 +157, +174..+189 (CLS SCREEN 2 colour bytes) | 16 / C5 | 06 / 05 | = | = | = VG | GEN 7 | **C-BIOS = VG-8020** |

### xtot (TOTEXT, 22-B records from +2) and xtot2 (30-B)
| field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| +1 RG1SAV | F0 / E0 / E8 / EB / E3 / F3 | bit 7 clear | = | = | = | GEN 1 | |
| +3 / +5 / +6 RG3 / 5 / 6SAV after INITXT | 00 | 80 / FF / 36 / 07 (earlier values) | = | = | = ref, but RG3 00 after INIMLT (xtot c18-19, xtot2 c12) | GEN 3 | C-BIOS INIMLT = VG-8020 |
| +7 RG7SAV via INIT32 | 04 | 07 | 04 | 07 | = ref | CONFIG | JP border |
| xtot c16-17, 22-23 / xtot2 c10, 13-16 (OLDSCR $5A / $7F / $80 / $81 / $FF): shadows, SCRMOD, OLDSCR, LINLEN, CSRX / Y, rows, sums | SCREEN 3 or 0 set up | nothing done (VRAM $5A, OLDSCR kept) | = | = | = ref | GEN 8 | |
| xtot +15 / 16, c14-15, 20-21 (SCREEN 1 name sum = font) | 70 1C | 52 16 | 70 1C | 52 16 | B5 A4 / 12 04 | CONFIG | font |
| xtot +19 / 20, xtot2 +27 / 28 all-VRAM sum (INITXT / INIT32 from SCREEN 2 / 3) | 0F51 ... | 3103 ... | EE49 ... | 0907 ... | C953 ... | CONFIG + UNKNOWN | the 8250 differs from the VG-8020 without a font difference |
| xtot2 c11-12 +27 (OLDSCR 2 / 3) | 80 | 5F | 5F | 5F | 80 | UNKNOWN | $21 residual; C-BIOS = VG-8020 |

### xclr (CLRSPR / CHGCLR, 7426 B, 128-B records; 58 cases)
| field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| CLRSPR +0 A / +1 F | FORCLR / 28, 95, 20, 08 | 40 / 00 | = | = | 01-0F / 93, 42 | GEN 11 (R-CS-REGS) | C-BIOS neither |
| CHGCLR SCREEN 1 +1 F (c13, 17, 20, 22, 36, 50, 57) | A0 / A4 / 44 / 20 | 42 | = | = | 43 | GEN 11 (R-CC-REGS) | |
| CHGCLR SCREEN 0 +1 F (c12, 16, 23, 35, 37, 39, 48, 56) | A4 | A4 | A4 | **00** | BA / AA / 82 | GEN 14 (MSX2+ only) | C-BIOS neither |
| CHGCLR +4..+7 DE / HL | 64 20 DB 97 ... | = VG | = | = | 00 / FF, F4, F3, EB | **C-BIOS** | MSX1 rule holds on MSX2; C-BIOS does not keep it |
| +26 R#1 (debugger) | 80 / E0 / E2 | 00 / 60 / 62 | = | = | = | CONFIG | V9938 has no bit 7 |
| CLRSPR c4, 29, 40 (SCREEN 0): +0..+3, W1 / W3, sums | sprite attribute $D1 written, BC 0020 | = VG | = VG | BC F0 / E0 / E2 01, VRAM untouched (47, 0A, 00) | = VG | GEN 14 (MSX2+ only) | **C-BIOS MSX2+ = VG-8020** |
| CLRSPR c11, 42, 53, 54 (SCRMOD $77 / $04 / $81) | mode-1 sprites | sprite mode 2 (+46 28, +65 D9) | = | = | = ref | GEN 10 | |
| CLRSPR c31 (ATR $3FC0, PAT $3C00) block 0 | wrapped (78 0F) | 00 00 | = | = | = VG | GEN 9 | **C-BIOS = VG-8020** |
| CLRSPR c43-44 (ATR $5B00 / $9B00, PAT $B800) | ANDed $3FFF | not ANDed | = | = | neither (block 0 zeroed) | GEN 9 / **C-BIOS** | |
| CLRSPR c55 (RG1SAV $60, 4K bit clear) +43 / +44 | 10 01 | 00 08 | = | = | = ref | GEN 9 | R-CS-VRAM's bit-7 condition gone |
| CHGCLR c50 (T32COL $FFFF) sums | E1 11 ... | 8C 1D ... | = F900 | 41 67, $54 at other blocks | = VG | GEN 9 (+ MSX2+ variant) | **C-BIOS = VG-8020** |

### xsetw (255 B)
| field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| +1..+24 (the probe's capture) | -- | -- | -- | -- | -- | -- | no difference: SETWRT / SETRD hold |
| +0, +$19..+$FE | power-on RAM | FF | pattern | pattern | 00 | APPARATUS 3 | outside the capture; set `@caplen 19` |

### xscank (SCANR, work area $F380-$FFFF × 3)
| field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| HL after SCANR (the subject) | -- | -- | -- | -- | -- | -- | no difference |
| $F3E0 RG1SAV | E0 | 60 | = | = | = | GEN 1 | |
| $F3AE LINL40, $F3E6 RG7SAV, $F3EB BDRCLR | 25 / 04 / 04 | 27 / 07 / 07 | 25 / 04 / 04 | 27 / 07 / 07 | = ref, LINL40 25 | CONFIG | JP defaults |
| $F3DC CSRY | 0F | 01 | 01 | 01 | 0A | CONFIG | boot-screen state |
| $F3F6 SCNCNT, $FC9E-$FCA2 JIFFY / INTCNT | -- | -- | -- | -- | -- | TIMING | |
| $F55E-$F567, $F663-$F6E3, $F74C, $F7C6-$F7FD, $F858-$F869, $F8DA-$F8E4, $FAF6-$FB20, $FBB2 / $FBB5, $FC40-$FC46, $FCAD-$FCFD, $FEFD-$FF00, $FFCA-$FFFF (EXTBIO / DISINT / ENAINT, RG8SAV+), $F39A-$F3AE (C-BIOS) | -- | -- | -- | -- | -- | CONFIG | MSX2 work area and hooks, disk / BASIC areas, EXPTBL slot 3 expanded ($FCC4 $80), C-BIOS has no BASIC |
| +LEN | -- | -- | -- | -- | -- | APPARATUS 4 (harmless) | trailing zeros trimmed |

### xvdpreg: NO READING on all six machines (APPARATUS 2); completed cases 0-~42 classified
| field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| header +5 / rec +18 $F3EB BDRCLR | 04 | 07 | 04 | 07 | = ref | CONFIG | JP border |
| header +6 / rec +19 $F3EC MAXUPD | C3 | C3 | C3 | C3 | 00 | CONFIG | C-BIOS has no BASIC |
| +1 F, WRTVDP C 0-7 | A0 / A4 | = VG | = VG | 00 / 0C / 44 | A0 | GEN 14 (MSX2+ only) / **C-BIOS** | C-BIOS A0 where the references give A4 (c4-11, 16-19 ...) |
| c1, c3 (R#0, B $FF / $A5) +0 / +1 / +2 | A B, F A0, B 00 | A 00, F 44, B kept | = | = | = VG | GEN 11 | |
| c32-39 (C 8-15): +0..+2, $F3E7+ (+14..+21), +22.. R#(C AND 7), +30 | A = B, $F3E7+(C-8) := B, R#(C AND 7) := B | A 00, F 44, B kept, $F3E7+ untouched, R#0-7 untouched | = | = | A kept, F A8, else = ref | GEN 12 / **C-BIOS** | extended registers |
| +22..+29 R#0-R#7 (debugger) | TMS widths (03, 0F, 07, C0) | V9938 widths (7E, 7F, 3F, 40) | = | = | = | CONFIG | VDP chip |
| trailing cases 43+ | -- | missing | missing | missing (from 49) | missing | APPARATUS 2 | stall |
