<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETC` (sub-ROM $009D) — set the current pixel

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubgc.asm](../../../probes/bios/spec/xsubgc.asm), [scratchpad/AE_xsubgc_msx2.out](../../../scratchpad/AE_xsubgc_msx2.out), decoded by `scratchpad/xsubgc_decode.py`; the separating cases [xsubgc2.asm](../../../probes/bios/spec/xsubgc2.asm), [scratchpad/AE_xsubgc2_msx2.out](../../../scratchpad/AE_xsubgc2_msx2.out), decoded by [scratchpad/xsubgc2_decode.py](../../../scratchpad/xsubgc2_decode.py) into [scratchpad/AE_xsubgc2_msx2_decoded.out](../../../scratchpad/AE_xsubgc2_msx2_decoded.out)). `[G1]` = the first run, `[G2 Pnn]` / `[G2 STATE]` = the second run's records.
>
> Goldfish pass 1 (test writer) 2026-11-23: 7 findings, 7 measured (LOGOPR: cases P42-P49 added for it), 0 moved to open.

## Summary

`SETC` is assumed to be the sub-ROM's counterpart of the main ROM's [SETC](../../bios/SETC.md)
($0120): it sets the pixel at the current graphics position to ATRBYT. In SCREEN 5-8 the pixel is
a field of one byte, so the MSX1 colour-cell rules fall away; what is new is whether the logical
operation in LOGOPR applies, whether the VDP's PSET command does the work, and which page it lands on.

## The specification

**Interface.**
- No published entry at $009D [P TH A1 SUB-ROM, by absence]; a callable entry on all three references [M] (case SC-00).
- In: CLOC / CMASK as [MAPXYC](MAPXYC.md) left them, ATRBYT ($F3F2) [A, as MSX1; the cell P TH A4].
  Out: the pixel's field := ATRBYT, the rest of the byte kept [A]; layout [P TH 4 §3.6-§3.9].
- LOGOPR ($FB02) [P TH A4]: applied in SCREEN 5 / 8 (destination := ATRBYT op destination, the T-form skipping
  colour 0, [P TH 4 §6.3]); ignored in SCREEN 2 [M, below]. The MSX1 SETC has no logical operation.
- If the PSET command is used, the call writes R#36-R#39, R#44, R#45, R#46 [P TH 4 §6.5.11 for the
  command; its use here A]; whether it waits for CE before returning is [A].
- ATRBYT wider than the field: masked [M, below] (the MSX1 SCREEN 3 SETC spills an over-15 ATRBYT into the other
  nibble, measured there).
- Registers kept and interrupts on after [A, as MSX1].

**Measured** [M] (the same on all three references; all at CHGMOD's state: **LOGOPR 0 (IMP)**, ACPAGE 0, LN 1 in
SCREEN 5-8, no command running [G2 STATE]): **the pixel's field is REPLACED by ATRBYT masked to the field width; the
rest of the byte is kept.** On a non-zero byte (ATRBYT planted by hand) [G2]:
- SCREEN 5, byte $A5, ATRBYT 9: X even $95, X odd $A9 [G2 P01, P02] (OR would give $B5 / $AD). ATRBYT $1A on byte
  $45, X odd: **$4A** -- masked; not "clear the field, OR the whole ATRBYT" ($5A), not "OR the field" ($5F) [G2 P03].
- SCREEN 6, byte $1B, ATRBYT 1: X 0..3 give $5B, $1B, $17, $19 [G2 P04-P07]; ATRBYT 5 at X 1 on $00 gives $10
  (masked to 2 bits, not spilt) [G2 P08].
- SCREEN 7, byte $A5, ATRBYT 9 at X 300 / 301: $95 / $A9 at the byte X / 2 + 256 Y [G2 P09, P10].
- SCREEN 8, byte $C3, ATRBYT $5A: $5A [G2 P11].
- SCREEN 2, 3, 4 (the multicolour form): the nibble CMASK names at CLOC, read back at CLOC away from $0000 too:
  $A5 -> $95 at $022C (CMASK $F0), $A9 at $07FF ($0F) [G2 P12, P13]; the same with MLTCGP $1000 as the base and in
  SCREEN 3 / 4 [G2 P14-P29].
- On a zeroed byte, ATRBYT from SETATR $0B [G1]: SCREEN 5 / 7 $B0 / $0B; SCREEN 6 $C0 / $30 / $03 for X 0 / 1 / 3
  (ATRBYT $0F there: [SETATR](SETATR.md)'s SCREEN 6 transform); SCREEN 8 $0B.

**LOGOPR applies in SCREEN 5 and 8, and not in SCREEN 2** (LOGOPR planted, byte $A5, ATRBYT 9, X even, SCREEN 5)
[G2 P42-P49]: 1 (AND) $85, 2 (OR) $B5, 3 (EOR) $35, 4 (NOT) $65 -- the high nibble $A op 9; 8 (TIMP) with ATRBYT 0
leaves $A5, with ATRBYT 9 gives $95. SCREEN 8, EOR: $C3 EOR $5A = $99. SCREEN 2 at LOGOPR 3: $95, as IMP. So
"replace" above is IMP, the LOGOPR CHGMOD leaves.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds write the same in SCREEN 3, and in SCREEN 5-8 at LOGOPR 0. **They ignore LOGOPR in
SCREEN 5 / 8**: AND, OR, EOR, NOT all give $95 where the references give $85 / $B5 / $35 / $65, TIMP with ATRBYT 0 writes $05 where the references leave $A5, and SCREEN 8 EOR writes $5A for $99 [G2 P42-P48].
**In SCREEN 2 and 4 they OR the MASK into the
byte** ($00 -> $F0 / $0F [G1]; $A5 -> $F5 / $AF [G2 P12-P25, P28, P29]) where the references replace the nibble with
the colour ($B0 / $0B; $95 / $A9) ([scratchpad/AE_xsubgc_msx2.out](../../../scratchpad/AE_xsubgc_msx2.out),
[scratchpad/AE_xsubgc2_msx2_decoded.out](../../../scratchpad/AE_xsubgc2_msx2_decoded.out)).

## Open (not measured)

The sets [PG], [LG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| SC-00 | — | SCREEN 5, MAPXYC (10, 10), ATRBYT 9 | a callable entry vs not | [M] callable [G1] | [M] callable | [M] callable |
| SC-01 | MAPXYC X even / odd | SCREEN 5, byte $A5, ATRBYT 9 | the field written ($95 vs $A9); replace vs OR | [M] $95 / $A9: replace [G2 P01, P02] | [M] same | [M] same |
| SC-02 | MAPXYC X 0..3 (one case each) | SCREEN 6, byte $00 and byte $FF, ATRBYT 1 | each 2-bit field: $40 / $10 / $04 / $01 on $00, $7F / $DF / $F7 / $FD on $FF | [M] on $1B instead: $5B / $1B / $17 / $19 [G2 P04-P07]; $00 / $FF — | [M] same | [M] same |
| SC-03 | ATRBYT $1A, MAPXYC X odd | SCREEN 5, byte $45 | low nibble masked ($4A) vs the field cleared and ATRBYT ORed in whole ($5A) vs ORed into the field ($5F) | [M] $4A: masked [G2 P03] | [M] same | [M] same |
| SC-04 | ATRBYT 5 (over 3), MAPXYC X 1 | SCREEN 6, byte $00 | masked ($10) vs spilt into the neighbour field | [M] $10: masked [G2 P08] | [M] same | [M] same |
| SC-05 | LOGOPR 0, 1, 2, 3, 4 | SCREEN 5 byte $A5, ATRBYT 9, X even | LOGOPR applied (the high nibble $A becomes $9, $8, $B, $3, $6) vs always $9 | [M] applied: $95, $85, $B5, $35, $65 [G2 P01, P42-P45] | [M] same | [M] same |
| SC-06 | [LG]: 8 with ATRBYT 0 and 9; 5, 13, $F3 | SCREEN 5 | T-forms (0 leaves the pixel); undefined codes; the high nibble masked or passed to R#46 | [M] 8: ATRBYT 0 leaves $A5, 9 gives $95 [G2 P46, P47]; 5, 13, $F3 — | [M] same | [M] same |
| SC-07 | ATRBYT $C3 | SCREEN 8, byte $5A | the full byte | [M] (mirror case: ATRBYT $5A on $C3) $5A; EOR $99 [G2 P11, P48] | [M] same | [M] same |
| SC-08 | — | [PG] in SCREEN 5 and 8 | the page written (in SCREEN 8 one of only two cases that show it) | — | — | — |
| SC-09 | — | a command running at entry; R#45 DIX / DIY / MXD garbage | waits for CE; MXD (expansion RAM) honoured or cleared | — | — | — |
| SC-10 | — | [SN] | S#2 on return (returns before its command ends); R#36-R#39, R#44-R#46 residue (PSET used: the pixel's coordinates, ATRBYT, $5x) vs no command in the port log (CPU write) | — | — | — |
| SC-11 | CLOC / CMASK set by hand, unlike MAPXYC's | SCREEN 5 | CLOC / CMASK are the position vs a hidden copy | — | — | — |
| SC-12 | garbage in all registers; DI / EI | each mode | A / F; registers kept; interrupts after | — | — | — |
| SC-13 | — | SCRMOD 2, 3, 4; [MD]; LOGOPR 3 | the MSX1 rules through the sub-ROM, and whether LOGOPR acts there | [M] not the MSX1 rule: the multicolour nibble replaced, at CLOC $022C / $07FF too [G2 P12-P29]; LOGOPR 3 ignored in SCREEN 2 [G2 P49]; [MD] — | [M] same | [M] same |
| SC-14 | — | SCRMOD 10-12 (FS-A1WSX) | writing in the YJK modes | n/a | n/a | — |
| SC-15 | SC-01, SC-05 inputs | SCREEN 5, called at the main-ROM SETC ($0120) | the main entry forwards in SCREEN 5-8; LOGOPR there | — | — | — |
| SC-16 | MAPXYC (10, 10), ATRBYT 9 | SCREEN 2 with R#25 CMD set and clear (V9958 lets commands run outside the bitmap modes) | whether the MSX2+ sub-ROM uses a command in SCREEN 2 -- per machine, no generation assumed | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [SETC](../../bios/SETC.md);
[SETATR](SETATR.md), [READC](READC.md), [MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
