# Goldfish review (test-writer role), 2026-11-23: docs/msx2/concepts/graphics-cursor.md docs/msx2/sub/MAPXYC.md docs/msx2/sub/READC.md docs/msx2/sub/SETATR.md docs/msx2/sub/SETC.md docs/msx2/sub/SCALXY.md

**Evidence decoded:** `probes/bios/spec/xsubgc.asm` (read in full) and `scratchpad/AE_xsubgc_msx2.out`: I hand-decoded
all 21 point records and all 15 SCALXY records of the **reference** CAP string (NMS 8250, line 5), and the
C-BIOS ("ours") string at the records the DIFF lists name plus the SCREEN 2 records. I took the HB-F900 and FS-A1WSX
reference strings as equal to the NMS 8250's on the basis of identical DIFF lists and a visual comparison, not a
byte-by-byte decode. Base: the dump starts at CAP = $C001 (the DIFF addresses only align that way, although the
probe says `@cap C000`). **Not read:** `scratchpad/xsubgc_decode.py` (named in backticks, not linked).

## 1. Rules not pinned by any measured case

1. **READC — "returns the pixel's colour" is not separated from "returns ATRBYT (masked to the field width)"**
   (READC.md, Measured). In every record ATRBYT = $0B and SETC has just written $0B, so both rules give $0B / $03.
   The run file itself shows the rival is real: C-BIOS's SCREEN 2 READC returned $0B while the probed byte held $F0.
   Pin it with READC on a planted pixel colour different from ATRBYT, with no SETC before it (RD-01 does this only if
   it states ATRBYT ≠ $A / $5).
2. **SETATR's SCREEN 6 "$0F" is not shown to be a stored value** (SETATR.md, Measured). The carry was never captured,
   and ATRBYT held 15 or FORCLR before the call, so "rejected, carry set, ATRBYT kept" (CHGMOD or FORCLR having left
   15) fits as well as "stored $0F". Pin it with ATRBYT planted to $05 and FORCLR ≠ 15 before SETATR $0B in SCREEN 6,
   recording ATRBYT and the carry right after the call (SA-01 must state the planted ATRBYT).
3. **SCALXY's X bound of 511 in SCREEN 6 / 7 was not measured** (SCALXY.md, Measured). The only over-255 X was 300,
   passed through unclipped, so any bound ≥ 300 (511, 1023, none) fits. Pin it with X 511 / 512 / $7FFF in SCREEN 6 and 7
   (SX-01 covers this; the Measured paragraph claims more than it measured).
4. **SCALXY's F bit 7 has no rule** (SCALXY.md, Measured). It reads $00 for (300, 250) in SCREEN 5 / 8, $80 for the
   same input in SCREEN 6 / 7 (only Y clipped), and $80 for (-5, -5). The page lists "F $80 / $00" without saying
   which case gives which. Pin it with each clip combination (X high, X low, Y high, Y low, alone and together) in one
   mode, F recorded. A was never captured, so the "A = $80 / 0" interface line is entirely unmeasured.
5. **SETC in SCREEN 2 at a non-zero CLOC was never checked in VRAM** (SETC.md, Measured). The probe reads back the
   SCREEN 2-layout address ($020C, $17FF), but the reference wrote at the multicolour CLOC ($022C, $07FF), so records 2
   and 3 read $00. Only (0, 0) and (1, 0), where both layouts coincide at $0000, back "writes ATRBYT into the nibble".
   Pin it by reading VRAM at CLOC for (10, 20) and (255, 191).
6. **The state behind every measured rule is unrecorded:** LOGOPR, ACPAGE, R#9 LN and the command-engine state are
   whatever CHGMOD left (all pages). "The pixel takes ATRBYT" on a zeroed byte (SETC.md) holds equally under LOGOPR
   IMP, OR or EOR, and "Y clips to 211" (SCALXY.md) holds at an unknown LN. Record those four cells in the capture, or
   restate the [M] lines as "at CHGMOD's defaults".
7. **MAPXYC's F ($42 in SCREEN 5, $02 in 6-8, $44 / $00 in SCREEN 2) is taken from an uncontrolled entry F**
   (MAPXYC.md, Measured). The entry F came from the preceding SETATR's return, not garbage, so "F computed by MAPXYC"
   and "F passed through" are not separated. Pin it with MX-11 (entry F $00 and $FF).
8. **The SCREEN 2 multicolour mapping does not pin its base or its wrap** (MAPXYC.md, Measured). GRPCGP and MLTCGP
   are both 0 after CHGMOD, so the base cell added is unknown. The out-of-range (255, 191) → $07FF fits "whole address
   AND $07FF", "X mod 64 and (Y/8) AND 7", and other wraps. Pin them with GRPCGP ≠ MLTCGP planted and with X 64 / Y 48
   separately.

## 2. Measured cases that a different rule could also explain

1. **SETATR SCREEN 6** (SETATR.md): "stores $0F, a transform of A ($0B OR $0C, or clamp to 15)" vs "rejects $0B and
   keeps the prior 15". The case that separates them is A 4 with ATRBYT pre-planted to 5: the first rule gives a
   transformed value, the second gives 5 with the carry set. This is the same case as 1.2. SETC's "(ATRBYT $0F there,
   all ones)" (SETC.md) inherits the ambiguity.
2. **READC** (READC.md): "reads the pixel" vs "returns ATRBYT AND the field mask" vs "returns the colour of the last
   SETC (a cached copy)". All three give $0B / $03 on every record. The separating case is a planted pixel ≠ ATRBYT,
   read with no SETC first.
3. **SCALXY's carry** (SCALXY.md): "carry set iff nothing was clipped" vs "carry clear iff Y was clipped" (or "iff
   any value was negative or Y was clipped"). Every clipped record has Y clipped: (300, 250) both, SCREEN 6 / 7 Y only,
   and (-5, -5) both. No record clips X alone. The separating case is X 600, Y 5 in SCREEN 5 (SX-04 puts it in SCREEN 6
   only).
4. **SCALXY SCREEN 2** (SCALXY.md): "divide by 4, then clip to 63 x 47" vs "clip to 255 x 191, then divide by 4" give
   the same coordinates for every input, so the page should not name an order. Only the carry can separate them, for
   example X 254 (unclipped before the divide, and 63 after). Separately, "SCREEN 2 handled as SCREEN 3" vs "every
   non-bitmap mode is multicolour" is separated only by SCREEN 3 / 4 (SX-05, MX-09).
5. **MAPXYC model C** (MAPXYC.md): "CLOC := BC verbatim, CMASK := E" vs "CLOC := X clipped or masked to the mode's
   width". Both fit, because every X was in range for its mode. The separating case is X 300 in SCREEN 5 (MX-08).
   "CMASK := E, D dropped" vs "a hidden 16-bit Y kept elsewhere" is also open: separate them with Y 256+ and the RAM
   diff (MX-08 / MX-13).
6. **SETC SCREEN 5 / 7 / 8** (SETC.md): "replace the field" vs "OR into the field" vs "apply LOGOPR (at its unknown
   value)". The byte was always $00 beforehand. The separating cases are SC-01 (byte $A5) and SC-05.
7. **SC-03's "ORed in whole ($5A)"** (SETC.md): $45 OR $1A is $5F, not $5A. $5A is "clear the field, then OR the whole
   ATRBYT". The row has three rules, not two, and names the value of the wrong one.

## 3. Citations that do not match the tables

1. **graphics-cursor.md** still says "DRAFT 0 … nothing measured yet", "The bitmap cursor is unpublished" and lists
   models B / C / M as open. MAPXYC.md's [M] (identical on all three references) selects model C, and the concept page
   does not record that.
2. **MAPXYC.md** Measured: "in SCREEN 5-8 … (511, 211) $01FF / $D3". X 511 was measured only in SCREEN 6 / 7. SCREEN 5 /
   8 used (255, 211) → $00FF / $D3.
3. **SCALXY.md** Measured: "SCREEN 6 / 7 to 511 x 211". No record clips X in SCREEN 6 / 7 (300 passed through
   unclipped); see 1.3.
4. **SCALXY.md** Measured / Differences: the SCREEN 2 F values ($00 clipped, $01 unclipped, $44 for (-5, -5)) are not
   cited. The Differences paragraph also omits that C-BIOS's SCREEN 2 F differs ($80 / $81 vs the reference's $00 /
   $01 / $44); it only names bit 7 for SCREEN 5-8.
5. **xsubgc.asm header** (the evidence SETATR.md cites): record +10 is labelled "ATRBYT after SETATR", but the code
   reads it after MAPXYC, SETC and READC. SETATR.md's "$0F" is therefore "ATRBYT at the end of the point", not proven to
   be SETATR's output.
6. **xsubgc.asm** `@cap C000` vs a dump whose first byte is CAP ($C001), as the DIFF addresses show. The record
   layout is right only from the $C001 base.

## 4. Gaps in the open lists

1. **SETATR.md:** no row records the carry. No row plants ATRBYT and FORCLR away from 15 before the call, which is
   the case that decides 1.2 / 2.1. SA-01 to SA-03 should state the planted prior ATRBYT.
2. **READC.md:** no row with pixel ≠ ATRBYT and no preceding SETC (2.2). RD-01, RD-02 and RD-04 do not state ATRBYT.
3. **MAPXYC.md:** no row for the SCREEN 2 multicolour behaviour that was found: the base cell (GRPCGP vs MLTCGP
   planted apart) and the wrap past X 63 / Y 47. MX-09 tests (100, 50) only.
4. **Stale "—" cells:** MX-00, MX-01 and MX-04 (both modes) are already answered by the measured records. So are MX-06's
   "B takes part" (X 511 → CLOC $01FF in SCREEN 6 / 7), SC-04's masking question (ATRBYT $0F gave $30 at X 1 and $03 at
   X 3: masked, not spilled), and the "callable entry" rows SC-00, RD-00, SA-00 and SX-00. The tables still show "—"
   on every machine, and "Tests that cover it: None yet".
5. **SCALXY.md:** SX-04 tests the X-only clip in SCREEN 6 only. Add it in SCREEN 5 / 8, where the X bound is 255, so
   the carry and F bit 7 rules are seen at both bounds. No row captures A.
6. **SETC.md:** no row reads VRAM at the multicolour CLOC in SCREEN 2 for points away from $0000 (1.5). SC-13 does not
   name it.
7. **All pages:** no row records LOGOPR, ACPAGE, LN and the command-engine state alongside the measured baseline
   (1.6), so the [M] lines cannot be reproduced as a test precondition.
