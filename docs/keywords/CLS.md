<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `CLS` — clear the screen

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors: not applicable · RAM usage not yet proven · every error not yet
> proven. One recorded difference: `CLS` followed by junk (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CLS` erases the text screen and puts the cursor in the top-left corner,
row 0, column 0. The function-key line at the bottom of the screen, when it is
shown, stays where it is. zerobas behaves like the Philips VG-8020 in every
case we have measured except one malformed spelling, `CLS 1`.

## Syntax

```
CLS
```

No arguments. Anything after `CLS` other than the end of the statement (`:`
or the end of the line) is a `Syntax error`.

## Details

- **The cursor goes home.** After `CLS`, [`CSRLIN`](CSRLIN.md) is 0 and
  [`POS(0)`](POS.md) is 0.
- **The function-key line survives.** With the key line on (the power-on
  state, or after `KEY ON`), the VG-8020 keeps `color auto goto list run` on
  the bottom row across a `CLS`, and so does zerobas. After `KEY OFF` the
  bottom row stays blank. See [`KEY`](KEY.md).
- **The rest of the line runs**: `CLS:PRINT "X"` prints `X` on row 0.
- **There is no common error to get wrong.** `CLS` takes nothing that could be
  out of range or of the wrong type, so the "common errors" rung is declared
  not applicable (Joost, 2026-09-29: *"go with (A)"*).
- **Its only error is junk after it**, `Syntax error` (error 2) — see
  *Differences*.

## Example

`CLS` wipes everything on the screen, including the program listing and the
`RUN` line, so what is left after the run is only what the program prints
afterwards:

```
10 PRINT "This text is wiped"
20 CLS
30 R=CSRLIN:C=POS(0)
40 PRINT "Cursor at";R;C
RUN
Cursor at 0  0
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_cls.out`](../../scratchpad/kwdoc_cls.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**`CLS 1` and `CLS,` clear the screen here before reporting their error.**
Both machines answer `Syntax error`, but the VG-8020 checks for the stray
argument first and leaves the screen intact, while zerobas clears the screen
and then raises the error (D-BAREEXTRA, found 2026-09-27, filed in
[TODO.md](../../TODO.md) as a TIER 6 item; `END 1` has the same shape). The
error code and line agree; the screen does not. It is the reason the "every
error" rung is not ticked.

The other rung not yet proven is **RAM usage**: `CLS` moves free memory the
same way on both machines, but the set of documented work-area cells each
one writes is not the same.

## What we found, and how

- **`CLS` erased the function-key line** (fixed 2026-09-26, D-KEYCLS). C-BIOS's
  own screen clear wipes all 24 rows, so the bottom row came back blank where
  the VG-8020 keeps the labels. `SCREEN 0` and a `WIDTH` change had the same
  problem, and also gave the key row back to the scrolling text. zerobas now
  repaints the line and re-reserves the row after all three.
- **The first test could not tell a working `CLS` from one that did nothing.**
  It printed a bare marker after `CLS`, which a `CLS` that parsed and cleared
  nothing prints just as happily. The row now reads `CSRLIN` back after the
  clear, so it only passes if the cursor really went home.
- **Junk after `CLS` is checked too late** (found 2026-09-27, D-BAREEXTRA, still
  open): the statement-end check runs after the clear instead of before it.

## Where it lives

`ex_cls` in [basic/screen.asm](../../basic/screen.asm) calls the BIOS screen
clear, then `key_repaint` in the same file puts the function-key line back
through the key-string tenant in [sub/keystr.asm](../../sub/keystr.asm).

## Tests that cover it

- `make kwsweep` — the everyday row: `CLS`, then `CSRLIN` must read 0.
- `make kwram` — the RAM-usage comparison.
