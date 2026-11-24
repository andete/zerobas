<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `XOR` — bitwise exclusive "or"

> **Spec:** DRAFT 1 (2026-11-24) — 76 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kops.py`](../../probes/basic/spec/kops.py)); every rule is executable and
> every recorded output is read by one. Goldfish pass 1 (2026-11-24) acted on ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-24):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`a XOR b` combines two numbers bit by bit as 16-bit integers: a result bit is 1
where exactly one of the operands has a 1. Applying the same `XOR` twice gives
the original number back, and `XOR -1` flips every bit. zerobas behaves exactly
like the Philips VG-8020 for every case we have measured, errors included.

The operand rules and the precedence order are shared by all the logical
operators and are described on the [`AND`](AND.md) page.

## Syntax

```
<numeric expression> XOR <numeric expression>
```

## Details

- **Bitwise on 16 bits.** `5 XOR 3` is 6, `12 XOR 9` is 5, `5 XOR -1` is −6
  (the same as `NOT 5`).
- **On truth values** (−1 and 0) it is "one or the other but not both".
- **Operands are truncated toward zero to an integer** first; outside −32768 to
  32767 is `Overflow` (error 6). See [`AND`](AND.md#details).
- **Precedence:** looser than `AND` and `OR`, tighter than `IMP`. `XOR` and
  [`EQV`](EQV.md) cannot be ordered against each other by any measurement —
  every grouping of the two gives the same result.

| you write | you get |
|---|---|
| `5 XOR 3` | 6 |
| `70000 XOR 1`, `1 XOR 70000` | error 6, `Overflow` |
| `1 XOR "A"` | error 13, `Type mismatch` |
| `PRINT 1 XOR` | error 24, `Missing operand` |

The whole set of errors `XOR` can raise is {6, 13, 24}, the same on both
machines.

## Example

```
10 PRINT 5 XOR 3;12 XOR 9
20 PRINT 5 XOR -1
30 A=1234:K=99:B=A XOR K
40 PRINT B;B XOR K
50 ON ERROR GOTO 80
60 PRINT 1 XOR 70000
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 6  5
-6
 1201  1234
Error 6
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_xor.out`](../../scratchpad/kwdoc_xor.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/xor_rules.py`](../../probes/basic/spec/xor_rules.py), model in
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
`R=x XOR y` (R a double, its 8 bytes) and as `Q=USR(x XOR y)`, whose routine copies the result's TYPE and own bytes;
before every case R holds -12345 and the type cell 255.
- **[KOP OI XOR *x* *y*]** integers: 0 / 0, 1 / 0, 0 / 1, -1 / 0, 12 / 10, 5 / 3, -1 / -1, -1 / 255, 255 / -256, 32767 / 1, -32768 / -1, -32768 / 32767, -5 / 3, 5 / -3, -5 / -3, 7 / 0, 0 / 7, 32767 / 32767, -32768 / 2, 1234 / -4321.
- **[KOP OS XOR *x* *y*]** singles: 2.5 / 1, -2.5 / 1, 2.7 / 3, -2.7 / 3, .5 / .5, -.5 / -.5, 3.5 / 7, 32767.9 / 1, -32768.9 / 1, 32768 / 1, 1 / 32768, -32769 / 1, 65535 / 1, 1E10 / 1, 1E-64 / 1, 5.9 / 2.9, -5.9 / 2.9, 7 / .9, 7 / -.5, 12345.6 / 255.
- **[KOP OD XOR *x* *y*]** doubles: 2.5 / 1, -2.5 / 1, 2.7 / 3, -2.7 / 3, 32767.99999999 / 1, -32768.99999999 / 1, 32768 / 1, -32769 / 1, 65535 / 1, 5.9 / 2.9, -5.9 / 2.9, 7 / .99999999999999, 1D20 / 1, .49999999999999 / -.5.
- **[KOP FX *i*]**: fixed expressions (`FX` in the probe): for every ordered pair of AND, OR, XOR, EQV and IMP two
  three-operand chains (some of them give the same value under both groupings; FY adds rows that separate); NOT before each; each operator twice in a row; NOT against `=`,
  `<` and `+`; `-NOT 0`; MOD against `*`, `+`, unary minus and `\`; literal types (`&HFFFF`, `65535`, `7.9`, `2.5!`,
  `1#`); a string on either side and nothing after the operator, for each operator.
- **[KOP FY *i*]** (goldfish pass 1, 2026-11-24): expressions that SEPARATE the groupings FX could not -- `1<2 AND 1`, `1+2 AND 0`, `1=2 OR 3`, `1+2 XOR 3`, `1 EQV 2+3`, `1=1 IMP 1=0`, `6 OR 1 IMP 0`; MOD's own grouping (`100 MOD 7 MOD 3`) and its place against `/` and `^`; `-32768 MOD 5`; Overflow against Division by zero (`32768 MOD 0` ...); two bad operands (`70000 AND "A"`, `"A" AND 70000`, `"A" MOD 0`); NOT after `-`, `*` and `+`; twenty NOTs; `5 AND * 3`, `1 AND )`; and for each two-operand operator a right operand of -32769, 32768# and 1D20.

**Controls** ([`kops_controls.py`](../../probes/basic/spec/kops_controls.py)): each is a rival rule run over the
reference's cases: “operands rounded half away from zero (not truncated)” is FALSE on 20 of the 45 cases R-XOR-VALUE selects (e.g. KOP OS XOR 2.5 1); “operands floored (as INT)” is FALSE on 10 of the 45 cases R-XOR-VALUE selects (e.g. KOP OS XOR -2.5 1); “operands read as unsigned 16-bit (32768 .. 65535 accepted)” is FALSE on 6 of the 12 cases R-XOR-RANGE selects (e.g. KOP OS XOR 32768 1); “XOR tighter than AND” is FALSE on 4 of the 20 cases R-XOR-PREC selects (e.g. KOP FX 2).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/xor_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/xor_rules.py --write` -->

**5 rules; 5 hold on the reference. Of the 400 recorded outputs (each case's error from `R=<expr>` and from `Q=USR(<expr>)`, R's 8 bytes, the result's type as USR saw it and the result's own bytes): 400 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The value

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-XOR-VALUE** Each operand is made an integer by CINT's rule first -- the fraction dropped toward zero (2.7 -> 2, -2.7 -> -2, 32767.9 -> 32767, -32768.9 -> -32768) -- and then where it is set in exactly one; on 16 bits, two's complement. The result is an INTEGER in every case. | 45 | ✓ | ✓ |
| **R-XOR-RANGE** An operand whose truncated value is outside -32768..32767 -- 32768, -32769, 65535, 1E10, 1D20 -- is error 6 (Overflow), whichever side it is on. | 12 | ✓ | ✓ |

#### 2. Precedence and forms

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-XOR-PREC** In an expression the operators bind in this order, tightest first: `^`; unary minus; `*` `/`; `\`; MOD; `+` `-`; the comparisons; NOT; AND; OR; XOR; EQV; IMP -- each group left to right (XOR and EQV cannot be told apart: every grouping of the two agrees). So NOT 1+2 is NOT 3 (-4), NOT 1<2 is 0, 7 MOD 4+2 is 5, -7 MOD 4 is -3, 7\2 MOD 2 is 1; a minus may stand before NOT (-NOT 0 is 1). A literal's own type counts (&HFFFF the integer -1; 65535 a single: error 6). | 20 | ✓ | ✓ |
| **R-XOR-ERRORS** A string on either side is error 13 (Type mismatch) -- unless the left operand is out of range: it is made an integer as soon as the operator is met, so `70000 AND "A"` is error 6; nothing after the operator is error 24 (Missing operand); an operator or `)` where an operand belongs is error 2. | 3 | ✓ | ✓ |

#### 3. The result stored

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-XOR-ASSIGN** `R=x XOR y` with R a double stores the integer result by its value; after an error R keeps its sentinel -12345. Read in every case. | 80 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `XOR` uses the same amount of free
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
`XOR` shares its history with the other logical operators; the details are on
the [`AND`](AND.md#what-we-found-and-how) page. Two points are its own:

- **`XOR` and `EQV` have no observable order** (measured 2026-07-27). Both
  reduce to the same three-way bit operation, so `(x XOR y) EQV z` and
  `x XOR (y EQV z)` are equal for every x, y and z. zerobas places `EQV` one
  level looser only so the table reads in the manual's order; that choice
  cannot change any result:
  [logicops-vg8020-characterization.md](../logicops-vg8020-characterization.md) §3.
- **`PRINT "A" XOR 1` printed `A` and then `1`** instead of `Type mismatch`
  (fixed 2026-07-27): [spec-basic-relational-chain.md](../spec-basic-relational-chain.md).

## Where it lives

The operator-precedence loop in [basic/expr.asm](../../basic/expr.asm) looks
the token up in `cl_lvtab` ([basic/islands.asm](../../basic/islands.asm)); the leaf `lg_xor` does
the work.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make logicops-acceptance` — results, precedence and the integer range.
- `make kwsweep` — the everyday row (`5 XOR 3`), the error rows for
  {6, 13, 24}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
