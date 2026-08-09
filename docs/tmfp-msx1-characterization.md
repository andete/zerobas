# D-TMFP — what MSX-BASIC reports when two faults are pending at once

Dated finding, 2026-08-09, measured on a **Philips VG-8020** and a **National
CF-3300** with `probes/basic/basic_probe_tmfp.py` (50 rows, 3 sides, both
references available because no row touches a file). Clean-room: observed screen
output only; both reference ROMs are black boxes.

The settled contract lives in [`spec-basic-tmfp.md`](spec-basic-tmfp.md); this
is the notebook.

---

## 1. The question, and why the filed answer could not be right

D-LOCARG (`887e78a`) filed one deferred row:

> `LOCATE STR$(1/0),3` → ERR 11 on both references, ERR 13 here.
> **a pending numeric fault outranks TMISMATCH too.**

That is a rank claim, and a rank claim is refutable by one row that ranks the
other way. D-EVALCHK §5.1 already had it: `WIDTH (A$<5)+0*(1/0)`, both flags
pending, ` 13 ` on both references — and green in the shipped
`width-acceptance` gate. **Both rows have both faults pending; they report
opposite faults.**

⚠️ The filed item asserted §5.1 was frozen on `PRINT #A$,"X"`, "a row that
cannot discriminate". It was not. That row belongs to D-BADFNUM §6 and is about
`eval_chan`. §5.1's row discriminates perfectly. Two correct measurements were
filed as one wrong rule because the second was read from memory of the wrong
document.

## 2. 🎯 The discriminator: the same two faults, swapped

If neither flag outranks the other, the only remaining variable is **which fault
happened first**. That is directly testable — concatenate the two fault seeds in
both orders:

| program | fault order | vg8020 | cf3300 | zb @ `887e78a` |
|---|---|---|---|---|
| `WIDTH (A$<5)+0*(1/0)` | type → numeric | ` 13 ` | ` 13 ` | ` 13 ` 🟢 |
| `WIDTH 0*(1/0)+(A$<5)` | numeric → type | ` 11 ` | ` 11 ` | ` 13 ` 🔴 |
| `WIDTH (A$<5)+0*SQR(-1)` | type → numeric | ` 13 ` | ` 13 ` | ` 13 ` 🟢 |
| `WIDTH 0*SQR(-1)+(A$<5)` | numeric → type | ` 5 ` | ` 5 ` | ` 13 ` 🔴 |

**The references swap their answer when the operands swap.** And the third row
of the four is what makes this a rule rather than an anecdote: the winning code
changes with the **operand** — 11 from `1/0`, 5 from `SQR(-1)` — not with the
operator. Any "division by zero is special" reading predicts 11 in both.

## 3. The rule, as measured

> **Of a pending type fault and a pending numeric fault, the one that occurred
> FIRST during evaluation is the one reported.**

And the reason is that there is **no rule on the reference at all**: it raises
**eagerly**. The first fault aborts the statement where it happens, so the
second fault never occurs. Every row above follows from that one fact, and so
does the fact that the references never disagreed with each other on any of the
50 rows.

zerobas cannot raise eagerly — `ev_rel` has no mid-expression unwind, which is
why `type_mismatch_set` exists at all — so it emulates with two sticky flags and
a static test order in the readers. **A static order is a rank, and the thing
being modelled is not a rank.** That is the whole divergence.

## 4. Where zerobas stood, and what moved

50 rows, 3 sides. **Before: 29 agree / 21 diverge. After: 49 agree / 1 deferred.**

All 21 divergences were the same shape — a numeric fault that occurred first,
reported as ` 13 ` — and they were spread across **nine different callers**,
which is what shows the defect was in the shared model and not in any verb:

| caller | row | refs | zb before | zb after |
|---|---|---|---|---|
| `eval_int16_checked` (WIDTH) | `o.w.fp` | ` 11 ` | ` 13 ` | ` 11 ` ✅ |
| `eval_int16_checked` (CLEAR) | `o.cl.fp` | ` 11 ` | ` 13 ` | ` 11 ` ✅ |
| LOCATE — **the filed row** | `o.loc.str` | ` 11 ` | ` 13 ` | ` 11 ` ✅ |
| `ex_if` | `o.if.fp` | ` 11 ` | ` 13 ` | ` 11 ` ✅ |
| `exp_num` (PRINT) | `o.pr.fp` | ` 11 ` | ` 13 ` | ` 11 ` ✅ |
| `check_expr_errors_popbc` (`ex_let`) | `o.let.fp` | ` 11 ` | ` 13 ` | ` 11 ` ✅ |
| `ex_let_arr` (arrays) | `o.ary.fp` | ` 11 ` | ` 13 ` | ` 11 ` ✅ |
| `els_tc_common` (`A$=<num>`) | `o.els.fp` | ` 11 ` | ` 13 ` | ` 11 ` ✅ |
| `eval_chan` (`PRINT #`) | `o.chan.fp` | ` 11 ` | ` 13 ` | ` 11 ` ✅ |
| `ev_ff_ckpdl` (PDL) | `r.pdl` | ` 11 ` | ` 13 ` | ` 11 ` ✅ |
| `ev_mc_arg_checked` (RND) | `r.rnd` | ` 11 ` | ` 13 ` | ` 11 ` ✅ |
| `fch_check` (LOF) | `r.lof` | ` 11 ` | ` 13 ` | ` 11 ` ✅ |
| `sfr_argok` (HEX$) | `r.hex` | ` 11 ` | ` 13 ` | ` 2 ` 🔴 §5 |

Plus six untrapped rows, which moved from `Type mismatch in 10` to
`Division by zero in 10` / `Illegal function call in 10` — the **message text**,
not just the code, and each printed exactly once with no run-on.

### 4.1 The part that was already right — and says so
`o.imp.fp` (`PRINT STR$(1/0) IMP 1`) read ` 11 ` on all three sides **before**
the fix. `exps_notrel` is the one site where the type fault is marked on the
spot rather than deferred out of the expression, and it was already reaching the
numeric fault first. It is in the row set precisely because a row that already
agrees is the one that catches an over-reaching fix — and it still agrees.

Likewise all seven negative controls (`n.tm.*`, a type fault with **no** numeric
fault pending, at every reader including the four that never test `FPERR`) are
unmoved at ` 13 `.

## 5. 🔴 The row that did not close, and the two defects it uncovered

`r.hex` — `Q2$=HEX$(0*(1/0)+(Q$<5))` — reads ` 11 ` on both references, read
` 13 ` before and reads ` 2 ` after. **It went from wrong to differently wrong.**

Localized on zb with a scratch probe:

| program | zb after |
|---|---|
| `PRINT HEX$(0*(1/0)+(Q$<5))` | ` 2 ` |
| `Q2$=HEX$(0*(1/0)+(Q$<5))` | ` 2 ` |
| `Q2$=STR$(0*(1/0)+(Q$<5))` | ` 2 ` |
| `PRINT OCT$(0*(1/0)+(Q$<5))` | ` 2 ` |
| `PRINT HEX$((Q$<5))` — type alone | ` 13 ` 🟢 |
| `PRINT HEX$(0*(1/0))` — numeric alone | ` 11 ` 🟢 |
| `Q2$=HEX$((Q$<5)+0*(1/0))` — type FIRST | ` 13 ` 🟢 |

So it is not `HEX$`, not the assignment driver, and not either fault alone: it
needs **both** faults inside a string function's parentheses. Two pre-existing
defects, both previously masked:

1. after a string-compare mismatch the cursor does not land on the closing `)`,
   so `str_fn_radix`'s `cp ')'` fails into `str_arg_empty`;
2. `str_arg_empty` does `ld a,4` / `ld (FPERR),a`, **overwriting** the pending
   11 with the deferred syntax-error code — which prints as ERR 2.

🔴 **Defect 2 is a first-error-wins violation of exactly the kind this slice is
about**, in the same file, fifteen lines from `sfr_argok`'s comment stating the
rule it breaks. Both were invisible before, because `TMISMATCH` was armed and
the statement check reported 13 before the clobbered code could surface. **A
masked defect is not a fixed one.** Priced at +6 B for half of it — the low
region's entire remaining budget — and filed in `TODO.md` as its own slice.

## 6. 🔴 A control that was itself under test

The first draft of the control set named `u.w.fp5` (`WIDTH 0*SQR(-1)+(A$<5)`) as
a positive control. That is a **both-flags row** — one of the rows under test.
It read `Type mismatch in 10` on zb, i.e. exactly the divergence being measured,
and the probe correctly exited 2 ("the instrument broke") on a run where the
instrument was fine. Caught on the first smoke run and replaced with `u.fp.w`
(`WIDTH 0*(1/0)+1`), a numeric fault with no type fault pending.

**A control must be a row that already agrees for a reason independent of the
claim.** A subject row cannot license reading the subject.

## 7. The denominator

The filed item named four callers. The tree has eighteen relevant sites:
twelve `check_expr_errors` call sites, two further hand-rolled copies of the
same ordering (`check_expr_errors_popbc`, `ex_let_arr`), and four readers of
`TMISMATCH` that never consult `FPERR` (`fch_check`, `ev_ff_ckpdl`,
`ev_mc_arg_checked`, `sfr_argok`). Of these, **nine can hold both flags** and
are measured here; **three provably cannot** (`INPUT#`, `LINE INPUT`, `READ`
each document that `TMISMATCH` is structurally 0 at their check).

The full axis list is printed by the gate itself (`DENOMINATOR:` line) and is
not duplicated here.

## 8. Why the untrapped battery exists

A trapped `[ERR]` reading is blind to the message **text**, to which line the
abort names, to whether the message printed **once**, and to whether the next
line ran anyway. The eight `u.*` rows read the clipped screen tail of `RUN` and
carry all four. They are what makes "reports 11" mean `Division by zero in 10`
and not merely a number that happens to be 11.
