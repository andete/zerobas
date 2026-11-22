<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `GRPPRT` ($008D) — draw a character on a graphics screen

> **Spec:** FINAL (2026-11-19), the core rules: the second test-writer review found no new behaviour; the
> separating cases it asked for (XGFX5B, cases 63-72) all confirmed the rules. Measured on the VG-8020, alone and with a disk
> interface.

## Summary

`GRPPRT` draws the character in A at the graphics accumulator (GRPACX $FCB7, GRPACY $FCB9) in FORCLR,
from the font CGPNT points at, and moves the accumulator on: 8 pixels in SCREEN 2, 32 in SCREEN 3 (one
glyph pixel is a 4 x 4 block there), wrapping to the next line past X 255 and to the top past Y 191.
It draws line by line, setting each pattern byte's bits as [SETC](SETC.md) sets one -- except that
it skips a byte with no bits to set and has neither the whole-byte nor the last-clear-bit step -- and
moving down as [TDOWNC](TDOWNC.md) does, stopping where TDOWNC stops. LOGOPR is not used. A position
outside the screen draws nothing; CR ($0D) is a line feed to X 0 -- worked on the low bytes of GRPACX
and GRPACY only; the other control codes do nothing.
ATRBYT becomes FORCLR; the registers are kept; interrupts are **on** after, except after a control
code.

zerobas does the same (D-GRPPRTPOS / D-GRPPRTCR / D-GRPPRTOFF / D-GRPPRTCOL, 2026-11-19): its GRPPRT
is built on the BIOS's own MAPXYC / TDOWNC / SETC / RIGHTC, as these rules describe the VG-8020's,
with the SCREEN 2 byte rule above. (BASIC's PRINT # to GRP keeps its own code, measured at BASIC
level.)

## The specification

References: the Philips VG-8020's main BIOS, alone (row `N`) and with an NMS 1200 disk interface
(row `D`). Ours: the C-BIOS repack, diskless on row `N`, the disk build on `D`.

**Evidence.** **[XT rNN]**: case `NN` on row `r` -- cases 00-62 from the XGFX5 probe, run 3
([`scratchpad/XGFX5_run3.out`](../../scratchpad/XGFX5_run3.out)), cases 63-72 from XGFX5B, run 1
([`scratchpad/XGFX5B_run1.out`](../../scratchpad/XGFX5B_run1.out)), both rows recording the same bytes.
`probes/bios/spec/xgfx5.asm` (and xgfx5b.asm, the same frame) document the presets, the font, the case
tables and the 128-byte record:
- Before each case the probe sets, by hand: the screen-table cells to the published defaults (set 0:
  GRPCGP $0000, GRPCOL $2000, MLTCGP $0000) or moved ones (set 1: GRPCGP $2000, GRPCOL $0000, MLTCGP
  $1000; set 6: GRPCGP $0800, GRPCOL $2000, MLTCGP $0000; set 7: the defaults with GRPCOL $0800); SCRMOD, FORCLR,
  LOGOPR, ATRBYT ($77), GRPACX and GRPACY to the case's; CLOC $5A5A, CMASK $A5; RG0SAV-RG7SAV $A5; CGPNT to the probe's
  own font in RAM (character c's line j is (c x 7) XOR (j x $33) XOR $96), so no ROM font byte is
  involved; every VRAM byte to ((address low) XOR (address high) XOR $5A) OR (address high AND $3C);
  the VDP registers to a preset with the display off. It reads the VDP status last.
- BC $1357, DE $9BDF, IX $4321, IY $8765 (complemented when bit 2 of the case number is set), HL
  $2468, A the character, F and the interrupt state as the case lists them. After the call it
  records every register, the interrupt state (read twice), RG0SAV-RG7SAV, SCRMOD, the VDP registers,
  the 16-bit sums of VRAM's 1 KB blocks, three 16-byte VRAM windows, CLOC, CMASK, ATRBYT, GRPACX,
  GRPACY, FORCLR and LOGOPR. BAKCLR / BDRCLR, recorded too, are not preset and not compared.
- SCREEN 2, set 0, "A" ($41) unless named: at (0, 0), (100, 50) with F $FF and interrupts on, (96,
  48) with FORCLR 9, code $00 (FORCLR 4), codes $20, $FF, $0D, $0A, $08, $1F (02-09); at (250, 10), (252, 188),
  (0, 190), (300, 50), (100, 200) (10-14); LOGOPR 3 (15), FORCLR $1A (16), set 1 (17); SCREEN 3 at (0,
  0), (100, 50) with FORCLR 9, F $FF and interrupts on, CR, (252, 188), set 1 (18-22); X $FFF8 (23).
- Run 2: code $3A, whose line 5 is $FF and line 0 $00, with FORCLR 9 / 3 (24, 25); X 248 and 247 at
  Y 48, (248, 184), (100, 191) (26-29); SCREEN 3 at (2, 6), (224, 0), (192, 160) (30-32); codes $7F,
  $0C, $1B, $80 (33-36); FORCLR 3 (37); Y $FFFF (38); $0A with interrupts on (39); CR at Y 186 in
  SCREEN 2 and Y 170 in SCREEN 3 (40, 41).
- Run 3: set 6 (42); CR at Y 180 (SCREEN 2) and 150 (SCREEN 3) (43, 44); SCREEN 3 at X 200 (45);
  outside the screen at Y 192 and X 256 in SCREEN 2 (46, 47) and 3 (48, 49); CR at X 300, Y 200, Y
  $FFFF (50-52); CR with F $FF and interrupts on, $0A with F $FF, X 300 with F $FF (53-55); SCREEN 3
  FORCLR $1A at block 1 (56); FORCLR $13 over foreground 3 (57); codes $01, $1C, $1D, $1E (58-61);
  FORCLR $1E over background $E (62).
- XGFX5B: SCREEN 2 at (96, 100) and SCREEN 3 at (96, 140), glyphs crossing a character / block row
  in the table's middle (63, 64); set 6 at Y 64 and Y 188 (65, 66); Y $0130 in SCREEN 2 and 3 (67,
  72); set 7 (68); colour byte $FF with FORCLR $0F at (160, 0) (69); $08 in SCREEN 3 (70); $00 with
  interrupts on (71).
- Cases 19 and 22's windows hold no drawn byte: their VRAM evidence is the block sums alone.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/bios/spec/xgrpprt_rules.py -- do not edit; `python3 tools/spec_rules.py probes/bios/spec/xgrpprt_rules.py --write` -->

**6 rules; 6 hold on the reference. Of the 2774 recorded outputs (each case's cursor, cells, A, table entries ...): 2774 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. GRPPRT ($008D): draw a character at the graphics accumulator

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-GP-VRAM** A character code $20-$FF at GRPACX / GRPACY ($FCB7 / $FCB9) within the screen (X 0-255, Y 0-191; outside, nothing is drawn) is drawn from the font at CGPNT ($F91F slot, $F920 address -- the probe's own RAM font): its 8 lines, each 8 pixels from bit 7, in FORCLR ($F3E9). SCREEN 2: from the position MAPXYC gives (GRPCGP-based), each line's bits shifted right by X AND 7 into the pattern byte and the rest into the next cell's (none past X 255: no wrap); each pattern byte with bits m, colour byte at its address XOR $2000 (GRPCOL not used: GRPCGP $0800 / GRPCOL $2000 measured): m = 0 -- nothing written; FORCLR (whole) = the background nibble -- the bits cleared; FORCLR's low nibble = the foreground nibble -- the bits set; otherwise the bits set and (FORCLR x 16) AND $F0 into the foreground nibble (no whole-byte or last-clear-bit step: a line $FF sets pattern $FF). SCREEN 3: each glyph pixel is one block (X / 4, Y / 4 the first), its nibble := FORCLR's as SETC writes it, none past block column 63. After each line the position moves down as TDOWNC does, and drawing stops where TDOWNC stops (in SCREEN 2 at the bottom; in SCREEN 3 at a block row's line 7 with CLOC's high byte 5 or more). LOGOPR is not used. Control codes draw nothing. (BAKCLR / BDRCLR, recorded, are not preset by the probe: not compared.) | 146 | ✓ | ✓ |
| **R-GP-POS** CLOC / CMASK ($F92A / $F92C): for a drawn character, the first column's position where the last TDOWNC step left it -- the line after the glyph, or the last line drawn where TDOWNC stopped (SCREEN 3: CMASK the block's nibble mask); otherwise kept. | 146 | ✓ | ✓ |
| **R-GP-ACC** GRPACX / GRPACY: a drawn character adds 8 to GRPACX in SCREEN 2, 32 in SCREEN 3; past 255 GRPACX := 0 and GRPACY goes on by the same step, to 0 past 191. CR ($0D) does that line feed whatever X is, on the LOW BYTES: GRPACX's low byte := 0 (X 300 gives 256), GRPACY's low byte + the step without a carry into the high byte (Y $FFFF gives $FF07), GRPACY := 0 when that low byte is past 191 (Y 186, 200). Other control codes ($00, $01, $08, $0A, $0C, $1B-$1F measured) and positions outside the screen keep both. | 146 | ✓ | ✓ |
| **R-GP-ATR** ATRBYT := FORCLR, except for a control code (kept: $77 preset). FORCLR and LOGOPR are kept. | 146 | ✓ | ✓ |
| **R-GP-KEEP** A, F, BC, DE, HL, IX and IY are kept; RG0SAV-RG7SAV, SCRMOD and the VDP registers are kept. | 146 | ✓ | ✓ |
| **R-GP-EI** Interrupts are on after a printable code (drawn or outside the screen); after a control code they are as they were. | 146 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None measured: every rule holds on zerobas.

## Open (not measured)

- **[A]** SCRMOD other than 2 and 3 (SCREEN 0 / 1); FORCLR over 15 only as $1A, $13, $1E (in SCREEN 3
  only $1A); LOGOPR only 0 and 3 (3 only in SCREEN 2); GRPCGP / MLTCGP other than the sets measured.
- **[A]** A background step that empties a pattern byte (no measured byte ends at $00).
- **[A]** Control codes other than $00, $01, $08, $0A, $0C, $0D, $1B-$1F; in SCREEN 3 only $08 and CR.
- **[A]** CR with a GRPACY whose low byte goes past 191 while its high byte is not 0.
- **[A]** The foreground step ("bits set", no colour write) leaves the VRAM the "otherwise" step
  would: only the VDP's write traffic could tell them apart.
- **[A]** The font from a ROM slot (CGPNT's default): only the probe's RAM font was used.
- **[A]** Entry with a VDP interrupt pending (the probe reads the status first); the interrupt state
  is read only after the call; the alternate registers and SP; the time it takes.
- **[A]** VRAM outside the three windows beyond the block sums; VRAM writes that keep a block's sum.
- **[A]** RAM other than the cells recorded.
- **[A]** The CF-3300 (the second reference).

## Related pages

[SETC](SETC.md) and [NSETCX](NSETCX.md), whose per-byte rule it shares in part; [TDOWNC](TDOWNC.md);
[MAPXYC](MAPXYC.md); the other graphics calls in [the index](index.md);
[screen modes](../concepts/screen-modes.md).

## Tests that cover it

**`spec-live`** ([tools/spec_live.py](../../tools/spec_live.py), in every gate): every rule above, run live on zerobas against these cases' measured reference values. It fails if a rule fails that *Differences from the reference* does not name, or a named one holds ([docs/spec-method.md](../spec-method.md) §8).

Also the suites `tools/entry_table.py --bios` lists for $008D.
