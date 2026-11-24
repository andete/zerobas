<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `ABS` — the absolute value of a number

> **Spec:** DRAFT 1 (2026-11-24) — 172 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kmath.py`](../../probes/basic/spec/kmath.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
> Goldfish pass 1 (test writer) 2026-11-24: 11 findings, 9 measured (or checked on the run), 0 moved to open; 2 were wording.
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. Three differences
> found by the spec probe: two invisible to PRINT, one the error code of a
> malformed call (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`ABS(x)` returns `x` without its sign: `ABS(-5)` is 5, `ABS(5)` is 5. It works
on every numeric type and over the whole number range. zerobas gives the same
value and the same errors as the Philips VG-8020 in every case we have measured,
with two exceptions (below): the result's type at one edge, and the error of a
call that is both unclosed and given a string.

## Syntax

```
ABS(<numeric expression>)
```

One argument, always.

## Details

- **The result keeps the argument's type.** `ABS(-1.5)` is 1.5, `ABS` of a
  double-precision value is double precision, and so on.
- **One integer has no positive twin.** An integer (`A%`) runs from −32768 to
  32767, so `ABS` of an integer −32768 cannot stay an integer: the answer,
  32768, comes back as a single-precision number on the reference, and as a
  double here (see *Differences*; the value is the same).
- **Only the sign changes.** A single or double keeps every digit: `ABS` clears
  the sign bit and nothing else, from 1E-64 to 9.99999E62.
- **No range errors.** `ABS(-1E38)` is the single 1E38 on both machines; only the
  type and the shape of the call can go wrong. Stored in an integer variable,
  `T%=ABS(&H8000)` is `Overflow` (error 6), as any 32768 would be.
- **A space before the parenthesis is allowed**: `ABS (-7)` is 7.
- **A string argument** (`ABS("A")`) is `Type mismatch` (error 13).
- **No argument, two arguments, no parentheses or a missing `)`** —
  `ABS()`, `ABS(1,2)`, `PRINT ABS`, `ABS(5` — are all `Syntax error`
  (error 2).
- **The argument is worked out first, the `)` checked next, the type last.**
  `ABS(1/0` (no `)`) is `Division by zero` (error 11), but `ABS("A"` and
  `ABS("A",2)` are `Syntax error` on the VG-8020 -- and `Type mismatch` here
  (see *Differences*).

| you write | you get |
|---|---|
| `ABS(-5)`, `ABS(5)` | 5 |
| `ABS(-1.5)` | 1.5 |
| `A%=-32768:PRINT ABS(A%)` | 32768 |
| `ABS(-1E38)` | no error |
| `ABS("A")` | error 13, `Type mismatch` |
| `ABS()`, `ABS(1,2)` | error 2, `Syntax error` |

The whole set of errors `ABS` can raise is {2, 13}, the same on both machines.

## Example

```
10 PRINT ABS(-5);ABS(3.5);ABS(0)
20 A%=-32768:PRINT ABS(A%)
30 PRINT ABS (-7)
40 ON ERROR GOTO 70
50 PRINT ABS("A")
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
 5  3.5  0
 32768
 7
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_abs.out`](../../scratchpad/kwdoc_abs.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/abs_rules.py`](../../probes/basic/spec/abs_rules.py), model in
[`kmath_model.py`](../../probes/basic/spec/kmath_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/kmath.py`](../../probes/basic/spec/kmath.py) (the maths region's first,
on the shared RAM-record harness [`ramrec.py`](../../probes/basic/spec/ramrec.py)), typed on both machines; run file
[`scratchpad/KMA_run1.out`](../../scratchpad/KMA_run1.out) (2026-11-24; zerobas's side on that day's build). The
argument is `READ` into a variable of the case's own type (`N%`, `N!` or `N#`) and that variable's own bytes are
recorded before the call, so the rules work from the exact value given. Each case is evaluated twice: `R=ABS(N)`,
with `R` a double whose 8 bytes are recorded, and `Q=USR(ABS(N))`, where `USR` is the probe's own 18-byte routine
(POKEd above `CLEAR`'s limit): by the MSX convention ([USR.md](USR.md)) it receives `ABS`'s result unconverted
in `DAC` with its type in `VALTYP`, and copies both into the probe's memory -- so the result's TYPE (2 integer, 4
single, 8 double) and its own bytes are seen, not only its value. Before every case `R` holds -12345 and the type cell
255, so an error, which assigns nothing and never reaches `USR`, cannot read as a result. An apparatus row per
argument (no function: `R=N`, `Q=USR(N)`) must hand `USR` the argument's own type and bytes on both machines, or the
loader refuses the run.
- **[KMA MI ABS *n*]**, **[KMA MS ABS *n*]**, **[KMA MD ABS *n*]**: the argument an integer, a single or a
  double, *n* the `DATA` text. Integers: 0, 1, -1, 2, -2, 3, 4, 5, -5, 9, 10, 16, 100, 255, 12345, -12345, 32767, -32767, -32768. Singles: 0, -0, 1, -1, .5, -.5, .4, -.4, .6, -.6, .9, -.9, .1, -.1, 1.5, -1.5, 1.9, -1.9, 2.5, -2.5, 2, 3, 4, 5, 9, 10, 16, .25, 2.25, 1.44, 99.9998, .999999, -.999999, 99999.5, -99999.5, 99999.9, -99999.9, 12345.6, -12345.6, 32767, 32767.5, -32767.5, 32768, -32768, -32768.5, -32769, 65535.5, 123456, -123456, 999999, -999999, 1E6, -1E6, 1E10, -1E10, 1E-10, -1E-10, 1E-6, -1E-6, 1.23456E-5, 1E-63, -1E-63, 1E-64, -1E-64, 9.99999E62, -9.99999E62. Doubles:
  0, -0, 1, -1, .5, -.5, .9, -.9, 1.5, -1.5, 2.5, -2.5, 2, 3, 5, 10, .25, 2.25, 99.99998, 32767.9, -32768.1, 32768, -32768, -32769, 65536.5, 1234567.5, -1234567.5, 12345678.9, -12345678.9, -9999999.5, .99999999999999, -.99999999999999, 1.9999999999999, -1.9999999999999, 9999999999999.5, -9999999999999.5, 1234567890123.4, -1234567890123.4, 12345678901234, -12345678901234, 1D14, -1D14, 1D20, -1D20, 1D-10, -1D-10, 1D-14, -1D-14, 1D-64, -1D-64, 9.9999999999999D62, -9.9999999999999D62.
- **[KMA FX *i*]**: a fixed statement, `S$` = `"12"`; the list, with what each one separates, is `FX` in the probe:
  a string literal or variable as the argument, the result assigned to `R$`, `1/0`, no argument, an extra one, no
  `)`, no parenthesis; the literals `2.5`, `-2.5`, `7`, `7%`, `2.5!`, `2.5#`, `&H8000`, `-32768`, `-0`, `1/4`;
  spaces; `ABS(ABS(2.25))`; and a single `N!` assigned 1 whose exponent byte is then POKEd to 0 or `&H80`
  (digit bytes `10 00 00`).
- **[KMA FY *i*]**, **[KMA FZ *i*]** (goldfish pass 1, 2026-11-24): more fixed statements, on a two-line frame
  (`FY` and `FZ` in the probe): the order of the checks (`ABS(1/0`, `ABS("A"`, `ABS(1/0,2)`, `ABS("A",2)`); the
  forms this page quotes (`PRINT ABS`, `ABS(1,2)`, `ABS(-1E38)`); the result stored in an integer `T%` or a single
  `T!` (holding -7 before) and read back through `USR(T%)` / `USR(T!)`; and (FZ) `ABS` nested 16
  and 32 deep. Two apparatus checks run before any rule, and the loader refuses the run if either fails: every
  literal the FX / FY forms use, alone (`R=<literal>`, `Q=USR(<literal>)`, KMA FY 70-92), has the type and bytes the
  FORMS rule gives it; and every matrix row's recorded argument is its `DATA` text's value in its type, on both
  machines -- so the six rows of one text (the apparatus row and the five functions) saw the same argument, no
  function changed its argument variable, and the two machines `READ` the text alike.

**Controls** ([`kmath_controls.py`](../../probes/basic/spec/kmath_controls.py)): each is a rival rule run over the reference's cases: “ABS(-32768%) the DOUBLE 32768 -- zerobas's rule” is FALSE on 1 of the 19 cases it selects (e.g. KMA MI ABS -32768); “ABS(-32768%) error 6 (no integer 32768)” is FALSE on 1 of the 19 cases it selects (e.g. KMA MI ABS -32768); “an exponent-0 result made a canonical zero” is FALSE on 2 of 2 cases it selects (e.g. KMA FX 21); “the argument's type checked before the `)` (13) -- zerobas's rule” is FALSE on 2 of the 4 cases it selects (e.g. KMA FY 1); “the call's shape checked before the argument is evaluated (2)” is FALSE on 2 of the 4 cases it selects (e.g. KMA FY 0); “32 deep is error 50 (zerobas before D-SPMERGE)” is FALSE on 1 of the 2 cases it selects (e.g. KMA FZ 1); “a single exponent-0 zero stored in T! as zero bytes -- zerobas's LET” is FALSE on 1 of the 3 cases it selects (e.g. KMA FY 53).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/abs_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/abs_rules.py --write` -->

**11 rules; 11 hold on the reference. Of the 860 recorded outputs (each case's error from `R=F(x)` and from `Q=USR(F(x))`, R's 8 bytes, the result's type as USR saw it and the result's own bytes): 860 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. ABS(x)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-ABS-INT** An integer gives an integer, its value without the sign (ABS(-5%) is 5%, ABS(32767%) 32767%) -- except -32768, whose 32768 is no integer: ABS(-32768%) is the SINGLE 32768 (45 32 76 80). | 19 | ✓ | ✗ 1: KMA MI ABS -32768 |
| **R-ABS-REAL** A single gives a single and a double a double: the argument's own bytes with the sign bit cleared, nothing else changed (every digit kept, 1E-64 and 9.99999E62 included; -0 READ is already 0). | 118 | ✓ | ✓ |
| **R-ABS-ODD** Only the sign bit changes even on a non-canonical single: exponent byte 0 or &H80 with digit bytes 10 00 00 both give 00 10 00 00. | 2 | ✓ | ✓ |
| **R-ABS-TYPE** A string as the argument (a literal or a variable) is error 13 (Type mismatch), and so is assigning the result to a string variable: the result is a number. | 3 | ✓ | ✓ |
| **R-ABS-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-ABS-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error); so are `PRINT ABS` and `ABS(1,2)`, the forms this page quotes. | 6 | ✓ | ✓ |
| **R-ABS-ORDER** The argument is evaluated before the call's shape is checked, and its type after: ABS(1/0 (no `)`) and ABS(1/0,2) raise the argument's own error 11, but ABS("A" (no `)`) and ABS("A",2) are error 2 (Syntax error), not 13 -- the `)` is required before the string is refused. | 4 | ✓ | ✗ 2: KMA FY 1, KMA FY 3 |
| **R-ABS-NEST** ABS nested 16 and 32 deep (ABS(ABS(...(-2.5)...))) gives what the rules above give applied that many times, with no error. | 2 | ✓ | ✓ |
| **R-ABS-FORMS** Spaces before the parenthesis and around the argument are allowed, and a literal's own type is the argument's: 2.5 and -2.5 are singles, 7 an integer, 7% / 2.5! / 2.5# what they say, &H8000 the integer -32768, -32768 a single (a minus on the single 32768), -0 the integer 0, 1/4 a double; ABS of ABS(2.25) is ABS of that result. Each gives what the rules above say for that type and value; so does ABS(-1E38), a single. These types are MEASURED: each literal alone, `R=<literal>` / `Q=USR(<literal>)`, gives that type and value on both machines (KMA FY 70-92; the loader refuses a run where it does not). | 14 | ✓ | ✗ 1: KMA FX 16 |
| **R-ABS-ASSIGN** `R=ABS(x)` with R a double stores the result's value -- an integer by its value, a single's own 4 bytes then four zero bytes, its exponent byte and digit bytes as they are (so ABS of the POKEd single 00 10 00 00 leaves R 00 10 00 00 00 00 00 00, KMA FX 21) -- and an error stores nothing (R keeps its sentinel). Read in every case that assigns R. | 169 | ✓ | ✗ 2: KMA FX 21, KMA FX 22 |
| **R-ABS-TARGET** Stored in an INTEGER variable, ABS's result loses its fraction -- truncated, not rounded (SQR(3) stores 1) -- and a value outside -32768..32767 is error 6 (Overflow), the variable unchanged; stored in a SINGLE, a single keeps its own 4 bytes (an exponent-0 one its digit bytes too), an integer becomes its value, a double is cut to 6 digits (SQR(2): 1.41421). Read back through USR(T%) / USR(T!). | 3 | ✓ | ✗ 1: KMA FY 53 |

<!-- RULES END -->

## Differences from the reference

- **`ABS(-32768%)` is a double here, a single on the VG-8020** (rule R-ABS-INT, KMA MI ABS -32768; R-ABS-FORMS, KMA
  FX 16 `ABS(&H8000)`) -- [D-ABSINTEDGE](../../todo/open/D-ABSINTEDGE.md). The value, 32768, is the same, so PRINT
  and arithmetic show nothing; a routine that reads the result's type does.
- **A single whose exponent byte is 0 but whose digit bytes are not is stored in a variable as zero bytes here**
  (rule R-ABS-ASSIGN, KMA FX 21, 22: `R=ABS(N!)` of the two POKEd singles) --
  [D-ZEROLET](../../todo/open/D-ZEROLET.md). It is the assignment's, not `ABS`'s: `ABS`'s own result agrees (R-ABS-ODD).
  Stored in a single the same (rule R-ABS-TARGET, KMA FY 53 `T!=ABS(N!)`).
- **`ABS("A"` (no `)`) and `ABS("A",2)` are error 13 here, error 2 on the VG-8020** (rule R-ABS-ORDER, KMA FY 1, 3)
  -- [D-ARGTYPEORDER](../../todo/open/D-ARGTYPEORDER.md). The reference requires the `)` before it refuses the
  string; the argument's own error (`ABS(1/0`, 11) wins on both.

The one rung not yet proven is **RAM usage**: `ABS` uses the same amount of
free memory on both machines, but the VG-8020 writes a few work-area cells
along the way that zerobas does not. Nothing a program can observe through
`FRE` or the documented variables differs.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] An argument's own error was measured with one kind (`1/0`, error 11); that any error of the argument wins is assumed.
- [A] Which work-area cells the call writes (the RAM-usage rung).
- [A] Non-canonical bytes other than the two measured singles (exponent byte 0 or `&H80` with digit bytes `10 00 00`): a double, non-BCD digit nibbles, `&H80` with zero digit bytes.
- [A] Stored in an INTEGER variable, a NEGATIVE result with a fraction: truncated toward zero or rounded down is not
  separated (no such case; the conversion region, [CINT](CINT.md)). Stored in a SINGLE, a double that needs its 7th
  digit rounded or cut is not separated either (`SQR(2)`'s 7th digit is 3).

## What we found, and how

- **The −32768 edge's TYPE was never tested** (2026-11-24, D-KWSPEC's maths
  probe). Every test compared the value, 32768, which agrees; reading the
  result's type through a `USR` routine showed a single on the reference and a
  double here ([D-ABSINTEDGE](../../todo/open/D-ABSINTEDGE.md)).
- **Empty or malformed calls returned a number** (fixed 2026-07-13 and
  2026-07-14, D-F2-3 and D-F2-4). `ABS()` printed 0, and `PRINT ABS` or
  `ABS(1,2)` quietly ran on whatever value was left over from earlier, where the
  VG-8020 says `Syntax error`. The two fixes cover all the math functions:
  [spec-basic-empty-expr-syntax-error.md](../spec-basic-empty-expr-syntax-error.md),
  [spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md).
- **The −32768 edge was already right.** A sweep of every place zerobas
  negates a 16-bit number (D-NEG8K, 2026-08-11) found that `ABS` of integer
  −32768 already gave 32768; it was unary minus next to it that had the edge
  backwards. [fixpoint8000-msx1-sweep.md](../fixpoint8000-msx1-sweep.md).
- **Deep nesting gave a nonsense error.** `ABS(ABS(…))` sixteen levels deep
  answered `FIELD overflow` (error 50), while both references go 32 deep
  without trouble (fixed 2026-09-12, D-SPMERGE, which merged two stacks). The
  spec probe now measures 16 and 32 deep on the VG-8020 and on zerobas (rule
  R-ABS-NEST, KMA FZ 0, 1): no error, the same result.
- **The space before the parenthesis was checked** (D-NUMSPACE, 2026-09-09):
  `ABS (-7)` was already accepted, as on both references
  ([`numspace_run.out`](../../scratchpad/numspace_run.out)).
- **The whole error set was measured on the reference** (D-KWT6, 2026-09-27):
  wrong type, no argument, an extra argument and `ABS(-1E38)`; zerobas matched
  every case ([`t6enum_run.out`](../../scratchpad/t6enum_run.out)).

## Where it lives

`evmc_abs` in [basic/expr.asm](../../basic/expr.asm), reached from the math
selector `ev_ff_mathconv`; the argument is read by `ev_mc_arg`, which all the
math functions share. The design notes are in
[spec-basic-math-pack.md](../spec-basic-math-pack.md) §9.

## Tests that cover it

- `make math-acceptance` — values and types against the VG-8020, including the
  integer −32768 case and the empty and malformed calls.
- `make kwsweep` — the everyday row (`ABS(-5)`), the error rows for {2, 13},
  and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
