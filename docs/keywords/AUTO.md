<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no verify=no reason="AUTO is an interactive line-entry mode that only CTRL+STOP ends" -->

# `AUTO` — number the lines for you while you type

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven. No known
> divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`AUTO` puts the machine in line-entry mode: it prints a line number, you type
the rest of the line and press RETURN, and it prints the next number. CTRL+STOP
ends it. zerobas behaves like the Philips VG-8020 in every case we have
measured.

## Syntax

```
AUTO [<start>][,<increment>]
```

## Details

- **`AUTO`** starts at 10 and counts in tens; **`AUTO 55`** starts at 55,
  still in tens; **`AUTO 100,5`** gives 100, 105, 110, ….
- **With the comma form, an absent start is 0**: `AUTO ,7` prompts 0, then 7.
  (Bare `AUTO`'s 10 applies only when there is no argument at all. `RENUM ,,5`
  starts at 10 — the sibling verb answers the same question the other way; see
  [`RENUM`](RENUM.md).)
- **A `*` after the number warns that the line already exists**: `10*` means
  whatever you type replaces line 10. The `*` is only on the screen; the stored
  line is ordinary.
- **Pressing RETURN on an empty line stores nothing**, and the next number
  comes up anyway.
- **CTRL+STOP leaves `AUTO`** and returns to command mode, without printing
  `Ok`.
- **`AUTO` ends the line and the program**: in `AUTO 10:B=9`, `B=9` never runs.
  It also works as a program statement.
- **An increment of 0 is refused**: `AUTO 10,0` and `AUTO ,` are
  `Illegal function call` (error 5).

## Example

With `10 REM OLD` already in the program, type `AUTO 5,5`, enter two lines,
and press CTRL+STOP at the `15` prompt; then `LIST`:

```
10 REM OLD
AUTO 5,5
5 REM FIRST
10*REM SECOND
15
LIST
5 REM FIRST
10 REM SECOND
```

This example is not run by the example checker, because `AUTO` waits for
typed lines and only CTRL+STOP ends it. Every rule it shows — the start and
step, the `*` on an existing line, the replaced line, CTRL+STOP — is measured
on both reference machines and on zerobas by `make editverb-acceptance` (the
`aut-` rows), and the three forms by `make kwsweep`. The exact screen around
the CTRL+STOP has not been compared.

## Differences from the reference

None known.

Two rungs are not yet proven: **RAM usage**, and **every error** — the full
set of errors `AUTO` can raise has not been enumerated on the reference yet.

Not yet measured on the reference: backspacing over the prompt's digits, and
what happens when a line typed during `AUTO` is itself an error (zerobas ends
the `AUTO` session).

## What we found, and how

- **`AUTO` used to be a `Syntax error`.** It got its token on 2026-08-01
  (D-KWGAP4) and its statement on 2026-08-06 (D-EDITVERB).
- **"It cannot be measured" turned out to be wrong** (D-EDITVERB). `AUTO` had
  been filed as untestable against the reference because it waits for typing.
  The test rig can type lines into it, and it can press CTRL+STOP as a key
  combination, so `AUTO` was measured on both references before it was built
  ([editverb-msx1-characterization.md](../editverb-msx1-characterization.md)).
- **`AUTO ,7` starts at 0, not 10** — the opposite of `RENUM ,,5`, measured
  rather than copied from the sibling verb.
- **One `AUTO` row once broke twenty-one others.** Because `AUTO` leaves the
  machine in line-entry mode, the keyword sweep's first `AUTO` row swallowed
  the input of the rows that followed it. Each `AUTO` row now gets a fresh
  machine of its own, which is what let all three forms get rows (2026-09-17,
  D-KWAUTO).

## Where it lives

- `ex_auto` in [basic/program.asm](../../basic/program.asm) prints each prompt
  (with the `*` when the line exists) and reads the line.
- `le_auto` in [sub/lineedit.asm](../../sub/lineedit.asm) parses the start and
  the increment.
- The design notes are in [spec-basic-editverb.md](../spec-basic-editverb.md).

## Tests that cover it

- `make editverb-acceptance` — the `aut-` rows: defaults, start, increment,
  `AUTO ,7`, the `*`, an empty entry, the `:` tail and CTRL+STOP.
- `make kwsweep` — one row per form (the first prompt, and the second prompt
  for the increment) and the increment-0 error row.
- `make kwram` — the RAM-usage comparison.
