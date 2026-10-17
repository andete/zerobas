<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# FRE(0) against the live stack, per expression shape (D-FREPLUS14)

Status: **design, 2026-10-17. Not implemented.** Measurements are done; this page
is the plan the implementation follows.

## The ruling

Joost, 2026-10-16: *"we have to match reference"* — `FRE(0)` must read what the
VG-8020 reads **in every expression shape**, not only at the top of a statement.
The reference counts `FRE(0)` down to the live Z80 stack pointer, so every
construct its evaluator has open when `FRE` runs costs free memory. zerobas's
`FRE(0)` is fixed against the control pool's frontier and reads the same in every
shape.

## What the reference spends (measured)

[`freshape_probe.py`](../scratchpad/freshape_probe.py) →
[`freshape_run3.out`](../scratchpad/freshape_run3.out), each reading against a
plain `A=FRE(0)` in the same program, variables created first. The cost is
**additive over what is pending** when `FRE` runs; anything already reduced
costs nothing (`FRE(0)+0` and `0+0+FRE(0)` read like one `+`).

| pending construct | bytes |
|---|---|
| an open `(` | 6 |
| unary minus, `NOT` | 6 |
| an enclosing function call (`ABS(`, `INT(`, `VAL(`, `STR$(` ...) | 10 |
| an arithmetic operator `+ - * / ^` | 8 + width of its left operand |
| a relational `= <> < > <= >=` | 10 + width of its left operand |
| an integer operator `MOD \ AND OR XOR EQV IMP` | 8 |
| a string concatenation `+` | 2 |
| an array subscript `R(` | 18 |
| a `DEF FN` call | 14 (zerobas's frame: 13) |

Width: integer 2, single 4, double 8 bytes — the left operand is kept at its own
type. And the **statement** sets a base: against a `LET` (which holds its target
variable while the right side runs), a `PRINT` and an `IF` condition read 4 bytes
more free, a `FOR` start 2 bytes less. At the top of a `LET` the VG-8020 reads 18
bytes below zerobas's fixed value, so 14 in a `PRINT`.

Not measured yet: string relationals, multi-argument functions (`MID$`'s second and
third argument, `INSTR`, `STRING$`), `ON … GOTO`, `PRINT #`, `INPUT`, `LOCATE` /
graphics argument lists, a `FRE` inside a `DEF FN` body.

## How zerobas will compute it

The hot evaluator stays as it is: a running depth counter there would cost time on
every expression, and only `FRE(0)` reads it. Instead `FRE(0)` computes the
reference's depth **at the call**:

1. `ev_ff_fre`'s numeric arm calls a new sub-ROM tenant with the current statement's
   start (`SAVTXT`, `$F6AF`) and the position of the `FRE` token.
2. The tenant scans the tokenised statement from its start up to that token,
   simulating the reference's operator precedence (a shunting-yard over the token
   stream: operands, operators by precedence, `(`, function tokens, array names
   followed by `(`). It infers each pending left operand's type from its form: a
   type suffix or the `DEFINT/SNG/DBL/STR` table for a variable, the constant's
   encoding for a number, a function's result type, an operator's result type.
3. It sums the table's costs over what is still pending at the `FRE` token, adds
   the statement's base (identified by the statement's first token: `LET` or an
   implicit assignment, `PRINT`, `IF`, `FOR`, ...), and returns that total.
4. `FRE(0)` = today's value − 18 (the `LET` base) − the total.

`FRE("")` (the string space) does not move: no stack there.

## Edge cases to settle when building it

- Several statements on one line: `SAVTXT` is the current one's start.
- Direct mode: `SAVTXT` points into the line buffer; the scan works the same.
- A `FRE(0)` inside a `DEF FN` body: the depth is the call site's (in the calling
  statement) plus the `FN` frame plus the depth inside the body, scanned from the
  `DEF` line. Phase 2.
- Allocation edges (`Out of memory` thresholds) keep zerobas's own reserves; this
  page changes what `FRE(0)` *reports*, as the ruling asks, not where allocations
  fail.

## Tests

A gate row per measured shape, the VG-8020 as the oracle, in a new
`frelive-acceptance` built from `freshape_probe.py`'s rows; knives that cut one
cost entry each (a paren, an operator class, a width) and must redden only the
rows that use it.
