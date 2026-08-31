# D-CATTM — the filed concatenation pair is one row, not two, and the stated hazard is not the obstacle

*2026-08-31. No ROM change. Probe `scratchpad/catterm_probe.py`, 9 rows, three
machines.*

## 1. Running the claim before building on it

`TODO.md` carried this since 2026-08-29 (D-STRTM §4):

> **`5+"AB"` READS ERR 24 AND `"AB"+(0*(1/0)+1)` READS ERR 13, WHERE BOTH
> REFERENCES SAY 13 AND 11.**

Re-measured:

| row | | vg8020 | cf3300 | zerobas |
|---|---|---|---|---|
| `c.numstr` | `5+"AB"` | 13 | 13 | **13** ✅ |
| `c.strfault` | `"AB"+(0*(1/0)+1)` | 11 | 11 | **13** 🔴 |

🔴 **Half the filed claim is stale.** `5+"AB"` agrees on all three machines. The
likely closer is D-TMFP, whose own headline is *"the rule was not a rank between
two flags but which fault happened first"* — the same question, settled for that
row and never struck from the filing.

## 2. And the mirrors narrow what is left

The filing covers one operand order. The other three forms were never measured:

| row | | all three machines |
|---|---|---|
| `c.strnum` | `"AB"+5` | 13 ✅ |
| `c.faultstr` | `(0*(1/0)+1)+"AB"` | 11 ✅ |
| `c.varnum` / `c.numvar` | `A$+5` / `5+A$` | 13 ✅ |

🎯 **`c.faultstr` is the one that matters.** With the faulting operand on the
**left** it is evaluated first, raises Division by zero, and zerobas agrees. Only
`<string> + <numeric expression carrying its own fault>` diverges.

**One row, one order** — not a broken class.

## 3. 🔴 The stated hazard is not the obstacle

The filing says a D-STRTM-style fix (evaluate the operand, then defer) is barred
because `sct_err2` returns NC and the caller re-drives, so evaluating there would
evaluate **twice** — and a string operand can contain `USR` or a `DEF FN` call
with side effects.

That reasoning is about a fix nobody needs to make. `sct_err2` does **not**
evaluate the operand today; the numeric re-drive does. The operand's Division by
zero is therefore reachable — it is simply **outranked**, because
`type_mismatch_set` armed FPERR *before* the re-drive ran and `ev_f_defer` is
first-error-wins.

➡️ **So the fix is about WHEN the type mismatch is armed, not about where the
operand is evaluated.** It needs the type mismatch to arm at a *lower priority*
than anything the re-drive raises — armed last rather than first — which is a
change in `check_expr_errors`' precedence, not in `sct_err2`'s evaluation.

⚠️ **Removing the arm stays closed** for the reason already recorded: without it
`PRINT A$+5` printed `" 0"`, a silent wrong answer.

## 4. What is NOT established

I did **not** measure that the re-drive evaluates the operand exactly once. The
error code cannot show it: armed-and-outranked and never-evaluated both produce
`13`. Distinguishing them needs an operand with an observable **side effect**
(`USR` writing through `POKE`), which this probe does not build.

That matters for the fix: if the re-drive does *not* reach the operand, the
lower-priority-arm route produces `13` as well and the fix has to go somewhere
else entirely. **Stated as unmeasured rather than assumed** — the mechanism above
is read off the code and its comments, and the one row that would separate the
two readings is named here for whoever takes it.
