<!-- Copyright (c) 2026 Joost Yervante Damad — SPDX-License-Identifier: 0BSD -->

# D-STRPAREN — `(A$)` in every string context, and the rule a two-row filing claimed

Measured 2026-08-21, **three sides** (Philips VG-8020, National CF-3300, zerobas
`C-BIOS_MSX1_EU_REPACK_DISK`). ⚠️ **No disk anywhere**, so unlike the filename
battery this grew out of, every row here has **two references** — and they agree
on all fourteen.

Apparatus: `probes/basic/basic_probe_strparen.py`, `make strparen-acceptance`.
**No ROM byte.**

---

## 1. Why

[`spec-basic-fnexpr.md`](spec-basic-fnexpr.md) §4 found `f.paren`
(`OPEN(A$)AS #1`) was the one row of fourteen its filename fix did not close,
correctly refused to charge it to the filename gate, and filed it as:

> 🎯 **Parentheses work for numbers; it is the STRING evaluator that has no `(`
> case.** `(A$)` is refused in *every* string context.

on the strength of **two** ad-hoc readings — `B$=(A$)` and `PRINT (A$)` — that
were never committed as rows. A rule claiming more than its evidence
[[a-rule-can-claim-more-than-its-evidence]]. This is the evidence.

---

## 2. The rows

Every case runs on `10 A$="Q"` / `20 A=5`, so the only variable between a row and
its control is the parenthesis.

| row | statement | vg8020 | cf3300 | zerobas |
|---|---|---|---|---|
| `p.let` | `B$=(A$)` | `Q` | `Q` | **`Type mismatch`** |
| `p.cat1` | `B$=(A$)+"Z"` | `QZ` | `QZ` | **`Type mismatch`** |
| `p.cat2` | `B$="Z"+(A$)` | `ZQ` | `ZQ` | **`Type mismatch`** |
| `p.nest` | `B$=((A$))` | `Q` | `Q` | **`Type mismatch`** |
| `p.inner` | `B$=(A$+"Z")` | `QZ` | `QZ` | **`Type mismatch`** |
| `p.lit` | `B$=("Z")` | `Z` | `Z` | **`Type mismatch`** |
| `p.print` | `PRINT"[";(A$);"]"` | `Q` | `Q` | **`Type mismatch`** |
| `p.if` | `IF (A$)="Q" THEN…` | `Y` | `Y` | **`Type mismatch`** |
| `p.len` | `LEN((A$))` | ` 1 ` | ` 1 ` | **`Type mismatch`** |
| `p.mid` | `MID$((A$),1,1)` | `Q` | `Q` | **`Type mismatch`** |
| `p.left` 🔴 | `LEFT$((A$),1)` | `Q` | `Q` | **`Syntax error`** |
| `p.ctl` 🟢 | `B$=A$` | `Q` | `Q` | `Q` |
| `p.numctl` 🟢 | `B=(A)` | ` 5 ` | ` 5 ` | ` 5 ` |
| `p.numprint` 🟢 | `PRINT"[";(A+1);"]"` | ` 6 ` | ` 6 ` | ` 6 ` |

**Eleven of eleven diverge. All three controls are green on all three sides.**

---

## 3. What the rows establish that the filing did not

### 3.1 ✅ The rule holds, and now it has a denominator

Eleven contexts, not two, and on two references rather than one. The filed
sentence survives contact with the evidence — which is worth recording as
plainly as a refutation would be.

### 3.2 🟢 The three controls are the finding's spine

Without `p.ctl`, *"strings are broken"* reads the eleven rows just as well.
Without `p.numctl` / `p.numprint`, so does *"parentheses are unsupported"*. The
controls are placed one per **dispatcher** — `p.numctl` for the LET/`str_eval`
side, `p.numprint` for `basic/print.asm`'s item loop — because a control that
does not run through the same dispatcher as its row is a control about something
else [[controls-for-the-verb-not-the-cell]].

### 3.3 🔴 `p.lit` says this is not about VARIABLES

`B$=("Z")` — a parenthesised **literal**, no variable anywhere — is refused too.
So the subject is the `(`, and any fix framed around string *variables* would
close ten rows and leave this one.

### 3.4 🔴 `p.left` has a different FACE — and I read that as a different SITE, wrongly

Ten rows answer `Type mismatch`; `LEFT$((A$),1)` answers **`Syntax error`**.

**What this section said when it was written, and it was wrong:** *"That is not a
wording detail, it is a different refusal site: `LEFT$`'s own argument parse
rejects the `(` before anything type-checks… one rule at at least TWO
mechanisms, the same shape D-FNARG2 found."*

🔴 **REFUTED BY THE FIX, ONE COMMIT LATER.** A single `(` arm in `str_eval_one`
closed `p.left` in the same run as the other nine. `LEFT$`'s parse consumes its
own `(`, checks for an empty argument, and then calls **`str_eval`** like
everyone else ([`basic/str-engine.asm`](../basic/str-engine.asm)); the different
face comes from what its caller does with a `CF clear` return, not from where
the refusal happens. **One site, two faces** — the opposite of the reading.

🎯 **The inference that produced the error is worth more than the error.** A
different face was taken as evidence of a different mechanism, and it is not
evidence of that at all: the same refusal reached through two different callers
prints two different things. D-FNARG2's *"one rule, THREE mechanisms"* was
established by tracing each path, not by reading the faces — and this section
read the faces. **A face is a claim about the LAST routine to run, not about the
first one to refuse.**

⚠️ Keeping `p.mid` beside `p.left` was still right, for a reason the wrong
analysis got backwards: they are the same kind of call, and the rows now confirm
they behave the same way. That is what made the refutation visible in one run.

### 3.5 🎯 It is a SPLIT-EVALUATOR question, not a missing `case` label

The residual says *"`str_eval_one` has no parenthesised-subexpression case"*.
True, and not sufficient. `p.let` / `p.cat1` / `p.nest` / `p.inner` / `p.lit`
reach `str_eval` and would close with a `(` case there. `p.print` never reaches
it: [`basic/print.asm`](../basic/print.asm)'s `exp_loop` dispatches on `"`, on
the string-function tokens and on a `$`-suffixed letter, and a leading `(` falls
through to `exp_num` — the **numeric** evaluator. `p.if` is the same story
through `ev_rel`.

zerobas has a numeric `eval` and a string `str_eval` and decides between them by
**peeking at the first byte**; the reference has one type-polymorphic evaluator
that returns whatever it found. **A leading `(` is the one operand shape a peek
cannot classify** — which is why this hole exists at all, and why the fix has to
be "try the string path and fall back" rather than "add a label".

---

## 4. Status

All eleven divergent rows are **DEFERRED** — measured, printed, never scored.
The three controls are **gated**. A known divergence that gates turns a battery
red forever instead of measuring anything; the controls are what make the eleven
a reading rather than an anecdote — D-FILESIDE's argument for its own row.

Not priced here. What the rows change is the SHAPE of the fix: not one label in
`str_eval_one`, but a string-first attempt with a numeric fallback at each
dispatcher that peeks, plus `LEFT$`'s own argument parse as a separate site.
