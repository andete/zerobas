<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `NEXT` — end of a `FOR` loop: step, test, go round

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`NEXT` closes a loop opened by [`FOR`](FOR.md). It adds the step to the loop
variable, compares it with the limit, and either jumps back to the statement
after the `FOR` or lets the program carry on. A bare `NEXT` closes the
innermost open loop; `NEXT I` names the loop; `NEXT J,I` closes several at
once. zerobas behaves like the Philips VG-8020 in every case we have measured,
errors included.

## Syntax

```
NEXT
NEXT <variable>[,<variable>...]
```

## Details

- **A bare `NEXT` takes the innermost loop.**
- **A named `NEXT` must match the whole variable: both significant characters
  and the type.** After `FOR A%=1 TO 3`, `NEXT A` is `NEXT without FOR`
  (error 1), because `A` and `A%` are different variables. So is `NEXT A` after
  `FOR AB=1 TO 3`.
- **A named `NEXT` closes any inner loops it passes.** With `FOR AB` and
  `FOR CD` open, `NEXT AB` abandons the `CD` loop and steps `AB`.
- **`NEXT J,I` is `NEXT J` followed by `NEXT I`**, innermost first. A trailing
  comma (`NEXT J,`) is `NEXT without FOR`; a number in the list (`NEXT J,1`) is
  `Syntax error`.
- **`NEXT A$` is not a type error**: it is `NEXT without FOR`, because no loop
  can have a string variable. The same goes for an array element: `NEXT A(1)`
  is `NEXT without FOR` (and, as on the reference, it creates the array `A` if
  it did not exist). A space before the bracket, `NEXT A (1)`, is read the
  same way.
- **The arithmetic follows the loop's type**: decimal for a single or double
  variable, integer for `%`, where stepping past 32767 is `Overflow` (error 6)
  on the `NEXT` line. See [`FOR`](FOR.md) for the loop rules.
- **`RETURN` throws away loops opened inside the subroutine**, so a `NEXT`
  after it no longer finds them — see [`RETURN`](RETURN.md).

### Errors

| you write | you get |
|---|---|
| `NEXT` or `NEXT I` with no loop open | 1 `NEXT without FOR` |
| `NEXT J` when only `I` is open, `NEXT A$`, `NEXT J,K` with `K` not open | 1 `NEXT without FOR` |
| `NEXT 5` | 2 `Syntax error` |

The whole set of errors `NEXT` raises in its three forms is {1, 2}, the same
on both machines (plus the integer `Overflow` above).

## Example

```
10 FOR I=1 TO 2:FOR J=1 TO 3
20 PRINT I;J;
30 NEXT J,I
40 PRINT:PRINT "I=";I;"J=";J
50 ON ERROR GOTO 80
60 NEXT K
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 1  1  1  2  1  3  2  1  2  2  2  3
I= 3 J= 4
Error 1
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_next.out`](../../scratchpad/kwdoc_next.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`NEXT` added two whole numbers** (fixed 2026-09-27, D-FORFLOAT). A loop
  with a fractional step never ended and one past 32767 wrapped round to
  negative numbers; `NEXT` now uses the same decimal arithmetic as the rest of
  BASIC, as the reference does. The details are on the [`FOR`](FOR.md) page.
- **Four `NEXT` forms were missing, all found and fixed on 2026-08-08**, each
  measured on both reference machines first:
  - **Matching on the full name and type** (D-FORVAR). zerobas compared one
    letter, so `NEXT A` closed a `FOR AB` loop. Measuring showed the type is
    part of the match too, which nobody had predicted
    ([forvar-msx1-characterization.md](../forvar-msx1-characterization.md)).
  - **`NEXT J,I`** (D-NXLIST) was `Syntax error`. It took three rounds of
    measurement to pin down: a trailing comma is not a bare `NEXT`, and a
    number in the list is a different error
    ([nxlist-msx1-characterization.md](../nxlist-msx1-characterization.md)).
  - **`NEXT A(1)`** (D-NXARY): the reference evaluates the subscript, and so
    creates the array, before failing to match
    ([spec-basic-nxary.md](../spec-basic-nxary.md)).
  - **`NEXT A (1)`** with a space (D-TGTSPC): the space is still in the stored
    line on all three machines, so the parser has to skip it
    ([spec-basic-tgtspc.md](../spec-basic-tgtspc.md)).
- **The tests had a blind spot.** `NEXT` had one row, the bare form, and a bare
  `NEXT` never exercises the name matching at all. Rows for the named and the
  comma-list forms were added (D-KWBATCH7).

## Where it lives

`ex_next` in [basic/program.asm](../../basic/program.asm), with `nx_comma`
(the list), `nx_scan` and `nx_cmp` (finding the matching loop) and `nx_have`
(step and test). The arithmetic is `combine_add` and `combine_cmp` in
[basic/float-arith.asm](../../basic/float-arith.asm); array names go through
the shared `tgt_parse` in [basic/vars.asm](../../basic/vars.asm).

## Tests that cover it

- `make forvar-acceptance` — name and type matching, and the decimal loops.
- `make nxlist-acceptance` — `NEXT J,I`, trailing commas, numbers in the list.
- `make nxary-acceptance` and `make tgtspc-acceptance` — `NEXT A(1)` and
  `NEXT A (1)`.
- `make kwsweep` — the bare, named and comma-list rows, and the error rows for
  {1, 2}.
- `make kwram` — the RAM-usage comparison.
