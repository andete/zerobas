<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `DSPFNK` (sub-ROM $011D) — show the function-key line

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubfnk.asm](../../../probes/bios/spec/xsubfnk.asm), [scratchpad/AE_xsubfnk_msx2.out](../../../scratchpad/AE_xsubfnk_msx2.out), decoded by [xsubfnk_decode.py](../../../scratchpad/xsubfnk_decode.py)). `[F n]` = that run's case n. Cases 4-11 and 13-19 fill ALL 128 KB of VRAM with an address-dependent pattern after CHGMOD and before the call, and count every byte that differs after it (a write of the byte the pattern already held is invisible). Every reading below is the same on all three references.
>
> Goldfish pass 1 (test writer) 2026-11-23: 5 findings, 5 measured, 0 moved to open.

## Summary

The sub-ROM's function-key display. The main ROM's DSPFNK ($00CF) goes to the sub-ROM in screen
modes 5 to 8, and handles the other modes itself. What the sub-ROM version shows in a bitmap
mode is the open question. Shared facts: [the screen-modes page](../concepts/screen-modes.md).

## The specification

**Interface.**
- In: none. Out: none. Registers: all [P App. 1, SUB-ROM DSPFNK].
- The main-ROM DSPFNK calls the sub-ROM in screen modes 5 to 8 [P App. 1, main-ROM DSPFNK, \*2].
- Interrupts on return: on (below).

**Behaviour.**
- Sets CNSDFG := $FF in every mode measured, SCREEN 0-8, also when it was $FF already [M F 4-19].
- **Text modes (SCREEN 0, 1): draws the first five keys' labels on row CRTCNT - 1** (row 23 with CRTCNT 24, row 12
  with CRTCNT 13) and writes nothing else in VRAM [M F 4-11: every changed byte lies in that row].
- The row is a LINLEN-cell window starting at the text screen's left margin: column 0 at LINLEN 40 / 80 / 32 in a
  40- / 80- / 32-column screen, column 2 at LINLEN 37 and 36 (SCREEN 0) and 29 (SCREEN 1) [M F 2, 4-9]; the general
  margin rule is the text screen's, measured here at those widths only [A beyond them].
- **The label width is (LINLEN + 1) / 5 - 1 characters** (integer division): 15 at 80, 7 at 40, 6 at 37 and 36,
  5 at 32 and 29 [M F 2, 4-9]. (LINLEN / 5 - 1 fits every width but 29, where it gives 4: F 8 shows 5.) Label k
  (0-4) starts at the margin + k x (width + 1); a space follows each as far as the window reaches (at 29 the last
  label ends the window); the rest of the window is spaces [M F 4, 5, 7, 8, 9].
- In SCREEN 0 the width comes from **LINLEN**, not LINL40: LINL40 40 with LINLEN 36 written after CHGMOD gives
  6-character labels in a 36-cell window [M F 9]. In SCREEN 1, LINL32 29 (LINL40 40) gives 29, not 40 [M F 8];
  LINLEN = LINL32 there, so LINLEN vs LINL32 is not separated in SCREEN 1 [A: LINLEN, as in SCREEN 0].
- Each label is FNKSTR's key k string (keys 1-5) up to its first 0, padded with spaces to the label width, or cut
  at the width when longer: "AAA" -> "AAA" + spaces [M F 4, 5]; a 16-byte string with no 0 -> its first 15
  characters at width 80 [M F 6].
- **SCREEN 2-8: CNSDFG := $FF and nothing in the 128 KB of VRAM changes** [M F 13-19] (ACPAGE = DPPAGE = 0).
- Interrupts ON on return, entered with DI and with EI, through EXTROM [M F 4, 12]; whether the call or the
  EXTROM path enables them is not separated [A].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) do NOTHING here: no labels, no VRAM byte changed, CNSDFG left as it was
(0, or $FF in F 11), interrupts left off when entered with DI ([scratchpad/AE_xsubfnk_msx2.out](../../../scratchpad/AE_xsubfnk_msx2.out), `--side ours`). Its F 12 row shows labels, but its CHGMOD drew them (CNSDFG was $FF from F 11
when CHGMOD ran; the probe set CNSDFG := 0 after it): not the call.

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every case gives the same bytes as on the FS-A1WSX, on both models [M] ([AE_trall/xsubfnk.out](../../../scratchpad/AE_trall/xsubfnk.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

Measured above: IE (in part), DF-40, DF-80, DF-1, DF-GR, DF-BM, DF-ROW (CRTCNT 13), DF-STR, DF-ON. Cases F 0-3
(the first run) are kept on file; F 1 and F 2 ran after a case that left CNSDFG $FF, so their CHGMOD may already
have drawn a key line (with FNKSTR's strings of the case before, which were the same): the rules above cite the
pattern-filled cases instead.

| case | inputs | state | what it separates |
|---|---|---|---|
| IE | F 4's case through SUBROM ($015C) and through the main ROM's $00CF | entered with DI | interrupts enabled by the call vs by the EXTROM path |
| DF-ROW | CRTCNT 26 | SCREEN 0 (80, 212-line R#9) | row CRTCNT - 1 beyond row 23 |
| DF-W | SCREEN 1 with LINLEN written ≠ LINL32; LINLEN 1-4, 41-79 (SCREEN 0 width 80), LINLEN > the screen width | — | the label width and margin rules outside the six widths measured (a label width of 0 or less) |
| DF-SH | — | SHIFT pressed in NEWKEY row 6 only; then in the keyboard matrix only | keys 1-5 vs 6-10; from NEWKEY vs a fresh scan |
| DF-OOR | — | SCRMOD 9, 10, 11, 12, $FF | out-of-range rule; 10-12 drawn as SCREEN 8 or not |
| DF-MAIN | main-ROM $00CF | SCREEN 0..8 | the *2 claim (sub-ROM used in 5-8 only) by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [INITXT](INITXT.md); [CLS](CLS.md);
MSX1 [DSPFNK](../../bios/DSPFNK.md), [ERAFNK](../../bios/ERAFNK.md).

## Tests that cover it

none yet
