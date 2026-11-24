# Goldfish review (test-writer role), 2026-11-23: docs/msx2/sub/NVBXLN.md, NVBXFL.md, DOGRPH.md, GRPPRT.md, SCANR.md, SCANL.md

**What I decoded.** By hand, from the reference `CAP ref` lines of all three machines (NMS 8250, HB-F900, FS-A1WSX):
- `scratchpad/AE_xsubbox_msx2.out`: all 7 records. Header fields (A, F, GXPOS..GRPACY, R#36-R#45) fully. Windows fully for cases 0, 1, 5 and 6. Cases 2 and 3 I only scanned for the fill rectangle. Case 4 (DOGRPH) I read only as the step pattern between `05` bytes, NOT counted pixel by pixel.
- `scratchpad/AE_xsubgpp_msx2.out`: all 7 records (header and window).
- `scratchpad/AE_xsubscan_msx2.out`: all 5 records (header and line).
- The `CAP ours` lines only where a page's "Differences" paragraph cites them.

**What I did not read or decode.** `scratchpad/xsubbox_decode.py` and `xsubgpp_decode.py` (named but not linked). The concept page `graphics-cursor.md`, so the sets [PG]/[LG]/[LN]/[MD]/[SN]/[R9] are taken on trust. Nothing was run.

## 1. Rules not pinned by any measured case

1. **GRPPRT**: "at Y 207 GRPACY stays (no wrap, no scroll)" is not a bottom-edge rule. Case 5 started at X 10, so no line feed was due and GRPACY would stay under any bottom rule. Pin it with a character at (250, 207) and a CR at Y 207 (and 203 / 204), reading GRPACY and the rows near Y 0 and Y 211.
2. **SCANR**: the B gate is unmeasured. The only B 0 case (op 1) has DE 0, which returns at once whatever B is, so "paints when B is not 0" rests on B 1 alone. Pin it with B 0 / B 1 / B $80 at DE 1 (SR-02 at DE 1, not DE 5 only).
3. **SCANR**: "skips border-colour pixels, counting DE down" is never exercised. No measured case starts on a border pixel, and DE 1 comes back 1. Pin it with SR-03 (start on 3 border pixels, DE 2 / 3 / 4), reading DE, HL and CLOC.
4. **GRPPRT**: what happens to the glyph at the right-edge wrap is unmeasured. Case 4's window (X 8-23) shows neither X 250-255 of row 10 nor X 0-7 of row 18. Pin it with a window over X 248-255 at Y 10-17 and X 0-15 at Y 18-25: clipped, drawn after the wrap, or nothing.
5. **GRPPRT**: in SCREEN 2 only the GRPACX advance is measured. The window address (Y x 128 + 4) is not where a SCREEN 2 glyph at (10, 10) lands (pattern byte $010A), so "drawn the MSX1 way" vs "only advances" is open. Read the pattern and colour bytes of the char cell at (8..15, 8..15).
6. **NVBXLN / NVBXFL**: "GRPACX / GRPACY kept" cannot be read from the box cases. Both were preset to 0, and a write of 0 is invisible. Use non-zero distinct markers (BL-11 / BF-11).
7. **SCANL**: "CSAVEA / CSAVEM untouched" rests on a 0 marker, which a write of 0 would also give. Preset CSAVEA/CSAVEM to distinct non-zero values before SCANL.
8. **DOGRPH**: the end point (23, 9) sits on the window's last column and first row. An overshoot past the end (an X 24 or Y 8 pixel, the kind C-BIOS's NVBXLN shows) would be invisible. Re-measure with both ends at least 2 pixels inside the window.
9. **GRPPRT**: "registers: none changed" is measured only for A. BC, DE, HL, IX and IY were not captured. Capture them with garbage in each (GP-15).
10. **GRPPRT**: drawing at an odd X in SCREEN 5 is unmeasured. Case 2's cell starts at X 10, byte-aligned, so a mask/merge at a shared byte is never tested. Add GRPACX 11 in SCREEN 5.
11. **NVBXLN**: "the same with the corners in either order" was measured for one other order only, (20, 15)-(10, 10). The anti-diagonal pair (20, 10)-(10, 15) is unmeasured (BL-02 second input).

## 2. Rules the cases could ALSO explain with a different rule

1. **NVBXLN**: the XOR case cannot show XOR. Preset $0F XOR ATRBYT $05 = **$0A, which is exactly the byte placed at $F3F3**, so an all-$0A outline also fits "under LOGOPR ≠ 0 it draws $F3F3 with PSET". It also fits "LOGOPR ignored, colour from $F3F3", and under that rule a corner drawn twice would still read $0A. "Each pixel drawn once" therefore depends on XOR really being applied. (The residue A $73, R#44 $05 points to XOR, but the page does not argue from it.) Separate them with $F3F3 set to a value ≠ preset XOR ATRBYT (e.g. $0C).
2. **GRPPRT**: "LOGOPR 8 (TIMP) does not make the 0 pixels transparent" cannot tell "LOGOPR ignored" from "TIMP honoured". TIMP skips only source colour 0, and BAKCLR was $03, so a faithful TIMP also draws every pixel. Separate them with LOGOPR 3 (XOR) over the $0F preset, or TIMP with BAKCLR 0. GP-05 as written (BAKCLR 2, non-zero) has the same blind spot.
3. **GRPPRT**: "1 pixels in FORCLR (not ATRBYT)" also fits "ATRBYT := FORCLR, then drawn with ATRBYT" (the MSX1 rule the interface keeps as [A]). The probe never reads $F3F2 after the call. Read ATRBYT after case 0.
4. **SCANR / SCANL**: "stops at the border BRDATR" also fits "stops at any pixel ≠ the start pixel's colour" or "at any non-zero pixel". The line is all $00 except the $0F borders. Separate them with a non-zero, non-BRDATR pixel (e.g. $07) inside the run, plus SR-05 / SL-06.
5. **SCANL**: "paints LEFTWARDS from the pixel left of the start" cannot be seen in an end state. Painting X 31-59 rightwards from the found border gives the same line, and the MSX1 summary says rightwards. Separate them with the [SN] port log or the command's DX / DIX residue (SL-14), or a mid-command snapshot.
6. **DOGRPH**: "(BC, DE) -> (GXPOS, GYPOS)" states a direction the pixels cannot show. The residue (DX $17 = 23, ARG $05 = DIX 1, MAJ 1, DIY 0, DY 16) reads as a LINE that *started* at (23, 9), GXPOS/GYPOS, and ran towards (20, 15). The two directions agree on which points are joined. Separate them by DG-03's swapped pair together with the R#36-R#45 residue, and say "joins", not "->".
7. **NVBXLN**: "After: GXPOS / GYPOS = (10, 14), the last side's start" fits several rules, and it was (10, 14) for BOTH corner orders. Other readings: "min X, max Y − 1" (corners sorted, then sides drawn in a fixed order), or "the last LINE's start under one fixed side order". Separate them with an asymmetric box elsewhere (e.g. (30, 40)-(50, 60) and its reverse).
8. **NVBXLN / DOGRPH**: "A $70" is not a constant. Case 5 (LOGOPR 3) returns **A $73**, which fits "A = the last byte written to R#46 (LINE $70 OR LOGOPR)". The page's flat "A $70, F $20" is refuted by its own table row. Separate the rules with LOGOPR 1 / 2 / 8.
9. **NVBXFL**: the MSX2 residue (R#44 **$80**, R#45 $04 in every case, while DY runs 15 → 9 in the reversed case) does not fit a single LMMV in colour $05: LMMV leaves CLR = the colour, and DIY would be 1. Rivals: a sequence of commands, a final POINT/LMCM-type command that loads CLR, or some other last write. Only the FS-A1WSX residue ($05, ARG $0C reversed) reads as one LMMV with the direction bits. Separate them with the [SN] port log (BF-04 / BF-10).
10. **SCANR**: "DE 0 returns at once" and "DE $FFFF likewise, DE coming back 0" fit several rules: "DE ≤ 0 as signed", "DE incremented, then tested for 0", or "DE counted down past 0 to exhaustion". Separate them with DE $7FFF, $8000 and 2.

## 3. Citations that do not match the tables

1. **DOGRPH**: the title "(assumed)", the Summary's "Every part of that is assumed", and the interface's [A] on the two points and the colour contradict the Measured paragraph, which settles the points, the colour cell and that the entry exists. The Measured paragraph's "the handbook's $F3F3" cites a handbook entry that, per the same page, does not exist for $0085. It is NVBXLN's.
2. **NVBXLN** (Interface: "which cell the call reads is [A] (case BL-01)") and **NVBXFL** ("the cell read is [A]") still mark the colour cell assumed. The Measured paragraph of each page settles it as $F3F2.
3. **NVBXLN**: "A $70, F $20" is true for cases 0 and 1 only. Case 5 gives A $73 (see 2.8).
4. **NVBXLN** Differences: "C-BIOS ... draw a different figure" over-generalises. In the forward order (case 0) the subject's window is identical to the reference, and only GXPOS/GYPOS and R#36-R#40 differ. The figure differs only in the reversed order (case 1) and under XOR (case 5).
5. **NVBXFL**: "R#44 / R#45 ($05 / $00 ...)" elides the FS-A1WSX reversed case's R#45 **$0C** (DIX = DIY = 1), which is the one measured fact bearing on "corners sorted vs direction bits". The Differences paragraph omits the R#36 / R#38 divergence in the reversed case (C1EF / C1F1).
6. **SCANL**: "It paints LEFTWARDS" states as [M] something the record cannot show (see 2.5).
7. **GRPPRT**: "at Y 207 GRPACY stays (no wrap, no scroll)" is cited as a measured bottom-edge rule. Case 5 did not reach the bottom-edge path (see 1.1).

## 4. Gaps in the open lists

1. Stale `—` rows that the Measured paragraphs already answer, at least in SCREEN 8: BL-01, BF-01, DG-00, DG-01, DG-02 (GXPOS/GRPACX part), DG-06, SR-00, SR-01 (partly), SL-00, SL-01 (partly). BL-10, BF-10 and DG-09's command residue was also captured (R#36-R#45) and is not recorded against them.
2. **NVBXFL** BF-02 is half-answered already. SCREEN 5 case 6 paints pixel 20 and leaves pixel 21 (byte $50). HMMV cannot write half a byte, so a pure HMMV is already excluded at the right edge. Only the odd left edge is open, and the row does not say so.
3. **NVBXFL** BF-04 is partly answered by the residue (FS-A1WSX ARG $0C, DX 20 / DY 9 after the reversed case: the corners were not sorted). The row is still `—` and the MSX2 discrepancy in 2.9 has no row.
4. **NVBXLN** BL-03 needs a constraint it does not state: the XOR case must not have preset XOR ATRBYT equal to the $F3F3 byte (see 2.1).
5. **GRPPRT** GP-05 cannot separate "LOGOPR ignored" from "TIMP honoured" with BAKCLR non-zero. Add an XOR row, or BAKCLR 0 under TIMP (see 2.2).
6. **GRPPRT** has no row for the bottom edge reached by a line feed (CR or right-edge wrap at Y ≥ 204). GP-07 does not say the line feed must be triggered.
7. **GRPPRT** has no row for where the glyph goes at the wrap (X 248-255 and the next row's X 0-7), and none for an odd X in SCREEN 5.
8. **GRPPRT** has no row reading ATRBYT after the call to separate FORCLR-direct from ATRBYT := FORCLR. GP-02 mentions "ATRBYT after" but under the same FORCLR ≠ ATRBYT setup it needs the cell actually captured.
9. **SCANR / SCANL** have no row for a non-border, non-zero pixel inside the run ("stop at BRDATR" vs "stop at ≠ start colour").
10. **SCANL** has no row for the paint direction (SL-14 asks for residue but does not name the direction as the question). SL-05's "B and DE unused" is already contradicted for DE as an output (DE 31 out), and the row does not say so.
11. **SCANR** has no row for DE $7FFF / $8000 (signed vs incremented skip count, 2.10). The SR-02 B-gate row should use a DE that does not return at once.
12. **DOGRPH** has no row placing both line ends well inside the read-back window (overshoot, 1.8). There is also no row for A out as a function of LOGOPR (2.8), and the same is missing on NVBXLN (BL-12 covers registers only generically).
