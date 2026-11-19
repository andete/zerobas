<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `SETC` ($0120) — set the current pixel

> **Spec:** FINAL (2026-11-19), the core rules: the fourth test-writer review found no new behaviour --
> only combinations of measured rules (now open items) and citations, fixed. Measured on the VG-8020, alone and with a disk
> interface.

## Summary

`SETC` sets the pixel at the current graphics position to the colour in ATRBYT. In SCREEN 2 it works
on the pattern byte at CLOC and its colour byte at CLOC XOR $2000 (GRPCOL and GRPCGP are not used),
and takes the first that applies: ATRBYT (the whole byte) is the background colour -- it clears the
pixel's bit; ATRBYT's low nibble is the foreground colour -- it sets the bit; every other bit of the
pattern byte is set -- it clears the pixel's bit and ORs ATRBYT into the colour byte's high nibble
(colour AND $F0), so ATRBYT becomes the background colour; otherwise it sets the bit and makes
ATRBYT the foreground colour, which recolours the byte's other set pixels too. In SCREEN 3 it puts
ATRBYT into the nibble CMASK selects -- for the low nibble ORed in whole, so ATRBYT over 15 spills
into the high one. A is the byte written last (F its flags, below); BC, DE, HL, IX, IY, the cells and
the VDP registers are kept, and interrupts are **on** after.

zerobas does all four the same (the third since D-SETCLAST, 2026-11-19); it differs in where the bytes
are with CLOC $2000 and above, in ATRBYT over 15 in SCREEN 3 and in F (below).

## The specification

References: the Philips VG-8020's main BIOS, alone (row `N`) and with an NMS 1200 disk interface
(row `D`). Ours: the C-BIOS repack, diskless on row `N`, the disk build on `D`.

**Evidence.** **[XP rNN]**: case `NN` of the XGFX3 probe, run 6, on row `r`, both rows in
[`scratchpad/XGFX3_run6.out`](../../scratchpad/XGFX3_run6.out) (the two rows recorded the same bytes).
`probes/bios/spec/xgfx3.asm` documents the presets, the case table and the 128-byte record:
- Before each case the probe sets, by hand: the screen-table cells to one of four sets -- set 0 the
  published defaults (GRPCGP $0000, GRPCOL $2000, MLTCGP $0000); set 1 GRPCGP $2000, GRPCOL $0000,
  MLTCGP $1000; set 5 GRPCGP = GRPCOL = $2000; set 6 GRPCGP $0800, GRPCOL $2000; SCRMOD, CLOC, CMASK
  and ATRBYT to the case's; every VRAM byte to ((address low) XOR (address high) XOR $5A) OR (address
  high AND $3C), so the sixteen 1 KB blocks sum to sixteen different values, none 0; the VDP registers
  to a preset with the display off. It reads the VDP status last.
- BC $1357, DE $9BDF, IX $4321, IY $8765 (complemented when bit 2 of the case number is set), HL, A
  $A7 (or the case's), entry F and the interrupt state as the case lists them. After the call it
  records every register, the interrupt state (read twice), CLOC, CMASK, ATRBYT, the 16-bit sums of
  VRAM's 1 KB blocks (read with R#1 := $80 first) and three 16-byte VRAM windows (the pixel's pattern
  byte, its colour byte, and the bytes after).
- Run 1, SCREEN 2, set 0: READC 00-05 (pixels at (100,50), (101,50), (0,0), (7,0), (255,191),
  (64,9)), SETC 06-09 (ATRBYT 5, $0F, 0, $1A), NSETCX 10-15 (HL 1, 5, 8 from a cell's start, 20, 12
  from x 250, 0). Set 1: READC 16, SETC 17, NSETCX 18. SCREEN 3: READC 19-22, SETC 23-25 (ATRBYT 5,
  $0F, $1A), NSETCX 26-28 (HL 1, 6, 9).
- Run 2: READC 29, SETC 30 (set 1); SETC 31 (completing pattern $FB with ATRBYT the background), 35
  (31 and 35 with entry A $00); NSETCX 32 (ATRBYT $1A, HL 20), 36-39 (SCREEN 3 HL 3, $17FF HL 2, SCREEN 3 HL 0,
  completing $FA); SETC 33 (SCREEN 3 ATRBYT $1A); READC 34 (colour 0); READC / SETC 40-41 (set 5),
  42-43 (set 6); READC / SETC / NSETCX 44-46 (SCREEN 3, set 1).
- Run 3: SETC 47-50 (completing $FB with ATRBYT neither nibble / the foreground; a set bit with
  ATRBYT the background; a clear bit with the foreground); NSETCX 51-53 (2 or 3 pixels with ATRBYT
  the background / neither / the foreground), 54-56 (SCREEN 3 HL $0100, $0102, $0101), 57-58
  (SCREEN 2 HL 0 on a clear bit, HL $0100), 59 (set 5).
- Run 4: READC 60-61 (sets 5 and 6; 61's candidate bytes differ only in the nibble it does not read); SETC 62 (pattern
  $FF, ATRBYT neither), 65 (ATRBYT $1A over background $A), 66 (colour byte $FF, ATRBYT $F), 68
  (clearing the only set bit); NSETCX 63-64 (a whole byte, ATRBYT the foreground / background), 67
  (SCREEN 3, ATRBYT $1A).
- Run 5: NSETCX with HL 0 and ATRBYT the background (69) / the foreground (70) / on pattern $FF
  (71, set 1); NSETCX completing its first byte and going on (72: CMASK $04, HL 5) and entering a
  byte from bit 7 and completing it (73: $015C, CMASK $01, HL 3); SETC with ATRBYT $1A over
  foreground $A (74) and on a byte's last clear bit (77); READC in set 6 where the two candidate
  colour bytes differ in the nibble read (75); NSETCX on colour byte $FF with ATRBYT $F (76).
- Run 6: SETC with entry F $FF on the pattern-only steps (78, 79) and the last-clear-bit step (80);
  NSETCX with ATRBYT $1A over foreground $A (81) and on a byte's last clear bit under foreground $E
  (82), SETC the same (84); SETC SCREEN 3 ATRBYT $1A into a low nibble under $A_ (83); SETC with
  ATRBYT $0E clearing a bit to pattern $36 (85); NSETCX HL 0 on pattern $FB with CMASK $04 (86);
  READC / SETC in SCREEN 3 at CLOC $2164 (87, 88).
- The record's RG0SAV-RG7SAV, SCRMOD and VDP registers are compared (R-xx-REGS); FORCLR / BAKCLR /
  BDRCLR, recorded too, are not preset by the probe and not compared.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/bios/spec/xsetc_rules.py -- do not edit; `python3 tools/spec_rules.py probes/bios/spec/xsetc_rules.py --write` -->

**5 rules; 5 hold on the reference. Of the 1024 recorded outputs (each case's cursor, cells, A, table entries ...): 1024 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. SETC ($0120): set the current pixel

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-SC-VRAM** VRAM, SCREEN 2: the pattern byte at CLOC and its colour byte at CLOC XOR $2000 (GRPCOL and GRPCGP are not used), by the first that applies -- ATRBYT equal to the colour byte's background nibble: CMASK's bit cleared; ATRBYT's low nibble equal to the foreground nibble: the bit set; the pattern byte OR CMASK = $FF (no other bit of the byte clear): the bit cleared and colour byte := (colour AND $F0) OR ATRBYT -- ATRBYT ORed in whole, so $1A over $E_ gives $FA; otherwise the bit set and (ATRBYT x 16) AND $F0 into the foreground nibble ($1A gives $A0). The background test takes the whole ATRBYT ($1A is not $A), the foreground test its low nibble ($1A is $A). SCREEN 3: CMASK $0F -- byte := (byte AND $F0) OR ATRBYT (whole: $1A over $A4 gives $BA); CMASK $F0 -- byte := (byte AND $0F) OR ((ATRBYT x 16) AND $F0). Nothing else changes. | 64 | ✓ | ✗ 24: XP N17, XP N25, XP N30, XP N33, XP N41, XP N47 … (+18) |
| **R-SC-AF** A := the byte written last, whatever A and F were on entry: in SCREEN 2 the colour byte when it is written, F its flags as an OR leaves them; when only the pattern byte is written, the pattern byte, F its S, Z and P/V flags with H, N, C and bits 3 / 5 clear ($FF gives $84, $00 $44). In SCREEN 3 the pixel byte, F its OR flags. | 64 | ✓ | ✗ 54: XP N06, XP N07, XP N08, XP N17, XP N25, XP N30 … (+48) |
| **R-SC-KEEP** BC, DE, HL, IX and IY are kept; CLOC, CMASK and ATRBYT are kept. | 64 | ✓ | ✓ |
| **R-SC-REGS** RG0SAV-RG7SAV ($A5 preset), SCRMOD and the VDP registers R#0-R#7 are kept: the call writes no VDP register. (FORCLR / BAKCLR / BDRCLR, recorded too, are not preset by the probe: not compared.) | 64 | ✓ | ✓ |
| **R-SC-EI** Interrupts are on after the call, whether they were on or off before it. | 64 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

| TODO item | rules zerobas fails |
|---|---|
| **D-SETCCOL** (with CLOC $2000-$3FFF zerobas swaps the two bytes: the pattern byte at CLOC AND NOT $2000, the colour byte at CLOC OR $2000 -- and in SCREEN 3 the byte at CLOC AND NOT $2000 -- where the VG-8020 uses CLOC and CLOC XOR $2000; they part where the pattern table is at $2000 -- cases 17, 30, 41, 62, 88) | R-SC-VRAM, R-SC-AF |
| **D-SETCATR** (SCREEN 3, ATRBYT over 15: zerobas writes $B for $1A into the nibble, where the VG-8020 writes (ATRBYT x 16) AND $F0 into the high one and ORs ATRBYT in whole into the low one -- cases 25, 33, 83) | R-SC-VRAM, R-SC-AF |
| **D-SETCF** (zerobas returns another F on most cases -- the colour-write steps too, A the same: case 06 $08 against $28 -- and other A / F where its bytes differ) | R-SC-AF |

## Open (not measured)

- **[A]** A colour byte whose two nibbles are equal measured once (case 66: the bit is cleared, so
  the background test comes first); ATRBYT over 15 only as $1A (SCREEN 2: 9, 65, 74, 77, 84;
  SCREEN 3: 25, 33, 83).
- **[A]** SCRMOD other than 2 and 3; CMASK values that are not one pixel's mask.
- **[A]** SCREEN 3 CLOC $2000-$3FFF measured once (88: the byte at CLOC itself).
- **[A]** The Z flag on a colour-byte or SCREEN 3 result (only pattern-only results of $00 measured).
- **[A]** CLOC $4000 and above: whether the colour byte is at CLOC XOR $2000 or (CLOC + $2000) AND
  $3FFF (the same below $4000).
- **[A]** Entry with a VDP interrupt pending (the probe reads the status first); the interrupt state
  is read only after the call; the alternate registers and SP; the time it takes.
- **[A]** VRAM outside the three windows beyond the block sums; VRAM writes that keep a block's sum.
- **[A]** RAM other than the cells recorded.
- **[A]** The CF-3300 (the second reference).

## Related pages

the other pixel calls ([READC](READC.md), [SETC](SETC.md), [NSETCX](NSETCX.md)), measured by the same
probe; [SETATR](SETATR.md), which sets ATRBYT; [MAPXYC](MAPXYC.md), [FETCHC](FETCHC.md) /
[STOREC](STOREC.md); [screen modes](../concepts/screen-modes.md).

## Tests that cover it

**`spec-live`** ([tools/spec_live.py](../../tools/spec_live.py), in every gate): every rule above, run live on zerobas against these cases' measured reference values. It fails if a rule fails that *Differences from the reference* does not name, or a named one holds ([docs/spec-method.md](../spec-method.md) §8).

Also the suites `tools/entry_table.py --bios` lists for $0120.
