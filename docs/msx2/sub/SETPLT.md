<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETPLT` (sub-ROM $014D) — set a palette entry

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xplt.asm](../../../probes/bios/spec/xplt.asm), [scratchpad/AE_xplt_msx2.out](../../../scratchpad/AE_xplt_msx2.out), decoded by [xplt_decode.py](../../../scratchpad/xplt_decode.py) into [scratchpad/AE_xplt_msx2_decoded.out](../../../scratchpad/AE_xplt_msx2_decoded.out)). `[XP n]` = that run's step n (0-59; 17-59 added 2026-11-23, with R#16 and the VDP's VRAM pointer recorded after every step). The three references agree on every step (the SCREEN 0 / 1 tables differ by font data only).
>
> Goldfish pass 1 (test writer) 2026-11-23: 3 findings, 2 measured, 0 moved to open, 1 corrected in wording (steps 21, 26, 53-59 added for it).

## Summary

`SETPLT` sets palette entry D to the colour given as red and blue in A and green in E. Whether it
also updates the VRAM palette table or a RAM copy — so that GETPLT and RSTPLT see the change — is
not published.

## The specification

Shared facts: [vdp-and-palette.md](../concepts/vdp-and-palette.md#the-palette).

### Interface

- **In:** D, the palette number, 0 to 15; A's high nibble red, A's low nibble blue; E's low nibble
  green [P A1 SETPLT].
- **Out:** none. Only AF changes [P A1 SETPLT].

### Behaviour

- P#D := the colour [P A1 SETPLT]; through R#16 and port #2 [P 4§2.1.2 for the port; that the call
  uses it is A].
- The VRAM table or a RAM copy updated too, D above 15, the nibbles' bit 3, E's high nibble, SCREEN
  8 (BASIC's `COLOR=` does nothing there [P 2§2.2]), and R#16 afterwards are [A].

**Measured** [M] (the same on all three references; D 5, A $73, E $04):
- SETPLT writes the VDP's palette register AND the mode's VRAM table entry (bytes 10 / 11 := $73 / $04): SCREEN 5
  [XP 2, 54], 8 (which shows no palette) [XP 16], 1 [XP 21], 0 width 40 [XP 26]. In SCREEN 5 the other five places
  (preset to the pattern) were left [XP 53-59]; the VRAM pointer after is the table + 12 (2 bytes at 10 / 11)
  [XP 2, 54].
- GETPLT reads that table entry live, not a RAM copy SETPLT keeps: a hand write after SETPLT is what GETPLT returns
  [XP 2-5].
- R#16 is D + 1 (6) after the call [XP 2, 16, 21, 26, 54].
- Out: A = E, F $03, B $5A and C kept (our inputs), D, E kept.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) match the palette, the table and GETPLT's source in SCREEN 0 width 80, 1,
5 and 8, but **in SCREEN 0 width 40 they use $0F00 (the width-80 place) instead of $0400**: INIPLT and SETPLT write
$0F00 and leave $0400, RSTPLT and GETPLT read $0F00 [XP 11, 24-26] (the first DRAFT 1 text said "they differ only in
the registers on return": step 11 already showed $0400 unwritten). Registers on return: the same as the references.
([scratchpad/AE_xplt_msx2.out](../../../scratchpad/AE_xplt_msx2.out)).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every case gives the same bytes as on the FS-A1WSX, on both models [M] ([AE_trall/xplt.out](../../../scratchpad/AE_trall/xplt.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded)
(palette snapshot, port $99 / $9A log, the whole of RAM and the six table places diffed).

| case | inputs | state | what it separates |
|---|---|---|---|
| SP-01 | D 0, 7, 15; A $5A, E $03 | — | the VDP gets red 5 / blue 2 / green 3 (A's nibble order); any RAM copy written (the diff) |
| SP-02 | D 7 | each of the six table places distinct; SCREEN 0 (40 and 80), 1-7 | the mode's VRAM table updated vs not; the bytes written (0 / 40, 1, 5, 8 measured for D 5; the others open) |
| SP-03 | D 7, then VRAM entry 7 overwritten through the ports, then GETPLT 7 | — | **decided** for entry 5 [XP 2-5]: GETPLT reads VRAM live |
| SP-04 | D 16, $FF | port log | masked by the call (the R#16 byte) vs passed and dropped by the VDP; anything written past the table |
| SP-05 | A $FF, E $FF | port log | bit 3 / E's high nibble dropped by the call vs by the VDP; stored in the table as given vs masked |
| SP-06 | D 7 | SCREEN 8 | **decided** for D 5 [XP 16]: VDP and table both written |
| SP-07 | D 7 | SCREEN 5, ACPAGE 1, DPPAGE 2, R#2's copy page 3; each page's table distinct | the page's table |
| SP-08 | D 7; D 15 | R#16 preset 3 | R#16 left at D + 1 (measured for D 5, R#16 $00 before [XP 1-2, 15-16, 20-21, 25-26, 53-54]) vs restored; D 15's wrap still open |
| SP-09 | — | BC, DE, HL, IX, IY, AF' BC' DE' HL', entry F garbage; interrupts on / off; the control call | registers kept; the call's interrupt state vs the path's |
| SP-10 | D 7 | a VDP command running (CE = 1) | VRAM written during it vs waits |

## Related pages

[GETPLT](GETPLT.md), [INIPLT](INIPLT.md), [RSTPLT](RSTPLT.md);
[vdp-and-palette.md](../concepts/vdp-and-palette.md).

## Tests that cover it

None yet.
