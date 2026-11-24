<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `BIN$` — a number written in binary

> **Spec:** DRAFT 1 (2026-11-24) — 86 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`knum.py`](../../probes/basic/spec/knum.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
> Goldfish pass 1 (test writer) 2026-11-24: 8 findings, 6 measured, 1 moved to open.
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence: the
> spec probe (2026-11-24) found zerobas agreeing in every case.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`BIN$(n)` returns the binary digits of `n` as a string: `BIN$(5)` is `"101"`.
It is the base-2 member of a family with [`HEX$`](HEX$.md) and
[`OCT$`](OCT$.md), and all three follow the same rules. zerobas behaves exactly
like the Philips VG-8020 for every case we have measured, errors included.

## Syntax

```
BIN$(<numeric expression>)
```

One argument, always.

## Details

- **The number is read as an unsigned 16-bit value.** Anything from −32768 to
  65535 is accepted; a negative number shows its two's-complement pattern, so
  `BIN$(-1)` and `BIN$(65535)` are the same string, sixteen `1`s.
- **No leading zeros, at least one digit.** `BIN$(0)` is `"0"`, `BIN$(2)` is
  `"10"`, and the longest result is 16 characters.
- **A fraction is truncated toward zero** below 32768: `BIN$(5.7)` is `"101"`,
  and `BIN$(-5.7)` is the pattern for −5. **From 32768 up the number is first
  taken as n − 65536, and then truncated**, so a fraction there moves UP:
  `BIN$(32768.5)` is `"1000000000000001"` and `BIN$(65535.5)` is `"0"` — not an
  error.
- **The result is an ordinary string**: it can be concatenated
  (`"<"+BIN$(5)+">"` is `<101>`) and assigned like any other.
- **`BIN` without the `$` is not this function** — it is an ordinary array
  name, as on the reference.

| you write | you get |
|---|---|
| `BIN$(5)` | `"101"` |
| `BIN$(0)` | `"0"` |
| `BIN$(255)` | `"11111111"` |
| `BIN$(-1)`, `BIN$(65535)` | `"1111111111111111"` |
| `BIN$(-32768)`, `BIN$(32768)` | `"1000000000000000"` |
| `BIN$(32768.5)`, `BIN$(65535.5)` | `"1000000000000001"`, `"0"` |
| `BIN$(65536)`, `BIN$(-32769)` | error 6, `Overflow` |
| `BIN$("A")` | error 13, `Type mismatch` |
| `BIN$`, `BIN$()`, `BIN$(1,1)` | error 2, `Syntax error` |
| `BIN$(255)` with string space full | error 14, `Out of string space` |

The errors measured are {2, 6, 13, 14}, plus the argument's own
(`BIN$(1/0)`: 11), the same on both machines.

## Example

```
10 PRINT BIN$(5);" ";BIN$(0)
20 PRINT BIN$(255)
30 PRINT BIN$(-1)
40 PRINT LEN(BIN$(256));BIN$(5.7)
50 ON ERROR GOTO 80
60 PRINT BIN$(65536)
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
101 0
11111111
1111111111111111
 9 101
Error 6
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_bin_s.out`](../../scratchpad/kwdoc_bin_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/bin_s_rules.py`](../../probes/basic/spec/bin_s_rules.py), model in
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
- **[KNM RX *fn* *t* *n*]**: `R$=fn(N%)`, `fn(N!)` or `fn(N#)` for *t* = I, S, D, with *n* the `DATA` text. Integers: -32768, -32767, -1, 0, 1, 255, 256, 32767, 2, 5, 511. Singles: -32769, -32768.5, -.9, 1.5, -1.5, 32767.9, 65535.9, 65536, -32768.9, 32768.5, 65534.5, 65535.5. Doubles: -1E10, -70000, -65536, -32769, -32768.5, -32768, -32767.9, -32767, -5.7, -1.5, -1, -.9, -.5, -.1, 0, .1, .5, .9, 1, 1.5, 2.5, 5.7, 7, 8, 15, 16, 255, 256, 4095, 4096, 32767, 32767.5, 32767.9, 32768, 32768.5, 40000, 65534.5, 65535, 65535.5, 65535.9, 65536, 70000, 1E10, -32768.9. The values sit on both sides of every boundary a rival rule would put elsewhere: truncation vs rounding vs `INT` (-.9, -.5, .5, 2.5), the range test before vs after truncation (-32768.5, -32768.9), and the fractions above 32767 (32767.5, 32768.5, 65534.5, 65535.5, 65535.9).
- **[KNM FX *i*]**: a fixed statement, `S$` = `"12345"`, `T$` = `"6.5"` (both in string space); the list, with what
  each one separates, is `FX` in the probe. Added by goldfish pass 1: `BIN$(&HFFFF)`, and `BIN$(255)` after line
  400 has filled string space with `W$()` until `FRE("")` is 0, `"<"+BIN$(5)+">"` and `BIN(1)=7:R=BIN(1)`.

**Controls** ([`knum_controls.py`](../../probes/basic/spec/knum_controls.py)): the same conversion with plain truncation above 32767 as well is FALSE on 8 of the 67 matrix cases (32768.5, 65534.5, 65535.5 and 65535.9, each as a single and as a double). The call succeeding with string space full is FALSE on its one case, and `BIN(` read as `BIN$`'s keyword (a syntax error) on KNM FX 102.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/bin_s_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/bin_s_rules.py --write` -->

**11 rules; 11 hold on the reference. Of the 602 recorded outputs (each case's error, the string result's length, first 24 bytes and byte sum, the numeric result's 8 bytes, the source string's length and sum): 602 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. BIN$(n)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-BIN-LOW** From -32768 to below 32768 the number is truncated toward zero and its 16-bit pattern (two's complement for a negative number) is written in binary, without leading zeros, "0" for 0: -1 and -1.5 give sixteen 1s, -.9 and .9 give "0", 32767.9 the pattern of 32767. -32768.5 and -32768.9 are -32768 (in a single and a double): the truncation comes before the range test, and nothing rounds. | 47 | ✓ | ✓ |
| **R-BIN-HIGH** From 32768 to below 65536 the pattern is that of n - 65536, truncated toward zero -- so a fraction there moves UP: 32768.5 gives "1000000000000001", 65534.5 gives sixteen 1s, and 65535.5 and 65535.9 give "0" (65536 wrapped to 16 bits), not an error. | 11 | ✓ | ✓ |
| **R-BIN-RANGE** Error 6 (Overflow), nothing assigned, when the number truncated toward zero is below -32768 (-32769, -65536, -1E10) or the number is 65536 or more (65536, 70000, 1E10) -- in every type. | 9 | ✓ | ✓ |
| **R-BIN-TYPE** A string as the argument is error 13 (Type mismatch), and so is assigning the result to a numeric variable: the result is a string. | 3 | ✓ | ✓ |
| **R-BIN-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-BIN-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error). | 4 | ✓ | ✓ |
| **R-BIN-FORMS** Spaces before the parenthesis, around the argument and before the closing parenthesis are allowed; a hex or integer literal is a number like any other (255, &HFF and 255% give the same; &HFFFF is -1, so it gives sixteen 1s); the result is an ordinary string: "<"+BIN$(5)+">" is "<101>". | 8 | ✓ | ✓ |
| **R-BIN-KEEP** The string variable S$ is left as it was, in every case, error or not (read back after every case). | 86 | ✓ | ✓ |
| **R-BIN-LITERAL** A literal out of range is the same error 6: BIN$(70000). | 1 | ✓ | ✓ |
| **R-BIN-NOSPACE** With string space full (filled until FRE("") is 0) BIN$(255) is error 14 (Out of string space) and assigns nothing. | 1 | ✓ | ✓ |
| **R-BIN-NAME** BIN without $ is an ordinary array name: BIN(1)=7 then BIN(1) gives 7. | 1 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `BIN$` changes free memory by
the same amount on both machines, but the set of work-area cells written
differs ([`kwram_full.out`](../../scratchpad/kwram_full.out)). Nothing a
program can observe through `FRE` differs. No keyword has this rung yet.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] An argument's own error was measured with one kind (`1/0`, error 11); that any error of the argument wins is assumed.
- [A] Which work-area cells the call writes (the RAM-usage rung, [`kwram_full.out`](../../scratchpad/kwram_full.out)).
- [A] Error 16 (`String formula too complex`): one call does not reach it; a deep string expression around it is not measured.
- [A] The "n - 65536, then truncated" rule above 32767 is measured at 32767.5, 32768.5, 65534.5, 65535.5 and 65535.9 (all but 32767.5 as a single too); a double just below 65536 with more digits (65535.99999999) is not.

## What we found, and how

- **`BIN$` did not exist until 2026-07-27**, and nothing said so: `BIN$(5)`
  was read as an element of a string array named `BIN$` and quietly gave `""`.
  It was one of the last two keywords that answered wrongly without an error.
  Its whole contract was measured first on the reference, using `HEX$` and
  `OCT$` as calibration because they share its rules:
  [binfre-vg8020-characterization.md](../binfre-vg8020-characterization.md),
  [spec-basic-binfre.md](../spec-basic-binfre.md).
- **Sixteen digits did not fit the buffer its siblings use.** `HEX$` and
  `OCT$` build their digits in an 8-byte buffer; a full-width `BIN$` needs 16.
  That was measured (`LEN(BIN$(65535))` is 16 on the reference) before the
  code was written, not discovered afterwards.
- **Adding it fixed two bugs in its siblings** (same day): `HEX$("A")` printed
  `0` instead of `Type mismatch`, and `OCT$(65536)` printed `0` instead of
  `Overflow`. The three functions now share one body, so the type check and
  the range check are written once.

## Where it lives

`str_fn_bin` in [basic/str-engine.asm](../../basic/str-engine.asm) is an
entry into `str_fn_radix`, the body `HEX$` and `OCT$` share; it reads and
checks the argument. The digits are built by `sh_bin_build` in
[sub/strheap.asm](../../sub/strheap.asm), in the sub-ROM.

## Tests that cover it

- `make binfre-acceptance` — the digit patterns, sign, truncation, length and
  the error rows.
- `make kwsweep` — the everyday row and the error rows for {2, 6, 13}.
- `make kwram` — the RAM-usage comparison.
