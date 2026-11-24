<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `OCT$` — a number written in octal

> **Spec:** DRAFT 1 (2026-11-24) — 84 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`knum.py`](../../probes/basic/spec/knum.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
> Goldfish pass 1 (test writer) 2026-11-24: 6 findings, 4 measured, 1 moved to open.
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence: the
> spec probe (2026-11-24) found zerobas agreeing in every case.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`OCT$(n)` returns the octal (base-8) digits of `n` as a string: `OCT$(8)` is
`"10"`. It follows exactly the rules of [`HEX$`](HEX$.md) and
[`BIN$`](BIN$.md), in base 8. zerobas behaves exactly like the Philips
VG-8020 for every case we have measured, errors included.

## Syntax

```
OCT$(<numeric expression>)
```

One argument, always.

## Details

- **The number is read as an unsigned 16-bit value**, −32768 to 65535; a
  negative number shows its two's-complement pattern, so `OCT$(-1)` is
  `"177777"`.
- **No leading zeros, at least one digit.** `OCT$(0)` is `"0"`; the longest
  result is six characters.
- **A fraction is truncated toward zero** below 32768 (`OCT$(-1.5)` is
  `"177777"`, `OCT$(-.9)` is `"0"`). **From 32768 up the number is first taken
  as n − 65536, and then truncated**, so a fraction there moves UP:
  `OCT$(32768.5)` is `"100001"` and `OCT$(65535.5)` is `"0"` — not an error.
- **There is no `&O` in front**; add it yourself to build a literal.
- Outside −32768 to 65535 the result is `Overflow` (error 6).

| you write | you get |
|---|---|
| `OCT$(8)` | `"10"` |
| `OCT$(0)` | `"0"` |
| `OCT$(-1)` | `"177777"` |
| `OCT$(32768.5)`, `OCT$(65535.5)` | `"100001"`, `"0"` |
| `OCT$(65536)`, `OCT$(70000)`, `OCT$(-70000)` | error 6, `Overflow` |
| `OCT$("A")` | error 13, `Type mismatch` |
| `OCT$()`, `OCT$(1,1)` | error 2, `Syntax error` |
| `OCT$(255)` with string space full | error 14, `Out of string space` |

The errors measured are {2, 6, 13, 14}, plus the argument's own
(`OCT$(1/0)`: 11), the same on both machines.

## Example

```
10 PRINT OCT$(8);" ";OCT$(0)
20 PRINT OCT$(511);" ";OCT$(-1)
30 ON ERROR GOTO 60
40 PRINT OCT$(70000)
50 END
60 PRINT "Error";ERR:RESUME NEXT
RUN
10 0
777 177777
Error 6
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_oct_s.out`](../../scratchpad/kwdoc_oct_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/oct_s_rules.py`](../../probes/basic/spec/oct_s_rules.py), model in
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
  each one separates, is `FX` in the probe. Added by goldfish pass 1: `OCT$(&HFFFF)`, and `OCT$(255)` after line
  400 has filled string space with `W$()` until `FRE("")` is 0.

**Controls** ([`knum_controls.py`](../../probes/basic/spec/knum_controls.py)): the same conversion with plain truncation above 32767 as well is FALSE on 8 of the 67 matrix cases (32768.5, 65534.5, 65535.5 and 65535.9, each as a single and as a double). The call succeeding with string space full is FALSE on its one case.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/oct_s_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/oct_s_rules.py --write` -->

**10 rules; 10 hold on the reference. Of the 588 recorded outputs (each case's error, the string result's length, first 24 bytes and byte sum, the numeric result's 8 bytes, the source string's length and sum): 588 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. OCT$(n)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-OCT-LOW** From -32768 to below 32768 the number is truncated toward zero and its 16-bit pattern (two's complement for a negative number) is written in octal, without leading zeros, "0" for 0: -1 and -1.5 give "177777", -.9 and .9 give "0", 32767.9 the pattern of 32767. -32768.5 and -32768.9 are -32768 (in a single and a double): the truncation comes before the range test, and nothing rounds. | 47 | ✓ | ✓ |
| **R-OCT-HIGH** From 32768 to below 65536 the pattern is that of n - 65536, truncated toward zero -- so a fraction there moves UP: 32768.5 gives "100001", 65534.5 gives "177777", and 65535.5 and 65535.9 give "0" (65536 wrapped to 16 bits), not an error. | 11 | ✓ | ✓ |
| **R-OCT-RANGE** Error 6 (Overflow), nothing assigned, when the number truncated toward zero is below -32768 (-32769, -65536, -1E10) or the number is 65536 or more (65536, 70000, 1E10) -- in every type. | 9 | ✓ | ✓ |
| **R-OCT-TYPE** A string as the argument is error 13 (Type mismatch), and so is assigning the result to a numeric variable: the result is a string. | 3 | ✓ | ✓ |
| **R-OCT-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-OCT-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error). | 4 | ✓ | ✓ |
| **R-OCT-FORMS** Spaces before the parenthesis, around the argument and before the closing parenthesis are allowed; a hex or integer literal is a number like any other (255, &HFF and 255% give the same; &HFFFF is -1, so it gives "177777"). | 7 | ✓ | ✓ |
| **R-OCT-KEEP** The string variable S$ is left as it was, in every case, error or not (read back after every case). | 84 | ✓ | ✓ |
| **R-OCT-LITERAL** A literal out of range is the same error 6: OCT$(70000). | 1 | ✓ | ✓ |
| **R-OCT-NOSPACE** With string space full (filled until FRE("") is 0) OCT$(255) is error 14 (Out of string space) and assigns nothing. | 1 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `OCT$` changes free memory by
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

- **`OCT$` arrived on 2026-07-10** with `HEX$`, `STRING$`, `SPACE$` and
  `INSTR`: [spec-basic-string-functions.md](../spec-basic-string-functions.md).
- **`OCT$` had no range check at all** (fixed 2026-07-27). `OCT$(65536)`
  printed `0` — the number cut to 16 bits — where the VG-8020 says
  `Overflow`. `HEX$` had the check and `OCT$` simply did not: the two were
  near-copies, and the five bytes that differed were exactly the missing
  check. `OCT$("A")` also printed `0` instead of `Type mismatch`. Both were
  found while measuring `BIN$` against its siblings, and the three now share
  one body: [binfre-vg8020-characterization.md](../binfre-vg8020-characterization.md),
  [spec-basic-binfre.md](../spec-basic-binfre.md).

## Where it lives

`str_fn_oct` in [basic/str-engine.asm](../../basic/str-engine.asm) is an
entry into `str_fn_radix`, shared with `HEX$` and `BIN$`; it reads and checks
the argument. The digits are built by `sh_oct_build` in
[sub/strheap.asm](../../sub/strheap.asm), in the sub-ROM.

## Tests that cover it

- `make string-acceptance` — `OCT$` of 8, 0 and −1 against the reference.
- `make str-domain-acceptance` — −1 and the overflow edge.
- `make binfre-acceptance` — the `OCT$(65536)` and type rows.
- `make kwsweep` — the everyday row and the error rows for {2, 6, 13}.
- `make kwram` — the RAM-usage comparison.
