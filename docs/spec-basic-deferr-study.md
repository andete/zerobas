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

### 1b. The per-site classification (draft, 2026-10-24)

[`deferr_sites_table.md`](../scratchpad/deferr_sites_table.md): 67 writer sites (the grep
of section 1 plus 7 it missed: `arrays.asm:497`, `expr.asm:146` / `:725` / `:1758`,
`str-engine.asm:1054`, `deffn.asm:178`, and one store in disk.rom, `kernel.asm:1419`).
Read from the source; nothing was run. Verdict if the site raised at once: SAME 36,
DIFFERENT 2, UNSAFE 10, UNSURE 14, n/a 5. Two of its load-bearing claims were
checked by hand before this was written: CLEAR's ordering (below) and that the sub
ROM calls main's `fp_add` / `fp_mul` / `fp_div` by address
([`sub/basic-resident-abi.inc`](../sub/basic-resident-abi.inc)), so a raise inside them
would fire in tenant context.

* **UNSAFE** sites run inside a sub-ROM or disk-ROM tenant, or in main code those
  tenants call (`float-arith.asm`'s overflow and `fp_div` writers), or skip a
  restore (CLEAR's POOLSIZE). They stay deferred; where they matter, the raise
  happens in main after the tenant returns.
* **Division by zero** and the **function-domain** family convert at their
  main-only points (`combine_div_float`, `sdivmod_zerocheck`, `combine_pow`'s `0^-1`,
  the `ev_f_ifc` tail); `fp_div`'s own check stays deferred for the tenants.
* **Blocker:** CLEAR stores the new POOLSIZE before it evaluates its memory-top
  argument and restores it only on the deferred path, so `CLEAR 200,1/0` raised at
  once would leave the pool floor moved. That ordering changes first.
* **Rule for the immediate-raise helper:** report an already-pending code FIRST
  (`str_heap_oom_error`'s shape: `penderr_set`, then `fp_runtime_error`), or
  `POKE 99999,1/0` stops being ERR 6.
* **No realisation point becomes dead** from converting those two families: every
  one is still reached by overflow, type mismatch, syntax or out-of-memory. Code
  only becomes deletable if those convert too; what goes stale first is comment
  text and test rows.

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

## 2b. Where does a type mismatch raise? (step 1b, black-box)

Step 1a found the reference evaluating `USR(0)` after `1+"X"`. Ten variations
([`tmorder_probe.py`](../scratchpad/tmorder_probe.py),
[`tmorder_run.out`](../scratchpad/tmorder_run.out)):

| case | VG-8020 count | zerobas count |
|---|---|---|
| `A=1+"X"+USR(0)` | **1** | **0** |
| `A=1-"X"+USR(0)` | **1** | **0** |
| `A=1+"X"+USR(0)+1` | **1** | **0** |
| `A="X"+1+USR(0)` | **0** | **1** |
| `A=1+"X"*USR(0)` | 0 | 0 |
| `A=(1+"X")+USR(0)` | 0 | 0 |
| `A=1+"X"<USR(0)` | 0 | 0 |
| `A=1+"X" AND USR(0)` | 0 | 0 |
| `PRINT 1+"X";USR(0)` | 0 | 0 |
| `A=ABS(1+"X")+USR(0)` | 0 | 0 |

On the VG-8020 the USR runs only when a number-op-string is followed by another
additive operator (`+`, `-`); a higher-precedence operator, a closing parenthesis, a
relational, `AND`, a PRINT separator or a function argument all raise first. zerobas
raises early in the three additive cases and runs on past `"X"+1` (a string
concatenation given a number). That is an evaluation-ORDER divergence, not a
deferral one, in both directions; it is filed on its own as D-TMORDER (TIER 6).
The prediction ("the reference raises a mismatch only at the end of the expression")
missed: 7 of the 10 cases raise before the USR.

## 2c. Family 1 shipped (2026-10-27, Joost: "convert, family by family")

The prototype's family -- the expression DOMAIN faults -- is on main: Division by
zero at `/` (combine_div_float), `\` / `MOD` (sdivmod_zerocheck) and `0^-1`
(cpow), `SQR` / `LOG` (evmc_sqr_err), `(-x)^frac` (cpow_frac) and `ASC("")`
(ev_ff_asc), each raised AT ONCE through `raise_now` (pending-first: a code
already pending still wins). CLEAR's pool-size store moved after the memory-top
argument (the blocker, §1b). And each site leaves VALTYP as the VG-8020 does,
which the prototype did not: `raise_now8` (E = 8: `/`, SQR, LOG, `(-x)^frac`)
and `raise_now_t` (E = the type: `ASC("")` 3); `\` and `0^-1` already left 2
([`herro_run2.out`](../scratchpad/herro_run2.out) vs
[`deferr1_herro.out`](../scratchpad/deferr1_herro.out), 10/10). Side effects:
[`deferr1_side.out`](../scratchpad/deferr1_side.out) agrees with
[`deferr_side_run.out`](../scratchpad/deferr_side_run.out) on 11 of 12 -- the
twelfth, `1+"X"+USR(0)`, is a type mismatch, D-TMORDER's family, not this one.
Cost 13 B of the low region. Gate: missing-acceptance row `dz-side`; knife K-DF1
([`deferr1_knife.out`](../scratchpad/deferr1_knife.out)). The host tests that
called these routines as returning subroutines now see the raise through
msxtest's OPT-IN `raise_now` trap (`trap_raise_now()`), which keeps the code and
abandons the call -- opt-in because a test that runs a whole program must reach
the real error path (installed for every machine, it stopped test_forint's
ON ERROR handlers); the rows
that asserted the deferred tail's "result 0" are gone, with a note where they stood.

## 3. Next

1. ~~Classify the writers~~ drafted (section 1b); the UNSURE rows are measured as the
   prototype reaches them.
2. ~~Pin the type-mismatch order~~ done (section 2b): D-TMORDER, its own item.
3. Step 2 of the TODO plan: first reorder CLEAR (evaluate both arguments before the
   POOLSIZE store), then convert Division by zero and the function-domain family to
   an immediate raise at their main-only points, with a pending-first helper; on a
   branch; full battery, the error rows, step 1a's probe, the tape collection, bytes.
