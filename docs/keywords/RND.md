<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `RND` — a pseudo-random number

> **Spec:** DRAFT 1 (2026-11-24) — 556 steps measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`krnd.py`](../../probes/basic/spec/krnd.py)): every result's bytes and the generator's
> state after every step. Every rule is executable and every recorded output is read by one. Not yet reviewed
> ([the keyword plan](spec-plan.md)).
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. Three differences, found
> by the spec probe (below): entering a program line does not restart the
> sequence here, the bytes of a zero result, and the error of an unclosed call
> given a string.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`RND(x)` returns a pseudo-random number from 0 up to (but not including) 1,
with 14 significant digits. The numbers come from a fixed formula, so a
program can make the sequence repeat. zerobas produces **the same sequence,
digit for digit**, as the Philips VG-8020 -- in all 556 measured steps the
numbers agree -- and keeps the generator's state in the same 8 bytes the
reference does: the formula was worked out by watching the reference's
output, without reading its ROM.

## Syntax

```
RND(<numeric expression>)
```

One argument, always. What the argument does depends only on its sign.

## Details

- **A positive argument gives the next number.** Its value and type do not
  matter: `RND(1)`, `RND(7)`, `RND(.3)`, `RND(1E-64)` and `RND(1%)` all step the
  sequence once, identically.
- **`RND(0)` repeats the last number** without stepping.
- **A negative argument restarts the sequence** from a point chosen by the
  argument's digits, and returns the first number from there. The same
  argument always gives the same restart, so `RND(-1)` makes everything after
  it repeatable. Only the digits count, not the position of the decimal
  point: `RND(-1)`, `RND(-0.001)`, `RND(-1E9)` and `RND(&HFFFF)` restart at the
  same place. A single variable holding −1/3 (−.333333, 6 digits) and the double
  −1/3 (14 digits) have different digits, so they restart at different places.
- **The sequence restarts at its power-on start** after `RUN`, `NEW`, `CLEAR`
  and -- on the VG-8020 -- whenever a program line is typed or edited, so an
  unseeded program draws the same numbers every time it is run; `CLS` and
  `GOTO` do not restart it.
- **Two calls in one expression run left to right**: `RND(1)-RND(0)` is 0.
- **There is no `RANDOMIZE`** in MSX1 BASIC: the VG-8020 answers it with
  `Syntax error`. Use `RND(-x)` with a changing `x` instead.
- **A string argument** (`RND("A")`) is `Type mismatch` (error 13), and so is
  `R$=RND(1)` -- but there `RND` has already run, so the sequence has stepped.
- **No argument, two arguments, no parentheses or a missing `)`** —
  `RND()`, `RND(1,2)`, `PRINT RND`, `RND(1` — are all `Syntax error`
  (error 2), and the sequence is left untouched. An argument that fails on its
  own (`RND(1/0)`) raises its own error first, also untouched.

| you write | you get |
|---|---|
| `RND(1)<1` | −1 (true) |
| `INT(RND(-1)*10000)` | 438 |
| `RND(-1)=RND(-1)` | −1 (true) |
| `RND(1)-RND(0)` | 0 |
| `RND("A")` | error 13, `Type mismatch` |
| `RND()`, `RND(1,2)` | error 2, `Syntax error` |

The whole set of errors `RND` can raise is {2, 13} (and an argument's own
error), the same on both machines.

**The formula, for the curious.** The state is a 14-digit whole number S; a
positive argument replaces it by (21132486540519 × S + 14389820420821) mod
10^14, a negative one puts its own 14 digits in S's place first, and the number
returned is S / 10^14. At power-on S is 40649651372358. The rules below state it
exactly and check it against every measured step.

## Example

Line 30 shows that restarting with `RND(-1)` repeats the sequence, line 40
that `RND(0)` repeats the last number. MSX prints a true comparison as −1.

```
10 A=RND(-1):B=RND(1):C=RND(1)
20 D=RND(-1):E=RND(1):F=RND(1)
30 PRINT A=D;B=E;C=F
40 PRINT RND(0)=F
50 PRINT INT(RND(-1)*10000)
60 PRINT RND(1)<1
70 ON ERROR GOTO 100
80 PRINT RND("A")
90 END
100 PRINT "Error";ERR:RESUME NEXT
RUN
-1 -1 -1
-1
 438
-1
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_rnd.out`](../../scratchpad/kwdoc_rnd.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/rnd_rules.py`](../../probes/basic/spec/rnd_rules.py), model in
[`krnd_model.py`](../../probes/basic/spec/krnd_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**A sequence, not a function.** RND's result depends on what came before, so a case here is a STEP of a sequence,
and each record holds the generator's state AFTER the step as well as the step's result. The state is read from
`RNDX`, the 8 bytes at `$F857` that C-BIOS's source (admissible for published work-area addresses,
[allowed-sources.md](../allowed-sources.md)) names "last calculated random double"; the probe itself shows they are
the state (they step on every positive argument, stay on `RND(0)`, and a negative argument sets them whatever came
before). The rules predict in two ways, so no rule replays the reference's own output: **one step at a time**
(R-RND-NEXT, -REPEAT, -SEED ...: from the state the PREVIOUS record read), and **whole sequences** (R-RND-CHAIN:
from the start-up constant and the arguments alone, reading no measured state). The three constants -- A =
21132486540519, C = 14389820420821, S0 = 40649651372358 -- were recovered black-box in July 2026 from 19 values
([spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md) §15.1); here they predict 556 measured steps,
and changing the last digit of any one of them makes its rule false (controls, below).

**Evidence.** One probe, [`probes/basic/spec/krnd.py`](../../probes/basic/spec/krnd.py) (on the shared RAM-record
harness [`ramrec.py`](../../probes/basic/spec/ramrec.py) and the USR readout of
[`kmath.py`](../../probes/basic/spec/kmath.py)), typed on both machines, each group on a fresh boot; run file
[`scratchpad/KRN_run1.out`](../../scratchpad/KRN_run1.out) (2026-11-24; zerobas's side on that day's build). A step
either assigns `R=RND(N)` -- R a double whose 8 bytes are recorded -- or evaluates `Q=USR(RND(N))`, where `USR` is
the probe's own 18-byte routine that copies `VALTYP` and `DAC` (the result unconverted, by the convention
[USR.md](USR.md) documents) into the probe's memory, so the result's TYPE is seen. Before every step R holds -12345
and the type cell 255. An argument is `READ` into a variable of the step's own type (`N%`, `N!`, `N#`) whose bytes
are recorded before the call and checked against the `DATA` text; apparatus rows (`Q=USR(N)`, no RND) check the
USR readout on each type, or the loader refuses the run. Only the probe's own memory and RNDX are PEEKed.
- **[KRN BOOT *i*]**: DIRECT MODE from power-on, before any program line: RNDX at power-on, `RND(0)`, `RND(1)`
  twice, `CLS`, `RND(1)`, then `10 REM` typed, `RND(1)`, `CLEAR`, `RND(1)`, `RND(-1)`, `NEW`, `RND(1)`, `RND(-5)`,
  `20 REM` and `RUN`, `RND(1)` twice.
- **[KRN RUNR *i*]**, **[KRN GOTO *i*]**, **[KRN GOTO2 *i*]**: a typed program; `RND(1)` twice and `RND(-7)` from
  direct mode; then `RUN` (RUNR), `GOTO 5` (GOTO), or `99 REM` typed and then `GOTO 5` (GOTO2). The program
  records the state at its first line, `RND(1)`, `RND(0)`, then the state after `CLEAR 2000,&HBF00` and `RND(1)`.
- **[KRN SQ1 *i*]**: after `CLEAR`: positive arguments of every type (1, 7, 32767 integers; 1, .3, 1E-64,
  9.99999E62 singles; 1, .5, 1D-64, 9.9999999999999D62, 12345.678901234 doubles) as `R=` and as `USR` steps; zero
  arguments (0%, 0!, -0!, 0#, -0#); other maths between (SIN, EXP, SQR, LOG, ATN, INT, ABS, STR$, HEX$); RND(1) 20
  more times.
- **[KRN SQ2 *i*]**: 46 reseeds, each followed by `RND(1)`, `USR(RND(1))` and `RND(0)`. Integers -1, -2, -5, -10,
  -100, -12345, -32767, -32768, -3; singles -1, -.001, -1E9, -.333333, -.5, -5, -1E-64, -9.99999E62, -123456,
  -.000001, -7, -.304949, -3, -.3; doubles -1, -1D-64, -1D62, -9.9999999999999D62, -.33333333333333,
  -.12345678901234, -12345678901234, -.5, -.99999999999999, -7, -1.0000000000001, -3, -.3, and ten chosen by
  inverting the recurrence so that the sequence passes through the states 0, 1, 10, 12345, 10^13 - 1, 10^13,
  99999999999999, 50000000000000 (the reseed's own result), 12300000000000 (one `RND(1)` later) and
  01000000000000 (two later): results with leading zero digits, trailing zeros, and none at all.
- **[KRN SQ3 *i*]**: `RND(-1)`, then 200 steps of `RND(1)` with `RND(0)` every 25.
- **[KRN FX *i*]**: 61 fixed statements, one a step, the state flowing through them (`FX` in the probe): every
  error form (none may move the state), spaces, literals (with apparatus rows measuring each literal's own type),
  `RND(RND(1))`, `RND(-RND(1))`, `RND(1)-RND(0)` and `RND(0)-RND(1)`, the result's type through USR for each
  argument type, singles and doubles whose exponent byte is POKEd to 0 or `&H80`, and the state 0.

**Controls** ([`krnd_controls.py`](../../probes/basic/spec/krnd_controls.py)): each is a rival rule run over the
reference's cases, and each is FALSE on some: A's last digit changed (FALSE on 360 of 362 steps), C's (362 of 362),
S0's (119 of 556); a positive argument that reseeds from its own digits (361); `RND(0)` that steps (76 of 76); the
reseed taken from the argument's VALUE (the exponent counting: 42 of 60), an integer's digits right-aligned (15), a
single's digits repeated instead of followed by zeros (17); an exponent-0 number with the sign bit taken as zero (2
of 4); right-to-left evaluation (2 of 2); the result not normalised (66 of 413); a zero result keeping digit bytes
-- zerobas's (5); RNDX holding the normalised result instead of the state (549 of 556); the result in the
argument's type (20 of 94); a program line, RUN, CLEAR or NEW that keeps the state (2 / 1 / 4 / 1 of 12); the
string target refused before RND runs (1 of 1); the type checked before the `)` -- zerobas's (2 of 3).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/rnd_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/rnd_rules.py --write` -->

**18 rules; 18 hold on the reference. Of the 2780 recorded outputs (each step's error, R's 8 bytes, the result's type and own bytes as USR saw them, and RNDX's 8 bytes after the step): 2780 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The generator

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-RND-CELL** The state is a 14-digit number S held in RNDX ($F857, 8 bytes; C-BIOS's source names the address): byte 0 is 00 and bytes 1-7 are S's 14 digits in packed BCD, the most significant first, leading zeros kept (S = 1 is 00 00 00 00 00 00 00 01). Read after every step. | 556 | ✓ | ✓ |
| **R-RND-NEXT** A positive argument -- any type, any value: 1, 7, 32767, .3, .5, 1E-64, 9.99999E62, 9.9999999999999D62, a nested RND(1) -- steps the state once: S' = (21132486540519 * S + 14389820420821) mod 10^14, S the state RNDX held before the call; the argument's value plays no part. | 362 | ✓ | ✓ |
| **R-RND-REPEAT** A zero argument (0%, 0!, -0!, 0#, -0#, the literals 0 and -0) leaves the state as it is, and RND returns the last number again. | 76 | ✓ | ✗ 2: KRN FX 57, KRN FX 58 |
| **R-RND-SEED** A negative argument sets the state from its own digits, whatever the state was: S' = (21132486540519 * m + 14389820420821) mod 10^14, m the argument's 14 mantissa digits -- a double's 14, a single's 6 followed by 8 zeros, an integer's decimal digits left-aligned (-12345% gives m = 12345000000000). Neither the exponent nor the sign counts: RND(-1), RND(-.001), RND(-1E9), RND(-1D-64) and RND(&HFFFF) restart at the same place; -.333333! and -.33333333333333# at different ones. | 60 | ✓ | ✗ 3: KRN SQ2 121, KRN FX 54, KRN FX 56 |
| **R-RND-SIGN** What counts as negative is the sign BIT: a single 80 10 00 00 or a double 80 12 34 56 78 90 12 34 (exponent byte &H80) reseeds from its digit bytes (10 00 00 ..., 12 34 56 78 90 12 34); without the sign bit an exponent byte of 0 is a zero (00 10 00 00 and 00 12 34 ... repeat the last number). | 4 | ✓ | ✓ |
| **R-RND-NESTED** An RND inside RND's argument runs first, and the outer call takes its result as any other argument: RND(RND(1)) steps twice, RND(RND(0)) once, and RND(-RND(1)) reseeds from the digits of the number RND(1) returned (normalised, R-RND-VALUE); RND(-RND(0)) in state 0 is RND(-0), which repeats the 0. | 5 | ✓ | ✗ 1: KRN FX 59 |
| **R-RND-ORDER** Two calls in one expression run left to right: RND(1)-RND(0) is exactly 0 (8 zero bytes) and steps once; RND(0)-RND(1) is the old number minus the new one, exactly. | 2 | ✓ | ✓ |
| **R-RND-CHAIN** Every group's whole sequence -- each result's bytes and each RNDX -- follows from the start-up state 40649651372358 and the arguments alone, by R-RND-NEXT, R-RND-REPEAT, R-RND-SEED and R-RND-START, reading no measured state (SQ3: RND(-1) then 200 steps of RND(1)). | 556 | ✓ | ✗ 8: KRN SQ2 121, KRN FX 13, KRN FX 14, KRN FX 54, KRN FX 56, KRN FX 57 … (+2) |

#### 2. The result

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-RND-VALUE** The number returned is S / 10^14 as a DOUBLE, normalised: S's 14 digits shifted left past their leading zeros, the exponent byte &H40 minus the count (S = 4389820420821 is .04389820420821, 3F 43 89 82 04 20 82 10; S = 1 is 1E-14, 33 10 00 ...); S = 0 gives 8 zero bytes. Read on every step that assigns R. | 413 | ✓ | ✗ 5: KRN SQ2 121, KRN FX 54, KRN FX 56, KRN FX 57, KRN FX 59 |
| **R-RND-TYPE** The result is always a double, whatever the argument's type (USR sees VALTYP 8 and the same 8 bytes R-RND-VALUE gives): RND(1%), RND(1!), RND(1#), RND(0), RND(-1), RND(0) in state 0 (8 zero bytes). | 94 | ✓ | ✗ 1: KRN FX 58 |
| **R-RND-ASSIGN** `R=RND(x)` with R a double stores the result's 8 bytes; a step that assigns nothing (an error, `Q=USR(...)`, another statement) leaves R's sentinel -12345. Read in every case. | 556 | ✓ | ✗ 5: KRN SQ2 121, KRN FX 54, KRN FX 56, KRN FX 57, KRN FX 59 |

#### 3. Start-up and resets

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-RND-START** At power-on RNDX holds 00 40 64 96 51 37 23 58: S0 = 40649651372358, so the first RND(1) is .59521943994623 and RND(0) before it .40649651372358. CLEAR (with or without arguments), NEW, RUN and ENTERING A PROGRAM LINE (`10 REM` typed in direct mode) each put S0 back; CLS and GOTO do not. | 12 | ✓ | ✓ |
| **R-RND-OTHER** Statements that do not call RND leave the state alone: other maths (SIN, EXP, SQR, LOG, ATN, INT, ABS, STR$, HEX$), READ, POKE, VARPTR, USR of a number, an error. | 16 | ✓ | ✓ |

#### 4. Forms, errors and literals

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-RND-ERR** A string argument (`RND("A")`, `RND(S$)`) is error 13; no argument, an extra one (also after a negative first), no `)` (also after a negative first), the name alone, and `RANDOMIZE 1` (not MSX1 BASIC) are error 2; `RND(1/0)` and `RND(-1/0)` raise the argument's own 11. None of them assigns R or moves the state. | 11 | ✓ | ✓ |
| **R-RND-CHECKS** The argument is worked out first, the `)` checked next, the type last: `RND(1/0` (no `)`) is error 11; `RND("A"` and `RND("A",2)` are error 2, not 13. | 3 | ✓ | ✗ 2: KRN FX 13, KRN FX 14 |
| **R-RND-STRTARGET** `R$=RND(1)` is error 13 -- but RND has already run: the state steps, and R is not assigned. | 1 | ✓ | ✓ |
| **R-RND-FORMS** A space before the parenthesis and spaces around the argument are allowed; a literal's own type is the argument's (R-RND-LIT), and each form does what R-RND-NEXT / -REPEAT / -SEED say for it. | 10 | ✓ | ✓ |
| **R-RND-LIT** The literals' own types (apparatus, `Q=USR(x)` with no RND): -1 and &HFFFF the integer -1, &H8000 the integer -32768, -.001 / -1E9 / -32768 singles, -1/3 AND -1!/3 doubles (c0 33 33 33 33 33 33 33: `/` gives a double even from a single). | 8 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

- **A zero result's bytes** ([D-RNDZERO](../../todo/open/D-RNDZERO.md)). In the one state that is 0, the
  reference returns 8 zero bytes; zerobas returns exponent 0 with leftover digit bytes (the reseed's argument
  digits, or other scratch). The value is 0 on both and RNDX agrees (R-RND-VALUE, -SEED, -REPEAT, -TYPE, -NESTED;
  KRN SQ2 121, FX 54-59).
- **`RND("A"` and `RND("A",2)` are error 13 here, 2 on the reference** ([D-ARGTYPEORDER](../../todo/open/D-ARGTYPEORDER.md),
  shared with the other maths functions): the reference requires the `)` before it refuses a string (R-RND-CHECKS,
  KRN FX 13-14).

Everything else agrees byte for byte, RNDX included, in all 556 steps.

The one rung not yet proven is **RAM usage**: `RND` uses the same amount of
free memory on both machines, and its state lives at the same address as the
reference's (RNDX, byte for byte), but the two still write different work-area
cells along the way — the VG-8020 a few that zerobas does not, and zerobas a few
of its own.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Power-on was measured once a group, under the harness's own start (`SCREEN 0:WIDTH 40` typed first); that
  no other start-up path (a disk boot, a cartridge) leaves another state is assumed.
- [A] Whether `LOAD`, `MERGE`, `CLOAD`, `DELETE`, `RENUM`, `CHAIN`-like paths, or an error stop reset the state (only
  CLEAR, NEW, RUN, a typed line, CLS and GOTO were measured).
- [A] Which work-area cells the call writes besides RNDX (the RAM-usage rung).
- [A] Non-canonical arguments other than the four measured (a single or double whose exponent byte is 0 or `&H80`,
  digit bytes `10 00 00` or `12 34 56 78 90 12 34`): non-BCD digit nibbles; `&H80` with zero digit bytes.
- [A] A result inside a larger expression other than `RND(1)-RND(0)` / `RND(0)-RND(1)` and the nested calls; a
  result stored in a single or an integer variable (the conversion region, [CSNG](CSNG.md), [CINT](CINT.md)).
- [A] The zero result (state 0) used in arithmetic, `STR$` or a comparison on either machine.
- [A] RNDX written by the program (POKE) before an RND: whether the generator reads it back as the state.

## What we found, and how

- **The spec probe** (D-KWSPEC, 2026-11-24): the July generator predicts all 556 measured steps on the VG-8020, one
  at a time and as whole sequences; and three new facts, each a rule now. Entering a program line restarts the
  sequence on the reference (zerobas too since D-RNDLINE's fix, 2026-11-24). `R$=RND(1)` steps the sequence before it reports `Type
  mismatch`. A single whose exponent byte is `&H80` (a zero with its sign bit set) RESEEDS from its digit bytes, while
  one with exponent byte 0 is a zero -- the sign bit decides, as for `SGN`. The zero result's bytes differ
  (D-RNDZERO), and `RND("A"` shares D-ARGTYPEORDER.
- **The generator was recovered from the outside** (2026-07-14). Capturing
  consecutive values, restarts and edge cases on the VG-8020 was enough to
  pin down the formula and its three constants exactly; zerobas reproduces
  every captured value, and the tests compare whole sequences digit for digit
  ([spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md) §15).
- **A malformed call changed the sequence** (fixed 2026-07-14, D-F2-4).
  `RND(1.5,2)` stepped the sequence and `RND(-1.5` (missing `)`) restarted it,
  so every later number was different — where the VG-8020 stops with
  `Syntax error` and leaves the sequence alone. Now zerobas does the same
  ([spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md)).
- **A test that only checked the range could not see the sequence**
  (D-KWBREADTH, 2026-09-13). `RND(1)<1` is true for any working generator. A
  row reading `INT(RND(-1)*10000)` — 438 on the VG-8020, on the CF-3300 and on
  zerobas — now checks the generator itself.
- **The state moved to the reference's own address** (D-ADDR29, 2026-09-25).
  MSX publishes the address of `RNDX`, where the generator keeps its state.
  Joost ruled on 2026-09-24 to rehome the published variables, *"`RNDX` now"*
  among them. In seven different states zerobas's bytes then matched the
  VG-8020's at that address every time
  ([spec-basic-addr29.md](../spec-basic-addr29.md),
  [`rndx_after.out`](../../scratchpad/rndx_after.out)).
- **The whole error set was measured on the reference** (D-KWT6, 2026-09-27):
  wrong type, no argument and an extra argument; zerobas matched every case
  ([`t6enum_b5.out`](../../scratchpad/t6enum_b5.out)).

## Where it lives

- Main ROM: dispatched by `evmc_total_scan` in
  [basic/expr.asm](../../basic/expr.asm) through `evmc_total_tab` in
  [basic/islands.asm](../../basic/islands.asm). `clear_vars` in
  [basic/vars.asm](../../basic/vars.asm) resets the state on `RUN`, `NEW` and
  `CLEAR`.
- Sub-ROM: `fp_rnd` in [sub/fp_rnd.asm](../../sub/fp_rnd.asm) steps,
  restarts or repeats the sequence.

## Tests that cover it

- `make math-acceptance` — whole sequences compared digit for digit with the
  VG-8020: from power-on, after restarts, `RND(0)`, positive arguments of
  different values, and the reset by `NEW`, `CLEAR` and `RUN`; plus the
  malformed calls, with a check that they leave the sequence alone.
- `make kwsweep` — the rows `RND(1)<1` and `INT(RND(-1)*10000)`, the error
  rows for {2, 13}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
