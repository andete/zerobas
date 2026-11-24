# Goldfish review (test-writer role), 2026-11-23: INITXT INIT32 INIGRP INIMLT SETTXT SETT32 SETGRP SETMLT

Decoded by hand, from `scratchpad/AE_xmode_msx2.out`, using the record layout in `probes/bios/spec/xmode.asm`
(96 B per record, +0 A, +1 F, +2 IFF, +3 case, +4 R#0-R#27, +32 $F3DF-$F3E6, +40 $FFE7-$FFFC, +62 SCRMOD, +63 OLDSCR,
+64 LINLEN, +65 CRTCNT, +66 NAMBAS..): the reference ("CAP ref") records 11-18 (INITXT..SETMLT) on all three machines
(NMS 8250, HB-F900, FS-A1WSX), and the C-BIOS ("CAP ours") records 11-18 of the NMS 8250 run, checking the other two
only spot-wise. I also used records 0 and 7-10 (CHGMOD 0, 7, 8, 9, 255) for the state that each case was entered with.
Not decoded: anything the `DIFF` lists say about records 11-18, because each DIFF list is truncated after about 80
bytes (records 0-4 only). Not read: `scratchpad/xmode_decode.py` (named but not linked) and
[CHGMOD](../docs/msx2/sub/CHGMOD.md), which is a page and not evidence, although every INI page's [M] paragraph points
to its table. Process note: I read the first 3 KB of the run file once through a shell `head` before switching to the
Read tool. That was the only command, and it only read the file.

## 1. Rules not pinned by any measured case

1. **INITXT, INIT32, INIGRP, INIMLT: the [M] values live on another page.** Each [M] paragraph says "the same VDP
   registers and table cells as CHGMOD with A n -- see its table". For a test-writer limited to these pages, the
   registers and cells these four calls must produce are not given at all. Fix: put the decoded R#0-R#7 / R#10 /
   R#11, the copies, SCRMOD / OLDSCR / LINLEN and NAMBAS..ATRBAS per record on each page. From the records they are:
   INITXT `20 75 00 A5 01 A5 25 F4`; INIT32 `20 65 06 80 00 36 07 04`; INIGRP `22 65 06 FF 03 36 07 04`;
   INIMLT `20 6D 02 A5 00 36 07 04`.
2. **INITXT, INIT32, INIGRP, INIMLT: the work-area writes cannot be attributed to the sub-ROM call.** The probe calls
   main-ROM CHGMOD 0 before every case, so SCRMOD 0, OLDSCR 0, LINLEN, the cursor and the cleared screen were already
   set before INITXT ran. INITXT's "SCRMOD / OLDSCR := 0, LINLEN := LINL40" therefore has no witness. To pin it, enter
   INITXT from SCREEN 5 (the xmode "SCREEN 5 first" flag) with LINLEN ≠ LINL40 and SCRMOD / OLDSCR garbage.
3. **INIT32: SCRMOD = 1, OLDSCR = 1 and LINLEN = $1D are measured (record 12, all three machines), yet Behaviour still
   marks them [A].** "LINLEN := LINL32" is not pinned either: LINL32 is not recorded, and $1D (29) is its default. To
   pin it, record LINL32 and run with LINL32 = 33 (case I32-W).
4. **INITXT: R#3 / R#5 / R#6 in TEXT 1 have no rule and no open case.** The record gives R#3 $A5, R#5 $A5, R#6 $25,
   which are the probe's $A5 copies. "Written from RG3SAV / RG5SAV / RG6SAV" and "VDP left as it was" both fit, and so
   might a cell. To separate them, use copies ≠ the VDP values on entry (for example copies $5A with VDP $A5).
5. **INITXT, INIT32, INIGRP, INIMLT: F $40 / A $00 is given as a single measurement, with no rule.** Only one input
   was used. It is unknown whether A and F are constant or the residue of the last operation (for example a VDP
   write). To pin it, enter with different A / F (for example A $FF, F $FF) and from a different previous mode.
6. **SETTXT, SETT32, SETGRP, SETMLT: the result "A $00, F $44" has no rule** (same problem as item 5). It is one input
   (A 0, BC $1357, DE $9BDF, HL $2468). Walk A and F on entry.
7. **INIT32 and INIGRP: "R#7 := BDRCLR" is not pinned.** The record gives R#7 = $04 (RG7SAV $04), but BAKCLR and
   BDRCLR are probably both 4, and neither is recorded. Cases I32-COL and IG-COL would pin it, but only if BAKCLR,
   BDRCLR and FORCLR are recorded as well.

## 2. Rules the measured cases could also explain with a different rule

1. **SETTXT, SETT32, SETGRP, SETMLT: "R#1's display bit is left clear (the $A5 copy's bits, not a rebuilt value)".**
   $A5 has bit 6 clear, so "bit 6 kept from RG1SAV" and "bit 6 forced to 0 (blank)" give the same R#1. The case that
   separates them is RG1SAV = $E5 (bit 6 set). Case ST-R01 asks for this on SETTXT only; S32-R01, SG-R01 and SM-R01
   say only "kept bits".
2. **SETTXT: "SCRMOD is NOT changed (stays 0)".** The call was entered from SCREEN 0, so "SCRMOD untouched" and
   "SCRMOD := 0" give the same 0. The same holds for NAMBAS $0000 / CGPBAS $0800, which are SCREEN 0's own values.
   ST-ONLY (SCRMOD 5) separates them. For SETT32, SETGRP and SETMLT the same sentence is a real witness (1, 2 and 3
   would show).
3. **SETTXT, SETT32, SETGRP, SETMLT: R#7 was written from RG7SAV, and the pages do not say so.** On entry the VDP had
   R#7 = $F4, set by CHGMOD 0 and visible in the C-BIOS records. RG7SAV was then poked to $A5, and after the call the
   reference VDP has R#7 = $A5 on all four calls. So the rule is "R#7 := RG7SAV", not "kept" and not
   FORCLR / BAKCLR / BDRCLR. This already answers the "written here or not" half of ST-R7 and S32-R7. The remaining
   alternative, "R#7 recomputed from colours", is excluded only if the colours were not $A5-equivalent; FORCLR,
   BAKCLR and BDRCLR are not recorded.
4. **SETxxx: R#0-R#7 "from RGnSAV" versus "from the VDP's current mode".** The probe overwrote all eight copies with
   $A5 but left the VDP in SCREEN 0. For example, SETMLT's "M1 cleared" is not exercised: the copy's M1 was already
   0 ($A5), although the VDP had M1 = 1. SM-R01's "R#1 M1 set (from TEXT)" must set **RG1SAV** bit 4, not just enter
   from TEXT.
5. **VDP read-back versus copy disagree in the masked bits.** Examples: R#0 = $20 against RG0SAV = $A1 (all INI and
   SET records); SETTXT R#1 = $35 against RG1SAV = $B5; R#6 = $25 against $A5. "The ROM writes a masked value" and
   "the debugger reads non-existent bits as 0" both fit. The pages quote the VDP values as the result without saying
   which bits the acceptance test may compare. Separate the two by a raw VDP write of $FF with read-back, outside the
   ROM call.
6. **INITXT: "LINLEN := LINL40".** The record shows LINLEN $25 (NMS 8250) and $27 (HB-F900, FS-A1WSX), but LINL40 is
   not recorded. Besides item 1.2, "LINLEN := LINL40" and "LINLEN := machine default 37 / 39" also coincide. Record
   LINL40 (IT-W).
7. **INITXT and SETTXT: TEXT 1 versus "TEXT 2 when LINL40 > 40".** The only inputs are LINL40 37 or 39, so the
   threshold rules "> 40", "≥ 41" and "> 32" all give TEXT 1 here. IT-W and ST-W are the right cases; the point is
   only that no measured row touches the TEXT 2 claim.
8. **INIT32: R#11 was written ("kept" is excluded), but its value rule is open.** INITXT left R#11 = $01 (RG11SAV
   $01, a stale value from SCREEN 7 / 8). After INIT32 it is $00 on all three machines. Both "R#11 := 0" and
   "R#11 := T32ATR >> 15" give 0, and T32ATR at $C000+ (I32-BASE) separates them. I32-BASE still lists "kept" as an
   outcome, although record 12 has already excluded it.

## 3. Citations that do not match the tables

1. **SETMLT: "R#1 $35 / $25" is wrong.** Record 18 gives R#1 = **$2D** (RG1SAV $AD, M2 set) on all three machines.
   $35 is SETTXT's value and $25 is SETT32's and SETGRP's. The sentence was copied unchanged across all four SET
   pages.
2. **SETT32 and SETGRP: "R#0 / R#2 / R#4 as CHGMOD's mode" understates what was measured.** The records show R#3,
   R#5 and R#6 computed from the cells and written to both VDP and copies: SETT32 `06 80 00 36 07`; SETGRP
   `06 FF 03 36 07`, the same as INIT32 / INIGRP. The page reads as if these registers were open.
3. **SETTXT, SETT32, SETGRP, SETMLT: "the copies are not normalised" contradicts the copies in the records.** RG0SAV
   became $A1 / $A3, RG1SAV became $B5 / $A5 / $AD, RG2SAV became $00 / $06 / $02, and for SETT32 / SETGRP RG3SAV-RG6SAV
   were rewritten. Only bit 7 and display-bit residues of $A5 survive. State which bits are kept.
4. **SETT32, SETGRP, SETMLT: "C-BIOS ... write R#3 / R#5 / R#6 / R#7 their own way (R#7 := $F4, the border)" does not
   match the "ours" records.** C-BIOS SETT32 and SETGRP have the same R#3-R#6 as the reference, and differ only in
   R#7. C-BIOS SETMLT differs in R#3 ($00 against $A5) and R#7. Only SETTXT differs in all four (R#3 $00, R#5 $36,
   R#6 $07, R#7 $F4). C-BIOS's $F4 is not "the border": it is the R#7 that CHGMOD 0 left (FORCLR / BAKCLR), and
   RG7SAV stays $A5. So C-BIOS leaves R#7 untouched; it does not write it.
5. **INITXT, INIT32, INIGRP, INIMLT: "C-BIOS ... set the same, but return with interrupts ON" omits other
   differences.** C-BIOS also returns other A / F (for example INITXT A $75, F $A0 against $00 / $40). On the HB-F900
   and FS-A1WSX, LINLEN after INITXT / INIGRP / INIMLT is $25 against $27. R#16 and R#21 / R#22 and their copies also
   differ: $00 against $0F / $3B / $05.
6. **INITXT: "the same VDP registers and table cells as CHGMOD with A 0" does not match record 0 (CHGMOD 0).** In
   INITXT's record, R#11 / RG11SAV = $01 (record 0: $00), and PATBAS / ATRBAS = $F000 / $FA00 (record 0: $3800 /
   $1B00). Both are stale from SCREEN 8 (records 7-10). The measured rule is that INITXT writes neither R#11 nor
   PATBAS / ATRBAS. INIT32, INIGRP and INIMLT do rewrite PATBAS / ATRBAS ($3800 / $1B00).
7. **All eight pages: "the same on all three references" is not literally true.** R#9 is $02 on the NMS 8250 against
   $00 on the others. LINLEN after INITXT / INIGRP / INIMLT / SET* is $25 against $27. R#17 and $FFF7-$FFFC differ
   (FS-A1WSX). Name the per-machine fields (PAL bit, LINL40 default).
8. **INIGRP: "OLDSCR: [A]" while record 13 measures OLDSCR = 0 after INIGRP** on all three machines. This excludes
   "OLDSCR := 2", but entry from SCREEN 0 cannot separate "kept" from ":= 0". IG-PREV covers that.
9. **SETT32, SETGRP, SETMLT: "nothing else [A]" is partly measured and not cited.** Records 16-18 show SCRMOD, OLDSCR,
   LINLEN, CRTCNT and NAMBAS / CGPBAS / PATBAS / ATRBAS all unchanged from SCREEN 0. If SETT32 wrote NAMBAS it would
   be $1800, and if SETMLT did it would be $0800. ST-BASES and S32-ONLY still list "written here vs by INITXT" as open
   for the bases.
10. **All eight pages: the decoder is cited as "decoded by `scratchpad/xmode_decode.py`" without a link**, and the
    run file's DIFF lists stop at record 4. No reader-visible decoded file backs any record-11-to-18 claim; it rests
    on the raw hex.

## 4. Gaps in the open lists

1. **INITXT: no case for R#3 / R#5 / R#6 in TEXT 1** (item 1.4), for R#11 kept (item 3.6), or for PATBAS / ATRBAS
   being left stale. IT-BASE covers only R#2 / R#4 / R#3 / R#10 under TEXT 2.
2. **INITXT, INIT32, INIGRP, INIMLT: no case enters from a mode other than SCREEN 0 *without* the preceding main
   CHGMOD 0** (item 1.2). The -PREV cases name previous modes, but nothing says the main CHGMOD before the call must be
   skipped. With that CHGMOD still in place they measure CHGMOD again.
3. **SETTXT, SETT32, SETGRP, SETMLT: the IE row asks "forced on, forced off, or kept", but the DI entry already
   measured ON.** So "forced off" and "kept" are excluded, and the EI half cannot add anything. Either drop the row or
   say what it is still for.
4. **SETxxx: no case where the copies and the VDP disagree in the direction that matters** (copy mode bits ≠ VDP mode
   bits, for example RG1SAV M1 = 1 for SETMLT, RG0SAV M4 = 1 for SETGRP). SG-G3 says "entered with R#0 M4 set (from
   SCREEN 4)", but the probe overwrites the copies after the CHGMOD (item 2.4), so it must say RG0SAV.
5. **INIT32, INIGRP, INIMLT: R#7 / colour cases do not list recording FORCLR / BAKCLR / BDRCLR themselves**, and the
   xmode record does not capture them. Without that, I32-COL, IG-COL and IT-COL cannot be decoded.
6. **INITXT and SETTXT: the -W cases do not list recording LINL40 / LINL32.** The xmode record lacks both, so "LINLEN
   as is" cannot be checked from a record (items 1.3 and 2.6).
7. **All eight pages: no case for A / F on return** (items 1.5 and 1.6).
8. **All eight pages: no row about which VDP register bits the debugger reads back** (item 2.5). Every R#0 / R#1 /
   R#6 "kept bits" case depends on it.
