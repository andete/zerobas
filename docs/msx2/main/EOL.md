<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `EOL` ($0168) — clear to the end of a line

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX (identical on all three;
> [xeol.asm](../../../probes/bios/spec/xeol.asm), [scratchpad/AE_xeol_msx2.out](../../../scratchpad/AE_xeol_msx2.out),
> decoded by `scratchpad/xeol_decode.py`).
> Goldfish pass 1 (test writer) 2026-11-23: 6 findings, 4 measured (cases 21-30 and the cells around LINTTB: the
> graphic-mode count and offset, the odd centring margin, H 42 / 255, the L 0 write), 2 citations corrected.

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
- **The first cell** is at offset (L - 1) x W + (H - 1) + M from the name-table base, where W is the screen's row width
  (40 or 80 in SCREEN 0, 32 in SCREEN 1 and in the graphic modes), M the centring margin
  ((W - LINLEN + 1) AND $FF) >> 1, and H - 1, L - 1 and M 8-bit values; DE returns this offset [M 0-30]. The margin is
  the rounded-UP half of the unused columns: LINLEN 39, 29 on the 40-column screen start at column 1, 6; LINLEN 75 on
  the 80-column screen at column 3; LINL32 29 in SCREEN 1 at column 2; LINLEN 30 at width 40 at column 5 [M 3, 25-28].
  The clear covers the text window, not the screen row.
- **How many cells:** the cells are consecutive from the first; it behaves as "clear the cell, H := H + 1 (8-bit),
  repeat while H <= LINLEN" -- LINLEN - H + 1 cells for H 1 .. LINLEN [M 0-5, 8-11, 13-28]; exactly one cell for H
  above LINLEN: H 41 clears row 3 column 0 (the cell after row 2's end), H 42 row 3 column 1 [M 7, 29]; H 0 (column 255)
  clears 41 cells from offset $014F, H 255 (column 254) 42 from $014E -- H wraps through 0 and counts on to LINLEN
  [M 6, 30]. H at the last column (40, 80, 32 in SCREEN 1): one cell [M 8, 9, 18].
- **One screen row only:** with LINTTB entry 0 for row 2 or row 3 (a continued logical line either way) the clear is
  36 cells of row L - 1 alone: row 2 for L 3 (cases 4, 5, 20), row 3 for L 4 (case 19) [M 4, 5, 19, 20].
- **The LINTTB write:** the byte at $FBB1 + L (16-bit: LINTTB - 1 + L) becomes $AF -- LINTTB[L - 1] for L 1-24; every
  other entry is left as found (a 0 stays 0) [M 0-11, 14-30]. **L 0 writes $AF to $FBB1** (LINTTB - 1, BASROM in the
  [RAM map](../../ram-map.md)) and **L 25 to $FBCA** (LINTTB + 24, FSTPOS's low byte); LINTTB[0-23] and $FCB1 (LINTTB
  + 255) are left alone [M 12, 13] (the probe presets $FBB1, $FBCA and $FCB1 to $3C and reads them back).
- **The cursor and the key line:** CSRX / CSRY stay (20, 10); CNSDFG is not changed [M 0-20]. L 24 clears row 23 with
  the key line off or on (CNSDFG $00 / $FF), nothing scrolls [M 10, 11].
- **Out-of-range rows:** L 25 clears row 24 (name table offset $03C4, past the 24-row screen) [M 13]; L 0 changes
  nothing in rows 0-26 -- DE comes back $27DC = 255 x 40 + 4, row L - 1 taken as 255, past the checked span [M 12].
- **Bitmap and graphic modes:** the same rule with W = 32, LINLEN as it stands (CHGMOD to SCREEN 2 / 5 / 8 does not
  change it), base $1800 in SCREEN 2 and $0000 in SCREEN 5 and 8. With LINLEN 40, H 5 L 3: 36 bytes of $20 at offset
  $C0 (2 x 32 + 4 + M, M = ($F9) >> 1 = $7C) [M 14-16]; with LINLEN 30 (set by a SCREEN 0 width-30 case just before):
  26 bytes at offset $45 (2 x 32 + 4 + 1) in SCREEN 2 and SCREEN 5 [M 22, 24]. LINTTB's entry := $AF as in text mode
  [M 14-16, 22, 24].
- **Registers:** IX, IY and the alternate set are kept [M 0-30]. The rest come back with: A = LINLEN, H = the H the
  loop ended on (LINLEN + 1 for H 0 .. LINLEN and H 255; H + 1 for H above LINLEN: H 41 -> 42, H 42 -> 43), L = the
  entry L, DE = the first cleared cell's offset from the name-table base, BC kept [M 0-30] (published as "all
  change").
- **Interrupts are ON on return**, entered with interrupts off or on [M 0-30].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject):
- **H past the row's end:** H 41 at width 40 -- C-BIOS clears the whole checked span, all 1080 cells of rows 0-26;
  H 42 -- 255 cells from row 3 column 1; the references clear one cell in both [M 7, 29]. (H 0 and H 255 match.)
- Registers on return differ (A $20, F $43, BC $0000, DE = CSRX / CSRY, HL = the first cell's address), which the
  published "all registers change" allows [M 0-30].
- Everything else above matches, including the graphic-mode offsets, the odd margins and the $FBB1 / $FBCA writes for
  L 0 / L 25 [M 0-30].

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every byte a case writes is as on the FS-A1WSX, on both models; the only difference is the capture's last byte, which no case writes (power-on RAM) [M] ([AE_trall/xeol.out](../../../scratchpad/AE_trall/xeol.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

- SCREEN 3, 4, 6, 7 (W = 32 and the base there are [A] from SCREEN 2 / 5 / 8); other H / L in graphic modes (one H, L
  per LINLEN measured).
- EL-13: the cursor shown (CSRSW) at the cleared position.
- Whether L 0 really writes at offset $27DC (only DE says so: it is past the probe's span).
- Stack depth and time.

## Related pages

[region page](README.md); [CHPUT](../../bios/CHPUT.md) (`ESC K`), [screen editor](../../concepts/screen-editor.md),
[screen modes](../../concepts/screen-modes.md).

## Tests that cover it

None yet.
