<!-- Copyright (c) 2026 Joost Yervante Damad — SPDX-License-Identifier: 0BSD -->

# A parenthesised string is a string, and a peek is what could not tell

**D-STRPAREN (fix), 2026-08-21**, on `main`, based on `6e58f0a` (the
denominator). `(A$)` works in every string context measured. `make
strparen-acceptance` **3/3 scored + 11 deferred → 16/16 scored, DEFERRED
EMPTY**; `make namspc-acceptance` 98/98 → **99/99** as `f.paren` graduates with
them.

Measurement: [`strparen-msx1-characterization.md`](strparen-msx1-characterization.md)
(eleven contexts, three controls, **two references** — no disk anywhere).

---

## 1. What the hole actually was

zerobas has a **numeric** evaluator (`eval`) and a **string** evaluator
(`str_eval`) and picks between them by **peeking at the first byte** of an
operand. The reference has one type-polymorphic evaluator that returns whatever
it found.

🎯 **A leading `(` is the one operand shape a peek cannot classify.** `(A$)` is a
string and `(A+1)` is not, and nothing short of evaluating the inside can say
which. Every string context inherited that: eleven of them, on both references,
answered `Type mismatch` (or, at `LEFT$`, `Syntax error`).

---

## 2. The change — 28 B, and the `ret nc` is the design

### 2.1 `str_eval_paren` ([`basic/strvar.asm`](../basic/strvar.asm)), 23 B

```
                cp      '('
                jr      z,str_eval_paren
...
str_eval_paren: push    hl                  ; the '(' -- restored if we decline
                inc     hl
                call    str_eval            ; full expression, `+` tail and all
                jr      nc,sep_decline
                call    skip_spaces
                cp      ')'
                jr      nz,sep_decline
                inc     hl
                pop     af                  ; discard the saved cursor (keep HL)
                scf
                ret
sep_decline:    pop     hl                  ; put the cursor back on the '('
                ; fall through into str_eval_no
```

🎯 **The decline is not an error path, it is the interface.** The routine is
written to be *tried*: on anything that is not a string it restores HL and
returns CF clear exactly as `str_eval_no` does, so a caller that guessed wrong
falls through to the numeric path with the cursor it would have had. That is
what lets a peeking dispatcher offer the string path **without committing to
it**. Falling *through* into `str_eval_no` rather than jumping to it is worth
2 B.

⚠️ **The recursion is `str_eval`, not `str_eval_one`** — the `+` tail belongs
*inside* the parentheses, so `(A$+"Z")` works and `((A$))` falls out for free.

⚠️ **A `(` here is never a subscript.** `A$(1)` reaches the variable arm via
`is_letter`, which consumes the name first; `str_eval_one` is only ever entered
at an operand boundary. Same disambiguation `ev_f_var`'s array check already
relies on.

### 2.2 The PRINT peek ([`basic/print.asm`](../basic/print.asm)), 5 B

```
                cp      '('
                jp      z,exp_strvar
```

`exp_strvar` already ended in `jr nc,exps_fallback`, whose own comment states the
contract this depends on — *"str_eval left HL unmoved on failure, so this
restores the same cursor `exp_num` would see un-gated"*. So `PRINT (A+1)` reaches
the numeric path untouched, and that is the **gated control `p.numprint`**, not
an assumption.

---

## 3. Ten rows closed on the first arm — two more than predicted

Predicted before the build: `p.let`, `p.cat1`, `p.cat2`, `p.nest`, `p.inner`,
`p.lit`, `p.len`, `p.mid` — **8**. Measured: those **plus `p.if` and `p.left`**.
Only `p.print` needed a second edit.

🔴 **AND `p.left` CLOSING REFUTED THIS SLICE'S OWN §3.4.** The characterization
had read `LEFT$((A$),1)`'s `Syntax error` — against ten `Type mismatch` — as
evidence of *"a different refusal site… one rule at at least TWO mechanisms"*.
One `(` arm closed it in the same run as the other nine: `LEFT$` consumes its own
`(`, checks for an empty argument, then calls **`str_eval`** like everyone else.
The different face came from what its caller does with a `CF clear` return.

🎯 **A face is a claim about the LAST routine to run, not the first one to
refuse.** D-FNARG2's *"one rule, THREE mechanisms"* was established by tracing
each path; §3.4 read the faces instead, and the analysis is inverted in place
rather than deleted.

---

## 4. 🔴 A patch that never landed, and the ROM hash is what caught it

The PRINT peek was applied, built and measured — and `p.print` stayed red. So did
the **wall**: 16 B before and 16 B after. A 5 B edit that costs 0 B has not
happened.

The `assert s.count(old) == 1` in the patch script had failed (the anchor was
copied from `strvar.asm`'s `INKEY_TOKEN` comment, not `print.asm`'s), and the
whole command had been handed to the background, so the traceback went to a task
log nobody read while the *probe* log looked like an honest measurement. **The
build then ran on unmodified source and `p.print` was red for the true reason:
nothing had changed.**

⚠️ Two rules, both already in this project's operating rules, and both bypassed
by running a patch and a build in one backgrounded command:

* **`ls` the log — and read the EXIT PATH — before believing a result.** The
  `DONE` sentinel printed regardless; the traceback was three lines above it.
* **Assert the ROM MOVED.** D-FNEXPR2 added exactly this guard to a knife runner
  after a knife scored on a stale machine. The same guard belongs on any edit
  that claims a byte cost. The rebuild script carries it now:

```
if diff -q "$S/b1-hash.txt" "$S/b3-hash.txt" >/dev/null; then
  echo "*** ROM IDENTICAL TO THE PRE-EDIT BUILD -- the edit did not land"; exit 3
fi
```

---

## 5. Cost

| wall | at `6e58f0a` | after | delta |
|---|---|---|---|
| main page 1 | 39 B | **11 B** | **−28 B** |
| page-0 low | 22 B | 22 B | 0 |
| sub page 0 | 3299 B | 3299 B | 0 |
| sub page 1 | 1624 B | 1624 B | 0 |

23 B for `str_eval_paren`, 5 B for the PRINT peek. Hand-counted at ~25 B for the
first arm; measured 23.

⚠️ **Main page 1 is thin at 11 B** and the next slice will need a carve.
`tools/clone_scout.py --min 6 --members 2` (2026-08-21) offers 12 B
(`sav_ascii_flag`/`sav_cas_flag`), 10 B in `basic/list.asm` and 9 B
(`ev_t_div`/`ev_t_mul`), all page 1.

---

## 6. The knives

| knife | cut | predicted |
|---|---|---|
| **K-SP1** | `str_eval_one`'s `cp '('` → `cp ')'` | all eleven string-side rows red; `p.numlet` + the 3 controls stay green |
| **K-SP2** | `sep_decline`'s `pop hl` → `pop de` | exactly `p.numlet` — and NOT `p.numprint`, which guards its own cursor |
| **K-SP3** | the PRINT peek's `cp '('` → `cp ')'` | exactly `p.print` |

**Measured. Two exact — and one that reddens nothing, twice.**

| knife | measured |
|---|---|
| **K-SP1** | **11 rows** — every str_eval-side row *and* `p.print`; `p.numlet`, `p.numif` and all three controls stayed green ✅ EXACT |
| **K-SP2** | **nothing**, in two rounds — §6.1 |
| **K-SP3** | exactly **`p.print`** ✅ EXACT |

### 6.1 🔴 K-SP2 reddens nothing, and the guard ships UNPINNED

`p.numlet` (`B$=(A+1)`) was added *specifically* to pin the decline path's
`pop hl`, on the reasoning that `ex_let_str` → `els_tc_common` re-evaluates from
HL where `p.numprint` guards its own cursor. **It does not pin it.** It agrees
for the wrong reason: `els_tc_common` raises `type_mismatch_error` once `eval`
returns, **from any cursor**, so a row scoring the FACE cannot see a cursor at
all.

`p.numif` (`IF (A+1)=6 THEN…`) was then added to score a **value** rather than a
face — get the cursor wrong and the comparison changes, and the `[Y]`/`[N]` arms
show it directly. **It does not pin it either.** That caller guards its own
operand start as well.

So every caller of `str_eval` that falls back either saves and restores its own
cursor (`exp_strvar` explicitly — `exps_fallback`'s comment says so) or raises
regardless. **The restore is correct, costs zero bytes (`pop hl` and `pop af` are
both one), makes the stated contract true — and no row can see it.**

🎯 **It is kept and it is declared.** A guard with no row is exactly what
D-FNEXPR2 shipped at `do_files` and filed against itself one commit earlier; the
difference here is that two rows were *built and measured* trying to make it
live, and both failed for reasons that are now written beside the code. **"I
could not find a row" is a stronger statement than "no row was needed", and only
one of them is honest here.**

⚠️ Both rows are KEPT. They are green, they widen the denominator (numeric-in-
parens through two more dispatchers), and they record what was tried.
