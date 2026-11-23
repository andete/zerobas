<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `GETPLT` (sub-ROM $0149) — read a palette entry

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xplt.asm](../../../probes/bios/spec/xplt.asm), [scratchpad/AE_xplt_msx2.out](../../../scratchpad/AE_xplt_msx2.out), decoded by `scratchpad/xplt_decode.py`).

## Summary

`GETPLT` returns palette entry A's colour: red and blue in B, green in C. The VDP's palette
registers cannot be read by the CPU, so the call must read a copy — the VRAM palette table or
RAM; the handbook does not say which.

## The specification

Shared facts: [vdp-and-palette.md](../concepts/vdp-and-palette.md#the-palette).

### Interface

- **In:** A, the palette number, 0 to 15 [P A1 GETPLT].
- **Out:** B's high nibble red, B's low nibble blue, C's low nibble green [P A1 GETPLT]. AF and DE
  may change [P A1 GETPLT] (B and C are the outputs).

### Behaviour

- The source is a copy, since port #2 is write-only [P 4§1.3]; which copy is [A].
- C's high nibble, bit 3 of each nibble, and A above 15 are [A].

**Measured** [M] (the same on all three references): **GETPLT reads the VRAM table, not the VDP**: after the
table was overwritten by hand, GETPLT 5 returned the table's bytes 10 / 11 (B $35, C $3A) -- and the same after
RSTPLT. Entry n is bytes 2n (B: red x 16 + blue) and 2n + 1 (C: green), unmasked. Out: A = C, F $34, D kept, E $00.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) match the palette, the table and GETPLT's source; they differ only in
the registers on return ([scratchpad/AE_xplt_msx2.out](../../../scratchpad/AE_xplt_msx2.out)).

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded).
"A RAM copy" means the one SETPLT's / RSTPLT's whole-RAM diffs locate (SP-01, RP-01); those run
first, and GETPLT's cases then preset that copy distinct from the VDP, the VRAM table and the
power-on table.

| case | inputs | state | what it separates |
|---|---|---|---|
| GL-01 | A 0, 7, 15 | VDP palette, VRAM table, any RAM copy each different, none the power-on table | the source: VRAM table vs RAM copy vs the power-on table |
| GL-02 | A 5 | SETPLT 5; then VRAM entry 5 overwritten through the ports | the VRAM table read live vs a RAM copy SETPLT kept |
| GL-03 | A 5 | after a port #2 write only | sees it (impossible unless snooped) vs not |
| GL-04 | A 5 | each of the six table places distinct; SCREEN 0 (40 and 80), 1-7 | the mode picks the table |
| GL-05 | A 16, $FF | VRAM after the 48-byte area (and before it) preset distinct | masked to 4 bits vs an out-of-table read |
| GL-06 | A 5 | table byte with bits 3 / 7 set | the nibbles masked vs as stored |
| GL-07 | — | C, HL, IX, IY, AF' BC' DE' HL', entry F garbage | C's high nibble; registers kept; F |
| GL-08 | A 5 | SCREEN 5, ACPAGE 1, DPPAGE 2, R#2's copy page 3; each page's table distinct | the page read |
| GL-09 | — | interrupts on / off; the control call | the call's interrupt state vs the path's |
| GL-10 | A 5 | a VDP command running (CE = 1) | VRAM read during it vs waits |

## Related pages

[SETPLT](SETPLT.md), [INIPLT](INIPLT.md), [RSTPLT](RSTPLT.md);
[vdp-and-palette.md](../concepts/vdp-and-palette.md).

## Tests that cover it

None yet.
