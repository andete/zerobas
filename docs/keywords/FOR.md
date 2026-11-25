<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `FOR` — start a counted loop

> **Spec:** DRAFT 1 (2026-11-25) — 58 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kfor.py`](../../probes/basic/spec/kfor.py), with FOR's and NEXT's cases together);
> every rule is executable and every recorded output is read by one. Goldfish pass 1 acted on (2026-11-25:
> the model is now an interpreter, 15 more cases); not yet re-reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-25):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ (a FOR that fails pushes no frame since D-FORFRAME, 2026-11-25) · RAM usage not yet proven · every
> error ✗ (D-FORINTLIM, D-FORSTEP0, D-FORCOMMA).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`FOR I=1 TO 10` starts a loop: the variable takes the start value, the
statements up to the matching [`NEXT`](NEXT.md) run, and `NEXT` adds the step
and decides whether to go round again. `FOR` sets the loop up; the counting and
the stop test happen at `NEXT`, so read the two pages together. zerobas
behaves like the Philips VG-8020 on the ordinary loops; it differs on an integer
loop's out-of-range or fractional bounds and on `STEP 0` (see Differences).

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
- **A loop over an integer (`%`) variable is integer arithmetic.** The start,
  the limit and the step are cut towards zero at the `FOR` (`FOR A%=1.7 TO 3`
  starts at 1, `-1.6` is -1) — so `FOR A%=1 TO 3 STEP .5` has a step of 0 and
  never ends, on the VG-8020 too. A start, limit or step outside
  -32768..32767 is `Overflow` (error 6) at the `FOR`; stepping past 32767 is
  `Overflow` at the `NEXT`.
- **A new loop variable is created before the start value is worked out**, as
  `LET` does: `FOR I=FRE(0) TO 9` with no `I` yet reads `FRE(0)` with I's
  11 bytes already spent, on both machines.
- **After the loop, the variable is one step past the last value the body
  saw**: after `FOR I=1 TO 3` it is 4, after `FOR A=.5 TO 3` it is 3.5. The body
  always runs at least once, so `FOR I=3 TO 1` runs once and leaves 4.
- **The body may change the variable**, and the loop counts on from the new
  value: `FOR A=1 TO 3:A=A+.5` runs with 1.5 and 3, then stops.
- **Loops nest**, and `FOR` inside a `GOSUB` and `GOSUB` inside a `FOR` mix
  freely; how far they nest depends on free memory. A `FOR` on a variable
  that already has an open loop opens a second one ON TOP; it does not replace
  the first.

### Errors

| you write | you get |
|---|---|
| `FOR I=1:NEXT` (no `TO`), `FOR 5=1 TO 2`, `FOR A(1)=1 TO 3` | 2 `Syntax error` |
| `FOR I=1 TO 2 STEP 1,2` | 2 `Syntax error` |
| `FOR I="A" TO 2`, `FOR I=1 TO "A"`, `STEP "A"` | 13 `Type mismatch` |
| `FOR A$=1 TO 2` | 13 `Type mismatch` |
| `FOR I=1 TO:NEXT`, `STEP` with nothing after it | 24 `Missing operand` |
| `FOR I%=1 TO 40000` (a start, limit or step an integer cannot hold) | 6 `Overflow` (at the `FOR`) |
| `FOR I=1/0 TO 3` (an error in the start, limit or step) | that error (here 11) |
| an integer loop that steps past 32767 | 6 `Overflow` (at the `NEXT`) |

Besides its expressions' own errors, `FOR` raises 2, 6, 13 and 24 (the
`Overflow` at the `FOR` is an integer variable's bound; the one at `NEXT` is
the count running out of range).

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

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/for_rules.py`](../../probes/basic/spec/for_rules.py), model in
[`kfor_model.py`](../../probes/basic/spec/kfor_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/kfor.py`](../../probes/basic/spec/kfor.py) (on the shared RAM-record
harness [`ramrec.py`](../../probes/basic/spec/ramrec.py)), typed on both machines as two programs, groups FX (the first
run's cases) and FY (goldfish pass 1's separating cases); run file
[`scratchpad/KFR_run1.out`](../../scratchpad/KFR_run1.out) (2026-11-25). Every case is its own line and starts from
nothing (`CLEAR`, `ON ERROR` set again); the body counts its runs in WN%; the next line records the FIRST error, the
LAST error and how many there were (RESUME NEXT carries on along the line, so after a failed FOR its body and NEXT
still run), the runs and the loop variable's bytes (VARPTR; a variable that does not exist reads "none" -- VARPTR
refuses it on both machines, KFR FY 31). The readout uses no FOR / NEXT (two subroutines of POKEs). A loop that could
run for ever carries a guard, `ON -(WN%>20) GOTO <the record line>` -- not `IF ... THEN`, whose false test would skip
the NEXT after it on the same line -- so 21 runs read "more than 20". The model,
[`kfor_model.py`](../../probes/basic/spec/kfor_model.py), is an INTERPRETER: it runs each case's own statements with
the laws the rules state and holds no per-case answer. Probe faults caught while building it: the last error alone
recorded, the IF guard, a VARPTR of a variable that does not exist (error 5), a FOR that failed and left a half-built
frame on zerobas (every counting body has the guard since), a readout that used FOR / NEXT itself, and -- unrolling
that readout inline -- a program too big for the RAM below HIMEM (both machines stopped while it was typed; hence the
two groups).
- **[KFR FX *i*]** (FOR):
  0: `FOR I=1 TO 3:WN%=WN%+1:<guard>:NEXT`, reads I
  1: `FOR I=1 TO 1:WN%=WN%+1:<guard>:NEXT`, reads I
  2: `FOR I=3 TO 1:WN%=WN%+1:<guard>:NEXT`, reads I
  3: `FOR I=3 TO 1 STEP -1:WN%=WN%+1:<guard>:NEXT`, reads I
  4: `FOR I=1 TO 3 STEP -1:WN%=WN%+1:<guard>:NEXT`, reads I
  5: `FOR I=1 TO 3 STEP 0:WN%=WN%+1:<guard>:NEXT`, reads I
  6: `FOR I=3 TO 1 STEP 0:WN%=WN%+1:<guard>:NEXT`, reads I
  7: `FOR I=0 TO 1 STEP .1:WN%=WN%+1:<guard>:NEXT`, reads I
  8: `FOR I!=0 TO 1 STEP .1:WN%=WN%+1:<guard>:NEXT`, reads I!
  9: `FOR I#=0 TO 1 STEP .1#:WN%=WN%+1:<guard>:NEXT`, reads I#
  10: `FOR I%=1 TO 3:WN%=WN%+1:<guard>:NEXT`, reads I%
  11: `FOR I%=32765 TO 32767:WN%=WN%+1:<guard>:NEXT`, reads I%
  12: `FOR I%=-32766 TO -32768 STEP -1:WN%=WN%+1:<guard>:NEXT`, reads I%
  13: `FOR I%=1 TO 3 STEP .5:WN%=WN%+1:<guard>:NEXT`, reads I%
  14: `FOR I%=1 TO 3.7:WN%=WN%+1:<guard>:NEXT`, reads I%
  15: `FOR I%=1.6 TO 3:WN%=WN%+1:<guard>:NEXT`, reads I%
  16: `FOR I%=1 TO 40000:WN%=WN%+1:<guard>:NEXT`, reads I%
  17: `FOR I=1 TO 3:WN%=WN%+1:<guard>:I=5:NEXT`, reads I
  18: `WL=3:FOR I=1 TO WL:WN%=WN%+1:<guard>:WL=1:NEXT`, reads I
  19: `WS=1:FOR I=1 TO 5 STEP WS:WN%=WN%+1:<guard>:WS=2:NEXT`, reads I
  20: `FOR I=1 TO 2:FOR J=1 TO 3:WN%=WN%+1:<guard>:NEXT J,I`, reads J
  21: `FOR I=1 TO 2:FOR J=1 TO 3:WN%=WN%+1:<guard>:NEXT:NEXT`, reads I
  23: `FOR I=1 TO 2:FOR I=1 TO 3:WN%=WN%+1:<guard>:NEXT I`, reads I
  24: `FOR I=1 TO 2`, reads I
  25: `FOR A$="A" TO "B":WN%=WN%+1:<guard>:NEXT`
  26: `FOR I=1 TO "A":WN%=WN%+1:<guard>:NEXT`, reads I
  27: `FOR I=1`, reads I
  28: `FOR I=1 TO`, reads I
  29: `FOR I TO 3`, reads I
  30: `FOR 1=1 TO 3`
  31: `FOR Q(1)=1 TO 3:WN%=WN%+1:<guard>:NEXT`
  32: `FOR I=1 TO 3 STEP:WN%=WN%+1:<guard>:NEXT`, reads I
  33: `FOR I=1/0 TO 3:WN%=WN%+1:<guard>:NEXT`, reads I
  34: `FOR I=1 TO 1/0:WN%=WN%+1:<guard>:NEXT`, reads I
  42: `FOR I=1 TO 2 STEP "A":WN%=WN%+1:<guard>:NEXT`, reads I
- **[KFR FY *i*]** (FOR, goldfish pass 1):
  0: `FOR I=1:WN%=WN%+1:<guard>:NEXT`, reads I
  1: `FOR I TO 3:WN%=WN%+1:<guard>:NEXT`, reads I
  2: `FOR I=1 TO:WN%=WN%+1:<guard>:NEXT`, reads I
  3: `FOR 1=1 TO 3:WN%=WN%+1:<guard>:NEXT`, reads I
  4: `FOR I=1 TO 1 STEP 0:WN%=WN%+1:<guard>:NEXT`, reads I
  5: `FOR I%=-1.6 TO 0:WN%=WN%+1:<guard>:NEXT`, reads I%
  6: `FOR I%=1 TO 5 STEP 1.5:WN%=WN%+1:<guard>:NEXT`, reads I%
  7: `FOR I%=3 TO 1 STEP -.5:WN%=WN%+1:<guard>:NEXT`, reads I%
  8: `FOR I%=1 TO -40000 STEP -1:WN%=WN%+1:<guard>:NEXT`, reads I%
  9: `FOR I%=40000 TO 1:WN%=WN%+1:<guard>:NEXT`, reads I%
  10: `FOR I%=1 TO 3 STEP 40000:WN%=WN%+1:<guard>:NEXT`, reads I%
  11: `FOR I%=32766 TO 32767.9:WN%=WN%+1:<guard>:NEXT`, reads I%
  12: `FOR I!=0 TO 1 STEP 1/3:WN%=WN%+1:<guard>:NEXT`, reads I!
  13: `FOR I#=0 TO 1 STEP 1/3:WN%=WN%+1:<guard>:NEXT`, reads I#
  14: `FOR I=1 TO 3 STEP 1/0:WN%=WN%+1:<guard>:NEXT`, reads I
  15: `FOR I="A" TO 3:WN%=WN%+1:<guard>:NEXT`, reads I
  16: `FOR I=1 TO 2 STEP 1,2:WN%=WN%+1:<guard>:NEXT`, reads I
  17: `WL=1:FOR I=1 TO WL:WN%=WN%+1:<guard>:WL=3:NEXT`, reads I
  18: `FOR I=1 TO 2:FOR I=1 TO 3:WN%=WN%+1:<guard>:NEXT I:NEXT I`, reads I
  19: `FOR I=1 TO 2:FOR J=1 TO 2:FOR I=1 TO 3:WN%=WN%+1:<guard>:NEXT I:NEXT J`, reads J
  20: `I=7:FOR I=1/0 TO 3:WN%=WN%+1:<guard>:NEXT`, reads I
  21: `I=7:FOR I TO 3:WN%=WN%+1:<guard>:NEXT`, reads I
  22: `I=7:FOR I=1 TO 40000:WN%=WN%+1:<guard>:NEXT`, reads I

**Controls** ([`kfor_controls.py`](../../probes/basic/spec/kfor_controls.py)): each changes ONE law of the interpreter model and runs over the reference's cases: “a start past the limit skips the body (0 runs)” is FALSE on 2 of the 6 cases R-FOR-RUNS selects (e.g. KFR FX 2); “STEP 0 ends at the limit (Microsoft's sign compare)” is FALSE on 1 of the 3 cases R-FOR-STEP0 selects (e.g. KFR FY 4); “STEP 0 is a positive step -- zerobas's” is FALSE on 1 of the 3 cases R-FOR-STEP0 selects (e.g. KFR FX 6); “the limit re-read at every NEXT” is FALSE on 2 of the 4 cases R-FOR-ONCE selects (e.g. KFR FX 18); “the step re-read at every NEXT” is FALSE on 1 of the 4 cases R-FOR-ONCE selects (e.g. KFR FX 19); “NEXT counts a private copy kept in the frame” is FALSE on 1 of the 4 cases R-FOR-ONCE selects (e.g. KFR FX 17); “a FOR on a variable with a frame replaces it (and the frames above)” is FALSE on 2 of the 6 cases R-FOR-NEST selects (e.g. KFR FY 18); “the sum is not rounded to the variable's type” is FALSE on 2 of the 5 cases R-FOR-FRACTION selects (e.g. KFR FY 12); “an integer variable ROUNDS start and limit” is FALSE on 3 of the 7 cases R-FOR-INT selects (e.g. KFR FX 14); “an integer variable FLOORS (towards minus infinity)” is FALSE on 2 of the 7 cases R-FOR-INT selects (e.g. KFR FY 5); “an integer variable keeps a fractional STEP, the sum cut -- zerobas's” is FALSE on 1 of the 7 cases R-FOR-INT selects (e.g. KFR FY 7); “32767 + 1 wraps to -32768” is FALSE on 6 of the 7 cases R-FOR-OVERFLOW selects (e.g. KFR FX 11); “the range is checked before the cut” is FALSE on 1 of the 7 cases R-FOR-OVERFLOW selects (e.g. KFR FY 11); “the variable is made only after `=`” is FALSE on 1 of the 15 cases R-FOR-ERRORS selects (e.g. KFR FX 29); “the start is stored only once the whole FOR has parsed” is FALSE on 7 of the 15 cases R-FOR-ERRORS selects (e.g. KFR FX 26); “a FOR error ends the line” is FALSE on 5 of the 5 cases R-FOR-NOFRAME selects (e.g. KFR FY 0); “text after STEP's value is caught before the push” is FALSE on 1 of the 5 cases R-FOR-NOFRAME selects (e.g. KFR FY 16).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/for_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/for_rules.py --write` -->

**9 rules; 9 hold on the reference. Of the 290 recorded outputs (each case's first and last error, the number of errors, the body's runs (WN%, 21 = the probe's guard ended a loop that did not stop) and the loop variable's value after it): 290 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The loop

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-FOR-RUNS** FOR stores the start in the variable, and the body runs AT LEAST ONCE -- also when the start is already past the limit. NEXT adds STEP (default 1) and runs the body again unless the variable has passed the limit in STEP's direction, so a loop ends one step past the last value its body saw (FOR I=1 TO 3: I 4; FOR I=3 TO 1: one run, I 4). | 6 | ✓ | ✓ |
| **R-FOR-FRACTION** STEP is converted to the variable's type at FOR and the sum is stored in that type: STEP 1/3 is .333333 for a single (4 runs, ending at 1.33333) and fourteen digits for a double. | 5 | ✓ | ✓ |
| **R-FOR-STEP0** STEP 0 never ends -- with the start below, at or past the limit (the probe's guard stops all three). | 3 | ✓ | ✗ 1: KFR FX 6 |
| **R-FOR-ONCE** The limit and STEP are evaluated once, at FOR: changing them in the body changes nothing. The VARIABLE is the counter itself: I=5 in the body ends the loop after one run with I 6. | 4 | ✓ | ✓ |
| **R-FOR-NEST** Loops nest, and a FOR pushes its frame ON TOP even when its variable already has one: FOR I=1 TO 2:FOR I=1 TO 3 ... NEXT I:NEXT I runs 3 bodies and ends with no error (I 5); a FOR on I above an open FOR J leaves J's frame alone. A FOR without NEXT is no error. | 6 | ✓ | ✓ |

#### 2. An integer loop variable

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-FOR-INT** An integer variable cuts the start, the limit and the STEP towards zero at FOR (-1.6 is -1; STEP 1.5 is 1; STEP .5 and -.5 are 0 and never end). | 7 | ✓ | ✗ 2: KFR FY 6, KFR FY 7 |
| **R-FOR-OVERFLOW** A start, limit or STEP an integer variable cannot hold is error 6 (Overflow) at the FOR, after the cut (32767.9 is 32767 and fits); stepping past 32767 or below -32768 is error 6 at NEXT, the variable keeping its last value. | 7 | ✓ | ✗ 4: KFR FX 16, KFR FY 8, KFR FY 9, KFR FY 10 |

#### 3. Errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-FOR-ERRORS** FOR works in order, and an error stops it where it stands: the variable is MADE first (a number as the variable makes nothing; an array element is error 2), then `=` (error 2), then the start is evaluated and STORED (its own error, or 13 for a string; a variable that existed keeps its value), then TO (error 2), the limit (nothing: 24; a string: 13), STEP (nothing: 24). A string variable is 13. | 15 | ✓ | ✓ |
| **R-FOR-NOFRAME** A FOR that stops on an error pushes NO frame: RESUME NEXT goes on with the statement after it, so the body runs once and its NEXT is error 1. Text after STEP's value is the one error that comes after the push: error 2, and the loop then runs. | 5 | ✓ | ✗ 1: KFR FY 16 |

<!-- RULES END -->

## Differences from the reference

- **An integer loop's bounds** (rules R-FOR-OVERFLOW, R-FOR-INT; cases KFR FX 16, FY 6 - 10;
  [D-FORINTLIM](../../todo/open/D-FORINTLIM.md)): the reference converts the start, limit and step to the
  variable's type at the FOR -- out of range is Overflow there, a fraction is cut. zerobas loops on a start or limit
  out of range, raises a step's Overflow only at the NEXT, and keeps a fractional step (STEP 1.5: 4 runs, not 5).
- **Text after STEP's value** (rule R-FOR-NOFRAME, case KFR FY 16; [D-FORCOMMA](../../todo/open/D-FORCOMMA.md)):
  `FOR I=1 TO 2 STEP 1,2` is one Syntax error on the reference and two on zerobas; the loop runs the same.
- **STEP 0 with the start past the limit** (rule R-FOR-STEP0, case KFR FX 6; [D-FORSTEP0](../../todo/open/D-FORSTEP0.md)):
  `FOR I=3 TO 1 STEP 0` never ends there; zerobas runs the body once.

The rung not yet proven is **RAM usage**. The loop's record on the stack was rebuilt at the reference's own size, 25
bytes, in September 2026; the cell-by-cell RAM comparison has not yet proven the rung.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] FOR inside GOSUB and GOSUB inside FOR, RETURN out of a loop, a loop left by GOTO and entered again many times
  (the frame's reuse), the nesting depth against free memory -- the flow region's next units.
- [A] A double loop variable beyond the integer range (`FOR A=56700 TO 56702`), DEFINT / DEFSTR'd names; ERL
  (where an error is raised: the record says WHICH error, not which statement).

## What we found, and how

- **A new loop variable was created after its start value** (fixed
  2026-10-19, D-LETNEWFIRST, with `LET`'s identical case). `FOR I=FRE(0) TO
  ...` with no `I` yet read 11 bytes more than on the VG-8020
  ([`letnew_run.out`](../../scratchpad/letnew_run.out)). `FOR` now creates the
  variable first and stores the start value straight into it.
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

## Related concepts

- [Variables](../concepts/variables.md) — names, types, arrays, and where they live

## Tests that cover it

- `make forvar-acceptance` — loop-variable names and types, and the ten
  decimal-arithmetic rows (fractional step and start, past the integer range,
  the 32767 edge, a body that changes the variable).
- `make kwsweep` — the three everyday rows (implied, explicit and negative
  step) and the error rows for {2, 13, 24}.
- `make kwram` — the RAM-usage comparison.
