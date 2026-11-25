<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `READ` — take the next values from `DATA`

> **Spec:** DRAFT 1 (2026-11-25) — 9 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kdata.py`](../../probes/basic/spec/kdata.py), with DATA's, READ's and RESTORE's cases
> together; it reads the screen); every rule is executable, every recorded output is read by one, and
> every rule is pinned by a control of its own. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-10-13):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven. No
> known difference (the line a bad item's error names, fixed 2026-10-10).
> Numbers like `1.5` read correctly since 2026-10-09.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`READ` assigns the next items of the program's [`DATA`](DATA.md) statements to
variables, one item per variable, in program order. [`RESTORE`](RESTORE.md)
moves the starting point. zerobas reads the same values and raises the same
errors as the Philips VG-8020 in every case we have measured, except two
out-of-range number cases that are filed.

## Syntax

```
READ <variable>[,<variable>]...
```

Any variable can be a target: a one- or two-character name, with or without a
type suffix (`%`, `!`, `#`, `$`), or an array element such as `A(I)` or
`B$(2,3)`.

## Details

- **Each variable takes the next item**, across `DATA` statements and lines.
  Numbers and strings can be mixed in one `READ`: `READ A,B$`.
- **How an item is cut out of the `DATA` line** — quotes, spaces, empty items —
  is described on [`DATA`](DATA.md)'s page.
- **Reading past the last item is `Out of DATA`** (error 4), also mid-`READ`.
- **Text read into a number is `Syntax error`** (error 2).
- **An array element with a bad subscript** gives the array's own error, as an
  assignment would: `READ A(9)` after `DIM A(3)` is `Subscript out of range`.
- **`READ` works at the prompt** too, reading the stored program's `DATA`.
- **The reading position goes back to the first item** when a program is
  started with `RUN`, after `CLEAR`, after any program edit, and after a bare
  `RESTORE`. A direct `READ` after a program has ended carries on where the
  program stopped.
- **A string read from `DATA` uses no string space**: the variable points at
  the text inside the program, as on the reference.

| situation | error |
|---|---|
| no items left (`READ A` with no `DATA`) | 4 `Out of DATA` |
| a text item read into a number | 2 `Syntax error` |
| a number too large for the target (`READ A%` of 70000) | 6 `Overflow`, on both machines (KDA FX 20) |

The measured set of errors for `READ` on the VG-8020 is {2, 4, 6}.

## Example

```
10 DIM A(2)
20 FOR I=0 TO 2:READ A(I):NEXT
30 READ N$,B%
40 PRINT A(0)+A(1)+A(2);N$;B%
50 ON ERROR GOTO 80
60 READ X
70 END
80 PRINT "Error";ERR:END
90 DATA 1,2.5,3,ZB,-5
RUN
 6.5 ZB-5
Error 4
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_read.out`](../../scratchpad/kwdoc_read.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/read_rules.py`](../../probes/basic/spec/read_rules.py), loader in
[`kdata_model.py`](../../probes/basic/spec/kdata_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does. The check is the
whole interpreter; what pins a rule's SENTENCE is its controls -- each rule has at least one rival law that is false
on its own cases.

**Evidence.** One probe, [`probes/basic/spec/kdata.py`](../../probes/basic/spec/kdata.py): it reads the SCREEN, as
[`kstop.py`](../../probes/basic/spec/kstop.py) does -- each case starts with `NEW` and `CLS`, types a short program
and the commands it names, and keeps the normalised screen (the prompt -- "Ok" there, "ZB" here, a deliberate
difference -- read as one token). The model is kstop's small BASIC ([`kstop_model.py`](../../probes/basic/spec/kstop_model.py)),
the one interpreter for every screen-reading keyword probe: it types each case and predicts the WHOLE screen. Run file
[`scratchpad/KDA_run1.out`](../../scratchpad/KDA_run1.out) (JSON, 2026-11-25).
- **[KDA FX *i*]** (READ), the lines typed after NEW / CLS:
  13: `10 READ A` / `RUN`
  14: `10 READ A,B` / `20 DATA 1` / `RUN`
  15: `10 READ A:PRINT A` / `20 DATA 5,6` / `RUN` / `READ B:PRINT B`
  16: `10 DIM A(3):READ A(9)` / `20 DATA 1` / `RUN`
  17: `10 READ A:PRINT A` / `20 DATA 5,6` / `RUN` / `RUN`
  18: `10 READ A:PRINT A` / `20 DATA 5,6` / `RUN` / `CLEAR` / `READ B:PRINT B`
  19: `10 READ A:PRINT A` / `20 DATA 5,6` / `RUN` / `30 REM` / `READ B:PRINT B`
  20: `10 READ A%` / `20 DATA 70000` / `RUN`
  21: `10 READ A,B$:PRINT A;"[";B$;"]"` / `20 DATA 1` / `30 DATA Z` / `RUN`

**Controls** ([`kdata_controls.py`](../../probes/basic/spec/kdata_controls.py)): each changes ONE law of the
interpreter and runs over the reference's cases: “a READ at the prompt starts again at the first item” is FALSE on 1 of the 5 cases R-READ-NEXT selects (e.g. KDA FX 15); “CLEAR keeps READ's position” is FALSE on 1 of the 5 cases R-READ-NEXT selects (e.g. KDA FX 18); “an edit keeps READ's position” is FALSE on 1 of the 5 cases R-READ-NEXT selects (e.g. KDA FX 19); “an integer target takes any number” is FALSE on 1 of the 4 cases R-READ-ERRORS selects (e.g. KDA FX 20); “an array element is not checked against its DIM” is FALSE on 1 of the 4 cases R-READ-ERRORS selects (e.g. KDA FX 16).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/read_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/read_rules.py --write` -->

**2 rules; 2 hold on the reference. Of the 69 recorded outputs (each case's normalised screen (prompts as <prompt>, the echo of the typed lines, the output, the messages)): 69 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The next item

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-READ-NEXT** Each variable takes the next item, across DATA lines; a READ typed at the prompt goes on where the program stopped. RUN, CLEAR and a program edit take the position back to the first item. | 5 | ✓ | ✓ |

#### 2. Errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-READ-ERRORS** No item left is error 4 (Out of DATA), also in the middle of a READ; an array element out of its DIM is error 9; a number an integer cannot hold is error 6. | 4 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

No known difference in behaviour.

The rung not yet proven is **RAM usage**.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] READ into a DEF FN parameter's name, into a FOR variable, and READ of a string longer than 255.

## What we found, and how

- **`Out of DATA` did not start the data over** (fixed 2026-10-13,
  D-DATARESET). On the VG-8020 the error also puts the `DATA` position back
  where the last `RESTORE` left it (the program start, or the `RESTORE n`
  line), so after `RESUME NEXT` the next `READ` reads the first item again.
  zerobas stayed at the end, so that `READ` failed a second time. Found while
  comparing where each machine keeps the `READ` position
  ([`datareset_probe.py`](../../scratchpad/datareset_probe.py)).
- **A bad item's error named the `READ` line** (fixed 2026-10-10, D-READERL).
  For `20 DATA 12X` / `30 READ A` the VG-8020 says `Syntax error in 20`, the
  `DATA` line where the typo is: `ERL` is 20 and `LIST .` lists line 20, even
  when `READ A` is typed at the prompt; `RESUME NEXT` still goes on after the
  `READ` ([`readerl_run.out`](../../scratchpad/readerl_run.out)). zerobas named
  line 30. Fixing it showed a second fault: after a refused item zerobas's
  pointer to the current `DATA` line had already run on to the end of the
  program, so reading the item again as a string and then the next `DATA`
  line gave `Out of DATA`. Both now match.
- **Numbers that were not whole numbers could not be read** (fixed
  2026-10-09, D-READFLT): `DATA 1.5`, `2E3` and `-.25` were `Syntax error`,
  and `DATA 40000` came back as -25536, because zerobas read every numeric
  item as a 16-bit whole number. The VG-8020 reads them all. Found while
  writing these pages: every earlier test happened to use whole numbers. A
  numeric item now goes through the same number reader as `INPUT` and `VAL`,
  which also fixed `DATA 1E99` (now `Overflow`, was `Syntax error`) and
  `99999` read into `A%` (now `Overflow`, was accepted).
- **Only single-letter number variables could be read** (fixed 2026-08-07,
  D-READVAR). `READ AB`, `READ A%` and every string were `Syntax error`; 24
  cases were measured on both references first
  ([readvar-msx1-characterization.md](../readvar-msx1-characterization.md)).
  Array elements followed the next day (D-ARYLV, 2026-08-08).
- **At the prompt, `READ` silently read 0** (fixed 2026-09-13, D-READDIR). With
  `10 DATA 7` stored, a `READ` typed before any `RUN` gave 0 where the
  reference gives 7 — a wrong answer with no error, and every test had missed
  it because they all `RUN` first. Asking the reference *when* the reading
  position resets found two more differences: `CLEAR` and a program edit reset
  it there and did not here
  ([readings](../../scratchpad/readfix_datareset.out)).
- **`DATA 42:READ A` was a `Syntax error`** (fixed 2026-09-15, D-KWBARS) — see
  [`DATA`](DATA.md).
- **Reading long strings ran out of string space** (fixed 2026-10-07,
  D-READREF): zerobas copied each string, the references point at the program
  text. A 1989 type-in program stopped at its fifth `READ` here. Joost ruled on
  2026-09-27: *"point at program text"*. `MID$` on such a string copies it out
  first, so the program itself is never changed — also measured.

## Where it lives

- `ex_read` in [basic/program.asm](../../basic/program.asm) parses each target
  and stores the value; `tgt_store_ref` in [basic/vars.asm](../../basic/vars.asm)
  points a string variable at the `DATA` text.
- The item reader is `read_one_value` in
  [basic/readdata-body.inc](../../basic/readdata-body.inc), which runs from the
  sub ROM ([sub/readdata.asm](../../sub/readdata.asm)).

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision
- [Strings and string space](../concepts/strings-and-string-space.md) — where string values live
- [Variables](../concepts/variables.md) — names, types, arrays, and where they live

## Tests that cover it

- `make readvar-acceptance` — every kind of target and how items are cut into
  strings, on both references.
- `make arylv-acceptance` — array elements as targets.
- `make readref-acceptance` — strings read from `DATA` use no string space.
- `make readerl-acceptance` — the line a refused item's error names (`ERL`,
  the message, `LIST .`, from a program and from the prompt), and reading on
  past it.
- `make kwsweep` — the everyday row, the `Out of DATA` row and the error rows
  for {2, 4}.
- `make kwram` — the RAM-usage comparison.
