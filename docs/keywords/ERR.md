<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `ERR` — the code of the last error

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`ERR` is the number of the most recent error: 5 for `Illegal function call`,
11 for `Division by zero`, and so on. An `ON ERROR GOTO` handler reads it to
decide what to do; its partner [`ERL`](ERL.md) gives the line. zerobas behaves
exactly like the Philips VG-8020 for every case we have measured.

## Syntax

```
ERR
```

No argument and no parentheses: `ERR` is used like a variable that BASIC
keeps up to date.

## Details

- **Inside a handler `ERR` is the code that brought you there**, whether BASIC
  raised it or the program did with [`ERROR`](ERROR.md) (`ERROR 53` reads 53).
- **[`RESUME`](RESUME.md), in all its forms, sets `ERR` back to 0.** `ERL` is
  left alone.
- **After an untrapped error** the program stops, and `PRINT ERR` typed at the
  prompt still shows the code.
- **After `No RESUME`** (a handler ran off the end of the program) `ERR` is 21,
  the code of that error, not the one that entered the handler.
- **On a machine that has not had an error yet**, `ERR` is 0.
- **`ERR` takes nothing after it**: `A=ERR 1` is `Syntax error` (error 2). That
  is the only error `ERR` itself causes on the VG-8020, and zerobas matches it.
- The numbers are the standard MSX error codes; the messages that go with them
  are listed by raising each one with `ERROR n` in
  [msgexact-msx1-characterization.md](../msgexact-msx1-characterization.md).

## Example

```
10 ON ERROR GOTO 70
20 A=1/0
30 PRINT ERR;ERL
40 A=ERR 1
50 PRINT "done"
60 END
70 PRINT "Error";ERR;"in";ERL
80 RESUME NEXT
RUN
Error 11 in 20
 0  20
Error 2 in 40
done
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_err.out`](../../scratchpad/kwdoc_err.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

Line 30 runs after the `RESUME NEXT`: `ERR` is back to 0, `ERL` still says 20.

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: the RAM comparison has not yet
been able to rate `ERR`'s test programs.

## What we found, and how

- **`ERR` arrived with error trapping on 2026-07-19.** Measuring the VG-8020
  showed that `RESUME` clears `ERR` but keeps `ERL`; the earlier design had
  guessed both were cleared:
  [spec-basic-error-handling.md](../spec-basic-error-handling.md).
- **Syntax errors in a program could not be caught** (fixed 2026-07-22), so a
  handler never saw `ERR` = 2 for a malformed statement. They are trapped now,
  as on the reference.
- **`ON ERROR GOTO 0` inside a handler swallowed the error** (fixed 2026-08-09,
  D-ONERR0) — and the row reading `ERR` and `ERL` afterwards agreed with the
  reference throughout, because the values had been written when the error was
  first raised. Only the message on the screen showed the defect; the rows now
  read both.
- **Every test raised code 7** (2026-09-14, D-KWBREADTH): an `ERR` that always
  answered 7 would have passed. A row raising 53 was added.

## Where it lives

`ev_f_errfn` in [basic/expr.asm](../../basic/expr.asm) reads the code that
`raise_error` in [basic/interp.asm](../../basic/interp.asm) stored; `ex_resume`
in the same file clears it.

## Related concepts

- [Errors](../concepts/errors.md) — codes, messages and `ON ERROR`

## Tests that cover it

- `make error-trap-acceptance` — `ERR` inside handlers, and its reset on
  `RESUME`.
- `make onerr0-acceptance` — `ERR`/`ERL` after each way a handler can end.
- `make kwsweep` — the everyday rows (7 and 53) and the error row `A=ERR 1`
  (2).
- `make kwram` — the RAM-usage comparison.
