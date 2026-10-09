<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `LET` — give a variable a value

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`LET A=5` stores the value of an expression in a variable or an array element.
The word `LET` is optional: `A=5` does exactly the same, and is how almost
every program writes it. zerobas behaves exactly like the Philips VG-8020 for
every case we have measured, errors included.

## Syntax

```
[LET] <variable> = <expression>
```

The variable may be a plain name (`A`, `NAME$`), a typed name (`A%`, `A!`,
`A#`, `A$`) or an array element (`Q(3)`, `Q$(I,J)`).

## Details

- **Names count by their first two characters.** `ZQ9` and `ZQ7` are the same
  variable, on both machines.
- **The type comes from the name**: `%` integer, `!` single precision, `#`
  double precision, `$` string. A name without a suffix is double precision
  unless a `DEFINT`, `DEFSNG`, `DEFDBL` or `DEFSTR` says otherwise for its first
  letter.
- **A number is converted to the variable's type as it is stored:**
  - to an integer by **truncating** toward zero: `A%=1.7` stores 1,
    `A%=-1.7` stores −1;
  - to single precision by **rounding** to 6 digits: `A!=1234567` stores
    1234570;
  - to double precision exactly.

  Note the asymmetry: integers truncate, single precision rounds.
- **A string into a number variable, or a number into a string variable**, is
  `Type mismatch` (error 13), and nothing is stored: `LET A="X"`, `A$=5`,
  `A$=1+1`, `Q$(0)=1`.
- **The target must be a variable.** `LET 5=1`, `LET "A"=1` and `LET TIME=5`
  are `Syntax error` (error 2). (`TIME=5` *without* `LET` is legal: it is the
  `TIME` statement, which sets the clock.)
- **An incomplete statement** — `LET` alone, or `LET A` with no `=` — is
  `Syntax error` (error 2).

| you write | you get |
|---|---|
| `LET A=5`, `A=5` | A is 5 |
| `A%=1.7` | A% is 1 |
| `LET A="X"`, `LET A$=5` | error 13, `Type mismatch` |
| `LET`, `LET A`, `LET 5=1` | error 2, `Syntax error` |

The whole set of errors `LET` can raise is {2, 13}, the same on both machines.

## Example

```
10 LET A=5
20 B=A*2
30 LET C$="LET"+"TER"
40 LET D%=7.9:E!=1234567
50 PRINT A;B;C$;D%;E!
60 ON ERROR GOTO 90
70 LET F="X"
80 LET 5=1
85 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
 5  10 LETTER 7  1234570
Error 13
Error 2
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_let.out`](../../scratchpad/kwdoc_let.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `LET` uses the same amount of free
memory on both machines, but the two machines write different work-area cells
along the way — the VG-8020 some that zerobas does not, and zerobas a few the
VG-8020 does not. Nothing a program can observe through `FRE` differs.

## What we found, and how

- **`LET 5=1` corrupted the screen and could restart the machine** (fixed
  2026-09-27, D-LETNUM). The VG-8020 answers `Syntax error`. zerobas's
  assignment code assumed the target started with a letter, which was only
  checked when `LET` was left out; with `LET`, a number reached it and the
  value was written to the wrong place. Typing `PRINT 7`, `LET 5=1`, `PRINT 8`
  rebooted zerobas. Now any target that does not start with a letter is
  `Syntax error`, `LET TIME=5` included. Found by measuring every error each
  keyword can raise.
- **A number into a string variable gave the wrong error** (fixed 2026-07-28,
  D-MISS-1). `A$=1`, `LET A$=A`, `Q$(0)=1` and similar were `Syntax error`
  instead of `Type mismatch`, so an `ON ERROR` handler saw the wrong code. The
  string assignment never checked the type of its right-hand side:
  [spec-basic-missing-class.md](../spec-basic-missing-class.md) §3.6.
- **Storing a fraction follows the variable's type** (since typed variables
  arrived, July 2026). The VG-8020 showed that an integer store truncates while
  a single-precision store rounds, and settled that a plain name is double
  precision, not single:
  [spec-basic-float-core.md](../spec-basic-float-core.md) §11.

## Where it lives

`ex_letkw` (the `LET` word and its target check), `ex_let` and `ex_let_str` in
[basic/interp.asm](../../basic/interp.asm); array elements are
`ex_let_arr` / `ex_let_arr_str` in [basic/arrays.asm](../../basic/arrays.asm).
A line that starts with a variable name goes straight to `ex_let`.

## Tests that cover it

- `make kwsweep` — the everyday row (`LET A=5`), the error rows for {2, 13}
  including `LET 5=1`, and the deliberately-broken-build check.
- `make float-acceptance` — storing into `%`, `!` and `#` variables, and the
  cross-type `Type mismatch`.
- `make missing-acceptance` — the number-into-string-variable rows.
- `make kwram` — the RAM-usage comparison.
