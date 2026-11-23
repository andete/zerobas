<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETPLT` (sub-ROM $014D) — set a palette entry

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`SETPLT` sets palette entry D to the colour given as red and blue in A and green in E. Whether it
also updates the VRAM palette table or a RAM copy — so that GETPLT and RSTPLT see the change — is
not published.

## The specification

Shared facts: [vdp-and-palette.md](../concepts/vdp-and-palette.md#the-palette).

### Interface

- **In:** D, the palette number, 0 to 15; A's high nibble red, A's low nibble blue; E's low nibble
  green [P A1 SETPLT].
- **Out:** none. Only AF changes [P A1 SETPLT].

### Behaviour

- P#D := the colour [P A1 SETPLT]; through R#16 and port #2 [P 4§2.1.2 for the port; that the call
  uses it is A].
- The VRAM table or a RAM copy updated too, D above 15, the nibbles' bit 3, E's high nibble, SCREEN
  8 (BASIC's `COLOR=` does nothing there [P 2§2.2]), and R#16 afterwards are [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded)
(palette snapshot, port $99 / $9A log, the whole of RAM and the six table places diffed).

| case | inputs | state | what it separates |
|---|---|---|---|
| SP-01 | D 0, 7, 15; A $5A, E $03 | — | the VDP gets red 5 / blue 2 / green 3 (A's nibble order); any RAM copy written (the diff) |
| SP-02 | D 7 | each of the six table places distinct; SCREEN 0 (40 and 80), 1-7 | the mode's VRAM table updated vs not; the bytes written |
| SP-03 | D 7, then VRAM entry 7 overwritten through the ports, then GETPLT 7 | — | GETPLT reads VRAM live vs a RAM copy SETPLT kept |
| SP-04 | D 16, $FF | port log | masked by the call (the R#16 byte) vs passed and dropped by the VDP; anything written past the table |
| SP-05 | A $FF, E $FF | port log | bit 3 / E's high nibble dropped by the call vs by the VDP; stored in the table as given vs masked |
| SP-06 | D 7 | SCREEN 8 | VDP written; table written |
| SP-07 | D 7 | SCREEN 5, ACPAGE 1, DPPAGE 2, R#2's copy page 3; each page's table distinct | the page's table |
| SP-08 | D 7; D 15 | R#16 preset 3 | R#16 left at D + 1 (8; 0 after the wrap) vs restored to 3 |
| SP-09 | — | BC, DE, HL, IX, IY, AF' BC' DE' HL', entry F garbage; interrupts on / off; the control call | registers kept; the call's interrupt state vs the path's |
| SP-10 | D 7 | a VDP command running (CE = 1) | VRAM written during it vs waits |

## Related pages

[GETPLT](GETPLT.md), [INIPLT](INIPLT.md), [RSTPLT](RSTPLT.md);
[vdp-and-palette.md](../concepts/vdp-and-palette.md).

## Tests that cover it

None yet.
