# Goldfish review (test-writer role), 2026-11-23: docs/msx2/sub/RIGHTC.md, LEFTC.md, UPC.md, DOWNC.md, TUPC.md, TDOWNC.md, TRIGHT.md, TLEFTC.md

**Decoded:** the NMS 8250 reference `CAP ref` line of `scratchpad/AE_xsubmv_msx2.out`, all 128 records, by hand against the
12-byte layout in `probes/bios/spec/xsubmv.asm` (SCRMOD, entry, CLOC/CMASK before, CLOC/CMASK after, A, F, X lo, Y lo),
and the `CAP ours` bytes at every DIFF address listed for that machine. **Not fully decoded:** the HB-F900 and FS-A1WSX
`CAP ref` lines. I compared them with the NMS line at selected records only (S2 TRIGHT (255,20), S5/S6 TLEFTC stop and
(511,20), the final record) and found them equal there. I also saw that the three DIFF lists are identical. I did not
compare them byte by byte. `scratchpad/xsubmv_decode.py` was not read (not a cited evidence file).

## 1. Rules NOT pinned by any measured case

1. **TRIGHT, TLEFTC, TDOWNC, TUPC: the A returned at a stop.** The pages say A = 0 [A], but the run already recorded A,
   and it is not 0 in most stops. TRIGHT gives A = $F8, F = $69 in S2/5/6/8. TLEFTC gives A = $00 in S2 and A = $FF,
   F = $AD in S5/6/8. TDOWNC gives A = $00 in S2 and A = $D3 (= Y), F = $41 in S5/6. TUPC gives A = $00, F = $45. No
   page states the measured stop A, so the test has no rule for it. Put these bytes on the pages and turn them into a rule.
2. **All eight pages: A and F after a move that does not stop.** Every record has these bytes, but no page reports them.
   For example, RIGHTC/LEFTC leave A = the new CMASK with AND-like flags ($0F/$1C, $F0/$B4), and UPC/DOWNC leave A = a
   CLOC AND 7 value. The xx-90 rows ask the question as if nothing had been measured. Put the A/F columns into the
   Measured tables. Then xx-90 only needs to cover the other registers and the interrupt state.
3. **TDOWNC (SCREEN 8, (10,211)): the carry is unmeasured.** It is record 128. Its F byte is at $C601, beyond the
   `@caplen 0600` capture: the dumped line ends `...08b10a00d30a00d3d3`, at A. The page's carry of 0 is not a
   measurement. Re-run with `@caplen` ≥ $0603.
4. **UPC, TUPC, DOWNC, TDOWNC: the R#9 line count and ACPAGE during the run.** Neither is recorded or stated, but both
   decide what "the last line" (211) and "Y 0" mean. Record R#9 and ACPAGE in the capture header.
5. **UPC: the AND-7 = 0 branch in SCREEN 5-8.** The only bitmap case that reaches it has CLOC = 0, at (0,0). So
   "CLOC AND 7 = 0 → −$F9" is pinned only at CLOC 0. Pin it with S5 MAPXYC (8, 20): the stated rule gives $FF0F.
6. **TUPC (SCREEN 2): the stop rule.** The page says only "the multicolour row step". The only stop is at CLOC $0000.
   Pin it with S2 MAPXYC (8, 0) (CLOC $0008).
7. **TDOWNC (SCREEN 2): the stop rule.** The only stop is (10,191) → CLOC $072F. The condition (a CLOC test, or a Y
   copy at 191) is not stated, and no non-stop case nearby measures it.
8. **All eight pages: "VDP registers and VRAM: none touched" and "registers kept".** The probe records neither (no BC,
   DE, HL, IX, IY or VRAM capture, and the probe re-issues `di` after each call). These stay [A] until the xx-90 and
   xx-94 cases run.

## 2. Rules the measured cases could ALSO explain with a different rule

1. **TDOWNC (SCREEN 5/6): stop at Y 211 vs Y ≥ 191.** The bitmap cases are Y 0, 20 and 211 only. A stop at 191, or at
   anything in 21..211, explains them equally. The page states "(211)" as [M]. TD-01 (190/191/210/211) separates them.
2. **RIGHTC, LEFTC, TRIGHT: the key is CMASK bit 7 vs bit 6 (or CMASK ≥ $80 vs ≥ $40).** Every measured CMASK ($F0,
   $0F, $14, $00, $D3) has bits 7 and 6 equal. CMASK $80 or $40 separates them: RC-06 ($80) and LC-04 ($8F, $4F) do.
   RC-05 ($F1, $3C, $00) does not.
3. **TLEFTC: stop on X = 0 vs on Y = 0 vs on CLOC = CMASK = 0.** Every stop is at (0,0), in every mode. TL-01 (0,3)
   separates them.
4. **TUPC: stop on Y = 0 vs on X = 0 or CLOC = 0.** Every stop is at (0,0). TU-01 (10,0) separates them.
5. **TRIGHT: an edge of X = 255 (S5/8) and X = 511 (S6) vs "the low byte of CLOC is $FF".** Both rules explain S5
   $00FF and S6 $01FF. Separate them with S6 X 255 ($00FF), which TR-02 includes.
6. **TRIGHT: the edge as equality (X = edge) vs "the step would pass the edge".** The step is +8, so these differ. The
   separating case is S5 (254, 3) or (250, 20), which TR-01 has.
7. **TRIGHT / TLEFTC (SCREEN 2): an X-coordinate test (255 / 0) vs a block/CLOC test.** S2 MAPXYC groups 4 pixels per
   cell, so X 252..255 give the same CLOC/CMASK. Separate them with S2 (252, 20) and (3, 20), or with a planted
   CLOC/CMASK. TR-03 and TL-03 only use 255 and 0.
8. **UPC/DOWNC: "a ±1 step within an 8-byte cell" (S2 arithmetic in every mode) vs "the vertical step reads X in
   bitmap modes".** The measured rows cannot tell these apart, but no row needs to. Note only that UC-02 and DC-02
   were designed for model B and do not separate anything under the measured CLOC = X.

## 3. Citations that do not match the tables

1. **All eight pages: the SCREEN 6 "(255, 20)" rows are really (511, 20).** The probe's case table has `dw 511, 20`
   for S6, and CLOC $01FF is X 511. The decoder records only X's low byte.
2. **TDOWNC: the last table row "8 | (0, 0) | $000A / $D3 | $000A / $D3 | 0" is wrong.** The case is (10, 211). The
   X, Y and carry columns were not captured (item 1.3), so the row comes from a truncated record.
3. **TUPC, TDOWNC, TLEFTC: the Interface says "where it does not stop, as UPC / DOWNC / LEFTC", but the Measured
   tables contradict it.** In S5-8, TUPC and TDOWNC change CMASK (Y ± 1) while UPC and DOWNC change CLOC (X ± 1). TLEFTC
   gives X − 1 while LEFTC does the multicolour step (CMASK := $F0, or CLOC − 8).
4. **TRIGHT, TLEFTC, TUPC, TDOWNC: "A = 0 at the stop" [A] is contradicted by the run file** for TRIGHT (A $F8),
   TLEFTC S5-8 ($FF) and TDOWNC S5/6 ($D3). See 1.1.
5. **All eight pages: the model B / model C Interface bullets are falsified by the Measured block on the same page.**
   MAPXYC leaves CLOC = X and CMASK = Y, and RIGHTC/LEFTC do neither model's step. The pages still state these rules
   as the specification.
6. **DOWNC: the Measured prose ends "In SCREEN 5-8 ... that is X + 1".** But its own table has $00FF → $01F8 and
   $01FF → $02F8 (X + $F9 at X AND 7 = 7). UPC has the same issue: $0000 → $FF07.
7. **TDOWNC Differences: "1 of the 16 cases"** should be "1 of the 15 captured". The SCREEN 8 (10,211) F byte was not
   compared, on either side.

## 4. Gaps in the open lists

1. **TDOWNC: no case re-measures SCREEN 8 (10,211).** It needs a capture length that covers record 128 (see 1.3).
2. **UPC, DOWNC, TUPC, TDOWNC, LEFTC: several open cases are still written for model B** (UC-02 CLOC $380, DC-02
   $387, TU-02/TU-04 CLOC $8005, TD-03/TD-06 $6985, LC-03 "previous line"). Under the measured CLOC = X, CMASK = Y
   they test nothing. Rewrite each one as an (X, Y) or a planted (CLOC = X, CMASK = Y) pair.
3. **UPC: no case for the AND-7 = 0 branch with CLOC ≠ 0 in a bitmap mode** (S5 (8, 20)); see 1.5. **LEFTC:** no
   case where CLOC − 8 wraps from X < 8 with CMASK bit 7 set (S5 (0, 200) → $FFF8?).
4. **TRIGHT, TLEFTC, TDOWNC: no case for the mode-dependence of the stop's A** ($F8 constant; $00 vs $FF; $00 vs
   Y). The xx-90 rows ask only "A and F left" with the MSX1 expectation.
5. **TUPC, TDOWNC: no SCREEN 2 edge cases** (S2 (8, 0); S2 rows 188..191). TU-91 and TD-91 only cover "the MSX1 rules
   through the sub-ROM", and the measured S2 behaviour is not MSX1's (S2 is treated as multicolour).
6. **All eight pages: no case records R#9 (LN) and ACPAGE alongside the existing matrix.** Without them the measured
   211 / 0 edges cannot be tied to a state (see 1.4).
7. **TRIGHT, TLEFTC: there is no xx-95 case** for a main-ROM entry. That is consistent with no MSX1 counterpart, but
   the absence is not stated as deliberate.
