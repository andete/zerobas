<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `CSRLIN` — the row the cursor is on

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CSRLIN` is the text cursor's row, counted from 0 at the top of the screen.
It is the reading half of [`LOCATE`](LOCATE.md)'s row; [`POS`](POS.md) gives
the column. zerobas behaves exactly like the Philips VG-8020 for every case we
have measured, errors included.

## Syntax

```
CSRLIN
```

No argument and no parentheses: it is used like a variable.

## Details

- **0-based.** After [`CLS`](CLS.md) it is 0; after one `PRINT` it is 1; after
  `LOCATE 0,5` it is 5.
- **An ordinary number.** It can be assigned (`X=CSRLIN`) and used in
  arithmetic (`CSRLIN+10`).
- **A parenthesis after it is a separate item.** `PRINT CSRLIN(0)` prints two
  numbers, the row and then 0, because `(0)` is read as the next item of the
  `PRINT`, not as an argument.
- **The bottom row depends on the function-key line.** With the key line shown
  (the power-on state) the last text row is 22 and scrolling starts below it;
  after `KEY OFF` it is 23. See [`KEY`](KEY.md).
- **Its only error is something stuck to it**: `A=CSRLIN 1` is `Syntax error`
  (error 2), on both machines. That is the whole error set.

## Example

The first line clears the screen so that the row numbers are known; the
listing and the `RUN` line are wiped with it.

```
10 CLS:PRINT "Top row is";CSRLIN
20 PRINT "Next is";CSRLIN
30 PRINT "Same row";:PRINT CSRLIN
40 ON ERROR GOTO 70
50 A=CSRLIN 1
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
Top row is 0
Next is 1
Same row 2
Error 2
```

Line 30 ends its first `PRINT` with `;`, so the cursor stays on row 2 for the
second.
Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_csrlin.out`](../../scratchpad/kwdoc_csrlin.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `CSRLIN` moves free memory the
same way on both machines, but the set of documented work-area cells each one
writes is not the same.

## What we found, and how

- **`CSRLIN` used to be silently wrong** (fixed 2026-07-27, the cursor slice
  [spec-basic-cursor-cluster.md](../spec-basic-cursor-cluster.md)). Without its
  own keyword it was read as an ordinary variable and answered 0 with no
  error. The rules above were measured on the VG-8020 first
  ([cursor-vg8020-characterization.md](../cursor-vg8020-characterization.md)).
- **An absolute row is a hard thing to test.** Without a `CLS` first, the
  answer depends on where the boot banner and earlier output left the cursor;
  in one run the VG-8020 and the National CF-3300 disagreed with each other.
  The sweep's row therefore reads the change across two `PRINT`s, which a
  `CSRLIN` that always answered 0 would fail.
- **The bottom row moved with the function-key line on the VG-8020 and not
  here** (fixed 2026-09-17, D-SCROLLBOUND): `LOCATE 0,23` then `CSRLIN` read 22
  there and 23 here until zerobas drew the key line and reserved its row.

## Where it lives

`ev_f_csrlin` in [basic/expr.asm](../../basic/expr.asm). It reads the BIOS
cursor row and subtracts 1, because the BIOS counts from 1.

## Tests that cover it

- `make cursor-acceptance` — the row after `CLS`, after one and two `PRINT`s,
  in arithmetic, and `CSRLIN(0)`.
- `make kwsweep` — the everyday row and the error row for {2}.
- `make kwram` — the RAM-usage comparison.
