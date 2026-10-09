<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `WIDTH` — set the number of text columns

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven. No known
> divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`WIDTH n` sets how many characters fit on a line of text: 1 to 40 in
`SCREEN 0`, 1 to 32 in `SCREEN 1`. Changing it clears the screen and centres
the narrower text area; asking for the width already in force does nothing at
all. zerobas behaves exactly like the Philips VG-8020 for every case we have
measured.

## Syntax

```
WIDTH <columns>
```

One numeric argument, always.

## Details

- **The limit depends on the screen mode**: 1..32 in `SCREEN 1`, and 1..40 in
  every other mode, the graphics modes included.
- **Each text mode remembers its own width.** `WIDTH` in `SCREEN 1` is kept in
  `LINL32` (`&HF3AF`), in any other mode in `LINL40` (`&HF3AE`); the width in
  force is `LINLEN` (`&HF3B0`). Going back to a mode brings back that mode's
  width: `SCREEN 0:WIDTH 32:SCREEN 1:SCREEN 0` is at width 32 again.
- **A new width clears the screen; the same width does not.** After
  `PRINT "KKKK":WIDTH 37` at width 37, the four K's and the cursor are still
  where they were.
- **The function-key line follows the width.** Its five fields shrink with
  narrower text, and at the narrowest widths (measured at 5 and 1) the line is
  blank. See [`KEY`](KEY.md).
- **Fractions are truncated before the check**: `WIDTH 40.9` is 40 and
  accepted, `WIDTH 41.9` is 41 and refused, `WIDTH -0.5` is 0 and refused.
- **A refused `WIDTH` changes nothing.**
- **The power-on width is 37** in `SCREEN 0` on the VG-8020, and on zerobas
  too. The National CF-3300 starts at 39. Where the two reference machines
  differ only in presentation, zerobas takes the VG-8020's value (Joost,
  2026-09-04: *"when there is stylish differences (color, screen) between the
  oracles, pick the VG8020"*; applied to the boot width on 2026-09-24).

### Errors

| you write | you get |
|---|---|
| `WIDTH 0`, `WIDTH 41` (in `SCREEN 1`: `WIDTH 33`), `WIDTH 256` | error 5, `Illegal function call` |
| `WIDTH 32768`, `WIDTH -32769` | error 6, `Overflow` |
| `WIDTH "40"`, `WIDTH A$` | error 13, `Type mismatch` |
| `WIDTH` on its own | error 24, `Missing operand` |
| `WIDTH ,` | error 2, `Syntax error` |
| `WIDTH 32,` | width 32 is applied, then error 2 |
| `WIDTH 41,` | error 5 — the range is checked before the stray comma |

## Example

```
10 PRINT "Width";PEEK(&HF3B0)
20 WIDTH 40
30 PRINT "Screen kept"
40 ON ERROR GOTO 80
50 WIDTH 41
60 WIDTH "A"
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
Width 40
Screen kept
Error 5
Error 13
```

The width is already 40, so line 20 does nothing and the listing stays on the
screen. A `WIDTH` to any other value would have cleared it.
Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_width.out`](../../scratchpad/kwdoc_width.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

Two rungs are not yet proven. **Every error**: the error sets of the two
"set a width" forms are measured and agree, but that of the third form, a
`WIDTH` to the width already in force, has not been measured on the reference.
**RAM usage**: the set of documented work-area cells each machine writes is
not the same.

## What we found, and how

- **Five ways to break the screen without an error** (fixed 2026-07-28,
  D-WID). `WIDTH 0`, `WIDTH 41` to `255`, `WIDTH "40"` and a bare `WIDTH` were
  all accepted and left the machine with no readable screen, where the
  VG-8020 refuses each one; and `SCREEN 2:WIDTH 29` stored the width for the
  wrong mode. Earlier the same day `WIDTH 300` itself had been fixed: its
  error was raised but the statement carried on and wrote the screen anyway
  ([width-vg8020-characterization.md](../width-vg8020-characterization.md),
  [spec-basic-width-domain.md](../spec-basic-width-domain.md)).
- **The instrument had to be pinned first.** A `WIDTH` changes the screen
  geometry that every screen-reading test depends on, so the measurement reads
  the width back with `PEEK` and restores a known width before printing
  anything.
- **The same width cleared the screen here** (fixed 2026-09-24, D-WIDTHKEEP).
  The VG-8020 keeps the screen when the width does not change. The existing
  test could not see it: it read `LINLEN`, which both machines set to the
  same value either way.
- **zerobas started at width 39** (fixed 2026-09-24, D-BOOTWIDTH), so every
  program that never set a width laid its text out differently from the
  VG-8020.
- **The function-key line ignored `WIDTH`** (fixed 2026-09-26, D-KEYWIDTH).
  24 widths were measured, and the rule for the line's layout was exact on
  all of them.

## Where it lives

`ex_width` in [basic/screen.asm](../../basic/screen.asm): the range check per
mode, the no-op test against `LINLEN`, then the BIOS mode switch to apply the
new width and `key_repaint` for the function-key line.

## Related concepts

- [The screen editor](../concepts/screen-editor.md) — typing, fixing and re-entering lines
- [Screen modes](../concepts/screen-modes.md) — the four MSX1 displays

## Tests that cover it

- `make width-acceptance` — the range in every mode, the four error kinds,
  truncation, ordering, and the per-mode memory.
- `make kwsweep` — one row per form (`SCREEN 0` width, `SCREEN 1` width, the
  same width) and the error rows for {5, 13, 24}.
- `make kwram` — the RAM-usage comparison.
