<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `DELLNO` (sub-ROM $0121) — delete a screen row (interface unpublished)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubdln.asm](../../../probes/bios/spec/xsubdln.asm), [xsubdln2.asm](../../../probes/bios/spec/xsubdln2.asm), [xsubdln3.asm](../../../probes/bios/spec/xsubdln3.asm); [scratchpad/AE_xsubdln_msx2.out](../../../scratchpad/AE_xsubdln_msx2.out), [scratchpad/AE_xsubdln2_msx2.out](../../../scratchpad/AE_xsubdln2_msx2.out), [scratchpad/AE_xsubdln3_msx2.out](../../../scratchpad/AE_xsubdln3_msx2.out); round 4 [xsubdln4.asm](../../../probes/bios/spec/xsubdln4.asm), [scratchpad/AE_xsubdln4_msx2.out](../../../scratchpad/AE_xsubdln4_msx2.out); decoded by [scratchpad/xsubdln_decode.py](../../../scratchpad/xsubdln_decode.py)).
>
> Goldfish pass 1 (test writer) 2026-11-23: 7 findings, 5 measured, 0 moved to open.

## Summary

An entry at sub-ROM $0121, named DELLNO by the MSX Assembly Page's list only; the MSX2 Technical
Handbook does not list it. In the text modes it deletes one screen row: the row given in L (counted
from 1) disappears, the rows below it up to the last text row move up one, and the last text row is
cleared to spaces. LINTTB moves with the rows, and the byte at $FBCA goes down by one. The cursor is not
moved. The three references behave the same, except for the interrupt state on return. C-BIOS has no
routine here: the call returns at once. Shared facts: [the screen-modes page](../concepts/screen-modes.md).

## The specification

Case numbers `[M r n]` are the decoder's: r = `xsubdln` (round 1, cases 0-16 are DELLNO), `xsubdln2` (round 2,
cases 0-9), `xsubdln3` (round 3, cases 0-5), `xsubdln4` (round 4, cases 0-15 are DELLNO: other BC / DE, L 128 / 255,
CNSDFG 1, a 0 in LINTTB[22] / [23], and LINLEN / LINL40 / LINL32 / NAMBAS / TXTNAM set after CHGMOD). Every case fills 27 name-table rows with a row-tagged pattern,
LINTTB[i] := $C0 + i, CSRX / CSRY 15 / 12, CRTCNT 24 unless stated; the same on all three references unless a
machine is named.

Below, **last** is the last text row, counted from 0: **CRTCNT − 1 + CNSDFG**, as a byte — CRTCNT − 1 with the key
line off (CNSDFG 0), CRTCNT − 2 with it on (CNSDFG $FF) [M xsubdln 0, 8, 15], and CRTCNT with CNSDFG $01 (row 24 is
the one cleared at CRTCNT 24) [M xsubdln4 5]. So the rule is not "CRTCNT − 2 for any non-zero CNSDFG". Only $00,
$01 and $FF were measured.

**Interface.**
- Not published: the handbook's sub-ROM listing goes from DSPFNK ($011D) to WRTVDP ($012D) [P App. 1, SUB-ROM].
  An entry on all three references [M xsubdln 0-16].
- In: **L = the screen row, counted from 1** (L 5 deletes row 4, L 9 row 8, L 1 row 0) [M xsubdln 0, 1, 5].
  H, A, CSRX, CSRY, BC and DE are not inputs: H 20, A 3, the cursor at (3, 18), and BC $2468 / DE $9ABC give the
  same result as the base case [M xsubdln 2, 3, 4; xsubdln4 0].
- Out: no result is documented. Registers on return:
  - after a delete or a clear (the first two rules below): A = LINLEN, H = LINLEN + 1, L = last + 1, DE = the
    name-table offset of the first cleared cell (last × row length + the window's margin), IX = $0168, IY kept;
    BC = $0098 when rows moved, kept when only the last row was cleared ($B1C1, $2468); F $BB at LINLEN 40 and 60,
    $93 at 80, $B3 at 32 and 37, $9B at 30, 29 and 72 [M xsubdln 0, 6, 10, 11, 12, 15; xsubdln2 8, 9; xsubdln4 1, 8,
    11, 13, 14]. These are the values
    [EOL](../main/EOL.md) returns for H 1, L = last + 1 (its page): that DELLNO ends in the same code is [A];
  - after the early return (L > last + 1): A = (last + 1) − L as a byte ($FF, $FE, $98, $19 for L 25, 26, 128,
    255 at CRTCNT 24), F = the flags of that `SUB` ($BB, $BB, $8F, $1B: bits 5 / 3 from the result, P/V the
    overflow, C set); BC, DE, HL and IX ($0121) kept (also BC $2468 / DE $9ABC) [M xsubdln 7; xsubdln3 1-4;
    xsubdln4 2-4].
- Interrupts on return, entered with DI: **after a delete or a clear, ON on the HB-F900 and NMS 8250, OFF on the
  FS-A1WSX** [M xsubdln 0-6, 8, 10-16; xsubdln2 0-9; xsubdln3 0, 5; xsubdln4 0, 1, 5-15]; after the early return
  ON on all three [M xsubdln 7; xsubdln3 1-4; xsubdln4 2-4]. Entered with EI: on [M xsubdln 9].

**Behaviour.**
- **L − 1 before last (L 1 to last):** the rows L .. last move up one (row r := the old row r + 1 for
  L − 1 ≤ r < last), and row last := $20 over the text window [M xsubdln 0, 1, 5, 8, 10, 11, 15, 16]. The
  deleted row's content is gone. Rows after last are not touched: row 23 with the key line on, rows 24-26, and rows 20-23
  with CRTCNT 20 [M xsubdln 0, 8, 15].
- **L − 1 = last:** row last := $20; nothing moves [M xsubdln 6; xsubdln3 0].
- **L > last + 1, unsigned** (L 25, 26, 128 and 255 at CRTCNT 24, L 21 and 22 at CRTCNT 20, L 24 with the key line
  on): nothing changes — VRAM, LINTTB and $FBCA as found [M xsubdln 7; xsubdln3 1-4; xsubdln4 2-4]. The test is on L
  itself, not on L − 1: L 0 is not early (below).
- **L 0** does what L 1 does (row 0 deleted, rows 1-23 up, row 23 cleared, the same registers) [M xsubdln 5;
  xsubdln3 5].
- **The text window only:** with LINLEN below the screen width, only LINLEN cells of each row move or are
  cleared, from column ⌊(W − LINLEN + 1) / 2⌋; the columns outside keep their old content. Measured: LINLEN 37 →
  columns 2-38, LINLEN 30 → columns 5-34, SCREEN 1 LINLEN 29 → columns 2-30 [M xsubdln2 7, 8, 9]. At width 80 and
  SCREEN 1 width 32 the whole row [M xsubdln 10, 11]. The margin follows **LINLEN**, not LINL40 / LINL32 (LINLEN 37,
  LINL40 33, LINL32 29 → margin 2; SCREEN 1 LINLEN 29, LINL32 25 → 2; 80 columns LINLEN 72, LINL40 75 → 4)
  [M xsubdln4 9, 10, 11].
- **The row width W** is 32 when SCRMOD ≠ 0 (SCREEN 1, also with LINLEN 40); in SCREEN 0 it is **80 when LINLEN >
  40, else 40, whatever the VDP's 40 / 80-column mode**: the 80-column mode with LINLEN 40 moved 40-cell rows
  (DE $0398 = 23 × 40), the 40-column mode with LINLEN 60 moved 80-cell rows (DE $073A = 23 × 80 + 10), LINLEN 29
  in SCREEN 0 used W 40 (DE $039E = 23 × 40 + 6) [M xsubdln4 12, 13, 14, 15]. With LINLEN > W (SCREEN 1, LINLEN 40)
  the margin is the byte W − LINLEN + 1 halved unsigned, $F9 / 2 = 124 (DE $035C = 23 × 32 + 124) [M xsubdln4 15].
  The same rule as [PUTVRM](PUTVRM.md)'s.
- **The table is NAMBAS ($F922)**, not TXTNAM / T32NAM or the VDP's R#2 table: with NAMBAS $2000, TXTNAM $3000 and
  R#2's table at $0000 the rows at $2000 moved and the 27 rows at $0000 kept their sum (SCREEN 1: NAMBAS $3000, the
  table at $1800 unchanged) [M xsubdln4 9, 10, 11].
- **LINTTB** moves with the rows: LINTTB[r] := the old LINTTB[r + 1] for L − 1 ≤ r < last, then LINTTB[last] :=
  $AF; on the clear-only path LINTTB[last] := $AF alone [M xsubdln 0, 5, 6, 8, 15]; $AF is a constant: with
  LINTTB[last] = 0 it is still $AF, on both paths (the 0 moves to LINTTB[last − 1] on a delete) [M xsubdln4 7, 8].
  Entries after last are kept [M xsubdln 8, 15] (in xsubdln 0, 5 and 6 last = 23, the last entry, so there are
  none after it).
  A 0 entry (a continued logical line) moves like any other and the delete is still one screen row:
  LINTTB[5] = 0 → LINTTB[4] = 0 after it; LINTTB[4] = 0 is dropped with its row; LINTTB[22] = 0 → LINTTB[21] = 0
  [M xsubdln 13, 14; xsubdln4 6].
- With CNSDFG $01 (last = 24 at CRTCNT 24) "LINTTB[24]" is $FBCA: LINTTB[23] := the old $FBCA and $FBCA := $AF,
  its decrement lost under that write [M xsubdln4 5]. A state BASIC does not produce; it shows the routine indexes
  LINTTB by last without a bound.
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
0-16; xsubdln2 0-9; xsubdln3 0-5; xsubdln4 0-15].

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every byte a case writes is as on the FS-A1WSX, on both models; the only difference is the capture's last byte (xsubdln, xsubdln4) or the RAM past the last record (xsubdln2, xsubdln3), which no case writes (power-on RAM) [M] ([AE_trall/xsubdln.out](../../../scratchpad/AE_trall/xsubdln.out), [AE_trall/xsubdln2.out](../../../scratchpad/AE_trall/xsubdln2.out), [AE_trall/xsubdln3.out](../../../scratchpad/AE_trall/xsubdln3.out), [AE_trall/xsubdln4.out](../../../scratchpad/AE_trall/xsubdln4.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

- The graphic and bitmap modes (SCREEN 2-8): EOL and CLRTXT write text-mode cells there; DELLNO is not measured.
- CNSDFG values other than $00 / $01 / $FF; CRTCNT above 24 (a 26.5-row R#9 screen).
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
