<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `FOR` — start a counted loop

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`FOR I=1 TO 10` starts a loop: the variable takes the start value, the
statements up to the matching [`NEXT`](NEXT.md) run, and `NEXT` adds the step
and decides whether to go round again. `FOR` sets the loop up; the counting and
the stop test happen at `NEXT`, so read the two pages together. zerobas
behaves like the Philips VG-8020 in every case we have measured, errors
included.

## Syntax

```
FOR <variable>=<start> TO <limit> [STEP <step>]
```

`STEP` is optional and defaults to 1. A negative step counts down.

## Details

- **The loop variable is any ordinary numeric variable**: a long name
  (`FOR INDEX=1 TO 3`; two characters are significant, as everywhere), a type
  suffix (`A%`, `A!`, `A#`), or the type a `DEFINT`/`DEFSNG`/`DEFDBL` gives
  it. `A`, `A%` and `A$` are three different variables, and a loop over one
  leaves the others alone.
- **It cannot be an array element or a string.** `FOR A(1)=1 TO 3` is
  `Syntax error`; `FOR A$=1 TO 3`, and a name that `DEFSTR` made a string, are
  `Type mismatch`.
- **A loop over a single or double variable is real decimal arithmetic.**
  Fractional starts and steps work, and so do values beyond the integer range:
  `FOR A=0 TO 1 STEP .25` runs 0, .25, .5, .75, 1; `FOR A=56700 TO 56702` and
  `FOR A=-40000 TO -39999` count as written.
- **A loop over an integer (`%`) variable is integer arithmetic.** The start is
  truncated (`FOR A%=1.7 TO 3` starts at 1) and so is the step — so
  `FOR A%=1 TO 3 STEP .5` has a step of 0 and never ends, on the VG-8020 too.
  Stepping past 32767 is `Overflow` (error 6), raised on the `NEXT` line.
- **After the loop, the variable is one step past the limit**: after
  `FOR I=1 TO 3` it is 4, after `FOR A=.5 TO 3` it is 3.5.
- **The body may change the variable**, and the loop counts on from the new
  value: `FOR A=1 TO 3:A=A+.5` runs with 1.5 and 3, then stops.
- **Loops nest**, and `FOR` inside a `GOSUB` and `GOSUB` inside a `FOR` mix
  freely; how far they nest depends on free memory.

### Errors

| you write | you get |
|---|---|
| `FOR I=1:NEXT` (no `TO`), `FOR 5=1 TO 2`, `FOR A(1)=1 TO 3` | 2 `Syntax error` |
| `FOR I=1 TO 2 STEP 1,2` | 2 `Syntax error` |
| `FOR I="A" TO 2`, `FOR I=1 TO "A"`, `STEP "A"` | 13 `Type mismatch` |
| `FOR A$=1 TO 2` | 13 `Type mismatch` |
| `FOR I=1 TO:NEXT`, `STEP` with nothing after it | 24 `Missing operand` |
| an integer loop that steps past 32767 | 6 `Overflow` (at the `NEXT`) |

The whole set of errors `FOR` raises in its three forms is {2, 13, 24}, the
same on both machines; the `Overflow` belongs to `NEXT`.

## Example

```
10 FOR I=1 TO 3:PRINT I;:NEXT:PRINT
20 FOR A=1 TO 0 STEP -.5:PRINT A;:NEXT
30 PRINT
40 PRINT "After:";I;A
50 ON ERROR GOTO 80
60 FOR B$=1 TO 2
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 1  2  3
 1  .5  0
After: 4 -.5
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_for.out`](../../scratchpad/kwdoc_for.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**. The loop's record on the stack
was rebuilt at the reference's own size, 25 bytes, in September 2026 (below);
the cell-by-cell RAM comparison has not yet proven the rung.

## What we found, and how

- **Every loop was integer arithmetic** (fixed 2026-09-27, D-FORFLOAT).
  `FOR A=0 TO 1 STEP .25` printed 0 for ever, `FOR A=.5 TO 3` counted 0, 1, 2,
  3, and `FOR A=56700 TO 56702` printed negative numbers: 4 of 15 measured
  loops agreed with the VG-8020. The reference keeps the step and limit as
  decimal numbers unless the variable is `%`; zerobas now does the same, and
  all 15 agree ([before](../../scratchpad/forfloat_run.out),
  [after](../../scratchpad/forfloat_after_run.out),
  [spec-basic-forfloat.md](../spec-basic-forfloat.md)). It was found by
  accident, by a memory probe that walked addresses above 32767 in a loop.
- **The loop variable could only be a single letter** (fixed 2026-08-08,
  D-FORVAR). `FOR AB=1 TO 3`, `FOR A%=1 TO 3` and `FOR A1=1 TO 3` were all
  `Syntax error`; 8 of 30 measured rows agreed, both reference machines
  agreeing with each other on all of them
  ([forvar-msx1-characterization.md](../forvar-msx1-characterization.md)).
- **`GOSUB` and `FOR` share one pool of stack frames** since September 2026
  (D-CTLPOOL on 2026-09-04, D-SPMERGE on 2026-09-12), as on the reference;
  before that each had a small fixed table.
- **`FOR` had no test of its own** until D-KWBARS: every `FOR` in the keyword
  sweep was scaffolding for a `NEXT` row. Three rows now check that the loop
  stops at the right value for the implied step, an explicit step and a
  negative step.

## Where it lives

`ex_for` in [basic/program.asm](../../basic/program.asm) builds the loop
record; `slot_store` and `slot_load` keep the limit and step in their own
type. The arithmetic is the evaluator's own (`combine_add`, `combine_cmp` in
[basic/float-arith.asm](../../basic/float-arith.asm)), reached from `NEXT`.
The design notes are in [spec-basic-forvar.md](../spec-basic-forvar.md) and
[spec-basic-forfloat.md](../spec-basic-forfloat.md).

## Tests that cover it

- `make forvar-acceptance` — loop-variable names and types, and the ten
  decimal-arithmetic rows (fractional step and start, past the integer range,
  the 32767 edge, a body that changes the variable).
- `make kwsweep` — the three everyday rows (implied, explicit and negative
  step) and the error rows for {2, 13, 24}.
- `make kwram` — the RAM-usage comparison.
