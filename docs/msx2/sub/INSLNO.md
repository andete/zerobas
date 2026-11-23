<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `INSLNO` (sub-ROM $0125) — insert a blank screen row (interface unpublished)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubdln.asm](../../../probes/bios/spec/xsubdln.asm), [xsubdln2.asm](../../../probes/bios/spec/xsubdln2.asm), [xsubdln3.asm](../../../probes/bios/spec/xsubdln3.asm); [scratchpad/AE_xsubdln_msx2.out](../../../scratchpad/AE_xsubdln_msx2.out), [scratchpad/AE_xsubdln2_msx2.out](../../../scratchpad/AE_xsubdln2_msx2.out), [scratchpad/AE_xsubdln3_msx2.out](../../../scratchpad/AE_xsubdln3_msx2.out); round 4 [xsubdln4.asm](../../../probes/bios/spec/xsubdln4.asm), [scratchpad/AE_xsubdln4_msx2.out](../../../scratchpad/AE_xsubdln4_msx2.out); decoded by [scratchpad/xsubdln_decode.py](../../../scratchpad/xsubdln_decode.py)).
>
> Goldfish pass 1 (test writer) 2026-11-23: 6 findings, 5 measured, 0 moved to open.

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
cases 10-19), `xsubdln3` (round 3, cases 6-11), `xsubdln4` (round 4, cases 16-31 are INSLNO: other BC / DE, L 128 / 255,
CNSDFG 1, a 0 in LINTTB[22] / [23], and LINLEN / LINL40 / LINL32 / NAMBAS / TXTNAM set after CHGMOD). Every case fills 27 name-table rows with a row-tagged pattern,
LINTTB[i] := $C0 + i, CSRX / CSRY 15 / 12, CRTCNT 24 unless stated; the same on all three references unless a
machine is named.

**last** is the last text row, counted from 0: **CRTCNT − 1 + CNSDFG**, as a byte — CRTCNT − 1 with the key line
off (CNSDFG 0), CRTCNT − 2 with it on (CNSDFG $FF) [M xsubdln 17, 25, 32], and CRTCNT with CNSDFG $01 (old row 23
moves to row 24) [M xsubdln4 21]; not "CRTCNT − 2 for any non-zero CNSDFG". Only $00, $01 and $FF were measured.

**Interface.**
- Not published: the handbook's sub-ROM listing goes from DSPFNK ($011D) to WRTVDP ($012D) [P App. 1, SUB-ROM].
  An entry on all three references [M xsubdln 17-33].
- In: **L = the screen row, counted from 1** (L 5 inserts at row 4, L 9 at row 8, L 1 at row 0) [M xsubdln 17,
  18, 22]. H, A, CSRX, CSRY, BC and DE are not inputs: H 20, A 3, the cursor at (3, 18) and BC $2468 / DE $9ABC
  give the same result as the base case [M xsubdln 19, 20, 21; xsubdln4 16].
- Out: no result is documented. Registers on return:
  - after an insert or a clear (the first two rules below): A = LINLEN, H = LINLEN + 1, L = the entry L, DE = the
    name-table offset of the first cleared cell (row L − 1's, plus the window's margin), IX = $0168, IY kept;
    BC = $0098 when rows moved, kept when only the last row was cleared ($B1C1, $2468); F $BB at LINLEN 40 and 60,
    $93 at 80, $B3 at 32 and 37, $9B at 30, 29 and 72 [M xsubdln 17, 23, 27, 28, 29; xsubdln2 18, 19; xsubdln4 17,
    24, 27, 29, 30]. These are the values
    [EOL](../main/EOL.md) returns for H 1 and the same L (its page): that INSLNO ends in the same code is [A];
  - after the early return (L > last + 1): A = (last + 1) − L as a byte ($FF, $FE, $98, $19 for L 25, 26, 128,
    255 at CRTCNT 24), F = the flags of that `SUB` ($BB, $BB, $8F, $1B), **H = last + 1** (24 at CRTCNT 24, 20 at
    CRTCNT 20, 23 with the key line on), L, BC, DE and IX ($0125) kept (also BC $2468 / DE $9ABC) [M xsubdln 24;
    xsubdln3 7-10; xsubdln4 18-20].
- Interrupts on return, entered with DI: **after an insert or a clear, ON on the HB-F900 and NMS 8250, OFF on the
  FS-A1WSX** [M xsubdln 17-23, 25, 27-33; xsubdln2 10-19; xsubdln3 6, 11; xsubdln4 16, 17, 21-31]; after the early
  return ON on all three [M xsubdln 24; xsubdln3 7-10; xsubdln4 18-20]. Entered with EI: on [M xsubdln 26].

**Behaviour.**
- **L − 1 before last (L 1 to last):** the rows L − 1 .. last − 1 move down one (row r := the old row r − 1 for
  L − 1 < r ≤ last); the old row last is lost; row L − 1 := $20 over the text window [M xsubdln 17, 18, 22, 25, 27,
  28, 32, 33]. Rows after last are not touched: row 23 with the key line on, rows 24-26, and rows 20-23 with
  CRTCNT 20 [M xsubdln 17, 25, 32].
- **L − 1 = last:** row last := $20; nothing moves [M xsubdln 23; xsubdln3 6].
- **L > last + 1, unsigned** (L 25, 26, 128 and 255 at CRTCNT 24, L 21 and 22 at CRTCNT 20, L 24 with the key line
  on): nothing changes — VRAM, LINTTB and $FBCA as found [M xsubdln 24; xsubdln3 7-10; xsubdln4 18-20]. The test is
  on L itself, not on L − 1: L 0 is not early (below).
- **L 0:** rows 1 .. last := the old rows 0 .. last − 1, and row 0 is NOT cleared (it keeps its old content, so
  rows 0 and 1 are the same); DE comes back $27D8 = 255 × 40, the clear aimed at row 255, outside the 27 rows read
  [M xsubdln3 11]. What it wrote there is not measured.
- **The text window only:** with LINLEN below the screen width, only LINLEN cells of each row move or are
  cleared, from column ⌊(W − LINLEN + 1) / 2⌋; the columns outside keep their old content. Measured: LINLEN 37 →
  columns 2-38, LINLEN 30 → columns 5-34, SCREEN 1 LINLEN 29 → columns 2-30 [M xsubdln2 17, 18, 19]. At width 80 and
  SCREEN 1 width 32 the whole row [M xsubdln 27, 28]. The margin follows **LINLEN**, not LINL40 / LINL32 (LINLEN 37,
  LINL40 33, LINL32 29 → margin 2; SCREEN 1 LINLEN 29, LINL32 25 → 2; 80 columns LINLEN 72, LINL40 75 → 4)
  [M xsubdln4 25, 26, 27].
- **The row width W** is 32 when SCRMOD ≠ 0 (SCREEN 1, also with LINLEN 40); in SCREEN 0 it is **80 when LINLEN >
  40, else 40, whatever the VDP's 40 / 80-column mode**: the 80-column mode with LINLEN 40 moved 40-cell rows (DE
  $00A0 = 4 × 40), the 40-column mode with LINLEN 60 moved 80-cell rows (DE $014A = 4 × 80 + 10), LINLEN 29 in
  SCREEN 0 used W 40 (DE $00A6 = 4 × 40 + 6) [M xsubdln4 28, 29, 30, 31]. With LINLEN > W (SCREEN 1, LINLEN 40) the
  margin is the byte W − LINLEN + 1 halved unsigned, $F9 / 2 = 124 (DE $00FC = 4 × 32 + 124) [M xsubdln4 31]. The
  same rule as [PUTVRM](PUTVRM.md)'s and [DELLNO](DELLNO.md)'s.
- **The table is NAMBAS ($F922)**, not TXTNAM / T32NAM or the VDP's R#2 table: with NAMBAS $2000, TXTNAM $3000 and
  R#2's table at $0000 the rows at $2000 moved and the 27 rows at $0000 kept their sum (SCREEN 1: NAMBAS $3000, the
  table at $1800 unchanged) [M xsubdln4 25, 26, 27].
- **LINTTB:** LINTTB[L − 1] := $AF; LINTTB[r] := the old LINTTB[r − 1] for L − 1 < r < last; and **LINTTB[last] :=
  $FB**, not the old LINTTB[last − 1] (at CRTCNT 24 and 20, key line off and on) [M xsubdln 17, 18, 22, 25, 32,
  33]. On the clear-only path LINTTB[last] := $AF alone [M xsubdln 23; xsubdln3 6]. At L 0: LINTTB[0] kept,
  LINTTB[1 .. last − 1] := the old [0 .. last − 2], LINTTB[last] := $FB [M xsubdln3 11]. Entries after last are kept.
  A 0 entry moves like any other: LINTTB[5] = 0 → LINTTB[6] = 0, LINTTB[4] = 0 → LINTTB[5] = 0, and the insert is
  still one screen row [M xsubdln 30, 31]. **$FB does not come from the old entries**: with LINTTB[last − 1] = 0
  or LINTTB[last] = 0 (every earlier old value was $C0 or more), LINTTB[last] is still $FB — the 0 in LINTTB[last − 1]
  is lost, as the old last entry always is — and the clear-only path still writes $AF over a 0 [M xsubdln4 22, 23,
  24]. Whether $FB follows LINTTB's address is [A] (LINTTB cannot be moved).
- With CNSDFG $01 (last = 24 at CRTCNT 24) "LINTTB[24]" is $FBCA, and it becomes $FB [M xsubdln4 21] — a state BASIC
  does not produce; the routine indexes LINTTB by last without a bound.
- **$FBCA and $FBCB are kept** (values 3, 4, 5, 6, 24, 0, 30) [M xsubdln2 10-19] (except as LINTTB[24] above) — unlike DELLNO, which decrements
  $FBCA.
- **Not changed:** CSRX, CSRY, CNSDFG, CRTCNT, LINLEN, SCRMOD; the key-line row (row 23 with CNSDFG $FF) is not
  redrawn [M xsubdln 17-33].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) have no routine at $0125: the address holds the RET filler of C-BIOS's
`sub.asm`, and the call returns at once — nothing moves or is cleared, LINTTB stays as found, every register comes
back as it went in (IX $0125), and the interrupt state is kept (off when entered with DI) [M xsubdln 17-33;
xsubdln2 10-19; xsubdln3 6-11; xsubdln4 16-31].

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every byte a case writes is as on the FS-A1WSX, on both models; the only difference is the capture's last byte (xsubdln, xsubdln4) or the RAM past the last record (xsubdln2, xsubdln3), which no case writes (power-on RAM) [M] ([AE_trall/xsubdln.out](../../../scratchpad/AE_trall/xsubdln.out), [AE_trall/xsubdln2.out](../../../scratchpad/AE_trall/xsubdln2.out), [AE_trall/xsubdln3.out](../../../scratchpad/AE_trall/xsubdln3.out), [AE_trall/xsubdln4.out](../../../scratchpad/AE_trall/xsubdln4.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

- The graphic and bitmap modes (SCREEN 2-8).
- CNSDFG values other than $00 / $01 / $FF; CRTCNT above 24.
- The VRAM L 0 writes at offset $27D8.
- Whether the moved rows are copied cell by cell from the row above at every LINLEN (only rows 4, 5 and 23 are
  dumped in full, at LINLEN 37, 30 and 29).
- The FS-A1WSX's interrupt state after an insert (EXTROM's handling or the routine's).
- Stack depth and time.

## Related pages

[DELLNO](DELLNO.md); [EOL](../main/EOL.md); [CLRTXT](CLRTXT.md); [the screen-modes page](../concepts/screen-modes.md);
the MSX1 [screen editor](../../concepts/screen-editor.md) and [CHPUT](../../bios/CHPUT.md) (`ESC L`, insert line).

## Tests that cover it

none yet
