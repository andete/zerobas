<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `LSET` — fill a string in place, left-justified

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`LSET v$ = s$` copies `s$` into the bytes `v$` already has, from the left,
and fills the rest with spaces. The length of `v$` never changes. Its usual
job is to fill a [`FIELD`](FIELD.md) variable — a piece of a random-file
record — before `PUT` writes the record. [`RSET`](RSET.md) is the same with
right-justification. It is a Disk BASIC statement, so the reference is the
National CF-3300.

## Syntax

```
LSET <string variable> = <string expression>
```

## Details

- **Left-justified, space-padded**: `LSET A$="HI"` on a 6-byte field makes
  it `HI    `.
- **A longer value is cut to fit, keeping its first characters**:
  `LSET B$="HELLO"` on a 2-character `B$` makes it `HE`.
- **It works on any string variable**, fielded or not, and on array
  elements. On a plain variable it overwrites the variable's current
  characters in place; `LSET A$="HI"` on `A$="XXXXX"` gives `HI   `, still
  five long.
- **An empty or never-assigned target is left alone**: no error, and its
  length stays 0.
- **The value must be a string**, and so must the target.
- **Without a disk system** (the diskless VG-8020) `LSET` is `Illegal
  function call` (error 5), fielded variable or not.
- Not measured on the reference: `LSET A$=A$`, a target that is its own
  source.

### Errors

| situation | error |
|---|---|
| a numeric target (`LSET A=1`) | 13 `Type mismatch` |
| a numeric value (`LSET A$=5`) | 13 `Type mismatch` |
| no value after `=` (`LSET A$=`) | 24 `Missing operand` |
| no `=` at all (`LSET A$`) | 2 `Syntax error` |
| not a variable (`LSET 5="A"`) | 2 `Syntax error` |

The whole set of errors `LSET` raises on the CF-3300 for its enumerated cases
is {2, 13}; zerobas raises the same set, and the same 24 for a missing value.

## Example

```
10 OPEN "R.DAT" AS #1 LEN=6
20 FIELD #1,6 AS A$
30 LSET A$="HI":PRINT "[";A$;"]"
40 B$="AB":LSET B$="HELLO":PRINT B$
50 ON ERROR GOTO 80
60 LSET A=1
70 CLOSE:END
80 PRINT "Error";ERR:RESUME NEXT
RUN
[HI    ]
HE
Error 13
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_lset.out`](../../scratchpad/kwdoc_lset.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`LSET` on a variable without a `FIELD` was a `Syntax error`** (fixed
  2026-08-08, D-LRVAR). The rule was measured first, over 21 rows on the
  CF-3300, because the one filed reading fitted several different rules.
  Three readings decided it: the length never changes, an empty target is
  left alone, and `RSET` cuts a long value from the same end as `LSET`
  ([spec](../spec-basic-lrvar.md)). The same slice made `A=1:LSET A=2` a
  `Type mismatch`, as on the reference, instead of a `Syntax error`.
- **Which machine is the reference was itself measured** (2026-09-02,
  D-LSETREF). The cassette-only VG-8020 refuses `LSET` with error 5, the
  CF-3300 pads in place. A cassette-only National, whose main BASIC ROM is
  byte-identical to the CF-3300's by its published checksum, also says
  error 5 — so the word belongs to the disk system, and the CF-3300 is the
  one to follow.
- **`LSET A$=5` and `LSET A$=` were both `Syntax error`** (fixed 2026-09-02,
  D-LSETTM); the reference says `Type mismatch` and `Missing operand`.
- **A diskless zerobas simply ran `LSET`** (fixed 2026-09-16, D-FLDGATE);
  the VG-8020 says error 5.

## Where it lives

- Main ROM: `ex_lset` and `lrset_common` in
  [basic/field.asm](../../basic/field.asm) hand the statement to the disk ROM
  through the `H_LSET` hook.
- Disk ROM: `hk_lrset` in [disk/kernel.asm](../../disk/kernel.asm), shared
  with `RSET`, finds the field (if any) and calls back for the value.
- The store itself, padding and justification included, is
  `lrset_store_tenant` in [sub/lrsetst.asm](../../sub/lrsetst.asm).

## Tests that cover it

- `make diskbasic-acceptance` — `FIELD`, `LSET` and `RSET` records written and
  compared with the CF-3300.
- `make lrvar-acceptance` — `LSET`/`RSET` on plain variables and array
  elements.
- `make kwsweep` — the everyday row (the first byte of a fielded buffer is
  the data, 66 for `B`) and the error rows for {2, 13}.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
