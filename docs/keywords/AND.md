<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `AND` — bitwise and logical "and"

> **Spec:** DRAFT 1 (2026-11-24) — 78 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kops.py`](../../probes/basic/spec/kops.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-24):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`a AND b` combines two numbers bit by bit as 16-bit integers: a result bit is 1
only where both operands have a 1. Because a comparison gives −1 (all bits set)
for true and 0 for false, the same operator also works as the logical "and" in
`IF A>0 AND A<10 THEN …`. zerobas behaves exactly like the Philips VG-8020 for
every case we have measured, errors included.

This page also holds the rules shared by all six logical operators: `AND`,
[`OR`](OR.md), [`XOR`](XOR.md), [`EQV`](EQV.md), [`IMP`](IMP.md) and
[`NOT`](NOT.md).

## Syntax

```
<numeric expression> AND <numeric expression>
```

## Details

- **Bitwise on 16 bits.** `5 AND 3` is 1, `12 AND 10` is 8, `-1 AND 255` is
  255. The result is always a whole number from −32768 to 32767.
- **As a logical "and"** it relies on true being −1 and false 0:
  `(1<2) AND (3<4)` is −1, `(1<2) AND (3>4)` is 0.
- **Each operand is converted to an integer first, by truncating toward zero**
  — never by rounding. `2.7` becomes 2, `-2.7` becomes −2, and `2.5` and `3.5`
  become 2 and 3. So `2.7 AND 3` is 2.
- **The operand range is −32768 to 32767.** A value outside it is `Overflow`
  (error 6), on either side: `70000 AND 1` and `1 AND 70000` both fail. A
  fraction just inside the range is fine — `32767.6` truncates to 32767.
  (This is stricter than `POKE`'s address range, which accepts up to 65535.)
- **A string on either side** is `Type mismatch` (error 13): `1 AND "A"`,
  and also `PRINT "A" AND 1`.
- **Nothing after the operator** (`PRINT 1 AND`) is `Missing operand`
  (error 24).

### Precedence of the logical operators

Measured on the VG-8020 for every ordered pair, in both directions:

| tightest | | | | loosest |
|---|---|---|---|---|
| `NOT` | `AND` | `OR` | `XOR`, `EQV` | `IMP` |

- Arithmetic and comparisons bind tighter than the two-operand ones, so
  `A>0 AND A<10` means `(A>0) AND (A<10)`. `NOT` sits below the
  comparisons too: `NOT A>5` is `NOT (A>5)` (see [`NOT`](NOT.md)).
- `XOR` and `EQV` cannot be ordered against each other by any measurement:
  every grouping of the two gives the same answer.
- All of them group left to right; this only shows with `IMP` (see its page).

### Errors

| you write | you get |
|---|---|
| `5 AND 3` | 1 |
| `2.7 AND 3` | 2 |
| `70000 AND 1`, `1 AND 70000` | error 6, `Overflow` |
| `1 AND "A"` | error 13, `Type mismatch` |
| `PRINT 1 AND` | error 24, `Missing operand` |

The whole set of errors `AND` can raise is {6, 13, 24}, the same on both
machines.

## Example

```
10 A=5
20 IF A>0 AND A<10 THEN PRINT "ok"
30 PRINT 5 AND 3;12 AND 10;-1 AND 255
40 PRINT 2.7 AND 3
50 ON ERROR GOTO 80
60 PRINT 70000 AND 1
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
ok
 1  8  255
 2
Error 6
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_and.out`](../../scratchpad/kwdoc_and.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/and_rules.py`](../../probes/basic/spec/and_rules.py), model in
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
`R=x AND y` (R a double, its 8 bytes) and as `Q=USR(x AND y)`, whose routine copies the result's TYPE and own bytes;
before every case R holds -12345 and the type cell 255.
- **[KOP OI AND *x* *y*]** integers: 0 / 0, 1 / 0, 0 / 1, -1 / 0, 12 / 10, 5 / 3, -1 / -1, -1 / 255, 255 / -256, 32767 / 1, -32768 / -1, -32768 / 32767, -5 / 3, 5 / -3, -5 / -3, 7 / 0, 0 / 7, 32767 / 32767, -32768 / 2, 1234 / -4321.
- **[KOP OS AND *x* *y*]** singles: 2.5 / 1, -2.5 / 1, 2.7 / 3, -2.7 / 3, .5 / .5, -.5 / -.5, 3.5 / 7, 32767.9 / 1, -32768.9 / 1, 32768 / 1, 1 / 32768, -32769 / 1, 65535 / 1, 1E10 / 1, 1E-64 / 1, 5.9 / 2.9, -5.9 / 2.9, 7 / .9, 7 / -.5, 12345.6 / 255.
- **[KOP OD AND *x* *y*]** doubles: 2.5 / 1, -2.5 / 1, 2.7 / 3, -2.7 / 3, 32767.99999999 / 1, -32768.99999999 / 1, 32768 / 1, -32769 / 1, 65535 / 1, 5.9 / 2.9, -5.9 / 2.9, 7 / .99999999999999, 1D20 / 1, .49999999999999 / -.5.
- **[KOP FX *i*]**: fixed expressions (`FX` in the probe): for every ordered pair of AND, OR, XOR, EQV and IMP a
  three-operand chain whose two groupings differ; NOT before each; each operator twice in a row; NOT against `=`,
  `<` and `+`; `-NOT 0`; MOD against `*`, `+`, unary minus and `\`; literal types (`&HFFFF`, `65535`, `7.9`, `2.5!`,
  `1#`); a string on either side and nothing after the operator, for each operator.

**Controls** ([`kops_controls.py`](../../probes/basic/spec/kops_controls.py)): each is a rival rule run over the
reference's cases: “operands rounded half away from zero (not truncated)” is FALSE on 21 of the 45 cases R-AND-VALUE selects (e.g. KOP OS AND 2.5 1); “operands floored (as INT)” is FALSE on 8 of the 45 cases R-AND-VALUE selects (e.g. KOP OS AND -2.5 1); “operands read as unsigned 16-bit (32768 .. 65535 accepted)” is FALSE on 5 of the 9 cases R-AND-RANGE selects (e.g. KOP OS AND 32768 1); “AND and OR at one level, left to right” is FALSE on 1 of the 21 cases R-AND-PREC selects (e.g. KOP FX 8).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/and_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/and_rules.py --write` -->

**5 rules; 5 hold on the reference. Of the 390 recorded outputs (each case's error from `R=<expr>` and from `Q=USR(<expr>)`, R's 8 bytes, the result's type as USR saw it and the result's own bytes): 390 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The value

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-AND-VALUE** Each operand is made an integer by CINT's rule first -- the fraction dropped toward zero (2.7 -> 2, -2.7 -> -2, 32767.9 -> 32767, -32768.9 -> -32768) -- and then a bit is set where it is set in both; on 16 bits, two's complement. The result is an INTEGER in every case. | 45 | ✓ | ✓ |
| **R-AND-RANGE** An operand whose truncated value is outside -32768..32767 -- 32768, -32769, 65535, 1E10, 1D20 -- is error 6 (Overflow), whichever side it is on. | 9 | ✓ | ✓ |

#### 2. Precedence and forms

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-AND-PREC** In an expression the operators bind in this order, tightest first: `^`; unary minus; `*` `/`; `\`; MOD; `+` `-`; the comparisons; NOT; AND; OR; XOR; EQV; IMP -- each group left to right (XOR and EQV cannot be told apart: every grouping of the two agrees). So NOT 1+2 is NOT 3 (-4), NOT 1<2 is 0, 7 MOD 4+2 is 5, -7 MOD 4 is -3, 7\2 MOD 2 is 1; a minus may stand before NOT (-NOT 0 is 1). A literal's own type counts (&HFFFF the integer -1; 65535 a single: error 6). | 21 | ✓ | ✓ |
| **R-AND-ERRORS** A string on either side is error 13 (Type mismatch); nothing after the operator (`1 AND`, `NOT` alone) is error 24 (Missing operand). | 3 | ✓ | ✓ |

#### 3. The result stored

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-AND-ASSIGN** `R=x AND y` with R a double stores the integer result by its value; after an error R keeps its sentinel -12345. Read in every case. | 78 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `AND` uses the same amount of
free memory on both machines, but the VG-8020 writes some work-area cells that
zerobas does not. Nothing a program can observe through `FRE` differs.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] Which work-area cells the operation writes (the RAM-usage rung).
- [A] An operand's own error other than a string (13) and a missing operand (24).

## What we found, and how

- **The spec probe** (D-KWSPEC, 2026-11-24): every operand made an integer by CINT's rule (toward zero, -32768..32767 strictly: 65535 is Overflow, not -1), the result an integer, and the precedence the pages give, NOT below the comparisons and arithmetic -- each against a rival the controls refute. zerobas agrees in every case.
- **Fractions were rounded, and out-of-range numbers silently became 0**, in
  an interim stage of the float work (fixed 2026-07-11, with the float
  arithmetic). Measuring the VG-8020 showed that the logical operators truncate
  toward zero and raise `Overflow` outside −32768 to 32767 — the same strict
  rule as `\` and `MOD`, and not the wider range `POKE` accepts:
  [spec-basic-float-core.md](../spec-basic-float-core.md) §10.3.
- **The precedence order was measured, not copied from the manual**
  (2026-07-27). Each pair was tested with three lines — the bare expression and
  both explicit groupings — so that a test whose two groupings happen to agree
  is reported as "cannot tell" rather than as a pass. That is how `XOR` and
  `EQV` turned out to be indistinguishable:
  [logicops-vg8020-characterization.md](../logicops-vg8020-characterization.md).
- **`PRINT "A" AND 1` printed two values** instead of `Type mismatch` (fixed
  2026-07-27). `PRINT` printed the string, then read the operator as the start
  of a second item. Eleven operators were affected, not the four first
  suspected: [spec-basic-relational-chain.md](../spec-basic-relational-chain.md).
- **One table now drives all five two-operand logical operators** (2026-07-27,
  when `EQV` and `IMP` were added). The first build of it passed every static
  check and crashed on any fractional operand (`2.7 AND 0`); the side-by-side
  test against the VG-8020 caught it before it shipped:
  [spec-basic-logicops-eqv-imp.md](../spec-basic-logicops-eqv-imp.md) §5.1.
- **The tests could not at first prove they would notice a broken `AND`**
  (2026-09-14, D-KWOPCUT). The deliberately-broken-build check finds a keyword
  by the compare that dispatches it, and the logical operators are found by
  walking a table instead. A cut for that table was added; a broken `AND` now
  fails the gates.

## Where it lives

The operator-precedence loop in [basic/expr.asm](../../basic/expr.asm) looks
the token up in `cl_lvtab` ([basic/islands.asm](../../basic/islands.asm));
`lg_apply` and the one-instruction leaf `lg_and` do the work. The integer
conversion is `fac_to_int_strict_reset` in
[basic/float-arith.asm](../../basic/float-arith.asm), shared with `\` and
[`MOD`](MOD.md).

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make logicops-acceptance` — results, every precedence pair, grouping, the
  integer range, and the operator-after-a-string rows.
- `make float-acceptance` — fractional and out-of-range operands
  (`1.5 AND 3`, `40000! AND 65535`).
- `make kwsweep` — the everyday row (`5 AND 3`), the error rows for
  {6, 13, 24}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
