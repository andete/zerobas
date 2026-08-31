# D-CVITM — `CVI`'s three error dispositions, and the helper already written for one of them

*2026-08-31. `basic/expr.asm` (`ev_ff_cvi`). Probe `scratchpad/cvitm_probe.py`,
arms `scratchpad/cvitm_knives.py`.*

**Cost: +11 B** — main page 1 367 → 356 B free. **Rows: 14, DIFF 3 → 0.**

## 1. Opened by a carve, not by a search

D-NGRAM15 gave every one of its seven sites a row, and `CVI(5)` came back
`Syntax error` here against `Type mismatch` on the CF-3300. Mapping the domain
then found a **second** divergence nobody was looking for.

⚠️ **One oracle only.** `CVI`/`MKI$` are Disk BASIC verbs: the cassette-only
VG-8020 answers `Illegal function call` to every form, well-formed or not, so it
cannot arbitrate and is not a side in this probe. Stated rather than silently
dropped.

## 2. What was measured, before anything was changed

| row | | CF-3300 | zerobas |
|---|---|---|---|
| `a.num` | `CVI(5)` | `Type mismatch` | **`Syntax error`** |
| `a.numvar` | `CVI(A)`, A numeric | `Type mismatch` | **`Syntax error`** |
| `b.nested` | `CVI(LEFT$("AB"))` | `Syntax error` | `Syntax error` ✅ |
| `c.empty` | `CVI()` | `Syntax error` | `Syntax error` ✅ |
| `g.short` | `CVI("A")` | `Illegal function call` | **`8769`** |
| `m.str` | `MKI$("A")` | `Type mismatch` | `Type mismatch` ✅ |

🔴 **`g.short` is the one nobody filed.** `CVI` needs two bytes; given a
one-byte string it read one byte of the string and one byte of *whatever
followed it*, and answered a plausible number. A wrong answer that looks like an
answer.

🎯 **And `b.nested` is what makes the fix possible.** Two different causes shared
one exit (`jp nc,ev_f_empty`), and the reference **separates** them — so they
could not both stay on one branch.

## 3. The first fix is zero bytes, because the helper was already there

`ev_f_tmm`'s own header, written long before this slice:

> deferred FPERR=10 "type mismatch" for a string function given a NON-string arg
> (LEN(5)/ASC(5)/VAL(5)): str_eval returned NC with FPERR clean. **First-error-wins
> keeps an inner error** (a nested malformed string fn like `LEN(LEFT$("AB"))`
> already set FPERR=4 → stays syntax error).

That is exactly this situation, and `CVI` simply was not wired to it. Changing
one operand — `ev_f_empty` → `ev_f_tmm` — costs **nothing**, and the existing
first-error-wins machinery does the separating for free: the nested case has
already set FPERR=4 *inside*, so it keeps its syntax error.

`g.short` needed a real guard: the descriptor's length byte is sitting in `HL`
before `pu_deref_body` turns it into a body pointer (6 B).

## 4. 🔴 The first cut over-reached, and a row caught it

Routing *every* `str_eval` decline to `ev_f_tmm` also caught `CVI()`, turning the
reference's `Syntax error` into `Type mismatch`. **An empty argument is a grammar
fault and has to be settled before the type question is asked** — the same order
`str_arg_open` uses, and the same shape as D-LEFTTM's finding that *the fix is
the ORDER, not the code*. 5 B for a `cp ')'` ahead of the evaluation.

Without `c.empty` in the row set this would have shipped: it was a row that
**already agreed**, kept because the domain was mapped rather than sampled.
[[a-row-written-off-as-out-of-scope-leaves-the-bookkeeping]]

## 5. Three changes, three arms, each isolating its own rows

| knife | cut | predicted | moved |
|---|---|---|---|
| K-CV1 | non-string decline back to `ev_f_empty` | `a.num`, `a.numvar` | the same 2 |
| K-CV2 | drop the 2-byte length guard | `g.short` | the same 1 |
| K-CV3 | drop the empty-argument test | `c.empty` | the same 1 |

All three exact on the first prediction.

🎯 **`b.nested` holds under K-CV1, and that is the arm's real content**: it says
first-error-wins is what separates the two causes, not the branch. If the
separation were being done by the branch, reverting the branch would have moved
`b.nested` too.

## 6. Falsification

| claim | what would refute it | result |
|---|---|---|
| `CVI(5)` should be Type mismatch | the disk reference | it says so; the VG-8020 cannot arbitrate and is excluded |
| the two decline causes are separable | `b.nested` moving under K-CV1 | it holds — first-error-wins does it |
| `CVI("A")` was wrong | the reference | `Illegal function call` vs a plausible `8769` |
| nothing else moved | the full battery | 48/48 |
