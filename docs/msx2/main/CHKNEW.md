<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CHKNEW` ($0165) — is the screen in one of the MSX2's new modes?

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX (identical on all three;
> [xchknew.asm](../../../probes/bios/spec/xchknew.asm), [scratchpad/AE_xchknew_msx2.out](../../../scratchpad/AE_xchknew_msx2.out),
> decoded by `scratchpad/xchknew_decode.py`).
> Goldfish pass 1 (test writer) 2026-11-23: 3 findings, 2 measured (SCRMOD $FF, entry A varied: cases 33-36), 1
> citation corrected.

## Summary

`CHKNEW` is an MSX2 jump-table entry the handbook does not list. It answers "is the screen mode 5 or
higher?" in the carry flag: it compares SCRMOD with 5, exactly as `CP 5` would with SCRMOD in A, and
leaves A and every other register as they were. Carry set = SCREEN 0-4, carry clear = SCREEN 5 and up.
It reads SCRMOD only, not the VDP or its register save cells.

## The specification

**Interface.** None published (absent from App. 1's MSX2 entries) [A].

**Measured** [M] (case numbers are the decoder's; entry A $A7 in cases 0-33, $00 / $05 / $FF in 34-36, F $00 and $FF,
every other register loaded with distinct values; identical on all three references):
- **F = the flags of SCRMOD - 5** (the flags `CP 5` leaves, undocumented bits 5 and 3 included): SCREEN 0 (width 40
  and 80), 1, 2, 3, 4 give F $93 -- **carry set**, Z clear, S set; SCREEN 5 gives $42 -- carry clear, **Z set**; SCREEN
  6, 7, 8 give $02 -- carry and Z clear [M 0-18]. Out-of-range SCRMOD values follow the same subtraction: 9, 10, 11, 12
  give $02, $10 gives $12, $80 gives $16 (P/V set: the signed overflow of $80 - 5), $FF gives $82 (S set, carry
clear: an unsigned compare, $FF is not "below 5") [M 23, 24, 26-28, 32, 33].
- **The entry F is not used:** F $00 and $FF give the same result in every mode [M 0-17].
- **A is kept** -- $A7, $00, $05, $FF all come back unchanged -- and the result does not depend on it (A $00 / $FF over
SCREEN 1 give $93, A $05 over SCREEN 5 gives $42, as A $A7 does); BC, DE, HL, IX, IY and the alternate set kept
[M 0-36].
- **It reads SCRMOD ($FCAF), nothing else:** the VDP in SCREEN 1 with SCRMOD 5 answers $42 (case 19), the VDP in
  SCREEN 5 with SCRMOD 1 answers $93 (case 20), SCRMOD 4 over a SCREEN 1 VDP answers $93 (case 31); RG0SAV / RG1SAV
  set to the other mode's values change nothing (cases 21, 22) [M 19-22, 31].
- SCRMOD is not written [M 0-36]. The interrupt state is kept: off stays off, on stays on (cases 29, 30) [M 0-36].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) give the same F in every case, but **return A = SCRMOD** where the
references keep A [M 0-36] (with entry A $05 over SCREEN 5 the two coincide, case 35). A caller that relies on A surviving the call gets a different A on C-BIOS.

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every byte a case writes is as on the FS-A1WSX, on both models; the only difference is the capture's last byte, which no case writes (power-on RAM) [M] ([AE_trall/xchknew.out](../../../scratchpad/AE_trall/xchknew.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

- SCRMOD 10-12 set up for real on the FS-A1WSX (SCREEN 10-12 with the V9958's YJK bits): only the bare SCRMOD values
  were measured, over a SCREEN 1 VDP (cases 26-28, $02); that a real SCREEN 10-12 answers the same [A].
- Stack depth and time.

## Related pages

[region page](README.md); [screen modes](../../concepts/screen-modes.md).

## Tests that cover it

None yet.
