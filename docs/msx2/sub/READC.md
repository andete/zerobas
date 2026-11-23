<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `READC` (sub-ROM $0095) — read the colour of the current pixel

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubgc.asm](../../../probes/bios/spec/xsubgc.asm), [scratchpad/AE_xsubgc_msx2.out](../../../scratchpad/AE_xsubgc_msx2.out), decoded by `scratchpad/xsubgc_decode.py`; the separating cases [xsubgc2.asm](../../../probes/bios/spec/xsubgc2.asm), [scratchpad/AE_xsubgc2_msx2.out](../../../scratchpad/AE_xsubgc2_msx2.out), decoded by [scratchpad/xsubgc2_decode.py](../../../scratchpad/xsubgc2_decode.py) into [scratchpad/AE_xsubgc2_msx2_decoded.out](../../../scratchpad/AE_xsubgc2_msx2_decoded.out)). `[G1]` = the first run, `[G2 Pnn]` / `[G2 STATE]` = the second run's records.
>
> Goldfish pass 1 (test writer) 2026-11-23: 5 findings, 4 measured, 0 moved to open, 1 corrected (stale cells).

## Summary

`READC` is assumed to be the sub-ROM's counterpart of the main ROM's [READC](../../bios/READC.md)
($011D): it returns in A the colour of the pixel at the current graphics position. In SCREEN 5-8 that
is a nibble, two bits or a byte of the pixel's byte, read either by the CPU or with the VDP's POINT
command; which one, and how the position is held, is not published.

## The specification

**Interface.**
- No published entry at $0095 [P TH A1 SUB-ROM, by absence]; a callable entry on all three references [M] (case RD-00).
- In: CLOC / CMASK, as [MAPXYC](MAPXYC.md) left them [A]. Out: A, the colour: 0-15 (SCREEN 5, 7),
  0-3 (6), 0-255 (8) [M, below]; the pixel layout is [P TH 4 §3.6-§3.9].
- If the POINT command is used, its result comes from S#7 and the call writes R#32-R#35, R#45,
  R#46 [P TH 4 §6.5.12 for the command; its use here A].
- ACPAGE's part: [A]. Changes nothing else [A, as MSX1]; interrupts after: [A] (MSX1: on).

**Measured** [M] (the same on all three references; CHGMOD's state: LOGOPR 0, ACPAGE 0, LN 1 in SCREEN 5-8, no
command running [G2 STATE]): **READC returns the pixel's field from VRAM**, right-aligned -- not ATRBYT, not a copy of
the last SETC. Planted bytes read with no SETC before, ATRBYT set to something else (the decoded file's `READC1`):
- SCREEN 5, byte $A5 with ATRBYT 9: X even $0A, X odd $05 [G2 P01, P02]. SCREEN 7 at X 300 / 301: $0A / $05
  [G2 P09, P10] (X past 255 reaches the byte X / 2).
- SCREEN 6, byte $1B (fields 00 01 10 11) with ATRBYT 1: X 0..3 give $00, $01, $02, $03 [G2 P04-P07].
- SCREEN 8, byte $C3 with ATRBYT $5A: $C3 [G2 P11].
- SCREEN 2, 3, 4 (the multicolour form, [MAPXYC](MAPXYC.md)), byte $A5 at CLOC: CMASK $F0 gives $0A, $0F gives $05
  [G2 P12-P29].
- After SETC, READC returns what SETC wrote: $0B in SCREEN 2, 5, 7, 8 and $03 in SCREEN 6 [G1]; ATRBYT $1A written
  into a low nibble reads back $0A [G2 P03].
- READC leaves the byte as it was (the decoded `byte(after READC1)` is the planted byte in every case).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds return the same in SCREEN 3 and 5-8. **In SCREEN 2 and 4 they return $00 for a
planted $A5** where the references return the nibble ($0A / $05) [G2 P12-P25, P28, P29], and ATRBYT ($09 / $0B) after
their own SETC -- their SCREEN 2 / 4 READC does not read the multicolour nibble
([scratchpad/AE_xsubgc_msx2.out](../../../scratchpad/AE_xsubgc_msx2.out),
[scratchpad/AE_xsubgc2_msx2_decoded.out](../../../scratchpad/AE_xsubgc2_msx2_decoded.out)).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: xsubgc gives the same bytes as on the FS-A1WSX, on both models; xsubgc2 too, except R#36 = $80 (the boot's last VDP command) and VDP S#2 (read at a random moment) in its state records [M] ([AE_trall/xsubgc.out](../../../scratchpad/AE_trall/xsubgc.out), [AE_trall/xsubgc2.out](../../../scratchpad/AE_trall/xsubgc2.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

The sets [PG], [LG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| RD-00 | — | SCREEN 5, CLOC / CMASK from MAPXYC (10, 10) | a callable entry vs not | [M] callable [G1] | [M] callable | [M] callable |
| RD-01 | MAPXYC (X even / odd, Y 7) | SCREEN 5, byte $A5 there, ATRBYT 9, no SETC before | the nibble read ($A vs $5): the cursor model's mask; the pixel vs ATRBYT | [M] $0A / $05 [G2 P01, P02] | [M] same | [M] same |
| RD-02 | MAPXYC X 0..3 | SCREEN 6, byte $1B, ATRBYT 1, no SETC before | each 2-bit field (0, 1, 2, 3) | [M] 0, 1, 2, 3 [G2 P04-P07] | [M] same | [M] same |
| RD-03 | MAPXYC (300, 7) | SCREEN 7 vs 5 | X past 255 | [M] SCREEN 7: $0A / $05 at X 300 / 301 [G2 P09, P10]; SCREEN 5 (planted) — | [M] same | [M] same |
| RD-04 | MAPXYC (9, 9) | SCREEN 8, byte $C3, ATRBYT $5A, no SETC before | the full byte | [M] $C3 [G2 P11] | [M] same | [M] same |
| RD-05 | CLOC / CMASK set by hand, unlike any MAPXYC result | SCREEN 5 | whether READC uses CLOC / CMASK or a hidden copy of the coordinates | — | — | — |
| RD-06 | MAPXYC (10, 10) | [PG] in SCREEN 5 and 8, each page's byte different | the page read: ACPAGE, DPPAGE or page 0 (in SCREEN 8 the only case that shows it) | — | — | — |
| RD-07 | — | a command running at entry; S#7 garbage; [SN] | POINT used (waits, S#7 changes, R#32-R#35 / R#45 / R#46 residue = the pixel's coordinates and $40) vs CPU read (no command in the port log) | — | — | — |
| RD-08 | — | R#45 with MXS set (expansion RAM) | MXS cleared by the call vs left (the read then comes from expansion RAM) | — | — | — |
| RD-09 | garbage in all registers, F; DI / EI | SCREEN 5 | A's flags, registers kept, the interrupt state | — | — | — |
| RD-10 | — | SCRMOD 2, 3, 4; [MD] | the MSX1 rules through the sub-ROM | [M] not the MSX1 rule: the multicolour nibble in all three [G2 P12-P29]; [MD] — | [M] same | [M] same |
| RD-11 | — | SCRMOD 10-12 (FS-A1WSX) | the value returned in the YJK modes | n/a | n/a | — |
| RD-12 | MAPXYC (10, 10) | SCREEN 5, called at the main-ROM READC ($011D) | the main entry forwards in SCREEN 5-8 | — | — | — |
| RD-13 | MAPXYC (10, 10) | SCREEN 2 with R#25 CMD set and clear | POINT in a non-bitmap mode on the V9958 -- per machine (on the V9938 there is no R#25: the MSX2 rows are the baseline) | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [READC](../../bios/READC.md);
[MAPXYC](MAPXYC.md), [SETC](SETC.md), [SCANR](SCANR.md) / [SCANL](SCANL.md).

## Tests that cover it

None yet.
