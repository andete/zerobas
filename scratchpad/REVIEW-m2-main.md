# Goldfish review (test-writer role), 2026-11-23: EXTROM / SUBROM / CHKSLZ / CHKNEW / EOL / RDRES / WRRES

Fresh reviewer; read the seven docs/msx2/main pages and the probe sources / run files they cite.

## 1. Rules not pinned
1. (MOST IMPORTANT) WRRES / RDRES round trip: the port write is never shown. In every WRRES case (5-11, 13) the port
   already read the expected value before the call (xrdres.asm: preset $80 reads $FF and A $00 expects $FF; preset $00
   reads $7F and A $80 / $FF / $A5 expect $7F). The page's "preset by hand to the opposite bit 7 first" is false
   because WRRES complements; a WRRES that only does CPL passes. Pin: preset the port to the OTHER reading before each
   call (OUT $00 -> reads $7F, then WRRES A = $00 must give $FF). RDRES's "WRRES v then RDRES gives v AND $80" rests on
   the same unshown write.
2. EXTROM: non-expanded EXBRSA slot never exercised (RAM slots $8B / $87 / $83 all expanded); on the FS-A1WSX page 0's
   secondary field was 0 before and during ((FFFF) cpl $00 / $00), so the secondary-register switch is shown only on
   the NMS 8250 / HB-F900. Pin: EXBRSA a plain primary RAM slot; on the FS-A1WSX a RAM sub-slot other than 3-0.
3. EOL graphic-mode clear length looks like a leftover LINLEN: case 15 (SCREEN 2, LINL32 32) returns A $28 (LINLEN 40)
   and clears 36 = 40 - 4. "count follows current LINLEN in any mode" vs "36 for H 5 in graphic modes". Separate: set
   another LINLEN (SCREEN 0 width 30) before switching to SCREEN 2 / 5 / 8.
4. EOL centring margin only with an even difference (40 - 30 -> 5): floor vs ceiling of (width - LINLEN) / 2. Separate:
   odd LINLEN (29 / 39). LINLEN below the width at 80 columns and in SCREEN 1 (LINL32 < 32) unmeasured.
5. EOL H beyond LINLEN + 1 unmeasured (only H 41); registers suggest "write, then H++ while H <= LINLEN" (one cell for
   every H 42-255). Pin: H 42, H 255.
6. CHKSLZ "EXBRSA not written" rests on the single preset $A5: "never writes" vs "writes only when 0 / invalid".
   Separate: preset $00, and the real sub-ROM slot, on the HB-F900. No acceptance criterion for the subject given that
   the references disagree.
7. RDRES / WRRES on MSX2: "$017A / $017D is not an entry" and "C-BIOS's MSX2 builds have no RDRES / WRRES" stated as
   facts; the probe ran on msx2p only; only the port was measured on the MSX2s.
8. CHKNEW: SCRMOD $FF cannot be measured with this probe ($FF = its "no override"); entry A only ever $A7.

## 2. Rival rules
1. EXTROM EXBRSA $00 cannot show a slot switch: port $A8 was already $F4 (page 0 = slot 0), so RSLREG $F4 fits
   "switched page 0 to slot 0" and "called IX with no switch". Separate: a target whose slot-0 view differs from the
   current page 0, or EXBRSA $00 vs the expanded slot 0 on the FS-A1WSX (EXPTBL[0] = $80).
2. RDRES "F bits 5 / 3 = bits of the new A" vs "= 0": new A only ever $00 / $80 (bits 6-0 of the port read 1). Also
   "A := NOT (IN $F4)" vs "bit 7 inverted, others 0"; no port separates them -- the test should pin only bit 7 and A
   bits 6-0 = 0. "The port is not written" also fits "written with the value just read".
3. EXTROM / SUBROM stack figures depend on which SP they count from: EXTROM's routine SP $E7E2, SP $E7FE before the
   CALL EXTROM, $E7FC after; 26 is from after the CALL pushed its return address (28 from the SP at the CALL), so
   "(the return address included)" is backwards. SUBROM's 28 counts from $E7FC (the SP at the JP). Counted the same
   way both are 28 -- the "28 vs 26" contrast is the counting convention.

## 3. Citations that do not match
1. EOL "H = LINLEN + 1 [M 0-20]" is false for case 7 (H 41 at width 40): HL $2A03, H 42 = LINLEN + 2.
2. EOL "the same 36 cells of row 2 [M 4, 5, 19, 20]" is wrong for case 19 (H 5 L 4: 36 cells at $007C, row 3;
   LINTTB[3] 0 -> $AF).
3. CHKNEW "Out-of-range SCRMOD [M 23-28, 32]" includes case 25, an ordinary SCREEN 1; the out-of-range cases are 23,
   24, 26-28, 32.
4. WRRES "the port preset by hand to the opposite bit 7 first" does not match the probe's table (1.1).
5. CHKSLZ Summary "runs for many seconds" holds only for the HB-F900; on the NMS 8250 JIFFY is unchanged.

## 4. Gaps in the open lists
1. WRRES / RDRES: the never-changed-port problem (1.1).
2. RDRES / WRRES: only a soft reset (JP $0000) measured; hardware reset and power cycle not listed -- the events a
   reset-status register exists to tell apart.
3. EOL: the LINTTB write for L 0 (index 255, $FCB1) never checked; odd margin, H > 41, graphic-mode LINLEN (1.3-1.5).
4. EXTROM: the non-expanded EXBRSA case and a separating EXBRSA $00 case (1.2, 2.1).
5. CHKSLZ: the EXBRSA-preset variation; what the subject's acceptance test should check given the disagreement.
6. CHKNEW: SCRMOD $FF and a varied entry A.
7. SUBROM: none beyond EXTROM's.
