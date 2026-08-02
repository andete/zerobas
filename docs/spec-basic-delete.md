<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-DELETE — `DELETE <range>`: the statement half

Measurement:
[`docs/delete-msx1-characterization.md`](delete-msx1-characterization.md) — the
crunch half is six `lna-del*` rows (all three sides byte-identical **before** this
slice), the run-time half is a 34-row `dlt` walk in two rounds. Two references
(Philips VG-8020, National CF-3300) agreeing on **every** row, `--repeat 2`,
every payload past the echo guard on all three sides.

Neighbours whose cells this must not move: D-KWGAP4
([`spec-basic-kwgap4.md`](spec-basic-kwgap4.md) **R-K1/R-K2/R-K3**), D-LNREF
(**R-R1/R-R2/R-E**), D-LNLIST (**R-L1/R-L3**), D-RETLN
([`spec-basic-retln.md`](spec-basic-retln.md) **R-T1..R-T5**), D-CONTR, D-ONELIN.

---

## 1. What is missing

D-KWGAP4 closed the **token** half of `DELETE`/`AUTO`/`RENUM`/`LLIST` and re-filed
the **statement** half with its numbers. This slice takes **`DELETE` only**.
`RENUM`, `AUTO` and `LLIST` stay filed, unchanged, for the reasons D-KWGAP4 gave
(`RENUM` needs a two-pass old→new map over every `$0E`; `AUTO` and `LLIST` cannot
be put to a reference in this harness at all).

Today `DELETE` crunches to `$A8` byte-exactly and has no `stmt_table` row, so
`exec_stmt`'s table search falls through to `es_noentry` → `stmt_error` →
**ERR 2** for every argument shape. `kwgd-delete` is pinned `KNOWN_DIVERGE` at
` 2  2 ` to record exactly that.

## 2. The rules to implement

All eight are measured on both references, both agreeing. `lo` and `hi` are the
two ends of the range; **a number that is absent is 0** (R-D5).

* **R-D1 — `DELETE n` is `DELETE n-n`.** `dlt-one` and `dlt-same` read the same
  ` 13  0 `. There is no separate single-line form.

* **R-D2 — 🔴 the HIGH end must name a stored line, EXACTLY, and the check runs
  BEFORE anything is deleted.** `DELETE 20-35` deletes **nothing** and raises
  **ERR 5** (*illegal function call*) even though lines 20 and 30 are inside the
  range (`dlt-himiss`). Past the last line is not an exemption:
  `DELETE 10-65529` is also ERR 5 (`dlt-hitop`).

* **R-D3 — the LOW end need not name anything.** `DELETE 15-30` deletes 20 and
  30 with no complaint (`dlt-lomiss`); the walk starts at the first stored line
  **≥ lo**, measured where that is a strict inequality (`dlt-lomid`,
  `DELETE 25-30` → only line 30).

  🔴 R-D2 and R-D3 are the finding. The two ends of the range are **not**
  symmetric, and moving the missing number from one side of the `-` to the other
  changes ` 9  0 ` into ` 15  5 `.

* **R-D4 — `lo > hi` is ERR 5 and deletes nothing.** `DELETE 30-20` (`dlt-rev`)
  — and line 20 *does* exist, so this is not R-D2 firing. A machine that simply
  deleted the empty set would read ` 15  0 `.

* **R-D5 — an absent number is 0, on either end.** `DELETE -30` = `0-30`
  (deletes 10, 20, 30 — `dlt-openlo`); `DELETE 20-` = `20-0` (ERR 5,
  `dlt-openhi`); bare `DELETE` = `0-0` (ERR 5, `dlt-none`). No extra rule: all
  three fall out of R-D2/R-D4 once the default is 0. `dlt-none` is what makes
  this a reading rather than a fit — `0-0` is not reversed, so only the
  absent-high-end clause of R-D2 can be raising it.

* **R-D6 — anything but end-of-statement after the range is ERR 2, raised
  BEFORE any deletion.** `DELETE 10,30` reads ` 15  2 ` — a comma is not a
  separator even though the tokeniser happily arms across it. A `:` **is**
  accepted (R-D8).

* **R-D7 — a SUCCEEDING `DELETE` is a program edit; a FAILING one is a complete
  no-op.** Success clears the variables and invalidates `CONT` (`dlt-vars`
  ` 0  0 `, `dlt-cont` ` 0  17 `) — the same `vars_reset` tail every other edit
  reaches. Failure changes **nothing**: `dlt-varsbad` keeps A = 1 and
  `dlt-contbad`'s `CONT` still resumes. These are two separate lines of code,
  and only round 2 could see the second.

* **R-D8 — `DELETE` ENDS the line and the program.** Inside a `RUN` the program
  stops with ERR 0 and no further line executes (`dlt-inprog` ` 0  0 `); in
  direct mode the rest of the typed line does not run either (`dlt-tail`
  ` 0  0 ` against its control's ` 9  0 `), and that is not a syntax error — the
  `:` is accepted and then abandoned.

  🔴 **THESE ARE TWO MECHANISMS, NOT ONE, AND KNIFE K5 IS WHAT SAID SO** (§7).
  The spec ran them together until the cut: `ENDFLAG` stops the **program**
  (`dlt-inprog`), while the handler's plain `ret` abandons the rest of the
  **line** (`dlt-tail`) — and K5, which removes only `ENDFLAG`, moves the first
  row and leaves the second exactly where it was.

### 2.1 What this does NOT change

* **the crunch.** All six argument shapes are already byte-identical to both
  references (characterization §1). Nothing in `tokenise.inc` or `kwtable.inc`
  is touched, and the `lna-del*` / `lnrx-delete` / `ref-delete` cells must not
  move.
* **`RENUM` / `AUTO` / `LLIST`.** Still undispatched, still ERR 2.
  `kwgd-renum` keeps its pin.
* **`LIST`'s ignored argument.** `ex_list` is untouched; `LIST <range>` stays
  filed.
* **`.`, the current-line pseudo-line-number** — measured (characterization §5),
  understood, deliberately deferred. See §6.

## 3. Funding — re-measured from a clean build at HEAD `3a25449`

`rm -rf build && make basic-reloc`:

| region | free |
|---|---|
| main page-0 low region | **23 B** |
| main page 1 | **124 B** |
| sub page 0 | 3913 B |
| sub page 1 | **3339 B** |

⚠️ **D-KWGAP4's verdict that this item does not fit was measured against a wall
with 143 B of slack in it.** It said `stmt_table` costs 3 B/row (knife K5, still
good), page 1 had 6 B free, and four rows are 12 B. D-RETLN's 160 B dead-
instruction carve (`3a25449`) took page 1 to 124 B and low to 23 B. One verb's
row is 3 B and the wall is no longer the reason to defer the other three — their
own reasons (§1) are.

### 3.1 The split, and why the parse goes sub-side

`SUBROM_IDX_LINEEDIT` (`sub/lineedit.asm`) is already the home of the whole
TXTTAB memmove engine — `prog_find_del`, `delete_at`, `open_gap` and the
`relink` loop, with its `vars_reset` tail. `DELETE` is that engine driven over a
range, so the **entire verb** goes there as a third `LE_OP`, and main pays only
a marshalling head:

| where | what | cost |
|---|---|---|
| main page 1 | one `stmt_table` row | **3 B** |
| main page 1 | `ex_delete`: marshal the cursor, `subrom_call`, raise / stop | **~34 B** |
| sub page 1 | `le_delrange`: parse + validate + the delete walk + `skip_spaces`/`find_line_bc` clones | **194 B** |

🎯 **THREE DESIGNS WERE ON THE TABLE AND K6 MEASURED ALL THREE FROM THE SYMBOL
TABLE, NOT FROM AN ESTIMATE** (`build/sub.sym`: `le_delrange` body 137 B,
`ldr_skipsp` 7 B, `ldr_num` 15 B, `ldr_find` 29 B = 188 B, against a measured
ROM delta of 194 B including the selector arm):

| design | main page 1 | sub page 1 |
|---|---|---|
| **(a) whole verb sub-side — SHIPPED** | **37 B** (3 + 34) | 194 B |
| (b) parse resident, walk sub-side | ~87 B | ~137 B |
| (c) whole verb resident | **~148 B** | 0 |

🔴 **AND (c) WAS NEVER ACTUALLY AVAILABLE.** Page 1 had **124 B** free; a fully
resident `DELETE` needs ~148 B — the 188 B verb, less the two clones (36 B) it
would not need resident and the ~7 B of marshalling, plus the 3 B table row.
The design that reads as the "simple, obvious" one does not fit, and nothing in
this slice would have discovered that without measuring the parts. (b) does fit,
and costs 50 B more than (a) for no behavioural difference.

The argument grammar is `[$0E lo] [$F2 [$0E hi]]` with no expression evaluation
anywhere, so the whole statement marshals as ONE POINTER and needs nothing from
page 1 but a blank-skipper — which is what makes (a) available at all.

⚠️ **A sub page-1 tenant cannot call `skip_spaces` ($4240, main page 1).** It
gets an ~8 B sub-local clone, the same call the file already made for
`skip_to_eol` + `le_tok_skip` (that header records the duplication and its
closure argument). `find_line_bc` ($4xxx, main page 1) is duplicated verbatim
for the same reason — it is a pure link-chain walk over RAM.

### 3.2 RAM — no new cells

`DELETE`'s two ends ride **`SL_NUM`** (low) and **`SL_SIZE`** (high), and the
cursor rides **`SL_TOK`** — the same cells `store_line` marshals, as a SECOND
VALUE NAMESPACE, exactly like `LE_OP` on `DISKOP_OP`.

🔴 **This is [[two-namespaces-sharing-a-value]], so the non-overlap is proved by
grep and not by assertion.** Every reader of the three cells is on the
`LE_OP_STORE` path: `le_store` itself, `prog_find_del` (`SL_NUM`) and `open_gap`
(`SL_SIZE`). `delete_at` reads only `SL_SLOT`+`PRGEND`; `relink_body` reads
neither. One `subrom_call` reaches exactly one `LE_OP`, so a store and a
delrange are never in flight together.

## 4. The change

1. **[`basic/sysvars.inc`](../basic/sysvars.inc)** — `LE_OP_DELRANGE equ 2`, the
   `SL_DELLO`/`SL_DELHI` aliases with §3.2's proof recorded at the equates, and
   the `LE_STATUS` contract widened: it now carries the **ERR code** (0 = ok,
   2 = R-D6, 5 = R-D2/R-D4), not a boolean.
2. **[`basic/interp.asm`](../basic/interp.asm)** — one `stmt_table` row,
   `db DELETE_TOKEN / dw ex_delete`. Position is free (the table is a linear
   search with no ordering contract beyond "hot statements near the front");
   it goes at the end, beside the other editor-adjacent verbs.
3. **[`basic/program.asm`](../basic/program.asm)** — `ex_delete`, next to
   `store_line`/`relink`, the other two `SUBROM_IDX_LINEEDIT` shims.
4. **[`sub/lineedit.asm`](../sub/lineedit.asm)** — `le_delrange` + the
   blank-skipper and `find_line_bc` clones; one new arm in `lineedit_tenant`'s
   selector.

## 5. Rows and pins

* **new**: 34 `dlt` rows (25 round 1 + 8 round 2 + `dlt-contbare`, §9) and 5
  `lna-del*` crunch rows.
  `dlt-` joins `lnblank-say-acceptance`'s default `ONLY=`, taking it to 74 rows.
* **retired**: `kwgd-delete`'s `KNOWN_DIVERGE` pin at ` 2  2 ` — **DELETED, not
  edited**. Eighth cohort to retire that way. The say gate goes 40/40 with
  3 pins to **74/74** with **4** — one retired, two added, so the set GREW by
  one and that is said out loud rather than rounded.
* **added**: `dlt-dot` and `dlt-dotedit`, pinned `KNOWN_DIVERGE` at zerobas's
  exact ` 15  2 ` (§6).
* **controls that must stay green**: `dlt-ctl` ` 15  0 `, `dlt-errctl` ` 1  2 `,
  `dlt-varsctl` ` 1  0 `, `dlt-contctl` ` 5  0 `, `dlt-tailctl` ` 9  0 `,
  `dlt-comma` ` 15  2 ` — the last of which **agrees today for the wrong reason**
  and must still agree after the handler lands.

## 6. Deliberately out of scope: `.`

> ✅ **NO LONGER OUT OF SCOPE — LANDED 2026-08-02 as D-DOTLINE**
> ([`spec-basic-dotline.md`](spec-basic-dotline.md), measured in
> [`dotline-msx1-characterization.md`](dotline-msx1-characterization.md)).
> `dlt-dot` / `dlt-dotedit` are **retired** and green. This section is kept as
> the record of the decision to decline, which was right: the walk found **four
> writers** where these two rows could see one, and three of the four would have
> been implemented wrongly from a `DELETE`-shaped reading — including the
> `DELETE` **verb itself**, which turns out **not** to write `.` even though the
> bare-line-number delete does.

`DELETE .` works on both references and resolves `.` to **the line the editor
last touched** — `dlt-dotedit` is the row that says "last touched" rather than
"highest", and one row could not have. That is a pseudo-line-number MSX-BASIC
shares across `LIST`/`DELETE`/`AUTO`/`RENUM`/`EDIT`; zerobas records nothing of
the kind, and the parts these two rows do **not** measure (what `.` is after a
`RUN`, after an error, after a `LIST`, on a cold machine) are a walk of their
own. Implementing it inside `DELETE` alone would ship a rule one verb wide.

It is filed in `TODO.md` and **pinned**, not silently dropped: `.` reaches the
statement as the literal `$2E` (characterization §1), which R-D6 answers with
ERR 2 — a consequence of a rule this slice *does* implement, so the pinned value
cannot drift for an unrelated reason.

## 7. Knives — each with a predicted RED set **and** predicted GREEN survivors

Every cut is scored against the **whole 34-row battery** on zerobas, and every
RED row carries a predicted **exact value** written down before the build — not
just "moves".

* **K1 — delete the high-end existence check** (R-D2): `jr c,ldr_walk` → `jr
  ldr_walk`. Every range with `lo ≤ hi` now proceeds.
  RED (12): `dlt-miss` `dlt-zero` `dlt-below` `dlt-above` `dlt-none` → ` 15  0 `
  (empty range, no complaint) · `dlt-himiss` `dlt-bothmiss` → ` 9  0 ` ·
  `dlt-hipast` `dlt-hitop` → ` 0  0 ` · `dlt-empty` → ` 0 ` · `dlt-varsbad` →
  ` 0  0 ` and `dlt-contbad` → ` 0  17 ` (the empty delete now takes the SUCCESS
  path, so the edit reset fires).
  GREEN (22): everything else — and 🔴 **`dlt-rev` and `dlt-openhi` MUST STAY
  GREEN.** They are R-D4's rows, not R-D2's, and that is exactly the attribution
  §2's R-D5 note rests on. If they redden, the two rules are not separated.
* **K2 — delete the `lo > hi` check** (R-D4): drop `jr c,ldr_fc`.
  RED (1): `dlt-rev` → ` 15  0 ` (hi = 20 exists, so R-D2 passes; the walk then
  finds line 30 already above hi and stops, deleting nothing, with no error).
  GREEN (33): all — including `dlt-openhi` and `dlt-none`, whose ERR 5 is
  R-D2's doing. The mirror of K1's claim.
* **K3 — "an absent number is 65535"** (R-D5): `ld de,0` → `ld de,$FFFF` in
  `ldr_num`.
  RED (1): `dlt-openlo` (`DELETE -30`) → ` 15  5 ` — lo becomes 65535, which is
  above hi, so R-D4 refuses what should delete three lines.
  GREEN (33): `dlt-openhi` and `dlt-none` still read ` 15  5 `, because line
  65535 does not exist either. The default's value is only observable on the
  LOW end, which is the asymmetry R-D2/R-D3 predict.
* **K4 — run the edit reset on the FAILURE path too** (R-D7's second half):
  `ldr_fail`'s `ret` → `jp relink_body`.
  RED (2): `dlt-varsbad` → ` 0  5 ` (A cleared by a delete that failed) ·
  `dlt-contbad` → ` 4  5 ` (A cleared, so the resumed line 30 makes 4, not 5).
  GREEN (32): all others — 🔴 **this is precisely the cut round 1 could not have
  scored**, because every round-1 failure row `RUN`s afterwards and `RUN` clears
  the variables itself.
* **K5 — drop `ENDFLAG`** (R-D8): delete `inc a / ld (ENDFLAG),a` in `ex_delete`.
  Predicted RED (2): `dlt-inprog` → ` 4  0 ` · `dlt-tail` → ` 9  0 `.
  **Measured: `dlt-inprog` → ` 4  0 ` as predicted; `dlt-tail` DID NOT MOVE.**

  🔴 **A PREDICTED-RED ROW STAYING GREEN IS A READING, AND THIS ONE SPLITS R-D8
  INTO TWO RULES.** Ending the *program* and ending the *line* are two different
  mechanisms here, and the spec had run them together:
  * the rest of the **program** is stopped by `ENDFLAG` — `dlt-inprog` is its
    row, and K5 is the proof;
  * the rest of the **line** is abandoned by the handler's plain `ret`, which is
    how `ex_rem` and a bare `RETURN` already end a line. `dlt-tail` is its row,
    and `ENDFLAG` has nothing to do with it.

  ⚠️ **AND THE `ret` CANNOT BE KNIFED, WHICH IS ITSELF THE POINT.** The obvious
  cut — `ret` → `jp exec_stmt` — would **hang**: `ex_delete` never advances HL
  past the argument (nothing marshals the cursor back, §4), so `exec_stmt` would
  re-dispatch the same `DELETE` token forever. Not running the tail is not a
  choice this handler makes, it is forced by the marshalling; `dlt-tail` is
  gated structurally rather than by a branch. What keeps that row from being
  vacuous is its control: `dlt-tailctl` reads ` 9  0 ` on all three sides, so a
  `:`-separated second statement demonstrably does run in general.
* **K7 — delete the `ERRFLG` store in `ex_cont_no`** (§9).
  RED (2): `dlt-contbare` → ` 0 ` · `dlt-cont` → ` 0  0 `.
  GREEN (32): `dlt-contctl` and `dlt-contbad` included — both reach a
  *succeeding* `CONT` and never enter the arm. The knife that says the fix is
  load-bearing on the refusal path and inert everywhere else.
* **K6 — aimed at the JUSTIFICATION, not the code.** §3.1 claims the sub-side
  split saves ~54 B of main page 1 over a main-side parse. Measure it: build
  both and read `make basic-reloc`'s page-1 figure. A justification that cannot
  be measured is not a reason.
* **K7 — delete the `ERRFLG` store in `ex_cont_no`** (§9). RED: `dlt-contbare`,
  `dlt-cont`. GREEN: `dlt-contctl`, `dlt-contbad` — both of which reach a
  *succeeding* `CONT` and so never enter the arm at all. This is the knife that
  says the fix is load-bearing on the refusal path and inert everywhere else.

### 7.1 Results — six cuts, five exact, one that corrected the spec

| knife | predicted RED | measured | verdict |
|---|---|---|---|
| K1 | 12 rows, listed values | all 12, every value exact; 22 green | ✅ |
| K2 | `dlt-rev` → ` 15  0 ` | exactly that, 33 green | ✅ |
| K3 | `dlt-openlo` → ` 15  5 ` | exactly that, 33 green | ✅ |
| K4 | `dlt-varsbad` ` 0  5 `, `dlt-contbad` ` 4  5 ` | both exact, 32 green | ✅ |
| K5 | `dlt-inprog` ` 4  0 `, `dlt-tail` ` 9  0 ` | `dlt-inprog` exact; **`dlt-tail` did not move** | 🔴 split R-D8 in two |
| K7 | `dlt-contbare` ` 0 `, `dlt-cont` ` 0  0 ` | both exact, 32 green | ✅ |

🔴 **K1 AND K2 ARE EACH OTHER'S CONTROL, AND THAT IS THE POINT OF RUNNING BOTH.**
K1 removes the existence check and leaves `dlt-rev` and `dlt-openhi` green; K2
removes the reversal check and reddens `dlt-rev` **alone**, leaving `dlt-openhi`
and `dlt-none` green. So R-D2 and R-D4 are separated in *both* directions —
neither rule is doing the other's work, which is what §2's R-D5 note asserts and
what a single knife could only have half-shown.

⚠️ **Every knife was reverted against the build it cut, and the restoration was
verified by hash**: all four touched source files and both ROMs returned to
their exact pre-knife md5s.

⚠️ **RUN THE WHOLE 34-ROW BATTERY FOR EVERY KNIFE, NOT JUST THE PREDICTED-RED
SUBSET.** D-RETLN's knife runner reported three of four cuts as proving nothing
and was wrong on all three; re-run by hand, every predicted row moved to its
exact predicted value, and the runner was DELETED rather than shipped. A knife
scored only against what it was expected to break cannot detect the case where
it broke something else instead.

⚠️ **Revert against the BUILD each knife cut, never `git checkout`** — that
reverts the SLICE. And never `shutil.copy2`: it preserves mtime, `make` then
skips the rebuild, and the check hashes the stale knifed ROM.

## 8. Gates — measured on the shipped bytes

Run against the final ROM (`basic-reloc.rom` md5 `6222a4fd…`, `sub.rom`
`4fcc98bb…`), rebuilt from clean after the last knife was reverted and
hash-verified against the pre-knife build.

`unit-test` **55/55** · `deadcode` **0 dead** both builds · `lnblank-acceptance
REPEAT=2` **526/526**, allowlist EMPTY · `lnblank-say-acceptance` **74/74**,
4 pins · `lnblank-echo` · `logicops` 193/193 · `float` exit 0 · `array` 149/151
(`ifc.instr.zero`/`.neg` by name) · `arrdim` 73/73 · `clearpool` 52/52 ·
`badfnum` 93, 0 unfiled · `lof` · `chancost-characterize` · `diskbasic` ·
`bdos` · `fat-error` · `error-trap` · `abort` · `stop`/`strig`/`key`-trap ·
`linemax` 60/60 · `sysvarsweep` exit 0.

⚠️ **`DELETE` mutates the program text, so `linemax`, `lnblank` and the
`cont`-related suites are the most exposed** — and D-RETLN's lesson is that the
suite which catches the regression is usually not the one written for the
feature.

### 8.1 Two gates fired, and neither was this slice's own battery

* 🔴 **`test_stmt_dispatch.py` FAILED on the first corpus run** —
  *"UNEXPECTED entry `$A8` → `ex_delete`: not in the pre-refactor chain"*. That
  is the gate working exactly as designed: a new statement may not reach the
  dispatch table without the independent `EXPECTED` list being told, and adding
  the row there is a deliberate act. It is the same alarm SWAP's note in that
  file records, fired in the opposite direction.
* ⚠️ **`badfnum` reported one unfiled divergence — `ind_cneg` reading `None`.**
  `None` is *no capture*, not a changed error class, and the payload
  (`A$=INPUT$(3,#-1)`) touches nothing this slice went near. **Re-run rather
  than assumed**: the second run reads `IFC`/`IFC`, 93 cases, **0 unfiled
  divergences**, exit 0. A flake, and it is recorded here rather than quietly
  dropped.

## 9. A byproduct: `CONT`'s refusal never set `ERR`, and it is not this verb's defect

`dlt-cont` read ` 0  0 ` against the references' ` 0  17 ` the first time zerobas
had a `DELETE` handler. The obvious reading — *"`DELETE` fails to invalidate
`CONT`"* — is **refuted by the row's own first number**: `A` is 0, so the edit
reset did run, and `CONTVALID` really was cleared.

[`basic/program.asm`](../basic/program.asm)'s `ex_cont_no` printed *can't
continue* and never stored an ERR code, so `PRINT ERR` read 0. `err_msgtab` had
mapped **ERR 17 → `err_cont`** all along ([`basic/interp.asm`](../basic/interp.asm));
only the store was missing, and nothing had ever looked — no probe in the tree
asserts `ERR` after a refused `CONT`.

🔴 **`dlt-contbare` IS THE ROW THAT SAYS WHOSE DEFECT IT IS**: a bare `CONT` on a
fresh machine, with no `DELETE` anywhere in the payload. *A "not mine"
falsification says nothing about whose it is* — this one names the owner. Fixed
here (+5 B) rather than pinned, because the alternative is a third pin for two
instructions, and `dlt-cont` is a `DELETE` gate row that would otherwise ship
red for a reason that has nothing to do with `DELETE`.
