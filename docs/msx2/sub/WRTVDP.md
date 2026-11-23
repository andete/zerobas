<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `WRTVDP` (sub-ROM $012D) — write a VDP register

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xwv.asm](../../../probes/bios/spec/xwv.asm), [scratchpad/AE_xwv_msx2.out](../../../scratchpad/AE_xwv_msx2.out), decoded by [xwv_decode.py](../../../scratchpad/xwv_decode.py) into [scratchpad/AE_xwv_msx2_decoded.out](../../../scratchpad/AE_xwv_msx2_decoded.out)). "Phase 1" = the first 43 records (two RAM windows); "phase 3" = the 53 records added 2026-11-23 (every C 0-46 plus six C 0 variants, each with a diff of the whole work area $F380-$FFFE and the first eight port $99 bytes).
>
> Goldfish pass 1 (test writer) 2026-11-23: 6 findings, 4 measured, 1 moved to open, 1 corrected in wording (phase 3 added for it).

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

**Measured** [M] (the same on all three references; B = the register's own value XOR $0F unless said):
- Every write is DIRECT: B then $80 | C through port $99, never through R#17 / port $9B -- for every C 0-46
  (phase 1: C 0-27, 32-46; phase 3: C 0-46 including 28-31).
- The copy, from the whole-work-area diff (phase 3): C 0-7 -> $F3DF + C; C 8-23 -> $FFE7 + (C - 8); on the
  FS-A1WSX also C 25-27 -> $FFFA-$FFFC (its V9958's registers). C 24 and 28-46 (and 25-27 on the V9938 machines)
  write NO byte of $F380-$FFFE; in particular "RG0SAV + C" ($F3E7-$F40D) is never written for C >= 8. The other
  bytes the diff shows are the timer interrupt's (JIFFY $FC9E, INTCNT $FCA2, SCNCNT / REPCNT $F3F6 / $F3F7, and
  STATFL $F3E7 in some cases): **an interrupt is taken during the call although the probe enters with DI** -- the
  EXTROM path or the call enables interrupts; which of the two is open (WV-11's control call).
- **C 0 also writes R#9 when B's bit 0 is set** (phase 3: B $0F, $01, $0D yes; $00, $0E no): R#9 := R#9's copy
  ($FFE8) OR $10, and the copy := the same, written BEFORE R#0 (port log `12 89 0F 80`). Copy $02 (NMS 8250) gives
  $12, $00 (HB-F900, FS-A1WSX) $10, a preset copy $80 gives $90 on all three -- so not a per-machine constant and not
  a function of B beyond bit 0.
- Out (phase 1): A $00, F $44, B and C kept.
- The VDP keeps only its own bits (R#0 $0F -> $0E, R#8 $07 -> $03, R#14 $0F -> $07 ...): the chip's, not the call's;
  C 24-31 on the V9938 machines (HB-F900, NMS 8250) and C 24 / 28-31 on the FS-A1WSX read back $00 -- the
  registers do not exist there.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) write every register directly with its copy, but: C 0 never writes R#9
(B bit 0 set or not, phase 3);
the MSX2+ build keeps no copy for R#25-R#27; out A = B, F $A0 / $A8, B $00 (the references: A $00, F $44, B kept)
([scratchpad/AE_xwv_msx2.out](../../../scratchpad/AE_xwv_msx2.out)).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: WRTVDP's results are the FS-A1WSX's, on both models. What differs is the machine and the timing: $FFF8 = $FF, $FFFD-$FFFE = $F054 (CHGCPU's stack cell), VDP R#16 = $0F as the boot leaves it (so phase 3's case C $10 computes B = $00 and changes $FFEF), JIFFY / INTCNT / SCNCNT and power-on cells [M] ([AE_trall/xwv.out](../../../scratchpad/AE_trall/xwv.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded):
R#0-R#46 by snapshot, every port $99 / $9B write logged, the whole of RAM diffed (RG0SAV + C
reaches $F400-$F40D for C 33-46 and $F4DE for C $FF). Each register's preset differs from its
copy's; R#17 and R#15 are preset distinctive.

| case | inputs | state | what it separates |
|---|---|---|---|
| WV-01 | C 0-7, B $5A / $A5 | copies ≠ registers; R#17 $2A | **decided** for B = own value XOR $0F (phase 1 / 3: direct, copy at $F3DF + C, R#17 not used -- two port $99 bytes only); B $5A / $A5 with copies ≠ registers still open |
| WV-02 | C 8-23, B $5A / $A5 | $FFE7-$FFF6 garbage; R#17 $2A | **decided** for B = own value XOR $0F (copy at $FFE7 + C − 8, not RG0SAV + C, direct); B $5A / $A5 with garbage copies still open |
| WV-03 | C 24-31 | per machine: the FS-A1WSX has registers there, the MSX2 machines none | **decided** (phase 3): the VDP write only; no RAM byte in $F380-$FFFE except the FS-A1WSX's $FFFA-$FFFC for C 25-27 |
| WV-04 | C 32-45, B $5A; C 46 with B $00 (stop) and B $D0 (HMMM, a harmless rectangle preset in R#32-R#43) | — | command registers written; any RAM copy; C 46 starts a command (S#2 CE, VRAM) |
| WV-05 | C 47-63, $80, $FF | port log | C masked by the call (the port byte) vs passed and dropped by the VDP; RAM written |
| WV-06 | C 9, B with bit 6 set (a bit R#9 does not define [A]) | — | the VDP keeps only the register's bits vs all |
| WV-07 | C 1, B with bit 5 (IE0) set | a VDP interrupt pending | whether the interrupt is taken inside the call (IFF1 in the port log) |
| WV-08 | C 15, B 2 | DI throughout, S#0 non-zero | R#15 left at 2 vs reset to 0 by the call (no ISR can do it) |
| WV-09 | C 16, B 5 | — | palette pointer left; RAM copy at $FFEF |
| WV-10 | C 32 | a VDP command running (CE = 1) | the register written mid-command vs waits |
| WV-11 | — | entry F $00 / $FF; DE HL IX IY AF' BC' DE' HL' garbage; interrupts on / off; the control call | A, B, C, F on return; kept registers; the call's interrupt state vs the path's |
| WV-12 | C 0, B with bit 0 set together with bits 4-7 (e.g. $11, $F1 -- interrupt enables, so DI and a guard) | R#9's copy $80 / $00 | the R#9 side effect's trigger beyond bit 0 (only $00, $01, $0D, $0E, $0F tried) |

## Related pages

[VDPSTA](VDPSTA.md); the MSX1 call [WRTVDP $0047](../../bios/WRTVDP.md);
[vdp-and-palette.md](../concepts/vdp-and-palette.md).

## Tests that cover it

None yet.
