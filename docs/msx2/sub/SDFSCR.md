<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SDFSCR` (sub-ROM $0185) — restore the screen settings from the clock chip (interface unpublished)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubscr.asm](../../probes/bios/spec/xsubscr.asm), [scratchpad/AE_xsubscr_msx2.out](../../scratchpad/AE_xsubscr_msx2.out), decoded by `scratchpad/xsubscr_decode.py`; run with `tools/agent_wt.py --fresh`).

## Summary

An entry at sub-ROM $0185 named SDFSCR by other open implementations. It applies the `SET SCREEN`
settings kept in the clock chip's block 2: it switches to SCREEN 0 or 1 with the stored width and
colours, and sets the key click, the printer type and the cassette speed. It leaves the
function-key line OFF whatever the stored key switch says. [SETSCR](SETSCR.md) does the same and
then prints the banner and the key line. The MSX2 Technical Handbook does not list it. Shared facts:
[the screen-modes page](../concepts/screen-modes.md#the-clock-chips-screen-settings).

## The specification

Case numbers `[M xsubscr n]` are the probe's case table (`cases` in the probe, `NAMES` in the decoder).

**Interface.**
- Not published: the handbook lists PROMPT ($0181) and then NEWPAD ($01AD) [P App. 1, SUB-ROM].
- In: none. A, carry and Z are not inputs: A = $00 / $FF, F = $00 / $01 (carry) / $40 (Z) give the same result
  [M xsubscr 6-9].
- Out: none. AF, BC, DE, HL, IX are changed; their values depend on the path taken and are the same on all three
  references [M xsubscr 0-19]. That IY and the alternate set are kept, [A].
- Interrupts on return: **on** when the result is the 80-column TEXT 2 (width > 40), whatever the entry state;
  **kept** when it is SCREEN 1 or 40-column SCREEN 0 (entered with DI: off; with EI: on)
  [M xsubscr 2-6, 9, 10, 18].

**Behaviour** (the same on all three references unless a machine is named).
- Reads clock-chip block 2 [P Ch. 5 §6.7, Figure 5.33] and applies:
  - register 3 bit 0, the screen mode: 0 → SCREEN 0, 1 → SCREEN 1. It is a real mode change, from any previous
    mode (SCREEN 0, 1 and 5 measured): SCRMOD = OLDSCR := the mode, the VDP reprogrammed, the screen cleared (rows 0
    and 23 read back as spaces) and the cursor homed (CSRY = CSRX = 1) [M xsubscr 0-2, 5, 10];
  - registers 4 (low nibble) and 5 (high nibble), the width, one binary byte (37 is 5 / 2, 80 is 0 / 5). SCREEN 0:
    LINL40 = LINLEN := width, LINL32 untouched; a width above 40 selects TEXT 2 (80 columns, R#0 = $04). SCREEN 1:
    LINL32 = LINLEN := width, LINL40 untouched. The width is NOT clamped: 100 gives LINL40 = LINLEN = 100 in TEXT 2.
    CLMLST follows the width as on MSX1 (width − width mod 14 − 14: 14, 14, 56, 84, 0 for 30, 37, 80, 100, 18)
    [M xsubscr 2, 5, 6, 10, 18];
  - registers 6 / 7 / 8: FORCLR / BAKCLR / BDRCLR, and R#7 (FORCLR · 16 + BAKCLR in SCREEN 0, BDRCLR in SCREEN 1)
    [M xsubscr 2, 5, 6, 10];
  - register 3 bit 1, interlace: R#9 bit 3 (IL) set, in RG9SAV too [M xsubscr 2]. With the bit at 0, R#9 bit 3 reads
    0 — but the probe cleared it before the call, so "cleared" and "left" are not separated, [A];
  - register 9 bit 1, key click: CLIKSW := $FF (1) / $00 (0) [M xsubscr 0, 2, 5, 6];
  - register 9 bit 2, printer: NTMSXP ($F417) $00 → $FF [M xsubscr 13];
  - register 9 bit 3, cassette speed: the five cassette-timing cells $F406-$F40A from 53 5C 26 2D 0F to
    25 2D 0E 16 1F [M xsubscr 14].
- Register 9 bit 0 (the key-line switch) is NOT applied: CNSDFG := $00 in every case, with the bit 1 or 0, and no
  key line is drawn [M xsubscr 0-19].
- Not applied: the adjust (registers 1 / 2: R#18 and RG18SAV stay 0 with adjust (3, −2)) [M xsubscr 2]; the beep
  (register 10) and the title colour (register 11): no work-area cell changes [M xsubscr 15, 16].
- The ID (register 0) is not checked: ID 5 gives the same result as ID $A [M xsubscr 16 / 17, 18 / 19].
- The clock chip is left as it was: block 2 reads back unchanged, MODE reads $A (timer enabled, block 2)
  [M xsubscr 0-19].
- Nothing else in the work area changes: a whole $F380-$FFFF diff between two runs that differ in one setting shows
  that setting's cells and the interrupt counters only (JIFFY $FC9E, $FCA2, SCNCNT / REPCNT) [M xsubscr 12-17].

**The clock chip after a fresh boot** (an empty persistent state, `--fresh`), as read before case 0 [M xsubscr 0]:

| register (block 2) | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|
| 0 ID | $A | $A | $A |
| 1 / 2 adjust | 0 / 0 | 0 / 0 | 0 / 0 |
| 3 mode / interlace | SCREEN 1 / off | SCREEN 0 / off | SCREEN 1 / off |
| 4 / 5 width | 29 | 37 | 29 |
| 6 / 7 / 8 colours | 15 / 4 / 7 | 15 / 4 / 4 | 15 / 4 / 7 |
| 9 key, click, printer, cassette | on, on, 0, 0 | on, on, 0, 0 | on, on, 0, 0 |
| 10 beep / 11 title colour / 12 | 0 / 0 / 0 | 1 / 0 / 2 | 0 / 0 / 0 |

So SDFSCR on a fresh machine gives SCREEN 1 width 29 on the two Japanese machines and SCREEN 0 width 37 on the
NMS 8250 [M xsubscr 0]. The same fresh state reads $F in every register on C-BIOS's machines [M xsubscr 0, ours],
which suggests the references' own start-up writes these values; that is [A].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject): **SDFSCR is a no-op** — nothing applied (mode, width, colours, CLIKSW,
CNSDFG, cursor, the printer and cassette cells all left as the probe set them), registers returned as entered,
interrupts on in every case. Their start-up also leaves clock-chip block 2 unwritten ($F in every register, no ID)
([scratchpad/AE_xsubscr_msx2.out](../../scratchpad/AE_xsubscr_msx2.out)).

## Open (not measured)

Recorded per case: A F BC DE HL IX IY, IFF (read twice), SCRMOD OLDSCR LINL40 LINL32 LINLEN CRTCNT CLMLST CNSDFG
CLIKSW FORCLR BAKCLR BDRCLR CSRY CSRX, RG0SAV-RG23SAV, clock-chip blocks 2 / 3 through ports $B4 / $B5 (and block 2
before the call), R#0-R#63 / S#0-S#15 / the palette (debugger), the name table's row 0 and row 23; a $F380-$FFFF
diff for cases 12-17 and 19.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | — | SCREEN 1 / width 37 / width 80, DI and EI | interrupt state on return | kept (S1, 40 col), on (80 col) | same | same |
| SD-EX | — | all three machines, SCREEN 0 | an entry at all | yes | yes | yes |
| SD-BLK2 | — | block 2: mode 1, width 30, colours 6 / 7 / 8, key off, adjust (+3, −2), interlace 1 | which settings it applies | mode, width, colours, IL, click; not adjust | same | same |
| SD-CY | A $00 / $FF, F $00 / $01 / $40 | width 80, key on | a flag selects the key line / a mode change | ignored | ignored | ignored |
| SD-WIDTH | — | width 80, 100 (measured); 41, 255 | TEXT 2 selected; out-of-range width | 80, 100 → TEXT 2, unclamped; 41, 255 ? | same | same |
| SD-ONE | — | printer, cassette, beep, title colour changed alone | the cell each lands in | NTMSXP; $F406-$F40A; none; none | same | same |
| SD-ID | — | ID 5 | ID checked vs applied anyway | applied anyway | same | same |
| SD-NOCLK | — | clock chip unresponsive (if the emulator can) | defaults vs garbage | ? | ? | ? |
| SD-PREV | — | entered in SCREEN 5 | switches to text or only stores cells | switches | switches | switches |
| SD-IL0 | — | R#9 IL preset 1, block-2 interlace 0 | IL cleared vs left | ? | ? | ? |
| SD-ADJ | — | R#18 preset non-zero, adjust 0 | adjust left vs cleared | ? | ? | ? |
| SD-REST | — | the screen fully read (all rows, colour and pattern tables) | which tables the mode change rewrites | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [SETSCR](SETSCR.md); [PROMPT](PROMPT.md);
[INITXT](INITXT.md); [WRTCLK](WRTCLK.md).

## Tests that cover it

none yet
