<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `GETPLT` (sub-ROM $0149) — read a palette entry

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xplt.asm](../../../probes/bios/spec/xplt.asm), [scratchpad/AE_xplt_msx2.out](../../../scratchpad/AE_xplt_msx2.out), decoded by [xplt_decode.py](../../../scratchpad/xplt_decode.py) into [scratchpad/AE_xplt_msx2_decoded.out](../../../scratchpad/AE_xplt_msx2_decoded.out)). `[XP n]` = that run's step n (0-59; 17-59 added 2026-11-23, with R#16 and the VDP's VRAM pointer recorded after every step). The three references agree on every step (the SCREEN 0 / 1 tables differ by font data only).
>
> Goldfish pass 1 (test writer) 2026-11-23: 7 findings, 4 measured, 0 moved to open, 3 corrected in wording (steps 17-40 added for it).

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
- A above 15 is [A]. (C's high nibble and bit 3 of each nibble: Measured, below.)

**Measured** [M] (the same on all three references):
- **GETPLT reads the VRAM table, not the VDP and not a RAM copy**: after the table was overwritten by hand (no call
  in between), GETPLT 5 returned the table's bytes 10 / 11 (B $35, C $3A) [XP 4, 5] -- and the same after RSTPLT
  [XP 7]. The table is the mode's: SCREEN 5 [XP 5], 1 [XP 20], 0 width 40 [XP 25], 0 width 80 [XP 30], 8 [XP 34].
- Entry n is bytes 2n (B: red x 16 + blue) and 2n + 1 (C: green), **unmasked** in both: an all-$FF table gives B
  $FF, C $FF [XP 37], all-$88 gives B $88, C $88 [XP 40]. Two bytes are read: the VRAM pointer after is the
  table + 2n + 3 (2 bytes plus the VDP's read-ahead) [XP 5, 20, 25, 30, 34].
- Out: A = C; **D := A, the palette number** (D entered $00 and $C3, came back $05 [XP 3, 20]); E kept ($00 / $3C
  [XP 3, 20]); F $34 in SCREEN 5 but $30 / $10 / $1C / $3C in SCREEN 1 / 0-40 / 0-80 / 8 [XP 20, 25, 30, 34]: F is
  not a constant of the call.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) match the palette, the table and GETPLT's source in SCREEN 0 width 80, 1,
5 and 8, but **in SCREEN 0 width 40 they use $0F00 (the width-80 place) instead of $0400**: INIPLT and SETPLT write
$0F00 and leave $0400, RSTPLT and GETPLT read $0F00 [XP 11, 24-26] (the first DRAFT 1 text said "they differ only in
the registers on return": step 11 already showed $0400 unwritten). Registers on return: D kept (the references D := A).
([scratchpad/AE_xplt_msx2.out](../../../scratchpad/AE_xplt_msx2.out)).

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded).
"A RAM copy" means the one SETPLT's / RSTPLT's whole-RAM diffs locate (SP-01, RP-01); those run
first, and GETPLT's cases then preset that copy distinct from the VDP, the VRAM table and the
power-on table.

| case | inputs | state | what it separates |
|---|---|---|---|
| GL-01 | A 0, 7, 15 | VDP palette, VRAM table, any RAM copy each different, none the power-on table | the source: VRAM table vs RAM copy vs the power-on table |
| GL-02 | A 5 | SETPLT 5; then VRAM entry 5 overwritten through the ports | **decided** [XP 2-5]: the VRAM table read live |
| GL-03 | A 5 | after a port #2 write only | sees it (impossible unless snooped) vs not |
| GL-04 | A 5 | each of the six table places distinct; SCREEN 0 (40 and 80), 1-7 | the mode picks the table (0 / 40, 0 / 80, 1, 5, 8 measured; 2, 3, 4, 6, 7 open) |
| GL-05 | A 16, $FF | VRAM after the 48-byte area (and before it) preset distinct | masked to 4 bits vs an out-of-table read |
| GL-06 | A 5 | table byte with bits 3 / 7 set | **decided** [XP 37, 40]: as stored, unmasked |
| GL-07 | — | C, HL, IX, IY, AF' BC' DE' HL', entry F garbage | C's high nibble (decided: the table byte's [XP 37]); D := A, E kept (decided [XP 20]); HL IX IY and the alternates still open |
| GL-08 | A 5 | SCREEN 5, ACPAGE 1, DPPAGE 2, R#2's copy page 3; each page's table distinct | the page read |
| GL-09 | — | interrupts on / off; the control call | the call's interrupt state vs the path's |
| GL-10 | A 5 | a VDP command running (CE = 1) | VRAM read during it vs waits |

## Related pages

[SETPLT](SETPLT.md), [INIPLT](INIPLT.md), [RSTPLT](RSTPLT.md);
[vdp-and-palette.md](../concepts/vdp-and-palette.md).

## Tests that cover it

None yet.
