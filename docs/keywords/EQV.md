<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `EQV` — bitwise equivalence

> **Spec:** DRAFT 1 (2026-11-24) — 76 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kops.py`](../../probes/basic/spec/kops.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-24):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`a EQV b` combines two numbers bit by bit as 16-bit integers: a result bit is 1
where the two operands have the *same* bit. It is exactly `NOT (a XOR b)`. On
truth values (−1 and 0) it answers "are both true, or both false?". zerobas
behaves exactly like the Philips VG-8020 for every case we have measured,
errors included.

The operand rules and the precedence order are shared by all the logical
operators and are described on the [`AND`](AND.md) page.

## Syntax

```
<numeric expression> EQV <numeric expression>
```

## Details

- **Measured results:**

  | expression | result | expression | result |
  |---|---|---|---|
  | `0 EQV 0` | −1 | `-1 EQV -1` | −1 |
  | `0 EQV -1` | 0 | `-1 EQV 0` | 0 |
  | `5 EQV 3` | −7 | `12 EQV 10` | −7 |
  | `1 EQV 0` | −2 | | |

  It is commutative: `a EQV b` equals `b EQV a`.
- **Operands are truncated toward zero to an integer** first: `2.7 EQV 0` is −3
  (operand 2) and `-2.7 EQV 0` is 1 (operand −2). The range is −32768 to 32767:
  `-32768 EQV 0` is 32767, `-32769 EQV 0` and `1E10 EQV 1` are `Overflow`
  (error 6). See [`AND`](AND.md#details).
- **Precedence:** looser than `AND` and `OR`, tighter than `IMP`. Against
  [`XOR`](XOR.md) no order can be observed. Arithmetic binds tighter:
  `1 EQV 2 + 3` is `1 EQV 5`, which is −5.

| you write | you get |
|---|---|
| `5 EQV 3` | −7 |
| `70000 EQV 1`, `1 EQV 70000` | error 6, `Overflow` |
| `1 EQV "A"`, `"A" EQV 1` | error 13, `Type mismatch` |
| `PRINT 1 EQV` | error 24, `Missing operand` |

The whole set of errors `EQV` can raise is {6, 13, 24}, the same on both
machines.

## Example

```
10 PRINT 5 EQV 3;1 EQV 0
20 PRINT 0 EQV 0;0 EQV -1
30 PRINT NOT (5 XOR 3)
40 PRINT (1>2) EQV (3>4)
50 ON ERROR GOTO 80
60 PRINT 1 EQV "A"
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
-7 -2
-1  0
-7
-1
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_eqv.out`](../../scratchpad/kwdoc_eqv.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/eqv_rules.py`](../../probes/basic/spec/eqv_rules.py), model in
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
`R=x EQV y` (R a double, its 8 bytes) and as `Q=USR(x EQV y)`, whose routine copies the result's TYPE and own bytes;
before every case R holds -12345 and the type cell 255.
- **[KOP OI EQV *x* *y*]** integers: 0 / 0, 1 / 0, 0 / 1, -1 / 0, 12 / 10, 5 / 3, -1 / -1, -1 / 255, 255 / -256, 32767 / 1, -32768 / -1, -32768 / 32767, -5 / 3, 5 / -3, -5 / -3, 7 / 0, 0 / 7, 32767 / 32767, -32768 / 2, 1234 / -4321.
- **[KOP OS EQV *x* *y*]** singles: 2.5 / 1, -2.5 / 1, 2.7 / 3, -2.7 / 3, .5 / .5, -.5 / -.5, 3.5 / 7, 32767.9 / 1, -32768.9 / 1, 32768 / 1, 1 / 32768, -32769 / 1, 65535 / 1, 1E10 / 1, 1E-64 / 1, 5.9 / 2.9, -5.9 / 2.9, 7 / .9, 7 / -.5, 12345.6 / 255.
- **[KOP OD EQV *x* *y*]** doubles: 2.5 / 1, -2.5 / 1, 2.7 / 3, -2.7 / 3, 32767.99999999 / 1, -32768.99999999 / 1, 32768 / 1, -32769 / 1, 65535 / 1, 5.9 / 2.9, -5.9 / 2.9, 7 / .99999999999999, 1D20 / 1, .49999999999999 / -.5.
- **[KOP FX *i*]**: fixed expressions (`FX` in the probe): for every ordered pair of AND, OR, XOR, EQV and IMP a
  three-operand chain whose two groupings differ; NOT before each; each operator twice in a row; NOT against `=`,
  `<` and `+`; `-NOT 0`; MOD against `*`, `+`, unary minus and `\`; literal types (`&HFFFF`, `65535`, `7.9`, `2.5!`,
  `1#`); a string on either side and nothing after the operator, for each operator.

**Controls** ([`kops_controls.py`](../../probes/basic/spec/kops_controls.py)): each is a rival rule run over the
reference's cases: “operands rounded half away from zero (not truncated)” is FALSE on 20 of the 45 cases R-EQV-VALUE selects (e.g. KOP OS EQV 2.5 1); “operands floored (as INT)” is FALSE on 10 of the 45 cases R-EQV-VALUE selects (e.g. KOP OS EQV -2.5 1); “operands read as unsigned 16-bit (32768 .. 65535 accepted)” is FALSE on 5 of the 9 cases R-EQV-RANGE selects (e.g. KOP OS EQV 32768 1); “EQV tighter than OR” is FALSE on 2 of the 19 cases R-EQV-PREC selects (e.g. KOP FX 12).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/eqv_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/eqv_rules.py --write` -->

**5 rules; 5 hold on the reference. Of the 380 recorded outputs (each case's error from `R=<expr>` and from `Q=USR(<expr>)`, R's 8 bytes, the result's type as USR saw it and the result's own bytes): 380 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The value

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-EQV-VALUE** Each operand is made an integer by CINT's rule first -- the fraction dropped toward zero (2.7 -> 2, -2.7 -> -2, 32767.9 -> 32767, -32768.9 -> -32768) -- and then where the two agree (NOT (x XOR y)); on 16 bits, two's complement. The result is an INTEGER in every case. | 45 | ✓ | ✓ |
| **R-EQV-RANGE** An operand whose truncated value is outside -32768..32767 -- 32768, -32769, 65535, 1E10, 1D20 -- is error 6 (Overflow), whichever side it is on. | 9 | ✓ | ✓ |

#### 2. Precedence and forms

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-EQV-PREC** In an expression the operators bind in this order, tightest first: `^`; unary minus; `*` `/`; `\`; MOD; `+` `-`; the comparisons; NOT; AND; OR; XOR; EQV; IMP -- each group left to right (XOR and EQV cannot be told apart: every grouping of the two agrees). So NOT 1+2 is NOT 3 (-4), NOT 1<2 is 0, 7 MOD 4+2 is 5, -7 MOD 4 is -3, 7\2 MOD 2 is 1; a minus may stand before NOT (-NOT 0 is 1). A literal's own type counts (&HFFFF the integer -1; 65535 a single: error 6). | 19 | ✓ | ✓ |
| **R-EQV-ERRORS** A string on either side is error 13 (Type mismatch); nothing after the operator (`1 AND`, `NOT` alone) is error 24 (Missing operand). | 3 | ✓ | ✓ |

#### 3. The result stored

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-EQV-ASSIGN** `R=x EQV y` with R a double stores the integer result by its value; after an error R keeps its sentinel -12345. Read in every case. | 76 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `EQV` uses the same amount of free
memory on both machines, but the VG-8020 writes some work-area cells that
zerobas does not.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] Which work-area cells the operation writes (the RAM-usage rung).
- [A] An operand's own error other than a string (13) and a missing operand (24).

## What we found, and how

- **The spec probe** (D-KWSPEC, 2026-11-24): every operand made an integer by CINT's rule (toward zero, -32768..32767 strictly: 65535 is Overflow, not -1), the result an integer, and the precedence the pages give, NOT below the comparisons and arithmetic -- each against a rival the controls refute. zerobas agrees in every case.
- **`EQV` was missing, and silently wrong** (added 2026-07-27). Before, zerobas
  read `EQV` as a variable name, so `PRINT 5 EQV 3` printed three separate
  values with no error. Its meaning was measured before it was written:
  `NOT (a XOR b)` was treated as a guess to search for test values with, and
  the VG-8020's own answers decided. The token number (`$F9`) was read from
  the VG-8020's own tokenised lines:
  [logicops-vg8020-characterization.md](../logicops-vg8020-characterization.md),
  [spec-basic-logicops-eqv-imp.md](../spec-basic-logicops-eqv-imp.md).
- **The integer conversion was read through `EQV` itself.** `EQV n 0` equals
  `NOT n`, so its printed result names the converted operand exactly; that is
  how truncation (not rounding) was established for all the logical operators.
- **`EQV` and `XOR` have no observable order**, so where `EQV` sits relative to
  `XOR` is a free choice; it was decided on 2026-07-27 to keep them on separate
  levels, in the manual's order.
- **Adding it made the parser smaller.** `EQV` and `IMP` came in with one
  table-driven layer replacing three hand-written ones, which took less ROM
  space than before.

## Where it lives

The operator-precedence loop in [basic/expr.asm](../../basic/expr.asm) looks
the token up in `cl_lvtab` ([basic/islands.asm](../../basic/islands.asm)); the leaf `lg_eqv`
(`xor`, then complement) does the work.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make logicops-acceptance` — the truth table, every precedence pair, the
  integer range; a build with the complement deleted fails it.
- `make kwsweep` — the everyday row (`5 EQV 3`), the error rows for
  {6, 13, 24}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
