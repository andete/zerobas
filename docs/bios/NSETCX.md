<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `NSETCX` ($0123) — set pixels to the right

> **Spec:** DRAFT 3 (2026-11-19), after two test-writer reviews, measured again (runs 2-5). Measured on the VG-8020, alone and with a disk
> interface.

## Summary

`NSETCX` sets pixels from the current graphics position rightwards, from cell to cell, to the colour
in ATRBYT: HL of them in SCREEN 2, L of them in SCREEN 3 (H is not used there, and L = 0 gives 256).
In SCREEN 2 it treats each pattern byte (colour byte at its address XOR $2000) as [SETC](SETC.md) does
one pixel, with all the byte's new bits at once; a byte with all 8 pixels to set becomes pattern $00
with colour byte ATRBYT -- the same pixels, drawn in the background colour. HL = 0 in SCREEN 2 sets
no pixel but still takes the byte at CLOC through those steps with no bits: unless ATRBYT matches a
colour already there, it goes into the background nibble when the pattern byte is $FF, the
foreground nibble otherwise. In SCREEN 3 each pixel's nibble becomes ATRBYT's, and CLOC / CMASK end
on the pixel after the last; in SCREEN 2 they are kept. The VDP registers are kept; interrupts are
**on** after.

zerobas sets the same pixels for HL from 1 to 255 where the pattern table is below $2000 and ATRBYT
is below 16 in SCREEN 3, except a byte whose other bits are all set; it writes whole bytes the other
way round, counts all of HL in SCREEN 3, and does nothing for HL = 0 (below).

## The specification

References: the Philips VG-8020's main BIOS, alone (row `N`) and with an NMS 1200 disk interface
(row `D`). Ours: the C-BIOS repack, diskless on row `N`, the disk build on `D`.

**Evidence.** **[XP rNN]**: case `NN` of the XGFX3 probe, run 5, on row `r`, both rows in
[`scratchpad/XGFX3_run5.out`](../../scratchpad/XGFX3_run5.out) (the two rows recorded the same bytes).
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
- The record's RG0SAV-RG7SAV, SCRMOD and VDP registers are compared (R-xx-REGS); FORCLR / BAKCLR /
  BDRCLR, recorded too, are not preset by the probe and not compared.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/bios/spec/xnsetcx_rules.py -- do not edit; `python3 tools/spec_rules.py probes/bios/spec/xnsetcx_rules.py --write` -->

**5 rules; 5 hold on the reference. Of the 748 recorded outputs (each case's cursor, cells, A, table entries ...): 748 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. NSETCX ($0123): set pixels to the right

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-NX-VRAM** VRAM: pixels from the current position rightwards, from cell to cell (into the next row's cells past the right edge) -- in SCREEN 2 HL of them, in SCREEN 3 L of them (H not used; L = 0 gives 256). SCREEN 2, per pattern byte with the bits m it gets (its colour byte at its address XOR $2000; GRPCOL / GRPCGP not used), the first that applies: all 8 bits -- pattern $00 and colour byte ATRBYT (the same pixels, drawn as background); ATRBYT (whole) equal to the background nibble -- the bits cleared; ATRBYT's low nibble equal to the foreground nibble -- the bits set; pattern OR m = $FF -- the bits cleared and ATRBYT's low nibble into the background nibble; otherwise the bits set and (ATRBYT x 16) AND $F0 into the foreground nibble. HL = 0 in SCREEN 2 takes the byte at CLOC through the same steps with no bits (m = 0). SCREEN 3: each pixel's nibble becomes ATRBYT's. Nothing else changes. | 68 | ✓ | ✗ 36: XP N12, XP N13, XP N15, XP N18, XP N32, XP N38 … (+30) |
| **R-NX-POS** CLOC and CMASK: kept in SCREEN 2; in SCREEN 3 moved to the pixel after the last one set. ATRBYT is kept. | 68 | ✓ | ✗ 6: XP N38, XP N55, XP N56, XP D38, XP D55, XP D56 |
| **R-NX-KEEP** IX and IY are kept. (A, F, BC, DE and HL are left holding working values: not compared, the group `XN`.) | 68 | ✓ | ✓ |
| **R-NX-REGS** RG0SAV-RG7SAV ($A5 preset), SCRMOD and the VDP registers R#0-R#7 are kept: the call writes no VDP register. (FORCLR / BAKCLR / BDRCLR, recorded too, are not preset by the probe: not compared.) | 68 | ✓ | ✓ |
| **R-NX-EI** Interrupts are on after the call, whether they were on or off before it. | 68 | ✓ | ✗ 10: XP N38, XP N57, XP N69, XP N70, XP N71, XP D38 … (+4) |

<!-- RULES END -->

## Differences from the reference

| TODO item | rules zerobas fails |
|---|---|
| **D-NSETCXFULL** (a pattern byte with all 8 pixels to set: zerobas writes pattern $FF and ATRBYT in the foreground nibble -- or leaves the colour when ATRBYT is a colour already there -- where the VG-8020 writes pattern $00 and colour byte ATRBYT: the same pixels, other bytes -- cases 12, 13, 32, 58, 63, 64) | R-NX-VRAM |
| **D-SETCLAST** (as SETC: a byte whose other bits are all set, ATRBYT neither colour -- the first byte of a run, its last, or the only one: zerobas turns the whole byte to ATRBYT -- cases 39, 72, 73) | R-NX-VRAM |
| **D-SETCCOL** (zerobas puts the colour byte at CLOC OR $2000, the VG-8020 at CLOC XOR $2000: they part where the pattern table is at $2000 -- cases 18, 59) | R-NX-VRAM |
| **D-SETCATR** (as SETC, SCREEN 3 ATRBYT over 15 -- case 67) | R-NX-VRAM |
| **D-NSETCXL** (SCREEN 3: zerobas counts HL, the VG-8020 L alone -- HL $0102 sets 258 pixels, not 2; cases 55, 56) | R-NX-VRAM, R-NX-POS |
| **D-NSETCX0** (HL = 0: zerobas returns at once, writing nothing and leaving interrupts as they were; the VG-8020 writes the colour byte in SCREEN 2 and sets 256 pixels in SCREEN 3 -- cases 15, 38, 57, 69-71) | R-NX-VRAM, R-NX-POS, R-NX-EI |

## Open (not measured)

- **[A]** A, F, BC, DE and HL after the call: working values, not compared (the group `XN`).
- **[A]** SCREEN 2 HL above $0100; ATRBYT over 15 in SCREEN 2 (measured for SETC only); a colour
  byte with equal nibbles measured once (76: the bits cleared, the background test first).
- **[A]** SCRMOD other than 2 and 3; CMASK values that are not one pixel's mask.
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

Also the suites `tools/entry_table.py --bios` lists for $0123.
