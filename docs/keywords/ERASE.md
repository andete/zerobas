<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `ERASE` — remove an array

> **Spec:** DRAFT 1 (2026-11-25) — 8 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kdim.py`](../../probes/basic/spec/kdim.py), with DIM's, ERASE's and CLEAR's cases
> together; it reads the screen); every rule is executable, every recorded output is read by one, and
> every rule is pinned by a control of its own. Goldfish pass 1 acted on
> (2026-11-25, 0 more cases); not yet re-reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`ERASE A` removes the array `A` and frees its memory. Afterwards the name is
as if it had never been declared: a new [`DIM`](DIM.md) works without
`Redimensioned array`, and the new array starts out cleared. zerobas behaves
like the Philips VG-8020 in every case we have measured, errors included.

## Syntax

```
ERASE <array name>[,<array name>]...
```

Just the name, with its type suffix if it has one — no parentheses, no
subscripts.

## Details

- **The type suffix is part of the name**: `ERASE A` removes the default-type
  array `A` and leaves `A%` and `A$` alone.
- **Names are removed one by one, left to right.** In `ERASE P,Q` with no
  array `Q`, `P` is removed and then the statement fails on `Q`.
- **An array that does not exist is `Illegal function call`** (error 5) — never
  declared, already erased, or of another type.
- **Anything that is not a plain name is `Syntax error`** (error 2): a bare
  `ERASE`, `ERASE A(1)`, `ERASE A()`, `ERASE 5`, or a stray comma.

| you write | you get |
|---|---|
| `ERASE A` (`A` exists) | `A` is gone |
| `ERASE A` (no array `A`), `ERASE A` twice | 5 `Illegal function call` |
| `ERASE A%` when only `A` exists | 5 `Illegal function call` |
| `ERASE`, `ERASE A(1)`, `ERASE A,` | 2 `Syntax error` |

The whole set of errors `ERASE` can raise is {2, 5}, the same on both machines.

## Example

```
10 DIM A(5):A(1)=7
20 ERASE A
30 DIM A(5):PRINT A(1)
40 ON ERROR GOTO 70
50 ERASE A,Z
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
 0
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_erase.out`](../../scratchpad/kwdoc_erase.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/erase_rules.py`](../../probes/basic/spec/erase_rules.py), loader in
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
- **[KDM FX *i*]** (ERASE), the lines typed after NEW / CLS:
  18: `10 DIM A(2):A(1)=5:ERASE A:PRINT A(1)` / `RUN`
  19: `10 ERASE A` / `RUN`
  20: `10 DIM A(2):ERASE A:ERASE A` / `RUN`
  21: `10 DIM A(2):ERASE A%` / `RUN`
  22: `10 ERASE` / `RUN`
  23: `10 DIM A(2):ERASE A(1)` / `RUN`
  24: `10 ON ERROR GOTO 90:DIM P(3):ERASE P,Q` / `20 END` / `90 DIM P(5):PRINT "[E]":END` / `RUN`
  25: `10 DIM A(2):ERASE A:DIM A(5):PRINT "[R]"` / `RUN`

**Controls** ([`kdim_controls.py`](../../probes/basic/spec/kdim_controls.py)): each changes ONE law of the interpreter and runs over the reference's cases; every rule has at least one of its own: “an ERASE that fails erases none of its names” is FALSE on 1 of the 3 cases R-ERASE-REMOVE selects (e.g. KDM FX 24); “ERASE ignores the type suffix” is FALSE on 1 of the 5 cases R-ERASE-ERRORS selects (e.g. KDM FX 21).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/erase_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/erase_rules.py --write` -->

**2 rules; 2 hold on the reference. Of the 44 recorded outputs (each case's normalised screen (prompts as <prompt>, the echo of the typed lines, the output, the messages)): 44 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. Removing

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-ERASE-REMOVE** ERASE removes arrays one by one -- a later failing name leaves the earlier ones erased; the name is free again (used, it is a new array of bound 10; DIM works again). | 3 | ✓ | ✓ |

#### 2. Errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-ERASE-ERRORS** An array that does not exist -- never made, already erased, or of ANOTHER type (the suffix is part of the name) -- is error 5; ERASE alone or an element is error 2. | 5 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] ERASE inside a FOR over the array's element, ERASE of a DEF FN parameter's name, FRE after ERASE.

## What we found, and how

- **`ERASE` arrived on 2026-07-15**, with its two kinds of error measured
  first. A review before it shipped caught `ERASE A$` removing the *numeric*
  array `A`: inside zerobas the `$` name had been given the same type code as a
  default-type number. The string type is now kept apart, and a test for it
  was added ([spec-basic-arrays-slice2-erase.md](../spec-basic-arrays-slice2-erase.md)).
- **Erasing stops where it fails, and that was checked against the reference**
  (2026-09-09, D-PARTSTATE). Some statements are all-or-nothing on the
  reference; `ERASE P,Q` is not — `P` is gone after the error on both
  references ([readings](../../scratchpad/partialstate_run.out)).
- **The keyword sweep's first `ERASE` row proved nothing** (2026-09-14,
  D-KWBATCH5): it printed a fixed marker, which an `ERASE` that did nothing
  prints just as well. The row that counts now reads the effect — after
  `ERASE`, a second `DIM` succeeds and the element reads 0, where without it
  the `DIM` is `Redimensioned array`.
- **`ERASE` held the frame interrupt off** (fixed 2026-10-29,
  D-LATEINT). Moving the arrays after the erased one down ran with the
  interrupt off, over 10 ms for a few kilobytes of arrays; the VG-8020
  keeps it on, and zerobas now does too.

## Where it lives

`ex_erase` in [basic/arrays.asm](../../basic/arrays.asm) reads the names; the
array engine's `aeng_erase` in [sub/arrays.asm](../../sub/arrays.asm) finds
the array and closes the gap it leaves.

## Related concepts

- [Variables](../concepts/variables.md) — names, types, arrays, and where they live

## Tests that cover it

- `make array-acceptance` — erasing, re-declaring, types and both kinds of
  error.
- `make kwsweep` — the effect row and the error rows for {2, 5}.
- `make kwram` — the RAM-usage comparison.
- `make gcdi-acceptance`, row `dimshift` — `ERASE` keeps the frame
  interrupt, against the VG-8020.
