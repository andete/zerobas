<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `PRINT` — write text and numbers to the screen

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven. Two
> recorded differences, both in rare `PRINT USING` formats with `$$` (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`PRINT` writes a list of strings and numbers to the screen at the cursor. A
`;` between items joins them, a `,` moves to the next 14-column zone, and
`TAB(` and `SPC(` position the next item. `PRINT USING` formats numbers and
strings through a template. zerobas behaves like the Philips VG-8020 for
every case we have measured, apart from two `PRINT USING` corner cases.

## Syntax

```
PRINT [<item>] [<separator> <item>]... [<separator>]
PRINT USING <format>; <value> [; <value>]... [;]
```

An item is a string or numeric expression, `TAB(<column>)` or
`SPC(<count>)`; a separator is `;` or `,`. `?` is typed as a shorthand for
`PRINT` and stored as the same keyword. `PRINT #n,...` writes to a file or
device channel instead — see [`OPEN`](OPEN.md). [`LPRINT`](LPRINT.md) is the
same statement for the printer.

## Details

- **Numbers** are printed with a leading space (or `-`) and a trailing space:
  `PRINT 1;2` shows ` 1  2 `, `PRINT -5` shows `-5 `.
- **`;` joins** items with nothing in between. **A trailing `;` or `,`** keeps
  the cursor on the line, so the next `PRINT` continues it. A bare `PRINT`
  ends the line (an empty line if nothing was printed on it).
- **`,` moves to the next zone**, zones being 14 columns apart. If the whole
  next zone does not fit on the line, `,` starts a new line instead: at
  `WIDTH 40`, `PRINT "A","B","C"` puts `C` at the start of the next line,
  because the third zone would run from column 28 to 41.
- **A number that does not fit moves whole to the next line.** If the sign
  and digits would run past the end of the line, the line is ended first; a
  string, by contrast, wraps character by character.
- **`TAB(n)`** pads to column n (0-based). If the cursor is already at or past
  column n it does nothing — no new line either. **`SPC(n)`** prints n spaces.
  Both take 0 to 255 and truncate fractions (`TAB(10.7)` is `TAB(10)`), and
  both exist only inside `PRINT`: `X=TAB(5)` is a `Syntax error`.
- **`PRINT USING`** fields, as measured on the VG-8020 (value `42` unless
  shown):

  | format | prints | format | prints |
  |---|---|---|---|
  | `###` | ` 42` | `###` with 12345 | `%12345` (too wide) |
  | `##.##` with 3.14159 | ` 3.14` | `##.#` with 2.35 | ` 2.4` |
  | `+###` | ` +42` | `###-` with -42 | ` 42-` |
  | `**###` | `***42` | `$$###` | `  $42` |
  | `#####,` with 12345 | `12,345` | `##.##^^^^` with 123.456 | ` 1.23E+02` |
  | `!` with "ABC" | `A` | `&` with "ABC" | `ABC` |
  | `\   \` with "ABCDE" | `ABCDE` | `X#Y` with 5 | `X5Y` |

### Errors

| you write | you get |
|---|---|
| `PRINT "A"+1` | error 13, `Type mismatch` |
| `TAB(256)`, `TAB(-1)`, `SPC(256)`, `SPC(-1)` | error 5, `Illegal function call` |
| `TAB(99999)`, `SPC(99999)` | error 6, `Overflow` |
| `TAB("A")`, `SPC("A")` | error 13 |
| `TAB()`, `SPC()`, and `TAB(` or `SPC(` outside a `PRINT` | error 2, `Syntax error` |
| `PRINT USING` with no format | error 24, `Missing operand` |
| `PRINT USING` with a format that is not a string | error 13 |
| `PRINT USING "##",5` (`,` instead of `;`) | error 2 |
| `PRINT USING` with `;` and a field, but no value | error 24 |
| `PRINT USING "abc";5` (no field in the format) | error 5 |

None of the `PRINT USING` errors prints anything first.

## Example

```
10 PRINT "A";"B";1;-2
20 PRINT "A","B","C"
30 PRINT "X";TAB(8);"Y";SPC(3);"Z"
40 PRINT USING "##.##";3.14159
50 PRINT "Same";:PRINT " line"
60 ON ERROR GOTO 90
70 PRINT "A"+1
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
AB 1 -2
A             B
C
X       Y   Z
 3.14
Same line
Error 13
```

Line 20 shows the zone rule: `B` goes to column 14, but the next zone would
not fit in 40 columns, so `C` starts a new line.
Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_print.out`](../../scratchpad/kwdoc_print.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**Two `PRINT USING` formats with `$$` in an unusual place still differ**
(recorded with D-USING on 2026-09-09, not re-measured since):

| format, value | VG-8020 | zerobas |
|---|---|---|
| `###$$`, 42 | ` 42` — the trailing pair is swallowed | ` 42$$` |
| `**$$###`, 42 | `$42$` | `****$42` |

The National CF-3300 gives a third answer for the second. Why the VG-8020
prints `$42$` has not been worked out; the ordinary `$$` in front of the
digits is implemented and matches.

Two rungs are not yet proven. **Every error**: the error sets of `TAB(` and
`SPC(` are measured and agree, but those of the separator forms (`;`, `,`,
trailing separator) have not been measured on the reference. **RAM usage**:
the set of documented work-area cells each machine writes is not the same.

## What we found, and how

- **`TAB(`, `SPC(`, `POS` and `CSRLIN` arrived together on 2026-07-27**
  ([spec-basic-cursor-cluster.md](../spec-basic-cursor-cluster.md)). Before
  that `TAB(5)` was read as element 5 of an array — and `PRINT TAB(99999)`
  raised `Overflow` on both machines for different reasons, so a comparison
  that only looked at the error code agreed while the feature was missing.
  The rule that `TAB(` to a column already passed does nothing could only be
  seen by where text landed on the screen.
- **The comma rule was wrong** (fixed the same day, D-CUR-1): zerobas always
  moved to the next zone and never started a new line, so `PRINT "A","B","C"`
  put `C` at column 28. Three items could not show where the reference's
  boundary lies at any legal width; two items at `WIDTH 27` and `28` did.
- **`X=TAB(5)` outside a `PRINT` answered `Missing operand`** where both
  references say `Syntax error` (fixed 2026-09-01, D-MISSOPBOUND).
- **`PRINT USING` had two answers for a malformed statement where the
  references have five** (fixed 2026-08-26, D-PUSING), and **its decimal,
  exponent, comma, sign and `**` formats were missing** (found 2026-09-02,
  shipped 2026-09-03/04: D-PUSTAR, D-PUDOT, D-PUCOMMA, D-PUEXP, D-PULEAD).
  Along the way the formatter turned out to render into an 8-byte buffer: the
  comma format already overran it, and a very large number printed nothing at
  all (fixed 2026-09-04, D-PUBUF).
- **`$$` follows the VG-8020** (2026-09-09, D-PUDOLLAR). The two references
  disagree: the VG-8020 floats one `$` against the digits, the CF-3300 prints
  `$$` literally. The CF-3300 handles `**` correctly, the same kind of
  two-character prefix, which showed that it simply lacks `$$`; zerobas
  follows the machine that implements it, as it already did for `&` and
  `\ \`, which the CF-3300 refuses.
- **A number was split across the end of the line** (fixed 2026-10-06,
  D-PRNUMWRAP): in a `PRINT I;` loop reaching the right edge, `601` became
  `6` / `01`, where both references move the whole number to the next line.

## Where it lives

- [basic/print.asm](../../basic/print.asm): `ex_print` and the item loop
  `exp_loop`; `print_comma_zone` (zones and the fit test), `exp_tab` and
  `exp_spc`, and `pnum_fit` (moving a number to the next line).
- `PRINT USING`: `ex_print_using` in
  [basic/printusing.asm](../../basic/printusing.asm), with the rendering in
  [basic/pu-render.inc](../../basic/pu-render.inc),
  [sub/printusing.asm](../../sub/printusing.asm) and
  [sub/punum.asm](../../sub/punum.asm).

## Tests that cover it

- `make cursor-acceptance` — `TAB(`, `SPC(` and the comma zones, read as the
  position of a marker on the screen.
- `make prnumwrap-acceptance` — numbers and a string at the end of a line.
- `make pusing-acceptance` — the `PRINT USING` formats, splits included.
- `make kwsweep` — one row per form (`;`, `,`, trailing separator, `TAB(`,
  `SPC(`), the `Type mismatch` row, and the error rows for `TAB(` and `SPC(`.
- `make kwram` — the RAM-usage comparison.
