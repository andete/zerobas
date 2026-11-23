<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CLRSPR` (sub-ROM $00F5) — clear all sprites

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xspr2.asm](../../../probes/bios/spec/xspr2.asm), [scratchpad/AE_xspr2_msx2.out](../../../scratchpad/AE_xspr2_msx2.out), decoded by `scratchpad/xspr2_decode.py`).

## Summary

`CLRSPR` resets all 32 sprites: their patterns are cleared, each plane shows the pattern of its
own number in the foreground colour, and every sprite is moved to Y = 217, off the screen. It
reads the screen mode from SCRMOD. In sprite mode 2 (SCREEN 4-8) the colour lives in a separate
colour table, 16 bytes per sprite; how the call fills it is not published.

## The specification

Shared facts — sprite modes 1 and 2, the colour table, the cells, the sub-ROM calling convention,
the recording: [vdp-and-palette.md](../concepts/vdp-and-palette.md).

### Interface

- **In:** SCRMOD ($FCAF), the screen mode [P A1 CLRSPR]. The cells it reads besides — RG1SAV for
  the size, FORCLR, ATRBAS / PATBAS — are [A] (the MSX1 call reads them:
  [CLRSPR](../../bios/CLRSPR.md)).
- **Out:** none; any register may change [P A1 CLRSPR].

### Behaviour

- The sprite patterns := null (zero bytes) [P A1 CLRSPR]; the span cleared (2048 bytes from
  PATBAS, or 32 patterns' worth) is [A].
- Each plane's pattern number := its plane number [P A1 CLRSPR]; times 4 for 16 x 16 sprites is
  [A].
- Each sprite's colour := the foreground colour [P A1 CLRSPR]. In sprite mode 1 that is the
  attribute's fourth byte [P 4§5.2.2]; in sprite mode 2 the colour is in the colour table
  [P 4§5.3.2], and which of its 16 bytes per plane are written, with what EC / CC / IC bits, and
  whether the attribute's (unused) fourth byte is written too, are [A].
- Each sprite's Y := 217 ($D9) [P A1 CLRSPR]. 217 is not a stop value in either mode (208 in mode
  1, 216 in mode 2 [P 4§5.2.2, 4§5.3.2]); whether the call writes 217 in sprite mode 1 as well
  (the MSX1 call writes 209) is [A]. X is not mentioned [A: left].
- VDP registers written (R#1, R#8 bit 1), and the interrupt state on return, are [A].

**Measured** [M] (the same on all three references; SCREEN 1 = sprite mode 1, SCREEN 5 = mode 2): every
attribute entry gets Y := $D1 (mode 1) / $D9 (mode 2), X LEFT as it was, the pattern number n (8 x 8) or 4n (16 x
16, from RG1SAV bit 1), and byte 3 := $0F. Out: A $40, F $00, HL = the attribute table's base + $80 / - $200 (SCREEN
1 $1B80, SCREEN 5 $7400).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds write the same attribute bytes; their A / F on return differ ([scratchpad/AE_xspr2_msx2.out](../../../scratchpad/AE_xspr2_msx2.out)).

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded).
Every case presets the pattern area (2048 bytes from PATBAS and 256 bytes beyond), the attribute
table and the colour table with address-dependent garbage, and FORCLR / RG1SAV / SCRMOD as shown.

| case | inputs | state | what it separates |
|---|---|---|---|
| CS-00 | SCRMOD 0 | default tables | anything written in a mode without sprites |
| CS-01 | SCRMOD 1, RG1SAV 8 x 8 | default tables | Y 217 vs 209 vs 208 in sprite mode 1; X left |
| CS-02 | SCRMOD 5, 8 x 8 | default tables | Y 217 vs 216; mode-2 colour table written at all |
| CS-03a | SCRMOD 1, 16 x 16 | FORCLR $0A | pattern k vs 4k in mode 1; span cleared: 2048 vs 32 x 32 vs 32 x 8 bytes |
| CS-03b | SCRMOD 5, 16 x 16 | FORCLR $0A | colour table 16 bytes / plane vs 8 vs 1; pattern k vs 4k in mode 2 |
| CS-03c | SCRMOD 1 and 5, 8 x 8 | the pattern area beyond 256 bytes | span cleared: 2048 vs 32 x 8 |
| CS-04 | SCRMOD 5, 8 x 8 | attribute 4th byte garbage | mode-2 4th byte written (FORCLR / 0) vs left |
| CS-05 | SCRMOD 5 | colour-table bytes with EC / CC / IC set | those bits cleared vs kept |
| CS-06 | SCRMOD 4 | RG0SAV / RG1SAV / R#8's copy hold SCREEN 1's mode bits | SCRMOD decides the sprite mode vs the register copies |
| CS-07 | SCRMOD 1 | the copies hold SCREEN 4's mode bits | the converse of CS-06 |
| CS-08 | RG1SAV 16 x 16, R#1 8 x 8 (and the reverse) | SCRMOD 1 | the size from RG1SAV vs from the VDP |
| CS-09 | SCRMOD 8 | ATRBAS $FA00, PATBAS $F000 | 16-bit bases used as is vs ANDed $3FFF (the MSX1 rule) |
| CS-10 | SCRMOD 5, 7 | ACPAGE 1, DPPAGE 2, R#14 preset 6 | tables of page 0 vs active vs display page |
| CS-11 | SCRMOD 5 | ATRBAS / PATBAS moved; RG5SAV, $FFEA (R#11), RG6SAV left at the defaults | the cells vs the register copies vs A5 defaults |
| CS-12 | FORCLR $FF, $1F | SCRMOD 1 and 5 | colour written whole vs nibble-masked, per mode |
| CS-13 | SCRMOD 5 | R#8 bit 1 set; RG1SAV ≠ R#1 | R#1 := RG1SAV (MSX1) still; R#8 touched |
| CS-14 | SCRMOD 6, 7 | default tables | the 512-wide modes place the tables as A5 says |
| CS-15 | SCRMOD 10-12 | FS-A1WSX only | sprite mode 2 tables in the MSX2+ modes |
| CS-16 | — | a VDP command running (CE = 1) | waits vs writes VRAM during it |
| CS-17 | all registers incl. AF' BC' DE' HL' IX IY garbage | interrupts on / off; the control call | registers kept; the call's interrupt state vs the path's |

## Related pages

[CALPAT](CALPAT.md), [CALATR](CALATR.md), [GSPSIZ](GSPSIZ.md), which compute from the same cells;
the MSX1 call [CLRSPR $0069](../../bios/CLRSPR.md);
[vdp-and-palette.md](../concepts/vdp-and-palette.md).

## Tests that cover it

None yet.
