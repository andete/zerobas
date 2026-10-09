<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `READ` — take the next values from `DATA`

> **Status (2026-10-09):** level 0 since this page found that the **happy path
> fails for numbers that are not whole numbers** (below) · reasonable time ✓ ·
> common errors ✓ · RAM usage not yet proven · every error not yet proven.
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
90 DATA 1,2,3,ZB,-5
RUN
 6 ZB-5
Error 4
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_read.out`](../../scratchpad/kwdoc_read.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**`READ` cannot read a number that is not a whole number** (D-READFLT,
found 2026-10-09, open, a TIER 1 item — the happy path). On the VG-8020
`DATA 1.5`, `DATA 2E3` and `DATA -.25` read into a numeric variable give 1.5,
2000 and -.25; zerobas raises `Syntax error`. `DATA 40000` reads back as
-25536 here, because zerobas reads every numeric item as a 16-bit whole
number ([`readflt_run.out`](../../scratchpad/readflt_run.out)). Whole numbers
from -32768 to 32767, and every string item, read correctly.

Two more open items, both TIER 6 (every error), are probably the same cause:

- **`READ A` of `DATA 1E99` is `Syntax error` here and `Overflow` on the
  VG-8020** (D-READOVF). 1E99 is a well-formed number too large for a
  variable; the reference converts it and overflows, zerobas's item reader
  rejects it as text ([readings](../../scratchpad/t6enum_b4.out)).
- **`READ A%` of `DATA 99999` is `Overflow` on the VG-8020 and accepted here**
  (D-READINTOVF, [readings](../../scratchpad/t6enum_b9.out)).

Until both are fixed, **every error** is not proven for `READ`.

The other rung not yet proven is **RAM usage**.

## What we found, and how

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
