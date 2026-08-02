<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-DELETE — `DELETE <range>`, measured: the **high** end is checked and the **low** end is not

Instrument: [`probes/basic/basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py),
the `dlt` battery (run time, `--say`) and six `lna-del*` rows (crunch, memory
read). Two references — **Philips VG-8020** and **National CF-3300** — plus
zerobas, `--repeat 2`, every payload past the echo guard on all three sides
before any reading below was read.

Gate: `make lnblank-say-acceptance` (run time — `dlt-` is in its default
`ONLY=`; scope with `ONLY=dlt-`) and `make lnblank-acceptance` (crunch).

34 run-time rows in two rounds — 25 in round 1, 8 in the round 2 that round 1's
answer made reachable (§3.2, §3.7), and `dlt-contbare`, which is not about
`DELETE` at all (§6).

---

## 0. The headline

**The two ends of a `DELETE` range are not symmetric, and no filed description
said so.** `DELETE 15-30` deletes lines 20 and 30 without complaint — its low end
names no stored line at all. `DELETE 20-35` deletes **nothing** and raises
**ERR 5** — its low end is a real line and only its high end is absent. The
range is not "the lines between two numbers"; it is *"every line from `lo`
onward, up to and including a line that must EXIST and be numbered exactly
`hi`"*.

Three more things the walk settled, each of which a single-shape row could not
have:

* **the check happens BEFORE anything is deleted.** `DELETE 20-35` leaves all
  four lines standing, not the two below its bad end;
* **`DELETE` is a program EDIT in the full sense** — it clears the variables and
  invalidates `CONT`, exactly like typing a line;
* **`DELETE` inside a running program ends the program**, silently and with
  ERR 0.

And one shape is deliberately **not** implemented by the slice that measured it:
`DELETE .` resolves `.` to the *current line* (§5), a pseudo-line-number shared
with `LIST`/`AUTO`/`RENUM`/`EDIT` that zerobas has no concept of at all.

---

## 1. The crunch was already byte-exact — on every argument shape

D-KWGAP4 locked `DELETE 10` and `DELETE 10-20`. The four shapes an editor verb
actually takes had **no reference answer at all**, and a run-time handler
written against bytes nobody locked is a handler written against nothing. All
six agree on all three sides (`lna-del*`, `--repeat 2`):

| row | typed | stored body (all three sides) |
|---|---|---|
| `lna-delrng` | `20 DELETE 10-20` | `<A8> <0E><0A><00><F2><0E><14><00>` |
| `lna-delopen` | `20 DELETE -30` | `<A8> <F2><0E><1E><00>` |
| `lna-delhi` | `20 DELETE 30-` | `<A8> <0E><1E><00><F2>` |
| `lna-delnone` | `20 DELETE` | `<A8>` |
| `lna-deldot` | `20 DELETE .` | `<A8> .` |
| `lna-delcomma` | `20 DELETE 10,30` | `<A8> <0E><0A><00>,<0E><1E><00>` |

Two readings matter for the statement half:

* **the `-` is the ordinary MINUS token `$F2`, and it does not disarm
  line-number mode** — the number behind it is another `$0E` reference, exactly
  as D-LNLIST measured for `20 GOTO 1-5`. The grammar the handler parses is
  therefore `[$0E lo] [$F2 [$0E hi]]`, all in the token alphabet, with no
  expression evaluation anywhere.
* **`.` is NOT crunched.** It survives as the literal character `$2E`, so
  resolving it is entirely the statement's problem (§5).

`lna-delcomma` is the row that says a comma is *not* a range separator even
though the tokeniser happily arms across it (`AUTO 10,5` is the precedent). Its
run-time answer is §3.6.

---

## 2. The controls, and that each can move its own subject

| row | all three sides | what it establishes |
|---|---|---|
| `dlt-ctl` | ` 15  0 ` | the four-line bitmask program with **no** DELETE. Every subject row below is this payload with exactly one typed line added. |
| `dlt-errctl` | ` 1  2 ` | 🔴 **`RUN` PRESERVES `ERR`.** Without this the second number in every row below would read 0 by construction and the whole error half of this walk would be decoration. |
| `dlt-varsctl` | ` 1  0 ` | a variable set by a `RUN` survives to the next direct-mode statement. |
| `dlt-contctl` | ` 5  0 ` | `CONT` after a `STOP` really resumes (A = 1+4). |
| `dlt-tailctl` | (§3.7) | a `:`-separated second statement on a direct-mode line really runs. |

The program is a **bitmask**, not a counter: lines 10/20/30/40 add 1/2/4/8, so
the single number `A` after `RUN` names exactly *which* lines survived. A
survivor count could not tell `DELETE 30-20` deleting the pair from it deleting
one of them.

## 3. The readings

Both references agree on **every** row below, `--repeat 2`, and zerobas
diverges on every one of them (it has no handler at all — §4).

### 3.1 R-D1 — a single line number deletes exactly that line

| row | typed | refs | mask |
|---|---|---|---|
| `dlt-one` | `DELETE 20` | ` 13  0 ` | 15−2: line 20 gone |
| `dlt-same` | `DELETE 20-20` | ` 13  0 ` | identical — `n` and `n-n` are the same statement |

### 3.2 R-D2 — 🔴 the HIGH end must name a line that EXISTS; the LOW end need not

This is the finding, and it takes four rows to state because two of them read
the same and mean opposite things:

| row | typed | refs | reading |
|---|---|---|---|
| `dlt-rng` | `DELETE 20-30` | ` 9  0 ` | both ends real → 20 and 30 deleted |
| `dlt-lomiss` | `DELETE 15-30` | ` 9  0 ` | **low end names nothing — no complaint**, same two lines |
| `dlt-himiss` | `DELETE 20-35` | ` 15  5 ` | **high end names nothing — ERR 5, and NOTHING deleted** |
| `dlt-bothmiss` | `DELETE 15-35` | ` 15  5 ` | the high end decides; the low end never gets a vote |
| `dlt-hipast` | `DELETE 10-45` | ` 15  5 ` | round 2: **past the LAST line is still ERR 5** |
| `dlt-hitop` | `DELETE 10-65529` | ` 15  5 ` | round 2: so is the whole legal line-number ceiling |

`dlt-lomiss` and `dlt-himiss` are the same shape with the missing number moved
from one side of the `-` to the other, and they read ` 9  0 ` and ` 15  5 `.

🔴 **`dlt-hipast` AND `dlt-hitop` ARE ROUND-2 ROWS AND THEY CLOSE A HOLE ROUND 1
COULD NOT SEE.** Every round-1 high end that failed (25, 35, 5, 70) named a
number the walk could reach *before* running out of program, so "a line numbered
exactly `hi` must exist" and the far weaker "`hi` must not be past the last
line" predicted the same answer on all of them. `DELETE 10-65529` — the natural
idiom for *delete everything from line 10 on*, and the one an implementer would
reach for — separates them, and it is **ERR 5**. The rule is **exact
existence**, with no ceiling exemption.

🔴 **AND `dlt-himiss` ALSO SETTLES THE ORDER.** Lines 20 and 30 are both inside
`20-35` and both survive, so the existence check runs **before** the first
deletion. An implementation that deleted as it walked and raised on reaching the
end would leave the mask at 9, not 15.

### 3.3 R-D3 — a single number that names nothing is the same error

| row | typed | refs |
|---|---|---|
| `dlt-miss` | `DELETE 25` | ` 15  5 ` |
| `dlt-zero` | `DELETE 0` | ` 15  5 ` |
| `dlt-below` | `DELETE 1-5` | ` 15  5 ` |
| `dlt-above` | `DELETE 60-70` | ` 15  5 ` |
| `dlt-empty` | `DELETE 10` on an EMPTY program | ` 5 ` |

`dlt-one` and `dlt-same` make `DELETE n` equivalent to `DELETE n-n`, so R-D3 is
not an extra rule — it is R-D2 with `hi = lo`. `dlt-empty` is the degenerate
case of the same thing and needed no special pleading.

And the low end really is *"the first stored line ≥ lo"*, measured where that is
a **strict** inequality rather than "below everything":

| row | typed | refs | mask |
|---|---|---|---|
| `dlt-lomid` | `DELETE 25-30` | ` 11  0 ` | 15−4: **only** line 30 — 20 is below 25 and survives |

### 3.4 R-D4 — a REVERSED range is an error, and it is not the same rule as R-D2

| row | typed | refs |
|---|---|---|
| `dlt-rev` | `DELETE 30-20` | ` 15  5 ` |

🔴 **This row is why R-D2 alone is not the rule.** Line 20 *does* exist, so the
high-end test passes; the range `[30,20]` is simply empty. A machine that
deleted the empty set would read ` 15  0 `. It reads ` 15  5 `.

⚠️ **Note what this does NOT license.** `lo ≤ hi` and *"the first stored line
≥ lo is at or below the line numbered hi"* predict the same answer on every
reachable input **whenever `hi` exists**, which R-D2 already requires: if
`lo ≤ hi` then `hi` is itself a line ≥ `lo`, so the first such line is ≤ `hi`;
if `lo > hi` then every line ≥ `lo` is numbered above `hi`. The two
formulations are not distinguishable by any row, and this document states the
one the rows can be read against — not a claim about how the reference is
written.

### 3.5 R-D5 — an open LOW end starts at the beginning; an open HIGH end is an error

| row | typed | refs | reading |
|---|---|---|---|
| `dlt-openlo` | `DELETE -30` | ` 8  0 ` | 15−1−2−4: lines 10, 20 **and** 30 gone |
| `dlt-openhi` | `DELETE 20-` | ` 15  5 ` | ERR 5, nothing deleted |
| `dlt-none` | `DELETE` | ` 15  5 ` | ERR 5, nothing deleted |

All three fall out of **"a missing number is 0"** plus R-D2/R-D4, with no extra
rule: `-30` is `0-30` and 0 ≤ 30 with line 30 present; `20-` is `20-0`, whose
high end 0 names nothing (and is also reversed); bare `DELETE` is `0-0`, whose
high end 0 names nothing.

⚠️ `dlt-openhi` has **two** candidate causes (absent high end *and* reversal)
and so decides neither on its own. `dlt-none` is the row that separates them:
`0-0` is not reversed, and it still reads ERR 5, so the absent-high-end clause
fires by itself.

### 3.6 R-D6 — a comma is a syntax error, not a separator

| row | typed | all three sides |
|---|---|---|
| `dlt-comma` | `DELETE 10,30` | ` 15  2 ` |

🔴 **The one run-time row zerobas already AGREES on, and it agrees for the wrong
reason** — today every `DELETE` is ERR 2 because the token is undispatched
(§4). It is a pinned control for exactly that reason: the handler must land
*keeping* this cell at ` 15  2 `, which is a different claim from it having
never moved.

### 3.7 R-D7 — `DELETE` is a program EDIT: it clears variables and kills `CONT`

| row | typed | refs | control |
|---|---|---|---|
| `dlt-vars` | `… RUN : DELETE 20 : PRINT A` | ` 0  0 ` | `dlt-varsctl` ` 1  0 ` |
| `dlt-cont` | `… RUN : DELETE 30 : CONT` | ` 0  17 ` | `dlt-contctl` ` 5  0 ` |

A is 1 before the DELETE and 0 after it, and `CONT` raises ERR 17
(*can't continue*). This is the `vars_reset` rule zerobas already implements for
every other edit ([`basic/program.asm:388`](../basic/program.asm:388) — RUN,
NEW, CLEAR/MAXFILES *and every program edit*), so `DELETE` joins the same tail
rather than getting a rule of its own.

🔴 **BUT A *FAILED* `DELETE` RESETS NOTHING, AND THAT IS A SECOND RULE, NOT A
COROLLARY.** Whether the ERR-5 exit also runs the edit reset is a separate line
of code, and no round-1 row could see it — every failure row `RUN`s afterwards,
and `RUN` clears the variables itself. Round 2 asked without the `RUN`:

| row | typed | refs | reading |
|---|---|---|---|
| `dlt-varsbad` | `… RUN : DELETE 25 : PRINT A` | ` 1  5 ` | **A survives.** ERR 5, no reset |
| `dlt-contbad` | `… RUN : DELETE 35 : CONT` | ` 5  5 ` | **`CONT` still resumes** (A = 1+4) |

`dlt-contbad`'s ` 5 ` is the same value its control `dlt-contctl` reads, so the
failed `DELETE` left the resume point untouched; the ` 5 ` in the ERR column is
the failure itself, still standing because `RUN` never ran to clear it. **A
failed `DELETE` is a complete no-op apart from `ERR`** — the program, the
variables and the `CONT` point are all exactly as they were.

### 3.8 R-D8 — `DELETE` inside a running program ENDS the program

| row | typed | refs |
|---|---|---|
| `dlt-inprog` | `10 A=A+1 : 20 DELETE 40 : 30 A=A+4 : 40 A=A+8 : RUN` | ` 0  0 ` |

Line 10 ran (A = 1), line 20 deleted line 40, and then **nothing else ran**:
line 30 would have made A = 4, and the `vars_reset` of R-D7 is what leaves the 0.
ERR is 0 — this is a clean stop, not an error.

⚠️ **This row was run ISOLATED before it was ever run in a batch.** An editor
verb rewriting the text under the interpreter's own cursor is the one payload
here with no reason to terminate, and `omsx_repl` raises `SystemExit` at its
240 s cap — such a row does not degrade a run, it kills it. It terminated.

And the same is true of a **direct-mode** line, which is a different question
(`RETURN <line>`'s own R-T4 is the precedent for asking it — a `:` there is *not*
trailing junk):

| row | typed | refs | control |
|---|---|---|---|
| `dlt-tail` | `DELETE 20:B=9` then `PRINT B` | ` 0  0 ` | `dlt-tailctl` (`C=1:B=9`) ` 9  0 ` |

B is 0, so `B=9` never ran — and ERR is **0**, so this is not a syntax error
rejecting the line. `DELETE` accepts the `:` and then simply stops. The control
reads ` 9  0 ` on all three sides, so a `:`-separated second statement on a typed
line does run in general; it is `DELETE` that ends it.

## 4. What zerobas does today

Every `dlt` row reads ` … 2 ` on zerobas: `DELETE` crunches to `$A8`
byte-exactly (§1) and has no `stmt_table` entry, so `exec_stmt`'s table search
falls through to `es_noentry` → `stmt_error` → **ERR 2**. The two controls
`dlt-ctl` (` 15  0 `) and `dlt-errctl` (` 1  2 `) read identically on all three
sides, which is what makes the divergences above readings about `DELETE` rather
than about the instrument.

One run-time row already **agrees**: `dlt-comma` (§3.6), and it agrees for a
reason that has nothing to do with commas.

## 5. `.` — measured, understood, and deliberately NOT implemented

| row | typed | refs | mask |
|---|---|---|---|
| `dlt-dot` | lines 10..40 entered in order, then `DELETE .` | ` 7  0 ` | 15−8: **line 40** |
| `dlt-dotedit` | …then line **20 re-entered**, then `DELETE .` | ` 13  0 ` | 15−2: **line 20** |

🔴 **ONE ROW COULD NOT HAVE SAID WHICH RULE THIS IS.** In `dlt-dot` line 40 is
both the last line typed *and* the highest-numbered line, so ` 7  0 ` is
consistent with either. `dlt-dotedit` re-enters line 20 last and separates them:
the answer moves to 13, so **`.` is the line the editor last touched**, not the
highest.

That makes `.` a *pseudo-line-number* — a piece of editor state MSX-BASIC shares
across `LIST`, `DELETE`, `AUTO`, `RENUM` and `EDIT` — and zerobas has no such
concept at all: nothing in the codebase records which line was last stored.
Implementing it inside `DELETE` alone would ship a rule one verb wide, and would
guess at the parts these two rows do **not** measure (what `.` is after a `RUN`,
after an error, after a `LIST`, on a cold machine). It is **out of scope for
D-DELETE, filed in `TODO.md`, and pinned**: `dlt-dot` and `dlt-dotedit` are
`KNOWN_DIVERGE` at zerobas's exact ` 15  2 `, so the day the current-line concept
lands, the gate says so.

⚠️ §1 is why the pin is safe to write today: `.` is **not crunched** — it reaches
the statement as the literal `$2E`. The handler this slice ships therefore sees
a byte that is neither `$0E` nor `$F2` nor a statement terminator, and answers
ERR 2 by the same trailing-junk rule as `dlt-comma`. The pinned value is a
consequence of a rule that IS implemented, not an accident waiting to move.


## 6. A byproduct: `CONT`'s refusal never set `ERR` — and it is not `DELETE`'s

`dlt-cont` was the one row where zerobas diverged after the handler landed: it
read ` 0  0 ` against both references' ` 0  17 `. **The obvious reading is
refuted by the row's own first number** — `A` is 0, so the `DELETE` really did
run its edit reset and `CONTVALID` really was cleared. What was missing was on
the other side of the seam: `ex_cont_no` printed *can't continue* and never
stored an ERR code, while `err_msgtab` had mapped ERR 17 → `err_cont` all along.
No probe in the tree asserts `ERR` after a refused `CONT`, so nothing had looked.

| row | typed | refs | zerobas before | after |
|---|---|---|---|---|
| `dlt-contbare` | `CONT` on a fresh machine | ` 17 ` | ` 0 ` | ` 17 ` |

🔴 **`dlt-contbare` IS THE ATTRIBUTION ROW.** It carries no `DELETE` anywhere. *A
"not mine" falsification says nothing about whose it is* — this one names the
owner, and it is why the fix went into `ex_cont_no` rather than into a pin on a
`DELETE` gate row.
