<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `PRINT` — write text and numbers to the screen

> **Status (2026-10-14):** level 3 — happy path ✓ · reasonable time ✓ · common
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
| a number field more than 24 columns wide, e.g. 25 `#` | error 5 |

None of the `PRINT USING` errors above prints anything first, except the last:
the text in front of the over-wide field comes out before the error
(`PRINT USING "AB` followed by 25 `#` prints `AB`, then error 5).

The 24 columns count every `#`, the point, commas, a leading `+`, `**` and
`$$`, but not `^^^^` and not a trailing `+` or `-`. A format itself can be up
to 255 characters long.

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

- **`PRINT` kept its own list of which items are strings, and it had drifted**
  (fixed 2026-10-30, D-PRSTRFN; found by rereading the code). `PRINT INPUT$(1)`
  and `PRINT SPRITE$(1)` were `Type mismatch`, and `PRINT CHR$(65) AND 1`
  printed `A` and then gave `Syntax error`, where the VG-8020 raises
  `Type mismatch` before printing anything. `PRINT` now hands every item to
  the string reader first and treats it as a number only when that declines,
  which is how `(A$)`, `FNA$` and `+A$` were already decided.

- **A string compared inside `PRINT` was worked out twice** (fixed 2026-10-30,
  D-PRSTR2X). `PRINT INKEY$="";A$="X"` reads the string, sees the `=`, and
  prints the comparison's -1 or 0. zerobas did that by starting the item again
  from its beginning, so `INKEY$`, `INPUT$` or a string `DEF FN` ran a second
  time: `PRINT INKEY$=""` with keys waiting took two of them. It now carries on
  from the string it already has. The first version of the fix broke
  `PRINT T` for every number variable (a `Type mismatch`); the test written
  for the fix has a row for that now.

- **A sign with no room gave up nothing** (fixed 2026-10-29, D-PUNEGLEAD).
  When a sign has no column of its own, the VG-8020 lets it take the place of
  the `0` in front of the point: `PRINT USING "#.##";-.5` prints `-.50`, and
  `"+.##";.5` prints `+.50`. zerobas printed `%-0.50`. With room the `0`
  stays (`-0.50`), and a value with a real integer digit still overflows.
  Measuring it found two more: `+.##` and `$$.##` were not taken as fields,
  and a sign after the field (`+#.##-`) replaced the one in front instead of
  printing as itself (`+0.25-`)
  ([measured](../../scratchpad/puneglead_measure.out),
  [both signs](../../scratchpad/puneglead_both.out)).
- **A number too small or too large for `PRINT`'s plain form printed its
  digits as if it were neither** (fixed 2026-10-29, D-PUTINY). `PRINT` writes
  such a value in E form (` 3.38081E-15 `), and `PRINT USING`'s fixed fields
  read those digits and stopped at the `E`: a trigonometry table printed
  COS(90°) as `-3.38082` where the VG-8020 prints `-0.00000`, and
  `"#######"` with 1E+15 printed `2`. On the VG-8020 a small value is rounded
  into the places like any other; a large one prints `%`, a space and the E
  form, whatever the field (`% 1E+15`, and its minus sign is dropped). Found by
  a table-printing program written for the program ladder
  ([measured](../../scratchpad/putiny_measure.out),
  [large values](../../scratchpad/putiny_big.out)).
- **`PRINT USING "**$##.##"` put the `$` at the left edge** (fixed
  2026-10-29, D-PUSTARDOL): `$***5.00` here, `***$5.00` on the VG-8020,
  which floats the `$` right before the digits and after any sign
  (`**-$5.00`; `+**$##.##` gives `***+$5.00`). Twelve shapes, all the same
  way. Found by a household-ledger program written for the project's program
  ladder ([before](../../scratchpad/pustardol_measure.out),
  [after](../../scratchpad/pustardol_after.out)).
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
- **A `PRINT USING` format longer than 32 characters was cut short** (fixed
  2026-10-14, D-PULONG). zerobas copied the format into 32 bytes of its own; a
  35-character format garbled its last field, and a field that started after
  column 32 gave error 5 because the copy held no field at all. The VG-8020
  reads the format where it is, and now so does zerobas. On the way, **a number
  field wider than 24 columns printed** where the VG-8020 gives error 5 (fixed
  the same day, D-PUWIDE).
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

## Related concepts

- [Files and devices](../concepts/files-and-devices.md) — numbered channels to the disk, the tape, the screen and the printer
- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make pustardol-acceptance` — `**$` floats the dollar (D-PUSTARDOL).
- `make putiny-acceptance` — values `PRINT` shows in E form in fixed
  `PRINT USING` fields (D-PUTINY).
- `make puneglead-acceptance` — a sign taking the `0`'s place, `+.##`,
  `$$.##` and a sign on both sides of a field (D-PUNEGLEAD).
- `make cursor-acceptance` — `TAB(`, `SPC(` and the comma zones, read as the
  position of a marker on the screen.
- `make prnumwrap-acceptance` — numbers and a string at the end of a line.
- `make pusing-acceptance` — the `PRINT USING` formats, splits included.
- `make pulong-acceptance` — formats longer than 32 characters (also with the
  string space being reorganised between values) and the 24-column limit.
- `make kwsweep` — one row per form (`;`, `,`, trailing separator, `TAB(`,
  `SPC(`), the `Type mismatch` row, and the error rows for `TAB(` and `SPC(`.
- `make prstrfn-acceptance` — `INPUT$` / `SPRITE$` items, and an operator
  after a string function (D-PRSTRFN).
- `make prstr2x-acceptance` — strings compared inside `PRINT`, keys read by
  `INKEY$` / `INPUT$` there, and a number variable (D-PRSTR2X).
- `make kwram` — the RAM-usage comparison.
