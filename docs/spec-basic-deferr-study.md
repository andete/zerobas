<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-DEFERRSTUDY — deferred errors against raising at the point of detection

Filed 2026-10-24 as TIER 1 at Joost's request (TODO.md, D-DEFERRSTUDY). The
question: how much of zerobas's per-command "which error wins" code exists only
because many faults are recorded as PENDING (`penderr_set`, first-error-wins) and
raised later at a realisation point (`check_expr_errors`, `check_fperr_only`,
`fperr_test`), where the VG-8020 behaves as if most faults are raised the moment
they are detected.

This document is the study's record. It grows one step at a time; nothing here is
a decision. Converting any family beyond the prototype is Joost's call.

## 1. The inventory (step 1, first count)

A grep of the tree on 2026-10-24 (writers and realisation points, by instruction):

| what | sites |
|---|---|
| `penderr_set` calls | 22 |
| direct `FPERR` / `TMISMATCH` stores | 6 |
| jumps into the deferral tails (`ev_f_defer`, `ev_f_empty`, `ev_f_ifc`, `type_mismatch_set`, `penderr_de0`) | 32 |
| realisation points (`check_expr_errors`, `check_fperr_only`, `fperr_test`) | 39 |

The writers sit almost entirely in the expression evaluator
([`basic/expr.asm`](../basic/expr.asm), [`basic/str-engine.asm`](../basic/str-engine.asm),
[`basic/float-arith.asm`](../basic/float-arith.asm), the math tenants in `sub/`); the
realisation points sit in the statement handlers. The per-site classification
("an immediate raise is equivalent" against "it protects state, which") is still to do.

## 2. Does evaluation run on past a fault? (step 1a, black-box)

A pending error and an immediate one differ observably only when something with a
visible effect happens between the fault and its realisation. Two such effects were
counted on both machines ([`deferr_side_probe.py`](../scratchpad/deferr_side_probe.py),
[`deferr_side_run.out`](../scratchpad/deferr_side_run.out)): a USR routine that counts
its calls (D-CATUSR's rig), placed after the faulting operand, and PRINT text after a
faulting item.

| case | VG-8020 count | zerobas count | reading |
|---|---|---|---|
| `A=1+USR(0)` (control) | 1 | 1 | the rig works |
| `A=1/0+USR(0)` | **0** | **1** | zerobas runs on past Division by zero |
| `A=(1/0)*(USR(0))` | **0** | **1** | the same, across parentheses |
| `A=SQR(-1)+USR(0)` | **0** | **1** | zerobas runs on past a function-domain fault |
| `A=ASC("")+USR(0)` | **0** | **1** | the same (`ev_f_ifc`) |
| `A=LEFT$("A",-1)+CHR$(USR(0))` | 0 | 0 | an argument range error already raises at once (the `*_checked` helpers) |
| `A%=40000+USR(0)` | 1 | 1 | not a test of deferral: the Overflow is the STORE into `A%`, after the operand |
| `A=1+"X"+USR(0)` | **1** | **0** | the other direction: the REFERENCE evaluates past the mismatch, zerobas raises first |
| `PRINT"[A]";1/0;"[B]"` (and `SQR(-1)`, `1/0;USR(0)`) | `[A]`, error, count 0 | the same | PRINT realises each item before the next |

What this shows:

* **Four observable divergences come from deferral alone**: Division by zero and the
  function-domain faults (`SQR`, `ASC("")`) are pending in zerobas and evaluation
  continues, so a later side effect happens that the reference never performs. This
  is the family the prototype (step 2) should convert, not the argument range checks
  first guessed: those already raise at once.
* **Type mismatch goes the other way.** The reference evaluates `USR(0)` after
  `1+"X"`; zerobas does not. Deferral cannot explain that direction; it is an
  evaluation-ORDER question for its own measurement.
* **PRINT already agrees**: its items are realised one by one.

Predictions made before the run, scored: "the reference counts 0 in every fault
case" missed `ovf` (a design error in the case) and `tm` (the reference is the lazy
one); "zerobas counts 1 in most fault cases" held for the four deferral cases and
missed `tm` and `fnarg`.

## 3. Next

1. Classify the ~60 writers (section 1) per site, starting with the domain-fault
   family of section 2.
2. Pin the type-mismatch order: where in `a+b+c` does the reference raise?
3. Step 2 of the TODO plan: convert the domain-fault family to an immediate raise on
   a branch; full battery, error rows, tape collection, bytes.
