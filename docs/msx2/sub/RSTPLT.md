<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `RSTPLT` (sub-ROM $0145) — load the palette from VRAM

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xplt.asm](../../probes/bios/spec/xplt.asm), [scratchpad/AE_xplt_msx2.out](../../scratchpad/AE_xplt_msx2.out), decoded by `scratchpad/xplt_decode.py`).

## Summary

`RSTPLT` loads the 16 palette registers from the palette table in VRAM — the machine-code side of
BASIC's `COLOR=RESTORE`, which a program uses after BLOADing a picture saved with its palette.

## The specification

Shared facts: [vdp-and-palette.md](../concepts/vdp-and-palette.md#the-palette).

### Interface

- **In:** none (the VRAM palette table) [P A1 RSTPLT]. **Out:** none. AF, BC and DE may change
  [P A1 RSTPLT].

### Behaviour

- The palette := the VRAM palette table [P A1 RSTPLT, 2§2.2 COLOR=RESTORE].
- Which table (one of six places [P A5]; the page; SCREEN 0's two places), the layout read, the bits
  of each value that reach the VDP, and SCREEN 8 are [A].
- Whether a RAM copy of the palette (one GETPLT could read) is updated too is [A].

**Measured** [M] (the same on all three references): RSTPLT loads the VDP's 16 palette registers from the
mode's VRAM table, entry n from bytes 2n / 2n + 1 (a pattern written into the table by hand came out in the VDP's
palette, masked to the VDP's 3-bit fields). Out: F $44, B $00, C $10, D $00, E $00.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) match the palette, the table and GETPLT's source; they differ only in
the registers on return ([scratchpad/AE_xplt_msx2.out](../../scratchpad/AE_xplt_msx2.out)).

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded)
(palette snapshot, port $9A log, whole-RAM diff — the diff locates any RAM copy).

| case | inputs | state | what it separates |
|---|---|---|---|
| RP-01 | — | a distinct palette at each of the six places, SCREEN 0 (40 and 80), 1-7 | which place is read per mode; any RAM copy written |
| RP-02 | — | table bytes with bit 3 / bit 7 set | masked by the call (the port $9A bytes) vs passed and dropped by the VDP |
| RP-03 | — | 48-byte area: bytes 32-47 distinct | whether bytes 32-47 are read |
| RP-04 | — | SCREEN 5, ACPAGE 1, DPPAGE 2, R#2's copy showing page 3; each page's table distinct | page 0 vs active vs DPPAGE vs the displayed page |
| RP-05 | — | RSTPLT; then the VRAM table overwritten through the ports; then GETPLT of each entry | GETPLT reads a RAM copy RSTPLT refreshed vs VRAM live |
| RP-06 | — | SCREEN 8 | palette changed at all |
| RP-07 | — | R#16 preset 9 | written from P#0 vs from the pointer |
| RP-08 | — | interrupts on / off; HL IX IY AF' BC' DE' HL' garbage; the control call | the call's interrupt state vs the path's; registers kept |
| RP-09 | — | FS-A1WSX SCREEN 10-12 | the place in the MSX2+ modes |
| RP-10 | — | a VDP command running (CE = 1) | VRAM read during it vs waits |

## Related pages

[INIPLT](INIPLT.md), [GETPLT](GETPLT.md), [SETPLT](SETPLT.md);
[vdp-and-palette.md](../concepts/vdp-and-palette.md).

## Tests that cover it

None yet.
