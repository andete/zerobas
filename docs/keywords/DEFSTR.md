<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `DEFSTR` — make variables strings by their first letter

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`DEFSTR S` makes every unsuffixed variable whose name starts with `S` a string
variable — as if you had written `S$`. zerobas behaves exactly like the
Philips VG-8020 for every case we have measured.

## Syntax

```
DEFSTR <letter>[-<letter>][,<letter>[-<letter>]...]
```

## Details

- **The rules are those of [`DEFINT`](DEFINT.md)**: first letter only, a
  suffix always wins, the last `DEF` for a letter wins, and the type is looked
  up at every use.
- **`S` and `S$` are then the same variable**: after `DEFSTR S`,
  `S$="X":PRINT S` prints `X`.
- **A number where a string is expected is `Type mismatch`** (error 13):
  `S=5`, `B=1+S`, and `FOR S=1 TO 3` all raise it.
- **`READ S` reads the next `DATA` item as a string.**
- **Errors in the statement itself:** every malformed `DEFSTR` (`DEFSTR 5`,
  `DEFSTR A-`, a reversed range) is `Syntax error` (error 2), the only error
  the VG-8020 raises for it. The full list is on the [`DEFINT`](DEFINT.md)
  page.

## Example

```
10 DEFSTR S-T
20 S="HI":T=S+"!"
30 PRINT S;T
40 ON ERROR GOTO 80
50 S=5
60 DEFSTR 5
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
HIHI!
Error 13
Error 2
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_defstr.out`](../../scratchpad/kwdoc_defstr.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**. In its test program
(`DEFSTR A:A="x"`) the assignment takes one byte of string space on zerobas
and none on the VG-8020, and the two machines write different cells of the
documented work area.

## What we found, and how

- **`DEFSTR` on a loop variable corrupted memory** (fixed 2026-08-01,
  D-DEFSTR). `DEFSTR I:FOR I=1 TO 3` stored a number into a string variable's
  slot, and printing it then dumped whatever was in memory; both references
  say `Type mismatch`. It was hidden by a coincidence: the code zerobas used
  for "string" in its type table happened to equal the one it used internally
  for string variables. The same fix made `B=1+S` a `Type mismatch` (it had
  read 0), and made the 26-entry type table in the work area hold the same
  bytes as the reference's: [spec-basic-deftbl-strcode.md](../spec-basic-deftbl-strcode.md).
- **`READ` into a `DEFSTR` variable** was a `Type mismatch` until zerobas
  learned string `READ` (fixed 2026-08-07, D-READVAR); both references read
  the item as text.
- **`DEFSTR` had no keyword entry of its own** until 2026-08-19 (D-DEFTYPETOK).
  It was stored as `DEF` plus the letters `STR`, and that left the tokeniser
  thinking it was still inside a name, so a number after it was read as part
  of the name. One keyword entry fixed both.
- **A malformed item could run its tail as a statement** (fixed 2026-08-31,
  D-DEFCORNER, for all four `DEF` statements — see [`DEFINT`](DEFINT.md)).
- **The range test reads a value against an error** (2026-09-14,
  D-KWBATCH6): without the range, `C="x"` is a `Type mismatch`.

## Where it lives

The same code as `DEFINT`: `ex_deftype` in [basic/usr.asm](../../basic/usr.asm)
and `deftype_tenant` in [sub/deftype.asm](../../sub/deftype.asm). The check
that a string-typed name is not read as a number is `check_vartype_num` in
[basic/arrays.asm](../../basic/arrays.asm).

## Related concepts

- [Variables](../concepts/variables.md) — names, types, arrays, and where they live

## Tests that cover it

- `make float-acceptance` — `DEFSTR` naming, the `S`/`S$` identity and the
  numeric `Type mismatch`, among the shared type rules.
- `make readvar-acceptance` — `READ` into a `DEFSTR` variable.
- `make kwsweep` — the single-letter and range rows, and the error rows
  `DEFSTR 5` and `DEFSTR A-` (2).
- `make kwram` — the RAM-usage comparison.
