<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `RESTORE` — choose where `READ` starts

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`RESTORE` moves the reading position of [`READ`](READ.md) back to the first
[`DATA`](DATA.md) item in the program, or, with a line number, to the `DATA`
in that line. zerobas behaves like the Philips VG-8020 in every case we have
measured, errors included.

## Syntax

```
RESTORE
RESTORE <line>
```

## Details

- **`RESTORE`** makes the next `READ` take the program's first `DATA` item
  again.
- **`RESTORE n`** makes the next `READ` take the `DATA` in line `n` — not the
  first item, and not the next one in order.
- **The rest of the line runs**: `READ A:RESTORE:READ B` reads the same item
  twice.
- **A line that does not exist is `Undefined line number`** (error 8):
  `RESTORE 99` with no line 99.
- **Anything else after `RESTORE` is the same error 8**, not a syntax error:
  `RESTORE X`, `RESTORE,`.
- **`RUN`, `CLEAR` and any program edit reset the position too**, as a bare
  `RESTORE` does (see [`READ`](READ.md)).

The whole set of errors `RESTORE` can raise is {8}, the same on both machines.

## Example

```
10 READ A,B:RESTORE:READ C
20 RESTORE 80:READ D
30 PRINT A;B;C;D
40 ON ERROR GOTO 60
50 RESTORE 99:END
60 PRINT "Error";ERR:END
70 DATA 1,2
80 DATA 3
RUN
 1  2  1  3
Error 8
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_restore.out`](../../scratchpad/kwdoc_restore.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

Not yet measured on the reference: `RESTORE` to a line that exists but holds no
`DATA`.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **A bare `RESTORE` ended the whole line** (fixed 2026-08-31, D-DATACOLON).
  In `READ A:RESTORE:READ B`, the second `READ` never ran, so `B` was wrong.
  The code returned in a way that skipped the rest of the line, under a comment
  saying nothing could follow a bare `RESTORE`
  ([spec-basic-datacolon.md](../spec-basic-datacolon.md)).
- **`RESTORE X` was silently ignored** (fixed the same day). Both references
  answer `Undefined line number`, as if asked for a line that is not there.
- **`CLEAR` and program edits did not reset the reading position** (fixed
  2026-09-13, D-READDIR), found while fixing a `READ` at the prompt that read
  0. The reference resets it at the same moments it clears the variables.
- **The line form had no test of its own** (2026-09-15, D-KWRETRES). The new
  row has three `DATA` lines, so only honouring the line number gives the
  expected value: the start gives a different one, and carrying on gives a
  third.

## Where it lives

`ex_restore` in [basic/program.asm](../../basic/program.asm): the bare form
and the line form share one ending (`restore_done`); a line that is not found
goes to `GOTO`'s `Undefined line number` error.

## Tests that cover it

- `make kwsweep` — the bare row (two `READ`s with a `RESTORE` between), the
  line row, and the error rows for {8}.
- `make kwram` — the RAM-usage comparison.
