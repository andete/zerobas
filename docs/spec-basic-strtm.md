# D-STRTM — sweeping the string-argument type-mismatch surface on purpose

*2026-08-29. `basic/str-engine.asm` (`ev_str_arg`'s decline). Probe
`scratchpad/strtm_probe.py`, arms `scratchpad/strtm_knives.py`.*

**Cost: +5 B of the low region** (124 → 119 B free; page 1 unchanged at 349).
**Rows: 22, DIFF 3 → 1** (plus 2 no-oracle). One filed, with its reason.

## 1. Why a sweep

Three slices found the *same* defect in three different places in one day — a
verb handed a number where it wants a string, answering `Syntax error` where
both references answer `Type mismatch`:

| slice | site | |
|---|---|---|
| D-NGRAM9 | `MID$` statement / `LINE INPUT` target | fixed |
| D-LEFTTM | `LEFT$` / `RIGHT$` / `MID$` function | fixed |
| D-INSTRTM | `INSTR`'s two string arguments | fixed |

Every one was found **incidentally**, by a carve that happened to touch the site.
Three instances is a class, not a coincidence — so this probe walks the whole
surface deliberately: every verb taking a string argument, handed a number, and
**each with an ordering twin**, because D-LEFTTM and D-INSTRTM both showed a verb
can answer 13 correctly and still get the *pending-fault* case wrong.

## 2. What the sweep found — three more

| row | references | before |
|---|---|---|
| `LEN(0*(1/0)+1)` | ERR 11 | ERR 13 |
| `5+"AB"` | ERR 13 | ERR 24 |
| `"AB"+(0*(1/0)+1)` | ERR 11 | ERR 13 |

🎯 **And note which half each is.** `"AB"+5` is **correct** at 13 while
`"AB"+(0*(1/0)+1)` is **wrong** — the same operator, opposite halves. A row set
containing only clean-expression rows would have declared concatenation fine.
That is the third time in one day that only the ordering row separates a working
fix from a broken one. [[two-rules-that-coincide-on-every-row-you-have]]

## 3. Fixed here: `LEN` / `ASC` / `VAL`

`ev_str_arg` — shared by all three — ended its decline with a bare
`jp nc,ev_f_tmm`: a deferred type mismatch **armed without looking at the
operand**. The comment beside it reasoned that first-error-wins would separate
`LEN(5)` from `LEN(LEFT$("AB"))`, and it does — but **only when the inner thing
already set FPERR**. `LEN(0*(1/0)+1)` sets nothing: `str_eval` declines without
evaluating, the mismatch arms first, and the division by zero is never raised.

The fix is the same as D-LEFTTM's and D-INSTRTM's, and for the third time **the
fix is the order**:

```
esa_tmm:
                call    eval                ; the operand, numerically
                jp      ev_f_tmm            ; -> ERR 13, unless the operand beat us
```

🟢 **And there is no double evaluation here, which is what makes it safe.**
`ev_str_arg` is already *on* the numeric evaluator's path, so nothing re-drives
the operand afterwards.

## 4. 🔴 Filed, not fixed: the concatenation pair — and the reason is a hazard

`5+"AB"` (ERR 24) and `"AB"+(0*(1/0)+1)` (ERR 13) live at `sct_err2`, which calls
`type_mismatch_set` and then **returns NC so the caller re-drives the whole
expression numerically**.

That difference is decisive. Evaluating the operand inside `sct_err2` would make
it evaluate **twice** — once here and once on the re-drive — and a string operand
can contain a `USR` call or a `DEF FN` invocation with side effects. So the route
that was safe for `ev_str_arg` is *not* safe here, and the honest fix probably
belongs in whatever the numeric re-drive meets, not in `sct_err2`.

⚠️ Removing the arm instead is closed by BUG C: without it, `PRINT A$+5` printed
`" 0"` — a silent wrong answer, which this project ranks worse than the refusal.

## 5. No oracle: `NAME` / `KILL` with a numeric argument

`NAME 5 AS "B"` and `KILL 5` read `Illegal function call` on the cassette-only
VG-8020 and `Type mismatch` on the disk-equipped CF-3300. zerobas targets the
disk machine and agrees with it. Scored separately and **named in the report**
rather than dropped. [[an-unnamed-outcome-reads-as-no-outcome]]

## 6. Falsification

| arm | requires | measured |
|---|---|---|
| K-ST1 | `ev_f_tmm` → `ev_f_empty` → the 3 clean rows return to ERR 2, `o.len` does **not** move | **exactly those 3** |
| K-ST2 | drop the `call eval` → **only** `o.len` moves, 11 → 13 | **exactly that 1** |
| `penderr-acceptance` | the standing first-error-wins gate | **61/61** |
| `tmfp-acceptance` | the type/numeric pair, 50 rows | **50/50** |

K-ST2 is the arm that matters and it is the third of its kind today: the clean
rows **cannot tell the two versions apart**, so a row set without `o.len` would
have scored the unfixed code green.
