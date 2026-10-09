<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `STOP` — pause the program with a `Break` message

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors: not applicable · RAM usage not yet proven · every error not yet
> proven. One recorded difference: `STOP` followed by junk (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`STOP` halts the program and prints `Break in <line>`, exactly as pressing
Ctrl-STOP would. Unlike [`END`](END.md) it is a pause: variables, open loops
and subroutines are kept, and [`CONT`](CONT.md) carries on with the next
statement. It is the classic debugging tool — stop, `PRINT` a few variables,
`CONT`. zerobas behaves like the Philips VG-8020 in every case we have
measured, except `STOP` followed by something it does not expect.

## Syntax

```
STOP
```

`STOP ON`, `STOP OFF` and `STOP STOP` are a different statement: they
switch the `ON STOP GOSUB` trap for the Ctrl-STOP key.

## Details

- **The message is `Break in <line>`** in a program. Typed at the prompt,
  `STOP` prints a bare `Break`.
- **`CONT` resumes at the statement after the `STOP`**, mid-line if there is
  one. Each new `STOP` moves the resume point.
- **A typed `STOP` does not spoil a pending `CONT`.** After a program stops,
  typing `STOP` at the prompt (or `END`, or a line with an error) and then
  `CONT` still continues the program.
- **Inside an `ON ERROR` handler, `STOP` keeps the handler active**, so `CONT`
  resumes inside it; `END` would finish it.
- **The message appears on the text screen.** A `STOP` in a `SCREEN 2`
  program returns to the text screen first, as an error message does.
- **Music stops.** A `PLAY` still sounding is silenced, and `CONT` does not
  bring it back.
- **Common errors: not applicable.** `STOP` has no arguments to get wrong;
  Joost ruled on 2026-09-29 to declare the common-errors rung not applicable
  for `END`, `STOP`, `REM`, `CLS` and `LLIST`.

## Example

```
10 FOR I=1 TO 3
20 PRINT I
30 IF I=2 THEN STOP
40 NEXT
RUN
 1
 2
Break in 30
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_stop.out`](../../scratchpad/kwdoc_stop.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)). The
[`CONT`](CONT.md) page shows the same pause followed by `CONT`.

## Differences from the reference

**`STOP 1` breaks here; the VG-8020 raises `Syntax error`** (error 2) instead
(found 2026-09-27 by the every-error enumeration;
[t6enum_b7.out](../../scratchpad/t6enum_b7.out)). zerobas does not check that
the statement ends after a bare `STOP`. It is filed with the same defect in
`END 1` and `CLS 1` (D-BAREEXTRA, a TIER 6 item in [TODO.md](../../TODO.md)),
and it is why the "every error" rung is not proven: `Syntax error` is the only
error `STOP` can raise. `STOP ON 1` and `STOP,` are `Syntax error` on the
VG-8020 too.

The other rung not yet proven is **RAM usage**.

## What we found, and how

- **`Break in 10` was invisible in graphics mode** (fixed 2026-09-27,
  D-GFXERRMSG). zerobas printed the message into the `SCREEN 2` picture and
  went back to text only for the prompt, so the user saw nothing but the
  prompt. The VG-8020 returns to the text screen first.
- **A typed `STOP` destroyed a pending `CONT`** (fixed 2026-07-30, D-CONTR).
  The old rule had been taken from a single row measured with nothing to
  continue, where "destroys it" and "leaves it alone" look the same; a row
  with a live resume point underneath showed the reference leaves it alone
  ([spec-basic-cont-record.md](../spec-basic-cont-record.md)).
- **A stopped program kept playing music** (fixed 2026-09-03, D-GICINI):
  both references silence the sound chip at a break; zerobas held the note
  for ever ([spec-basic-gicini.md](../spec-basic-gicini.md)).
- **Why `STOP` keeps an error handler and `END` does not** was measured on
  2026-07-29 (D-ONEFLG): two rows say "must not clear", and a deliberately
  wrong build failed exactly those two
  ([spec-basic-oneflg-reset-scope.md](../spec-basic-oneflg-reset-scope.md)).

## Where it lives

`ex_stop` in [basic/program.asm](../../basic/program.asm) sends a bare `STOP`
to `do_break`, which Ctrl-STOP uses too: it records the `CONT` point
(`cont_record`), silences the sound, returns to the text screen and prints
`Break` with `print_in_lineno`. `STOP ON`/`OFF`/`STOP` are handled in the
same routine.

## Related concepts

- [Errors](../concepts/errors.md) — codes, messages and `ON ERROR`
- [Interrupts and traps](../concepts/interrupts-and-traps.md) — what runs between statements

## Tests that cover it

- `make kwsweep` — the everyday row (the `Break in 10` message is what it
  reads) and the `STOP 1` error row, which does not agree yet.
- `make abort-acceptance` — the `CONT` point a `STOP` records, and what typed
  statements do to it.
- `make direct-ctrl-acceptance` — a `STOP` typed at the prompt.
- `make gicini-acceptance` — music after a `STOP` and after `CONT`.
- `make kwram` — the RAM-usage comparison.
