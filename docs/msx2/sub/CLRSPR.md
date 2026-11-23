<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CLRSPR` (sub-ROM $00F5) — clear all sprites

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xspr2.asm](../../../probes/bios/spec/xspr2.asm), [scratchpad/AE_xspr2_msx2.out](../../../scratchpad/AE_xspr2_msx2.out), decoded by [xspr2_decode.py](../../../scratchpad/xspr2_decode.py)).
> Goldfish pass 1 (test writer) 2026-11-23: 12 findings, 7 measured, 3 moved to open ([xspr3.asm](../../../probes/bios/spec/xspr3.asm), [scratchpad/AE_xspr3_msx2.out](../../../scratchpad/AE_xspr3_msx2.out), decoded by [xspr3_decode.py](../../../scratchpad/xspr3_decode.py)).

## Summary

`CLRSPR` resets all 32 sprites: the 2048-byte sprite pattern table is zeroed, each plane shows the
pattern of its own number in the foreground colour, and every sprite is moved off the screen --
measured, to Y = 209 ($D1) in sprite mode 1 (SCREEN 1-3) and Y = 217 ($D9) in sprite mode 2 (SCREEN
4-8; the handbook says 217 for both). It reads the screen mode from SCRMOD. In sprite mode 2 the
colour lives in a separate colour table, 16 bytes per sprite, which the call fills with FORCLR.

## The specification

Shared facts — sprite modes 1 and 2, the colour table, the cells, the sub-ROM calling convention,
the recording: [vdp-and-palette.md](../concepts/vdp-and-palette.md).

### Interface

- **In:** SCRMOD ($FCAF), the screen mode [P A1 CLRSPR]. Besides it the call reads RG1SAV bit 1 (the size),
  FORCLR, PATBAS and ATRBAS [M, below].
- **Out:** none; any register may change [P A1 CLRSPR]; the measured values are below.

### Behaviour

- The sprite patterns := null (zero bytes) [P A1 CLRSPR]; each plane's pattern number := its plane number
  [P A1 CLRSPR]; each sprite's colour := the foreground colour [P A1 CLRSPR]; Y := 217 [P A1 CLRSPR]. 217 is
  not a stop value in either mode (208 in mode 1, 216 in mode 2 [P 4§5.2.2, 4§5.3.2]).
- VDP registers written (R#1, R#8 bit 1), and the interrupt state on return, are [A] (CS-13, CS-17).

**Measured** [M] (the same on all three references; SCREEN 1 = sprite mode 1, SCREEN 5 = mode 2; 8 x 8 and
16 x 16):

- Patterns: the 2048 bytes from PATBAS := $00, in both modes and both sizes; the 256 bytes after them are not zeroed
  (SCREEN 5) ([AE_xspr3](../../../scratchpad/AE_xspr3_msx2.out)).
- Attributes, all 32 planes: Y := $D1 (mode 1) / $D9 (mode 2); X LEFT as it was; the pattern number n (8 x 8) or
  4n (16 x 16: plane 31 gets $7C); byte 3 := FORCLR, the whole byte, in both modes -- FORCLR $0F, $0A and $FF
  give $0F, $0A, $FF (AE_xspr3; planes 0-3 also in [AE_xspr2](../../../scratchpad/AE_xspr2_msx2.out)). In
  mode 2 the attribute's unused fourth byte is therefore written too.
- The mode-2 colour table (ATRBAS - $200): every byte of planes 0, 1 and 31 := FORCLR, the whole byte -- the
  preset $E7 (EC, CC, IC set) is overwritten, and FORCLR $FF writes $FF (AE_xspr3). Planes 2-30 were not read
  (CS-05b). In mode 1 the 512 bytes below ATRBAS are not written (planes 0, 1, 31's positions keep $E7).
- The tables come from the PATBAS / ATRBAS cells, not the mode's defaults: with PATBAS / ATRBAS := $3000 / $2800
  (SCREEN 1) and $6000 / $6E00 (SCREEN 5) the moved tables are cleared and written (AE_xspr3). Whether the
  default tables are also written is [A] (CS-11b).
- The size is RG1SAV's bit 1, not the VDP's R#1: with R#1 written through port $99 to the opposite size, the
  pattern numbers follow RG1SAV (AE_xspr3).
- Out: A $40, F $00 in every case; HL = ATRBAS + $80 (mode 1) / ATRBAS - $200 (mode 2), following the moved cell
  ($1B80, $2880; $7400, $6C00); BC = $0020 (mode 1, 8 x 8), $0080 (mode 1, 16 x 16), $0000 (mode 2); D kept, E =
  FORCLR; IX (the entry address) and IY kept (AE_xspr2, AE_xspr3).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds write the same pattern and attribute bytes and the same mode-2 colour bytes for
FORCLR $0F / $0A, and return the same BC, DE, HL, IX, IY ([AE_xspr2](../../../scratchpad/AE_xspr2_msx2.out),
[AE_xspr3](../../../scratchpad/AE_xspr3_msx2.out)). They differ in:

- **the mode-2 colour table with FORCLR $FF: C-BIOS writes $0F (the low nibble), the references $FF** (the
  attribute's byte 3 is $FF on both) (AE_xspr3) -- a wrong result;
- A / F on return: A $01, F $93 in mode 1; A = FORCLR AND $0F, F $42 in mode 2 (the references: A $40, F $00).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every case gives the same bytes as on the FS-A1WSX, on both models [M] ([AE_trall/xspr2.out](../../../scratchpad/AE_trall/xspr2.out), [AE_trall/xspr3.out](../../../scratchpad/AE_trall/xspr3.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded).
Every case presets the pattern area (2048 bytes from PATBAS and 256 bytes beyond), the attribute
table and the colour table with address-dependent garbage, reads all of them back in full (all 128 attribute
bytes, all 512 colour-table bytes), and sets FORCLR / RG1SAV / SCRMOD as shown. Measured and removed: CS-01, CS-02,
CS-03a/b/c (the span; n vs 4n; the colour table's 16 bytes for planes 0, 1, 31), CS-04, CS-05 (EC / CC / IC
overwritten, for planes 0, 1, 31), CS-08 (RG1SAV vs R#1),
CS-11 (the cells, for the moved tables), CS-12 (FORCLR whole, in SCREEN 1 alone and SCREEN 5).

| case | inputs | state | what it separates |
|---|---|---|---|
| CS-00 | SCRMOD 0 | default tables | anything written in a mode without sprites |
| CS-05b | SCRMOD 5, 16 x 16 | the colour table preset, all 512 bytes read | planes 2-30 written like 0, 1, 31 vs a partial span |
| CS-06 | SCRMOD 4 | RG0SAV / RG1SAV / R#8's copy hold SCREEN 1's mode bits | SCRMOD decides the sprite mode vs the register copies |
| CS-07 | SCRMOD 1 | the copies hold SCREEN 4's mode bits | the converse of CS-06 |
| CS-09 | SCRMOD 8 | ATRBAS $FA00, PATBAS $F000 | 16-bit bases used as is vs ANDed $3FFF (the MSX1 rule) |
| CS-09b | SCRMOD 5 | ATRBAS $7F80 (plane 31's entry and the pattern span cross the 16 KB boundary at $8000) | the address counter carried past A14 vs wrapped |
| CS-10 | SCRMOD 5, 7 | ACPAGE 1, DPPAGE 2, R#14 preset 6 | tables of page 0 vs active vs display page |
| CS-11b | SCRMOD 5 | ATRBAS / PATBAS moved; the DEFAULT tables preset and read; RG5SAV, $FFEA (R#11), RG6SAV left at the defaults | the cells only vs the default tables written as well; the cells vs the register copies |
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
