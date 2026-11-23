<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SDFSCR` (sub-ROM $0185) — restore the screen settings from the clock chip (interface unpublished)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubscr.asm](../../../probes/bios/spec/xsubscr.asm), [scratchpad/AE_xsubscr_msx2.out](../../../scratchpad/AE_xsubscr_msx2.out), decoded by `scratchpad/xsubscr_decode.py`; run with `tools/agent_wt.py --fresh`). Goldfish pass 1 adds [xsubsc2.asm](../../../probes/bios/spec/xsubsc2.asm),
> [scratchpad/AE_xsubsc2_msx2.out](../../../scratchpad/AE_xsubsc2_msx2.out) (`scratchpad/xsubscr_decode.py --cases
> xsubsc2`), cited `[M xsubsc2 n]`.
>
> Goldfish pass 1 (test writer) 2026-11-23: 8 findings, 7 measured (xsubsc2 cases 0-8), 1 corrected, 1 moved to open
> (cells written with the value they already held).

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
- In: none. A, carry and Z are not inputs: A = $00 / $FF, F = $00 / $01 (carry) / $40 (Z) give the same result on
  the TEXT 2 path [M xsubscr 6-9], and A $FF with F $41 (carry and Z) gives the same result as A = F = 0 on the
  SCREEN 1 path [M xsubscr 2, xsubsc2 4, 5].
- Out: none. AF, BC, DE, HL, IX are changed; their values depend on the path taken and are the same on all three
  references [M xsubscr 0-19]. That IY and the alternate set are kept, [A].
- Interrupts on return: **on** when the call switches the VDP into the 80-column TEXT 2 (width > 40) from TEXT 1 or
  SCREEN 1, whatever the entry state [M xsubscr 6-10]; **kept** when the result is SCREEN 1 or 40-column SCREEN 0
  (entered with DI: off; with EI: on) [M xsubscr 2-5, 18], and also when the call is entered with DI already in
  80-column TEXT 2 and the result is TEXT 2 again: off [M xsubsc2 2]. So it is the switch into TEXT 2, not the
  result, that turns them on.

**Behaviour** (the same on all three references unless a machine is named).
- Reads clock-chip block 2 [P Ch. 5 §6.7, Figure 5.33] and applies:
  - register 3 bit 0, the screen mode: 0 → SCREEN 0, 1 → SCREEN 1. It is a real mode change, from any previous
    mode (SCREEN 0, 1, 5 and 80-column TEXT 2 measured): SCRMOD = OLDSCR := the mode, NAMBAS / CGPBAS follow the
    mode, the cursor homed (CSRY = CSRX = 1) [M xsubscr 0-2, 5, 10; xsubsc2 2, 4];
  - the VDP registers (read back as last written, and RG0SAV-RG23SAV, the same on all three): R#0-R#4 the mode's
    values (TEXT 1: 00 70 00 xx 01; TEXT 2: 04 70 03 27 02; SCREEN 1: 00 60 06 80 00), R#7 the colour (below), R#8
    $08, R#9 the interlace bit. **R#5 / R#6 are written only for SCREEN 1** ($36 / $07, also when entered from
    SCREEN 5, where they were $EF / $0F); a SCREEN 0 result leaves them as the previous mode had them ($EF / $0F after
    SCREEN 5, $36 / $07 after SCREEN 1) [M xsubscr 1, 4, 5, 6, 10]. In TEXT 1, R#3 (xx) is the previous state's: $80
    after TEXT 1 / SCREEN 1, $27 after TEXT 2 [M xsubscr 4; xsubsc2 3] — not written either, [A] from these two values;
  - the screen cleared: with the name table filled with 'Z' just before the call, rows 0 and 23 read back as spaces
    in every result (TEXT 2 entered from TEXT 2, TEXT 1, SCREEN 1); in TEXT 1 exactly 24 × 40 bytes: the 'Z' after
    them is left [M xsubsc2 2, 3, 4]. (Without the fill the probe's own CHGMOD had already blanked the rows, so
    xsubscr's spaces separate only the cases entered from SCREEN 5 [M xsubscr 1, 5].) Which other rows and tables
    are rewritten is open (SD-REST);
  - registers 4 (low nibble) and 5 (high nibble), the width, one binary byte (37 is 5 / 2, 80 is 0 / 5). SCREEN 0:
    LINL40 = LINLEN := width, LINL32 untouched; a width above 40 selects TEXT 2 (80 columns, R#0 = $04). SCREEN 1:
    LINL32 = LINLEN := width, LINL40 untouched. The width is NOT clamped: 100 gives LINL40 = LINLEN = 100 in TEXT 2.
    CLMLST follows the width as on MSX1 (width − width mod 14 − 14: 14, 14, 56, 84, 0 for 30, 37, 80, 100, 18)
    [M xsubscr 2, 5, 6, 10, 18]. Nor in SCREEN 1: width 36 and 50 give LINL32 = LINLEN = 36 / 50 and the mode stays
    SCREEN 1 (no switch to text at > 32 or > 40), CLMLST 14 / 28; and width 0 in SCREEN 0 gives LINL40 = LINLEN = 0,
    TEXT 1, CLMLST $F2 (−14) [M xsubsc2 6, 7, 8];
  - registers 6 / 7 / 8: FORCLR / BAKCLR / BDRCLR, and R#7 (FORCLR · 16 + BAKCLR in SCREEN 0, BDRCLR in SCREEN 1)
    [M xsubscr 2, 5, 6, 10];
  - register 3 bit 1, interlace: R#9 bit 3 (IL) set, in RG9SAV too [M xsubscr 2]. With the bit at 0, R#9 bit 3 reads
    0 — but the probe cleared it before the call, so "cleared" and "left" are not separated, [A];
  - register 9 bit 1, key click: CLIKSW := $FF (1) / $00 (0) [M xsubscr 0, 2, 5, 6];
  - register 9 bit 2, printer: NTMSXP ($F417) $00 → $FF [M xsubscr 13]; and back: with the bit 0, NTMSXP $FF → $00
    [M xsubsc2 1];
  - register 9 bit 3, cassette speed: the five cassette-timing cells $F406-$F40A from 53 5C 26 2D 0F to
    25 2D 0E 16 1F [M xsubscr 14]; and back: with the bit 0, 25 2D 0E 16 1F → 53 5C 26 2D 0F [M xsubsc2 1]. So both
    bits are applied either way: 0 writes the default, not "leave".
- Register 9 bit 0 (the key-line switch) is NOT applied: CNSDFG := $00 in every case, with the bit 1 or 0, and no
  key line is drawn [M xsubscr 0-19] — not even drawn and erased: with the bit 1, nothing in the log of every byte
  sent to port $98 during the call matches "AAA" (key 1's label) [M xsubsc2 3].
- Not applied: the adjust (registers 1 / 2: R#18 and RG18SAV stay 0 with adjust (3, −2)) [M xsubscr 2]; the beep
  (register 10) and the title colour (register 11): no work-area cell changes [M xsubscr 15, 16].
- The ID (register 0) is not checked: ID 5 gives the same result as ID $A [M xsubscr 16 / 17, 18 / 19].
- The clock chip is left as it was: block 2 reads back unchanged, MODE reads $A (timer enabled, block 2)
  [M xsubscr 0-19].
- Nothing else in the work area changes: a whole $F380-$FFFF diff between two runs that differ in one setting shows
  that setting's cells and the interrupt counters only (JIFFY $FC9E, $FCA2, SCNCNT / REPCNT) [M xsubscr 12-17; xsubsc2
  1]. One call's own before / after diff (SCREEN 1 width 30 from a garbled SCREEN 0) changes exactly LINL32, LINLEN,
  CLIKSW, CSRY, CSRX, CNSDFG, RG1SAV-RG4SAV, RG7SAV, FORCLR / BAKCLR / BDRCLR, ATRBYT ($F3F2 := FORCLR), NAMBAS.h /
  CGPBAS.h ($F923 / $F925), SCRMOD, OLDSCR, RG9SAV and the interrupt counters, the same 22 cells on all three
  [M xsubsc2 4]. A cell written with the value it already held does not show in either kind of diff (LINTTB, CLMLST,
  the other table bases), [A].

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
([scratchpad/AE_xsubscr_msx2.out](../../../scratchpad/AE_xsubscr_msx2.out)).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every case gives the same bytes as on the FS-A1WSX, on both models except VDP S#2 (read at a random moment), R#36 = $80 before case 0 (the boot's last VDP command) and JIFFY / INTCNT one count apart in xsubsc2 case 1 (timing) [M] ([AE_trall/xsubscr.out](../../../scratchpad/AE_trall/xsubscr.out), [AE_trall/xsubsc2.out](../../../scratchpad/AE_trall/xsubsc2.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

Recorded per case: A F BC DE HL IX IY, IFF (read twice), SCRMOD OLDSCR LINL40 LINL32 LINLEN CRTCNT CLMLST CNSDFG
CLIKSW FORCLR BAKCLR BDRCLR CSRY CSRX, RG0SAV-RG23SAV, clock-chip blocks 2 / 3 through ports $B4 / $B5 (and block 2
before the call), R#0-R#63 / S#0-S#15 / the palette (debugger), the name table's row 0 and row 23; a $F380-$FFFF
diff for cases 12-17 and 19. xsubsc2: the same, with the name table filled with 'Z' first (cases 2-4), the port-$98
log searched for "AAA" (3), a $F380-$FFFF diff against the snapshot of the previous case (1) or of the same call's
entry (4).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | — | SCREEN 1 / width 37 / width 80, DI and EI; entered in TEXT 2 | interrupt state on return | kept (S1, 40 col, TEXT 2 → TEXT 2), on (switched into 80 col) | same | same |
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
| SD-OFF | — | block 2 printer / cassette bits 1 → 0 | 0 writes the default vs leaves | default | default | default |
| SD-CLR | — | name table := 'Z' before the call | cleared vs left | cleared (24 rows) | same | same |
| SD-IE2 | — | entered in TEXT 2 with DI, result TEXT 2 | IE on for "result TEXT 2" vs "switched into TEXT 2" | kept (off) | same | same |
| SD-W1 | — | SCREEN 1 width 36, 50; SCREEN 0 width 0 | clamped / mode switched vs stored as is | as is | same | same |
| SD-SAME | — | work-area cells pre-set to junk (LINTTB, CLMLST, table bases) | cells written with the value they already held | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [SETSCR](SETSCR.md); [PROMPT](PROMPT.md);
[INITXT](INITXT.md); [WRTCLK](WRTCLK.md).

## Tests that cover it

none yet
