# Goldfish review (test-writer role), 2026-11-23: docs/msx2/sub/CALPAT.md docs/msx2/sub/CALATR.md docs/msx2/sub/GSPSIZ.md docs/msx2/sub/CLRSPR.md docs/msx2/sub/GETPAT.md

**Evidence read:** `probes/bios/spec/xspr2.asm` (record layout, case table) and `scratchpad/AE_xspr2_msx2.out`.
I decoded by hand all 35 records (32 bytes each) of the **ref** CAP for all three runs (NMS 8250, HB-F900, FS-A1WSX;
the three ref strings are byte-identical) and the **ours** records named in the DIFF lists (CLRSPR and GETPAT). I
compared the other `ours` records only as hex strings. I did **not** read or run `scratchpad/xspr2_decode.py` (it is
named, not linked). I did not read `vdp-and-palette.md` or the MSX1 pages (they are not evidence files).

Facts that the items below depend on (ref, decoded): CALPAT F = $68 (8x8) / $28 (16x16) / $10 (A $FF, 16x16);
CALATR F = $48 (SCREEN 1) / $60 (SCREEN 5) / $68 (SCREEN 5, A $FF); GSPSIZ F = $48 / $49, HL $2468 kept; GETPAT A $00, F
$08 / $08 / $30, **HL = $1DCF / $1BC7 / $23BF for A $41 / $00 / $FF (= $1BBF + 8 x (A + 1))**; CLRSPR A $40, F $00. The
probe records only A, F and HL, never BC / DE / IX / IY, and only the **first 16 attribute bytes** (planes 0-3).
Every case ran with the CHGMOD-default tables and FORCLR.

## 1. Rules not pinned by any measured case

1. **CLRSPR**: the pattern clear (the [P] rule "patterns := null" and the [A] span) is not measured at all. The
   probe reads no pattern VRAM. Pin: preset 2048 + 256 bytes from PATBAS to garbage and read them back (CS-03a/c).
2. **CLRSPR**: the mode-2 colour table is not measured (no byte at ATRBAS - $200 is read), and neither is any plane
   past 3. The Measured line says "every attribute entry", but only planes 0-3 were observed. Pin: read all 128
   attribute bytes and the 512 colour-table bytes (CS-02 / CS-03b).
3. **GETPAT**: the source is still [A] in the page. But the measured HL ($1BBF + 8(A+1)) points straight past the
   character in the main ROM's font at $1BBF, and not into SCREEN 1's VRAM pattern table at $0000. The page does
   not use this evidence, and it does not name the RAM pointer CGPNT as a candidate source. Pin: GP-01, plus CGPNT
   moved (see 2.2).
4. **GSPSIZ**: "magnification (bit 0) ignored" is not measured. The probe changes only bit 1, so bit 0 kept whatever
   CHGMOD left. Pin: GS-01 with RG1SAV $E1 / $E3.
5. **GSPSIZ / CALPAT / CALATR**: the register-preservation claims are not measured for BC and DE. GSPSIZ says "only
   AF changes" and the MSX1 rule says "DE := offset", but the probe never stores BC or DE. HL kept ($2468) is
   measured only for GSPSIZ. Pin: store BC, DE, IX, IY after the call (GS-04 / CP-06 / CA-06).
6. **GSPSIZ / CALPAT / CALATR / CLRSPR / GETPAT**: the flags are measured but not stated. Each page leaves F [A]
   while the run already holds a constant F per case, for example GSPSIZ $48 / $49 (Z and bit 3 set on all three
   references). A test writer has no rule to assert. State the measured F, or say explicitly that F is excused.
7. **CALATR**: only 8 x 8 was measured (every CALATR case has size 0). "The sprite size plays no part" is not
   pinned. Pin: CA-01 with RG1SAV bit 1 set.
8. **CLRSPR**: no case pins A $40 and HL (ATRBAS + $80 / ATRBAS - $200) as rules. Both come from one table position
   per mode, with default bases only. Pin: CS-11 (ATRBAS moved) and record A / HL.

## 2. Rules the measured cases could also explain with a different rule

1. **CLRSPR** byte 3 := $0F: this could be FORCLR (the default is 15) or the constant $0F. FORCLR was never changed.
   CS-12 / CS-03a (FORCLR $0A / $1F) separate the two. This also bears on the C-BIOS comparison ("write the same
   attribute bytes").
2. **GETPAT**: the source could be the fixed ROM font at $1BBF, the font found through CGPNT (slot plus address), or
   VRAM. Every case is consistent with the first two. Separating case: CGPNT's address moved to a RAM copy holding
   distinct bytes. GP-02 moves CGPBAS (VRAM) instead, so it does not separate them.
3. **CALPAT / CALATR**: the base could be "PATBAS / ATRBAS cell + offset" or "the mode's default table + offset".
   Neither cell was ever moved. CP-02 (PATBAS $F000) separates them only if SCRMOD is not 7 / 8, where $F000 is the
   default, and CP-02 states no SCRMOD. CA-05 does separate them for CALATR.
4. **GSPSIZ / CALPAT / CLRSPR**: the size could come from RG1SAV bit 1 or from the shadow CHGMOD wrote (R#1). The
   probe changes RG1SAV in RAM only, so in some cases R#1 likely held the previous case's size. The page does not
   say which cases (if any) had the two disagreeing, so "read from RG1SAV bit 1" is asserted, not shown.
5. **CLRSPR** pattern number 4n for 16 x 16: this could be "n x 4" or "n x (size / 8)". Planes 0-3 only, so a
   5-bit-masked or 8-bit result cannot be told apart. This is harmless while n ≤ 31, but plane 31 = 124 was not
   observed.

## 3. Citations that do not match the tables

1. **CALPAT** Measured says "a plain 16-bit sum, **no wrap**". No measured sum exceeds $FFFF (the largest is
   $97E0), so wrap is untested. The page's own CP-02 and Behaviour bullet keep it open. "No mask" is pinned; "no
   wrap" is not.
2. **GETPAT** Differences says C-BIOS returns "other flags" only. On the EU C-BIOS build, A $FF returns **A $55**
   (ref $00) and PATWRK AA 55 AA 55 ... (C3C7-C3D2 in the DIFF). So A differs too, at least on msx2eu.
3. **CLRSPR** Summary says every sprite goes to Y = 217. The Measured line (correctly) says $D1 = 209 in sprite
   mode 1. The Behaviour bullet still holds "whether the call writes 217 in sprite mode 1" as [A], although the run
   answers it.
4. **CLRSPR** Behaviour holds "whether the attribute's (unused) fourth byte is written" in mode 2 as [A]. The run
   shows it written ($5A → $0F, SCREEN 5 records), and the Measured line says so.

## 4. Gaps in the open lists

1. Several open rows are already answered by the run and should be narrowed or marked measured:
   - CALPAT CP-01 (exactly the measured inputs) and CP-05;
   - CALATR CA-02 (the 8-bit and 5-bit-mask alternatives are already excluded by $1EFC at A $FF) and CA-01 at $1B00
     / $7600;
   - GSPSIZ GS-03 and the "8 / 32 vs 8 / 16" half of GS-01;
   - GETPAT GP-04;
   - CLRSPR CS-01 (Y 209, X left), CS-02 (Y 217) and the "written vs left" half of CS-04.
2. **GETPAT** has no row that moves CGPNT ($F91F-$F921), the cell that most plausibly names the font (see 2.2). It
   also has no row for HL / F on return, although these are measured and explain the source.
3. **CALPAT** CP-02 does not name a SCRMOD. It must name a mode whose default PATBAS is not $F000, or it cannot
   separate the cell from the default (2.3).
4. **CLRSPR** has no row that reads planes 4-31. The rows also never ask for the attribute bytes to be read back in
   full: every row implicitly relies on a recording richer than this probe's 16 bytes.
5. **GSPSIZ / CALPAT** rows GS-02 / CP-04 ("the RAM copy vs the VDP"): R#1 is write-only, so the rows as worded
   separate nothing for a read. The realistic alternative is "RG1SAV vs another RAM cell" (or vs a value CHGMOD
   cached), and no row names one.
6. **CLRSPR** has no row that varies FORCLR in SCREEN 1 alone with 8 x 8 (CS-12 mixes modes). It also has no row
   for an ATRBAS whose plane-31 entry crosses a 16 KB boundary.
