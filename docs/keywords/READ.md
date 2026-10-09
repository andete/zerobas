<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `READ` — take the next values from `DATA`

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven. One
> recorded difference: which line a bad item's `Syntax error` names (below,
> an open TIER 3 item). Numbers like `1.5` read correctly since 2026-10-09.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`READ` assigns the next items of the program's [`DATA`](DATA.md) statements to
variables, one item per variable, in program order. [`RESTORE`](RESTORE.md)
moves the starting point. zerobas reads the same values and raises the same
errors as the Philips VG-8020 in every case we have measured, except two
out-of-range number cases that are filed.

## Syntax

```
READ <variable>[,<variable>]...
```

Any variable can be a target: a one- or two-character name, with or without a
type suffix (`%`, `!`, `#`, `$`), or an array element such as `A(I)` or
`B$(2,3)`.

## Details

- **Each variable takes the next item**, across `DATA` statements and lines.
  Numbers and strings can be mixed in one `READ`: `READ A,B$`.
- **How an item is cut out of the `DATA` line** — quotes, spaces, empty items —
  is described on [`DATA`](DATA.md)'s page.
- **Reading past the last item is `Out of DATA`** (error 4), also mid-`READ`.
- **Text read into a number is `Syntax error`** (error 2).
- **An array element with a bad subscript** gives the array's own error, as an
  assignment would: `READ A(9)` after `DIM A(3)` is `Subscript out of range`.
- **`READ` works at the prompt** too, reading the stored program's `DATA`.
- **The reading position goes back to the first item** when a program is
  started with `RUN`, after `CLEAR`, after any program edit, and after a bare
  `RESTORE`. A direct `READ` after a program has ended carries on where the
  program stopped.
- **A string read from `DATA` uses no string space**: the variable points at
  the text inside the program, as on the reference.

| situation | error |
|---|---|
| no items left (`READ A` with no `DATA`) | 4 `Out of DATA` |
| a text item read into a number | 2 `Syntax error` |
| a number too large for the target (see *Differences*) | 6 `Overflow` on the reference |

The measured set of errors for `READ` on the VG-8020 is {2, 4, 6}.

## Example

```
10 DIM A(2)
20 FOR I=0 TO 2:READ A(I):NEXT
30 READ N$,B%
40 PRINT A(0)+A(1)+A(2);N$;B%
50 ON ERROR GOTO 80
60 READ X
70 END
80 PRINT "Error";ERR:END
90 DATA 1,2.5,3,ZB,-5
RUN
 6.5 ZB-5
Error 4
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_read.out`](../../scratchpad/kwdoc_read.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**Which line a bad item's `Syntax error` names** (D-READERL, found
2026-10-09, open, TIER 3). For `20 DATA 12X` / `30 READ A`, the VG-8020 says
`Syntax error in 20` — the `DATA` line, where the typo is — and zerobas says
`in 30`, the `READ` line. Both resume at the `READ` after `RESUME NEXT`, and
both leave the bad item unread, so the next `READ` refuses it again
([`readflt_after.out`](../../scratchpad/readflt_after.out)).

The rung not yet proven is **RAM usage**.

## What we found, and how

- **Numbers that were not whole numbers could not be read** (fixed
  2026-10-09, D-READFLT): `DATA 1.5`, `2E3` and `-.25` were `Syntax error`,
  and `DATA 40000` came back as -25536, because zerobas read every numeric
  item as a 16-bit whole number. The VG-8020 reads them all. Found while
  writing these pages: every earlier test happened to use whole numbers. A
  numeric item now goes through the same number reader as `INPUT` and `VAL`,
  which also fixed `DATA 1E99` (now `Overflow`, was `Syntax error`) and
  `99999` read into `A%` (now `Overflow`, was accepted).
- **Only single-letter number variables could be read** (fixed 2026-08-07,
  D-READVAR). `READ AB`, `READ A%` and every string were `Syntax error`; 24
  cases were measured on both references first
  ([readvar-msx1-characterization.md](../readvar-msx1-characterization.md)).
  Array elements followed the next day (D-ARYLV, 2026-08-08).
- **At the prompt, `READ` silently read 0** (fixed 2026-09-13, D-READDIR). With
  `10 DATA 7` stored, a `READ` typed before any `RUN` gave 0 where the
  reference gives 7 — a wrong answer with no error, and every test had missed
  it because they all `RUN` first. Asking the reference *when* the reading
  position resets found two more differences: `CLEAR` and a program edit reset
  it there and did not here
  ([readings](../../scratchpad/readfix_datareset.out)).
- **`DATA 42:READ A` was a `Syntax error`** (fixed 2026-09-15, D-KWBARS) — see
  [`DATA`](DATA.md).
- **Reading long strings ran out of string space** (fixed 2026-10-07,
  D-READREF): zerobas copied each string, the references point at the program
  text. A 1989 type-in program stopped at its fifth `READ` here. Joost ruled on
  2026-09-27: *"point at program text"*. `MID$` on such a string copies it out
  first, so the program itself is never changed — also measured.

## Where it lives

- `ex_read` in [basic/program.asm](../../basic/program.asm) parses each target
  and stores the value; `tgt_store_ref` in [basic/vars.asm](../../basic/vars.asm)
  points a string variable at the `DATA` text.
- The item reader is `read_one_value` in
  [basic/readdata-body.inc](../../basic/readdata-body.inc), which runs from the
  sub ROM ([sub/readdata.asm](../../sub/readdata.asm)).

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision
- [Strings and string space](../concepts/strings-and-string-space.md) — where string values live
- [Variables](../concepts/variables.md) — names, types, arrays, and where they live

## Tests that cover it

- `make readvar-acceptance` — every kind of target and how items are cut into
  strings, on both references.
- `make arylv-acceptance` — array elements as targets.
- `make readref-acceptance` — strings read from `DATA` use no string space.
- `make kwsweep` — the everyday row, the `Out of DATA` row and the error rows
  for {2, 4}.
- `make kwram` — the RAM-usage comparison.
