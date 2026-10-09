<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `LOCATE` — move the text cursor

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`LOCATE x,y` puts the text cursor at column `x`, row `y`, so the next
`PRINT` starts there. Columns and rows count from 0. Either position can be
left out and then keeps its current value; a third argument sets the cursor
switch. Positions past the edge of the screen are pulled back onto it rather
than refused. zerobas behaves exactly like the Philips VG-8020 for every case
we have measured, errors included.

## Syntax

```
LOCATE [<column>] [, [<row>] [, <cursor switch>]]
```

All three are numeric expressions. At least one must be present.

## Details

- **Column first, then row, both 0-based.** `LOCATE 5,3` puts the next
  character on row 3, column 5. Fractions are truncated: `LOCATE 5.7,3.2` is
  `LOCATE 5,3`, and `LOCATE 4.5,2.5` is `LOCATE 4,2`.
- **An omitted position keeps its value.** `LOCATE 7` moves only the column;
  `LOCATE ,4` moves only the row. `LOCATE 0` is a real column 0, not an
  omission.
- **Too large is clamped, not refused.** Any value from 0 to 255 is accepted
  and then pulled onto the screen. The column stops at the last column of the
  current [`WIDTH`](WIDTH.md): at `WIDTH 40`, `LOCATE 40` and `LOCATE 255` both
  land on column 39; at `WIDTH 32`, on column 31. The row stops at the last
  text row: **22** while the function-key line is shown, **23** after
  `KEY OFF` (see [`KEY`](KEY.md)). Both axes clamp independently:
  `LOCATE 255,255` lands on row 22, column 39.
- **The cursor switch** (third argument) accepts 0 to 255 and stores 0 for 0
  and 1 for anything else in the work-area cell `CSRSW` (`&HFCA9`), as both
  reference machines do. What that switch shows on screen while a program
  runs has not been measured here.
- **Nothing moves when an argument is wrong** — except for a fourth argument,
  which is found only after the first three have been applied: `LOCATE 1,1,1,1`
  moves the cursor to (1,1) and then reports `Syntax error` there.
- **An error inside an argument wins.** In `LOCATE 70000+0*(1/0),3` the
  division by zero is reported (error 11), not the overflow the value would
  otherwise cause.
- `LOCATE` works in the graphics modes too (`SCREEN 2:LOCATE 5,3` raises
  nothing). Read the position back with [`CSRLIN`](CSRLIN.md) and
  [`POS`](POS.md).

### Errors

| you write | you get |
|---|---|
| `LOCATE -1,0`, `LOCATE 256,0`, `LOCATE 0,256`, `LOCATE 5,3,256` | error 5, `Illegal function call` |
| `LOCATE 32768,0`, `LOCATE -32769,0`, `LOCATE 0,32768`, `LOCATE 5,3,32768` | error 6, `Overflow` |
| `LOCATE "5",3`, `LOCATE ,"A"`, `LOCATE 1,1,"A"` | error 13, `Type mismatch` |
| `LOCATE`, `LOCATE ,`, `LOCATE ,,`, `LOCATE 5,3,` | error 24, `Missing operand` |
| `LOCATE 1,1,1,1` | error 2, `Syntax error` (after moving the cursor) |

## Example

```
10 Y=CSRLIN:LOCATE 5,Y:PRINT "Hello"
20 LOCATE 9,Y:LOCATE ,Y+1:A=POS(0)
30 PRINT "Column kept:";A
40 LOCATE 99:A=POS(0):LOCATE 0
50 PRINT "Clamped to";A
60 ON ERROR GOTO 90
70 LOCATE 0,-1
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
     Hello
         Column kept: 9
Clamped to 39
Error 5
```

Line 20 moves the row and keeps column 9, which is where line 30 then
prints. Line 40 asks for column 99 and gets the last column, 39.
Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_locate.out`](../../scratchpad/kwdoc_locate.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `LOCATE` moves free memory the
same way on both machines, but the set of documented work-area cells each one
writes is not the same.

## What we found, and how

- **`LOCATE` arrived on 2026-07-27**, with the other missing statements of
  that slice ([spec-basic-missing-class.md](../spec-basic-missing-class.md)),
  measured first in
  [missing-vg8020-characterization.md](../missing-vg8020-characterization.md).
  The measurement settled two things nobody had guessed: a bare `LOCATE` is
  `Missing operand`, not a no-op, and out-of-range positions clamp instead of
  erroring. The row clamp was the hard one to see, because printing near the
  bottom scrolls the screen before it can be read; it was read through
  `CSRLIN` captured into variables instead.
- **An error inside an argument was reported as `Overflow`** (fixed
  2026-08-09, D-LOCARG): `LOCATE 70000+0*(1/0),3` must report the division by
  zero, and `LOCATE 70000+0*SQR(-1),3` must report error 5 — a different code,
  which is what shows the rule is "the error that happened first", not
  "division by zero is special"
  ([locarg-msx1-characterization.md](../locarg-msx1-characterization.md)).
  `LOCATE STR$(1/0),3` followed the same day (D-TMFP).
- **The cursor switch was parsed and thrown away** until 2026-09-16
  (D-LOCCSR). Both references store it in `CSRSW`, folded to 0 or 1; `SCREEN`'s
  neighbouring key-click switch is stored as given, so `,,2` was measured
  before either was written.
- **The row limit ignored the function-key line** (fixed 2026-09-17,
  D-SCROLLBOUND). The VG-8020 keeps the bottom row for the key labels, so
  `LOCATE 0,23` lands on row 22 there; zerobas let it reach 23 until it drew
  the key line itself.

## Where it lives

`ex_locate`, `loc_next` (one argument) and `loc_apply_pos` (the clamp) in
[basic/missing.asm](../../basic/missing.asm).

## Tests that cover it

- `make missing-acceptance` — position, omitted arguments, the clamp on both
  axes, the argument count and the error codes.
- `make locarg-acceptance` and `make tmfp-acceptance` — which error wins when
  an argument expression fails.
- `make kwsweep` — one row per form (column, row, omitted column, cursor
  switch) and the error rows for {5, 13}.
- `make kwram` — the RAM-usage comparison.
