<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `INIPLT` (sub-ROM $0141) — set the power-on palette

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xplt.asm](../../probes/bios/spec/xplt.asm), [scratchpad/AE_xplt_msx2.out](../../scratchpad/AE_xplt_msx2.out), decoded by `scratchpad/xplt_decode.py`).

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

- The palette is initialised and "the current palette is saved in VRAM" [P A1 INIPLT]. That the
  initial values are Table 2.5's [P 2§2.2] is [A] (the table is BASIC's `COLOR=NEW`).
- Which palette ends up in VRAM — the new (power-on) one, or the one the VDP held before — is [A]:
  the VDP's palette cannot be read by the CPU [P 4§1.3], so "save the old one" would need a copy.
- The VRAM place (one of six [P A5]; the call's choice when SCRMOD and the mode copies disagree,
  and in SCREEN 5-8 with ACPAGE ≠ 0), the 48-byte layout, and whether SCREEN 8 is skipped are [A].
- R#16 afterwards, VDP registers, and the interrupt state are [A].

**Measured** [M] (the same on all three references): INIPLT writes the power-on palette to the VDP AND to the
mode's VRAM table, 32 bytes -- 16 entries x 2 (byte 0: red x 16 + blue, byte 1: green), the VDP's own layout:
`0000 0000 1106 3307 1701 2703 5101 2706 7101 7303 6106 6406 1104 6502 5505 7707`. The other 16 bytes of the
48-byte area are not written. **The power-on palette is the same on the HB-F900, NMS 8250 and FS-A1WSX.** The
table is the mode's: $7680 (SCREEN 5), $2020 (1), $0400 (0, width 40), $0F00 (0, width 80), $FA80 (8). Out: A $07,
F $11, B $00, C kept, D $10, E $07.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) match the palette, the table and GETPLT's source; they differ only in
the registers on return ([scratchpad/AE_xplt_msx2.out](../../scratchpad/AE_xplt_msx2.out)).

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded)
(the palette by snapshot, port $9A writes logged, the whole of RAM diffed). Each case presets
distinct palettes: one in the VDP (port #2), a different one at each of the six table places (and
each page's copy of the SCREEN 5-8 places), and VRAM round them with address-dependent garbage.

| case | inputs | state | what it separates |
|---|---|---|---|
| IP-01 | — | SCREEN 0 (width 40, 80), 1, 2, 3, 4, 5, 6, 7 — the six places | the table place per mode (A5) |
| IP-02 | — | VDP palette ≠ VRAM table | VRAM gets the power-on palette vs the VDP's old one vs left |
| IP-03 | — | SCREEN 0, the 2 x 2 x 2 of LINLEN 40 / 80, LINL40 40 / 80, the mode copies TEXT 1 / TEXT 2 | what picks $0F00 vs $0400 |
| IP-04 | — | SCREEN 5, ACPAGE 1, DPPAGE 2, R#2's copy showing page 3 | the table in page 0 vs active vs DPPAGE vs the displayed page |
| IP-05 | — | SCREEN 8 | palette set / VRAM written at all |
| IP-06 | — | SCRMOD 5, RG0SAV / RG1SAV / R#8's copy holding SCREEN 1's mode bits | SCRMOD vs the mode copies decides the place |
| IP-07 | — | 48-byte table area garbage | which bytes are written: 32 vs 48; the per-entry layout |
| IP-08 | — | R#16 preset 7 | all 16 written from P#0 (R#16 reset) vs from the pointer |
| IP-09 | — | R#8 bit 5 (colour 0 solid) set | R#8 untouched |
| IP-10 | — | interrupts on / off; HL IX IY AF' BC' DE' HL' garbage; the control call | the call's interrupt state vs the path's; registers kept |
| IP-11 | — | each machine, expected value open per machine | the power-on palette each machine writes (Table 2.5 is MSX2 BASIC's) |
| IP-12 | — | FS-A1WSX SCREEN 10-12 | the table place in the MSX2+ modes |
| IP-13 | — | a VDP command running (CE = 1) | VRAM written during it vs waits |
| IP-14 | — | a palette RAM copy found by the diff in SETPLT's cases | INIPLT refreshes it vs not |

## Related pages

[RSTPLT](RSTPLT.md), [GETPLT](GETPLT.md), [SETPLT](SETPLT.md);
[vdp-and-palette.md](../concepts/vdp-and-palette.md).

## Tests that cover it

None yet.
