# D-LEFTTM — `PRINT LEFT$(5,2)` answered Syntax error where both references say Type mismatch

*2026-08-29. `basic/str-engine.asm` (`ev_ff_strnum`'s string-only-token arm).
Probe `scratchpad/ngram8_probe.py`, arms `scratchpad/lefttm_knives.py`.*

**Cost: +16 B of the low region** (page-0 low 134 → 118 B free; page 1 unchanged
at 331). **Rows: 20, DIFF 5 → 0.**

## 1. The divergence

Filed by D-NGRAM8 and left open, with **both obvious fixes measured wrong**.

| row | references | before | after |
|---|---|---|---|
| `PRINT LEFT$(5,2)` | ERR 13 | ERR 2 | **ERR 13** |
| `PRINT RIGHT$(5,2)` | ERR 13 | ERR 2 | **ERR 13** |
| `PRINT MID$(5,1,2)` | ERR 13 | ERR 2 | **ERR 13** |
| `PRINT LEFT$(0*(1/0)+1)` | ERR 11 | ERR 2 | **ERR 11** |
| `PRINT MID$(0*(1/0)+1)` | ERR 11 | ERR 2 | **ERR 11** |

## 2. Where it actually lived

Not in `str_arg_snap`, where it was first attacked. `str_eval` **declines** a
non-string argument, the PRINT path re-drives the whole thing as a numeric
factor, and `ev_ff_strnum` meets a `$FF` token that is string-only
(`LEFT$`/`RIGHT$`/`MID$`). That arm read:

```
                jp      ev_f_empty          ; deferred FPERR=4 "syntax error"
```

— a fault armed **without ever looking at the argument**.

The reference rule is the opposite: **evaluate the argument and report what it
raises; only a clean expression is a type mismatch.** `ev_f_defer` is already
first-error-wins, so the fix is entirely one of *order*:

```
                inc     ix                  ; past the selector
                call    ev_sp
                cp      '('
                jr      nz,evff_strnum_tm   ; malformed: no argument to evaluate
                inc     ix
                call    ev_e                ; the argument -- it arms its OWN fault first
evff_strnum_tm:
                ld      e,FPERR_TYPEMM      ; -> ERR 13, unless the argument beat us
                jp      ev_f_defer
```

## 3. 🔴 The same mechanism, on the wrong side of the evaluation

D-NGRAM8 tried a deferred `type_mismatch_set` **in `str_arg_snap`** and it
measured wrong. This slice arms the *same code* for the *same reason* and it is
right — because at `str_arg_snap` the argument has **not yet been evaluated**, so
the mismatch arms first and first-error-wins then **blocks** the real fault; here
the argument has already run.

**That is not an argument, it is arm K-LT2.** It plants exactly the earlier
mistake — `penderr_set` moved ahead of `call ev_e`:

| row | fixed | K-LT2 (armed too early) |
|---|---|---|
| `s.left.bad` / `s.right.bad` / `s.mid.bad` | ERR 13 | **ERR 13 — unmoved** |
| `s.left.pexp` / `s.mid.pexp` | ERR 11 | **ERR 13** |

🎯 **The three clean-expression rows cannot tell the two fixes apart.** A row set
containing only `.bad` would have scored the wrong fix green — which is very
nearly what happened, since `.bad` was the whole original row set and the
`.pexp` rows were added by D-NGRAM8 only after a red gate.

## 4. Falsification

| arm | requires | measured |
|---|---|---|
| K-LT1 | restore `jp ev_f_empty` → all **5** rows return to ERR 2 | **exactly those 5** |
| K-LT2 | arm TYPEMM before evaluating → **only** the 2 `.pexp` rows move, 11 → 13 | **exactly those 2** |
| `penderr-acceptance` | the gate that caught both earlier wrong fixes | **61/61 agree** |

Both arms score against an **expected row set**, not against "did anything move".
