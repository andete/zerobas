<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no run="DELETE 20-30" answers="LIST|DELETE 25" -->

# `DELETE` — remove program lines

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`DELETE` removes one line or a range of lines from the stored program. It is an
editor command, normally typed at the prompt. zerobas behaves like the Philips
VG-8020 in every case we have measured, errors included — and `DELETE` has
stricter rules than [`LIST`](LIST.md), even though the two are typed the same
way.

## Syntax

```
DELETE <line>
DELETE <from>-<to>
DELETE -<to>
```

There is **no** `DELETE <from>-` form: both reference machines refuse it with
`Illegal function call`. `.` may stand for a line number (the line the editor
last touched).

## Details

- **The high end must name a line that exists.** `DELETE 15-30` deletes lines
  20 and 30 without complaint, but `DELETE 20-35` (no line 35) deletes
  **nothing** and is `Illegal function call` (error 5). So is
  `DELETE 10-65529`, the natural "everything from 10 on" — the end has to be
  an exact, stored line number.
- **The low end need not exist**: deletion starts at the first stored line at
  or above it.
- **The check comes before any deletion.** A refused `DELETE` removes nothing,
  keeps the variables and keeps the `CONT` point — only `ERR` changes.
- **A reversed range is refused** (`DELETE 30-20`), even when both lines exist.
- **A missing number counts as 0**, which is why `DELETE -30` deletes from the
  start up to 30, while `DELETE 20-` and a bare `DELETE` are error 5.
- **A comma is not a separator**: `DELETE 10,30` is `Syntax error` (error 2).
- **A successful `DELETE` is a program edit**: it clears all variables, and a
  following `CONT` is `Can't CONTINUE`.
- **`DELETE` ends the line and the program.** `DELETE 20:B=9` deletes line 20
  and never runs `B=9` (no error); inside a running program, `DELETE` deletes
  and the program stops.

| you type (program 10, 20, 30, 40) | you get |
|---|---|
| `DELETE 20` | line 20 gone |
| `DELETE 20-30`, `DELETE 15-30` | lines 20 and 30 gone |
| `DELETE -30` | lines 10, 20 and 30 gone |
| `DELETE 25`, `DELETE 20-35`, `DELETE 10-65529` | error 5, nothing deleted |
| `DELETE 30-20`, `DELETE 20-`, `DELETE` | error 5, nothing deleted |
| `DELETE 10,30` | error 2, `Syntax error` |

The errors the measured forms raise are {2, 5}, the same on both machines.

## Example

```
10 REM A
20 REM B
30 REM C
40 REM D
DELETE 20-30
LIST
10 REM A
40 REM D
DELETE 25
Illegal function call
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_delete.out`](../../scratchpad/kwdoc_delete.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`DELETE` used to be a `Syntax error`.** It was given its token on
  2026-08-01 (D-KWGAP4) and its statement on 2026-08-02 (D-DELETE).
- **The two ends of a range are not symmetric** (D-DELETE). Measured on both
  references before any code: the high end must exist exactly, the low end need
  not, and the check runs before the first line is removed. A second round
  added `DELETE 10-65529`, which the first round could not tell apart from the
  weaker rule "the high end must not be past the last line"
  ([delete-msx1-characterization.md](../delete-msx1-characterization.md)).
- **A failed `DELETE` changes nothing.** No first-round row could see this,
  because each one ran the program again afterwards, which clears the
  variables anyway. It took rows without the `RUN`.
- **A `CONT` defect turned up along the way** (fixed 2026-08-02, D-DELETE):
  after a `DELETE`, `CONT` printed its message but `ERR` stayed 0, where the
  references set error 17.
- **`.` landed the same day** (D-DOTLINE, 2026-08-02).
- **The keyword sweep could not rate `DELETE` at first** (2026-09-16,
  D-KWEDIT): measured from inside a running program, every form just stops the
  program. Typed at the prompt, the program text left afterwards tells every
  form apart, and that is how the sweep reads it now.

## Where it lives

- `ex_delete` in [basic/program.asm](../../basic/program.asm) hands the
  statement to the line-editor code in the sub ROM and turns its answer into a
  BASIC error.
- `le_delrange` in [sub/lineedit.asm](../../sub/lineedit.asm) parses the range,
  makes both checks and deletes.
- The design notes are in [spec-basic-delete.md](../spec-basic-delete.md).

## Tests that cover it

- `make lnblank-say-acceptance` — the `dlt-` rows: every range shape, the
  refusals, the variables and `CONT` after success and after failure, the `:`
  tail and `DELETE` inside a program.
- `make kwsweep` — one row per form, the refused `DELETE 20-`, and the error
  rows for {2, 5}.
- `make kwram` — the RAM-usage comparison.
