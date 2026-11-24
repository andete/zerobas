<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `MOD` — the remainder of an integer division

> **Spec:** DRAFT 1 (2026-11-24) — 64 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kops.py`](../../probes/basic/spec/kops.py)); every rule is executable and
> every recorded output is read by one. Goldfish pass 1 (2026-11-24) acted on ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-24):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`a MOD b` is what is left over when `a` is divided by `b` as whole numbers:
`7 MOD 3` is 1. It is the partner of integer division `\`: for any `a` and `b`,
`a = (a\b)*b + (a MOD b)`. zerobas behaves exactly like the Philips VG-8020
for every case we have measured, errors included.

## Syntax

```
<numeric expression> MOD <numeric expression>
```

## Details

- **The result takes the sign of the left operand** (the dividend), because
  `\` truncates toward zero:

  | `7 MOD 2` | `-7 MOD 2` | `7 MOD -2` | `-7 MOD -2` |
  |---|---|---|---|
  | 1 | −1 | 1 | −1 |

- **Both operands are converted to integers first, by truncating toward zero**
  — never by rounding: `7.5 MOD 4` is `7 MOD 4`, which is 3. This is the same
  rule the logical operators use ([`AND`](AND.md#details)).
- **The operand range is −32768 to 32767.** A value outside it is `Overflow`
  (error 6): `70000 MOD 2`, `40000 MOD 7`.
- **Dividing by zero** is `Division by zero` (error 11): `5 MOD 0`.
- **A string operand** is `Type mismatch` (error 13), on either side:
  `5 MOD "A"`, and also `PRINT "A" MOD 2`.
- **Nothing after the operator** (`PRINT 5 MOD`) is `Missing operand`
  (error 24).
- **Where it sits among the arithmetic operators:** after `*`, `/` and `\`,
  before `+` and `-`, measured on the reference: `7 MOD 4*2` is 7, `7 MOD 4+2`
  is 5, `7\2 MOD 2` is 1, and `-7 MOD 4` is −3 (rule R-MOD-PREC below).

| you write | you get |
|---|---|
| `7 MOD 3` | 1 |
| `-7 MOD 2` | −1 |
| `7.5 MOD 4` | 3 |
| `70000 MOD 2` | error 6, `Overflow` |
| `5 MOD 0` | error 11, `Division by zero` |
| `5 MOD "A"` | error 13, `Type mismatch` |
| `PRINT 5 MOD` | error 24, `Missing operand` |

The whole set of errors `MOD` can raise is {6, 11, 13, 24}, the same on both
machines.

## Example

```
10 PRINT 7 MOD 3;-7 MOD 2;7 MOD -2
20 PRINT 7.9 MOD 3;7.5 MOD 4
30 FOR I=1 TO 6:PRINT I MOD 3;:NEXT
40 PRINT
50 ON ERROR GOTO 80
60 PRINT 5 MOD 0
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 1 -1  1
 1  3
 1  2  0  1  2  0
Error 11
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_mod.out`](../../scratchpad/kwdoc_mod.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/mod_rules.py`](../../probes/basic/spec/mod_rules.py), model in
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
`R=x MOD y` (R a double, its 8 bytes) and as `Q=USR(x MOD y)`, whose routine copies the result's TYPE and own bytes;
before every case R holds -12345 and the type cell 255.
- **[KOP OI MOD *x* *y*]** integers: 0 / 0, 1 / 0, 0 / 1, -1 / 0, 12 / 10, 5 / 3, -1 / -1, -1 / 255, 255 / -256, 32767 / 1, -32768 / -1, -32768 / 32767, -5 / 3, 5 / -3, -5 / -3, 7 / 0, 0 / 7, 32767 / 32767, -32768 / 2, 1234 / -4321.
- **[KOP OS MOD *x* *y*]** singles: 2.5 / 1, -2.5 / 1, 2.7 / 3, -2.7 / 3, .5 / .5, -.5 / -.5, 3.5 / 7, 32767.9 / 1, -32768.9 / 1, 32768 / 1, 1 / 32768, -32769 / 1, 65535 / 1, 1E10 / 1, 1E-64 / 1, 5.9 / 2.9, -5.9 / 2.9, 7 / .9, 7 / -.5, 12345.6 / 255.
- **[KOP OD MOD *x* *y*]** doubles: 2.5 / 1, -2.5 / 1, 2.7 / 3, -2.7 / 3, 32767.99999999 / 1, -32768.99999999 / 1, 32768 / 1, -32769 / 1, 65535 / 1, 5.9 / 2.9, -5.9 / 2.9, 7 / .99999999999999, 1D20 / 1, .49999999999999 / -.5.
- **[KOP FX *i*]**: fixed expressions (`FX` in the probe): for every ordered pair of AND, OR, XOR, EQV and IMP two
  three-operand chains (some of them give the same value under both groupings; FY adds rows that separate); NOT before each; each operator twice in a row; NOT against `=`,
  `<` and `+`; `-NOT 0`; MOD against `*`, `+`, unary minus and `\`; literal types (`&HFFFF`, `65535`, `7.9`, `2.5!`,
  `1#`); a string on either side and nothing after the operator, for each operator.
- **[KOP FY *i*]** (goldfish pass 1, 2026-11-24): expressions that SEPARATE the groupings FX could not -- `1<2 AND 1`, `1+2 AND 0`, `1=2 OR 3`, `1+2 XOR 3`, `1 EQV 2+3`, `1=1 IMP 1=0`, `6 OR 1 IMP 0`; MOD's own grouping (`100 MOD 7 MOD 3`) and its place against `/` and `^`; `-32768 MOD 5`; Overflow against Division by zero (`32768 MOD 0` ...); two bad operands (`70000 AND "A"`, `"A" AND 70000`, `"A" MOD 0`); NOT after `-`, `*` and `+`; twenty NOTs; `5 AND * 3`, `1 AND )`; and for each two-operand operator a right operand of -32769, 32768# and 1D20.

**Controls** ([`kops_controls.py`](../../probes/basic/spec/kops_controls.py)): each is a rival rule run over the
reference's cases: “operands rounded half away from zero (not truncated)” is FALSE on 14 of the 35 cases R-MOD-VALUE selects (e.g. KOP OS MOD 2.7 3); “operands floored (as INT)” is FALSE on 6 of the 35 cases R-MOD-VALUE selects (e.g. KOP OS MOD -2.7 3); “operands read as unsigned 16-bit (32768 .. 65535 accepted)” is FALSE on 7 of the 15 cases R-MOD-RANGE selects (e.g. KOP OS MOD 32768 1); “the remainder with the divisor's sign” is FALSE on 10 of the 35 cases R-MOD-VALUE selects (e.g. KOP OI MOD -1 255); “MOD looser than + and -” is FALSE on 1 of the 11 cases R-MOD-PREC selects (e.g. KOP FX 57).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/mod_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/mod_rules.py --write` -->

**6 rules; 6 hold on the reference. Of the 375 recorded outputs (each case's error from `R=<expr>` and from `Q=USR(<expr>)`, R's 8 bytes, the result's type as USR saw it and the result's own bytes): 375 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The value

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-MOD-VALUE** Each operand is made an integer by CINT's rule first -- the fraction dropped toward zero (2.7 -> 2, -2.7 -> -2, 32767.9 -> 32767, -32768.9 -> -32768) -- and then x MOD y is the remainder of x \ y, with x's sign (-5 MOD 3 is -2, 5 MOD -3 is 2); y = 0 -- after truncation: .5, .9 -- is error 11 (Division by zero); on 16 bits, two's complement. The result is an INTEGER in every case. | 35 | ✓ | ✓ |
| **R-MOD-RANGE** An operand whose truncated value is outside -32768..32767 -- 32768, -32769, 65535, 1E10, 1D20 -- is error 6 (Overflow), whichever side it is on, before any Division by zero. | 15 | ✓ | ✓ |
| **R-MOD-ZERO** A divisor that truncates to 0 -- 0, .5, -.5, .9, .99999999999999 -- is error 11 (Division by zero). | 10 | ✓ | ✓ |

#### 2. Precedence and forms

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-MOD-PREC** In an expression the operators bind in this order, tightest first: `^`; unary minus; `*` `/`; `\`; MOD; `+` `-`; the comparisons; NOT; AND; OR; XOR; EQV; IMP -- each group left to right (XOR and EQV cannot be told apart: every grouping of the two agrees). So NOT 1+2 is NOT 3 (-4), NOT 1<2 is 0, 7 MOD 4+2 is 5, -7 MOD 4 is -3, 7\2 MOD 2 is 1; a minus may stand before NOT (-NOT 0 is 1). A literal's own type counts (&HFFFF the integer -1; 65535 a single: error 6). | 11 | ✓ | ✓ |
| **R-MOD-ERRORS** A string on either side is error 13 (Type mismatch) -- unless the left operand is out of range: it is made an integer as soon as the operator is met, so `70000 AND "A"` is error 6; nothing after the operator is error 24 (Missing operand); an operator or `)` where an operand belongs is error 2. | 4 | ✓ | ✓ |

#### 3. The result stored

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-MOD-ASSIGN** `R=x MOD y` with R a double stores the integer result by its value; after an error R keeps its sentinel -12345. Read in every case. | 75 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `MOD` uses the same amount of free
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

- **The spec probe** (D-KWSPEC, 2026-11-24): every operand made an integer by CINT's rule (toward zero, -32768..32767 strictly: 65535 is Overflow, not -1), the result an integer, and the precedence the pages give, NOT below the comparisons and arithmetic -- each against a rival the controls refute. zerobas agrees in every case.
- **`MOD` used to be unsigned, and `MOD 0` gave 0** (fixed 2026-07-11). The
  first integer-only version divided without regard to sign and returned 0
  for a zero divisor; both were written down as known differences. Measuring the
  VG-8020 settled the sign rule, the truncation of fractional operands and the
  `Division by zero` error, and the float arithmetic brought all three in:
  [spec-basic-float-core.md](../spec-basic-float-core.md) §10.3–§10.4.
- **`PRINT "A" MOD 2` printed `A` and then `0`** instead of `Type mismatch`
  (fixed 2026-07-27). `PRINT` printed the string and then read `MOD` as the
  start of a second item; eleven operators had the same fault:
  [spec-basic-relational-chain.md](../spec-basic-relational-chain.md).
- **The tests could not at first prove they would notice a broken `MOD`**
  (2026-09-14, D-KWOPCUT). The deliberately-broken-build check looks for a
  compare followed by a jump to the keyword's code, and `MOD`'s compare is
  followed by a plain return instead. It is now found by the routine it lives
  in, and a broken `MOD` fails the gates.

## Where it lives

The operator-precedence loop in [basic/expr.asm](../../basic/expr.asm) looks
the token up in `cl_lvtab` ([basic/islands.asm](../../basic/islands.asm)); the
remainder is `signed_mod_de_bc` and the integer conversion
`fac_to_int_strict_reset`, both in
[basic/float-arith.asm](../../basic/float-arith.asm).

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make float-acceptance` — the signs, division by zero, fractional and
  out-of-range operands (`7.9 MOD 3`, `40000 MOD 7`).
- `make logicops-acceptance` — the operator-after-a-string row (`"A" MOD 2`).
- `make kwsweep` — the everyday row (`7 MOD 3`), the error rows for
  {6, 11, 13, 24}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
