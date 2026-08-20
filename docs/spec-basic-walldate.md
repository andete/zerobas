# A wall figure must say when it was read

D-WALLDATE, 2026-08-19, on `main`, based on `8dce108` (D-RECLEN). Not a fidelity
slice — a measurement of the *filed record*, and the gate for a class
[`repricing-page1-2026-08-19.md`](repricing-page1-2026-08-19.md) §4 found and
filed the same day. **0 ROM bytes.**

---

## 1. The class

D-REPRICE went looking for declines a 64 B carve might fund and found something
else: **four open `TODO.md` items asserting a current free-space figure in prose,
as fact, and all four wrong.**

| item | asserted | actual that day |
|---|---|---|
| editor / program management | *"THE PAGE-1 WALL IS NOW **14 B**"* | 64 B |
| `FIELD overflow` | *"main page 1 is now **16 B**"* | 64 B |
| `ex_let_arr_str` | *"Main page 1 is down to **49 B**"* | 64 B |
| slim the file-channel context | *"**9 B** free low / **6 B** free page 1"* | 5 B / 64 B |

🎯 **THIS IS THE 160-DEAD-BYTES SHAPE, IN PROSE**: a figure that was a reading
when written, copied nowhere, checked by nothing, and false from the next slice
onward. ⚠️ **Three of the four UNDERSTATE the wall**, so each reads as *less*
affordable than it is — a slice opening one and trusting the inline figure
declines work it can already fund.

The session that filed it then moved the walls **three more times** (D-FORRET
64 → 41, D-LOADSWEEP 41 → 50 and low 5 → 23, D-RECLEN 50 → 22), which is
precisely the condition that manufactures more of them.

---

## 2. 🔴 The hard half is the grammar, and the first two drafts prove it

Deciding *"is this sentence stale?"* means parsing English tense and intent. So
the tool asks a different question, one that is mechanical and that a human can
always satisfy:

> **A free-space figure must carry a DATE or a COMMIT, and must not be phrased in
> the present tense.**

That converts an unanswerable question into a crisp one, and dating a figure
makes its staleness self-evident to the next reader with no tool at all. **A
dated reading STANDS AS TAKEN** — this never second-guesses one.

Getting there took three drafts, and each failure was measured against the
**pre-D-REPRICE `TODO.md`**, where all four defects were live:

| draft | rule | founding defects caught |
|---|---|---|
| 1 | a date/commit **anywhere in the item** | 🔴 **0 of 4** |
| 2 | + the qualifier must be **line-local**, past tense allowed | 3 of 4 |
| 3 | + **only a date or commit counts**, and present tense is its own finding | ✅ **4 of 4** |

🔴 **DRAFT 1 WAS VACUOUS AND REPORTED CLEAN.** Every item names a slice
(`D-LSTRNG`) or carries a date somewhere in its history, so a block-wide search
exempts everything. **It would not have caught a single one of the defects it was
built for** — and it said so with a green run and a confident denominator.

🔴 **DRAFT 2 FAILED ON THE WORD `was`.** Allowing past-tense prose as a qualifier
let the 14 B item through, because its *next* line reads *"82 B **was** itself
the post-carve figure"*. `was` is exactly how a stale figure reads. Only a date
or a commit counts.

🎯 **AND A DATE ALONE IS NOT ENOUGH — THE FOURTH DEFECT PROVES IT.** *"RE-PRICED
2026-08-09 by D-EVALCHK … main page 1 **is now 16 B**"* carries its date on the
line above and still read as current. A date beside a present-tense claim does
not retract it. That is why PRESENT-TENSE is a **separate finding with a
different remedy** — not *"add a date"* but *"say WAS, not IS NOW"*.

Two exclusions were added for signal, each measured: a **ledger** line (a cost or
a `→` delta — *"It cost 11 B of page 1"*, *"page 1 24 → 13 B free"*) is history
and misleads nobody, which took the calibration set from 17 figures to 11; and a
**quoted** figure is evidence, not an assertion — the first live run flagged
**this tool's own residual**, which quotes all four defects verbatim in order to
document them.

---

## 3. What it does NOT catch — measured, not guessed

**K-WA3 missed, and the miss is recorded rather than tuned away.** The UNDATED
rule is the weak half: a figure is exempt if a date appears within one line, and
that date need not be *about* the figure. K-WA3 planted an undated wall claim one
line below an unrelated `Filed 2026-08-11` and it was **not** flagged.

The radius was chosen by measurement:

| radius | founding defects | false positives on the clean tree |
|---|---|---|
| 0 | 4/4 | **6** |
| **1** | **4/4** | **0** ← chosen |
| 2 | 4/4 | 0 |

Radius 0 flags every dated record whose date wrapped onto the previous line,
which is ordinary prose here. **PRESENT-TENSE is the strong half** and is not
defeated by an adjacent date at all. Read a clean run as evidence about
present-tense claims and only weak evidence about undated ones.

---

## 4. Falsification

| knife | plant | predicted | measured |
|---|---|---|---|
| **K-WA1** | *"The low region has 5 B free"* | flagged | flagged (as PRESENT-TENSE, via `has`) ✅ |
| **K-WA2** | *"Measured 2026-08-19: main page 1 **is now** 22 B"* | flagged **despite the date** | exactly that ✅ |
| **K-WA3** | an undated figure beside an unrelated date | flagged | 🔴 **NOT flagged** — §3 |

⚠️ **K-WA1 tripped the PRESENT rule, not the UNDATED one**, so it is not evidence
about the undated path; K-WA3 is, and it failed. Recorded as such rather than
counted as two-thirds of a pass.

🎯 **K-WA2 IS THE ONE THAT MATTERS**: it is the fourth founding defect, rebuilt
as a cut, and it confirms the design decision that a date does not license
present tense.

---

## 5. What it found and fixed

Ten figures across five open items, all now dated or in the past tense — three
of them the surviving originals of the founding four, which had received dated
addenda but kept their present-tense opening line, so a reader skimming still hit
*"THE PAGE-1 WALL IS NOW 14 B"* first. The readings are unchanged; only their
tense and their dates are.

## 6. Gates

`make wall-assertion-check` — **0 findings**, 62 open items swept, 6 quoting a
wall. `unit-test` 59/59, `deadcode` 0 dead, `redundant-load-check` clean,
`audit-citations` CLEAN. No `.asm` touched and no ROM change.
