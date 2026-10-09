<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `COLOR` — set the foreground, background and border colours

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`COLOR fg,bg,border` sets the three screen colours, each a palette number
from 0 to 15. Any of the three can be left out, and a colour that is left out
keeps its current value. zerobas behaves exactly like the Philips VG-8020 for
every case we have measured, errors included.

## Syntax

```
COLOR [<foreground>] [, [<background>] [, <border>]]
```

Each argument is a numeric expression. At least one must be present.

## Details

- **The three values land in the documented work-area cells** `FORCLR`
  (`&HF3E9`), `BAKCLR` (`&HF3EA`) and `BDRCLR` (`&HF3EB`), so a program can
  read them back with `PEEK`. The example does.
- **An omitted position is skipped, not shifted.** `COLOR ,5` changes only the
  background; the foreground keeps its value. `COLOR ,,3` changes only the
  border. `COLOR ,4`, `COLOR 15,,4` and `COLOR ,,4` are all legal.
- **All or nothing.** If any argument is wrong, nothing changes: after a
  rejected `COLOR 7,99` the foreground is still what it was, on both machines.
- **The foreground is also the drawing colour.** `COLOR` copies the foreground
  into `ATRBYT`, the colour the graphics statements use when no colour is
  given (`COLOR 5` makes it 5; `COLOR ,1` leaves it at the foreground).

### Errors

| you write | you get |
|---|---|
| `COLOR 16`, `COLOR -1`, `COLOR 256`, `COLOR 15,99`, `COLOR 15,4,99` | error 5, `Illegal function call` |
| `COLOR "A"`, `COLOR ,"A"`, `COLOR 7,"A"` | error 13, `Type mismatch` |
| `COLOR` on its own | error 24, `Missing operand` |
| a trailing comma: `COLOR 15,4,`, `COLOR ,,` | error 24, `Missing operand` |
| a fourth argument: `COLOR 1,1,1,1` | error 2, `Syntax error` |

The range is checked on the whole number, so `COLOR 256` is an error even
though its low byte is 0. The error set for the three positions is
{5, 13} for the foreground and the background and {2, 5, 13} for the border,
the same on both machines.

## Example

```
10 COLOR 7,4
20 COLOR ,5
30 PRINT PEEK(&HF3E9);PEEK(&HF3EA)
40 ON ERROR GOTO 80
50 COLOR 1,99
60 PRINT PEEK(&HF3E9);PEEK(&HF3EA)
70 COLOR 15,4,4:END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 7  5
Error 5
 7  5
```

Line 20 changes only the background. Line 50 is rejected as a whole: the
foreground does not become 1.
Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_color.out`](../../scratchpad/kwdoc_color.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `COLOR` moves free memory the
same way on both machines, but the set of documented work-area cells each one
writes is not the same.

## What we found, and how

The first three were found in one night (2026-09-07/08), each by a different
sweep over the argument shapes of every statement; the fourth turned up in the
fix for the third. `COLOR` was, at that point, the least-checked statement in
the tree.

- **A bare `COLOR` re-applied the current colours** where both references say
  `Missing operand` (fixed 2026-09-07, D-BAREFIX).
- **A trailing comma was accepted** — `COLOR 15,4,` and `COLOR ,,` did nothing
  and raised nothing; every other statement already refused its trailing comma
  (fixed 2026-09-08, D-OMITARG).
- **No range check at all** (fixed 2026-09-08, D-DOMAIN): `COLOR 16`,
  `COLOR 99` and `COLOR 256` were accepted. Measuring the boundary showed 15 is
  the last legal value and that 256 must be caught too.
- **A rejected `COLOR` was half applied** (fixed 2026-09-08, D-PARTIAL).
  `COLOR 7,99` stored the 7 and then refused the 99; the references change
  nothing. And `COLOR 7,"A"` left the background at 0, a value nobody asked
  for. The fix keeps the new colours in a shadow and copies them into place
  only after the whole statement has been checked.
- **`COLOR` did not set the drawing colour cell `ATRBYT`** (fixed 2026-09-25,
  D-ADDR29), found by comparing which work-area cells each machine writes.
- **The tests read two cells, not one.** Each `COLOR` row reads the cell it
  must change and the foreground it must leave alone, so a parser that moved
  `,5` into the foreground position would fail.

## Where it lives

`ex_color` in [basic/screen.asm](../../basic/screen.asm). The range check
`clr_eval` and the shadow (`clr_prep`, `clr_commit`) are in
[basic/main.asm](../../basic/main.asm). The colours reach the screen through
the BIOS colour call.

## Related concepts

- [Screen modes](../concepts/screen-modes.md) — the four MSX1 displays

## Tests that cover it

- `make kwsweep` — one row per position (each reading two cells) and the
  error rows for {2, 5, 13}.
- `make kwram` — the RAM-usage comparison.
