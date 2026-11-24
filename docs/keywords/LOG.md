<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `LOG` — the natural logarithm of a number

> **Spec:** DRAFT 1 (2026-11-24) — 321 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`ktrans.py`](../../probes/basic/spec/ktrans.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
> Goldfish pass 1 (test writer) 2026-11-24: 6 findings, 0 measured, 1 moved to open (new cases: KTR TS3, TD3, FY).
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference, deliberate: the last printed digits of some results (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`LOG(x)` returns the natural logarithm of `x` (base e), which must be greater
than 0. It is the inverse of [`EXP`](EXP.md): `LOG(1)` is 0. The answer has 14
significant digits. zerobas raises the same errors as the Philips VG-8020 in
every case we have measured; the last digits of a result can differ, because
neither machine is exact there and zerobas's own calculation is closer to the
true value.

## Syntax

```
LOG(<numeric expression>)
```

One argument, always. For a logarithm in another base, divide:
`LOG(x)/LOG(10)`.

## Details

- **`LOG(1)` is exactly 0**, on both machines, and the result is always double precision.
- **Zero or a negative argument** is `Illegal function call` (error 5):
  `LOG(0)` and `LOG(-1)` both.
- **A string argument** (`LOG("A")`) is `Type mismatch` (error 13).
- **No argument, two arguments, no parentheses or a missing `)`** —
  `LOG()`, `LOG(1,2)`, `PRINT LOG`, `LOG(1` — are all `Syntax error`
  (error 2).

| you write | you get |
|---|---|
| `LOG(1)` | 0 |
| `LOG(0)`, `LOG(-1)` | error 5, `Illegal function call` |
| `LOG("A")` | error 13, `Type mismatch` |
| `LOG()`, `LOG(1,2)` | error 2, `Syntax error` |

The whole set of errors `LOG` can raise is {2, 5, 13}, the same on both
machines.

## Example

```
10 PRINT LOG(1);INT(LOG(10)*1000)
20 ON ERROR GOTO 60
30 PRINT LOG(0)
40 PRINT LOG(-1)
50 END
60 PRINT "Error";ERR:RESUME NEXT
RUN
 0  2302
Error 5
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_log.out`](../../scratchpad/kwdoc_log.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/log_rules.py`](../../probes/basic/spec/log_rules.py), model in
[`ktrans_model.py`](../../probes/basic/spec/ktrans_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Bounds, not digits.** `LOG`'s last digits are the reference's own approximation. Where a rule says "within B
units", the target is computed exactly (to 60 digits and more, in Python, from the argument's own bytes) and a unit is
one in the 14th significant digit of the target; B is the worst error MEASURED on the VG-8020, rounded up to a whole unit (the measured
worst is in the sentence), and a control with a bound just below that worst is FALSE, so the bound cannot be tightened past the measured worst. Whether zerobas's digits equal the
reference's byte for byte is a separate observation, under *Differences*: a zerobas result inside the bound agrees
with the rule even where its digits differ.

**Evidence.** One probe, [`probes/basic/spec/ktrans.py`](../../probes/basic/spec/ktrans.py) (the maths region's
second, on the shared RAM-record harness [`ramrec.py`](../../probes/basic/spec/ramrec.py) and the frame of
[`kmath.py`](../../probes/basic/spec/kmath.py)), typed on both machines; run file
[`scratchpad/KTR_run1.out`](../../scratchpad/KTR_run1.out) (2026-11-24, all groups; zerobas's side on that day's build). The
argument is `READ` into a variable of the case's own type (`N%`, `N!` or `N#`) and that variable's own bytes are
recorded before the call. Each case is evaluated twice: `R=LOG(N)`, with `R` a double whose 8 bytes are recorded,
and `Q=USR(LOG(N))`, where `USR` is the probe's own 18-byte routine (POKEd above `CLEAR`'s limit) that copies
`VALTYP` and `DAC` -- `LOG`'s result unconverted, by the convention [USR.md](USR.md) documents -- into the probe's
memory, so the result's TYPE and its own bytes are seen. Before every case `R` holds -12345 and the type cell 255, so
an error cannot read as a result; an apparatus row per argument (`R=N`, `Q=USR(N)`) must give back the argument's own
type and bytes on both machines, or the loader refuses the run.
- **[KTR TI LOG *n*]** (integers), **[KTR TS1 / TS2 LOG *n*]** (singles), **[KTR TD1 / TD2 LOG *n*]** (doubles),
  *n* the `DATA` text. Integers: 0, 1, -1, 2, -2, 3, -3, 4, 5, -5, 7, 10, -10, 20, -20, 50, -50, 100, -100, 145, 146, -147, -148, -149, -150, -200, -297, -298, 1000, -1000, 12345, 32767, -32768. Singles: 0, -0, 1E-64, -1E-64, 1E-20, 1E-10, -1E-10, 1E-6, -1E-6, .001, -.001, .01, .1, -.1, .2, .25, .5, -.5, .693147, .7, .75, .9, .999999, 1, -1, 1.00001, 1.5, -1.5, 2, -2, 2.5, -2.5, 2.71828, 3, 5, 10, -10, 20, -20, 50, -50, 99, 100, -100, 145.062, 145.063, -147.3, -147.4, -149.66, -149.67, -297.03, -297.04, -1000, 1000, 12345.6, 99999.9, .785398, -.785398, 1.0472, .523599, 1.5708, -1.5708, 1.57079, 3.14159, -3.14159, 3.1416, 4.71239, 6.28318, 6.28319, 7, 10.5, 100.5, 1E5, 123456, 1E6, -1E6, 1E10, 1E12, 1E13, 5E13, 7E13, 1E14, 1E20, 1E38, -1E38, 9.99999E62, -9.99999E62, 1.23456E-5, 3.33333, .333333, -.333333, 4, 8, 16, 64, .0625, 1E30, -1E30, 1E-30, 1E-63, 1.73205, .57735, -.57735, -40000, -65535, -65536, -99999, -1E5, -999999. Doubles:
  0, -0, 1D-64, -1D-64, 1D-14, -1D-14, 1D-10, 1D-7, .001, -.001, .1, -.1, .5, -.5, .69314718055995, 1.0000000000001, .99999999999999, 1, -1, 2, -2, 2.302585092994, 2.718281828459, 2.7182818284590, 10, -10, 1.2345678901234, -1.2345678901234, 12.345678901234, 50, -50, 100, -100, 145.06286, 145.0628, 145.063, -147.3, -147.4, -149.668, -149.67, -297.033, -297.04, -1000, 1000, 1D10, 1D20, 1D-20, 9.9999999999999D62, -9.9999999999999D62, 32767.9, 123456789.01234, .78539816339745, -.78539816339745, .78539816339744, 1.0471975511966, .5235987755983, 1.5707963267949, -1.5707963267949, 1.5707963267948, 3.1415926535898, -3.1415926535898, 3.1415926535897, 4.7123889803847, 6.2831853071796, -6.2831853071796, 12.566370614359, 1000, -1000, 1D10, -1D10, 1D11, 1D12, 1D13, 7D13, 1D14, 1D38, 1.7320508075689, .57735026918963, -.57735026918963, 1D-5, -1D-5, .12345678901234, -.12345678901234, 1234.5678901234, 31415.926535898, 100, 3.3333333333333, 1D30, -1D30, 1D-30.
- **[KTR FX *i*]**: a fixed statement, `S$` = `"12"`; the list, with what each one separates, is `FX` in the probe:
  a string literal or variable as the argument, the result assigned to `R$`, `1/0`, no argument, an extra one, no
  `)`, no parenthesis; the literals `2.5`, `-2.5`, `7`, `7%`, `2.5!`, `2.5#`, `&H8000`, `-32768`, `-0`, `1/4`;
  spaces; `LOG(LOG(.5))`; and a single `N!` assigned 1 whose exponent byte is then POKEd to 0 or `&H80`
  (digit bytes `10 00 00`).
- **[KTR TS3 LOG *n*]** (singles) and **[KTR TD3 LOG *n*]** (doubles), added by the goldfish pass to separate rival rules the first run could not tell apart: the angles where p has 13 integer digits, ties in p, p just below and above 1E-64, EXP's edges and its huge-negative threshold. Singles: 6E12, 7E12, -7E12, 9E12, 1.1E13, -1.1E13, 1.2E13, 1.3E13, -1.3E13, 1.5E13, -1.5E13, 1.7E13, 3E13, 6.3E13, 1.75, 2.75, 7.5, -7.5, 9.5, 13.5, 5E-64, -5E-64, 6E-64, 6.28318E-64, 6.28319E-64, -6.28319E-64, 7E-64, -65536.5, -65537, -70000, -80000, -90000, -99990, -99998, -75000, -75450, -75451, -75452, -75453, -76000, -75460, -75500, -75600, -75700, -75800, -75900. Doubles: -147.36, -147.365, -147.3654, -147.3655, -147.36544595, -147.36544596, -147.366, 145.06286085, 145.06286086, 145.0628609, 145.06287, 145.0629, 1.1D13, -1.1D13, 1.3D13, 1.5D13, 6.2831D-64, 6.2832D-64.
- **[KTR FY *i*]**: fixed statements that USE a non-canonical result (SIN(0), COS(7E13), TAN(1E13), EXP(-147.4), ATN of the single `80 10 00 00`) -- in `STR$` (PRINT's number format; its length and first bytes are recorded), `=0`, `<0`, `+1`, `*1E10`, negated, assigned to a single `Z!` and an integer `Z%` (read back through `USR`) -- and the non-canonical single `00 12 34 56` / `80 12 34 56` as the argument; `FY` in the probe.

**Controls** ([`ktrans_controls.py`](../../probes/basic/spec/ktrans_controls.py)): each is a rival rule run over the reference's cases: “within 5 units (this page before 2026-11-24)” is FALSE on 3 of the 180 cases it selects (e.g. KTR TD1 LOG 2.718281828459); “within 8 units” is FALSE on 1 of the 180 cases it selects (e.g. KTR TD2 LOG .5235987755983); “correctly rounded” is FALSE on 106 of the 180 cases it selects (e.g. KTR TI LOG 2).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/log_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/log_rules.py --write` -->

**10 rules; 10 hold on the reference. Of the 1607 recorded outputs (each case's error from `R=F(x)` and from `Q=USR(F(x))`, R's 8 bytes, the result's type as USR saw it and the result's own bytes): 1607 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. LOG(x)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-LOG-DOMAIN** Zero or a negative argument is error 5 (Illegal function call), in every type and size (0, -0, -1E-64, -9.99999E62) -- also a single whose exponent byte is 0 or &H80 (a zero, signed or not). | 129 | ✓ | ✓ |
| **R-LOG-ONE** LOG(1) is exactly 0: 8 zero bytes, a double. | 3 | ✓ | ✓ |
| **R-LOG-NEAR** Any other positive argument gives a DOUBLE within 9 units of the 14th significant digit of ln x -- measured worst 8.3 (LOG(.5235987755983#)), the next 7.3 (LOG(2.718281828459#)); LOG(2) 1.5 units low, LOG(1D-64) and LOG(9.99999E62) within 0.5. | 180 | ✓ | ✓ |
| **R-LOG-ODDBYTES** On a non-canonical single (exponent byte 0 or &H80, digit bytes 10 00 00 or 12 34 56) it gives what the rules above say for a zero argument. | 4 | ✓ | ✓ |
| **R-LOG-NESTED** LOG(LOG(.5)) is LOG of the double that LOG(.5) returns (the KTR TS1 row): what the rules above say for that double -- error 5, LOG(.5) being negative. | 1 | ✓ | ✓ |

#### 2. LOG(x): forms, errors and assignment

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-LOG-TYPE** A string as the argument (a literal or a variable) is error 13 (Type mismatch), and so is assigning the result to a string variable: the result is a number. | 3 | ✓ | ✓ |
| **R-LOG-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-LOG-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error). | 4 | ✓ | ✓ |
| **R-LOG-FORMS** Spaces before the parenthesis and around the argument are allowed, and a literal's own type is the argument's (2.5 a single, 7 an integer, &H8000 the integer -32768, -32768 a single, -0 the integer 0, 1/4 a double); each gives what the rules above say for that value. | 12 | ✓ | ✓ |
| **R-LOG-ASSIGN** `R=LOG(x)` with R a double stores the result's 8 bytes as they are (a zero's digit bytes included), and an error stores nothing (R keeps its sentinel). Read in every case. | 321 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

- **The last digits of a result can differ.** The VG-8020's `LOG` is within 8.3 units of the 14th digit of ln x over
  the 180 positive arguments measured (R-LOG-NEAR, bound 9; this page said "up to 5 units" before 2026-11-24 -- a
  control shows 5 is false on 3 cases, and 8 on 1), zerobas within 1.69 (LOG(1.00001!); an observation,
  `ktrans_controls.py --zb`, not a rule). zerobas uses its own calculation, never the reference's;
  reproducing the reference's digits would need its internal constants, which can only be read from its ROM --
  something this project does not do. The approach — be accurate and record the difference rather than imitate —
  was signed off by Joost on 2026-07-13 ([spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md) §2).
  Every LOG rule holds on zerobas.

The one rung not yet proven is **RAM usage**: `LOG` uses the same amount of free memory on both machines, but the two write different work-area cells along the way — the VG-8020 a few that zerobas does not, and zerobas some scratch cells of its own for the calculation.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] An argument's own error was measured with one kind (`1/0`, error 11); that any error of the argument wins is assumed.
- [A] Which work-area cells the call writes (the RAM-usage rung).
- [A] Non-canonical bytes other than the four measured singles (exponent byte 0 or `&H80` with digit bytes `10 00 00`
  or `12 34 56`: all error 5).
- [A] Whether the reference's error is ever more than 9 units: 180 results measured; the bound is the measured
  worst (8.27) rounded up.
- [A] LOG's result assigned to a single or an integer, or used inside a larger expression (only `R=LOG(x)` and
  `USR(LOG(x))` were measured). LOG's one zero result, LOG(1), is the canonical 8 zero bytes, so the non-canonical
  zeros the other pages measure in use (KTR FY) do not arise here.

## What we found, and how

- **Goldfish pass 1** (2026-11-24, a fresh test-writer review of the six pages): the bound is now 9 (the measured
  worst 8.27 rounded up to a whole unit, with a control at 8), not 10; zerobas's own accuracy is quoted from a
  committed readout; the non-canonical singles 00 12 34 56 and 80 12 34 56 are error 5 too.
- **The transcendentals' rules are bounds, measured** (2026-11-24, D-KWSPEC's maths region, second unit). LOG is a double always, LOG(1) exactly 0 (8 zero bytes), error 5 for 0, -0 and every negative (also a zero whose sign bit is set); the VG-8020 is within 8.3 units of the 14th digit, not 5.
- **`LOG()` gave the wrong error** (fixed 2026-07-14, D-F2-4). Empty, bare
  (`PRINT LOG`) or two-argument calls answered `Illegal function call`: the
  domain check ran on a left-over value before anything noticed the call was
  malformed. The VG-8020 says `Syntax error`, and so does zerobas now
  ([spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md)).
- **The format's far corners were measured** (2026-09-05, with D-EXPBAND):
  `LOG(1E-64)` and `LOG(9.9E62)`, the smallest and largest numbers MSX can
  hold, are handled the same way on both references, and are now test rows.
- **The whole error set was measured on the reference** (D-KWT6, 2026-09-27):
  wrong type, no argument, an extra argument, `LOG(0)` and `LOG(-1)`; zerobas
  matched every case ([`t6enum_run.out`](../../scratchpad/t6enum_run.out)).

## Where it lives

- Main ROM: `evmc_log` in [basic/expr.asm](../../basic/expr.asm) reads the
  argument and rejects zero and negative values before anything is computed.
- Sub-ROM: `fp_log` in [sub/fp_log.asm](../../sub/fp_log.asm) does the
  calculation, with this project's own polynomial.
- The design notes are in
  [spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md) §12.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make math-acceptance` — values against the mathematically true answer, the
  range corners, the domain error, and the empty and malformed calls.
- `make kwsweep` — the everyday row (`LOG(1)`), the error rows for {2, 5, 13},
  and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
