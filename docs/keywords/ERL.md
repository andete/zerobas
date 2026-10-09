<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `ERL` — the line of the last error

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`ERL` is the line number on which the most recent error happened. An
`ON ERROR GOTO` handler uses it, with [`ERR`](ERR.md), to tell one error from
another. zerobas behaves exactly like the Philips VG-8020 for every case we
have measured.

## Syntax

```
ERL
```

No argument and no parentheses, like `ERR`.

## Details

- **It is the line that was running when the error happened** — the same
  number an untrapped error's message shows after `in`. It survives the stop:
  `PRINT ERL` typed at the prompt afterwards still shows it.
- **[`RESUME`](RESUME.md) does not change it.** `ERR` goes back to 0, `ERL`
  keeps the failing line until the next error.
- **An error typed at the prompt has no line**: `ERL` is then 65535. The same
  goes for a line the editor refuses as you type it (`70 X=1E99` is
  `Overflow`, `70000 X=1` is `Syntax error`): `ERL` reads 65535 afterwards.
- **On a machine that has not had an error yet**, `ERL` is 0.
- **`No RESUME`** (a handler ran off the end of the program) sets `ERL` to the
  last line that ran.
- **`ON ERROR GOTO 0` inside a handler** re-raises the original error with its
  original line, not the handler's.
- **`ERL` takes nothing after it**: `A=ERL 1` is `Syntax error` (error 2), the
  only error `ERL` itself causes on the VG-8020.

## Example

```
10 ON ERROR GOTO 60
20 PRINT "A":X=SQR(-1)
30 GOTO 1000
40 PRINT "B"
50 END
60 PRINT "Error";ERR;"in";ERL
70 IF ERL=30 THEN RESUME 50
80 RESUME NEXT
RUN
A
Error 5 in 20
Error 8 in 30
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_erl.out`](../../scratchpad/kwdoc_erl.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

The handler lets the error on line 20 pass, but uses `ERL` to jump past
line 40 after the bad `GOTO` on line 30.

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: the RAM comparison has not yet
been able to rate `ERL`'s test programs.

## What we found, and how

- **`ERL` arrived with error trapping on 2026-07-19**, together with the rule
  that `RESUME` keeps it:
  [spec-basic-error-handling.md](../spec-basic-error-handling.md).
- **`No RESUME` named the wrong line** in its first write-up: the handler's
  line instead of the last line that ran (corrected before it shipped,
  2026-07-31, D-ERR21). The program it had been measured on ended on the
  handler's line, so the two answers could not be told apart:
  [spec-basic-err21-no-resume.md](../spec-basic-err21-no-resume.md).
- **A line refused by the editor left `ERL` stale** (fixed 2026-08-30,
  D-ERLENTRY): `ERL` kept whatever the last run had left, where both
  references read 65535. Ten older test rows had been carrying this as a
  second, unnoticed difference: [spec-basic-erlentry.md](../spec-basic-erlentry.md).
- **The test rows read `ERR` and `ERL` together** (2026-09-14, D-KWBREADTH),
  so "the right error" and "an error on the right line" are checked
  separately.

## Where it lives

`ev_f_erlfn` in [basic/expr.asm](../../basic/expr.asm) returns the line that
`record_errline` in [basic/interp.asm](../../basic/interp.asm) stored. It is
returned as an unsigned number, so 65535 prints as 65535 rather than −1. The
editor's case is `dl_ovf_report` in
[basic/program.asm](../../basic/program.asm).

## Tests that cover it

- `make error-trap-acceptance` — `ERL` inside handlers, after `RESUME`, and
  for `No RESUME`.
- `make onerr0-acceptance` — `ERL` after each way a handler can end.
- `make kwsweep` — the everyday row (reads 10, the failing line) and the error
  row `A=ERL 1` (2).
- `make kwram` — the RAM-usage comparison.
