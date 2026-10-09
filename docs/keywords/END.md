<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `END` — stop the program

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors: not applicable · RAM usage not yet proven · every error not yet
> proven. One recorded difference: `END` followed by junk (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`END` stops the program and returns to the prompt, with no message. It is how
a program keeps from running on into the subroutines written after its main
part. zerobas behaves like the Philips VG-8020 for every case we have
measured, except `END` followed by something it does not expect.

## Syntax

```
END
```

No arguments.

## Details

- **Statements after `END` do not run**, whether on the same line or later
  lines.
- **`CONT` after `END` continues**, right after the `END` — mid-line if more
  statements follow it on the same line. See [`CONT`](CONT.md).
- **`END` finishes an `ON ERROR` handler for good.** If a handler ends the
  program, the next error is caught normally, and a typed `RESUME` is
  `RESUME without error`. ([`STOP`](STOP.md) is different: it only pauses,
  and `CONT` resumes inside the handler.)
- **Open files stay open** after `END` (measured on the CF-3300); it is `RUN`
  that closes them.
- **Music keeps playing.** A `PLAY` queue still sounding when the program
  ends is left to finish; only an error or a break silences it.
- **Common errors: not applicable.** `END` has no arguments to get wrong;
  Joost ruled on 2026-09-29 to declare the common-errors rung not applicable
  for `END`, `STOP`, `REM`, `CLS` and `LLIST`.

## Example

```
10 PRINT "Start"
20 GOSUB 100
30 PRINT "Back"
40 END
50 PRINT "Never"
100 PRINT "In sub"
110 RETURN
RUN
Start
In sub
Back
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_end.out`](../../scratchpad/kwdoc_end.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**`END 1` and `END,` end the program silently here; the VG-8020 raises
`Syntax error`** (error 2) without ending (D-BAREEXTRA, found 2026-09-27;
[t6enum_b5.out](../../scratchpad/t6enum_b5.out)). zerobas never checks that
the statement stops after `END`. `CLS 1` and `STOP 1` have the same kind of
difference. This is filed as a TIER 6 item in [TODO.md](../../TODO.md), and
it is why the "every error" rung is not proven: `Syntax error` is the only
error `END` can raise, and here it does not.

The other rung not yet proven is **RAM usage**.

## What we found, and how

- **`CONT` after `END` said `Can't CONTINUE`** (fixed 2026-07-30, D-CONTR).
  The source carried a comment stating, as fact, that `END` leaves nothing to
  continue; it had never been measured, and it was wrong. Measuring also
  showed *where* `END` resumes: right after itself, mid-line
  ([spec-basic-cont-record.md](../spec-basic-cont-record.md)).
- **Ending inside an error handler left the handler marked busy** (fixed
  2026-07-29, D-ONEFLG), so the next program's first error was not caught.
  The reference clears it when a run ends or aborts, but not on a `STOP`
  ([spec-basic-oneflg-reset-scope.md](../spec-basic-oneflg-reset-scope.md)).
- **That `END` leaves music playing was measured, not assumed** (2026-09-03,
  D-GICINI): it is one of the rows that pinned the rule "an abort silences
  `PLAY`, a clean end does not"
  ([spec-basic-gicini.md](../spec-basic-gicini.md)).

## Where it lives

`ex_end` in [basic/interp.asm](../../basic/interp.asm): it records the
`CONT` point through `cont_record` in
[basic/program.asm](../../basic/program.asm), clears the error-handler flag,
and stops the run loop.

## Tests that cover it

- `make kwsweep` — the everyday row: an `END` that keeps the program from
  falling into its subroutine. There is no agreeing row for `END 1` yet
  (see *Differences*).
- `make abort-acceptance` — `CONT` after `END`, mid-line and at the end of a
  line.
- `make error-trap-acceptance` — what `END` does to an active error handler.
- `make gicini-acceptance` — music after `END`.
- `make kwram` — the RAM-usage comparison.
