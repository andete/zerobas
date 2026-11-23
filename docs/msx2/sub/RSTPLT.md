<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `RSTPLT` (sub-ROM $0145) — load the palette from VRAM

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xplt.asm](../../../probes/bios/spec/xplt.asm), [scratchpad/AE_xplt_msx2.out](../../../scratchpad/AE_xplt_msx2.out), decoded by [xplt_decode.py](../../../scratchpad/xplt_decode.py) into [scratchpad/AE_xplt_msx2_decoded.out](../../../scratchpad/AE_xplt_msx2_decoded.out)). `[XP n]` = that run's step n (0-59; 17-59 added 2026-11-23, with R#16 and the VDP's VRAM pointer recorded after every step). The three references agree on every step (the SCREEN 0 / 1 tables differ by font data only).
>
> Goldfish pass 1 (test writer) 2026-11-23: 4 findings, 3 measured, 0 moved to open, 1 corrected in wording (steps 17-38 added for it).

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

**Measured** [M] (the same on all three references):
- RSTPLT loads the VDP's 16 palette registers from the mode's VRAM table, entry n from bytes 2n / 2n + 1 (a pattern
  written into the table by hand came out in the VDP's palette, masked to the VDP's 3-bit fields): SCREEN 5
  [XP 6], 1 [XP 19], 0 width 40 [XP 24], 0 width 80 [XP 29], 8 [XP 33] (so SCREEN 8 is not skipped).
- **It reads exactly 32 bytes:** the VDP's VRAM pointer after the call is the table + 33 in every mode -- 32 bytes
  plus the VDP's one-byte read-ahead (GETPLT's 2-byte read leaves + 2n + 3 the same way) [XP 6, 19, 24, 29, 33,
  38]. A on return is byte 31, the last byte read ($9E of the pattern, $FF of an all-$FF table) [XP 6, 38].
- Bits 3 / 7 of the table bytes do not reach the palette: an all-$FF table gives 7 / 7 / 7 in every entry
  [XP 38]; whether the call masks them or the VDP drops them needs the port $9A log (RP-02).
- R#16 is 0 after the call and the palette comes out in order although R#16 was 6 before [XP 5, 6].
- Out: F $44, B $00, C $10, D := $00 (entered $00 and $C3 [XP 6, 19]), E kept ($00 / $3C [XP 6, 19]).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) match the palette, the table and GETPLT's source in SCREEN 0 width 80, 1,
5 and 8, but **in SCREEN 0 width 40 they use $0F00 (the width-80 place) instead of $0400**: INIPLT and SETPLT write
$0F00 and leave $0400, RSTPLT and GETPLT read $0F00 [XP 11, 24-26] (the first DRAFT 1 text said "they differ only in
the registers on return": step 11 already showed $0400 unwritten). Registers on return: F $A8 and D kept (the references F $44, D := 0).
([scratchpad/AE_xplt_msx2.out](../../../scratchpad/AE_xplt_msx2.out)).

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded)
(palette snapshot, port $9A log, whole-RAM diff — the diff locates any RAM copy).

| case | inputs | state | what it separates |
|---|---|---|---|
| RP-01 | — | a distinct palette at each of the six places, SCREEN 0 (40 and 80), 1-7 | which place is read per mode (0 / 40, 0 / 80, 1, 5, 8 measured; 2, 3, 4, 6, 7 open); any RAM copy written |
| RP-02 | — | table bytes with bit 3 / bit 7 set | masked by the call (the port $9A bytes) vs passed and dropped by the VDP |
| RP-03 | — | 48-byte area: bytes 32-47 distinct | **decided** [XP 6, 19, 24, 29, 33]: 32 bytes (the VRAM pointer; A = byte 31) |
| RP-04 | — | SCREEN 5, ACPAGE 1, DPPAGE 2, R#2's copy showing page 3; each page's table distinct | page 0 vs active vs DPPAGE vs the displayed page |
| RP-05 | — | RSTPLT; then the VRAM table overwritten through the ports; then GETPLT of each entry | **decided** for entry 5 [XP 4, 5, 6, 7]: GETPLT reads VRAM live, before and after RSTPLT |
| RP-06 | — | SCREEN 8 | **decided** [XP 33]: the palette is loaded from $FA80 |
| RP-07 | — | R#16 preset 9 | **decided** with R#16 6 before [XP 5, 6]: from P#0, R#16 0 after |
| RP-08 | — | interrupts on / off; HL IX IY AF' BC' DE' HL' garbage; the control call | the call's interrupt state vs the path's; registers kept (D / E decided [XP 19]: D := 0, E kept) |
| RP-09 | — | FS-A1WSX SCREEN 10-12 | the place in the MSX2+ modes |
| RP-10 | — | a VDP command running (CE = 1) | VRAM read during it vs waits |

## Related pages

[INIPLT](INIPLT.md), [GETPLT](GETPLT.md), [SETPLT](SETPLT.md);
[vdp-and-palette.md](../concepts/vdp-and-palette.md).

## Tests that cover it

None yet.
