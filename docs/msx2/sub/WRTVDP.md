<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `WRTVDP` (sub-ROM $012D) — write a VDP register

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xwv.asm](../../probes/bios/spec/xwv.asm), [scratchpad/AE_xwv_msx2.out](../../scratchpad/AE_xwv_msx2.out), decoded by `scratchpad/xwv_decode.py`).

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

**Measured** [M] (the same on all three references; C 0-27 and 32-46, B = the register's own value XOR $0F):
- Every write is DIRECT: two port $99 writes, B then $80 | C -- never through R#17 / port $9B -- for every C up to 46.
- The copy: C 0-7 -> $F3DF + C; C 8-23 -> $FFE7 + (C - 8); on the FS-A1WSX also C 25-27 -> $FFFA-$FFFC (its V9958's
  registers). C 24 and 28-46 have no copy. (R#15 was written with its own value; R#16's copy not decided by this run.)
- **C 0 writes R#9 too:** R#9 := $12 (NMS 8250, PAL) / $10 (HB-F900, FS-A1WSX: NTSC), with its copy $FFE8 -- four
  port writes.
- Out: A $00, F $44, B and C kept.
- The VDP keeps only its own bits (R#0 $0F -> $0E, R#8 $07 -> $03, R#14 $0F -> $07 ...): the chip's, not the call's;
  C 24-27 on the V9938 (HB-F900, NMS 8250) read back $00 -- the registers do not exist there.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) write every register directly with its copy, but: C 0 does not write R#9;
the MSX2+ build keeps no copy for R#25-R#27; out A = B, F $A0 / $A8, B $00 (the references: A $00, F $44, B kept)
([scratchpad/AE_xwv_msx2.out](../../scratchpad/AE_xwv_msx2.out)).

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
