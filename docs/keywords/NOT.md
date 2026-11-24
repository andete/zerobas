<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `NOT` — bitwise and logical "not"

> **Spec:** DRAFT 1 (2026-11-24) — 65 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kops.py`](../../probes/basic/spec/kops.py)); every rule is executable and
> every recorded output is read by one. Goldfish pass 1 (2026-11-24) acted on ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-24):** level 3 — happy path ✗ (`-NOT 0`) · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One difference, found by the spec probe (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`NOT a` flips every bit of a number taken as a 16-bit integer, so `NOT a` is
always `-a - 1`. Because true is −1 and false is 0, it also turns true into
false and back: `IF NOT (A>5) THEN …`. zerobas gives the same results as the Philips VG-8020, except where NOT stands after another operator (below).

The operand rules and the precedence order are shared by all the logical
operators and are described on the [`AND`](AND.md) page.

## Syntax

```
NOT <numeric expression>
```

`NOT` takes one operand, on its right.

## Details

- **Bitwise on 16 bits.** `NOT 0` is −1, `NOT -1` is 0, `NOT 5` is −6.
- **The operand is truncated toward zero to an integer** first: `NOT 2.5` is −3
  (that is, `NOT 2`), `NOT 1.5` is −2. The range is −32768 to 32767; `NOT 70000`
  is `Overflow` (error 6). See [`AND`](AND.md#details).
- **It can be repeated**: `NOT NOT 7` is 7.
- **Precedence:** `NOT` binds tighter than `AND`, `OR` and `IMP`:
  `NOT 1 AND 3` is `(NOT 1) AND 3`, which is 2, and `NOT 1 IMP 2` is
  `(NOT 1) IMP 2`, which is 3. Against `XOR` and `EQV` no order can be
  observed — both groupings always give the same result.
- **NOT takes in a whole comparison and its arithmetic.** `NOT A>5` means
  `NOT (A>5)`: `NOT 1<2` is 0 and `NOT 1+2` is `NOT 3`, −4 (rule R-NOT-PREC
  below). A minus may stand before it: `-NOT 0` is 1.

| you write | you get |
|---|---|
| `NOT 0` | −1 |
| `NOT 2.5` | −3 |
| `NOT 70000` | error 6, `Overflow` |
| `NOT "A"` | error 13, `Type mismatch` |
| `PRINT NOT` | error 24, `Missing operand` |

The whole set of errors `NOT` can raise is {6, 13, 24}, the same on both
machines.

## Example

```
10 PRINT NOT 0;NOT -1;NOT 5
20 PRINT NOT 2.5;NOT NOT 7
30 A=3
40 IF NOT (A>5) THEN PRINT "small"
50 ON ERROR GOTO 80
60 PRINT NOT 70000
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
-1  0 -6
-3  7
small
Error 6
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_not.out`](../../scratchpad/kwdoc_not.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/not_rules.py`](../../probes/basic/spec/not_rules.py), model in
[`kops_model.py`](../../probes/basic/spec/kops_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/kops.py`](../../probes/basic/spec/kops.py) (the operators region's first,
on the shared RAM-record harness [`ramrec.py`](../../probes/basic/spec/ramrec.py) and the USR type readout of
[`kmath.py`](../../probes/basic/spec/kmath.py)), typed on both machines; run file
[`scratchpad/KOP_run1.out`](../../scratchpad/KOP_run1.out) (2026-11-24; zerobas's side on that day's build). Both
operands are `READ` into variables of the group's type and their own bytes recorded first; each case is evaluated as
`R=NOT x` (R a double, its 8 bytes) and as `Q=USR(NOT x)` -- y is READ but unused, so rows that share x repeat a measurement, whose routine copies the result's TYPE and own bytes;
before every case R holds -12345 and the type cell 255.
- **[KOP OI NOT *x* *y*]** integers: 0 / 0, 1 / 0, 0 / 1, -1 / 0, 12 / 10, 5 / 3, -1 / -1, -1 / 255, 255 / -256, 32767 / 1, -32768 / -1, -32768 / 32767, -5 / 3, 5 / -3, -5 / -3, 7 / 0, 0 / 7, 32767 / 32767, -32768 / 2, 1234 / -4321.
- **[KOP OS NOT *x* *y*]** singles: 2.5 / 1, -2.5 / 1, 2.7 / 3, -2.7 / 3, .5 / .5, -.5 / -.5, 3.5 / 7, 32767.9 / 1, -32768.9 / 1, 32768 / 1, 1 / 32768, -32769 / 1, 65535 / 1, 1E10 / 1, 1E-64 / 1, 5.9 / 2.9, -5.9 / 2.9, 7 / .9, 7 / -.5, 12345.6 / 255.
- **[KOP OD NOT *x* *y*]** doubles: 2.5 / 1, -2.5 / 1, 2.7 / 3, -2.7 / 3, 32767.99999999 / 1, -32768.99999999 / 1, 32768 / 1, -32769 / 1, 65535 / 1, 5.9 / 2.9, -5.9 / 2.9, 7 / .99999999999999, 1D20 / 1, .49999999999999 / -.5.
- **[KOP FX *i*]**: fixed expressions (`FX` in the probe): for every ordered pair of AND, OR, XOR, EQV and IMP two
  three-operand chains (some of them give the same value under both groupings; FY adds rows that separate); NOT before each; each operator twice in a row; NOT against `=`,
  `<` and `+`; `-NOT 0`; MOD against `*`, `+`, unary minus and `\`; literal types (`&HFFFF`, `65535`, `7.9`, `2.5!`,
  `1#`); a string on either side and nothing after the operator, for each operator.
- **[KOP FY *i*]** (goldfish pass 1, 2026-11-24): expressions that SEPARATE the groupings FX could not -- `1<2 AND 1`, `1+2 AND 0`, `1=2 OR 3`, `1+2 XOR 3`, `1 EQV 2+3`, `1=1 IMP 1=0`, `6 OR 1 IMP 0`; MOD's own grouping (`100 MOD 7 MOD 3`) and its place against `/` and `^`; `-32768 MOD 5`; Overflow against Division by zero (`32768 MOD 0` ...); two bad operands (`70000 AND "A"`, `"A" AND 70000`, `"A" MOD 0`); NOT after `-`, `*` and `+`; twenty NOTs; `5 AND * 3`, `1 AND )`; and for each two-operand operator a right operand of -32769, 32768# and 1D20.

**Controls** ([`kops_controls.py`](../../probes/basic/spec/kops_controls.py)): each is a rival rule run over the
reference's cases: “operands rounded half away from zero (not truncated)” is FALSE on 20 of the 46 cases R-NOT-VALUE selects (e.g. KOP OS NOT 2.5 1); “operands floored (as INT)” is FALSE on 9 of the 46 cases R-NOT-VALUE selects (e.g. KOP OS NOT -2.5 1); “operands read as unsigned 16-bit (32768 .. 65535 accepted)” is FALSE on 4 of the 8 cases R-NOT-RANGE selects (e.g. KOP OS NOT 32768 1); “NOT tighter than comparisons and arithmetic” is FALSE on 5 of the 13 cases R-NOT-PREC selects (e.g. KOP FX 50); “NOT after an operator a Syntax error -- zerobas's” is FALSE on 4 of the 13 cases R-NOT-PREC selects (e.g. KOP FX 53).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/not_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/not_rules.py --write` -->

**5 rules; 5 hold on the reference. Of the 345 recorded outputs (each case's error from `R=<expr>` and from `Q=USR(<expr>)`, R's 8 bytes, the result's type as USR saw it and the result's own bytes): 345 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The value

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-NOT-VALUE** Each operand is made an integer by CINT's rule first -- the fraction dropped toward zero (2.7 -> 2, -2.7 -> -2, 32767.9 -> 32767, -32768.9 -> -32768) -- and then NOT x is -x-1: every bit inverted; on 16 bits, two's complement. The result is an INTEGER in every case. | 46 | ✓ | ✓ |
| **R-NOT-RANGE** An operand whose truncated value is outside -32768..32767 -- 32768, -32769, 65535, 1E10, 1D20 -- is error 6 (Overflow), whichever side it is on (NOT has one). | 8 | ✓ | ✓ |

#### 2. Precedence and forms

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-NOT-PREC** In an expression the operators bind in this order, tightest first: `^`; unary minus; `*` `/`; `\`; MOD; `+` `-`; the comparisons; NOT; AND; OR; XOR; EQV; IMP -- each group left to right (XOR and EQV cannot be told apart: every grouping of the two agrees). So NOT 1+2 is NOT 3 (-4), NOT 1<2 is 0, 7 MOD 4+2 is 5, -7 MOD 4 is -3, 7\2 MOD 2 is 1; a minus may stand before NOT (-NOT 0 is 1). A literal's own type counts (&HFFFF the integer -1; 65535 a single: error 6). | 13 | ✓ | ✗ 4: KOP FX 53, KOP FY 17, KOP FY 18, KOP FY 19 |
| **R-NOT-ERRORS** A string operand (`NOT "A"`) is error 13 (Type mismatch); `NOT` alone is error 24 (Missing operand). | 2 | ✓ | ✓ |

#### 3. The result stored

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-NOT-ASSIGN** `R=x NOT y` with R a double stores the integer result by its value; after an error R keeps its sentinel -12345. Read in every case. | 69 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

- **`-NOT 0` (and NOT after any operator) is a Syntax error here; the VG-8020 gives 1** ([D-MINUSNOT](../../todo/open/D-MINUSNOT.md); rule R-NOT-PREC, KOP FX 53; and NOT after any operator -- `2*NOT 0`, `2+NOT 0=0`, `-NOT 0=1` -- KOP FY 17-19): zerobas accepts NOT only at the start of an operand.

The one rung not yet proven is **RAM usage**: `NOT` uses the same amount of free
memory on both machines, but the VG-8020 writes some work-area cells that
zerobas does not.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] Which work-area cells the operation writes (the RAM-usage rung).
- [A] An operand's own error other than a string (13) and a missing operand (24).
- [A] DAC's bytes beyond the integer result (DAC+0/+1: the reference leaves an operand's bytes there, zerobas zeros) are not evidence -- a USR routine reading them is outside the contract.
- [A] The error set's closure: the nesting limit (error 7 in a very deep chain) and other structure errors beyond `5 AND * 3` / `1 AND )` are not tried.

## What we found, and how

- **The spec probe** (D-KWSPEC, 2026-11-24): every operand made an integer by CINT's rule (toward zero, -32768..32767 strictly: 65535 is Overflow, not -1), the result an integer, and the precedence the pages give, NOT below the comparisons and arithmetic -- each against a rival the controls refute. One difference: `-NOT 0` (D-MINUSNOT).
- **Fractional operands** follow the VG-8020's truncate-or-`Overflow` rule
  since 2026-07-11 (`NOT 2.5` is −3, not −4):
  [spec-basic-float-core.md](../spec-basic-float-core.md) §10.3.
- **`NOT` against the other operators was measured with care** (2026-07-27).
  `NOT 1 EQV 2` gives 3 under both groupings, because `EQV` and `XOR` absorb a
  complement; so `NOT` against `EQV` and `XOR` cannot be ordered by any test,
  while against `IMP` (`NOT 1 IMP 2`) it can:
  [logicops-vg8020-characterization.md](../logicops-vg8020-characterization.md) §5.
- **Deeply nested expressions had no stack limit** (fixed 2026-09-27,
  D-STACKFLOOR). With arrays filling memory to the edge, a deep enough formula
  could overwrite them. A chain of `NOT`s is one of the two ways an expression
  nests (parentheses and functions are the other), so `NOT` got the same check:
  the evaluator now stops with `Out of memory` (error 7) instead, as the
  reference does.
- **The tests could not at first prove they would notice a broken `NOT`**
  (2026-09-14, D-KWOPCUT): its dispatch is a short jump that the
  deliberately-broken-build check did not recognise. It is now found by the
  routine it lives in, and a broken `NOT` fails the gates.

## Where it lives

`cl_not` in [basic/expr.asm](../../basic/expr.asm): a prefix of the
operator-precedence loop, between the logical operators and the comparisons; the integer conversion is
`fac_to_int_strict_reset` in
[basic/float-arith.asm](../../basic/float-arith.asm).

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make logicops-acceptance` — results, precedence against the two-operand
  operators, and the integer range.
- `make float-acceptance` — fractional operands (`NOT 1.5`, `NOT 2.5`).
- `make kwsweep` — the everyday row (`NOT 0`), the error rows for {6, 13, 24},
  and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
