<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `INSLNO` (sub-ROM $0125) — insert a blank screen row (interface unpublished)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubdln.asm](../../../probes/bios/spec/xsubdln.asm), [xsubdln2.asm](../../../probes/bios/spec/xsubdln2.asm), [xsubdln3.asm](../../../probes/bios/spec/xsubdln3.asm); [scratchpad/AE_xsubdln_msx2.out](../../../scratchpad/AE_xsubdln_msx2.out), [scratchpad/AE_xsubdln2_msx2.out](../../../scratchpad/AE_xsubdln2_msx2.out), [scratchpad/AE_xsubdln3_msx2.out](../../../scratchpad/AE_xsubdln3_msx2.out); decoded by [scratchpad/xsubdln_decode.py](../../../scratchpad/xsubdln_decode.py)).

## Summary

An entry at sub-ROM $0125, named INSLNO by the MSX Assembly Page's list only; the MSX2 Technical
Handbook does not list it. In the text modes it inserts a blank screen row: the row given in L
(counted from 1) and the rows below it move down one, the last text row's old content is lost, and the
given row is cleared to spaces. LINTTB moves with the rows, except that the last row's entry becomes
$FB. The cursor is not moved. The three references behave the same, except for the interrupt state on
return. C-BIOS has no routine here: the call returns at once. The counterpart is [DELLNO](DELLNO.md).
Shared facts: [the screen-modes page](../concepts/screen-modes.md).

## The specification

Case numbers `[M r n]` are the decoder's: r = `xsubdln` (round 1, cases 17-33 are INSLNO), `xsubdln2` (round 2,
cases 10-19), `xsubdln3` (round 3, cases 6-11). Every case fills 27 name-table rows with a row-tagged pattern,
LINTTB[i] := $C0 + i, CSRX / CSRY 15 / 12, CRTCNT 24 unless stated; the same on all three references unless a
machine is named.

**last** is the last text row, counted from 0: CRTCNT − 1 with the key line off (CNSDFG 0), CRTCNT − 2 with it on
(CNSDFG $FF) [M xsubdln 17, 25, 32]. Only CNSDFG $00 and $FF were measured.

**Interface.**
- Not published: the handbook's sub-ROM listing goes from DSPFNK ($011D) to WRTVDP ($012D) [P App. 1, SUB-ROM].
  An entry on all three references [M xsubdln 17-33].
- In: **L = the screen row, counted from 1** (L 5 inserts at row 4, L 9 at row 8, L 1 at row 0) [M xsubdln 17,
  18, 22]. H, A, CSRX and CSRY are not inputs: H 20, A 3 and the cursor at (3, 18) give the same result as the
  base case [M xsubdln 19, 20, 21].
- Out: no result is documented. Registers on return:
  - after an insert or a clear (the first two rules below): A = LINLEN, H = LINLEN + 1, L = the entry L, DE = the
    name-table offset of the first cleared cell (row L − 1's, plus the window's margin), IX = $0168, IY kept;
    BC = $0098 when rows moved, kept when only the last row was cleared; F $BB at LINLEN 40, $93 at 80, $B3 at 32
    and 37, $9B at 30 and 29 [M xsubdln 17, 23, 27, 28, 29; xsubdln2 18, 19]. These are the values
    [EOL](../main/EOL.md) returns for H 1 and the same L (its page): that INSLNO ends in the same code is [A];
  - after the early return (L − 1 past last): A = last − (L − 1) (8-bit: $FF, $FE), F $BB, **H = last + 1**
    (24 at CRTCNT 24, 20 at CRTCNT 20, 23 with the key line on), L, BC, DE and IX ($0125) kept [M xsubdln 24;
    xsubdln3 7-10].
- Interrupts on return, entered with DI: **after an insert or a clear, ON on the HB-F900 and NMS 8250, OFF on the
  FS-A1WSX** [M xsubdln 17-23, 25, 27-33; xsubdln2 10-19; xsubdln3 6, 11]; after the early return ON on all three
  [M xsubdln 24; xsubdln3 7-10]. Entered with EI: on [M xsubdln 26].

**Behaviour.**
- **L − 1 before last (L 1 to last):** the rows L − 1 .. last − 1 move down one (row r := the old row r − 1 for
  L − 1 < r ≤ last); the old row last is lost; row L − 1 := $20 over the text window [M xsubdln 17, 18, 22, 25, 27,
  28, 32, 33]. Rows after last are not touched: row 23 with the key line on, rows 24-26, and rows 20-23 with
  CRTCNT 20 [M xsubdln 17, 25, 32].
- **L − 1 = last:** row last := $20; nothing moves [M xsubdln 23; xsubdln3 6].
- **L − 1 past last** (L 25 and 26 at CRTCNT 24, L 21 and 22 at CRTCNT 20, L 24 with the key line on): nothing
  changes — VRAM, LINTTB and $FBCA as found [M xsubdln 24; xsubdln3 7-10].
- **L 0:** rows 1 .. last := the old rows 0 .. last − 1, and row 0 is NOT cleared (it keeps its old content, so
  rows 0 and 1 are the same); DE comes back $27D8 = 255 × 40, the clear aimed at row 255, outside the 27 rows read
  [M xsubdln3 11]. What it wrote there is not measured.
- **The text window only:** with LINLEN below the screen width, only LINLEN cells of each row move or are
  cleared, from column ⌈(W − LINLEN) / 2⌉ (W = 40 in SCREEN 0, 32 in SCREEN 1); the columns outside keep their
  old content. Measured: LINLEN 37 → columns 2-38, LINLEN 30 → columns 5-34, SCREEN 1 LINLEN 29 → columns 2-30
  [M xsubdln2 17, 18, 19]. At width 80 and SCREEN 1 width 32 the whole row [M xsubdln 27, 28].
- **LINTTB:** LINTTB[L − 1] := $AF; LINTTB[r] := the old LINTTB[r − 1] for L − 1 < r < last; and **LINTTB[last] :=
  $FB**, not the old LINTTB[last − 1] (at CRTCNT 24 and 20, key line off and on) [M xsubdln 17, 18, 22, 25, 32,
  33]. On the clear-only path LINTTB[last] := $AF alone [M xsubdln 23; xsubdln3 6]. At L 0: LINTTB[0] kept,
  LINTTB[1 .. last − 1] := the old [0 .. last − 2], LINTTB[last] := $FB [M xsubdln3 11]. Entries after last are kept.
  A 0 entry moves like any other: LINTTB[5] = 0 → LINTTB[6] = 0, LINTTB[4] = 0 → LINTTB[5] = 0, and the insert is
  still one screen row [M xsubdln 30, 31]. Whether $FB is a constant or follows LINTTB's address is [A] (LINTTB
  cannot be moved).
- **$FBCA and $FBCB are kept** (values 3, 4, 5, 6, 24, 0, 30) [M xsubdln2 10-19] — unlike DELLNO, which decrements
  $FBCA.
- **Not changed:** CSRX, CSRY, CNSDFG, CRTCNT, LINLEN, SCRMOD; the key-line row (row 23 with CNSDFG $FF) is not
  redrawn [M xsubdln 17-33].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) have no routine at $0125: the address holds the RET filler of C-BIOS's
`sub.asm`, and the call returns at once — nothing moves or is cleared, LINTTB stays as found, every register comes
back as it went in (IX $0125), and the interrupt state is kept (off when entered with DI) [M xsubdln 17-33;
xsubdln2 10-19; xsubdln3 6-11].

## Open (not measured)

- The graphic and bitmap modes (SCREEN 2-8).
- CNSDFG values other than $00 / $FF; CRTCNT above 24.
- The VRAM L 0 writes at offset $27D8; whether LINTTB[last] = $FB depends on anything.
- Whether the moved rows are copied cell by cell from the row above at every LINLEN (only rows 4, 5 and 23 are
  dumped in full, at LINLEN 37, 30 and 29).
- The FS-A1WSX's interrupt state after an insert (EXTROM's handling or the routine's).
- Stack depth and time.

## Related pages

[DELLNO](DELLNO.md); [EOL](../main/EOL.md); [CLRTXT](CLRTXT.md); [the screen-modes page](../concepts/screen-modes.md);
the MSX1 [screen editor](../../concepts/screen-editor.md) and [CHPUT](../../bios/CHPUT.md) (`ESC L`, insert line).

## Tests that cover it

none yet
