<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `DIM` — declare an array

> **Spec:** DRAFT 1 (2026-11-25) — 37 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kdim.py`](../../probes/basic/spec/kdim.py), with DIM's, ERASE's and CLEAR's cases
> together; it reads the screen); every rule is executable, every recorded output is read by one, and
> every rule is pinned by a control of its own. Goldfish pass 1 acted on
> (2026-11-25, 19 more cases); not yet re-reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-10-10):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: how close to the end of free memory an array may reach (below),
> now about 30 bytes where it was about 170.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`DIM A(10)` creates an array `A` with elements `A(0)` to `A(10)`;
`DIM B$(3,4)` creates a two-dimensional string array. The new elements are 0
(or empty strings). zerobas behaves like the Philips VG-8020 in every case we
have measured, errors included, except at the very edge of free memory.

## Syntax

```
DIM <name>(<bound>[,<bound>]...)[,<name>(<bound>[,<bound>]...)]...
```

Each bound is a numeric expression. The name may carry a type suffix (`%`,
`!`, `#`, `$`); without one it has the default type, which is double precision
unless a `DEFINT`/`DEFSNG`/`DEFSTR` says otherwise.

## Details

- **Subscripts start at 0**: `DIM A(3)` has four elements.
- **There is no limit on the number of dimensions** that a program line can
  reach; the reference was measured storing and reading an element through 32
  subscripts.
- **An array used without `DIM` is created with bound 10 in every dimension**
  on first use, so `A(11)` on an undeclared `A` is `Subscript out of range`.
- **The size check is on bytes, before anything is allocated.** If the
  elements need more than 65535 bytes (2 per integer, 4 per single, 8 per
  double, 3 per string), the answer is `Subscript out of range`; if they fit
  that limit but not in free memory, it is `Out of memory`. So `DIM Q%(200,200)`
  is `Subscript out of range` although neither bound is large.
- **Several arrays in one `DIM` are created one by one.** In
  `DIM P(3),Q(-1)`, `P` is created and then `Q` fails; `P` stays.
- **`DIM` an existing array again is `Redimensioned array`** — whatever the new
  bounds. Use [`ERASE`](ERASE.md) first.
- **A name with no bounds is accepted and does nothing**: `DIM A` and
  `DIM A,B(2)` run without error, and `A` is not created.

| you write | you get |
|---|---|
| `DIM A(-1)` | 5 `Illegal function call` |
| `DIM A(70000)` | 6 `Overflow` |
| `DIM A(10000)` (80008 bytes of doubles) | 9 `Subscript out of range` |
| `A(9)=1` after `DIM A(3)` | 9 `Subscript out of range` |
| `DIM A(2):DIM A(2)` | 10 `Redimensioned array` |
| `DIM A("X")` | 13 `Type mismatch` |
| `DIM 5`, bare `DIM`, `DIM A,` | 2 `Syntax error` |
| more elements than free memory | 7 `Out of memory` |

The measured set of errors for `DIM` is {2, 5, 6, 7, 9, 10, 13} for one dimension
and {5, 9, 10, 13} for several, the same on both machines.

## Example

```
10 DIM A(3),B$(2,1)
20 FOR I=0 TO 3:A(I)=I*I:NEXT
30 B$(2,1)="HI"
40 PRINT A(3);B$(2,1)
50 ON ERROR GOTO 80
60 A(4)=1
70 DIM A(5):END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 9 HI
Error 9
Error 10
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_dim.out`](../../scratchpad/kwdoc_dim.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/dim_rules.py`](../../probes/basic/spec/dim_rules.py), loader in
[`kdim_model.py`](../../probes/basic/spec/kdim_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does. The check is the
whole interpreter; what pins a rule's SENTENCE is its controls -- each rule has at least one rival law that is false
on its own cases.

**Evidence.** One probe, [`probes/basic/spec/kdim.py`](../../probes/basic/spec/kdim.py): it reads the SCREEN, as
[`kstop.py`](../../probes/basic/spec/kstop.py) does -- each case starts with `NEW` and `CLS`, types a short program
and the commands it names, and keeps the normalised screen (the prompt -- "Ok" there, "ZB" here, a deliberate
difference -- read as one token). The memory-limit cases are far from the edge (`DIM A%(20000)`, `CLEAR 30000` exceed
any free memory a 32 K VG-8020 has -- `CLEAR 30000` by a few hundred bytes only), and the model's
one memory figure (29000 bytes, which the string space and the arrays share) sits between the reference's
accepted CLEAR 28000 and refused CLEAR 30000. The model is kstop's small
BASIC ([`kstop_model.py`](../../probes/basic/spec/kstop_model.py)), the one interpreter for every screen-reading keyword
probe. Run file [`scratchpad/KDM_run1.out`](../../scratchpad/KDM_run1.out) (JSON, 2026-11-25).
- **[KDM FX *i*]** (DIM), the lines typed after NEW / CLS:
  0: `10 DIM A(3):A(3)=7:PRINT A(3);A(0)` / `RUN`
  1: `10 DIM A(3):A(4)=1` / `RUN`
  2: `10 A(10)=5:PRINT A(10)` / `RUN`
  3: `10 A(11)=5` / `RUN`
  4: `10 DIM A(2,3):A(2,3)=4:PRINT A(2,3)` / `RUN`
  5: `10 DIM A(-1)` / `RUN`
  6: `10 DIM A(70000)` / `RUN`
  7: `10 DIM A(10000)` / `RUN`
  8: `10 DIM Q%(200,200)` / `RUN`
  9: `10 DIM A%(20000)` / `RUN`
  10: `10 DIM A(2):DIM A(2)` / `RUN`
  11: `10 DIM A("X")` / `RUN`
  12: `10 DIM 5` / `RUN`
  13: `10 DIM` / `RUN`
  14: `10 DIM A,` / `RUN`
  15: `10 ON ERROR GOTO 90:DIM P(3),Q(-1)` / `20 END` / `90 DIM P(5):PRINT "[N]":END` / `RUN`
  16: `10 DIM A:PRINT "[";A;"]"` / `RUN`
  17: `10 DIM A%(2),A(2):A%(1)=1.7:A(1)=1.7:PRINT A%(1);A(1)` / `RUN`
- **[KDM FY *i*]** (DIM, goldfish pass 1), the lines typed after NEW / CLS:
  8: `10 DIM A%(10000),B%(10000)` / `RUN`
  9: `10 DIM A#(2):ERASE A:PRINT "[E]"` / `RUN`
  10: `10 A#(3)=1:PRINT A(3)` / `RUN`
  11: `10 DIM AB1(2),AB2(2)` / `RUN`
  12: `10 DIM A%(32766)` / `RUN`
  13: `10 DIM A%(32767)` / `RUN`
  14: `10 DIM A!(16382)` / `RUN`
  15: `10 DIM A!(16383)` / `RUN`
  16: `10 DIM A$(21844)` / `RUN`
  17: `10 DIM A$(21845)` / `RUN`
  18: `10 DIM A(32768)` / `RUN`
  19: `10 B(10,10)=1:PRINT B(10,10)` / `RUN`
  20: `10 B(0,11)=1` / `RUN`
  21: `10 DIM A(2):ERASE A:A(10)=1:PRINT A(10)` / `RUN`
  22: `10 DIM A%(2):A%(1)=-1.7:PRINT A%(1)` / `RUN`
  23: `10 DIM A:DIM A(2):PRINT "[D]"` / `RUN`
  24: `10 A(-1)=1` / `RUN`
  25: `10 DIM A(2):A(1,1)=1` / `RUN`
  26: `10 DIM A(2.7):A(2)=1:A(3)=1` / `RUN`

**Controls** ([`kdim_controls.py`](../../probes/basic/spec/kdim_controls.py)): each changes ONE law of the interpreter and runs over the reference's cases; every rule has at least one of its own: “an undeclared array has bound 9” is FALSE on 3 of the 13 cases R-DIM-BOUNDS selects (e.g. KDM FX 2); “a negative subscript is error 9” is FALSE on 1 of the 13 cases R-DIM-BOUNDS selects (e.g. KDM FY 24); “there is no 65535-byte limit, only free memory” is FALSE on 5 of the 14 cases R-DIM-SIZE selects (e.g. KDM FX 7); “the name as written (suffix and all) is the identity” is FALSE on 3 of the 4 cases R-DIM-NAMES selects (e.g. KDM FY 9); “a DIM that fails makes none of its arrays” is FALSE on 1 of the 6 cases R-DIM-FORMS selects (e.g. KDM FX 15).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/dim_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/dim_rules.py --write` -->

**4 rules; 4 hold on the reference. Of the 189 recorded outputs (each case's normalised screen (prompts as <prompt>, the echo of the typed lines, the output, the messages)): 189 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. Bounds

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-DIM-BOUNDS** Subscripts run from 0 to the bound (DIM A(3): four elements); an array used without DIM is made with bound 10 in every dimension; past a bound is error 9 (Subscript out of range) -- so is the wrong number of subscripts; a NEGATIVE subscript is error 5. A bound is cut to an integer (DIM A(2.7) makes bound 2); after ERASE the default is 10 again. Arrays have any number of dimensions; an integer element stores the whole part, cut towards zero. | 13 | ✓ | ✓ |
| **R-DIM-NAMES** An array's identity is its first two characters and its TYPE: AB1 and AB2 are one array; with no DEF, A and A# are one (ERASE A removes A#; A#(3) is A(3)). A name without bounds makes nothing (DIM A, then DIM A(2), is no error). | 4 | ✓ | ✓ |

#### 2. Errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-DIM-SIZE** A negative bound is error 5; a bound too large for an integer (70000) error 6 (32768 already); a string bound 13. The elements -- 2 bytes an integer, 4 a single, 8 a double, 3 a string -- must fit 65535 BYTES, else error 9 however small the bounds (DIM Q%(200,200); 65536 bytes of any type); within that but past the memory left -- which the string space and every array already made share -- error 7. | 14 | ✓ | ✓ |
| **R-DIM-FORMS** DIM of an existing array is error 10 (Redimensioned array); a number for a name, DIM alone or a trailing comma error 2; a name without bounds is no error and makes nothing. Several arrays are made one by one: a failing one leaves those before it. | 6 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

**An array that leaves very little memory free fits on the VG-8020 and is
`Out of memory` here** (D-DIMRESERVE, open, a TIER 4 item). Size it with
`X=INT((FRE(0)-K)/8):DIM A(X)`: the VG-8020 accepts the `DIM` down to `K` = 110,
and zerobas down to `K` = 140 ([gate](../../probes/basic/basic_probe_dimedge.py)).
Until 2026-10-10 zerobas refused below `K` = 280, because it kept a fixed
256-byte reserve for its own stack ([readings](../../scratchpad/dimedge_run.out)).
Joost ruled on 2026-10-09: *"yes, we need to match reference there"*. Three
steps on 2026-10-10 did most of it. The expression evaluator was reworked, so a
simple statement needs 101 bytes of stack instead of 147 (the VG-8020: 79,
[after](../../scratchpad/stackhwref_after_s2.out)). Then the reserve was cut to
116 bytes, the deepest stack zerobas reaches without its expression check (92
bytes, in the line editor), plus room to spare
([statements](../../scratchpad/lowpoint_disk2.out),
[editor](../../scratchpad/lowpoint_dm.out)). The last 30 bytes are that
deeper stack.

Both machines behave alike just past the edge: the `DIM` fits, and the next
statement may itself be `Out of memory`, because a formula needs a little stack
too. The VG-8020 runs a simple `PRINT` again from about `K` = 126, zerobas from
about 192: zerobas's formula check keeps more in hand
([VG-8020](../../scratchpad/dimedge_ref_fine.out),
[zerobas](../../scratchpad/edgesafe_run.out)). That check was also tested at
this edge: no statement wrote into the array.

More generally, zerobas has less free memory than the VG-8020, so an array that
only just fits there can be `Out of memory` here. That is part of the **RAM
usage** rung, which is not yet proven.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] The exact free-memory edge (7 against no error), string arrays, 32 dimensions, an array element as
  a FOR variable.

## What we found, and how

- **Arrays arrived between 2026-07-15 and 2026-07-17**: numeric arrays with
  the auto-dimension to 10 first, then string arrays.
- **A huge `DIM` gave the wrong error** (fixed 2026-07-29, D-ARR-B):
  `DIM Q(20000)` was `Out of memory` here and `Subscript out of range` on the
  reference. Measuring the edge for each type showed the limit is 65535 bytes
  of elements, so it moves with the element size, and that it also applies to
  an array created without `DIM`
  ([arrdim-vg8020-characterization.md](../arrdim-vg8020-characterization.md)).
- **Arrays were limited to four dimensions** (fixed 2026-07-29, D-ARR-C). That
  limit had been written down as matching the reference and never measured;
  the reference has none ([arrdim-c-vg8020-characterization.md](../arrdim-c-vg8020-characterization.md)).
- **`DIM A` was a `Syntax error`** (fixed 2026-08-28, D-DIMBARE). The comment
  next to the code said a bound list was required; both references accept the
  bare name and ignore it ([spec-basic-dimbare.md](../spec-basic-dimbare.md)).
- **A deep formula could overwrite an array that filled memory** (fixed
  2026-09-27, D-STACKFLOOR). Looking into the reserve above showed nothing
  stopped a nested expression's stack from growing down into the arrays;
  the reference raises `Out of memory` instead. The evaluator now checks its
  stack as it goes.
- **The reserve at the end of memory was cut from 256 bytes to 116**
  (2026-10-10, D-DIMRESERVE). Two probes on zerobas's own stack measured how deep
  each kind of statement goes and how close it gets to the arrays
  ([`lowpoint_probe.py`](../../scratchpad/lowpoint_probe.py),
  [`edgesafe_probe.py`](../../scratchpad/edgesafe_probe.py)). With the reserve cut
  to 16 bytes, the second probe saw the stack write into the array, so it can
  tell ([knife](../../scratchpad/edgesafe_knife.out)).
- **A large `DIM` held the frame interrupt off** (fixed 2026-10-29,
  D-LATEINT). Clearing a new array, and moving the arrays up when a new
  variable appears after them, ran with the interrupt off: over 10 ms
  each with large arrays, so a frame came late. The VG-8020 keeps it on;
  zerobas now does too.

## Where it lives

- `ex_dim` in [basic/arrays.asm](../../basic/arrays.asm) reads the names and
  bounds; the array engine itself runs from the sub ROM —
  `aeng_dim` and `ary_alloc` in [sub/arrays.asm](../../sub/arrays.asm), which
  makes the size check before allocating.
- The evaluator's stack check is `stk_guard` in
  [basic/expr.asm](../../basic/expr.asm).
- The design notes are in [spec-basic-arrays.md](../spec-basic-arrays.md).

## Related concepts

- [The memory map](../concepts/memory-map.md) — where BASIC keeps things in RAM
- [Variables](../concepts/variables.md) — names, types, arrays, and where they live

## Tests that cover it

- `make array-acceptance` — creating, using, re-declaring and erasing arrays.
- `make arrdim-acceptance` — the size limit per type, the number of
  dimensions, and what a failed `DIM` leaves behind.
- `make ctllim-acceptance` — a deep formula next to an array that fills memory.
- `make kwsweep` — one- and multi-dimensional rows (the second reads the cell
  with its subscripts swapped) and the error rows.
- `make kwram` — the RAM-usage comparison.
- `make gcdi-acceptance`, row `dimshift` — large `DIM`, `ERASE` and new
  variables keep the frame interrupt, against the VG-8020.
