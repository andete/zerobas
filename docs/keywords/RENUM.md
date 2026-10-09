<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no run=RENUM answers="LIST|RENUM 100,20,5|LIST|RENUM 10,,0" -->

# `RENUM` — renumber the program

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

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

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

- `ex_renum` in [basic/program.asm](../../basic/program.asm) calls the
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
