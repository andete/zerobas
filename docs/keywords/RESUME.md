<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `RESUME` — leave an error handler and carry on

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven. One
> recorded difference: `RESUME NEXT` after an `Overflow` (below, an open
> TIER 3 item).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`RESUME` ends an `ON ERROR GOTO` handler and tells BASIC where to continue:
at the statement that failed (to try it again), at the statement after it, or
at a line you name. It is the other half of `ON ERROR GOTO`, which is why that
statement is described here too. zerobas behaves like the Philips VG-8020 in
every case we have measured.

## Syntax

```
RESUME
RESUME 0
RESUME NEXT
RESUME <line number>
```

## Details

- **`RESUME` and `RESUME 0` run the failing statement again**, from its start.
  The handler is expected to have fixed the cause first; if it has not, the
  same error happens again.
- **`RESUME NEXT` continues with the statement after the failing one** — on
  the same line if the failing statement was followed by `:`, otherwise on the
  next line. A `:` inside a string in the failing statement does not confuse it.
- **`RESUME <line>` continues at the start of that line.**
- **Every `RESUME` sets `ERR` back to 0 but leaves `ERL` alone**: read after
  the `RESUME`, they give `0` and the line that failed.
- **`RESUME` with no error to resume from** is `RESUME without error`
  (error 22).
- **A handler that runs off the end of the program without `RESUME`** stops with
  `No RESUME` (error 21), naming the *last line that ran* — not the handler's
  first line — and `ERL` becomes that line. A handler that ends with `END`
  instead stops quietly.
- **An error inside the handler, before its `RESUME`,** is not caught again:
  the program stops with that second error's message.
- **`STOP` inside a handler keeps the handler open**; `CONT` carries on inside
  it, and its `RESUME` still works.

### `ON ERROR GOTO`

- **`ON ERROR GOTO <line>`** arms a handler; any later error jumps to that line.
  An undefined line is `Undefined line number` (error 8) when the statement
  runs, not when the error happens.
- **`ON ERROR GOTO 0`** disarms it — and, executed *inside* an active handler,
  it also re-raises the error that entered the handler, untrapped, with the
  original code and the original line. This is how a handler hands an error it
  does not want back to BASIC.
- **`ON ERROR GOTO` with nothing after it** is the same as `ON ERROR GOTO 0`.
- **`ON ERROR GOTO <line>` inside a handler** simply arms the new line and
  carries on.
- **A non-number after `GOTO`** (`ON ERROR GOTO A`) is a `Syntax error` that the
  current handler does *not* catch.
- **The handler is disarmed** whenever the variables are cleared: `RUN`, `NEW`,
  `CLEAR` (and `MAXFILES`), and editing any program line.

## Example

```
10 ON ERROR GOTO 90
20 B=-1
30 A=SQR(B):PRINT "SQR";A
40 ERROR 7:PRINT "after"
50 ERROR 9
60 PRINT "not run"
70 PRINT "line 70":END
90 PRINT "Error";ERR;"in";ERL
100 IF ERR=5 THEN B=9:RESUME
110 IF ERR=7 THEN RESUME NEXT
120 RESUME 70
RUN
Error 5 in 30
SQR 3
Error 7 in 40
after
Error 9 in 50
line 70
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_resume.out`](../../scratchpad/kwdoc_resume.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

The first error is repaired and retried (`SQR(9)` is 3), the second is
skipped, and the third jumps over line 60.

## Differences from the reference

**`RESUME NEXT` after a trapped `Overflow` skips the rest of the line**
(D-RESNEXTOVF, found 2026-10-09, open, TIER 3). With
`20 PRINT 1E62*9:PRINT "A"`, the VG-8020 resumes at `PRINT "A"`; zerobas
goes on at the next line. The same happens for `X=1E62*9` and
`PRINT CINT(40000)`. Division by zero, `SQR(-1)`, `ERROR 6` and an undefined
line resume at the right statement on both
([`resnext_run.out`](../../scratchpad/resnext_run.out)).

Two rungs are not yet proven. **Every error**: the set of errors `RESUME`
itself can raise has not been measured, because the tool that enumerates error
sets reads each error through an `ON ERROR` handler, and it got no reading for
any `RESUME` case on the VG-8020. **RAM usage**: the RAM comparison has not yet
been able to rate `RESUME`'s test programs.

## What we found, and how

- **Error trapping arrived on 2026-07-18 and 2026-07-19**, after the first
  measurement showed that an untrapped error did not even stop a zerobas
  program. `ERR` going back to 0 on `RESUME` while `ERL` stays was measured on
  the VG-8020 and added the same day:
  [spec-basic-error-handling.md](../spec-basic-error-handling.md).
- **`CLEAR` or `MAXFILES` in a running program did not disarm the handler**
  (fixed 2026-07-29, D-ONELIN). Measuring showed the rule is "whenever the
  variables are cleared", program edits included.
- **`No RESUME` was never raised** (fixed 2026-07-31, D-ERR21): a handler that
  ran off the end of the program ended silently. The line it names turned out
  to be the last line that ran, not the handler's — the earlier write-up had
  measured a program where the two were the same line:
  [spec-basic-err21-no-resume.md](../spec-basic-err21-no-resume.md).
- **`ON ERROR GOTO 0` inside a handler just disarmed** (fixed 2026-08-09,
  D-ONERR0); both references re-raise the original error. A cheaper fix that
  re-ran the failing statement was rejected by a row showing the reference
  does not re-run it:
  [onerr0-msx1-characterization.md](../onerr0-msx1-characterization.md).
- **`ON ERROR GOTO A` was caught by the current handler** (fixed 2026-09-02,
  D-ONERRGO); on both references it is not. The obvious fix would have made a
  bare `ON ERROR GOTO` an error as well, where the references treat it as
  `ON ERROR GOTO 0`: [spec-basic-onerrgo.md](../spec-basic-onerrgo.md).
- **Only `RESUME NEXT` had a test** until 2026-09-15 (D-KWRETRES). The bare and
  line forms got rows that only the right form can pass: the retried `SQR`
  must give 3, and the line form must skip an assignment in between.

## Where it lives

- `ex_resume` in [basic/interp.asm](../../basic/interp.asm); `RESUME without
  error` leaves through `ex_resume_noerr` / `raise_error_forced` in the same
  file. `RESUME NEXT`'s search for the end of the failing statement is
  `scan_stmt_end` in the sub-ROM, [sub/errtrap.asm](../../sub/errtrap.asm).
- `No RESUME` is raised by `e21_no_resume` in
  [basic/arrays.asm](../../basic/arrays.asm).
- `ON ERROR GOTO` is `ex_on_error` (disarm: `oe_disable`) in
  [basic/program.asm](../../basic/program.asm).

## Related concepts

- [Errors](../concepts/errors.md) — codes, messages and `ON ERROR`

## Tests that cover it

- `make error-trap-acceptance` — the three destinations, `RESUME without
  error`, `No RESUME`, nested errors, and what disarms a handler.
- `make onerr0-acceptance` — `ON ERROR GOTO 0` and its operand, on both
  references.
- `make kwsweep` — one row per form (bare, `NEXT`, line), and `RESUME` typed
  with no error (22).
- `make kwram` — the RAM-usage comparison.
