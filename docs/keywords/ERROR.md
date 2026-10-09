<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `ERROR` — raise an error on purpose

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven. One
> recorded differences: a malformed argument raises the wrong error, and the
> diskless build prints disk messages for codes 60–64 (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`ERROR n` raises error number `n` exactly as if BASIC had found it itself: an
armed `ON ERROR GOTO` handler catches it, and `ERR` and `ERL` read `n` and the
line. Without a handler the program stops with the message for `n`. It is how
a program signals its own errors, and how you test an error handler.
zerobas matches the Philips VG-8020 for every valid code measured; what
differs is how a *malformed argument* is reported.

## Syntax

```
ERROR <numeric expression>
```

One argument, an error code from 1 to 255.

## Details

- **Codes 1 to 255 are raised as given.** `ERROR 53` sets `ERR` to 53 and
  prints `File not found`. A code with no message of its own still sets
  `ERR` to that code: `ERROR 200` reads back as 200.
- **A code with no message prints `Unprintable error`.** Measured on the
  VG-8020 for 23 and 26, and for 60 to 64 (on a diskless machine the disk
  messages start at 50 and stop at 59). The messages themselves are the
  reference's text, letter for letter, capitals included (`Can't CONTINUE`,
  `NEXT without FOR`).
- **`ERROR 0` and `ERROR 256`** are `Illegal function call` (error 5).
- **In a program the message names the line** (`Division by zero in 60`); typed
  at the prompt it does not.
- **A typed `ERROR` is caught too.** After a program has armed a handler and
  ended, `ERROR 7` typed at the prompt still jumps into the handler.
- **`ERROR 21` and `ERROR 22`** print `No RESUME` and `RESUME without error`,
  the two messages that belong to [`RESUME`](RESUME.md).

| you write | you get |
|---|---|
| `ERROR 7` | error 7, `Out of memory` |
| `ERROR 200` | error 200, `Unprintable error` |
| `ERROR 0`, `ERROR 256` | error 5, `Illegal function call` |
| `ERROR "A"` | error 13 on the VG-8020; error 5 here (see *Differences*) |
| `ERROR` | error 24 on the VG-8020; error 5 here |
| `ERROR 70000` | error 6 on the VG-8020; error 5 here |
| `ERROR 1,1` | error 2 on the VG-8020; error 1 here |

The whole set of errors the VG-8020 raises for a malformed `ERROR` is
{2, 5, 6, 13, 24}.

### `ON ERROR GOTO`

`ON ERROR GOTO <line>` arms a handler; `ERROR` is the simplest way to reach it.
How a handler is armed, disarmed and left is on the [`RESUME`](RESUME.md) page.

## Example

```
10 ON ERROR GOTO 80
20 ERROR 53
30 ERROR 200
40 ERROR 0
50 ON ERROR GOTO 0
60 ERROR 11
70 END
80 PRINT "Error";ERR;"in";ERL
90 RESUME NEXT
RUN
Error 53 in 20
Error 200 in 30
Error 5 in 40
Division by zero in 60
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_error.out`](../../scratchpad/kwdoc_error.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**A malformed argument is always error 5 here** (D-ERRORARG, found
2026-09-27, open, TIER 6). The VG-8020 evaluates the argument as an ordinary
integer expression and then insists the statement ends: a string is
`Type mismatch` (13), a missing argument is `Missing operand` (24), a value
past 32767 is `Overflow` (6), and `ERROR 1,1` is `Syntax error` (2). zerobas
reports 5 for the first three and runs `ERROR 1` before it sees the `,1`.
Ordinary use — a valid code — is not affected. This is why *every error* is not
yet proven for `ERROR`.

**Codes 60 to 64 on a machine without a disk** (D-NODISKERRTXT, found
2026-10-09, open, TIER 6). The VG-8020 has no disk messages, so `ERROR 60`
to `ERROR 64` print `Unprintable error`; zerobas's diskless build prints the
CF-3300's texts (`Bad FAT`, `Bad file mode`, `Bad drive name`, `Bad sector
number`, `File still open`)
([`errtext6064_run.out`](../../scratchpad/errtext6064_run.out)).

The other rung not yet proven is **RAM usage**: the RAM comparison has not yet
been able to rate `ERROR`'s test programs.

## What we found, and how

- **An error did not stop a running program** (fixed 2026-07-18, the first
  slice of the error-handling work). zerobas printed the message and carried on
  with the next line; the VG-8020 stops. The same slice added the
  ` in <line>` suffix: [spec-basic-error-handling.md](../spec-basic-error-handling.md).
- **`ERROR n` took only the low byte of `n`** (fixed 2026-07-19), so `ERROR 300`
  raised error 44, and 0, 256 and −1 were mishandled. Measuring the VG-8020 pinned the
  rule above: 1 to 255 as given, 0 and 256 are error 5.
- **`ERROR 21` and `ERROR 25` printed the wrong text.** Both had a slot in the
  message table that pointed nowhere (fixed 2026-07-29 for 25, 2026-07-31 for
  21, D-ERR21).
- **Message wording followed a house style** until 2026-08-02 (D-MSGEXACT,
  D-MSGSUB): lower-case text, and fourteen codes with no message at all. Every
  message is now the reference's own, measured by raising each code with
  `ERROR n` on both reference machines:
  [msgexact-msx1-characterization.md](../msgexact-msx1-characterization.md).
- **Every test raised code 7** (2026-09-14, D-KWBREADTH). An `ERROR` that
  ignored its argument and always raised 7 would have passed them all; a row
  raising 53 and reading both `ERR` and `ERL` was added.

## Where it lives

`ex_error` in [basic/interp.asm](../../basic/interp.asm) checks the range and
hands the code to `raise_error` in the same file, which records `ERR`/`ERL`
and either jumps to the handler or stops the program. The common messages are
`err_msgtab` in [basic/islands.asm](../../basic/islands.asm); the rarer ones
live in the sub-ROM, [sub/errmsg.asm](../../sub/errmsg.asm).

## Related concepts

- [Errors](../concepts/errors.md) — codes, messages and `ON ERROR`

## Tests that cover it

- `make error-acceptance` and `make error-trap-acceptance` — the abort, the
  ` in <line>` suffix, trapping, and the message-table bounds (25 has a
  message, 26 does not).
- `make msgexact-gate` — every message's text against both references.
- `make kwsweep` — the everyday rows (`ERROR 7`, `ERROR 53`) and the error
  row `ERROR 0` (5).
- `make kwram` — the RAM-usage comparison.
