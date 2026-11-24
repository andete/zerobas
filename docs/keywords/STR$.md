<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `STR$` — a number as text

> **Spec:** DRAFT 1 (2026-11-24) — 142 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`knum.py`](../../probes/basic/spec/knum.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence: the
> spec probe (2026-11-24) found zerobas agreeing in every case.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`STR$(n)` returns the text `PRINT` would show for `n`, without the space
`PRINT` puts after a number. Its inverse is [`VAL`](VAL.md):
`VAL(STR$(1.5))` is 1.5. zerobas behaves exactly like the Philips VG-8020 for
every case we have measured, errors included.

## Syntax

```
STR$(<numeric expression>)
```

One argument, always.

## Details

- **A non-negative number keeps its leading space**; a negative one starts
  with `-`. So `STR$(5)` is `" 5"` (two characters) and `STR$(-34)` is
  `"-34"`.
- **There is no trailing space.** `PRINT` adds one after every number;
  `STR$` does not.
- **Fractions and large numbers are written the way `PRINT` writes them**:
  `STR$(1.5)` is `" 1.5"` and `STR$(1E9)` is `" 1000000000"`; `STR$(.5)` and
  `STR$(1E-5)` read `.5` and `1E-05`.
- **In full from .01 up to (not including) 10^14, in exponent form outside
  that**, in single and double precision alike: `STR$(1E13)` is
  `" 10000000000000"` even for a single, `STR$(.01)` is `" .01"`, but
  `STR$(.001)` is `" 1E-03"` and `STR$(1E14)` is `" 1E+14"`. The exponent
  letter is `E` for a double too, always with a sign and two digits.
- **Every stored digit is written**, and no more: up to 6 for a single, 14
  for a double (`STR$(1#/3)` is `" .33333333333333"`).
- **A string argument** (`STR$("A")`) is `Type mismatch` (error 13).
- **No argument, or two** (`STR$()`, `STR$(1,1)`), is `Syntax error`
  (error 2).

| you write | you get |
|---|---|
| `STR$(5)` | `" 5"` |
| `STR$(-34)` | `"-34"` |
| `STR$(1.5)` | `" 1.5"` (length 4) |
| `STR$(0)` | `" 0"` (length 2) |
| `STR$(1E9)` | `" 1000000000"` (length 11) |
| `STR$(.001)`, `STR$(1E14)` | `" 1E-03"`, `" 1E+14"` |
| `STR$("A")` | error 13, `Type mismatch` |
| `STR$()`, `STR$(1,1)` | error 2, `Syntax error` |

The whole set of errors `STR$` can raise is {2, 13}, the same on both
machines.

## Example

```
10 PRINT "<";STR$(5);">"
20 PRINT "<";STR$(-34);">"
30 PRINT "<";STR$(1.5);">"
40 PRINT LEN(STR$(0));LEN(STR$(1E9))
50 PRINT VAL(STR$(1.5))+1
60 ON ERROR GOTO 90
70 PRINT STR$("A")
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
< 5>
<-34>
< 1.5>
 2  11
 2.5
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_str_s.out`](../../scratchpad/kwdoc_str_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/str_s_rules.py`](../../probes/basic/spec/str_s_rules.py), model in
[`knum_model.py`](../../probes/basic/spec/knum_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/knum.py`](../../probes/basic/spec/knum.py) (the strings region's
third, on the shared RAM-record harness [`ramrec.py`](../../probes/basic/spec/ramrec.py)), typed on both
machines; run file [`scratchpad/KNM_run1.out`](../../scratchpad/KNM_run1.out) (2026-11-24; zerobas's side on that
day's build). Before every case the string result variable `R$` holds `CHR$(250)` and the numeric one `R` holds
-12345, so an error, which assigns nothing, cannot read as a result, and a result written to the wrong kind of
variable is seen. A string result is read through `VARPTR` and `PEEK`, never through a string function: its length,
its first 24 bytes and the sum of all its bytes; a numeric result as its variable's own 8 bytes (a double), compared
byte for byte. A numeric argument is `READ` into a variable of the case's own type (`N%`, `N!` or `N#`) and that
variable's own bytes are recorded before the call: the rules work from the exact value the function was given, not
from the `DATA` text.
- **[KNM SN *t* *n*]**: `R$=STR$(N%)`, `STR$(N!)` or `STR$(N#)` for *t* = I, S, D, with *n* the `DATA` text. Integers: 0, 1, -1, 5, -34, 9, 10, 99, 100, 255, 32767, -32767, -32768. Singles: 0, 1, -1, .5, -.5, 1.5, -1.5, 10, 100, 1000, 10000, 32767, 32768, 65535, 99999, 100000, 999999, 1000000, 1100000, 1200000, 1234567, 123456, 12345.6, 1234.56, .123456, .0123456, .00123456, .1, .01, .02, .012, .001, .0012, .0001, 1E-5, 1.5E-5, -1E-5, -.01, -.001, 1E-10, 1E5, 1E6, 1E7, -1E6, -999999, 1E10, 1.5E10, 1E37, 1E62, 9.99999E62, 1E-62, 1E-63, 1E-64, 1E-65, 1E13, 1E14, 1.5E13, 1.23456E13, 1.23456E14, -1E13, -1E14, .0099, .00999999, 99999.9. Doubles: 0, 1, -1, .5, 1.5, -1.5, 32768, -32769, 1234567, 1234567.8, 1E6, 1E7, 12345678901234, 99999999999999, 100000000000000, 123456789012345, 1E13, 1E14, 1E15, 1E16, -12345678901234, .1, .01, .001, .0012345678901234, .012345678901234, .12345678901234, .33333333333333, 1.2345678901234, 1D-5, -1D-5, 1D-10, 1D62, 1D-64, 9.9999999999999D62, 123456.7, 1234567890.12, 1.5D13, 1.2345678901234D13, .0099, 1D-2, 9.9999999999999D-3, 12345678901.234, -1D14. Both sides of the full / exponent boundary at .01 and 10^14 in both types, 6 and 14 significant digits, a stored digit count below the type's, and the ends of the exponent range.
- **[KNM FX *i*]**: a fixed statement, `S$` = `"12345"`, `T$` = `"6.5"` (both in string space); the list, with what
  each one separates, is `FX` in the probe.

**Controls** ([`knum_controls.py`](../../probes/basic/spec/knum_controls.py)): PRINT's trailing space kept is FALSE on all 121 matrix cases; no leading space for a non-negative number on 101; numbers written in full only up to a single's 6 digits on 25; written in full down to .001 on 10; `D` as a double's exponent letter on 16 of the 44 doubles.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/str_s_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/str_s_rules.py --write` -->

**9 rules; 9 hold on the reference. Of the 994 recorded outputs (each case's error, the string result's length, first 24 bytes and byte sum, the numeric result's 8 bytes, the source string's length and sum): 994 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. STR$(n)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-STR-INT** An integer (a % variable) is written as its decimal digits, with "-" in front of a negative number and a space in front of any other; nothing after the last digit (0, 9, 10, 32767, -32768). | 13 | ✓ | ✓ |
| **R-STR-FIXED** A single or double n = .d1d2...dk x 10^E (k its significant digits, trailing zeros dropped) with E from -1 to 14 is written in full: a space or "-", then the digits with the decimal point in place -- zeros added up to the point when the number is whole (1E13! is " 10000000000000", 14 digits, though a single holds 6), no 0 before a leading point (" .5", " .0123456"), no point after a whole number. Every stored digit is written: 6 at most for a single, 14 for a double. | 69 | ✓ | ✓ |
| **R-STR-EXP** Outside that range (n below .01 or 10^14 and up, in size) it is written d1.d2...dkE+xx or E-xx: one digit before the point, the point only when more digits follow, then E -- for a double too, never D -- a sign and two digits (" 1E-03", " 1.23456E-03", " 1E+14", " 9.9999999999999E+62", " 1E-64"). | 36 | ✓ | ✓ |
| **R-STR-ZERO** Zero is " 0" in every type -- also a single whose exponent byte is 0 but whose digit bytes are not (READ left 1E-65 that way on the reference: KNM SN S 1E-65). | 3 | ✓ | ✓ |
| **R-STR-TYPE** A string as the argument is error 13 (Type mismatch), and so is assigning the result to a numeric variable: the result is a string. | 3 | ✓ | ✓ |
| **R-STR-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-STR-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error). | 4 | ✓ | ✓ |
| **R-STR-FORMS** Spaces before the parenthesis, after it and before the closing parenthesis are allowed; &HFF is " 255" and &HFFFF "-1" (a hex literal is a signed integer); -0 is " 0"; 1/4 is " .25"; the result is an ordinary string (STR$(5)+"X" is " 5X"). | 13 | ✓ | ✓ |
| **R-STR-KEEP** The string variable S$ is left as it was, in every case, error or not (read back after every case). | 142 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `STR$` changes free memory by
the same amount on both machines, but the set of work-area cells written
differs ([`kwram_full.out`](../../scratchpad/kwram_full.out)). Nothing a
program can observe through `FRE` differs. No keyword has this rung yet.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] An argument's own error was measured with one kind (`1/0`, error 11); that any error of the argument wins is assumed.
- [A] Which work-area cells the call writes (the RAM-usage rung, [`kwram_full.out`](../../scratchpad/kwram_full.out)).
- [A] Negative zero and other non-canonical bytes in a double argument (one single with an exponent byte of 0 and digit bytes, from READ, is measured).
- [A] Whether STR$ of a single ever writes a 7th digit: every single measured holds at most 6 stored digits.

## What we found, and how

- **`STR$` handled only whole numbers** (fixed 2026-08-30, D-STRFLT). Any
  other number was silently cut to an integer: `STR$(1.5)` gave 1, and
  `STR$(.5)` and `STR$(1E9)` gave 0. `PRINT`'s own number formatter was
  already right, so the fix was to reuse it rather than write a second one:
  [spec-basic-strflt.md](../spec-basic-strflt.md). The gap had been found the
  day before by D-VAL, which measured `VAL` and `STR$` together:
  [spec-basic-val.md](../spec-basic-val.md).
- **The trailing space was invisible to the tests.** The usual test prints
  `"[";STR$(x);"]"` and the screen reader strips spaces, so `" 1.5"` and
  `"1.5 "` look the same there. The rule is pinned two other ways: a fence
  (`"<"+STR$(1.5)+">"` must read `< 1.5>`) and the length (4, 2 and 11 for
  `1.5`, `0` and `1E9`). A deliberately broken build that kept `PRINT`'s
  trailing space moved exactly those rows and no others.

## Where it lives

`str_fn_str` in [basic/str-engine.asm](../../basic/str-engine.asm). A whole
number is formatted by `pu_fmt_int` in
[basic/printusing.asm](../../basic/printusing.asm); any other number by
`flt_fmt` in [basic/float.asm](../../basic/float.asm), the formatter `PRINT`
uses.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make string-acceptance` — `STR$(42)`, `STR$(-3)` and `STR$` inside
  concatenations.
- `make kwsweep` — the everyday row and the error rows for {2, 13}.
- `make kwram` — the RAM-usage comparison.
- The fraction, size and space rows are in
  [`scratchpad/strflt_probe.py`](../../scratchpad/strflt_probe.py), which no
  `make` target runs.
