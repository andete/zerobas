<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `GOTO` — jump to a line

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference, in the `IF … GOTO` form (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`GOTO 100` continues the program at line 100. Nothing is remembered, so there
is no way back (for that, use [`GOSUB`](GOSUB.md)). zerobas behaves like the
Philips VG-8020 in every case we have measured, errors included.

## Syntax

```
GOTO <line number>
ON <expression> GOTO <line number>[,<line number>...]
IF <condition> GOTO <line number>
```

The line number is a constant; `GOTO A` and `GOTO "100"` are not allowed.

## Details

- **Anything after the line number is never reached**, so `GOTO 100 ZZ` is
  accepted on both machines.
- **A line number stops before it would pass 65529.** The digits of
  `GOTO 70000` are read as `GOTO 7000` followed by a stray `0`, so with no
  line 7000 it is `Undefined line number` on both machines
  ([spec-basic-lnref.md](../spec-basic-lnref.md)).
- **`ON n GOTO 100,200,300`** jumps to the n-th line in the list. `n` is
  truncated, not rounded (`ON 1.7` takes the first). `ON 0` or an `n` past the
  end of the list does nothing and the program carries on; a negative `n` or
  one above 255 is `Illegal function call` (error 5), and one beyond the
  integer range is `Overflow` (error 6). A string is `Type mismatch`
  (error 13), and an empty list is `Syntax error`.
- **`IF <condition> GOTO <line>`** is `IF` without `THEN`; see [`IF`](IF.md).

### Errors

| you write | you get |
|---|---|
| `GOTO 99` when there is no line 99 | 8 `Undefined line number` |
| `GOTO 70000` | 8 `Undefined line number` (read as 7000, see above) |
| `GOTO`, `GOTO "A"`, `GOTO -1` | 2 `Syntax error` |

The whole set of errors `GOTO` raises is {2, 8}, the same on both machines.

## Example

```
10 N=1
20 PRINT N;
30 N=N*2
40 IF N>100 THEN 60
50 GOTO 20
60 PRINT:ON 2 GOTO 70,80
70 PRINT "One"
80 PRINT "Two"
90 ON ERROR GOTO 120
100 GOTO 999
110 END
120 PRINT "Error";ERR:RESUME NEXT
RUN
 1  2  4  8  16  32  64
Two
Error 8
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_goto.out`](../../scratchpad/kwdoc_goto.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**`IF 1 GOTO` with no line number** is accepted by the VG-8020, which carries
on without jumping, and is `Syntax error` here (D-IFGOTOBARE, found
2026-09-27; [t6enum_b6.out](../../scratchpad/t6enum_b6.out)). A plain `GOTO`
with no line number is `Syntax error` on both machines. This is filed as a
TIER 6 item ("every error") in [TODO.md](../../TODO.md) and is listed under
both `GOTO` and `IF`.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **Big line numbers wrapped** (fixed 2026-08-01, D-LNREF). `GOTO 99999` was
  stored as a jump to line 34463. The reference neither wraps nor refuses: it
  splits the digits at 65529, the same ceiling as a program line's own number
  ([lnref-msx1-characterization.md](../lnref-msx1-characterization.md)).
- **`GOTO` had no test of its own** (D-KWGOTOROW). It was used by dozens of
  rows in the keyword sweep and was the subject of none — its only row was the
  `GOTO 9999` error. Being used is not being measured: the row added puts a
  statement after the `GOTO` that must be skipped, so a `GOTO` that fell
  through shows a different value.
- **`ON n GOTO`'s selector was checked on 2026-08-30** (D-ONDOM) and found
  correct everywhere: 15 rows, no difference. The rows that matter are the
  ones that do *not* raise — an `n` past the list falls through silently, so
  a wrong answer there has no error to notice
  ([spec-basic-ondom.md](../spec-basic-ondom.md)).

## Where it lives

`ex_goto` and `goto_resolve` in [basic/interp.asm](../../basic/interp.asm).
The line number is read by the shared `req_lineno` (also used by `GOSUB`,
`RESUME` and `ON ERROR GOTO`); `goto_resolve` is shared with `RESUME <line>`.
`ON … GOTO` is `ex_on` and `eon_seek_nth` in
[basic/program.asm](../../basic/program.asm).

## Tests that cover it

- `make kwsweep` — the jump row, the `ON 2 GOTO` row, and the error rows for
  {2, 8}.
- `make lnblank-acceptance` — how line-number references are stored, the
  65529 split included.
- `make kwram` — the RAM-usage comparison.
