<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `DATA` — values stored in the program for `READ`

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven. No
> known difference (the line a bad item's error names, fixed 2026-10-10).
> Numbers like `1.5` read correctly since 2026-10-09.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`DATA` holds a list of constants — numbers or text — inside the program, for
[`READ`](READ.md) to take one at a time; [`RESTORE`](RESTORE.md) chooses where
reading starts. When the program runs past a `DATA` statement nothing happens:
it is only read. zerobas reads the same items as the Philips VG-8020 in every
case we have measured, with one open difference in an error case.

## Syntax

```
DATA <constant>[,<constant>]...
```

Each constant is a number, a quoted string or unquoted text. The statement ends
at the end of the line or at a `:` outside quotes.

## Details

- **`DATA` statements can be anywhere** — before the `READ`, after an `END`,
  in any line. `READ` takes the items in program order, line after line.
- **Unquoted text is taken as typed**, with leading spaces skipped and trailing
  spaces **kept**: `DATA PAD  ,X` reads back as `"PAD  "`. Spaces inside the
  text are kept too (`DATA HI THERE`).
- **Quotes protect commas and colons**: `DATA "A,B"` is one item, `A,B`, and
  `DATA "A:B":C=7` is one item and then runs `C=7`. The quotes are not part of
  the item, and inside them spaces at both ends are kept.
- **An unterminated quote runs to the end of the line**, so in
  `DATA "A:B:C=7` the `C=7` is part of the item and never runs.
- **An empty item** (`DATA 1,,3`) reads as 0 into a number and as an empty
  string into a string.
- **Digits read into a string variable stay text**: `DATA 42` read into `A$`
  is the two-character string `42`.
- **Text read into a number is `Syntax error`** (error 2), as on the reference
  — the commonest `DATA` mistake: a missing comma or a stray letter.
- **A string read from `DATA` uses no string space.** Like the reference,
  zerobas points the variable at the text inside the program instead of
  copying it, so a program can `READ` many long strings without a `CLEAR`.

## Example

```
10 DATA 4.2,"A,B",  HI THERE,,7
20 READ N,A$,B$,C$,D
30 PRINT N;A$;"|";B$;"|";C$;"|";D
40 ON ERROR GOTO 70
50 READ X
60 END
70 PRINT "Error";ERR:END
80 DATA ABC
RUN
 4.2 A,B|HI THERE|| 7
Error 2
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_data.out`](../../scratchpad/kwdoc_data.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

No known difference in behaviour.

The rung not yet proven is **RAM usage**.

## What we found, and how

- **A bad item's error named the `READ` line** (fixed 2026-10-10, D-READERL).
  For `20 DATA 12X` / `30 READ A` the VG-8020 says `Syntax error in 20`, the
  `DATA` line where the typo is: `ERL` is 20 and `LIST .` lists line 20, even
  when `READ A` is typed at the prompt; `RESUME NEXT` still goes on after the
  `READ` ([`readerl_run.out`](../../scratchpad/readerl_run.out)). zerobas named
  line 30. Fixing it showed a second fault: after a refused item zerobas's
  pointer to the current `DATA` line had already run on to the end of the
  program, so reading the item again as a string and then the next `DATA`
  line gave `Out of DATA`. Both now match.
- **Numbers that were not whole numbers could not be read** (fixed
  2026-10-09, D-READFLT): `DATA 1.5`, `2E3` and `-.25` were `Syntax error`,
  and `DATA 40000` came back as -25536, because zerobas read every numeric
  item as a 16-bit whole number. The VG-8020 reads them all. Found while
  writing these pages: every earlier test happened to use whole numbers. A
  numeric item now goes through the same number reader as `INPUT` and `VAL`,
  which also fixed `DATA 1E99` (now `Overflow`, was `Syntax error`) and
  `99999` read into `A%` (now `Overflow`, was accepted).
- **Strings could not be read at all** (fixed 2026-08-07, D-READVAR): items
  were only ever parsed as whole numbers. Measuring how the references cut a
  `DATA` line into strings found the rule above — and the surprise that
  trailing spaces are kept, where trimming both ends was the obvious guess
  ([readvar-msx1-characterization.md](../readvar-msx1-characterization.md)).
  The same work made text read into a number an error; it used to read as 0.
- **A quoted `:` ended the `DATA` statement** (fixed 2026-08-31, D-DATACOLON):
  `DATA "A:B"` was split at the colon and the rest run as program. The scan had
  no notion of quotes, in two places
  ([spec-basic-datacolon.md](../spec-basic-datacolon.md)).
- **`DATA 42:READ A` was a `Syntax error`** (fixed 2026-09-15, D-KWBARS): the
  reader did not accept a `:` as the end of an item. The keyword sweep's new
  `DATA` row found it — and that row had to put the `DATA` *before* the `READ`,
  because a `DATA` that is never stepped over is never executed, so a test that
  disabled `DATA`'s own code would not have noticed.
- **Reading long strings ran out of string space** (fixed 2026-10-07,
  D-READREF). zerobas copied every string it read; the references point at the
  program text. A 1989 type-in program stopped at its fifth `READ` here and ran
  to the end on the VG-8020. Joost ruled on 2026-09-27: *"point at program
  text"*.

## Where it lives

- `ex_data` in [basic/interp.asm](../../basic/interp.asm) steps over the
  statement at run time; `tk_data_rest` in
  [basic/tokenise.inc](../../basic/tokenise.inc) stores the items as typed when
  the line is entered. Both track quotes.
- The item reader is `read_one_value` in
  [basic/readdata-body.inc](../../basic/readdata-body.inc), which runs from the
  sub ROM ([sub/readdata.asm](../../sub/readdata.asm)).

## Related concepts

- [Program text](../concepts/program-text.md) — how a typed line becomes a program line
- [Strings and string space](../concepts/strings-and-string-space.md) — where string values live

## Tests that cover it

- `make kwsweep` — a number, a quoted string, unquoted text with a space, and
  an empty item, plus the text-into-a-number error row.
- `make readvar-acceptance` — how items are cut into strings, on both
  references.
- `make readref-acceptance` — strings read from `DATA` use no string space.
- `make readerl-acceptance` — the line a refused item's error names (`ERL`,
  the message, `LIST .`, from a program and from the prompt), and reading on
  past it.
- `make kwram` — the RAM-usage comparison.
