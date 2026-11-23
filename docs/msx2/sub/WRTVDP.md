<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `WRTVDP` (sub-ROM $012D) — write a VDP register

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`WRTVDP` writes B to VDP register C. On the MSX2 the VDP has registers R#0-R#23 and R#32-R#46,
and RAM copies of R#0-R#23 in two places: RG0SAV-RG7SAV and $FFE7-$FFF6. Whether the call keeps
those copies, and what it does for a register number with no copy or no register, are not
published. The FS-A1WSX's MSX2+ VDP has further registers the handbook does not cover.

## The specification

Shared facts — the register set, the copies, the ports, the recording:
[vdp-and-palette.md](../concepts/vdp-and-palette.md).

### Interface

- **In:** C, the register number; B, the data [P A1 WRTVDP (sub)].
- **Out:** none. AF and BC may change [P A1 WRTVDP (sub)].

### Behaviour

- VDP register C := B [P A1 WRTVDP (sub)]. Direct (port #1) or indirect (R#17, port #3) [P 4§2.1.1]
  is [A].
- The RAM copy: RG0SAV + C for C 0-7, $FFE7 + (C − 8) for C 8-23 [P 4§2.1.1 places the copies; that
  the call updates them is A]. For C 24-31 (no register on the MSX2 VDP [P 4§1.1]) and 32-46 (no
  copy named), what is written is [A]: a linear "RG0SAV + C" rule would write into the system area
  from $F3F7 on, and a "$FFE7 + C − 8" rule into $FFF7 (the main ROM's slot) for C 24
  [P A4 Fig A.5].
- C above 46, and how many bits of C reach the VDP (the handbook prints five [P 4§2.1.1]), are [A].
- What the MSX1 call returns (A = B, B = 0, F from the port write, EI on return:
  [WRTVDP $0047](../../bios/WRTVDP.md)) carrying over is [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded):
R#0-R#46 by snapshot, every port $99 / $9B write logged, the whole of RAM diffed (RG0SAV + C
reaches $F400-$F40D for C 33-46 and $F4DE for C $FF). Each register's preset differs from its
copy's; R#17 and R#15 are preset distinctive.

| case | inputs | state | what it separates |
|---|---|---|---|
| WV-01 | C 0-7, B $5A / $A5 | copies ≠ registers; R#17 $2A | the MSX1 rule carries over; direct write (R#17 unchanged, port #1 only in the log) vs indirect |
| WV-02 | C 8-23, B $5A / $A5 | $FFE7-$FFF6 garbage; R#17 $2A | copy at $FFE7 + C − 8 vs RG0SAV + C vs none; direct vs indirect |
| WV-03 | C 24-31 | per machine: the FS-A1WSX has registers there, the MSX2 machines none | a write anywhere (RAM, $FFF7, $FFFA-$FFFC, the VDP) vs none |
| WV-04 | C 32-45, B $5A; C 46 with B $00 (stop) and B $D0 (HMMM, a harmless rectangle preset in R#32-R#43) | — | command registers written; any RAM copy; C 46 starts a command (S#2 CE, VRAM) |
| WV-05 | C 47-63, $80, $FF | port log | C masked by the call (the port byte) vs passed and dropped by the VDP; RAM written |
| WV-06 | C 9, B with bit 6 set (a bit R#9 does not define [A]) | — | the VDP keeps only the register's bits vs all |
| WV-07 | C 1, B with bit 5 (IE0) set | a VDP interrupt pending | whether the interrupt is taken inside the call (IFF1 in the port log) |
| WV-08 | C 15, B 2 | DI throughout, S#0 non-zero | R#15 left at 2 vs reset to 0 by the call (no ISR can do it) |
| WV-09 | C 16, B 5 | — | palette pointer left; RAM copy at $FFEF |
| WV-10 | C 32 | a VDP command running (CE = 1) | the register written mid-command vs waits |
| WV-11 | — | entry F $00 / $FF; DE HL IX IY AF' BC' DE' HL' garbage; interrupts on / off; the control call | A, B, C, F on return; kept registers; the call's interrupt state vs the path's |

## Related pages

[VDPSTA](VDPSTA.md); the MSX1 call [WRTVDP $0047](../../bios/WRTVDP.md);
[vdp-and-palette.md](../concepts/vdp-and-palette.md).

## Tests that cover it

None yet.
