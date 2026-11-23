<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `INIPLT` (sub-ROM $0141) — set the power-on palette

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xplt.asm](../../../probes/bios/spec/xplt.asm), [scratchpad/AE_xplt_msx2.out](../../../scratchpad/AE_xplt_msx2.out), decoded by [xplt_decode.py](../../../scratchpad/xplt_decode.py) into [scratchpad/AE_xplt_msx2_decoded.out](../../../scratchpad/AE_xplt_msx2_decoded.out)). `[XP n]` = that run's step n (0-59; 17-59 added 2026-11-23, with R#16 and the VDP's VRAM pointer recorded after every step). The three references agree on every step (the SCREEN 0 / 1 tables differ by font data only).
>
> Goldfish pass 1 (test writer) 2026-11-23: 7 findings, 4 measured, 0 moved to open, 3 corrected in wording (steps 41-52 added for it).

## Summary

`INIPLT` puts the 16 palette registers back to the power-on colours and saves a palette in the
VRAM palette table. The handbook's wording leaves open which palette is saved — the one before
the call or the new one — and where the table is in each mode.

## The specification

Shared facts — the palette, the port, the power-on table, the six VRAM palette-table places:
[vdp-and-palette.md](../concepts/vdp-and-palette.md#the-palette).

### Interface

- **In:** none [P A1 INIPLT]. **Out:** none. AF, BC and DE may change [P A1 INIPLT].

### Behaviour

- The palette is initialised and "the current palette is saved in VRAM" [P A1 INIPLT]. The initial
  values are Table 2.5's [P 2§2.2] (BASIC's `COLOR=NEW`) except entry 11 (Measured, below).
- Which palette ends up in VRAM — the new (power-on) one, or the one the VDP held before — is [A]:
  the VDP's palette cannot be read by the CPU [P 4§1.3], so "save the old one" would need a copy.
- The VRAM place (one of six [P A5]; the call's choice when SCRMOD and the mode copies disagree,
  and in SCREEN 5-8 with ACPAGE ≠ 0), the 48-byte layout, and whether SCREEN 8 is skipped are [A].
- R#16 afterwards, VDP registers, and the interrupt state are [A].

**Measured** [M] (the same on all three references):
- INIPLT writes the power-on palette to the VDP AND to the mode's VRAM table, 32 bytes -- 16 entries x 2 (byte 0:
  red x 16 + blue, byte 1: green), the VDP's own layout:
  `0000 0000 1106 3307 1701 2703 5101 2706 7101 7303 6106 6406 1104 6502 5505 7707` [XP 1, 9, 11, 13, 15, 47].
  **The power-on palette is the same on the HB-F900, NMS 8250 and FS-A1WSX**, and equals Table 2.5 [P 2§2.2]
  except entry 11: `6406` = red 6, **blue 4**, green 6, where the table prints blue 3.
- VRAM gets the NEW (power-on) palette, not the one the VDP held: before step 9 the VDP held RSTPLT's pattern
  palette [XP 7, 8], and the table got the power-on values [XP 9].
- Only bytes 0-31 of the mode's table are written: bytes 32-47 kept their preset ($55 [XP 1], the pattern's
  $A3-$EE [XP 47]); in SCREEN 5 the other five places ($0400, $0F00, $2020, $1B80, $FA80, preset to the pattern)
  were left [XP 41-52]. The VDP's VRAM pointer ends at the table + 32 [XP 1, 47].
- The table is the mode's: $7680 (SCREEN 5), $2020 (1), $0400 (0, width 40), $0F00 (0, width 80), $FA80 (8); SCREEN 8
  is not skipped [XP 15].
- R#16 is 0 after the call, and the palette comes out in order although R#16 was $0F before [XP 0, 1]: all 16
  written from P#0.
- Out: A $07, F $11, B $00, C kept, D $10, E $07.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) match the palette, the table and GETPLT's source in SCREEN 0 width 80, 1,
5 and 8, but **in SCREEN 0 width 40 they use $0F00 (the width-80 place) instead of $0400**: INIPLT and SETPLT write
$0F00 and leave $0400, RSTPLT and GETPLT read $0F00 [XP 11, 24-26] (the first DRAFT 1 text said "they differ only in
the registers on return": step 11 already showed $0400 unwritten). Registers on return: F $A8, C $10, D $00, E $00 (the references F $11, C kept, D $10, E $07).
([scratchpad/AE_xplt_msx2.out](../../../scratchpad/AE_xplt_msx2.out)).

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded)
(the palette by snapshot, port $9A writes logged, the whole of RAM diffed). Each case presets
distinct palettes: one in the VDP (port #2), a different one at each of the six table places (and
each page's copy of the SCREEN 5-8 places), and VRAM round them with address-dependent garbage.

| case | inputs | state | what it separates |
|---|---|---|---|
| IP-01 | — | SCREEN 0 (width 40, 80), 1, 2, 3, 4, 5, 6, 7 — the six places | the table place per mode (A5); 0 / 40, 0 / 80, 1, 5, 8 measured, 2, 3, 4, 6, 7 open |
| IP-02 | — | VDP palette ≠ VRAM table | **decided** [XP 9]: VRAM gets the power-on palette |
| IP-03 | — | SCREEN 0, the 2 x 2 x 2 of LINLEN 40 / 80, LINL40 40 / 80, the mode copies TEXT 1 / TEXT 2 | what picks $0F00 vs $0400 |
| IP-04 | — | SCREEN 5, ACPAGE 1, DPPAGE 2, R#2's copy showing page 3 | the table in page 0 vs active vs DPPAGE vs the displayed page |
| IP-05 | — | SCREEN 8 | **decided** [XP 15]: palette set and VRAM ($FA80) written |
| IP-06 | — | SCRMOD 5, RG0SAV / RG1SAV / R#8's copy holding SCREEN 1's mode bits | SCRMOD vs the mode copies decides the place |
| IP-07 | — | 48-byte table area garbage | **decided** [XP 1, 47]: 32 bytes, the VDP's layout |
| IP-08 | — | R#16 preset 7 | **decided** with R#16 $0F before [XP 0, 1]: from P#0, R#16 0 after |
| IP-09 | — | R#8 bit 5 (colour 0 solid) set | R#8 untouched |
| IP-10 | — | interrupts on / off; HL IX IY AF' BC' DE' HL' garbage; the control call | the call's interrupt state vs the path's; registers kept |
| IP-11 | — | each machine, expected value open per machine | **decided** [XP 1]: the same on all three; Table 2.5 except entry 11's blue (4, not 3) |
| IP-12 | — | FS-A1WSX SCREEN 10-12 | the table place in the MSX2+ modes |
| IP-13 | — | a VDP command running (CE = 1) | VRAM written during it vs waits |
| IP-14 | — | a palette RAM copy found by the diff in SETPLT's cases | INIPLT refreshes it vs not |

## Related pages

[RSTPLT](RSTPLT.md), [GETPLT](GETPLT.md), [SETPLT](SETPLT.md);
[vdp-and-palette.md](../concepts/vdp-and-palette.md).

## Tests that cover it

None yet.
