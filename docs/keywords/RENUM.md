<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no run=RENUM answers="LIST|RENUM 100,20,5|LIST|RENUM 10,,0" -->

# `RENUM` — renumber the program

> **Spec:** DRAFT 1 (2026-11-25) — 9 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`klist.py`](../../probes/basic/spec/klist.py), with NEW's, LIST's, DELETE's and RENUM's
> cases together; it reads the screen); every rule is executable, every recorded output is read by one,
> and every rule is pinned by a control of its own. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`RENUM` gives the program's lines new, evenly spaced numbers and rewrites every
`GOTO`, `GOSUB`, `THEN`, `RESTORE` and other line reference to match. It is an
editor command, normally typed at the prompt. zerobas behaves like the Philips
VG-8020 in every case we have measured, errors and messages included.

## Syntax

```
RENUM [<new start>][,[<old start>][,<increment>]]
```

All three are optional. The defaults: new start 10, increment 10, and
renumbering begins at the program's first line. `.` may stand for either line
number.

## Details

- **`RENUM`** makes the lines 10, 20, 30, …; **`RENUM 100`** makes them 100,
  110, 120, ….
- **`RENUM 100,30`** renumbers only from the old line 30 onwards; lines below
  30 keep their numbers. **`RENUM 100,,5`** sets the increment.
- **An absent new start is 10**, also in the comma forms: `RENUM ,,5` starts at
  10. (`AUTO ,7` starts at 0 — the sibling verb answers the same question the
  other way; see [`AUTO`](AUTO.md).)
- **Every line reference is rewritten**: `GOTO`, `GOSUB`, `RESTORE`, `THEN`,
  `ELSE`, every number in an `ON … GOTO` list, `RUN <line>`, and references in
  lines that were not themselves renumbered.
- **Only real references are touched.** A number inside a string, a `DATA` or
  `REM` text, or a `&H` constant is left alone.
- **A reference to a line that does not exist is reported, not refused.**
  `RENUM` prints `Undefined line 77 in 3` — the target, then the containing
  line's **old** number — once per such reference, and renumbers anyway. It is
  not an error: `ERR` stays 0 and `ON ERROR` does not catch it.
- **`RENUM` keeps variables and the `CONT` point** (unlike `DELETE`), and ends
  the line: in `RENUM:B=9`, `B=9` never runs. It also works as a program
  statement, and the program stops after it.

| you type | you get |
|---|---|
| `RENUM 10,,0` (increment 0) | error 5, `Illegal function call`, nothing changed |
| new numbers that would not stay above the lines left alone (`RENUM 20,30` on 10, 20, 30) | error 5, nothing changed |
| new numbers that would pass 65529 | error 5, nothing changed |
| a typed number past 65529 (`RENUM 65530`) | error 2, `Syntax error` |
| four arguments (`RENUM 10,1,10,7`) | error 2, `Syntax error` |

The errors the measured forms raise are {2, 5}, the same on both machines.

## Example

```
1 PRINT "A"
2 GOTO 1
3 GOSUB 77
RENUM
Undefined line 77 in 3
LIST
10 PRINT "A"
20 GOTO 10
30 GOSUB 77
RENUM 100,20,5
Undefined line 77 in 30
LIST
10 PRINT "A"
100 GOTO 10
105 GOSUB 77
RENUM 10,,0
Illegal function call
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_renum.out`](../../scratchpad/kwdoc_renum.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/renum_rules.py`](../../probes/basic/spec/renum_rules.py), loader in
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
- **[KNL FX *i*]** (RENUM), the lines typed after NEW / CLS:
  30: `5 GOTO 9` / `7 PRINT "X"` / `9 PRINT "Y"` / `RENUM` / `LIST`
  31: `5 GOTO 9` / `7 PRINT "X"` / `9 PRINT "Y"` / `RENUM 100` / `LIST`
  32: `10 PRINT "A"` / `20 PRINT "B"` / `30 GOTO 20` / `RENUM 100,20` / `LIST`
  33: `5 PRINT "A"` / `7 PRINT "B"` / `RENUM ,,5` / `LIST`
  34: `5 GOTO 77` / `RENUM` / `LIST`
  35: `5 PRINT "GOTO 7":REM 9` / `7 RESTORE 7:GOSUB 7:ON 1 GOTO 7,5` / `RENUM` / `LIST`
  36: `10 PRINT "A"` / `RENUM 10,,0` / `LIST`
  37: `10 PRINT "A"` / `20 PRINT "B"` / `30 PRINT "C"` / `RENUM 20,30` / `LIST`
  38: `10 A=5:STOP` / `20 PRINT A` / `30 REM` / `RUN` / `RENUM 100` / `CONT`

**Controls** ([`klist_controls.py`](../../probes/basic/spec/klist_controls.py)): each changes ONE law of the
interpreter and runs over the reference's cases: “an absent new start in the comma forms is 0” is FALSE on 1 of the 4 cases R-RENUM-NUMBERS selects (e.g. KNL FX 33); “a reference to a missing line is error 8” is FALSE on 1 of the 2 cases R-RENUM-REFS selects (e.g. KNL FX 34); “numbers inside strings are rewritten too” is FALSE on 1 of the 2 cases R-RENUM-REFS selects (e.g. KNL FX 35); “overlapping new numbers are allowed” is FALSE on 1 of the 2 cases R-RENUM-CHECK selects (e.g. KNL FX 37); “RENUM is a program edit” is FALSE on 1 of the 1 cases R-RENUM-KEEPS selects (e.g. KNL FX 38).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/renum_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/renum_rules.py --write` -->

**4 rules; 4 hold on the reference. Of the 92 recorded outputs (each case's normalised screen (prompts as <prompt>, the echo of the typed lines, the output, the messages)): 92 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The new numbers

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-RENUM-NUMBERS** RENUM makes the lines 10, 20, ...; RENUM n starts at n; RENUM n,old renumbers only from the old line `old` on; an absent new start is 10, also in the comma forms (RENUM ,,5: 10, 15). | 4 | ✓ | ✓ |

#### 2. References

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-RENUM-REFS** Every line reference is rewritten -- GOTO, GOSUB, RESTORE, every number of an ON ... GOTO list -- but not a number inside a string or a REM. A reference to a missing line is reported (`Undefined line 77 in 5`: the target, then its line's OLD number), left as it is, and the renumbering goes on: no error. | 2 | ✓ | ✓ |

#### 3. Errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-RENUM-CHECK** An increment of 0, or new numbers that would not stay above the lines left alone, is error 5, and nothing changes. | 2 | ✓ | ✓ |
| **R-RENUM-KEEPS** RENUM is not an edit of the variables: they and the CONT point survive it (CONT goes on in the renumbered line). | 1 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] RENUM of references after THEN / ELSE / RUN, RENUM past 65529, and AUTO (CTRL+STOP: its own page).

## What we found, and how

- **`RENUM` used to be a `Syntax error`.** It got its token on 2026-08-01
  (D-KWGAP4) and its statement on 2026-08-06 (D-EDITVERB), after 23 rules were
  measured on both references
  ([editverb-msx1-characterization.md](../editverb-msx1-characterization.md)).
- **The first measurements could not tell any rule apart.** They renumbered a
  program already numbered 10, 20, 30 — which `RENUM` leaves as it is, so even
  "`RENUM` does nothing" agreed. They were re-run on a program numbered 1, 2,
  3, ….
- **A `&H0E0E` constant settled how references are found.** On both
  references it survives `RENUM` intact and prints no `Undefined line`
  message, so the reference walks the line token by token rather than scanning
  its bytes. zerobas does the same.
- **The first build refused `RENUM 65529` on a one-line program**: it checked
  the number a second line would have needed, in a program that has none. Fixed
  before it shipped, and the edge is now tested with one, two and three lines.
- **The keyword sweep could not rate `RENUM` at first** (2026-09-16,
  D-KWEDIT): inside a running program its only reading was an error. Typed at
  the prompt, on a program numbered 5, 7, 9, the listing afterwards separates
  all four forms.

## Where it lives

- `pe_renum` in [sub2/pgmedit.asm](../../sub2/pgmedit.asm) (the sub-ROM's page 1 since 2026-11-04; the second sub-ROM's from 2026-10-24) calls the
  line-editor code in the sub ROM and prints each `Undefined line … in …`
  report it hands back.
- `le_renum` and `le_renum_next` in [sub/lineedit.asm](../../sub/lineedit.asm)
  check the arguments and rewrite the line numbers and references in place.
- The design notes are in [spec-basic-editverb.md](../spec-basic-editverb.md).

## Related concepts

- [Program text](../concepts/program-text.md) — how a typed line becomes a program line

## Tests that cover it

- `make editverb-acceptance` — the `rnm-` rows: every rule above, on both
  references and zerobas.
- `make kwsweep` — one row per form, and the error rows for {2, 5}.
- `make kwram` — the RAM-usage comparison.
