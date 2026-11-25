<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no run="DELETE 20-30" answers="LIST|DELETE 25" -->

# `DELETE` — remove program lines

> **Spec:** DRAFT 1 (2026-11-25) — 11 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`klist.py`](../../probes/basic/spec/klist.py), with NEW's, LIST's, DELETE's and RENUM's
> cases together; it reads the screen); every rule is executable, every recorded output is read by one,
> and every rule is pinned by a control of its own. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
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

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/delete_rules.py`](../../probes/basic/spec/delete_rules.py), loader in
[`klist_model.py`](../../probes/basic/spec/klist_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does. The check is the
whole interpreter; what pins a rule's SENTENCE is its controls -- each rule has at least one rival law that is false
on its own cases.

**Evidence.** One probe, [`probes/basic/spec/klist.py`](../../probes/basic/spec/klist.py): it reads the SCREEN, as
[`kstop.py`](../../probes/basic/spec/kstop.py) does -- each case starts with `NEW` and `CLS`, types a short program
and the commands it names, and keeps the normalised screen (the prompt -- "Ok" there, "ZB" here, a deliberate
difference -- read as one token; a listed line longer than 37 characters wraps). The model is kstop's small BASIC
([`kstop_model.py`](../../probes/basic/spec/kstop_model.py)), the one interpreter for every screen-reading keyword
probe. Run file [`scratchpad/KNL_run1.out`](../../scratchpad/KNL_run1.out) (JSON, 2026-11-25).
- **[KNL FX *i*]** (DELETE), the lines typed after NEW / CLS:
  19: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `40 PRINT "D"` / `DELETE 20` / `LIST`
  20: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `40 PRINT "D"` / `DELETE 15-30` / `LIST`
  21: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `40 PRINT "D"` / `DELETE 20-35` / `LIST`
  22: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `40 PRINT "D"` / `DELETE -30` / `LIST`
  23: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `40 PRINT "D"` / `DELETE 20-` / `LIST`
  24: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `40 PRINT "D"` / `DELETE` / `LIST`
  25: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `40 PRINT "D"` / `DELETE 30-20` / `LIST`
  26: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `40 PRINT "D"` / `DELETE 10,30` / `LIST`
  27: `10 A=5:STOP` / `20 PRINT A` / `30 REM` / `RUN` / `DELETE 30` / `CONT`
  28: `10 A=5:STOP` / `20 PRINT A` / `30 REM` / `RUN` / `DELETE 30` / `PRINT A`
  29: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `40 PRINT "D"` / `DELETE 20:PRINT "Z"` / `LIST`

**Controls** ([`klist_controls.py`](../../probes/basic/spec/klist_controls.py)): each changes ONE law of the
interpreter and runs over the reference's cases: “the low end must exist too” is FALSE on 1 of the 3 cases R-DELETE-RANGE selects (e.g. KNL FX 20); “the high end need not exist” is FALSE on 1 of the 5 cases R-DELETE-CHECK selects (e.g. KNL FX 21); “DELETE keeps the variables and CONT” is FALSE on 2 of the 3 cases R-DELETE-EDIT selects (e.g. KNL FX 27).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/delete_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/delete_rules.py --write` -->

**3 rules; 3 hold on the reference. Of the 139 recorded outputs (each case's normalised screen (prompts as <prompt>, the echo of the typed lines, the output, the messages)): 139 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. Which lines

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-DELETE-RANGE** DELETE n deletes line n; n-m every stored line from n to m -- the LOW end need not exist; -m from the start. | 3 | ✓ | ✓ |

#### 2. Errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-DELETE-CHECK** The HIGH end must be a stored line, the range must not be reversed, and there must be a range: else error 5 (Illegal function call) -- checked before anything is deleted, so nothing is. A comma is error 2. | 5 | ✓ | ✓ |

#### 3. An edit

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-DELETE-EDIT** A DELETE that succeeds is a program edit: the variables go and CONT is `Can't CONTINUE`; it ends its line. | 3 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] DELETE of the line that is running (inside a program); DELETE of every line.

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

- `pe_delete` in [sub2/pgmedit.asm](../../sub2/pgmedit.asm) (the sub-ROM's page 1 since 2026-11-04; the second sub-ROM's from 2026-10-24) hands the
  statement to the line-editor code in the sub ROM and turns its answer into a
  BASIC error.
- `le_delrange` in [sub/lineedit.asm](../../sub/lineedit.asm) parses the range,
  makes both checks and deletes.
- The design notes are in [spec-basic-delete.md](../spec-basic-delete.md).

## Related concepts

- [Program text](../concepts/program-text.md) — how a typed line becomes a program line

## Tests that cover it

- `make lnblank-say-acceptance` — the `dlt-` rows: every range shape, the
  refusals, the variables and `CONT` after success and after failure, the `:`
  tail and `DELETE` inside a program.
- `make kwsweep` — one row per form, the refused `DELETE 20-`, and the error
  rows for {2, 5}.
- `make kwram` — the RAM-usage comparison.
