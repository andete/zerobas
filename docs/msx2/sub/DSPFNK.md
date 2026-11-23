<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `DSPFNK` (sub-ROM $011D) — show the function-key line

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubfnk.asm](../../probes/bios/spec/xsubfnk.asm), [scratchpad/AE_xsubfnk_msx2.out](../../scratchpad/AE_xsubfnk_msx2.out)).

## Summary

The sub-ROM's function-key display. The main ROM's DSPFNK ($00CF) goes to the sub-ROM in screen
modes 5 to 8, and handles the other modes itself. What the sub-ROM version shows in a bitmap
mode is the open question. Shared facts: [the screen-modes page](../concepts/screen-modes.md).

## The specification

**Interface.**
- In: none. Out: none. Registers: all [P App. 1, SUB-ROM DSPFNK].
- The main-ROM DSPFNK calls the sub-ROM in screen modes 5 to 8 [P App. 1, main-ROM DSPFNK, \*2].
- Interrupts on return: [A].

**Behaviour.**
- Sets CNSDFG and draws the first five function keys' labels on row CRTCNT in a text mode [A] (as
  MSX1 [DSPFNK](../../bios/DSPFNK.md)); at 80 columns, the label width and placement [A].
- In SCREEN 5-8: sets CNSDFG only, or draws on the bitmap, [A].

**Measured** [M] (the same on all three references; FNKSTR key k = 15 x ('A' + k), CRTCNT 24): CNSDFG := $FF; in the
text modes the first five keys' labels are drawn on row 23, each label (width / 5 - 1) characters then a space --
**7 at width 40, 15 at width 80, 5 in SCREEN 1** ("AAAAAAA BBBBBBB ..."); in SCREEN 5 CNSDFG is set and nothing is
drawn on the bitmap (line 204 unchanged). Interrupts ON on return.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) do NOTHING here: no labels, CNSDFG left 0, interrupts left off ([scratchpad/AE_xsubfnk_msx2.out](../../scratchpad/AE_xsubfnk_msx2.out)).

## Open (not measured)

Recorded per case: registers, interrupt state, CNSDFG, CRTCNT, LINTTB, CSRX / CSRY, the name table's
key-line row (and every other row's sum), the bitmap's last lines (modes 5-8), VRAM block sums.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | interrupt state on return: forced on, forced off, or kept (read twice, §3a) | ? | ? | ? |
| DF-40 | — | SCREEN 0 width 40, 37; CNSDFG 0 | = MSX1 DSPFNK | ? | ? | ? |
| DF-80 | — | SCREEN 0 width 80, 72, 41 | label slot width and margin at 80 columns | ? | ? | ? |
| DF-1 | — | SCREEN 1 | = MSX1 | ? | ? | ? |
| DF-GR | — | SCREEN 2, 3, 4 | CNSDFG set; nothing drawn (MSX1 rule) vs drawn | ? | ? | ? |
| DF-BM | — | SCREEN 5, 6, 7, 8; ACPAGE ≠ DPPAGE | CNSDFG only vs labels drawn on the bitmap (which page, lines) | ? | ? | ? |
| DF-ROW | CRTCNT 13, 24, 26 | SCREEN 0 (80, 212-line R#9) | row CRTCNT vs last row | ? | ? | ? |
| DF-SH | — | SHIFT pressed in NEWKEY row 6 only; then in the keyboard matrix only | keys 1-5 vs 6-10; from NEWKEY vs a fresh scan | ? | ? | ? |
| DF-STR | — | FNKSTR's ten strings distinct, one 16 bytes with no 0 | labels from FNKSTR vs built-in; cut length | ? | ? | ? |
| DF-OOR | — | SCRMOD 9, 10, 11, 12, $FF | out-of-range rule; 10-12 drawn as SCREEN 8 or not | ? | ? | ? |
| DF-ON | — | CNSDFG already $FF, key line already drawn | redrawn vs nothing | ? | ? | ? |
| DF-MAIN | main-ROM $00CF | SCREEN 0..8 | the *2 claim (sub-ROM used in 5-8 only) by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [INITXT](INITXT.md); [CLS](CLS.md);
MSX1 [DSPFNK](../../bios/DSPFNK.md), [ERAFNK](../../bios/ERAFNK.md).

## Tests that cover it

none yet
