<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no verify=no reason="the listing goes to the printer, not the screen" -->

# `LLIST` — print the program on the printer

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors: not applicable · RAM usage not yet proven · every error not yet
> proven. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`LLIST` is [`LIST`](LIST.md) with the printer as its destination: the same
line selection, the same text, sent to the printer instead of the screen.
zerobas behaves like the Philips VG-8020 in every case we have measured.

## Syntax

```
LLIST
LLIST <line>
LLIST <from>-<to>
LLIST <from>-
LLIST -<to>
```

## Details

- **Everything about choosing lines is `LIST`'s**: `LLIST 20` prints one line,
  `LLIST 20-` prints to the end, neither end of a range has to exist, and a
  reversed range or a missing line prints nothing with no error.
- **Each line goes to the printer as its number, a space, the text, then
  carriage return and line feed.**
- **Nothing of the listing appears on the screen.**
- **A comma is not a separator**: `LLIST 10,20` is `Syntax error` and prints
  nothing.
- **`LLIST` ends the line and the program**: in `LLIST:B=9`, `B=9` never runs.
- **The screen is the destination again afterwards**: a `PRINT` after `LLIST`
  appears on the screen and sends nothing to the printer.

## Example

```
10 REM P
20 REM Q
30 REM R
LLIST 20-
```

The screen shows nothing more than the typed lines. The printer receives:

```
20 REM Q
30 REM R
```

This example is not run by the example checker, because what matters is what
reaches the printer. The same shapes are measured on both reference machines
and on zerobas by `make editverb-acceptance` (the `llt-` rows), which plugs a
printer into the emulator and compares the exact bytes it received.

## Differences from the reference

None known.

**Common errors** are declared not applicable to `LLIST`: Joost ruled on
2026-09-29 that it has no common error to prove. Two rungs
are not yet proven: **RAM usage**, and **every error** — the full set of errors
`LLIST` can raise has not been enumerated on the reference yet.

Not measured: what happens when no printer is connected.

## What we found, and how

- **`LLIST` used to be a `Syntax error`.** It got its token on 2026-08-01
  (D-KWGAP4) and its statement on 2026-08-06 (D-EDITVERB).
- **"It cannot be measured" turned out to be wrong** (D-EDITVERB). `LLIST` had
  been filed as untestable because a machine with no printer waits for one.
  The emulator's printer port takes a logging printer that is always ready and
  writes every byte to a file, so the reading is the exact byte stream —
  better than a screen, with no line wrapping
  ([editverb-msx1-characterization.md](../editverb-msx1-characterization.md)).
- **The zerobas side needed a control of its own.** An empty printer log could
  mean "no `LLIST`" or "no working printer path", so a test that prints through
  `OPEN "LPT:"` runs alongside and proves the printer path works.
- **All twenty range shapes measured for `LIST` answer the same under
  `LLIST`** on both references, so the two share one implementation and differ
  only in where the text goes.
- **The tests caught a false justification** (D-EDITVERB): four bytes that
  were supposed to switch the output back to the screen turned out to protect
  nothing, because `LLIST` always ends the run and the prompt resets the
  destination itself. They were removed; the `llt-sink` row guards the rule.

## Where it lives

`ex_llist` in [basic/list.asm](../../basic/list.asm) — it shares `ex_list`'s
parse (`le_lstrange` in [sub/lineedit.asm](../../sub/lineedit.asm)) and walk
(`list_walk`), and only selects the printer as the destination, after the parse
so that a refused `LLIST` never leaves the printer selected.

## Tests that cover it

- `make editverb-acceptance` — the `llt-` rows: the whole program, one line,
  open ranges, a reversed range, the comma error, the `:` tail and the return
  to the screen, read off the printer log.
- `make kwsweep` — the everyday row, read off the printer log.
- `make kwram` — the RAM-usage comparison.
