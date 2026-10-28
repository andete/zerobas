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

## 2d. Family 2, measured (2026-10-28): OVERFLOW

[`deferr2_probe.py`](../scratchpad/deferr2_probe.py) ->
[`deferr2_run.out`](../scratchpad/deferr2_run.out) (a USR counter after the fault):
the VG-8020 raises an overflow INSIDE an expression at once -- `EXP(1000)`,
`VAL("&H1FFFF")`, `&B` with 17 digits, `1E38*1E38`, `CINT(40000)` all leave the
counter 0 -- while an overflow at the STORE (`A%=40000+USR(0)`) runs the USR
first (1), on both machines. zerobas defers four of the five (1); `&B` already
raises at once. VALTYP at the error
([`herro3_run.out`](../scratchpad/herro3_run.out)): EXP 2, VAL 2, `1E38*1E38` 8,
`X!*X!` 8, CINT 4, `&B` 8 on the VG-8020; zerobas agrees except CINT (2) and `&B`
(2). Prediction scored 1/6 on VALTYP and 7/7 on the reference's counter.

⚠️ Two of the writers are SHARED, so converting them converts more than the
rows measured: CINT overflows through `fac_to_int_go` (basic/float-arith.asm),
which is also `\`, MOD, AND / OR / XOR / NOT's operand conversion and the
address-domain arguments (POKE, VPOKE ...); the float multiply overflows in
`round_and_finalize`, shared by every float operation. ➡️ Before converting:
measure those other callers the same way (a USR counter after the fault, VALTYP
at the error) -- `1 AND 40000`, `NOT 40000`, `40000\1`, `1E38+1E38`, `1E38/1E-38`,
`POKE 70000+USR(0),1` -- then convert per writer. `EXP` (evmc_exp_overflow) and
`VAL` (evv_refuse) are single-site and can go first.

### 2d (cont.) Family 2, partly shipped (2026-10-28)

The other callers, measured ([`deferr2b_run.out`](../scratchpad/deferr2b_run.out)):
`1 AND 40000`, `NOT 40000`, `40000\1` and `1E38/1E-38` raise at once on the
VG-8020 (counter 0); `POKE 70000+USR(0),1` runs the USR first on both (the
address is converted after its expression). (`1E38+1E38` and `10^40` do not
overflow at all -- doubles reach ~1E63; a wrong premise of the case list.)

Converted: `EXP` (evmc_exp_overflow), `VAL` (evv_refuse's overflow arm; its
syntax arm stays deferred) and `&B` (evnl_bovf, now leaving VALTYP 8 as there).
`penderr_de0` lost its last caller and went (-6 B). After: 7/7 counter rows and
the VALTYP rows for EXP / VAL / `&B` as on the VG-8020
([`deferr2_after.out`](../scratchpad/deferr2_after.out),
[`herro3_after.out`](../scratchpad/herro3_after.out)). Gate: missing-acceptance
`ov-side`; knife K-DF2 ([`deferr2_knife.out`](../scratchpad/deferr2_knife.out)).

🔴 NOT converted, and why -- the build REFUSED it: `fac_to_int_go` (CINT, `\`,
AND/OR/XOR/NOT operands) and `check_preexp_bounds` (float `*` / `/` overflow)
are called by the sub-ROM's page-1 math TENANTS, where main page 1 -- and so
`fp_runtime_error` -- is switched out; tools/check_tenant_closure.py failed on
the raise's whole closure. These are §1b's UNSAFE class. ➡️ They need a
tenant-safe shape: a deferring entry for tenant callers and an immediate one for
main's, or a raise the tenant bridge performs on the way back.

### 2d (cont. 2) Family 2 complete (2026-10-28)

The tenant-safe shape, measured into place: `fac_to_int_go` turned out NOT to be in
the tenants' closure -- converting it ALONE builds clean (the first attempt changed
both writers at once, and only `check_preexp_bounds` -- reached through the
imported `fp_mul` / `fp_div` -- made the closure fail). So `fac_to_int_go` raises
at once (CINT, `\`, AND / OR / XOR / NOT operands; CINT now leaves VALTYP 4, as the
VG-8020, because the raise comes before FACTYP := 2). The float writer keeps
deferring for the tenants, and main's two callers (combine_mul, combine_div_float)
go through new page-1 wrappers `fp_mul_raise` / `fp_div_raise` (basic/expr.asm,
17 B of page 1, 0 of the low region) that raise right after it returns -- only
code 1, so a pending type mismatch keeps its own timing (D-TMORDER). After: all 22
rows of [`deferr2c_after.out`](../scratchpad/deferr2c_after.out),
[`deferr2bc_after.out`](../scratchpad/deferr2bc_after.out) and
[`herro3c_after.out`](../scratchpad/herro3c_after.out) as on the VG-8020. Gate:
missing-acceptance `ov-side2`; knife K-DF2C
([`deferr2c_knife.out`](../scratchpad/deferr2c_knife.out)).

## 2e. Family 3, syntax (2026-10-28)

[`deferr3_probe.py`](../scratchpad/deferr3_probe.py) ->
[`deferr3_run.out`](../scratchpad/deferr3_run.out): the VG-8020 raises a syntax
fault inside an expression at once -- nine forms (`SQR()`, `LEN()`, `VARPTR(5)`,
`INSTR("AB")`, a bare `USR`, `(1,2)`, `Q(1;2)`, `VAL("&")`, and `PRINT`'s
`SQR()` item) leave the USR counter 0. zerobas already did on six; `SQR()`,
`USR` and `VAL("&")` ran on. `ev_f_empty` -- the code-4 entry of the evaluator's
deferral tail, 16 callers, all syntax -- now raises at once (+3 B page 1), and
VAL's syntax arm goes there instead of deferring (-2 B low). NOT `ev_f_defer`
itself: its callers include `cl_not_oom`, the stack-floor family §1b keeps
deferred. After: 10/10 counter rows and the 10 original VALTYP rows unchanged
([`deferr3_after.out`](../scratchpad/deferr3_after.out),
[`deferr3_herro.out`](../scratchpad/deferr3_herro.out)). Gate:
missing-acceptance `sx-side`; knife K-DF3
([`deferr3_knife.out`](../scratchpad/deferr3_knife.out)).

## 2f. Family 4, overflow inside a math tenant (2026-10-28)

[`deferr4_probe.py`](../scratchpad/deferr4_probe.py) ->
[`deferr4_run.out`](../scratchpad/deferr4_run.out): the VG-8020 raises `10^1000`,
`.5^-2000` and `10^500.5` at once (counter 0); zerobas ran on. (`SIN(1E38)*...`
does not overflow at all there -- SIN(1E38) is 0, D-TANBIG.) The overflow is found
inside the sub-ROM power / exp tenant -- §1b UNSAFE (a) -- so it stays deferred
there, and every math tenant's way back, `cpow_tail`, now ends in a page-1
`mt_back` (basic/expr.asm, 15 B of page 1 on 2026-10-28, 0 of the low region)
that raises code 1 at once in main. After: 5/5, and families 2's rows unchanged
([`deferr4_after.out`](../scratchpad/deferr4_after.out),
[`deferr4_f2.out`](../scratchpad/deferr4_f2.out),
[`deferr4_h3.out`](../scratchpad/deferr4_h3.out)). Gate: missing-acceptance
`pw-side`; knife K-DF4 ([`deferr4_knife.out`](../scratchpad/deferr4_knife.out)).

## 3. Next

1. ~~Classify the writers~~ drafted (section 1b); the UNSURE rows are measured as the
   prototype reaches them.
2. ~~Pin the type-mismatch order~~ done (section 2b): D-TMORDER, its own item.
3. Step 2 of the TODO plan: first reorder CLEAR (evaluate both arguments before the
   POOLSIZE store), then convert Division by zero and the function-domain family to
   an immediate raise at their main-only points, with a pending-first helper; on a
   branch; full battery, the error rows, step 1a's probe, the tape collection, bytes.
