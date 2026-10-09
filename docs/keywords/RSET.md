<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `RSET` — fill a string in place, right-justified

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`RSET v$ = s$` copies `s$` into the bytes `v$` already has, against the
right edge, with spaces in front. The length of `v$` never changes. It is the
mirror of [`LSET`](LSET.md), and like it is mostly used on
[`FIELD`](FIELD.md) variables before `PUT` writes a record. It is a Disk
BASIC statement, so the reference is the National CF-3300.

## Syntax

```
RSET <string variable> = <string expression>
```

## Details

- **Right-justified, space-padded**: `RSET A$="HI"` on a 6-byte field makes
  it `    HI`.
- **A longer value is cut to fit, keeping its FIRST characters** — the same
  end `LSET` keeps, not the last ones: `RSET B$="HELLO"` on a 2-character
  `B$` makes it `HE`, not `LO`.
- **It works on any string variable**, fielded or not; on a plain variable
  it overwrites the current characters in place (`RSET A$="HI"` on
  `A$="XXXXX"` gives `   HI`). An empty or never-assigned target is left
  alone, with no error.
- **Without a disk system** (the diskless VG-8020) `RSET` is `Illegal
  function call` (error 5).

### Errors

| situation | error |
|---|---|
| a numeric target (`RSET A=1`) | 13 `Type mismatch` |
| a numeric value (`RSET A$=5`) | 13 `Type mismatch` |
| no value after `=` (`RSET A$=`) | 24 `Missing operand` |
| no `=` at all (`RSET A$`) | 2 `Syntax error` |
| not a variable (`RSET 5="A"`) | 2 `Syntax error` |

The whole set of errors `RSET` raises on the CF-3300 for its enumerated cases
is {2, 13}; zerobas raises the same set, and the same 24 for a missing value.

## Example

```
10 OPEN "R.DAT" AS #1 LEN=6
20 FIELD #1,6 AS A$
30 RSET A$="HI":PRINT "[";A$;"]"
40 B$="AB":RSET B$="HELLO":PRINT B$
50 ON ERROR GOTO 80
60 RSET A$
70 CLOSE:END
80 PRINT "Error";ERR:RESUME NEXT
RUN
[    HI]
HE
Error 2
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_rset.out`](../../scratchpad/kwdoc_rset.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`RSET` on a variable without a `FIELD` was a `Syntax error`** (fixed
  2026-08-08, D-LRVAR). Of the 21 rows measured on the CF-3300 before the
  fix, the one a hand-written version would most likely have got wrong is
  `RSET A$="HELLO"` on `A$="AB"`: the reference keeps `HE`, not `LO`
  ([spec](../spec-basic-lrvar.md)). The existing store already did exactly
  that, for both verbs.
- **`RSET A$=5` and `RSET A$=` were both `Syntax error`** (fixed 2026-09-02,
  D-LSETTM); the reference says `Type mismatch` and `Missing operand`.
- **A diskless zerobas simply ran `RSET`** (fixed 2026-09-16, D-FLDGATE);
  the VG-8020 says error 5. `LSET` and `RSET` turned out to use two separate
  hook cells on the reference, each found by switching it off and seeing
  which verb stopped working (D-HOOKID, 2026-09-15).

## Where it lives

- Main ROM: `ex_rset` and `lrset_common` in
  [basic/field.asm](../../basic/field.asm), through the `H_RSET` hook.
- Disk ROM: `hk_lrset` in [disk/kernel.asm](../../disk/kernel.asm), shared
  with `LSET`.
- The store, with its right-justification, is `lrset_store_tenant` in
  [sub/lrsetst.asm](../../sub/lrsetst.asm).

## Tests that cover it

- `make diskbasic-acceptance` — `FIELD`, `LSET` and `RSET` records written and
  compared with the CF-3300.
- `make lrvar-acceptance` — `LSET`/`RSET` on plain variables and array
  elements.
- `make kwsweep` — the everyday row (the first byte of a right-justified
  field is a space, 32) and the error rows for {2, 13}.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
