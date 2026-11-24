# Goldfish review (test-writer role), 2026-11-23: BLTVD / BLTDV / BLTMD / BLTDM + concepts/block-transfer.md

Fresh reviewer; read only the pages, probes/bios/spec/xsubbltd.asm, scratchpad/AE_xsubbltd_msx2.out (header, diff)
and scratchpad/AE_xsubbltd_msx2_decoded.out (all three references, cases 0-21).

## 1. Rules no measured case pins
1. BLTVD / BLTDV "the VDP command has ended at return (S#2 CE clear)": the probe calls `cewait` (spins until CE = 0)
   before the snapshot (xsubbltd.asm:231-236) -- clear by construction. Pin: read S#2 before cewait / count the loop.
2. Concept "How every BLT case is recorded" says every case presets/records all VRAM, $F55E-$F572, LOGOPR, ACPAGE /
   DPPAGE, emulated time and a GSPSIZ control call "unless a row says otherwise"; the probe does none (6x16 VRAM window
   or 96 RAM bytes, $F562-$F570 only, no timing, no control call). Only whole-VRAM (BLTDV [A], VD-15, MD-13, DM-13) and
   LOGOPR (VD-06) are said skipped -- so "does not touch LOGOPR / ACPAGE / DPPAGE / $F55E-$F561 / $F571-$F572" reads as
   measured when it is not.
3. BLTVD / BLTDV "FNPTR's field := $8003": every case a 9-byte quoted name on drive A as the only open file; constant vs
   derived from name length / drive / FCB. Pin: other lengths, "A:X.PIC", a long name.
4. BLTVD / BLTDV position rules: SY / DY always 8; DX only 40 / 252, SX only 8 / 15; "reads DY / SY from the block"
   pinned only by R#38 / R#34 = 8 + NY. Pin: another Y, ideally page >= 256.
5. All four: register values on return (BC $0300/$0301, DE $F2C4/$0007, HL $0300, IX $56D3) stated "on all three", but
   no page says which are contract (only BLTDM calls IX / IY no contract); one entry state each. Vary entry registers
   and name, or declare not contract.
6. BLTDV: no error path measured, no "Out, on an error" section. Pin: unquoted name, full / write-protected disk
   (DV-05, DV-07).

## 2. Rules the cases could also explain differently
1. BLTVD R#44 rule CONTRADICTED by a cited case: XD 19 (DX 252, NX 8) R#44 = $43 on all three, the array's last dot is
   $47. Rival: the call stops sending a row's dots at the right edge (dropped by the call) vs R#44 = last dot with VDP
   clip / wrap -- bears on the page's open "wrapped or dropped". Separate: a window over x 0-3 of rows 9-12 + R#44,
   NY >= 2.
2. BLTVD LOGOP: XD 10 LOGOP 0 (IMP) over $00 (IMP / OR / EOR / T forms all give the plain dots); XD 11 LOGOP 3 (EOR)
   over $FF (EOR and NOT give the same). "LOGOP passed as given" vs off-by-one / wrong mapping / "always IMP".
   Separate: LOGOP 0 and 3 over a mixed preset ($0F / $55).
3. BLTDM "HL is READ": in XD 16 the $9F00 and $F562 blocks share SPTR ($9000) and +6..+14; differ only in EPTR and
   FNPTR. SPTR from $F562 + EPTR / FNPTR from HL passes. Redo XD 16 with blocks differing in every byte.
4. BLTVD "R#45 = ARG": ARG $00 in every case and the probe sets R#45 := 0 before each -- coincides with "never writes
   R#45". Separate: ARG != 0 with R#45 recorded (VD-08).
5. BLTVD R#32-35 / BLTDV R#36-39 "= the block's slots as masked": dummy always $5453 / $5857 -- copied vs constant;
   XD 11, 12, 19 R#32-35 also equal the previous case's leftover ($0003 / $0053), the probe never resets R#32-43; only
   XD 10, 14 separate written-by-this-call from left-over.
6. BLTDV "LOGOP not used": garbage LOGOP $5F, low nibble 15 = a no-op code. Rerun with LOGOP $03 at +14.
7. All records R#46 = $00 incl. XD 11 (LOGOP 3, an LMMC with EOR would leave $B3): either not captured or rewritten
   (STOP). State whether R#46 is in scope.
8. BLTMD EPTR < SPTR: XD 18 (EPTR = SPTR - 1) fits "unsigned compare -> nothing" and "count = EPTR - SPTR + 1 mod 64K,
   0 -> nothing". EPTR = SPTR - 2 separates (count $FFFF loads the whole file).
9. BLTVD SCREEN 5 odd NX: XD 14's 8th dot reads 0 over a $00 preset -- needs an open row with a nonzero preset.
10. BLTDV SCREEN 5 padding nibble: XD 13's last nibble 0 = padded 0 vs residue of a zeroed buffer; run after a call
    that leaves nonzero data in the buffer.
11. BLTDM "replaced, not overwritten in place": XD 17 shows only the final length; deleted+recreated vs truncated --
    the directory slot / clusters separate them; the page claims the first.

## 3. Citations that do not match
1. BLTVD "R#44 = the last dot [M XD 10-12, 14, 19]": XD 19 has $43, not $47.
2. BLTDM "IX ... and IY differ by machine": IY is the same on all three in every case ($0154 XD 0-1, $0144 XD 16-17);
   it changes between cases (carried over from error paths), not machines.
3. BLTDM "the block is left as given [M XD 0, 1, 16, 17]": XD 16's used block is at $9F00, never recorded; only the
   unused $F562 block was read back.
4. BLTVD Interface "In: ... CDUMMY +12, ARG +13, LOGOP +14 [M XD 10]": XD 10 has ARG 0 and LOGOP 0; LOGOP is witnessed
   by XD 11, ARG by no case.
5. Concept page: header "DRAFT 0 ... nothing measured yet" with a "Measured (2026-11-23)" bullet; its "an unquoted one
   gives error 13" was measured for BLTDM only (XD 2) but stated for all; the parameter table shows "—" for BLTDV's ARG
   at $F56F though BLTDV measured ARG read (XD 20, 21).
6. BLTDM summary "a disk error goes to BASIC's error handler": no disk error measured (DM-05 open); only error 13.
7. BLTDV "VRAM is not written ... read back unchanged": the window is mode 2 (read-only), never preset; it holds the
   source dots and CHGMOD's fill; a call writing back identical data passes.

## 4. Gaps in the open lists
1. All four: no row for LOGOPR, ACPAGE / DPPAGE, the block's neighbours, timing (see 1.2).
2. BLTVD / BLTDV: no row for name length / drive prefix vs $8003 (1.3); SY / DY != 8 inside the visible area.
3. BLTVD: LOGOP 0 / 3 over a mixed preset; SCREEN 5 odd NX over nonzero preset; NX = 0 / NY = 0 in the header.
4. BLTDV: saving over an existing file; NX = 0 / NY = 0; missing drive / not ready.
5. BLTMD: EPTR = SPTR - 2, EPTR = SPTR, 0-byte file, load past $FFFF, load over the stack / system area.
6. BLTDM: DM-03 lacks the SPTR - 1 vs - 2 split; no row redoing XD 16 with fully different blocks.
7. All four: S#2 before the probe's own wait (1.1); is R#46 in scope (2.7).
