<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `FOR` — start a counted loop

> **Spec:** DRAFT 1 (2026-11-25) — 35 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kfor.py`](../../probes/basic/spec/kfor.py), with FOR's and NEXT's cases together);
> every rule is executable and every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-25):** level 2 — happy path ✓ · reasonable time ✓ · common
> errors ✗ (a FOR that fails still pushes its frame: D-FORFRAME) · RAM usage not yet proven · every error ✗
> (D-FORINTLIM, D-FORSTEP0).
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
- **A new loop variable is created before the start value is worked out**, as
  `LET` does: `FOR I=FRE(0) TO 9` with no `I` yet reads `FRE(0)` with I's
  11 bytes already spent, on both machines.
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
harness [`ramrec.py`](../../probes/basic/spec/ramrec.py)), typed on both machines; run file
[`scratchpad/KFR_run1.out`](../../scratchpad/KFR_run1.out) (2026-11-25; zerobas's side on that day's build). Every case
is its own line and starts from nothing (`CLEAR`, `ON ERROR` set again); the body counts its runs in WN%; the next line
records the FIRST error (the statement's own), the LAST error (RESUME NEXT carries on along the line, so after a failed
FOR its body and NEXT still run), the runs and the loop variable's bytes. A loop that could run for ever carries a
guard, `ON -(WN%>20) GOTO <the record line>` -- not `IF ... THEN`, whose false test would skip the NEXT after it on the
same line -- so 21 runs read "it did not stop". Three probe faults were caught while building it, each by a run that
read wrong on both machines: the last error alone recorded, the IF guard, and a VARPTR of a variable that does not
exist (error 5 on both machines).
- **[KFR FX *i*]** (FOR):
  0: `FOR I=1 TO 3:WN%=WN%+1:<guard>:NEXT`
  1: `FOR I=1 TO 1:WN%=WN%+1:<guard>:NEXT`
  2: `FOR I=3 TO 1:WN%=WN%+1:<guard>:NEXT`
  3: `FOR I=3 TO 1 STEP -1:WN%=WN%+1:<guard>:NEXT`
  4: `FOR I=1 TO 3 STEP -1:WN%=WN%+1:<guard>:NEXT`
  5: `FOR I=1 TO 3 STEP 0:WN%=WN%+1:<guard>:NEXT`
  6: `FOR I=3 TO 1 STEP 0:WN%=WN%+1:<guard>:NEXT`
  7: `FOR I=0 TO 1 STEP .1:WN%=WN%+1:<guard>:NEXT`
  8: `FOR I!=0 TO 1 STEP .1:WN%=WN%+1:<guard>:NEXT`
  9: `FOR I#=0 TO 1 STEP .1#:WN%=WN%+1:<guard>:NEXT`
  10: `FOR I%=1 TO 3:WN%=WN%+1:<guard>:NEXT`
  11: `FOR I%=32765 TO 32767:WN%=WN%+1:<guard>:NEXT`
  12: `FOR I%=-32766 TO -32768 STEP -1:WN%=WN%+1:<guard>:NEXT`
  13: `FOR I%=1 TO 3 STEP .5:WN%=WN%+1:<guard>:NEXT`
  14: `FOR I%=1 TO 3.7:WN%=WN%+1:<guard>:NEXT`
  15: `FOR I%=1.6 TO 3:WN%=WN%+1:<guard>:NEXT`
  16: `FOR I%=1 TO 40000:WN%=WN%+1:<guard>:NEXT`
  17: `FOR I=1 TO 3:WN%=WN%+1:<guard>:I=5:NEXT`
  18: `WL=3:FOR I=1 TO WL:WN%=WN%+1:<guard>:WL=1:NEXT`
  19: `WS=1:FOR I=1 TO 5 STEP WS:WN%=WN%+1:<guard>:WS=2:NEXT`
  20: `FOR I=1 TO 2:FOR J=1 TO 3:WN%=WN%+1:<guard>:NEXT J,I`
  21: `FOR I=1 TO 2:FOR J=1 TO 3:WN%=WN%+1:<guard>:NEXT:NEXT`
  23: `FOR I=1 TO 2:FOR I=1 TO 3:WN%=WN%+1:<guard>:NEXT I`
  24: `FOR I=1 TO 2`
  25: `FOR A$="A" TO "B":WN%=WN%+1:<guard>:NEXT`
  26: `FOR I=1 TO "A":WN%=WN%+1:<guard>:NEXT`
  27: `FOR I=1`
  28: `FOR I=1 TO`
  29: `FOR I TO 3`
  30: `FOR 1=1 TO 3`
  31: `FOR Q(1)=1 TO 3:WN%=WN%+1:<guard>:NEXT`
  32: `FOR I=1 TO 3 STEP:WN%=WN%+1:<guard>:NEXT`
  33: `FOR I=1/0 TO 3:WN%=WN%+1:<guard>:NEXT`
  34: `FOR I=1 TO 1/0:WN%=WN%+1:<guard>:NEXT`
  42: `FOR I=1 TO 2 STEP "A":WN%=WN%+1:<guard>:NEXT`

**Controls** ([`kfor_controls.py`](../../probes/basic/spec/kfor_controls.py)): each is a rival rule run over the
reference's cases: “a start past the limit skips the body (0 runs)” is FALSE on 2 of the 5 cases R-FOR-RUNS selects (e.g. KFR FX 2); “STEP 0 with the start past the limit runs once -- zerobas's” is FALSE on 1 of the 2 cases R-FOR-STEP0 selects (e.g. KFR FX 6); “the limit re-read at every NEXT” is FALSE on 1 of the 3 cases R-FOR-ONCE selects (e.g. KFR FX 18); “the step re-read at every NEXT” is FALSE on 1 of the 3 cases R-FOR-ONCE selects (e.g. KFR FX 19); “an integer variable ROUNDS start and limit” is FALSE on 2 of the 4 cases R-FOR-INT selects (e.g. KFR FX 14); “an integer variable keeps a fractional STEP” is FALSE on 1 of the 4 cases R-FOR-INT selects (e.g. KFR FX 13); “a failed FOR keeps its frame -- zerobas's” is FALSE on 3 of the 8 cases R-FOR-NOFRAME selects (e.g. KFR FX 26).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/for_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/for_rules.py --write` -->

**9 rules; 9 hold on the reference. Of the 140 recorded outputs (each case's first and last error, the body's runs (WN%, 21 = the probe's guard ended a loop that did not stop) and the loop variable's bytes after it): 140 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The loop

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-FOR-RUNS** FOR stores the start in the variable and the body runs AT LEAST ONCE; NEXT adds STEP (default 1) and runs the body again while the variable has not passed the limit in STEP's direction. FOR I=1 TO 3 runs 3 times and leaves I 4; FOR I=1 TO 1 once (I 2); FOR I=3 TO 1 once (I 4); FOR I=3 TO 1 STEP -1 3 times (I 0); FOR I=1 TO 3 STEP -1 once (I 0). | 5 | ✓ | ✓ |
| **R-FOR-FRACTION** A fractional STEP adds in the variable's own type: FOR I=0 TO 1 STEP .1 runs 11 times and ends at 1.1, for a double, a single or a double literal step alike. | 3 | ✓ | ✓ |
| **R-FOR-STEP0** STEP 0 never ends -- also when the start is already past the limit (FOR I=3 TO 1 STEP 0); the probe's guard stops both. | 2 | ✓ | ✗ 1: KFR FX 6 |
| **R-FOR-ONCE** The limit and STEP are evaluated once, at FOR: changing L or S in the body changes nothing (FOR I=1 TO L with L=1 in the body still runs 3 times; STEP S with S=2 still steps 1, 5 runs). Changing the VARIABLE does count: I=5 in the body ends the loop after one run with I 6. | 3 | ✓ | ✓ |
| **R-FOR-NEST** Loops nest: FOR I / FOR J closed by NEXT J,I or by two bare NEXTs run 6 bodies; a second FOR on the same variable replaces the first's frame (3 runs, not 6); a FOR without NEXT is no error (the body runs 0 times after it: the line ends). | 4 | ✓ | ✓ |

#### 2. An integer loop variable

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-FOR-INT** An integer variable TRUNCATES the start, the limit and the step: FOR I%=1.6 TO 3 and FOR I%=1 TO 3.7 both run 3 times (I% 4); STEP .5 is 0 and never ends. FOR I%=1 TO 3 leaves I% 4. | 4 | ✓ | ✓ |
| **R-FOR-OVERFLOW** Stepping an integer variable past 32767 or below -32768 is error 6 (Overflow) at NEXT, the variable keeping its last value (3 runs: I% 32767, or -32768); a LIMIT an integer variable cannot hold is error 6 at the FOR itself (FOR I%=1 TO 40000), and no frame is pushed. | 3 | ✓ | ✗ 1: KFR FX 16 |

#### 3. Errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-FOR-ERRORS** A string variable, limit or STEP is error 13 (Type mismatch); no TO, no `=`, a number or an array element as the variable error 2 (Syntax error); nothing after TO or after STEP error 24 (Missing operand); an error in the start or the limit is that error (1/0: 11). A shape error ends the line there (no body runs); the others leave the line running on (R-FOR-NOFRAME). | 11 | ✓ | ✗ 3: KFR FX 26, KFR FX 32, KFR FX 42 |
| **R-FOR-NOFRAME** A FOR that fails pushes NO frame: after RESUME NEXT the body runs once and its NEXT is error 1 (NEXT without FOR), the variable as the failed FOR left it. | 8 | ✓ | ✗ 4: KFR FX 16, KFR FX 26, KFR FX 32, KFR FX 42 |

<!-- RULES END -->

## Differences from the reference

- **A FOR that fails still pushes its frame** (rules R-FOR-NOFRAME and R-FOR-ERRORS; cases KFR FX 26, 32,
  42; [D-FORFRAME](../../todo/open/D-FORFRAME.md)). After `FOR I=1 TO "A"`, `FOR I=1 TO 3 STEP` or `FOR I=1 TO 2 STEP
  "A"` and RESUME NEXT, the reference's NEXT is NEXT without FOR; zerobas's iterates -- and with STEP missing or a
  string the step is 0, so the program hangs.
- **A limit an integer variable cannot hold** (rule R-FOR-OVERFLOW, case KFR FX 16;
  [D-FORINTLIM](../../todo/open/D-FORINTLIM.md)): `FOR I%=1 TO 40000` is Overflow at the FOR there; zerobas loops.
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
- [A] A double loop variable beyond the integer range (`FOR A=56700 TO 56702`), DEFINT / DEFSTR'd names.
- [A] STEP 0 with the start equal to the limit.

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
