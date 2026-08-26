<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-MISSOP3 — the filed row set was wrong in both directions

Status: **✅ SWEPT. Measurement only — no source file changed, no ROM byte
moved** (`fa720d6a` / `ae796ccb` / `cb06e156` throughout). 2026-08-26, on
`82f4de9`. `scratchpad/missop3_probe.py`, **29 rows × 3 machines**
(`missop3_base.out`, `missop3_sep.out`). Predictions pinned in
`missop3_predictions.md` before either round ran.

`TODO.md`:762 carried the `Missing operand` residual as *"3 rows still
diverge"* plus a denominator it named as *"unmeasured, not green"*. This is
that measurement, and **the filed set was wrong in both directions at once**:
two of its three rows are no longer defects, and the sweep found **eight more**.

---

## 1. The filed justification, run first — and FALSE

> *"Predicted not to move under the evaluator fix, and they did not — they reach
> an abort by another route."*

| row | statement | refs | filed | **measured today** |
|---|---|---|---|---|
| `r.lets` | `A$=` | 24 | zb 2 | **24 ✅ GREEN** |
| `r.letsp` | `A$=+` | 24 | zb 2 | **24 ✅ GREEN** |
| `r.midd` | `MID$(A$,2)=` | 24 | zb 2 | 2 🔴 still live |
| `r.key` | `KEY1,` | 24 | zb 2 | 2 🔴 **but misdiagnosed — see §3** |

**Two of the three closed themselves and nothing re-read the item.** Same shape
as [[a-justification-parenthesis-is-an-unrun-claim]], one level up: not a
parenthesis this time but the item's own *result column*, carried forward across
three days and two slices that touched the evaluator.

---

## 2. 🔴 THE ONE-RULE PREDICTION WAS REFUTED, THEN HALF-RESTORED BY ITS OWN SEPARATOR

D-MISSOP's rule is *"a required slot that ends where a value was needed is
`Missing operand`"*. I predicted it for all ten unmeasured verbs **as one rule**,
which makes it falsifiable in one shot — and two rows falsified it on **both**
references: `SWAP A,` is **2**, `DRAW` is **5**.

Then the separators split those two apart:

| separator | statement | refs | zb | what it settled |
|---|---|---|---|---|
| `d.swapblank` | `SWAP ,B` | **2** | 2 ✅ | SWAP's slot is a **NAME**, and a missing name really is `Syntax error` on both references |
| `d.drawscr2` | `SCREEN2:DRAW` | **24** | **13** 🔴 | DRAW's slot is a **VALUE** after all — the rule holds, and zerobas is wrong here |

🔴 **`d.draw` WAS A CASE THAT AGREED FOR THE WRONG REASON, AND IT AGREED ON ALL
THREE MACHINES.** `DRAW` with no operand in **SCREEN 0** is `Illegal function
call` (5) everywhere — the statement never reaches its operand at all, because
the mode check fires first. The row looked like evidence that DRAW breaks the
rule. In a graphics mode both references say **24** and zerobas says **13**
(*Type mismatch*), which is a divergence the baseline row was structurally
incapable of seeing ([[a-case-that-agrees-can-agree-for-the-wrong-reason]]).

🎯 **THE REFINED RULE, and the two axes are not the same axis:**

> **A required slot that ends where a VALUE was needed is `Missing operand`
> (24). Where a NAME was needed it is `Syntax error` (2). And a slot whose
> SEPARATOR is missing rather than its value is also `Syntax error`** —
> `PRINT USING"##"` is **2** on both references, not 24, because the format
> string is present and it is the `;` that is absent.

⚠️ **SCOPE: this is the partition over the verbs measured, and no wider.** The
name/value axis is settled by exactly two rows (`SWAP ,B`, `SCREEN2:DRAW`).

---

## 3. 🔴 A CONTROL FOUND THE BIGGEST DEFECT, AND THE FILED ROW BESIDE IT WAS A SYMPTOM

`r.keyok` (`KEY1,"X"`) was a throwaway well-formed row, expected green on all
three. It is **0 / 0 / 2** — a valid statement that both references complete and
zerobas refuses.

`basic/screen.asm:294` says so in its own comment: `jp stmt_error` for
*"KEY <n>,\"str\" / KEY LIST unsupported"*. `ex_key` implements `KEY ON`,
`KEY OFF` and the T3 `KEY(n)` arming form, and nothing else. `KEY LIST` is
**0 / 0 / 2** too.

🎯 **SO `r.key` (`KEY1,` → 2 vs 24) IS NOT A WRONG ERROR CODE.** It is the
statement form being absent. The filed item proposed to move it from 2 to 24;
that repair would have been **correct in the row and wrong in the tree**, and
only the control could tell the difference. Filed as its own `- [ ]` item.

⚠️ **IT WAS ALREADY WRITTEN DOWN AND STILL INVISIBLE**: `TODO.md`:6645, a
Phase-1 `- [x]` block ending *"all Phase-3 scope"*. The 2026-08-09 staleness
sweep enumerated `- [ ]` items, so it could not see it, and
`docs/kwsweep-msx1-coverage.md` explicitly scopes itself to **reserved words
only** — *"a word can be present and still wrong in its third argument"*. So
`make kwsweep` printing no `MISSING=` line is not evidence about this, and the
denominator that looks like it covers verbs does not cover verb FORMS.

---

## 4. The measurement — 29 rows, 10 LIVE divergences

**Live (references unanimous, zerobas differs):**

| row | statement | refs | zb | |
|---|---|---|---|---|
| `r.keyok` | `KEY1,"X"` | **0** | 2 | 🔴 a valid statement REFUSED |
| `r.keylist` | `KEY LIST` | **0** | 2 | 🔴 same |
| `r.key` | `KEY1,` | 24 | 2 | 🔴 symptom of the two above |
| `r.midd` | `MID$(A$,2)=` | 24 | 2 | 🔴 the one filed row that survives |
| `d.play` | `PLAY` | 24 | 2 | 🔴 confirms `TODO.md`:1569 |
| `d.using` | `PRINT USING` | 24 | 2 | 🔴 new |
| `d.usingfmt` | `PRINT USING"##"` | **2** | **0** | 🔴 new — SILENTLY COMPLETES |
| `d.ongoto` | `ON 1 GOTO` | 2 | **0** | 🔴 new — SILENTLY COMPLETES |
| `d.ongosub` | `ON 1 GOSUB` | 2 | **0** | 🔴 new — SILENTLY COMPLETES |
| `d.drawscr2` | `SCREEN2:DRAW` | 24 | 13 | 🔴 new — invisible in SCREEN 0 |

**Already correct** (24 on all three): `WIDTH`, `OPEN`, `INPUT#`, `PRINT#`.
**Green as filed**: `A$=`, `A$=+`. **Correct by the refined rule**: `SWAP A,`,
`SWAP ,B` (2 on all three), `DRAW` in SCREEN 0 (5 on all three).
**Controls**: `r.letsok`, `r.middok`, `d.swapok`, `d.widthok`, `d.playok`,
`d.ongotook`, `d.drawok2`, `r.keyoff` — all 0 on all three.

⚠️ **EXCLUDED, NOT GREEN — `FIELD`: THE REFERENCES DISAGREE** (VG-8020 **5**,
CF-3300 **24**). The VG-8020 has no disk, so its answer is about the machine and
not about the rule. A row where the references disagree is not a want
and this one cannot become one without a second disk-bearing reference.

⚠️ **UNMEASURABLE BY THIS INSTRUMENT, NAMED RATHER THAN DROPPED**: bare `INPUT`
and `LINE INPUT` are valid statements that prompt and **wait**. A boot-per-case
probe row would hang, not answer. `INPUT#` is the reachable parse error in that
family and it is green.

---

## 5. Predictions scored — 13 of 28

Round 1: **8 of 20.** Round 2: **5 of 8.**

* **The one-rule prediction is the useful failure.** Predicting all ten verbs
  from a single rule is what made two rows able to refute it at once; ten
  independent guesses would have been ten shrugs. The refutation then survived
  its own separators only half — `SWAP` really is an exception, `DRAW` never was.
* **Three rows I predicted as still-broken are green** (`A$=`, `A$=+`, and four
  of the ten denominator verbs). Predicting from a filed result column rather
  than from the tree is the same error as §1's, made by me instead of inherited.
* **`d.drawscr2` and `d.usingfmt` I got wrong on the REFERENCE side**, which is
  the only kind of miss that cannot be argued away: it is a fact about MSX BASIC
  I did not know and could only have learned by running it.

---

## 6. What this does NOT establish

* **No fix is proposed here and none was measured.** Ten live divergences at
  four different roots (KEY's absent form, `MID$()=`'s string path, `ON`'s
  silent completion, the `PLAY`/`USING`/`DRAW` operand slots) are four slices,
  not one, and each needs its own price against a 99 B page 1.
* The name/value/separator partition in §2 rests on **two** separating rows.
* Nothing here says the sixteen D-MISSOP slots are still green; they were not
  re-run.
