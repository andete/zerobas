<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `VAL` — the number at the start of a string

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`VAL(a$)` reads a number from the start of `a$` the way BASIC reads a number
typed in a program line: signs, decimals, exponents and `&H`/`&O`/`&B`
prefixes included. It stops at the first character it cannot use, and a string
with no number at the start is 0, not an error. It is the inverse of
[`STR$`](STR$.md). zerobas behaves exactly like the Philips VG-8020 for every
case we have measured, errors included.

## Syntax

```
VAL(<string expression>)
```

One argument, always.

## Details

- **Integers, fractions and exponents**: `VAL("-12")` is −12, `VAL("1.5")` is
  1.5, `VAL(".5")` is .5, `VAL("1E3")` and `VAL("1D3")` are 1000, and
  `VAL("1E-3")` is 1E-03. Numbers past 32767 are kept: `VAL("40000")` is
  40000.
- **It stops at the first character it cannot use** and keeps what it had:
  `VAL("12ABC")` is 12, `VAL("1.2.3")` is 1.2, `VAL("5.")` is 5 and
  `VAL("1E")` is 1.
- **No number at the start is 0**: `VAL("")`, `VAL("ABC")`.
- **Spaces are skipped everywhere inside a number**, not only in front:
  `VAL("1 2")` is 12, `VAL(" - 12")` is −12, `VAL("1 . 5")` is 1.5 and
  `VAL("1 E 3")` is 1000. Forty spaces between two digits still give 12.
- **`&H`, `&O` and `&B` read hexadecimal, octal and binary**, in either case:
  `VAL("&HFF")` and `VAL("&hff")` are 255, `VAL("&O17")` is 15,
  `VAL("&B101")` is 5. The result is a signed 16-bit number, so
  `VAL("&HFFFF")` is −1. A prefix with no valid digit after it
  (`VAL("&HZZ")`, `VAL("&O9")`) is 0, and a minus sign in front of a prefix
  does not apply: `VAL("-&H10")` is 0.
- **So `VAL` does raise, in three cases:**

| you write | you get |
|---|---|
| `VAL("1E99")`, `VAL("1D99")` | error 6, `Overflow` |
| `VAL("&H1FFFF")`, `VAL("&HFFFFF")` | error 6, `Overflow` |
| `VAL("&")`, `VAL("&17")` — `&` without `H`, `O` or `B` | error 2, `Syntax error` |
| `VAL(5)` | error 13, `Type mismatch` |
| `VAL()`, `VAL("1","2")`, a bare `VAL` | error 2, `Syntax error` |

The errors were measured per form on both machines and are the same:
{2, 13} for the plain call, 6 for an exponent or a prefix that overflows, 2
for an extra argument.

## Example

```
10 PRINT VAL("12");VAL("-1.5")
20 PRINT VAL("1E3");VAL(".5")
30 PRINT VAL("&HFF");VAL("&B101")
40 PRINT VAL("12ABC");VAL("")
50 PRINT VAL("1 2");VAL("40000")
60 ON ERROR GOTO 90
70 PRINT VAL("&")
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
 12 -1.5
 1000  .5
 255  5
 12  0
 12  40000
Error 2
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_val.out`](../../scratchpad/kwdoc_val.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `VAL` changes free memory by
the same amount on both machines, but the set of work-area cells written
differs ([`kwram_full.out`](../../scratchpad/kwram_full.out)). Nothing a
program can observe through `FRE` differs. No keyword has this rung yet.

## What we found, and how

- **`VAL` read only whole decimal numbers**, and the tests had a single row
  for it. Measuring 40 shapes on 2026-08-29 (D-VAL) found 20 that differed:
  fractions, exponents, spaces inside a number and `&H`/`&O`/`&B` all read
  wrong, and `VAL("&")` gave 0 instead of an error. Because `VAL` returns 0
  on junk instead of complaining, every one of these was a silent wrong
  answer: [spec-basic-val.md](../spec-basic-val.md).
- **The prefixes came first** (fixed 2026-08-30, D-VALBASE). All nine edge
  cases — the signed 16-bit result, the overflow, a prefix with no digit, `&`
  alone, a minus in front — were measured on both references before any code
  was written: [spec-basic-valbase.md](../spec-basic-valbase.md).
- **Then `VAL` stopped being its own number reader** (fixed 2026-08-30,
  D-VALFLT). It now calls the scanner that reads numbers in program lines, so
  the two cannot drift apart. The old reader had also wrapped large numbers
  silently: `VAL("40000")` gave −25536:
  [spec-basic-valflt.md](../spec-basic-valflt.md).
- **`VAL(5)` said `Syntax error`** where the reference says `Type mismatch`
  (fixed 2026-07-17, with `LEN` and `ASC`, which share the code); and since
  2026-08-29 (D-STRTM) a numeric argument that fails on its own reports its
  own error: [spec-basic-strtm.md](../spec-basic-strtm.md).

## Where it lives

`ev_ff_val` in [basic/str-engine.asm](../../basic/str-engine.asm) reads the
argument and turns the answer into a number or an error. The parse runs in
the sub-ROM: `sh_val_parse` in [sub/strheap.asm](../../sub/strheap.asm)
handles the `&` prefixes itself and hands everything else to `tk_float` in
[sub/tkfloat.asm](../../sub/tkfloat.asm), the tokeniser's own number scanner.

## Tests that cover it

- `make kwsweep` — one row per form: `VAL("-12")`, `VAL("1.5")`, `VAL("1E3")`,
  `VAL("&HFF")` and `VAL("12ABC")`, each reading a value no other form
  produces, plus the error rows.
- `make string-acceptance` — `VAL("34")+1` among the core string verbs.
- `make kwram` — the RAM-usage comparison.
- The full 97-row comparison is
  [`scratchpad/val_probe.py`](../../scratchpad/val_probe.py), which no `make`
  target runs.
