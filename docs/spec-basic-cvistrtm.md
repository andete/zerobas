# D-CVISTRTM — the fix I shipped an hour earlier had a hole, documented in the file I was editing

*2026-08-31. `basic/expr.asm` (`ev_ff_cvi`). Probe `scratchpad/cvitm_probe.py`
(16 rows), arms `scratchpad/cvitm_knives.py`.*

**Cost: +1 B** — page 1 356 → 355 B free. **Rows: DIFF 1 → 0.**

## 1. Found by reading the neighbours, not by a new idea

D-CVITM pointed CVI's non-string decline at `ev_f_tmm` and shipped. Sweeping the
same class afterwards — *which other verbs route a string decline to which
helper* — landed on `basic/str-engine.asm`, where D-STRTM's own comment says:

> This was a bare `jp nc,ev_f_tmm` — armed **WITHOUT LOOKING AT THE OPERAND** —
> and the comment above reasoned that first-error-wins would split `LEN(5)` from
> `LEN(LEFT$("AB"))`. It does, but **ONLY when the inner thing already set
> FPERR**. `LEN(0*(1/0)+1)` sets nothing: `str_eval` declines without evaluating,
> the mismatch arms first, and the division by zero is never raised. Both
> references answer Division by zero.

That is a description of the code I had just written. Measured:

| row | CF-3300 | zerobas |
|---|---|---|
| `LEN(0*(1/0)+1)` | `Division by zero` | `Division by zero` ✅ (D-STRTM) |
| `CVI(0*(1/0)+1)` | `Division by zero` | **`Type mismatch`** |

⚠️ **Not a regression, and the parent commit was checked rather than assumed.**
At `fef3d69~1` that row read `Syntax error` — also wrong. D-CVITM closed 3 of 4
and left the 4th wrong in a *new* way.

## 2. The fix is the ORDER, for the fourth time in this class

D-LEFTTM, D-INSTRTM, D-STRTM, and now here: **evaluate the operand, then defer.**
`ev_f_defer` is first-error-wins, so a fault the operand raises keeps the answer.
`esa_tmm` (`call eval` / `jp ev_f_tmm`) already exists; CVI needed only to reach
it with `HL` on the operand:

```
cvi_tmm:        push    ix
                pop     hl                  ; the operand cursor, unadvanced
                jp      esa_tmm
```

🟢 **No double evaluation**, which is what makes it safe — nothing re-drives the
operand after this point. (D-STRTM records `sct_err2`'s mirror of the bug as
*not* having that property, which is why that one stays filed.)

## 3. 🎯 A knife that stopped moving, and was right to

D-CVITM had also added an explicit `cp ')'` test so `CVI()` would stay a Syntax
error, with K-CV3 to witness it. After the order fix, **K-CV3 moved zero rows** —
because `eval` now meets the `)` and raises that syntax error itself, and
first-error-wins keeps it.

The test had become dead weight. It and its knife are both gone and **5 B came
back**, which is why the net for this slice is +1 B rather than +6.

**An arm that stops moving can mean the code it guards has become redundant, not
that the arm went blind.** The row set is what separates those: still 0 DIFF
with the test removed.

## 4. Three arms, and K-CV4 got stronger

| knife | cut | moved |
|---|---|---|
| K-CV1 | decline back to `ev_f_empty` | `a.num`, `a.numvar`, `a.fault` |
| K-CV4 | defer **without** evaluating first | `a.fault`, `c.empty` |
| K-CV2 | drop the 2-byte length guard | `g.short` |

🎯 **K-CV4 moves two rows, and the second is the point.** With the redundant test
gone, `CVI()` rides on the same single correction as the operand-fault case — one
change now covers what took two.

🎯 **And `b.nested` holds under every one of them**, which is what says
first-error-wins is doing the separating rather than any branch.

## 5. What this says about the method

D-EXPNEG was reverted for changing a behaviour without reading whether it was
already decided. This is the same lesson from the other side: **the answer was in
the neighbouring routine's own comment, in the file being edited.** The sweep
that found it took four minutes and asked one question — *where does each string
decline go?* — which is a question worth asking whenever a shared exit is
repointed.
