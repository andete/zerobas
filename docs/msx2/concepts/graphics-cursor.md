<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# The MSX2 sub-ROM's graphics cursor and drawing entries — shared facts

> **Status:** DRAFT 0 (2026-11-23), from the published interface; the cursor model and the baseline state are now
> MEASURED on the call pages ([MAPXYC](../sub/MAPXYC.md), [SETC](../sub/SETC.md), [READC](../sub/READC.md),
> [SETATR](../sub/SETATR.md), [SCALXY](../sub/SCALXY.md)) and summarised below, cited to them.
> References: Sony HB-F900 (MSX2, JP), Philips NMS 8250 (MSX2, EU), Panasonic FS-A1WSX
> (MSX2+). Subject: C-BIOS's MSX2 / MSX2+ builds. Each call's state is on its own page, never here.
>
> Goldfish pass 1 (test writer) 2026-11-23: 3 findings, 1 measured (the baseline state), 0 moved to open, 2 corrected (the stale "nothing measured" / "model unpublished" text).

## Summary

The MSX2 sub-ROM is taken to carry, from $0085 to $00CD, a second copy of the graphics position calls the MSX1
main ROM has from $00FC up ([the MSX1 graphics calls](../../concepts/graphics-calls.md)), plus a line
(DOGRPH), two edge-checked horizontal moves (TRIGHT, TLEFTC) and two box routines (NVBXLN, NVBXFL).
Their new territory is the bitmap modes SCREEN 5-8 (and, on an MSX2+, 10-12): one pixel is 2, 4 or
8 bits of a byte, the screen is 212 (or 192) lines high, VRAM holds several pages, a logical
operation (LOGOPR) can combine the colour with what is there, and the VDP has a command engine
that draws points, lines and rectangles.

**The handbook publishes only three of these nineteen entries** (GRPRT $0089, NVBXLN $00C9, NVBXFL
$00CD). The others' names and addresses are not in it; nearly everything on their pages is
therefore **[A]**, and the first measurement for each is whether the address is a callable entry
at all on each reference.

## Sources and tags

- **[P TH A1 …]** — the MSX2 Technical Handbook, Konamiman's English translation, Appendix 1 (BIOS
  listing). **[P TH A4]** — Appendix 4 (work area). **[P TH 4 §n]** — Chapter 4 (VDP), section n.
  **[P TH 2 …]** — Chapter 2 (BASIC). Every [P] is a paraphrase.
- **[A]** — assumed, not measured, and not published.
- C-BIOS's source is consulted only for which entries it implements; it states no reference rule.

## The published facts

- **Calling a sub-ROM entry:** IX := the entry address, `CALL EXTROM` ($015F); or push IX, load it
  and `JP SUBROM` ($015C) when IX must survive [P TH A1 SUB-ROM, preamble]. EXTROM keeps
  the alternate registers and IY [P TH A1 MAIN-ROM: EXTROM]; what a called entry itself keeps is
  per entry.
- **The sub-ROM listing in this area** names only GRPRT ($0089: one character to the graphic screen,
  active only in SCREEN 5-8), NVBXLN ($00C9: a box) and NVBXFL ($00CD: a filled box) [P TH A1
  SUB-ROM]. **It has no entry for $0085, $008D, $0091-$00C5** [P TH A1 SUB-ROM, by absence].
- **The main-ROM listing** marks GRPPRT ($008D) `*2`, "calls the sub-ROM internally in SCREEN 5 to
  8", and names LOGOPR as its input [P TH A1 MAIN-ROM: GRPPRT; legend]. **It has no entries for the
  MSX1 graphics calls $00FC-$012F at all** [P TH A1 MAIN-ROM, by absence]: whether those forward
  to the sub-ROM in SCREEN 5-8 is unpublished [A]. Every cursor page therefore has a **main-entry
  row**: the same SCREEN 5 case through the main-ROM address, compared with the sub-ROM entry's.
- **Work-area cells** [P TH A4]: ATRBYT $F3F2 (1 byte, initial 15: the graphics colour); CLOC $F92A
  (2) and CMASK $F92C (1), both "used internally by the graphic routines" -- **their meaning in the
  bitmap modes is unpublished**; DPPAGE $FAF5 and ACPAGE $FAF6 (display / active page); MODE $FAFC
  (VRAM size, bits 1-2, and bit 3 "mask VRAM addresses with $3FFF in SCREEN 0-3"); LOGOPR $FB02
  (the logical operation code); SCRMOD $FCAF; BRDATR $FCB2 (PAINT's border colour); GXPOS $FCB3 and
  GYPOS $FCB5 (a coordinate pair); GRPACX $FCB7 and GRPACY $FCB9 (the graphics accumulator, the
  "last point"); FORCLR $F3E9; CGPNT $F91F; PATWRK $FC40.
- **A conflict inside the handbook:** NVBXLN's and NVBXFL's entries give ATRBYT as **$F3F3**
  [P TH A1 SUB-ROM: NVBXLN, NVBXFL], Appendix 4 as **$F3F2** [P TH A4]. Which cell the boxes read
  is a measurement: cases BL-01 ([NVBXLN](../sub/NVBXLN.md)), BF-01 ([NVBXFL](../sub/NVBXFL.md)),
  SA-06 ([SETATR](../sub/SETATR.md)), DG-06 ([DOGRPH](../sub/DOGRPH.md)).

## The bitmap modes' pixel layout

From [P TH 4 §3.6-§3.9] and the VDP command coordinate system [P TH 4 §6.1]:

| SCREEN | VDP mode | pixels | bits / pixel | byte address of (X, Y) in a page | pixel within the byte | pages (size) |
|---|---|---|---|---|---|---|
| 5 | GRAPHIC 4 | 256 x 212 (or 192) | 4 | X/2 + 128 Y | even X the high nibble, odd X the low | 4 x $8000 (128 KB VRAM) |
| 6 | GRAPHIC 5 | 512 x 212 | 2 | X/4 + 128 Y | X mod 4 = 0, 1, 2, 3: bits 7-6, 5-4, 3-2, 1-0 | 4 x $8000 |
| 7 | GRAPHIC 6 | 512 x 212 | 4 | X/2 + 256 Y | even X high nibble, odd X low | 2 x $10000 |
| 8 | GRAPHIC 7 | 256 x 212 | 8 | X + 256 Y | the whole byte: G (3 bits), R (3), B (2) | 2 x $10000 |

- The VDP commands address VRAM as one coordinate space: X 0-255 or 0-511, **Y 0-1023** across the
  pages (page n starts at Y = 256 n) [P TH 4 §6.1, figure 4.72]. A screen Y and a page combine into
  one command Y; whether the BIOS calls add ACPAGE x 256 is unpublished [A].
- In SCREEN 5-8, BASIC's VPEEK / VPOKE address is an offset from the active page's start
  [P TH 2, VPEEK / VPOKE].
- SCREEN 7 and 8 need 128 KB VRAM [P TH 4 §3.8, §3.9].
- **SCREEN 10-12 (MSX2+) are not in this handbook.** Their layout, and how these calls treat them,
  is [A] and measured on the FS-A1WSX only.

## Logical operations and the command engine

- **Logical operations** [P TH 4 §6.3, table 4.6]: code 0 IMP (destination := source colour), 1 AND,
  2 OR, 3 EOR, 4 NOT (destination := NOT source); 8-12 the same with T: a source colour of 0 leaves
  the destination as it was. 5-7 and 13-15 are undefined.
- BASIC's names are PSET (the default), AND, OR, XOR, PRESET and the T-prefixed forms
  [P TH 2, table 2.7]. **That LOGOPR holds the table 4.6 code** (PSET 0, AND 1, OR 2, XOR 3, PRESET
  4, T + 8) is [A]: the handbook only calls it "the logical operation code" [P TH A4].
- **The commands** [P TH 4 §6.2, §6.5]: PSET ($5x), LINE ($7x), LMMV ($8x) and the others take the
  logical operation in R#46's low nibble; SRCH ($60) and POINT ($40) take none. Parameters sit in
  R#32-R#45, the colour in R#44; S#2 bit 0 (CE) is 1 while a command runs; POINT leaves the colour
  in S#7, SRCH the found X in S#8 / S#9 and "found" in S#2 bit 4 (BD). Commands are guaranteed only
  in GRAPHIC 4-7 [P TH 4 §6.2]. After a command, DY (and SY, NY) hold their end values, the rest
  is kept [P TH 4 §6.7, table 4.7].

## The cursor model — rival rules to separate

The bitmap cursor is unpublished. **Measured: model C, identical on all three references** -- in SCREEN 5-8 MAPXYC
stores CLOC := X verbatim (0-511, never clipped) and CMASK := Y's low byte; SETC / READC address the pixel from them,
replace its field (LOGOPR applied) and read it back ([MAPXYC](../sub/MAPXYC.md), [SETC](../sub/SETC.md),
[READC](../sub/READC.md), [M]). In SCREEN 2, 3 and 4 the sub-ROM calls use the MULTICOLOUR form (CLOC := MLTCGP +
the cell's byte, CMASK $F0 / $0F; SCALXY divides by 4), not the MSX1 SCREEN 2 bit form ([MAPXYC](../sub/MAPXYC.md),
[SCALXY](../sub/SCALXY.md), [M]). Whether ACPAGE takes part is still open (MX-07, SC-08, RD-06). The candidate
models, as they were set up to be separated [A]:

| model | CLOC | CMASK | pages |
|---|---|---|---|
| **B (byte)** | the pixel's byte address, low 16 bits (SCREEN 7 / 8 lose bit 16) | the pixel's bits in the byte: $F0 / $0F (5, 7); $C0 / $30 / $0C / $03 (6); $FF (8) | ACPAGE added into the address, or not |
| **C (coordinate)** | the X coordinate (0-511) | the Y coordinate's low byte (Y 0-211 fits) | ACPAGE added to Y at draw time, or not |
| **M (MSX1-shaped)** | as model B | as SCREEN 2: one bit $80 >> (X AND 7) | — |

Separating inputs: X with X ≠ the byte address (any Y > 0); Y > 0 with X = 0 (B gives 128 Y or 256
Y, C gives 0); X odd vs even (CMASK $0F vs $F0 under B; unchanged under C); SCREEN 6 X mod 4 = 1 ($30
under B, $40 under M). **ACPAGE** separates in CLOC only in SCREEN 5 / 6, where B with the page
added moves by $8000 x ACPAGE (ACPAGE 2 gives $10000 and is lost in 16 bits like page 0). In SCREEN
7 / 8 a page is $10000, so CLOC is the same under every model: only a call that DRAWS or READS
(SETC's SC-08, READC's RD-06) shows the page there. And because MAPXYC may or may not add the page,
an edge test's page dependence is measured with a **hand-planted CLOC** ($8000 + offset), not only
through MAPXYC.

## Shared measurement setup (every page's matrix assumes it)

The pages cite these sets by name.

- **No generation carries over (Joost, 2026-11-23).** Every case runs on the HB-F900, the NMS 8250
  and the FS-A1WSX, and each machine's result is its own record (the pages' per-machine columns). No
  MSX1 or MSX2 behaviour is a premise for the MSX2+; a rule that holds on one generation only names
  it. Where the V9958 could change a rule (R#25's command bit outside the bitmap modes, the R#26 /
  R#27 scroll, SCREEN 10-12), the page has a row whose answer is open per machine.

- **The baseline the measured cases ran at** [M, [xsubgc2.asm](../../../probes/bios/spec/xsubgc2.asm) STATE,
  [decoded](../../../scratchpad/AE_xsubgc2_msx2_decoded.out)]: CHGMOD leaves LOGOPR 0 (IMP), ACPAGE 0, DPPAGE 0,
  GRPCGP = MLTCGP = $0000, R#9 LN 1 in SCREEN 5-8 and LN 0 in 2-4 (bit 1, PAL, set on the NMS 8250 only), S#2 CE 0
  (no command running), R#45 / R#46 0, on all three references. A page's [M] line holds at that state unless it says
  otherwise; the [PG], [LG], [LN] sets below are what moves away from it.
- **Desynced cells:** GRPACX / GRPACY, GXPOS / GYPOS, CLOC / CMASK and BC / DE each name a
  DIFFERENT point, so "the call used this pair" is visible. FORCLR ≠ ATRBYT ≠ BAKCLR; the byte at
  $F3F3 ≠ ATRBYT.
- **The page set [PG]:** (ACPAGE, DPPAGE) = (0, 0), (1, 0), (2, 3), (3, 1) in SCREEN 5 / 6; (0, 0),
  (1, 0), (0, 1) in SCREEN 7 / 8. VRAM garbage address-dependent over all 128 KB (never a valid
  colour pattern), so a write to the wrong page shows.
- **The LOGOPR set [LG]:** 0 (IMP), 3 (EOR), 4 (NOT), 8 (TIMP) with the colour 0 and with a
  non-zero colour, and the undefined codes 5 and 13; $F3 for "is the high nibble masked". Separates
  "honours LOGOPR" from "ignores it" from "masks it".
- **The line set [LN]:** every edge or clipping case runs with R#9 LN 0 and 1 (192 / 212 lines).
- **The MODE set [MD]:** every SCRMOD 2 / 3 case runs with MODE ($FAFC) bit 3 clear and set (VRAM
  addresses masked with $3FFF or not [P TH A4]), with CLOC planted above $3FFF in one case.
- **ATRBYT** in range and above the mode's range ($1A in SCREEN 5 / 7, 5 in SCREEN 6, $C3 in 8).
- **The command engine at entry:** idle; busy (a long LMMV started, CE = 1); R#45 garbage (DIX, DIY,
  MXD / MXS set). Separates "waits for CE" from "writes over a running command", and "sets every
  register" from "leaves the probe's".
- **The snapshot [SN]** taken before and after every case, through the openMSX debugger: the whole
  of RAM (a diff, which finds cells no page names), VRAM, the VDP registers R#0-R#46 (the command
  registers' residue included), S#0-S#9 (S#2 read at once on return: CE still 1 means the call
  returned before its command ended), the palette, and the log of writes to the VDP ports (which
  counts the commands issued). "Nothing else changes" on a page is a claim on this snapshot.
- **The R#9 copy [R9]:** the handbook lists RG0SAV-RG7SAV only [P TH A4]. Before any case that
  desyncs R#9 from its RAM copy, locate the copy: a RAM diff across a WRTVDP (main $0047) write of
  R#9, done once per reference.
- **Registers and flags** loaded with garbage before every call (IX holds the entry by convention);
  the interrupt state read twice; SCNCNT held off. Per [the spec method](../../spec-method.md) §3a.
- **Modes:** SCRMOD 2, 3, 4 (the MSX1-shaped modes through the sub-ROM entry), 5, 6, 7, 8; on the
  FS-A1WSX also 10, 11, 12.

## Related pages

[The MSX1 graphics calls](../../concepts/graphics-calls.md) (the measured SCREEN 2 / 3 contracts);
[DOGRPH](../sub/DOGRPH.md), [GRPPRT](../sub/GRPPRT.md), [SCALXY](../sub/SCALXY.md), [MAPXYC](../sub/MAPXYC.md), [READC](../sub/READC.md), [SETATR](../sub/SETATR.md), [SETC](../sub/SETC.md), [TRIGHT](../sub/TRIGHT.md), [RIGHTC](../sub/RIGHTC.md), [TLEFTC](../sub/TLEFTC.md), [LEFTC](../sub/LEFTC.md), [TDOWNC](../sub/TDOWNC.md), [DOWNC](../sub/DOWNC.md), [TUPC](../sub/TUPC.md), [UPC](../sub/UPC.md), [SCANR](../sub/SCANR.md), [SCANL](../sub/SCANL.md), [NVBXLN](../sub/NVBXLN.md), [NVBXFL](../sub/NVBXFL.md).
