<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no answers=JOOST|ABC|42|3,4|5,9|A,B -->

# `INPUT` — read a typed line into variables

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven. One
> recorded difference: text typed after a closing quote (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`INPUT` prints a prompt, waits for the user to type a line and press Enter,
and puts what was typed into one or more variables. `LINE INPUT` takes the
whole line, commas and all, into one string. `INPUT$(n)` reads exactly `n`
keys. This page covers the keyboard forms; reading
from a file, `INPUT #`, is part of file handling (see [`OPEN`](OPEN.md)).
zerobas behaves like the Philips VG-8020 in every case we have measured,
except one edge with quotes.

## Syntax

```
INPUT ["<prompt>";] <variable>[,<variable>...]
LINE INPUT ["<prompt>";] <string variable>
INPUT$(<count>)
```

A variable may be an array element: `INPUT A(3)`.

## Details

### `INPUT`

- **The prompt is `? `.** With a prompt string and `;`, the string is printed
  first: `INPUT "Name";N$` shows `Name? `. (A `,` in place of the `;` prints
  the string without the `? ` here; that form has not been compared with the
  reference yet.)
- **One typed line feeds the whole list**, split at commas: `INPUT X,Y`
  answered `3,4` gives `X=3`, `Y=4`.
- **Numbers are read the way `VAL` reads them**: `1.5`, `40000`, `1E3`,
  `-.025`, `&H10` (16) and `1D2` (100) all work. Blanks inside a number are
  ignored (`1 2` is 12). Only blanks may follow the number; `1-2` or `ABC` gets
  `?Redo from start`, and the whole line is asked for again with `? `. An empty
  field is 0.
- **Too many values**: the extra ones are dropped with `?Extra ignored`, and
  the program carries on with what fitted.
- **Strings**: leading blanks are dropped, blanks inside and at the end are
  kept up to the next comma. A field in quotes is taken exactly as written,
  commas and blanks included: `"A,B"` gives `A,B`.
- **Editing the answer** with the cursor keys, even across two screen rows,
  gives the same result as on the reference.

### `LINE INPUT`

- **The whole line goes into one string**, with its commas and its leading
  blanks: typed ` A,B C`, the variable holds ` A,B C`.
- **No `? ` is printed** — the example shows it.
- **The variable must be a string**: `LINE INPUT A` is `Type mismatch`
  (error 13).

### `INPUT$(n)`

- **Reads exactly `n` keys** and returns them as a string. The keys are not
  shown on the screen.
- `n` is 1 to 255. `INPUT$(0)`, `INPUT$(256)` and `INPUT$(-1)` are
  `Illegal function call` (error 5), a string count is `Type mismatch` (13)
  and a count outside the integer range is `Overflow` (6). These were measured
  on the CF-3300, and `INPUT$(0)` and the string count on the VG-8020 too.
- `INPUT$(n,#f)` (the `#` is optional) reads from an open file instead.

## Example

```
10 INPUT "Name";N$
20 INPUT A
30 INPUT X,Y
40 INPUT B
50 LINE INPUT L$
60 PRINT N$;A;X+Y;B;L$
RUN
Name? JOOST
? ABC
?Redo from start
? 42
? 3,4
? 5,9
?Extra ignored
A,B
JOOST 42  7  5 A,B
```

The replies typed were `JOOST`, `ABC`, `42`, `3,4`, `5,9` and `A,B`, each
followed by Enter. `ABC` is not a number, so line 20 asks again; `5,9` is one
value too many for line 40.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_input.out`](../../scratchpad/kwdoc_input.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**Text typed after a closing quote.** Typed at an `INPUT A$`, `"AB"CD` is
`?Redo from start` on the VG-8020; zerobas takes `AB`. Measured on 2026-09-30
([`inpquote_run.out`](../../scratchpad/inpquote_run.out)) and filed as a
TIER 6 item, D-INPQUOTE2, together with the same edge in files.

**Every error** is not yet proven: the full set of errors `INPUT` can raise
has not been listed and compared yet. **RAM usage** is not proven either: the
RAM comparison has rows only for the file form `INPUT #`, none yet for the
keyboard form.

## What we found, and how

- **Numbers were 16-bit integers only** (fixed 2026-09-29, D-INPNUM). `1.5`
  was `?Redo from start`, and `40000` was silently stored as −25536 — a wrong
  answer with no error. `INPUT` now uses `VAL`'s number reader, with the
  edge rules measured on the reference first
  ([`inpnum_run2.out`](../../scratchpad/inpnum_run2.out)).
- **Leading blanks of a string were kept**, and **a quoted field was split at
  its comma** (fixed 2026-09-29, D-INPSTR, and 2026-09-30, D-INPQUOTE). Both
  were measured on file and keyboard input alike, which share one field
  reader.
- **An array element could not be a target** (fixed 2026-08-08, D-ARYLV).
  `INPUT A(1)` was a `Syntax error`; both references accept any variable
  `LET` accepts ([inputary-msx1-characterization.md](../inputary-msx1-characterization.md)).
- **The messages were in lower case** (`?redo from start`) until 2026-08-02
  (D-MSGEXACT), when every message zerobas prints was made the reference's
  exact text.
- **`INPUT$(n)` from the keyboard did not exist** (added 2026-09-16,
  D-INPDCON); only the file form worked. `INPUT$(0)` and `INPUT$(256)`
  returned `""` until 2026-10-07 (D-INPUTDN).
- **The tests had a blind spot.** Until 2026-09-14 (D-KWRESPOND) the keyword
  sweep's two `INPUT` rows both drove the file form, so the keyboard
  statement had no row at all. Rows that type a reply were added then.

## Where it lives

- `input_console` in [basic/input.asm](../../basic/input.asm): the prompt, the
  variable list, `?Redo from start` / `?Extra ignored`, and `LINE INPUT`;
  `inp_num` there reads a number.
- `ex_input` / `ex_line` in [basic/files.asm](../../basic/files.asm) pick the
  keyboard or the file form; `read_into_strscr` there splits a line into
  fields for both.
- `str_inputd` in [basic/strvar.asm](../../basic/strvar.asm) is `INPUT$`.
- Design notes: [spec-basic-input.md](../spec-basic-input.md) (2026-07-11;
  its "integer fields" and "lower-case messages" no longer hold — this page is
  current).

## Related concepts

- [Files and devices](../concepts/files-and-devices.md) — numbered channels to the disk, the tape, the screen and the printer
- [The screen editor](../concepts/screen-editor.md) — typing, fixing and re-entering lines
- [Variables](../concepts/variables.md) — names, types, arrays, and where they live

## Tests that cover it

- `make input-acceptance` — numbers, strings, several variables, `LINE INPUT`,
  the prompt, `?Redo from start` and `?Extra ignored`, typed into both
  machines.
- `make inputary-acceptance` — array elements as targets.
- `make inputdn-acceptance` — `INPUT$`'s count rules.
- `make screditor-acceptance` — editing an answer with the cursor keys.
- `make kwsweep` — rows that type replies for each form, and `?Redo from
  start` as the common error.
