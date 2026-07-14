# Spec — malformed intrinsic-function call → "syntax error" (repack build)

Status: **CONTRACT** (2026-07-14). Sibling of
[spec-basic-empty-expr-syntax-error.md](spec-basic-empty-expr-syntax-error.md)
(D-F2-3); this is **D-F2-4**. Repack build only (`ROM_BASE < $4000`); the lean
16 KB cart is untouched by construction (all affected code is inside
`IF ROM_BASE < $4000`). Origin: math-pack slice-2e (`RND`) adversarial review,
Finding 1 (disk/docs/tier2-review-queue.md; spec-basic-mathpack-slice2.md §15.7)
— deferred there to this dedicated family-wide fix.

## 1. The bug

A **malformed CALL** to any of the 15 `ev_mc_arg`-family intrinsic math
functions — `ABS SGN INT FIX CINT CSNG CDBL SQR ATN EXP LOG SIN COS TAN RND` —
does **not** raise the reference's `Syntax error`. Three malformed forms, all
reaching the same argument parser (`ev_mc_arg`, basic/expr.asm):

| Form | Example | reference | zerobas (repack) BEFORE |
|---|---|---|---|
| bare (no parens) | `PRINT SIN` | `Syntax error` | ` 0` (runs on stale operand) |
| bare | `PRINT LOG` | `Syntax error` | `illegal function call` (LOG(stale)) |
| bare | `PRINT RND` | `Syntax error` | ` .40649651372358` (RND(0)) |
| extra arg | `PRINT SIN(1,2)` | `Syntax error` | ` 0 … 2 syntax error` (garbage) |
| extra arg | `PRINT RND(1.5,2)` | `Syntax error` | advances seed + garbage + delayed err |
| unclosed | `PRINT SIN(1` | `Syntax error` | ` 0` |
| unclosed | `PRINT RND(-1.5` | `Syntax error` | **reseeds** the RND state (catastrophic) |

Plus a **latent regression** in the D-F2-3 (empty-parens) slice that the
transcendentals reintroduced: an EMPTY arg to a domain/overflow-checked
function raises the WRONG message, because the function's own check overwrites
the FPERR=4 the empty-parens gate had set:

| Form | Example | reference | zerobas (repack) BEFORE |
|---|---|---|---|
| empty | `PRINT LOG()` | `Syntax error` | `illegal function call` |
| empty | `PRINT LOG(1,2)` | `Syntax error` | `illegal function call` |
| empty | `PRINT SQR()` | `Syntax error` | `syntax error` (SQR(0) in-domain — OK by luck) |

(All BEFORE values captured live on VG-8020 reference / C-BIOS_MSX1_EU_REPACK_DISK
zerobas, 2026-07-14, `probes/lib/omsx_repl.py`; no ROM disasm.)

### 1.1 Root cause (two chokepoints)

`ev_mc_arg` parses `"(" <expr> ")"` from the selector byte. Its two error
exits — a missing `(` (bare / operator-after / space-separated) and a missing
`)` (extra arg / unclosed) — both `jp nz,ev_f_err`. **`ev_f_err` writes only
the `$DD` ERRMARK landmark and returns `DE=0`; it does NOT set FPERR**, so no
statement-abort is raised. The caller (`evmc_*`) then runs its body on the
stale FAC/ARGA:

- **pure total functions** (ABS SGN INT FIX ATN SIN COS TAN): harmless wrong
  value, silently returned (no error at all).
- **domain/overflow-checked** (SQR LOG EXP CINT CSNG CDBL): the check fires on
  the stale operand and sets FPERR=1/3 → a WRONG error message
  (`overflow`/`illegal function call`) instead of `syntax error`.
- **RND**: `evmc_rnd` runs `fp_rnd` on the stale operand and **mutates the
  persistent seed** — for an int stale operand it degrades to `RND(0)` (no
  advance, benign) because `ev_f_err` zeroed DE, but for a **float** stale
  operand `widen_rhs_operand` dispatches to `widen_fac_to` and reads the live
  FAC, so `RND(1.5,2)` **advances** and `RND(-1.5` **reseeds** the state,
  diverging every subsequent `RND` until the next `NEW`/`CLEAR`/`RUN`.

The **empty-parens** form (`SQR()`, `LOG()`) is a THIRD entry point: there
`ev_mc_arg` returns normally (the `)` is present) but FPERR=4 was set deep in
`ev_f_empty` (D-F2-3) while `ev_xor` parsed the empty arg. The function body
then runs anyway and (for LOG/EXP/CINT/…) clobbers FPERR=4. So a robust fix
must key on the FPERR **flag**, not on a return-path signal.

## 2. Reference contract (black-box, VG-8020, 2026-07-14)

Uniform: **every** malformed form of **every** one of the 15 functions →
`Syntax error`, and the **statement aborts before any side effect** (no output,
and for `RND` the seed is left untouched). Proven for `RND`: after a malformed
`RND` call of any form, the next `RND(1)` returns v1 = `.59521943994623` (the
first advance from the power-on seed S0), i.e. the malformed call did NOT
advance the seed — vs zerobas-BEFORE where `RND(1.5,2)` made the next `RND(1)`
return v2 = `.10658628050158` and `RND(-1.5` diverged entirely.

zerobas emits its own lowercase `syntax error` wording (the D-F2-3 message),
a documented wording divergence (like every F2 error), not the reference's
capitalised `Syntax error`.

## 3. The fix (D-F2-4) — two edits, both repack-only

**Invariant established:** *no `evmc_*` runs its body while a deferred error is
already pending.*

1. **`ev_mc_arg`'s two error exits** raise the deferred syntax error:
   `jp nz,ev_f_err` → `jp nz,ev_f_empty` (×2). `ev_f_empty` (D-F2-3) already
   sets `FPERR=4` and falls into `ev_f_err` (ERRMARK + `DE=0`). This handles the
   missing-`(` (bare/space/operator) and missing-`)` (extra/unclosed) forms.

2. **A shared gate** `ev_mc_arg_checked` = `call ev_mc_arg / ld a,(FPERR) /
   or a / ret` (returns Z iff FPERR==0). Every `evmc_*` changes its
   `call ev_mc_arg` → `call ev_mc_arg_checked` and adds `ret nz` immediately
   after. On a pending deferred error (from either exit above, OR the
   empty-parens `ev_f_empty` set deep inside a normal-return parse) the function
   returns to `eval` WITHOUT running its body:
   - no domain/overflow check → FPERR=4 (`syntax error`) is preserved, not
     clobbered to 3/1 (fixes the `LOG()`/`CINT()`/… latent regression);
   - no `fp_rnd` → the RND seed is left untouched (fixes the float-arg
     advance/reseed divergence);
   - the value returned to `eval` (`DE`, FAC) is discarded at the
     statement-boundary `check_expr_errors` (print.asm `exp_num` calls it right
     after `eval`, BEFORE `print_number`), so no partial output is emitted.

`ev_mc_arg_checked` clobbers only `A`; every `evmc_*` reloads `A`
(`ld a,(FACTYP)`) or ignores it, so the gate is transparent on the clean
(FPERR==0) path — the body runs byte-for-byte as before.

### 3.1 Why the guard is safe (no false bail)

`exec_stmt` (interp.asm) clears FPERR to 0 at the start of every statement, so
inside a factor FPERR is 0 unless THIS statement's eval set it. FPERR is only
ever set for HARD, statement-aborting errors (overflow=1, div-by-zero=2,
illegal=3, syntax=4). Therefore "FPERR set" ⟺ "the reference has already
aborted this statement", so skipping the function body is always correct — in
every operand ordering. E.g. `PRINT SQR(-1)+RND(1)`: SQR(-1) sets FPERR=3,
`RND(1)`'s gate then bails (seed untouched) — matching the reference, which
aborts at SQR(-1) before RND(1) runs. Symmetrically `PRINT RND(1)+SQR(-1)`
advances the seed first on BOTH (left-to-right eval) then aborts.

## 4. Scope / non-goals

- **In scope:** the 15 `ev_mc_arg`-family functions, forms: bare (missing
  `(`), extra arg / unclosed (missing `)`), empty (`f()`). All → `syntax error`,
  side-effect-free.
- **Out of scope (unchanged, pre-existing):**
  - The EOL `Missing operand` message (`PRINT 5+`) — still deferred from
    D-F2-3; zerobas has no such message.
  - Trailing-operator-after-a-malformed-factor interactions (`SIN*2`,
    `RND()+1`): these produce a clean `syntax error` here too (the gate sets
    FPERR=4 and `check_expr_errors` aborts before print), but the intervening
    binary op runs on a stale FAC; a pathological stale FAC could in principle
    set a different FPERR. This is a pre-existing empty-expr-era edge, not a
    malformed-CALL case, and is not addressed.
  - Non-`ev_mc_arg` functions (`PEEK`/`VPEEK`/`INP`/`USR`/`VARPTR`/`BASE`/
    string funcs) keep their own arg-parse contracts.
  - **Driver-coverage (pre-existing, unchanged):** the deferred FPERR=4 only
    becomes a visible `syntax error` in a statement driver that calls
    `check_expr_errors` after its `eval` — verified for `PRINT`, `LET`
    (`A=SIN`, `A=LOG()`), and `IF` (`IF SIN(1,2) THEN …`), including the RND
    seed-untouched property in `LET`. The **`FOR`** initial-value driver
    (`ex_for`) does NOT check FPERR, so `FOR I=SIN TO 3` yields `out of memory`
    (a stale-operand FOR set-up) instead of `Syntax error`. This is
    **pre-existing** — identical on the pre-fix build (bare `SIN` gave
    `out of memory` before and after) — and is a `FOR`-driver FPERR-propagation
    gap, not a malformed-CALL issue; the same class the D-F2-3 empty-parens
    slice also left to each driver. (`FOR I=SIN(1,2)` still errors via FOR's
    own missing-`TO` structural check.) Other numeric-expression drivers that
    may not propagate FPERR (`WHILE`, `ON…GOTO`, subscripts, `PRINT USING`)
    are the same pre-existing category and out of scope here.

## 5. Gate

`probes/basic/basic_probe_math_conv.py`, new `MALFORMED_CALL` battery — a
reference-DIFFERENTIAL (`run_differential`, reference == zerobas) over
representative functions spanning the behaviour classes:

- pure-total: `SIN`, `ABS`
- domain-checked (FPERR=3): `LOG`, `SQR`
- overflow-checked (FPERR=1): `CINT`
- stateful: `RND` — plus a **seed-untouched** sequence check (a malformed
  `RND(1.5,2)`/`RND(-1.5`/bare `RND` between two `RND(1)` calls must leave the
  second `RND(1)` equal to a clean first advance).

Forms per function: bare, extra-arg, unclosed, empty. All assert
reference-identical output (both emit their own "Syntax error"/"syntax error"
line; the differential compares the normalised error token + the surviving
RND sequence value, not the exact capitalisation).

## 6. Outcome — SHIPPED (2026-07-14)

Implemented in two commits (the `ev_mc_arg` exits + `ev_mc_arg_checked` gate +
15 site guards + the `MALFORMED_CALL` battery), then a review-fix commit for
the Fable adversarial pass below. All gates green: `math-acceptance` (full
value matrix + RND reference-identity + `MALFORMED_CALL` 33/33), `unit-test`
45/45, `float-acceptance`. Lean `basic.rom` byte-identical (same SHA-256 with
and without the change — verified by clean-tree rebuild). Every affected
context now reference-correct: PRINT / LET / IF give the reference's error,
RND's seed is provably untouched by a malformed call (incl. the LET context).

**Fable adversarial review — verdict SHIP, one real finding fixed:**

- **Finding 1 (NEW REGRESSION, FIXED):** the two new `jp nz,ev_f_empty` exits
  routed through `ev_f_empty`, which stored FPERR=4 **unconditionally** — so a
  malformed call whose *argument* already raised a hard error reported "syntax
  error" instead of that first error (`SIN(1/0,2)` → the reference's `Division
  by zero`; `SQR(9E62*9E62` → `Overflow`). The reference is first-error-wins.
  Fixed by making `ev_f_empty` store 4 only when FPERR==0 (keep any pending
  error). This ALSO repaired the **pre-existing D-F2-3 sibling** `(1/0)+()`
  (was `syntax error`, now `Division by zero`). New `errmatch` battery rows
  (`SIN/LOG/SQR/RND(1/0,2)`, `(1/0)+()`) lock it in — the original battery's
  args never errored, so this was matrix-invisible.
- **Finding 2 (hardening, DONE):** the gate now also bails on a pending D-2
  `TMISMATCH` (`RND("A")`), so the "no body runs while a deferred error is
  pending" invariant literally holds for BOTH deferred flags — previously RND's
  seed-safety under a type-mismatched arg was only incidental (the stale
  operand happened to be int-0). Verified: `RND("A")` → `type mismatch`, seed
  untouched.
- **Findings 3 & 4 (PRE-EXISTING, logged, NOT this fix's scope):** driver
  coverage — `FOR`/`SCREEN`/`COLOR`/`OUT`/`ON…GOTO`/`PRINT USING`/file-channel/
  etc. drivers don't check the deferred flags, so a malformed call there is
  silent or `out of memory` rather than `Syntax error` (identical before this
  commit; the commit only improves the stale value to 0); and stored-mode `RUN`
  continues past a deferred error instead of halting (the D-F2-1 statement-abort
  model, not this fix). Both logged to disk/docs/tier2-review-queue.md as the
  natural next steps for the deferred-error architecture.

Fable verified sound (no live divergence): stack/return balance of the
`ret nz` idiom across all 15 sites; no false bail on legal nested calls
(`RND(RND(RND(1)))`, `PRINT SQR(-1)+RND(1)` ordering); A-clobber transparent;
stale-FAC + trailing binary op effectively unreachable (cursor parks on a
non-operator, operands are 0); RND seed untouched in every ordering/form.
