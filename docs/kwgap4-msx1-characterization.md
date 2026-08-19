<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-KWGAP4 — `DELETE` / `AUTO` / `RENUM` / `LLIST`, measured: the token, the arm, and what the verb DOES

Instrument: [`probes/basic/basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py).

The **crunch** side is D-LNREF's, not re-derived here: batteries `lnrx` (25 rows),
`ref` (4 of them), `lna` (3 of them), oracle-locked over the whole 162-word
denominator in
[`lnref-msx1-characterization.md`](lnref-msx1-characterization.md) §1/§4.

The **run-time** side is new: two batteries added by this slice, `kwgd` (5 rows,
three sides) and `kwgz` (5 rows, **zerobas only** — §3.1 says why).

Two oracles, **Philips VG-8020** and **National CF-3300**, `--repeat 2`, every
payload past the echo guard on all three sides. The two references agree on
every row below.

---

## 0. The headline

1. 🔴 **The four verbs are not one problem, they are two, and the filed item
   already knew it: a missing TOKEN and a missing STATEMENT.** This slice closes
   the token half completely and byte-exactly, and leaves the statement half
   filed — with the numbers that say why (§4).
2. 🔴 **Adding the token changes NOTHING at run time, and that had to be
   measured rather than reasoned.** All four verbs already raise **ERR 2** on
   zerobas today, by four *different* accidental parses; after the token they
   raise ERR 2 by one deliberate path (`exec_stmt`'s table search falling
   through to `stmt_error`). The risk the TODO item named — "a token for a
   statement with no handler may turn a currently-working garbage parse into a
   new error class" — is real in general and **empty here**, and §3 is the
   reading that says so on both sides of the change.
3. 🔴 **AND THE ECHO GUARD HAD NEVER SEEN A SINGLE `--say` PAYLOAD IN THIS
   PROBE.** `--echo` shared the measurement pass's `SAY_ONLY` filter, so
   `--echo --only lnrd-` answered *"no rows selected"*. D-LNREF's spec §6 claims
   "every gating payload typed verbatim on every side"; it was true of the 210
   rows the filter left. Found while trying to guard this slice's own new rows,
   fixed, and **all seven `lnrd` rows are now `ECHOED` on all three sides** —
   the claim was correct, it had simply never been checked (§5).

---

## 1. The crunch — what the four words store (D-LNREF's lock, unchanged)

`20 <WORD> 10`, both references identical:

| word | reference | zerobas at HEAD `cb6ae68` | wrong in |
|---|---|---|---|
| `DELETE` | `<A8> <0E><0A><00>` | `DE<88>E 10` | token **and** argument |
| `AUTO` | `<A9> <0E><0A><00>` | `AU<D9> <0F><0A>` | token **and** argument |
| `RENUM` | `<AA> <0E><0A><00>` | `RENUM 10` | token **and** argument |
| `LLIST` | `<9E> <0E><0A><00>` | `L<93> <0E><0A><00>` | **token only** |

⚠️ **`LLIST`'s argument is already right, and it is right BY ACCIDENT.** zerobas
mangles `LLIST` into the variable `L` plus a genuine `LIST` token (`$93`), and
`$93` is one of the fourteen words D-LNREF taught `branch_lineno` to arm on — so
the `10` behind it crunches to `$0E` for a reason that has nothing to do with
`LLIST`. The pin on this row moved once inside D-LNREF's own slice for exactly
that reason ([`spec-basic-lnref.md`](spec-basic-lnref.md) §5).

**The mode reaches the whole statement for all three arg-taking verbs** (`lna`,
both references):

| row | typed | both references |
|---|---|---|
| `lna-delrng` | `20 DELETE 10-20` | `<A8> <0E><0A><00><F2><0E><14><00>` |
| `lna-auto2` | `20 AUTO 10,5` | `<A9> <0E><0A><00>,<0E><05><00>` |
| `lna-renum3` | `20 RENUM 10,20,30` | `<AA> <0E><0A><00>,<0E><14><00>,<0E><1E><00>` |

🔴 **`lna-auto2` is the row that says the mechanism has no idea what a line
number IS.** `AUTO 10,5`'s second argument is an **increment**; it is stored as
`$0E,5` anyway. A `$0E` is a MODE over digit runs, not a typed value — which is
why the token and the arm cannot be separated, and why adding the entry without
the arm would be a regression rather than a partial fix.

## 2. 🔴 The four words collide with NOTHING, in either direction

`match_kw` stops at the **first** table entry that matches and does no
longest-match and no word-boundary check — the reason
[`kwtable.inc`](../basic/kwtable.inc) has to place `DEFINT` before `DEF`. So the
question "may these four entries go anywhere in the table?" is a real one, and
it is answered by walking all **137** existing entries rather than by eyeballing
the neighbours:

| new word | existing keywords that are a PREFIX of it | existing keywords it is a prefix OF |
|---|---|---|
| `DELETE` | none | none |
| `AUTO` | none | none |
| `RENUM` | none | none |
| `LLIST` | none | none |

Table order is therefore free for all four. The near-misses are near-misses and
no more: `DEF`/`DEFINT` diverge from `DELETE` at char 3 (`F` vs `L`), `REM` from
`RENUM` at char 3 (`M` vs `N`), and `LIST` from `LLIST` at char 2 (`I` vs `L`) —
which is also precisely why today's mangles are `DE`+`LET`+`E`, `AU`+`TO` and
`L`+`LIST`: the reference words were being found **one or two positions late**.

## 3. What the four verbs DO at run time — before, on all three sides

### 3.1 ⚠️ Two of the four may not be put to a reference at all

`AUTO` enters interactive line-entry and `LLIST` drives `LPTOUT`, which **hangs**
a machine with no printer plugged. Both are already classified **crunch-only for
exactly these reasons** by the keyword sweep (`TODO.md`, the 18 crunch-only
holes), and `omsx_repl` raises `SystemExit` at its 240 s cap — so one such row
does not degrade a run, it **kills** it.

🔴 **So the instrument REFUSES them rather than sampling around them.** `SIDE_LOCK`
in the probe names `kwgz-*` as zerobas-only and fails loudly, with the reason,
if anyone points them at a reference. The hazard is now a property of the
apparatus instead of a note somebody has to remember — and the alternative,
quietly dropping the rows, is the shape where `--sides vg8020,cf3300,zb --only
kwgz-` would have read as a clean run.

**The consequence is stated, not hidden: the `kwgz` readings carry no oracle
lock and gate nothing.** They are a before/after on one machine, which is
exactly the question §0.2 asks.

### 3.2 The three-sided rows (`kwgd`, say mode, `--repeat 2`)

| row | typed | both references | zerobas |
|---|---|---|---|
| `kwgd-ctl`^ | `ZZTOP 10` | ` 2 ` | ` 2 ` |
| `kwgd-delctl`^ | `10 A=1` `20 A=2` `RUN` | ` 2  0 ` | ` 2  0 ` |
| `kwgd-delete` | …`DELETE 20` `RUN` | ` 1  0 ` | 🔴 ` 2  2 ` |
| `kwgd-renctl`^ | `10 A=1` `20 A=2:END` `GOTO 20` | ` 2  0 ` | ` 2  0 ` |
| `kwgd-renum` | …`RENUM 100` `GOTO 110` | ` 2  0 ` | 🔴 ` 0  8 ` |

`DELETE 20` really removes line 20 on both references (`A` keeps the value line
10 gave it); `RENUM 100` really renumbers, so `GOTO 110` finds the line that used
to be `20`. On zerobas the first is a Syntax error that leaves the program
standing (`A` reaches 2, `ERR` is the 2 the failed `DELETE` left) and the second
leaves line `110` non-existent (`ERR 8`, Undefined line number).

🔴 **Each control can move its own subject, and that is not decoration.**
`kwgd-delctl` reads the value ` 2 ` that `kwgd-delete` must *change to* ` 1 `;
`kwgd-renctl` proves the direct-mode `GOTO` instrument reads ` 2  0 ` when the
target line **does** exist, so `kwgd-renum`'s ` 0  8 ` is a missing LINE and not
a broken instrument. `kwgd-ctl` pins the class this machine gives a word it
cannot dispatch **on every side**, so zerobas' pinned ` 2 `s below are a
difference and not a number floating on its own.

### 3.3 The one-sided rows (`kwgz`, zerobas only)

| row | typed | zerobas at HEAD | by what path |
|---|---|---|---|
| `kwgz-ctl`^ | `10 A=1` | ` 0 ` | nothing went wrong |
| `kwgz-delete` | `DELETE 10` | ` 2 ` | `DE` `<88>` `E 10` — a name, then a `LET` token |
| `kwgz-auto` | `AUTO 10` | ` 2 ` | `AU` `<D9>` — a name, then a `TO` token |
| `kwgz-renum` | `RENUM 10` | ` 2 ` | `RENUM 10` verbatim — a name, then a number |
| `kwgz-llist` | `LLIST 10` | ` 2 ` | `L` `<93>` — a name, then a `LIST` token |

🔴 **Four different accidental parses, one error code.** That is the whole
finding: today's ERR 2 is not one behaviour, it is four coincidences that happen
to land on the same number, and nothing about *"garbage parse"* guaranteed it.
`kwgz-ctl` reading ` 0 ` is what says the instrument can tell a 2 from a
non-2 at all.

### 3.4 AFTER — the same ten rows, on the built change

| battery | row | before | after |
|---|---|---|---|
| `kwgz` (zb) | `ctl` / `delete` / `auto` / `renum` / `llist` | ` 0 ` ` 2 ` ` 2 ` ` 2 ` ` 2 ` | **identical** |
| `kwgd` (3 sides) | `ctl` `delctl` `renctl` | agree | agree |
| `kwgd` (3 sides) | `delete` | ref ` 1  0 ` / zb ` 2  2 ` | **unchanged**, now pinned |
| `kwgd` (3 sides) | `renum` | ref ` 2  0 ` / zb ` 0  8 ` | **unchanged**, now pinned |

🔴 **Nothing moved, and that is the reading the slice needed.** The four verbs
reached ERR 2 through four accidental parses before and reach it through one
deliberate path now (`es_noentry` → `stmt_error`); the *class* is the same, so
adding a token for an undispatched statement cost no behaviour. Had this been
assumed rather than measured, the `kwgd`/`kwgz` rows would not exist and the
claim would have rested on reading `es_noentry` — the shape
[[answer-signoff-questions-by-measuring]] exists to refuse.

⚠️ **The two `kwgd` pins are the STATEMENT half's trip-wire and they are pinned
at values that did NOT change.** A pin whose value happens to survive the slice
that files it is still a pin: it passes only while zerobas keeps failing in
exactly this way, so the day a `DELETE` or `RENUM` handler lands, the gate says
so instead of the row quietly turning green.

⚠️ **`kwgz-delete` and `kwgz-renum` repeat two verbs that §3.2 already covers,
and that is deliberate.** Without them the zerobas-side reading would be a
sample of two verbs where the question is about four — and the four rows have to
be in the *same shape* for "they all read 2" to mean anything.

## 4. Why the STATEMENTS are not in this slice — the numbers

Measured on a clean `make basic-reloc` at HEAD:

| region | free | who lives there |
|---|---|---|
| main ROM low (`$2812-$3FFF`) | **9 B** | string engine, input, float, `stmt` bodies |
| main ROM page 1 (`$4000-$7FFF`) | **6 B** | `exec_stmt`, `stmt_table` (`$40AF`), handlers |
| sub ROM page 0 | **3958 B** | `kwtable`, the tokeniser, the detokeniser |

🔴 **`stmt_table` is at `$40AF` — main page 1 — and costs 3 B per entry. Four
dispatch rows are 12 B against 6 B free.** The four *table rows alone* do not
fit, before a single byte of handler. Low and page 1 are co-mapped and therefore
coupled ([[rom-region-structure-review]]), so the 9 B next door is not relief.

And the handlers are not small:

* **`RENUM`** must rewrite every line's number *and* every `$0E` reference in the
  whole program, including the ones inside `ON..GOTO` lists — the largest verb
  of the four by a wide margin, and it needs a two-pass old→new map.
* **`AUTO`** is interactive: it drives the line editor's prompt loop, which is a
  sub-ROM page-1 tenant (`lineedit_tenant`), from a main-ROM statement.
* **`DELETE`** must unlink a range and rebuild the link fields — the smallest,
  and still not a handful of bytes.
* **`LLIST`** is the cheapest: a printer sink already exists
  ([`basic/print.asm:434`](../basic/print.asm:434), `PRDEST=1` → `LPTOUT`) and
  `ex_list` already exists, so the handler is "set the sink, jump to `ex_list`".
  ⚠️ **But it would inherit a filed defect:** `ex_list` ignores its argument
  (`LIST <range>` is a standing item), so `LLIST 10-20` would print the whole
  program to the printer.

**None of the four is a table edit, and all four want main-ROM page 1.** They are
filed with these numbers attached; see [`spec-basic-kwgap4.md`](spec-basic-kwgap4.md) §3.4.

## 5. 🔴 The apparatus finding: an echo guard that could not see its own payloads

```
$ python3 probes/basic/basic_probe_lnblank.py --echo --only lnrd- --sides zb
APPARATUS FAILURE: no rows selected
```

`main()` filtered `SAY_ONLY` rows out of **both** the measurement pass and the
`--echo` pass with one condition. The measurement pass has a reason (a say row
reads the screen, not the stored line). The echo pass does not: it reads its own
typed lines back off the screen and needs no measurement capture at all.

**So no `--say` row in this probe had ever been echo-guarded** — not `err`, not
`dir`, not `dotd`/`lnld`/`cnmd`, and not D-LNREF's seven `lnrd` rows. This is
[[say-only-rows-are-ungated]] a second time, on the **guard** instead of on the
gate, and it is the shape D-DECBLANK filed as *"delivery that cannot be verified
MAY NOT GATE"*.

Two fixes, both in `main()`:

* `--echo` no longer shares the filter. All 7 `lnrd` and all 10 new `kwgd`/`kwgz`
  rows now read **`ECHOED` on every side they are allowed on** — the pre-existing
  claim was true; it had simply never been tested.
* `--echo --say` is **refused**. `run_side` returns the say values before it ever
  reaches the echo branch, so the combination silently ran the SAY pass and let
  `main()` print an `APPARATUS FAILURE` banner over readings that were never echo
  verdicts at all. That is how this defect was found.

⚠️ **The second fix is the one to keep in mind.** The first run of this slice's
new rows used `--echo --say` and produced a red banner listing every row as "not
typed verbatim" — a *failure* report over a pass that had measured something
else. A guard whose output cannot be trusted in either direction is worse than
no guard.

### 5.1 🔴 And letting the guard see the rows exposed a THIRD fault, in batching

`run_side` decided batching with a single `any()` over the whole selection:

```python
batch = (not isolate) and not any(lb in SAY_ONLY for lb, _l in cases)
```

One say row therefore forced **boot-per-case on every other row too**. That was
invisible for as long as say rows were filtered out of every non-say pass — and
the moment `--echo` could see them, `make lnblank-echo` (which selects
*everything*) went from ~3 batched boots per side to **~560**. Caught by watching
the target's elapsed time, not by a gate.

The isolation itself is load-bearing and is not what was wrong: `err-ctl` reads
`ERRCODE` state that `err-over` leaves behind, so say rows genuinely may not share
a boot. The fix splits the selection — say rows boot-per-case, the other 518 stay
batched, results reassembled in the original order. The memory pass (no say rows)
and the say pass (only say rows) are unmixed and behave exactly as before, and
the self-heal path passes `isolate=True` and is untouched.

⚠️ **Three faults, one family: a check that could not see its own subject, and
said something anyway.** Two failed toward "nothing to see" (the filter, the
`copy2` restore in §7.0 of the spec), two toward a false alarm (`--echo --say`,
K5's landing guard) — and this one toward a target that would still have been
*correct*, just unrunnable. Correct-but-unrunnable is how a gate quietly stops
being run at all.
