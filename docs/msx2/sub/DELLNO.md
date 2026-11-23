<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `DELLNO` (sub-ROM $0121) — delete a screen row (interface unpublished)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubdln.asm](../../../probes/bios/spec/xsubdln.asm), [xsubdln2.asm](../../../probes/bios/spec/xsubdln2.asm), [xsubdln3.asm](../../../probes/bios/spec/xsubdln3.asm); [scratchpad/AE_xsubdln_msx2.out](../../../scratchpad/AE_xsubdln_msx2.out), [scratchpad/AE_xsubdln2_msx2.out](../../../scratchpad/AE_xsubdln2_msx2.out), [scratchpad/AE_xsubdln3_msx2.out](../../../scratchpad/AE_xsubdln3_msx2.out); decoded by [scratchpad/xsubdln_decode.py](../../../scratchpad/xsubdln_decode.py)).

## Summary

An entry at sub-ROM $0121, named DELLNO by the MSX Assembly Page's list only; the MSX2 Technical
Handbook does not list it. In the text modes it deletes one screen row: the row given in L (counted
from 1) disappears, the rows below it up to the last text row move up one, and the last text row is
cleared to spaces. LINTTB moves with the rows, and the byte at $FBCA goes down by one. The cursor is not
moved. The three references behave the same, except for the interrupt state on return. C-BIOS has no
routine here: the call returns at once. Shared facts: [the screen-modes page](../concepts/screen-modes.md).

## The specification

Case numbers `[M r n]` are the decoder's: r = `xsubdln` (round 1, cases 0-16 are DELLNO), `xsubdln2` (round 2,
cases 0-9), `xsubdln3` (round 3, cases 0-5). Every case fills 27 name-table rows with a row-tagged pattern,
LINTTB[i] := $C0 + i, CSRX / CSRY 15 / 12, CRTCNT 24 unless stated; the same on all three references unless a
machine is named.

Below, **last** is the last text row, counted from 0: CRTCNT − 1 with the key line off (CNSDFG 0), CRTCNT − 2 with
it on (CNSDFG $FF) [M xsubdln 0, 8, 15]. Only CNSDFG $00 and $FF were measured.

**Interface.**
- Not published: the handbook's sub-ROM listing goes from DSPFNK ($011D) to WRTVDP ($012D) [P App. 1, SUB-ROM].
  An entry on all three references [M xsubdln 0-16].
- In: **L = the screen row, counted from 1** (L 5 deletes row 4, L 9 row 8, L 1 row 0) [M xsubdln 0, 1, 5].
  H, A, CSRX and CSRY are not inputs: H 20, A 3, and the cursor at (3, 18) give the same result as the base case
  [M xsubdln 2, 3, 4].
- Out: no result is documented. Registers on return:
  - after a delete or a clear (the first two rules below): A = LINLEN, H = LINLEN + 1, L = last + 1, DE = the
    name-table offset of the first cleared cell (last × row length + the window's margin), IX = $0168, IY kept;
    BC = $0098 when rows moved, kept when only the last row was cleared; F $BB at LINLEN 40, $93 at 80, $B3 at 32
    and 37, $9B at 30 and 29 [M xsubdln 0, 6, 10, 11, 12, 15; xsubdln2 8, 9]. These are the values
    [EOL](../main/EOL.md) returns for H 1, L = last + 1 (its page): that DELLNO ends in the same code is [A];
  - after the early return (L − 1 past last): A = last − (L − 1) (8-bit: $FF, $FE), F $BB, BC, DE, HL and IX
    ($0121) kept [M xsubdln 7; xsubdln3 1-4].
- Interrupts on return, entered with DI: **after a delete or a clear, ON on the HB-F900 and NMS 8250, OFF on the
  FS-A1WSX** [M xsubdln 0-6, 8, 10-16; xsubdln2 0-9; xsubdln3 0, 5]; after the early return ON on all three [M xsubdln 7;
  xsubdln3 1-4]. Entered with EI: on [M xsubdln 9].

**Behaviour.**
- **L − 1 before last (L 1 to last):** the rows L .. last move up one (row r := the old row r + 1 for
  L − 1 ≤ r < last), and row last := $20 over the text window [M xsubdln 0, 1, 5, 8, 10, 11, 15, 16]. The
  deleted row's content is gone. Rows after last are not touched: row 23 with the key line on, rows 24-26, and rows 20-23
  with CRTCNT 20 [M xsubdln 0, 8, 15].
- **L − 1 = last:** row last := $20; nothing moves [M xsubdln 6; xsubdln3 0].
- **L − 1 past last** (L 25 and 26 at CRTCNT 24, L 21 and 22 at CRTCNT 20, L 24 with the key line on): nothing
  changes — VRAM, LINTTB and $FBCA as found [M xsubdln 7; xsubdln3 1-4].
- **L 0** does what L 1 does (row 0 deleted, rows 1-23 up, row 23 cleared, the same registers) [M xsubdln 5;
  xsubdln3 5].
- **The text window only:** with LINLEN below the screen width, only LINLEN cells of each row move or are
  cleared, from column ⌈(W − LINLEN) / 2⌉ (W = 40 in SCREEN 0, 32 in SCREEN 1); the columns outside keep their
  old content. Measured: LINLEN 37 → columns 2-38, LINLEN 30 → columns 5-34, SCREEN 1 LINLEN 29 → columns 2-30
  [M xsubdln2 7, 8, 9]. At width 80 and SCREEN 1 width 32 the whole row [M xsubdln 10, 11].
- **LINTTB** moves with the rows: LINTTB[r] := the old LINTTB[r + 1] for L − 1 ≤ r < last, then LINTTB[last] :=
  $AF; on the clear-only path LINTTB[last] := $AF alone; entries after last are kept [M xsubdln 0, 5, 6, 8, 15].
  A 0 entry (a continued logical line) moves like any other and the delete is still one screen row:
  LINTTB[5] = 0 → LINTTB[4] = 0 after it; LINTTB[4] = 0 is dropped with its row [M xsubdln 13, 14].
- **$FBCA := $FBCA − 1** (8-bit; $00 → $FF) whenever rows moved, whatever its value relative to L (3, 4, 5, 6, 24, 0
  and 30 with L 5) [M xsubdln 0; xsubdln2 0-5, 7-9]; kept on the clear-only path and on the early return
  [M xsubdln 6; xsubdln2 6; xsubdln3 0-4]; $FBCB kept [M xsubdln2 0-9]. The work-area listings name $FBCA FSTPOS (the start of the line being input) [A: not in this
  repo's sources].
- **Not changed:** CSRX, CSRY, CNSDFG, CRTCNT, LINLEN, SCRMOD; the key-line row (row 23 with CNSDFG $FF) is not
  redrawn [M xsubdln 0-16].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) have no routine at $0121: the address holds the RET filler of C-BIOS's
`sub.asm`, and the call returns at once — nothing moves or is cleared, LINTTB and $FBCA stay as found, every
register comes back as it went in (IX $0121), and the interrupt state is kept (off when entered with DI) [M xsubdln
0-16; xsubdln2 0-9; xsubdln3 0-5].

## Open (not measured)

- The graphic and bitmap modes (SCREEN 2-8): EOL and CLRTXT write text-mode cells there; DELLNO is not measured.
- CNSDFG values other than $00 / $FF; CRTCNT above 24 (a 26.5-row R#9 screen).
- What L 0 does past the checked rows, and what the early return's A is used for.
- Whether the moved rows are copied cell by cell from the row below at every LINLEN (the full-row check reads whole
  rows; only rows 4, 5 and 23 are dumped in full, at LINLEN 37, 30 and 29).
- The FS-A1WSX's interrupt state: why the delete path ends with interrupts off there (EXTROM's own handling, or the
  routine's) is not separable with these probes.
- Stack depth and time.

## Related pages

[INSLNO](INSLNO.md); [EOL](../main/EOL.md); [CLRTXT](CLRTXT.md); [the screen-modes page](../concepts/screen-modes.md);
the MSX1 [screen editor](../../concepts/screen-editor.md) and [CHPUT](../../bios/CHPUT.md) (`ESC M`, delete line).

## Tests that cover it

none yet
