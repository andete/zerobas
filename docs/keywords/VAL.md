<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `VAL` — the number at the start of a string

> **Spec:** DRAFT 1 (2026-11-24) — 230 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`knum.py`](../../probes/basic/spec/knum.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
> Goldfish pass 1 (test writer) 2026-11-24: 13 findings, 7 measured, 1 moved to open.
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓ for the plain call; five
> divergences found on 2026-11-24 by the spec probe, two of them an error where the
> reference returns a value (TAB / LF in or before a number, a gap after `&`, a digit
> count past 191, a zero that keeps its digits, `"-32768%"`): see Differences.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`VAL(a$)` reads a number from the start of `a$` the way BASIC reads a number
typed in a program line: signs, decimals, exponents and `&H`/`&O`/`&B`
prefixes included. It stops at the first character it cannot use, and a string
with no number at the start is 0, not an error. It is the inverse of
[`STR$`](STR$.md). zerobas behaves like the Philips VG-8020 in every case we
have measured except five rare shapes: a TAB or line feed in or before the
number, a gap between `&` and its letter, a digit count that wraps the exponent,
the bytes of a number too small to keep, and `"-32768%"` (see Differences).

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
  `VAL("1 E 3")` is 1000. Forty spaces between two digits still give 12. On
  the VG-8020 TAB (`CHR$(9)`) and line feed (`CHR$(10)`) are skipped the same
  way; zerobas stops at them (see Differences). Other control characters are
  not skipped: `VAL(CHR$(13)+"12")` is 0.
- **Spaces, TAB and LF before `&` are skipped too**: `VAL(CHR$(9)+"&HFF")` is
  255 on the VG-8020 (0 on zerobas, see Differences).
- **14 significant digits are kept, rounded half up at the 15th**:
  `VAL("123456789012345")` is 1.2345678901235E+14 and
  `VAL("-123456789012345")` its negative; a 16th digit plays no part
  (`VAL("1234567890123449")` is 1.2345678901234E+15). Seven or more digits stay
  double precision even with an `E` exponent (`VAL("1.23456789E3")` is
  1234.56789).
- **A type mark ends the number**: `!` rounds it to 6 digits, half up
  (`VAL("1234567!")` and `VAL("1234565!")` are 1234570), `#` changes nothing,
  `%` cuts it toward zero to a whole number and then checks -32768..32767
  (`VAL("1.5%")` is 1, `VAL("-1.5%")` −1, `VAL("-32768.5%")` −32768 on the
  VG-8020 and `Overflow` on zerobas, `VAL("32768%")` and `VAL("40000%")` are
  `Overflow`).
- **`&H`, `&O` and `&B` read hexadecimal, octal and binary**, in either case
  (on the VG-8020 a space, TAB or LF may come between `&` and the letter:
  `VAL("& H10")` is 16 there, a `Syntax error` here; never after the letter:
  `VAL("&H 10")` is 0 on both):
  `VAL("&HFF")` and `VAL("&hff")` are 255, `VAL("&O17")` is 15,
  `VAL("&B101")` is 5. The result is a signed 16-bit number, so
  `VAL("&HFFFF")` is −1. A prefix with no valid digit after it
  (`VAL("&HZZ")`, `VAL("&O9")`) is 0, and a minus sign in front of a prefix
  does not apply: `VAL("-&H10")` is 0.
- **So `VAL` does raise errors, in these shapes:**

| you write | you get |
|---|---|
| `VAL("1E99")`, `VAL("1D99")` | error 6, `Overflow` |
| `VAL("1E-66")`, `VAL("1E300")`, 64 to 191 digits | error 6, `Overflow` (the exponent leaves its 8 bits) |
| `VAL("32768%")`, `VAL("-32769%")` | error 6, `Overflow` (`"-32768%"` too on zerobas) |
| `VAL("1E-65")` | 0 |
| `VAL("&H1FFFF")`, `VAL("&HFFFFF")` | error 6, `Overflow` |
| `VAL("&")`, `VAL("&17")`, `VAL("& ")` — `&` without `H`, `O` or `B` | error 2, `Syntax error` (`"& H10"` too on zerobas) |
| `VAL(5)` | error 13, `Type mismatch` |
| `VAL()`, `VAL("1","2")`, a bare `VAL` | error 2, `Syntax error` |
| `VAL(MID$(S$,0))` | error 5, the argument's own error |

On the VG-8020 the errors are: {2, 13} for the call's form (2 for no, an extra
or an unclosed argument), 6 for an exponent, a `%` value or a prefix that
overflows, 2 for `&` without its letter, and an argument's own error (11, 5).
zerobas raises the same, and two more where the reference returns a value:
error 2 for a gap between `&` and its letter (KNM VL 84, 164-168), error 6 for
192, 193, 200 and 255 digits and for `"-32768%"` / `"-32768.5%"` (KNM VL 148, 175, 185,
186, 189, 192); see Differences.

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

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/val_rules.py`](../../probes/basic/spec/val_rules.py), model in
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
- **[KNM VL *i*]**: `R=VAL(S$)` with `S$` the *i*-th string of `VL_SRC` in the probe (205 of them; 183-204 added by goldfish pass 1), built byte by byte in string space: empty and blank strings, signs, points, exponents in `E` `D` `e` `d`, junk after the number, spaces / TAB / LF / other control characters before and inside it, every `&` form (either case, no digit, a wrong letter, a gap, 16 bits and one more), the type marks `%` `!` `#`, 6 / 7 / 14 / 15 / 16 digits with rounding at the half, the ends of the exponent range and digit counts of 63 to 255 (130, 191, 192 and 193 among them), three-digit `E` exponents, `%` at ±32768. The byte that follows `S$` in memory is recorded too: building a string leaves its own shorter prefix behind it (`"12"` is followed by `"1"`), so a `VAL` that read past its end would be seen.
- **[KNM FX *i*]**: a fixed statement, `S$` = `"12345"`, `T$` = `"6.5"` (both in string space); the list, with what
  each one separates, is `FX` in the probe (KNM FX 94, `VAL(MID$(S$,0))`, added by goldfish pass 1).

**Controls** ([`knum_controls.py`](../../probes/basic/spec/knum_controls.py)): zerobas's own rules, run over the reference's cases, are FALSE there: only spaces skipped on 11 of the 205 matrix cases, nothing allowed between `&` and its letter on 6, no wrap of the digit count on 4, `%` an overflow from a magnitude of 32768 on 2. An exponent of 0 always a clean zero is FALSE on 6 (KNM VL 103, 107, 178-180, 185) -- not zerobas's rule as such: zerobas keeps the digits of `"1D-65"` (KNM VL 107) and clears them after `E` and after a point. The `E` exponent wrapping inside the 8 bits as the digit count does is FALSE on 3 (KNM VL 202-204). Rounding half to even at the 15th digit (or the 7th for `!`) is FALSE on 4, truncation on 8, a 16th guard digit rounded twice on 1 (KNM VL 200), half toward +infinity on 1 (KNM VL 201), `%`'s range tested before truncation on 1 (KNM VL 192), 6 digits (a single) after an `E` exponent on 8. Reading on into the byte after `a$` is FALSE on all 67 cases where it would change the outcome (R-VAL-END); `VAL`'s own error 13 for a bad string argument on KNM FX 94.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/val_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/val_rules.py --write` -->

**15 rules; 15 hold on the reference. Of the 1610 recorded outputs (each case's error, the string result's length, first 24 bytes and byte sum, the numeric result's 8 bytes, the source string's length and sum): 1610 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. VAL(a$)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-VAL-NUMBER** A string that starts with a decimal number: an optional + or -, digits, an optional point and more digits, an optional exponent (E, D, e or d, an optional sign, digits). The value keeps 14 significant digits, rounded once, the magnitude half up at the 15th ("123456789012345" is 1.2345678901235E+14, "-123456789012345" -1.2345678901235E+14, "999999999999995" 1E+15, "12345678901234.5" 12345678901235); a 16th digit plays no part ("1234567890123449" is 1.2345678901234E+15); 7 to 14 digits are kept even with an E exponent ("1.23456789E3" is 1234.56789). Leading zeros do not count. | 56 | ✓ | ✓ |
| **R-VAL-SPACE** Spaces, TAB (CHR$(9)) and LF (CHR$(10)) are skipped everywhere in a decimal number: before it, between the sign and the digits, between digits, around the point, inside the exponent ("1 2" and "1"+CHR$(9)+"2" are 12, " - 12" is -12, "1E- 3" .001; 254 spaces then 7 is 7). | 17 | ✓ | ✗ 7: KNM VL 45, KNM VL 46, KNM VL 47, KNM VL 160, KNM VL 161, KNM VL 162 … (+1) |
| **R-VAL-STOP** The number ends at the first character that cannot continue it, and what was read so far is the value: "12ABC" 12, "1.2.3" 1.2, "1,000" 1, "2+3" 2, "1E3E3" 1000, "1.5E1.5" 15, "1E" and "1E+" 1, "1"+CHR$(0)+"2" 1, "1"+CHR$(255)+"2" 1. | 11 | ✓ | ✓ |
| **R-VAL-NONE** No number at the start is 0, not an error: "", spaces only, "ABC", ".", "-", "+", "E3", ".E3", "$12", and a second sign ("--1", "+-1", "-+1"). Zero is stored as 8 zero bytes, "-0" included. Control characters other than TAB and LF are not skipped: CR, CHR$(0), CHR$(11), CHR$(12), CHR$(28), CHR$(31), CHR$(127) and CHR$(160) before the digits give 0. | 23 | ✓ | ✓ |
| **R-VAL-SUFFIX** A type mark after the digits or the exponent ends the number and sets its precision: ! rounds to 6 digits, half up ("1234567!" is 1234570, "1234565!" 1234570, "1234575!" 1234580), # changes nothing, % cuts the value toward zero to a whole number and THEN tests -32768..32767 ("1.5%" 1, "-1.5%" -1, "32767.9%" 32767, "-32768%" and "-32768.5%" -32768; "32768%", "-32769%" and "40000%" error 6, Overflow). Nothing after the mark is read ("12%3" is 12, "1.5!E3" 1.5). | 21 | ✓ | ✗ 2: KNM VL 189, KNM VL 192 |
| **R-VAL-RANGE** The exponent byte is 64 + E for .d1d2... x 10^E. The part of E that the digits and the point make is counted in 8 bits: 64 to 191 digits give 128 to 255, error 6 (Overflow); 192 ones give exactly 0, 193 ones 1.1111111111111E-63, 200 ones 1.1111111111111E-57, 255 ones .011111111111111 (the count wrapped past 255); a point followed by 70 zeros wraps below 0 to 250, Overflow. An E (or D) exponent is added to that WITHOUT wrapping: past 127 or below 0 is Overflow ("1E63", "1E99", "1E300", "1E-66", "1E-194", "1E-200"). From 1 to 127 the number is in range; at exactly 0 ("1E-65", "5E-65", 192 ones, a point, 64 zeros and a 1) the value is 0 but its digits stay in the mantissa bytes (00 10 00 ... for "1E-65"). | 25 | ✓ | ✗ 8: KNM VL 103, KNM VL 148, KNM VL 175, KNM VL 178, KNM VL 179, KNM VL 180 … (+2) |
| **R-VAL-PREFIX** &H, &O and &B (either case; spaces, TABs and LFs are skipped before & -- CHR$(9)+"&HFF" is 255 -- and between & and the letter, never after it) read hexadecimal, octal or binary digits up to the first that does not belong; the value is a 16-bit pattern taken as signed ("&HFFFF" is -1, "&H8000" -32768, "&H0000FFFF" -1); a pattern past 16 bits is error 6 (Overflow); no digit is 0 ("&HZZ", "&O9", "&H 10"); & followed by any other letter, a digit, nothing, or only spaces / TABs ("& ") is error 2 (Syntax error). A sign before & is not a number ("-&H10" is 0). | 52 | ✓ | ✗ 8: KNM VL 84, KNM VL 164, KNM VL 165, KNM VL 166, KNM VL 167, KNM VL 168 … (+2) |
| **R-VAL-END** VAL reads its own string only: in every case where reading on into the byte that follows a$ in memory would give another outcome, the outcome is NOT that one (whatever the other rules say about it). | 67 | ✓ | ✓ |
| **R-VAL-TYPE** A number as the argument is error 13 (Type mismatch), and so is assigning the result to a string variable: the result is a number. | 2 | ✓ | ✓ |
| **R-VAL-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-VAL-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error). | 4 | ✓ | ✓ |
| **R-VAL-FORMS** Spaces before the parenthesis, after it and before the closing parenthesis are allowed; the argument may be a literal in the program text, a LEFT$ / MID$ / RIGHT$ of a longer string (VAL(LEFT$("12345",2)) is 12: the rest of the longer string is not read) or a concatenation ("12345"+"6.5" is 123456.5, "6.5"+"12345" 6.512345). | 15 | ✓ | ✓ |
| **R-VAL-KEEP** The string variable S$ is left as it was, in every case, error or not (read back after every case). | 230 | ✓ | ✓ |
| **R-VAL-ARGERR** An error inside a string argument is that error, not VAL's own: VAL(MID$(S$,0)) is error 5. | 1 | ✓ | ✓ |
| **R-VAL-LITERAL** Inside a literal string the rules are the same: VAL("1E99") is error 6, VAL("&") error 2. | 2 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

- **TAB and line feed in or before a number** (rules R-VAL-SPACE and R-VAL-PREFIX, cases KNM VL 45, 46, 47, 160,
  161, 162, 163, 196, 197; [D-VALWS](../../todo/open/D-VALWS.md)). The VG-8020 skips `CHR$(9)` and `CHR$(10)`
  wherever it skips a space; zerobas stops there: `VAL(CHR$(9)+"12")` is 12 there and 0 here,
  `VAL("1"+CHR$(9)+"2")` 12 and 1, `VAL("1E"+CHR$(9)+"3")` 1000 and 1, `VAL("-"+CHR$(9)+"12")` −12 and 0,
  `VAL(CHR$(9)+"&HFF")` 255 and 0.
- **A gap between `&` and its letter** (rule R-VAL-PREFIX, cases KNM VL 84, 164-168;
  [D-VALWS](../../todo/open/D-VALWS.md)). `VAL("& H10")`, `VAL("&  H10")`, `VAL("& O17")`, `VAL("& B101")` and
  the TAB and LF forms are 16, 15 or 5 on the VG-8020 and `Syntax error` (error 2) here.
- **A digit count that wraps the exponent** (rule R-VAL-RANGE, cases KNM VL 148, 175, 185, 186;
  [D-VALEXP](../../todo/open/D-VALEXP.md)). The reference counts the digits' exponent in 8 bits, so 192 ones are a
  zero with its digits kept, 193 ones 1.1111111111111E-63, 200 ones 1.1111111111111E-57 and 255 ones
  .011111111111111 there; zerobas raises `Overflow`. 64 to 191 digits are `Overflow` on both, and so is an `E`
  exponent that leaves the range (`"1E-194"`, `"1E300"`): the reference does not wrap that part.
- **An exponent that lands exactly on 0** (rule R-VAL-RANGE, cases KNM VL 103, 178, 179, 180 -- and 185 above;
  [D-VALEXP](../../todo/open/D-VALEXP.md)). `VAL("1E-65")` is 0 on both machines, but the reference leaves the
  digits in the variable's mantissa bytes (`00 10 00 00 ...`) where zerobas stores eight zero bytes; `"1D-65"`
  agrees. `READ` behaves the same way (the argument of case KNM SN S 1E-65: `00 10 00 00` on the reference, four
  zeros here). Only `VARPTR` / `PEEK` (or `MKD$`) can see it; `STR$` of either is `" 0"`.
- **`"-32768%"`** (rule R-VAL-SUFFIX, cases KNM VL 189, 192; [D-VALPCT](../../todo/open/D-VALPCT.md)).
  `VAL("-32768%")` and `VAL("-32768.5%")` are −32768 on the VG-8020 and `Overflow` (error 6) here: zerobas
  tests `%`'s range on the magnitude. Every other `%` case agrees (`"32768%"`, `"-32769%"`, `"32767.9%"`,
  `"-1.5%"`).
- **R-VAL-END** (VAL reads its own string only) holds on zerobas in every case: none of the differences above is a
  read past the end of `a$`.

The one rung not yet proven is **RAM usage**: `VAL` changes free memory by
the same amount on both machines, but the set of work-area cells written
differs ([`kwram_full.out`](../../scratchpad/kwram_full.out)). Nothing a
program can observe through `FRE` differs. No keyword has this rung yet.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] An argument's own error was measured with two kinds (`1/0`, error 11; `MID$(S$,0)`, error 5); that any error of the argument wins is assumed.
- [A] Which work-area cells the call writes (the RAM-usage rung, [`kwram_full.out`](../../scratchpad/kwram_full.out)).
- [A] A type mark after a space (`VAL("1 %")`).
- [A] An `E` exponent with a digit count past 63 (`"1"` x 100 + `"E-99"`): whether the `E` part is added to the
  wrapped 8-bit digit exponent (1.1111111111111E+0 under the page's model) or the digit count overflows first.
  Separates two rules the measured cases cannot tell apart.
- [A] The result's numeric TYPE: it is assigned to a double variable, so whether a short number comes back as an integer or a single is not seen; only its value and digits are.
- [A] A negative number whose exponent lands at 0 (`VAL("-1E-65")`): the sign bit in that zero is not measured.

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

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make kwsweep` — one row per form: `VAL("-12")`, `VAL("1.5")`, `VAL("1E3")`,
  `VAL("&HFF")` and `VAL("12ABC")`, each reading a value no other form
  produces, plus the error rows.
- `make string-acceptance` — `VAL("34")+1` among the core string verbs.
- `make kwram` — the RAM-usage comparison.
- The full 97-row comparison is
  [`scratchpad/val_probe.py`](../../scratchpad/val_probe.py), which no `make`
  target runs.
