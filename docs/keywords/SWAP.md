<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `SWAP` — exchange the values of two variables

> **Spec:** DRAFT 1 (2026-11-24) — 30 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`klet.py`](../../probes/basic/spec/klet.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-24):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✗ (a SWAP that fails leaves a different variable behind). One difference, found by the spec probe (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`SWAP A,B` exchanges the values of two variables of the same type: afterwards
`A` holds what `B` held and the other way round. It works for numbers, strings
and array elements. zerobas behaves exactly like the Philips VG-8020 for every
case we have measured, errors included.

## Syntax

```
SWAP <variable>,<variable>
```

Both operands must be variables or array elements — not numbers, expressions
or functions.

## Details

- **Every type exchanges**: integer, single, double and string variables, and
  array elements (`SWAP Q(0),Q(1)`, `SWAP A,Q(0)`, `SWAP Q$(0),Q$(1)`).
  `SWAP A,A` is allowed and changes nothing.
- **The types must be exactly equal.** A number with a string is
  `Type mismatch` (error 13), and so is any mix of numeric types: `A%` with
  `B!`, `A!` with `B#`, `A%` with a plain `B` (which is double). `DEFINT` and
  friends count: after `DEFINT C`, `C` and `D` are different types.
- **Strings are exchanged without copying their text.** Only the strings'
  descriptors move, so swapping a 2-character string with a 20-character one
  leaves both intact, also after later string allocations.
- **The second variable must already exist; the first need not.**
  `B=1:SWAP A,B` creates `A` (it ends up 1, `B` ends up 0), but `A=1:SWAP A,B`
  with no `B` yet is `Illegal function call` (error 5). An array that was
  never `DIM`med is no problem: `A=1:SWAP A,Q(0)` creates `Q` as `DIM` would
  and exchanges.
- **A wrong subscript** is `Subscript out of range` (error 9):
  `DIM Q(2):SWAP A,Q(9)`.
- **The shape errors** are `Syntax error` (error 2): `SWAP`, `SWAP A`,
  `SWAP A,1`, `SWAP 1,A`, `SWAP A,LEN("x")`, `SWAP (A),B`.
- **Anything after the second variable** is `Syntax error` too — but only
  *after* the exchange has happened: `A=1:B=2:SWAP A,B,C` leaves `A`=2 and
  `B`=1, then raises error 2. An operator after it counts the same way:
  `SWAP A,B+0`, `B-0`, `B*1` exchange, then raise error 2. If `B` does not exist, the error is 5 instead.
- **Which error wins:** a type mismatch is reported before the missing second
  variable — `SWAP A,B$` with neither defined is error 13, not 5.

| you write | you get |
|---|---|
| `A=1:B=2:SWAP A,B` | A is 2, B is 1 |
| `A=1:B$="x":SWAP A,B$` | error 13, `Type mismatch` |
| `A%=1:B!=2.5:SWAP A%,B!` | error 13, `Type mismatch` |
| `A=1:SWAP A,B` (no `B`) | error 5, `Illegal function call` |
| `DIM Q(2):SWAP A,Q(9)` | error 9, `Subscript out of range` |
| `SWAP A`, `SWAP A,1` | error 2, `Syntax error` |

Every error above is the same on both machines.

## Example

```
10 A=1:B=2:SWAP A,B:PRINT A;B
20 A$="LEFT":B$="RIGHT"
30 SWAP A$,B$:PRINT A$;" ";B$
40 DIM Q(3):Q(0)=7:Q(1)=9
50 SWAP Q(0),Q(1):PRINT Q(0);Q(1)
60 ON ERROR GOTO 100
70 SWAP A,B$
80 SWAP A,Z
90 END
100 PRINT "Error";ERR:RESUME NEXT
RUN
 2  1
RIGHT LEFT
 9  7
Error 13
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_swap.out`](../../scratchpad/kwdoc_swap.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/swap_rules.py`](../../probes/basic/spec/swap_rules.py), model in
[`klet_model.py`](../../probes/basic/spec/klet_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/klet.py`](../../probes/basic/spec/klet.py) (on the shared RAM-record
harness [`ramrec.py`](../../probes/basic/spec/ramrec.py)), typed on both machines; run file
[`scratchpad/KLT_run1.out`](../../scratchpad/KLT_run1.out) (2026-11-24; zerobas's side on that day's build). Every case
starts from nothing -- its line begins with `CLEAR` -- runs its statement(s), the one under test last, and the next
line records ERR and the variables it names, read through VARPTR: a number's own bytes, a string's length and first 7
bytes. A variable the case did not create reads 0 or "" (reading it creates it). The probe's own variables (all
starting with W) are created before the case, because a variable created later moves the arrays and would make an
array element's address stale -- measured on both machines while building the probe.
- **[KLT FX *i*]** (SWAP):
  27: `A=1:B=2:SWAP A,B`
  28: `A%=1:B%=-2:SWAP A%,B%`
  29: `A!=1.5:B!=-2.5:SWAP A!,B!`
  30: `A$="X":B$="YZ":SWAP A$,B$`
  31: `A=1:SWAP A,A`
  32: `A%=1:B!=2.5:SWAP A%,B!`
  33: `A!=1:B#=2:SWAP A!,B#`
  34: `A%=1:B=2:SWAP A%,B`
  35: `A=1:B$="X":SWAP A,B$`
  36: `DEFINT C:C=1:D=2:SWAP C,D`
  37: `B=1:SWAP A,B`
  38: `A=1:SWAP A,B`
  39: `A=1:SWAP A,Q(0)`
  40: `DIM Q(2):Q(1)=5:A=1:SWAP A,Q(1)`
  41: `Q$(0)="P":Q$(1)="QR":SWAP Q$(0),Q$(1)`
  42: `DIM Q(2):A=1:SWAP A,Q(9)`
  43: `SWAP`
  44: `A=1:SWAP A`
  45: `A=1:SWAP A,1`
  46: `A=1:SWAP 1,A`
  47: `A=1:B=2:SWAP A,B+0`
  48: `A=1:B=2:SWAP (A),B`
  49: `A=1:B=2:SWAP A,B,C`
  50: `A=1:SWAP A,B,C`
  51: `SWAP A,B$`
  52: `A$="AB":B$=STRING$(20,"X"):SWAP A$,B$:C$=STRING$(50,"Y")`
  53: `Q$(0)="P":Q$(1)="QR"`
  54: `Q$(0)="P":Q$(1)="QR":SWAP Q$(1),Q$(0)`
  55: `A=1:B=2:SWAP A,B-0`
  56: `A=1:B=2:SWAP A,B*1`

**Controls** ([`klet_controls.py`](../../probes/basic/spec/klet_controls.py)): each is a rival rule run over the
reference's cases: “numeric types converted and exchanged (no error)” is FALSE on 4 of the 5 cases R-SWAP-TYPES selects (e.g. KLT FX 32); “a missing second variable created and exchanged” is FALSE on 2 of the 4 cases R-SWAP-NEW selects (e.g. KLT FX 38); “the missing second created holding the first's value -- zerobas's” is FALSE on 2 of the 4 cases R-SWAP-NEW selects (e.g. KLT FX 38); “the Syntax error before any exchange” is FALSE on 4 of the 4 cases R-SWAP-AFTER selects (e.g. KLT FX 47).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/swap_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/swap_rules.py --write` -->

**6 rules; 6 hold on the reference. Of the 90 recorded outputs (each case's ERR and the bytes of the (up to two) variables it names, read after it): 90 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The exchange

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-SWAP-EXCH** SWAP exchanges two variables of exactly the same type -- integer, single, double, string, array elements (an array never DIMmed is created as DIM would) -- and a variable with itself is unchanged; strings keep their text after later string allocations. | 11 | ✓ | ✓ |

#### 2. Errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-SWAP-TYPES** Two different types -- integer and single, single and double, integer and a plain name, a number and a string, an integer and a double by DEFINT -- are error 13 (Type mismatch); nothing moves. | 5 | ✓ | ✓ |
| **R-SWAP-NEW** The first variable may be new: it is created and takes the second's value, the second gets 0. A second variable that does not exist is error 5 (Illegal function call) -- also with a third after it -- and the first keeps its value; the second is not created (it reads 0). Both new and of different types: error 13 first. | 4 | ✓ | ✗ 2: KLT FX 38, KLT FX 50 |
| **R-SWAP-SUBSCR** An array element out of range is error 9 (Subscript out of range); nothing moves. | 1 | ✓ | ✓ |
| **R-SWAP-SHAPE** SWAP alone, one variable, a number in either place, or a parenthesised first variable are error 2 (Syntax error); nothing moves. | 5 | ✓ | ✓ |
| **R-SWAP-AFTER** Anything after the second variable -- `,C`, `+0`, `-0`, `*1` -- is error 2, but only AFTER the exchange: A and B have been swapped. | 4 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

- **`A=1:SWAP A,B` with no `B` leaves `B` holding A's value here** ([D-SWAPNEW](../../todo/open/D-SWAPNEW.md); rule R-SWAP-NEW, KLT FX 38, 50): both raise error 5, but on the VG-8020 `B` is not created (it reads 0 afterwards), while zerobas has created it with the first variable's value.

The one rung not yet proven is **RAM usage**: `SWAP` uses the same amount of
free memory on both machines, but the two machines write different work-area
cells along the way — the VG-8020 some that zerobas does not, and zerobas a few
the VG-8020 does not.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] Which work-area cells the statement writes (the RAM-usage rung).
- [A] `SWAP A,LEN("x")` and other function forms; SWAP of whole arrays (not allowed?).

## What we found, and how

- **The spec probe** (D-KWSPEC, 2026-11-24): every claim of this page held, and one more: an operator after the second variable (`SWAP A,B+0`) exchanges first and raises Syntax error after, as a third variable does. One difference: a failed SWAP with a new second variable (D-SWAPNEW).
- **`SWAP` arrived on 2026-07-28**, after its behaviour on the VG-8020 was
  measured first (2026-07-27). Three things there are easy to guess wrong: the
  type rule is exact type equality, not just "number or string"; strings move
  by descriptor; and only the *second* variable has to exist:
  [missing-vg8020-characterization.md](../missing-vg8020-characterization.md) §4.
- **An extra operand gave the wrong error, at the wrong moment** (fixed
  2026-08-24, D-SWAP3). zerobas had its own check for a third operand that
  raised error 5 before exchanging anything; both reference machines exchange
  first and then raise error 2. The earlier measurement had agreed for the
  wrong reason — its `B` did not exist, so it was really measuring the
  second-operand rule. The check was deleted and the general end-of-statement
  check now handles it, which also saved ROM space:
  [spec-basic-swap3.md](../spec-basic-swap3.md).
- **Two undefined variables of different types gave the wrong error** (fixed
  2026-09-16, D-SWAPTYPE). `SWAP A,B$` with neither defined was
  `Illegal function call`; both references say `Type mismatch`
  ([kwt3_swapchk.out](../../scratchpad/kwt3_swapchk.out)). zerobas now checks
  the types, which it knows from the names, before complaining about the
  missing variable. The fix was ready on 2026-09-13 but had to wait three days
  for the ten bytes of ROM it needed.

## Where it lives

`ex_swap` in [basic/missing.asm](../../basic/missing.asm): `sw_operand`
resolves each operand (creating the first if needed), `sw_absent` raises the
missing-second-operand error, and `sw_types` checks the types and exchanges the
bytes.

## Related concepts

- [Variables](../concepts/variables.md) — names, types, arrays, and where they live

## Tests that cover it

- `make missing-acceptance` — every type, array elements, string descriptors,
  the type-equality and existence rules, and the shape errors.
- `make kwsweep` — the everyday row (`SWAP A,B`), the error rows for 2 and 13,
  the `Type mismatch` row with undefined variables, and the
  deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
