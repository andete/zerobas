<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `DATA` — values stored in the program for `READ`

> **Status (2026-10-09):** level 0 since this page found that **a numeric item
> that is not a whole number cannot be read** (below) · reasonable time ✓ ·
> common errors ✓ · RAM usage not yet proven · every error not yet proven.
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
10 DATA 42,"A,B",  HI THERE,,7
20 READ N,A$,B$,C$,D
30 PRINT N;A$;"|";B$;"|";C$;"|";D
40 ON ERROR GOTO 70
50 READ X
60 END
70 PRINT "Error";ERR:END
80 DATA ABC
RUN
 42 A,B|HI THERE|| 7
Error 2
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_data.out`](../../scratchpad/kwdoc_data.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**`READ` cannot read a number that is not a whole number** (D-READFLT,
found 2026-10-09, open, a TIER 1 item — the happy path). On the VG-8020
`DATA 1.5`, `DATA 2E3` and `DATA -.25` read into a numeric variable give 1.5,
2000 and -.25; zerobas raises `Syntax error`. `DATA 40000` reads back as
-25536 here, because zerobas reads every numeric item as a 16-bit whole
number ([`readflt_run.out`](../../scratchpad/readflt_run.out)). Whole numbers
from -32768 to 32767, and every string item, read correctly.

**An integer item too large for an integer variable is accepted here.**
`READ A%` of `DATA 99999` is `Overflow` (error 6) on the VG-8020; zerobas
reads it without an error (D-READINTOVF, open, a TIER 6 item;
[readings](../../scratchpad/t6enum_b9.out)). A related open item is on
[`READ`](READ.md)'s page: `DATA 1E99` read into a number is `Overflow` on the
VG-8020 and `Syntax error` here (D-READOVF). Until both are fixed, **every
error** is not proven for `DATA`.

The other rung not yet proven is **RAM usage**.

## What we found, and how

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
- `make kwram` — the RAM-usage comparison.
