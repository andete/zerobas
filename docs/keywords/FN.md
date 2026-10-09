<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `FN` and `DEF FN` — one-line functions of your own

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. Two recorded
> differences: an argument that reads the caller's own parameter after it was
> rebound, and `DEF FNA(5)=…` being accepted (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`DEF FNA(X)=X*X+1` defines a function named `FNA` with a parameter `X`;
`FNA(3)` then calls it. The result's type comes from the name, like a
variable's: `FNA$` returns a string, `FNA%` an integer. zerobas follows the
Philips VG-8020 (and the National CF-3300, which agrees on every case) in when
the definition is checked, how parameters are bound, and which error wins.

## Syntax

```
DEF FN<name>[(<parameter>[,<parameter>…])]=<expression>
FN<name>[(<argument>[,<argument>…])]
```

Up to nine parameters. A function with none is called without parentheses.

## Details

- **A parameter is private to the function's own body.** `X=5:DEF FNA(X)=…`
  leaves the program's `X` at 5 during and after the call, even if the call
  fails. Other variables are read normally: with `Y=3`, `DEF FNA(X)=X+Y`
  sees 3.
- **Arguments are worked out in the caller's scope**, before the body runs:
  `X=5:FNA(X+1)` passes 6.
- **`DEF FN` does not look at the body** until the function is called, so
  `DEF FNA(X)=X+*2` is accepted until the first call. What it does check:
  the name must start with a letter (`DEF FN1(X)` is a syntax error at the
  `DEF`), and on the VG-8020 a parameter must be a name — zerobas does not
  check that yet (see *Differences*).
- **The definition is made when the `DEF FN` statement runs**, not when the
  line is typed. `CLEAR` erases it, like a variable.
- **`FNA` and the variable `A` are different things** and can both exist.
- **`DEF FN` only works inside a program.** Typed at the prompt it is
  `Illegal direct` (error 12). `DEF USR` is not restricted.
- **Calls nest:** a body may call another function, and an argument may
  itself be a call; `FNA(FNA(…FNA(1)…))` answers the VG-8020's values at
  depths up to 24, the deepest measured here.
- **Errors, in the order they are checked** — an unknown name wins over
  everything else:

| situation | error |
|---|---|
| no such function (`FNZ(1)`), or it was erased by `CLEAR` | 18 `Undefined user function` |
| wrong number of arguments (`FNA(1,2)`, `FNA` with no list) | 2 `Syntax error` |
| more than nine parameters | 5 `Illegal function call`, at the call |
| a string for a numeric parameter (`FNA("A")`) | 13 `Type mismatch` |
| a string function used as a number (`A=FNA$(1)`) | 13 `Type mismatch` |
| `DEF FN1(X)`, `DEF FN(X` — no letter after `FN` | 2 `Syntax error`, at the `DEF` |
| `DEF FN…` typed at the prompt | 12 `Illegal direct` |

The error sets for the call are {2, 13, 18} for a numeric function and
{13, 18} for a string one, the same on both machines.

## Example

```
10 Y=3:DEF FNA(X)=X*X+Y
20 DEF FNB$(S$)=S$+"!"
30 X=5:PRINT FNA(2);X
40 PRINT FNB$("HI")
50 ON ERROR GOTO 90
60 PRINT FNA("A")
70 PRINT FNZ(1)
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
 7  5
HI!
Error 13
Error 18
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_fn.out`](../../scratchpad/kwdoc_fn.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

- **An argument that reads a parameter of the function making the call can
  see the wrong value** (D-FNALIAS, measured 2026-08-27,
  [spec-deffn-alias.md](../spec-deffn-alias.md)). Both references evaluate
  every argument in the caller's scope:
  `DEF FNA(P,Q)=P*100+Q : P=3 : FNA(5,P)` is 503 there and 505 here, and
  `DEF FNB(X)=FNA(9,X)` with `DEF FNA(X,Q)=X*100+Q` gives `FNB(3)` = 903 there
  and 909 here — zerobas binds the first parameter before reading the second
  argument. Joost ruled on 2026-09-09 *"we need to match the reference"*, and
  on 2026-09-27 chose the route: evaluate every argument into the
  control-frame pool before binding. Open, TIER 6.
- **`DEF FNA(5)=1` is accepted here** and `Syntax error` on the VG-8020, as is
  `DEF FNA$(5)=1` (D-DEFFNPARAM, found 2026-09-27): a parameter must be a
  name. Open, TIER 6; it holds back `DEF FN`'s own every-error rung.

The rung not yet proven is **RAM usage**, and here the free memory itself
differs: defining and calling a numeric function in the sweep's row costs 22
bytes of `FRE(0)` on the VG-8020 and 11 on zerobas, a string function 12 and 6
([`rdrndfix_kwram.out`](../../scratchpad/rdrndfix_kwram.out)).

## What we found, and how

- **`DEF FN` was the last missing MSX1 keyword** (shipped 2026-08-23,
  D-DEFFNLAND). It was measured first — 82 cases on both references — and the
  measurement overturned the obvious design: the parameter is not saved in and
  restored from the program's variable; it lives in a separate shadow that
  only the function's body sees
  ([deffn-design-2026-08-22.md](../deffn-design-2026-08-22.md)).
- **A string parameter could be lost in a garbage collection** (fixed
  2026-08-27, D-FNGCROOT): the string tidier did not know the shadow existed.
  The test that proved it did not exist until this fix; it now reads `ABCD`
  where it read garbage ([spec-deffn-gcroot.md](../spec-deffn-gcroot.md)).
- **…and the same, one call deeper** (fixed 2026-09-11, D-FNPOOL). A string
  function calling another string function that triggered a collection
  returned `qLMNO` where both references return `qABCD`. The saved outer call
  now lives in the control-frame pool, where the tidier can find it
  ([spec-basic-fnpool.md](../spec-basic-fnpool.md)).
- **Nesting ran out at depth 11** (found 2026-09-10, fixed 2026-09-12 by
  D-SPMERGE, which merged two stacks). Both references nest at least 30
  deep; zerobas now gives the VG-8020's answers at every depth measured up to
  24 ([`spmerge_fndepth.out`](../../scratchpad/spmerge_fndepth.out)).

## Where it lives

- [basic/deffn.asm](../../basic/deffn.asm): `ex_deffn` records a definition
  (reached from `ex_def` in [basic/usr.asm](../../basic/usr.asm)); `ev_fn`
  and `str_ev_fn` are the numeric and string calls, `fn_call` / `fn_leave`
  the binding.
- [sub/deffn.asm](../../sub/deffn.asm): `deffn_tenant` walks the parameter and
  argument lists and raises the call's errors.
- The shadow lookup sits in `scv_find` in [sub/arrays.asm](../../sub/arrays.asm),
  where every variable reference passes.

## Related concepts

- [Strings and string space](../concepts/strings-and-string-space.md) — where string values live

## Tests that cover it

- `make deffn-acceptance` / `make deffn-strict` — the measured behaviour set,
  scope, types, errors and nesting, against both references.
- `make deffn-selftest` — deliberately broken versions the gate must catch.
- `make kwsweep` — numeric and string `DEF FN` / `FN` rows and the error rows.
- `make kwram` — the RAM-usage comparison.
