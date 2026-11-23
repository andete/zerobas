<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `EOL` ($0168) — clear to the end of a line

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX (identical on all three;
> [xeol.asm](../../probes/bios/spec/xeol.asm), [scratchpad/AE_xeol_msx2.out](../../scratchpad/AE_xeol_msx2.out),
> decoded by `scratchpad/xeol_decode.py`).

## Summary

`EOL` clears one screen row of the text screen from a given position to the row's end, writing spaces
into the name table. The position comes in HL, H the column and L the row, counted from 1 like CSRX /
CSRY. The cursor does not move, a continued logical line's next rows are not cleared, and the row's
LINTTB entry is rewritten. It ends with interrupts enabled.

## The specification

**Interface.**
- In: H = the X coordinate, L = the Y coordinate [P A1]. Out: none [P A1]. Changes: all registers [P A1].

**Measured** [M] (case numbers are the decoder's; every case fills the span it reads with an address-dependent
pattern, puts the cursor at (20, 10), CRTCNT 24, LINTTB[i] := $C0 + i; identical on all three references):
- **What is cleared:** the name-table cells of screen row L - 1 (0-based), from column H - 1 to the row's last
  column LINLEN - 1, each := $20; nothing else in the name table (27 rows checked) [M 0-2, 20]: SCREEN 1 H 5 L 3 -> 28
  cells from row 2 column 4 (case 0); SCREEN 0 width 40 H 1 L 1 -> the whole first row (case 1); width 80 H 30 L 3 ->
  51 cells from column 29 of row 2 (case 2).
- **LINLEN below the screen width** (LINL40 30 on the 40-column screen, case 3): from column 4 + the centring margin 5
  = 9, 26 cells -- the clear covers the text window, not the screen row [M 3].
- **H at the last column** (40 at width 40, 80 at width 80, 32 in SCREEN 1): exactly one cell [M 8, 9, 18].
- **H past the end** (41 at width 40): one cell, the FIRST cell of the next row (row 3 column 0) [M 7].
  **H 0:** 41 cells from name-table offset $014F -- column H - 1 taken as 255 [M 6].
- **One screen row only:** with row 2's or row 3's LINTTB entry 0 (a continued logical line either way) the clear is
  the same 36 cells of row 2 [M 4, 5, 19, 20].
- **LINTTB:** the entry of row L - 1 becomes $AF; every other entry is left as found (a 0 stays 0) [M 0-11, 14-20].
  Row L 0 and L 25 leave LINTTB[0-23] alone [M 12, 13].
- **The cursor and the key line:** CSRX / CSRY stay (20, 10); CNSDFG is not changed [M 0-20]. L 24 clears row 23 with
  the key line off or on (CNSDFG $00 / $FF), nothing scrolls [M 10, 11].
- **Out-of-range rows:** L 25 clears row 24 (name table offset $03C4, past the 24-row screen) [M 13]; L 0 changes
  nothing in rows 0-26 -- DE comes back $27DC = 255 x 40 + 4, row L - 1 taken as 255, past the checked span [M 12].
- **Bitmap and graphic modes:** in SCREEN 5 and 8 it writes 36 bytes of $20 at VRAM $00C0, in SCREEN 2 at $18C0 (the
  name table + $C0), for H 5 L 3 -- the text-mode cells of a different offset ($C0, where width 40 gives $54); LINTTB's
  row-2 entry := $AF as in text mode [M 14-16]. One position only: how the offset follows H / L there is open.
- **Registers:** IX, IY and the alternate set are kept [M 0-20]. The rest come back with: A = LINLEN, H = LINLEN + 1,
  L = the entry L, DE = the first cleared cell's offset from the name-table base, BC kept [M 0-20] (published as "all
  change").
- **Interrupts are ON on return**, entered with interrupts off or on [M 0-20].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject):
- **H past the row's end** (H 41 at width 40): C-BIOS clears the whole checked span -- all 1080 cells of rows 0-26 --
  where the references clear one cell [M 7].
- Registers on return differ (A $20, F $43, BC $0000, DE = CSRX / CSRY, HL = the first cell's address), which the
  published "all registers change" allows [M 0-20].
- Everything else above matches, including the graphic-mode writes at $00C0 / $18C0 [M 0-20].

## Open (not measured)

- The graphic-mode offset's rule (one H / L measured), SCREEN 3, 4, 6, 7.
- EL-13: the cursor shown (CSRSW) at the cleared position.
- Whether L 0 really writes at offset $27DC (only DE says so); the byte past LINTTB that L 25 might write ($FBCA).
- Stack depth and time.

## Related pages

[region page](README.md); [CHPUT](../../bios/CHPUT.md) (`ESC K`), [screen editor](../../concepts/screen-editor.md),
[screen modes](../../concepts/screen-modes.md).

## Tests that cover it

None yet.
