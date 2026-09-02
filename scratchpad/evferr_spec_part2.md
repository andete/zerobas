
## 7. The last DIFF was an ORDERING one — and the rule is NARROWER than it looks

After the five retargets: **26 scored, 1 DIFF.** `A=VARPTR(B` with `B` unset was
ERR **5** where both references say **2**, while `B=1:A=VARPTR(B` — the same
missing `)` with the lookup satisfied — was already 2 on all three. So zerobas
answers the operand's DOMAIN error and the references answer the form's SYNTAX
error, and nothing else separates them.

🔴 **BEFORE PRICING A FIX AT `vptr_unset`, THE RULE IT IMPLIES NEEDED ITS OWN
DENOMINATOR** — *out of scope for the FIX is not out of scope for the
BOOKKEEPING* ([[a-row-written-off-as-out-of-scope-leaves-the-bookkeeping]]). Two
candidates: one TYPE over, and one ARM over.

| row | statement | refs | zb | |
|---|---|---|---|---|
| `d.strunset` | `A=VARPTR(B$` | 2 | **5** | 🔴 a SECOND member — same class, string scalar |
| `d.strunsetok` | `A=VARPTR(B$)` | 5 | 5 | ✅ control (D-VPTRDOM: an unset scalar is IFC) |
| `d.arybadsub` | `DIM Z(2):A=VARPTR(Z(9)` | **9** | **9** | ✅ **the rule does NOT extend here** |
| `d.arybadsubok` | `DIM Z(2):A=VARPTR(Z(9))` | 9 | 9 | ✅ control |

🎯 **`d.arybadsub` IS THE ROW THAT SEPARATED TWO RULES THAT COINCIDE ON EVERY
SCALAR CASE** ([[two-rules-that-coincide-on-every-row-you-have]]). I had the
general rule written down — *"syntax outranks domain"* — and it is **wrong**:
the array arm's out-of-range subscript beats the missing `)` on BOTH references,
because an array reference's subscripts are evaluated *while the form is being
parsed*, whereas a scalar is looked up only once the form is known to be well
formed. The narrow rule is the true one:

> **A SCALAR LOOKUP HAPPENS AFTER THE CLOSING `)`, NOT BEFORE IT.**

⚠️ **AND THAT VINDICATED AN UNTESTED JUSTIFICATION RATHER THAN FALSIFYING ONE.**
`vptr_none` declines the very check at issue, in prose, with a reason nobody had
run: *"no `')'` check (it could only raise a masking second error)"*. It is
**correct**, and `d.arybadsub` is the row that says so — the first time that
sentence has been evidence rather than an argument. This is the mirror of
[[a-justification-parenthesis-is-an-unrun-claim]]: running one can confirm it,
and the outcome is not knowable in advance, which is the entire reason to run it.

### 7.1 The fix, and why it is 8 B rather than 3

```
vptr_unset:     call    ev_sp
                cp      ')'
                jp      nz,ev_f_empty       ; malformed close -> Syntax error (2)
                ld      e,3                 ; (unchanged)
                jp      ev_f_defer          ; (unchanged)
```

**+8 B of main page 1: 107 → 99 B**, measured from clean, exactly as priced.

⚠️ **`call vptr_close` WOULD HAVE BEEN 5 B CHEAPER AND WAS DECLINED.** Every
factor error path ends in `ret` **to the factor's caller**, so a `call` here puts
one frame between `ev_f_err`'s `ret` and the address it means to land on. It
*does* unwind correctly — the extra frame is consumed by the first pass through
the tail and re-supplied by the second — and that is precisely the accident
[[abort-chain-returns-into-caller]] records **twice** as a measured failure
(`LOCATE` erroring twice; `WIDTH 300` continuing with the error code as data).
8 B is the price of not repeating it, and 99 B of page 1 can pay it.

**Final: 30 rows × 3 machines, references unanimous, 0 DIFF.**

---

## 8. 🔬 Knives

See `scratchpad/evferr_knives.py` / `evferr_knives.out`. Predictions pinned in
`evferr_predictions.md` before the runner ran.

---

## 9. Predictions scored

**Round 1 — 19 of 20 exact.** The one miss is `b.openeol` (`A=BASE(`): I
predicted `gfx_syntax`'s ERR 2 would beat the deferred missing-operand and
called it 2/2; it is **24 on all three machines**. An AGREEING row, mispredicted
— the deferred FPERR reaches the statement boundary and wins, and both
references agree that an empty `BASE(` slot is *Missing operand*. ⚠️ The
prediction doc's own **tally** said "8 DIFF" while its row table listed **nine**;
the rows were right and the arithmetic beneath them was not. A summary line is
not a prediction, and it is not covered by one either.

**Round 2 — 3 of 4 exact.** The miss is the important one: I predicted
`d.arybadsub` would read **2** on the references (the wide rule) and it reads
**9**. Had that row not been in the set, the fix would have shipped with a
justification stating a rule the tree measurably does not follow — the fix
itself would still have been correct, because it is sited where the narrow rule
lives.

🎯 **BOTH MISSES ARE THE SAME SHAPE: A CLAIM ABOUT WHICH LAYER ANSWERS FIRST,
MADE BY READING CODE.** That is the shape this whole slice is about, and I made
it twice more while writing the slice about it.

---

## 10. Gates

`make gates`, from clean.

---

## 11. What this does NOT establish

* The 26-row set is a **hand-listed sample around five named sites**, which is a
  scope claim and not a coverage one ([[a-hand-listed-denominator-is-a-scope-claim]]).
  Every `ev_f_err` jump instruction in the tree is covered; every *row* that can
  reach one is not.
* **`e.eofcrt`/`e.lofcrt` reach `:1135`/`:1157` through a `CRT:` channel only.**
  The cassette arm of `fch_mode_class`'s NC branch is untested here — it needs a
  tape image and it is the same instruction.
* The two `IF !G8_RESIDENT` sites were retargeted with the rest and **have never
  been assembled**. `make switch-build-check` proves the arm builds; nothing runs
  it.
* `A=VARPTR(B` was fixed at `vptr_unset`. Whether other *factors* look up a name
  before validating their form is not measured — VARPTR is the only one whose
  grammar has a `)` after a bare name.
