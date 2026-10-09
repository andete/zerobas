<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no verify=no reason="needs a printer" -->

# `LPRINT` — print to the printer

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven. No known
> divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`LPRINT` is [`PRINT`](PRINT.md) with the output going to the printer instead
of the screen: the same items, the same separators, the same number format.
[`LPOS`](LPOS.md) tells you where the printer head is. zerobas sends the same
bytes as the Philips VG-8020 for every case we have measured, on the VG-8020
and the National CF-3300 alike.

## Syntax

```
LPRINT [<item>] [<separator> <item>]... [<separator>]
LPRINT USING <format>; <value> [; <value>]...
```

Items and separators are `PRINT`'s: `;`, `,`, `TAB(n)`, `SPC(n)`.

## Details

All measured with a printer attached, on both reference machines:

- **Each `LPRINT` ends its line with a carriage return and line feed**, unless
  it ends with `;` or `,`. A bare `LPRINT` prints an empty line.
- **Numbers are printed as on the screen**: a leading space or `-` for the
  sign and a trailing space. `LPRINT 5` sends ` 5 `, `LPRINT -5` sends `-5 `.
- **`;` joins, `,` moves to the next 14-column zone**, counted from the
  printer head's own column: `LPRINT "A","B"` sends `A`, 13 spaces, `B`.
- **`TAB(n)` pads to column n and `SPC(n)` sends n spaces.**
- **`LPRINT USING` formats exactly like `PRINT USING`**: `LPRINT USING"##";5`
  sends ` 5`.
- **It does not end the program line.** `LPRINT "A":B=9` runs the `B=9`, and
  the statement after an `LPRINT` prints to the screen again.
- **A line left open with `;` is finished when BASIC returns to the prompt**,
  so the printer does get its carriage return (see [`LPOS`](LPOS.md)).
- **There is no `#channel` form.** `LPRINT #1,"A"` is `Syntax error` and
  prints nothing. To print to a numbered channel, open `"LPT:"` with
  [`OPEN`](OPEN.md) and use `PRINT #`.
- **It needs a printer.** With nothing on the printer port, a program that
  uses `LPRINT` produced no output at all on either machine, so the example
  below needs a printer attached.

### Errors

| you write | you get |
|---|---|
| `LPRINT "A"+1` | error 13, `Type mismatch` |
| `LPRINT #1,"A"` | error 2, `Syntax error`, nothing printed |

The full set of errors `LPRINT` can raise has not been enumerated on the
reference yet, which is why "every error" is not ticked.

## Example

With a printer attached:

```
10 LPRINT "ABC";:PRINT LPOS(0)
20 LPRINT "DEF":PRINT LPOS(0)
30 ON ERROR GOTO 60
40 LPRINT "A"+1
50 END
60 PRINT "Error";ERR:RESUME NEXT
RUN
 3
 0
Error 13
```

The screen shows the head column after `ABC` and after the completed line;
the paper shows `ABCDEF`. The example needs a printer, so it is not run by the
example checker; the behaviour it shows is covered by
`make lptverb-acceptance` (the head column, the line endings) and by
`make kwsweep` (the type error).

## Differences from the reference

None known.

The rungs not yet proven are **RAM usage**, which has not been compared for
`LPRINT` yet, and **every error**, whose set has not been measured.

## What we found, and how

- **`LPRINT` arrived on 2026-08-06** (D-LPTVERB), after 38 rows were measured
  on both reference machines
  ([lptverb-msx1-characterization.md](../lptverb-msx1-characterization.md)).
  Until then it was not a keyword at all (`Syntax error`), and the keyword
  sweep had skipped it on the belief that the printer would hang the tests;
  a printer logger plugged into the emulated machine never blocks, which
  removed that reason.
- **`LPRINT #1,"A"` printed several hundred zeros** in the first build. The
  design had assumed the expression parser would reject the `#`; it did not,
  and a row written to check that assumption caught it. It is now a
  `Syntax error` before anything is printed.
- **Comma zones were counted from the screen cursor** in the first build, so
  `LPRINT "A","B"` sent 14 spaces where both references send 13: the screen
  cursor was at column 0 while the printer head was at 1.
- **The first prompt sent a stray carriage return to the printer** in the
  first build, because the head counter was never set at power-on.

## Where it lives

`ex_lprint` in [basic/print.asm](../../basic/print.asm) points the output at
the printer and then runs `PRINT`'s own item loop. The printer sink is
`pch_lpt` in the same file, which also keeps the head column for `LPOS`.
`LPRINT USING` goes to `ex_print_using` in
[basic/printusing.asm](../../basic/printusing.asm).

## Tests that cover it

- `make lptverb-acceptance` — the `lpr-` rows read the printer log byte for
  byte (numbers, separators, zones, `TAB`, `SPC`, `USING`, line endings,
  `#1`), and the `scr-` rows check what reaches the screen.
- `make kwsweep` — the everyday row and the `Type mismatch` row, both with a
  printer plugged in.
