# Spec — empty-expression → "syntax error" (repack build)

Status: **IMPLEMENTED + GATED** (2026-07-13, "also gate `,`"). All acceptance
suites green (math/float/string/input + unit-test), reference-matching over the
characterized matrix (modulo zerobas's own lowercase wording).
Scope: `basic/expr.asm` factor parser (`ev_f`), `basic/interp.asm` error mapper.
Gated: **repack build only** (`ROM_BASE < $4000`); lean 16 KB cart unchanged.
Origin: SQR slice-1b adversarial review (2026-07-13) flagged this as a
**pre-existing** trait (not introduced by the math pack).

## 1. The bug

An empty-argument intrinsic call, or a bare empty parenthesised expression,
returns **0** on zerobas (repack) instead of raising an error like the
reference. Verified live on `PRINT SQR()`, `ABS()`, `INT()`, `CINT()`,
`SGN()`, `FIX()`, `CSNG()`, `CDBL()`, `PEEK()`, `SQR(())`, `SQR( )`, `()`.

Root cause: `ev_f` (the factor parser) reaches `ev_f_err` when a factor is
expected but the token is a closing `)`. `ev_f_err` writes only the **ERRMARK
landmark byte** (`$DD`, a probe marker) and returns `DE=0` — it does **not**
raise a real statement-abort. Every function's `( <expr> )` argument is parsed
through `ev_xor`/`ev_mc_arg`, so this is one general expression-layer trait,
not per-function.

## 2. Reference contract (black-box, VG-8020, 2026-07-13)

Characterized with `probes/lib/omsx_repl.py` (screen capture; no ROM disasm,
per clean-room rule). The reference distinguishes an empty factor by its
**terminator**:

| Input | Reference | zerobas (repack) now |
|---|---|---|
| `SQR()`,`ABS()`,`INT()`,`CINT()`,`SGN()`,`FIX()`,`CSNG()`,`CDBL()` | `Syntax error` | `0` |
| `PEEK()` | `Syntax error` | `243` (garbage: `peek(0)`) |
| `SQR(())`, `SQR( )` | `Syntax error` | `0` |
| `()` (bare parens) | `Syntax error` | `0` |
| `(5+)` (trailing op before `)`) | `Syntax error` | `5` (drops `+`) |
| `-()` | `Syntax error` | wedges |
| `(,)` | `Syntax error` | `0` |
| `5+`, `5*`, `-` (trailing op at **end of statement**) | **`Missing operand`** | wedges |
| `PRINT` (no args), `VAL("")` | valid (blank / `0`) | valid |
| `(5)`, `(5+6)` | valid | valid |

Two distinct reference errors: an empty factor **closed by `)`/`,`** →
`Syntax error`; an empty factor **at end-of-statement** → `Missing operand`.

zerobas's own wording is lowercase `syntax error` (the D-2 divergence idiom:
we do **not** copy the reference's capitalised strings; cf. `overflow`,
`type mismatch`, `illegal function call`). zerobas has **no** `Missing operand`
message.

## 3. Fix — reuse the FPERR deferred-abort plumbing

zerobas evaluators have **no mid-expression unwind**: an error SETs a flag and
yields a defined value; the statement-boundary driver checks the flag and
aborts (the D-F2-1 / D-2 pattern). `FPERR` (`$F069`) already carries codes
`1 overflow / 2 division-by-zero / 3 illegal-function-call`, is cleared per
statement at `exec_stmt`, and is checked by every numeric-eval driver
(`check_expr_errors`, `check_expr_errors_popbc`, and inline `ld a,(FPERR)` +
`jp nz,fp_runtime_error` in print/poke/vars/vdpio/str-engine/interp).

**Add code `4` = "syntax error".** Every existing FPERR checker then covers
the empty-expression case for free — no per-driver edits.

### 3.1 `ev_f` (basic/expr.asm) — detect the empty factor

At `ev_f` entry, after the existing `ev_sp`, add a **repack-gated** check:
a factor can never begin with `)`. When `(ix+0) == ')'`, set `FPERR=4`, fall
into the existing `ev_f_err` (which still sets `ERRMARK=$DD` and returns
`DE=0`). Precisely isolated: `ev_f` is called **only** where a factor is
required, so a leading `)` is unambiguously an empty expression. It does **not**
touch the many other `jp ev_f_err` sites (string type-mismatch, `ASC("")`
illegal-function-call, INSTR `p<1`, unknown `$FF` function, …) — those keep
their current disposition.

```
ev_f:
        call    ev_sp
    IF ROM_BASE < $4000
        ld      a,(ix+0)
        cp      ')'                 ; empty factor: a factor cannot start with
        jr      z,ev_f_empty        ;  a closing paren -> deferred syntax error
    ENDIF
        ld      a,(ix+0)
        cp      MINUS_TOKEN
        ...
    IF ROM_BASE < $4000
ev_f_empty:
        ld      a,4
        ld      (FPERR),a           ; deferred "syntax error" (checked at stmt boundary)
        ; fall through to ev_f_err (ERRMARK=$DD, DE=0, ret)
    ENDIF
ev_f_err:
        ...
```

### 3.1a Three gate sites (all feed `FPERR=4`)

The empty factor is detected wherever an argument/expression is parsed. Three
gates set `FPERR=4` (`ev_f_empty` in expr.asm, or a local set + `str_eval_no`),
covering every intrinsic and paren:

1. **`ev_f`** (expr.asm) — the numeric factor parser. Catches `SQR()`, `ABS()`,
   … `PEEK()`, `()`, `(5+)`, `-()`, `(,)`, and every function whose arg is a
   numeric expression (`CHR$()`/`STR$()`/`HEX$()`/`SPACE$()`/`STRING$()`/
   `INSTR()` all call `eval` on their arg → this gate; the PRINT `ems_print`
   FPERR check then aborts).
2. **`ev_str_arg`** (str-engine.asm) — the `( <string-expr> )` parser for the
   numeric-returning string functions **LEN/ASC/VAL**. Without this, the empty
   `)` failed via `jp ev_f_err`, whose `ret` landed in `ev_ff_len`'s
   continuation and read a **stale STRPTR** → a garbage length/byte printed
   before the error (`LEN()` → `255 syntax error`). Gating here sets `FPERR=4`
   on the first eval so `check_expr_errors` aborts before the garbage prints.
3. **`str_fn_left`/`str_fn_right`/`str_fn_mid`** (str-engine.asm) — these parse
   their string first-arg with `str_eval` (not `eval`), so the empty `)` fell
   back to the numeric path (`ev_ff_strnum` → `ev_f_err`) which returns 0
   **without advancing the cursor**, and the PRINT item loop **spun forever
   printing 0** (a pre-existing hard wedge). A shared `str_arg_empty` label sets
   `FPERR=4` then takes the ordinary `str_eval_no` exit → clean abort.

### 3.1b Makefile dependency fix (prerequisite)

`basic/str-engine.asm` and `basic/input.asm` were **missing from `$(DEPS)`** —
they are `include`d by main.asm but Make didn't treat them as prerequisites, so
edits to them did **not** trigger a rebuild (caught live: an str-engine edit
silently tested a stale ROM). Both added to `$(DEPS)`.

### 3.2 `fp_runtime_error` (basic/interp.asm) — map code 4

```
        cp      4
        jr      z,fre_syntax
        ...
fre_syntax:
        ld      hl,err_syntax       ; reuse stmt_error's own "syntax error" string
        jr      fre_abort
```

`err_syntax` (`"syntax error",13,10,0`) already exists in interp.asm.

### 3.3 Why the flag survives to the boundary

Downstream of the empty factor, the value `0` flows through the enclosing op
(`SQR()`→`fp_sqrt(0)`, `(5+)`→`combine_add(5,0)`, `CINT()`→convert `0`). Audit
confirms **every** `FPERR` write in the float ops is a SET on that op's *own*
error condition (overflow/divzero/illegal/domain); **none clears FPERR to 0 on
success**. `sqrt(0)`, `abs(0)`, `0+0`, `cint(0)` are all in-domain, so `FPERR=4`
is untouched until the next `exec_stmt` clears it. Confirmed by source audit of
float-arith.asm:{785,960,1261,1783} and expr.asm:1072.

## 4. Scope (SIGNED OFF: gate `)` AND `,`)

Gate `ev_f` on **both** `)` and `,`. Covers all reported cases plus `-()`,
`(5+)`, and `(,)`/stray-comma-in-parens (`sqr(1,2)`, `left$(a$,)`).

**Comma-regression audit — DONE (source, 2026-07-13), no valid construct routes
a leading `,` into `ev_f`:** the codebase idiom is universal — every driver
that permits an omitted comma-argument or a comma separator checks the
delimiter (`cp ','` / `cp ':'` / `or a`) and consumes/short-circuits it
**before** calling `eval`:
- `SCREEN` / `COLOR`: explicit `cp ','` skip of omitted args before each
  `eval` (screen.asm:48,63,72,87,100).
- `PRINT`: item loop dispatches `,`→tab, `;`, `:`, EOL before `exp_num`/`eval`
  (print.asm:124).
- `POKE addr,val`: `eval`; require `,`; `inc hl` past it; `eval` — the cursor
  is never on the comma at an `eval` call (poke.asm).
- `FOR i=a TO b STEP c`: each `eval` follows a consumed keyword/`=`, never a
  comma (program.asm).
- string funcs (LEFT$/MID$/INSTR/…): consume their own `,` in str-engine.asm
  before the numeric sub-arg eval; `left$(a$,)` now correctly errors.

So `ev_f` sees `,` only inside a parenthesised/argument expression after `(`
or a binary operator — always a genuine empty operand.

**Still out of scope** — the reference's *other* error, not this bug:
trailing op at end-of-statement (`5+`, `-`) → reference `Missing operand`
(an EOL terminator, not `)`/`,`); zerobas has no such message and `ev_f` at
EOL keeps its current 0-return. Noted as a deviation in §5.

## 5. Documentation

New divergence entry in `docs/spec-basic-float-core.md` §10.2 error model:
**D-F2-3 — empty parenthesised/argument expression → `syntax error`** (own
lowercase wording; the reference's end-of-statement `Missing operand` variant
is a noted deviation). Update FPERR equate comment in `sysvars.inc`
(`4 syntax error`).

## 6. Gate (DONE)

`probes/basic/basic_probe_math_conv.py` (the `make math-acceptance` gate) gains
an `EMPTY_ARG` battery. Each case is checked: **both** sides produce no value
span AND an error tail containing "error" (the "error" test rules out a runaway
`0 0 0…` tail as well as a value leak). Cases: `sqr()`, `abs()`, `int()`,
`cint()`, `sgn()`, `fix()`, `csng()`, `cdbl()`, `peek()`, `sqr(())`, `()`,
`(5+)`, `-()`, `(,)`, `len()`, `asc()`, `val()`, `chr$()`, `str$()`, `left$()`,
`right$()`, `mid$()`, `hex$()`, `space$()`, `string$()`, `instr()`. Regression
guards (must still print a value): `(5)`, `(5+6)` (+ the whole existing SQR/
CINT/ABS matrix). All green.

## 7. Regression results (all green, 2026-07-13)

`make unit-test` (45/45), `make math-acceptance`, `make float-acceptance`,
`make string-acceptance`, `make input-acceptance` — all PASS. Black-box
characterization (VG-8020 vs repack) matches across the full matrix except the
out-of-scope EOL `Missing operand` cases (§4). Lean 16 KB build compiles clean
and is unaffected (every change is `IF ROM_BASE < $4000`, and str-engine.asm is
included only in the repack build). No valid construct routes a leading `)`/`,`
into `ev_f`/`ev_str_arg`/`str_fn_*` — the codebase's universal "check the
delimiter before `eval`" idiom (SCREEN/COLOR/PRINT/POKE/FOR/string-fns) means a
`)`/`,` at a factor position is always a genuine empty operand.
```
