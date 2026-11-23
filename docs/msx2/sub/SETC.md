<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETC` (sub-ROM $009D) — set the current pixel

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubgc.asm](../../probes/bios/spec/xsubgc.asm), [scratchpad/AE_xsubgc_msx2.out](../../scratchpad/AE_xsubgc_msx2.out), decoded by `scratchpad/xsubgc_decode.py`).

## Summary

`SETC` is assumed to be the sub-ROM's counterpart of the main ROM's [SETC](../../bios/SETC.md)
($0120): it sets the pixel at the current graphics position to ATRBYT. In SCREEN 5-8 the pixel is
a field of one byte, so the MSX1 colour-cell rules fall away; what is new is whether the logical
operation in LOGOPR applies, whether the VDP's PSET command does the work, and which page it lands on.

## The specification

**Interface.**
- No published entry at $009D [P TH A1 SUB-ROM, by absence]; a callable entry is [A] (case SC-00).
- In: CLOC / CMASK as [MAPXYC](MAPXYC.md) left them, ATRBYT ($F3F2) [A, as MSX1; the cell P TH A4].
  Out: the pixel's field := ATRBYT, the rest of the byte kept [A]; layout [P TH 4 §3.6-§3.9].
- LOGOPR ($FB02) [P TH A4]: applied (destination := ATRBYT op destination, T-forms skipping colour
  0, [P TH 4 §6.3]) or ignored -- [A]. The MSX1 SETC has no logical operation.
- If the PSET command is used, the call writes R#36-R#39, R#44, R#45, R#46 [P TH 4 §6.5.11 for the
  command; its use here A]; whether it waits for CE before returning is [A].
- ATRBYT wider than the field: masked, or spilt into the neighbour field (the MSX1 SCREEN 3 SETC
  spills an over-15 ATRBYT into the other nibble, measured there) [A].
- Registers kept and interrupts on after [A, as MSX1].

**Measured** [M] (the same on all three references, ATRBYT from SETATR $0B): the pixel at CLOC / CMASK takes
ATRBYT -- SCREEN 5 / 7: the high nibble for even X ($B0), the low one for odd ($0B); SCREEN 6: 2 bits per pixel, X 0
-> bits 7-6 ($C0), X 1 -> 5-4, X 3 -> 1-0 (ATRBYT $0F there, all ones); SCREEN 8: the byte ($0B). In SCREEN 2 it writes
ATRBYT into the nibble MAPXYC's mask names ($B0 / $0B at $0000).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds write the same in SCREEN 5-8; in SCREEN 2 they write the MASK ($F0 / $0F) where the
references write the colour ($B0 / $0B) ([scratchpad/AE_xsubgc_msx2.out](../../scratchpad/AE_xsubgc_msx2.out)).

## Open (not measured)

The sets [PG], [LG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| SC-00 | — | SCREEN 5, MAPXYC (10, 10), ATRBYT 9 | a callable entry vs not | — | — | — |
| SC-01 | MAPXYC X even / odd | SCREEN 5, byte $A5, ATRBYT 9 | the field written ($95 vs $A9) | — | — | — |
| SC-02 | MAPXYC X 0..3 (one case each) | SCREEN 6, byte $00 and byte $FF, ATRBYT 1 | each 2-bit field: $40 / $10 / $04 / $01 on $00, $7F / $DF / $F7 / $FD on $FF | — | — | — |
| SC-03 | ATRBYT $1A, MAPXYC X odd | SCREEN 5, byte $45 | low nibble masked ($4A) vs ATRBYT ORed in whole ($5A) | — | — | — |
| SC-04 | ATRBYT 5 (over 3), MAPXYC X 1 | SCREEN 6, byte $00 | masked ($10) vs spilt into the neighbour field | — | — | — |
| SC-05 | LOGOPR 0, 1, 2, 3, 4 | SCREEN 5 byte $A5, ATRBYT 9, X even | LOGOPR applied (the high nibble $A becomes $9, $8, $B, $3, $6) vs always $9 | — | — | — |
| SC-06 | [LG]: 8 with ATRBYT 0 and 9; 5, 13, $F3 | SCREEN 5 | T-forms (0 leaves the pixel); undefined codes; the high nibble masked or passed to R#46 | — | — | — |
| SC-07 | ATRBYT $C3 | SCREEN 8, byte $5A | the full byte | — | — | — |
| SC-08 | — | [PG] in SCREEN 5 and 8 | the page written (in SCREEN 8 one of only two cases that show it) | — | — | — |
| SC-09 | — | a command running at entry; R#45 DIX / DIY / MXD garbage | waits for CE; MXD (expansion RAM) honoured or cleared | — | — | — |
| SC-10 | — | [SN] | S#2 on return (returns before its command ends); R#36-R#39, R#44-R#46 residue (PSET used: the pixel's coordinates, ATRBYT, $5x) vs no command in the port log (CPU write) | — | — | — |
| SC-11 | CLOC / CMASK set by hand, unlike MAPXYC's | SCREEN 5 | CLOC / CMASK are the position vs a hidden copy | — | — | — |
| SC-12 | garbage in all registers; DI / EI | each mode | A / F; registers kept; interrupts after | — | — | — |
| SC-13 | — | SCRMOD 2, 3, 4; [MD]; LOGOPR 3 | the MSX1 rules through the sub-ROM, and whether LOGOPR acts there | — | — | — |
| SC-14 | — | SCRMOD 10-12 (FS-A1WSX) | writing in the YJK modes | n/a | n/a | — |
| SC-15 | SC-01, SC-05 inputs | SCREEN 5, called at the main-ROM SETC ($0120) | the main entry forwards in SCREEN 5-8; LOGOPR there | — | — | — |
| SC-16 | MAPXYC (10, 10), ATRBYT 9 | SCREEN 2 with R#25 CMD set and clear (V9958 lets commands run outside the bitmap modes) | whether the MSX2+ sub-ROM uses a command in SCREEN 2 -- per machine, no generation assumed | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [SETC](../../bios/SETC.md);
[SETATR](SETATR.md), [READC](READC.md), [MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
