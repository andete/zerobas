<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-LSTRNG — `LIST <range>`, measured

Instrument: [`probes/basic/basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py),
the 20-row `lst` battery (run time, `--say`, **`screen_tail` readout**) and ten
`lna-list*` rows (crunch, memory read). Two references — **Philips VG-8020** and
**National CF-3300** — plus zerobas, `--repeat 2`, every payload past the echo
guard on all three sides before any reading below was read.

Gate: `make lnblank-say-acceptance ONLY=lst-` (run time) and
`make lnblank-acceptance ONLY=lna-list` (crunch).

---

## 0. The apparatus finding that came first: `say()` is STRUCTURALLY BLIND to a listing

🔴 **No `lst` row could have been read by the mechanism every other `--say`
battery in this probe uses, and the reason is not a bug — it is the definition.**
`say()` ([`basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py))
classifies a screen row as *echo* when every character in it also appears in
something the case typed:

```python
if row and set(row) - typed:      # keep the row only if it has an UNTYPED char
```

Every line `LIST` prints is a line the case typed in order to store it. So a
listing's characters are always a subset of the typed alphabet, and `say()`
returns `<nothing printed>` — for a correct full listing, for a correct
one-line listing, and for a machine that printed nothing at all. That is the
[[chancost-noread-guard]] shape exactly: a sentinel that also means *no reading*
is not a measurement, and here it would have compared EQUAL across all three
sides and reported `agrees` on every row in the battery.

The bracket span (`result_span_after_echo`, what the other SAY_ONLY rows use)
cannot read one either, for a different reason: it returns **one value**, and
"which lines were listed" is a **set**.

The readout used instead is **`screen_tail`**
([`probes/lib/omsx_repl.py:539`](../probes/lib/omsx_repl.py:539)) — the rows
between the echoed command and the closing prompt, `|`-joined. It is not new
(three probes already use it); what is new here is a third decode arm in
`run_side`, `TAIL_ONLY`, a subset of `SAY_ONLY` that keeps all of that set's
isolation and filtering and changes only the final decode. It carries **both
ends of the range in one reading**, and on a row that refuses it carries the
error TEXT instead — so one row answers *what was listed* and *did it refuse*
together.

⚠️ **The two "empty" answers are kept apart, deliberately.** `screen_tail`
returns `None` when the echo row cannot be found (apparatus failure) and `""`
when the command printed nothing between its echo and the prompt — which for
`lst-above` is the expected ANSWER. They decode to `<NO ECHO>` and
`<nothing listed>`. Collapsing them would make a machine that listed nothing
indistinguishable from a machine the scraper lost, and both would compare EQUAL.

⚠️ **The LIST must be the case's last typed line**, because `screen_tail` stops
at the first row that IS a prompt and the closing prompt is bare only when
nothing was typed after it. And a command line whose echo WRAPS breaks the
readout silently ([`basic_probe_missing.py:188`](../probes/basic/basic_probe_missing.py:188));
the longest here is `LIST 10-65529` at 13 columns against 40.

---

## 1. The crunch — all ten shapes, all three sides, byte-identical

D-LNREF locked the three shapes its `$0E` arming needed. The four an argument
handler actually has to parse had **no reference answer at all**, and a handler
written against bytes nobody locked is a handler written against nothing (the
same argument [`delete-msx1-characterization.md`](delete-msx1-characterization.md) §1
made for `DELETE`). All ten agree on **all three sides**, `--repeat 2`:

| row | typed | stored body (all three sides) |
|---|---|---|
| `lna-listctl` | `20 LIST 10` | `<93> <0E><0A><00>` |
| `lna-listrng` | `20 LIST 10-20` | `<93> <0E><0A><00><F2><0E><14><00>` |
| `lna-listopen` | `20 LIST -20` | `<93> <F2><0E><14><00>` |
| `lna-listplus` | `20 LIST 10+20` | `<93> <0E><0A><00><F1><0E><14><00>` |
| `lna-listkw` | `20 LIST 10 AND 20` | `<93> <0E><0A><00> <F6> <0F><14>` |
| `lna-listcol` | `20 LIST 10:20` | `<93> <0E><0A><00>:<0F><14>` |
| **`lna-listhi`** | `20 LIST 30-` | `<93> <0E><1E><00><F2>` |
| **`lna-listnone`** | `20 LIST` | `<93>` |
| **`lna-listcomma`** | `20 LIST 10,30` | `<93> <0E><0A><00>,<0E><1E><00>` |
| **`lna-listdot`** | `20 LIST .` | `<93> .` |

The four new rows (bold) were **predicted before the run** to be byte-for-byte
mirrors of D-DELETE's `lna-delhi` / `-delnone` / `-delcomma` / `-deldot` with
`$93` in place of `$A8`, and they are. That is a reading about the tokeniser and
not only about `LIST`: D-LNREF measured the arming set as a **list of 14
keywords**, and this says the arming state machine really is uniform across that
list rather than per-keyword. Had any one of the four differed from its `DELETE`
mirror, the arming would not have been uniform and that would have been a
finding of its own.

Three readings matter for the statement half:

* **the `-` is the ordinary MINUS token `$F2`, and it does not disarm
  line-number mode** — the number behind it is another `$0E` reference. The
  grammar to parse is `[$0E lo] [$F2 [$0E hi]]`, entirely in the token alphabet,
  with **no expression evaluation anywhere**.
* **`.` is NOT crunched** — it survives as the literal `$2E`, so resolving it is
  entirely the statement's problem, and a statement that does not resolve it
  sees a byte that is neither `$0E` nor `$F2` nor a terminator (§5).
* **a comma is kept verbatim and the mode arms across it** (`lna-listcomma`), so
  whether a comma is a separator is a **run-time** question the crunch cannot
  answer.

---

## 2. The controls

| row | what it establishes |
|---|---|
| `lst-all` | 🔴 **THE ROW WITHOUT WHICH NOTHING BELOW IS A READING ABOUT RANGES.** |

The tail is **detokenised text**. A row can therefore differ across sides
because the *range* differs or because zerobas renders `10 REM A` differently
from the reference — two candidate causes, and a row with two candidate causes
measures neither. `lst-all` types the same four-line program and lists **all**
of it: it is the one row in the battery whose subject zerobas already
implements, so it must read identically on all three sides *before* this slice
changes anything. If it does, every divergence below is about the argument. If
it does not, the argument rows measure nothing and the finding is in the
detokeniser instead.

`lst-all` reads `10 REM A|20 REM B|30 REM C|40 REM D` on **all three sides**. So
zerobas's detokeniser already renders this program identically to both
references, and every divergence in §3 is about the argument.

---

## 3. The headline: `LIST`'s range is **NOT** `DELETE`'s range

Both references agree on **every** row below, `--repeat 2`. Sixteen of the
twenty diverge on zerobas, which lists the whole program for every argument
(§4). Shorthand: **A** = `10 REM A`, **B** = `20 REM B`, **C** = `30 REM C`,
**D** = `40 REM D`.

🔴 **EVERY PLACE `DELETE` RAISES ERR 5, `LIST` SIMPLY LISTS WHAT IS IN RANGE.**
D-DELETE measured, one week earlier and with the same grammar and the same
instrument, that `DELETE`'s high end must name a stored line *exactly*, that a
reversed range is an error, and that an absent number is 0 on **either** end.
Not one of those three carries over:

| typed | `LIST` (both refs) | `DELETE` (D-DELETE) |
|---|---|---|
| `20-35` — high end names nothing | **`B\|C`** | **ERR 5**, nothing deleted |
| `10-65529` — the "everything from 10" idiom | **`A\|B\|C\|D`** | **ERR 5** |
| `30-20` — reversed | **nothing, no error** | **ERR 5** |
| `25` — names nothing | **nothing, no error** | **ERR 5** |
| `20-` — absent HIGH end | **`B\|C\|D`** | **ERR 5** (`20-0`) |

The one rule that fits all twenty rows is **D-DELETE's algorithm with the
default for `hi` changed from 0 to 65535 and both validations deleted**:

```
lo = 0 ; hi = 65535
if a $0E number is present         :  lo = hi = that number
if a $F2 '-' follows               :  hi = 65535
    if a $0E number follows the '-':  hi = that number
list every stored line with lo <= number <= hi
```

### 3.1 R-L1 — `LIST n` is `LIST n-n`

| row | typed | refs |
|---|---|---|
| `lst-one` | `LIST 20` | `B` |
| `lst-same` | `LIST 20-20` | `B` |

Identical, exactly as `dlt-one`/`dlt-same` were for `DELETE`. This is the one
rule the two verbs **do** share.

### 3.2 R-L2 — 🔴 NEITHER end has to name a stored line

| row | typed | refs | reading |
|---|---|---|---|
| `lst-rng` | `LIST 20-30` | `B\|C` | both ends real |
| `lst-lomiss` | `LIST 15-30` | `B\|C` | low end names nothing — no complaint |
| `lst-himiss` | `LIST 20-35` | `B\|C` | **high end names nothing — also no complaint** |
| `lst-bothmiss` | `LIST 15-35` | `B\|C` | neither does |
| `lst-hipast` | `LIST 10-45` | `A\|B\|C\|D` | past the last line is fine |
| `lst-hitop` | `LIST 10-65529` | `A\|B\|C\|D` | so is the line-number ceiling |

🔴 **`lst-himiss` IS THE ROW THAT REFUTES THE INHERITED RULE.** It is the exact
payload shape that reads ` 15  5 ` under `DELETE` — the same program, the same
numbers, the same crunched bytes — and it lists two lines without complaint.
The asymmetry D-DELETE found is a property of `DELETE`, not of the shared range
grammar, and a `LIST` written by copying `le_delrange`'s validations would
refuse five of the twenty shapes measured here.

`lst-hipast` and `lst-hitop` were D-DELETE's round-2 rows, added there because
every round-1 high end was reachable before the program ran out. They are in
round 1 here precisely because that lesson was already paid for.

### 3.3 R-L3 — the walk starts at the first stored line ≥ lo

| row | typed | refs | reading |
|---|---|---|---|
| `lst-lomid` | `LIST 25-30` | `C` | 25 sits BETWEEN two stored lines; B is below it and is not listed |

Measured where the inequality is **strict**, which `lst-lomiss` (whose low end
is below everything) cannot distinguish.

### 3.4 R-L4 — an empty range lists nothing and raises nothing

| row | typed | refs |
|---|---|---|
| `lst-miss` | `LIST 25` | `<nothing listed>` |
| `lst-zero` | `LIST 0` | `<nothing listed>` |
| `lst-below` | `LIST 1-5` | `<nothing listed>` |
| `lst-above` | `LIST 60-70` | `<nothing listed>` |
| `lst-rev` | `LIST 30-20` | `<nothing listed>` |
| `lst-empty` | `LIST 10` on an EMPTY program | `<nothing listed>` |

⚠️ **SIX ROWS, ONE VALUE — SO NO ONE OF THEM SAYS WHY, and this was written down
as a weakness of the round BEFORE the run** (`predictions-round1.md`). The tail
readout does distinguish *listed nothing* from *refused*, because a refusal
prints its message into the tail and `lst-comma` demonstrates that it does. But
that is an argument about direct mode, not a measurement, and `lst-rev` is
exactly the row where `DELETE` has a **rule** rather than an empty walk. Round 2
(`lse-*`, §6) asks `ERR` directly on five of the six.

### 3.5 R-L5 — 🔴 an absent number is NOT 0; it is the nearest EXTREME

| row | typed | refs | reading |
|---|---|---|---|
| `lst-openlo` | `LIST -30` | `A\|B\|C` | absent low end = 0 |
| `lst-openhi` | `LIST 20-` | **`B\|C\|D`** | **absent high end = the END, not 0** |
| `lst-all` | `LIST` | `A\|B\|C\|D` | neither end given = everything |

🔴 **`lst-openhi` IS THE SINGLE MOST DANGEROUS ROW IN THE BATTERY FOR AN
IMPLEMENTER.** D-DELETE's R-D5 states, correctly for `DELETE` and with three
rows behind it, that *an absent number is 0*. Carried over unexamined it makes
`LIST 20-` mean `LIST 20-0` — an empty range that lists nothing — where both
references list three lines. The default is not a shared property of the
grammar; it is per-verb, and it is asymmetric within `LIST` itself.

And bare `LIST` is what forbids the tidier-looking rule *"hi defaults to lo"*:
under that rule bare `LIST` would be `0-0` and would list nothing. It lists
everything. The default for `hi` is 65535 **until a low number without a `-`
overrides it**, which is what the §3 pseudocode encodes.

### 3.6 R-L6 — a comma is a syntax error, not a separator

| row | typed | refs |
|---|---|---|
| `lst-comma` | `LIST 10,30` | `Syntax error` |

The tokeniser arms a `$0E` reference across the comma (§1 `lna-listcomma`), so
the bytes reach the statement as two perfectly good line-number references and
the refusal is entirely the statement's. This is the one rule `LIST` and
`DELETE` share on the failure side (`dlt-comma` ` 15  2 `). Round 2 pins the
numeric class.

⚠️ **This is also the row that proves the tail readout can see a refusal at
all** — without it, the six `<nothing listed>` rows of §3.4 would have no
demonstration that a refusing machine reads differently from a silent one.

### 3.7 `.` — measured, and OUT OF SCOPE

| row | typed | refs |
|---|---|---|
| `lst-dot` | `LIST .` | `D` |

`.` reaches the statement as the literal `$2E` (§1), and both references resolve
it to a line. ⚠️ **`lst-dot` ALONE CANNOT SAY WHICH RULE THAT IS**: line 40 is
both the last line typed and the highest-numbered, the identical ambiguity
`dlt-dot` had before `dlt-dotedit` separated them. Round 2's `lse-dotedit`
re-enters line 20 last and asks again (§6).

It is **out of scope for this slice** by the same reasoning D-DELETE gave: `.`
is one editor-state mechanism shared by `LIST`/`DELETE`/`AUTO`/`RENUM`/`EDIT`,
zerobas records nothing of the kind, and what `.` reads after a `RUN`, after an
error, after a `LIST` and on a cold machine is still unmeasured. Implementing it
inside `LIST` alone would ship a rule one verb wide. It is filed in `TODO.md`
and **pinned**.

## 4. What zerobas does today

`ex_list` ([`basic/list.asm:41`](../basic/list.asm:41)) does `inc hl` past the
`LIST` token and walks the whole program, so **every** row reads the full
listing `A|B|C|D` — 16 of the 20 diverge. `lst-all` and `lst-empty` agree (their
subject is the whole-program walk, which is what zerobas implements), and
`lst-hipast`/`lst-hitop` agree **for the wrong reason**: their correct answer
happens to be the whole program too. Those two are the `dlt-comma` shape — cells
that must go on agreeing after the handler lands, which is a different claim
from never having moved.

⚠️ The 16 divergences were all re-run **boot-per-case by the probe's own
self-heal** before being reported; a batched delivery mangle reads exactly like
a divergence and `--repeat` cannot tell them apart. The healed values are the
ones tabulated above.

---

## 5. Round 2 — `ERR`, and what `LIST` ENDS

Fourteen `lse` rows, bracket-span readout (each asks for ONE number, which is
what that readout returns), both references agreeing on every row, `--repeat 2`,
echo guard green on all three sides.

### 5.1 There is no error to raise for a range — R-LS2/R-LS4 confirmed

| row | typed | refs | zerobas |
|---|---|---|---|
| `lse-ctl` | `LIST` then `ERR` | ` 0 ` | ` 0 ` |
| `lse-rev` | `LIST 30-20` then `ERR` | ` 0 ` | ` 0 ` |
| `lse-miss` | `LIST 25` then `ERR` | ` 0 ` | ` 0 ` |
| `lse-himiss` | `LIST 20-35` then `ERR` | ` 0 ` | ` 0 ` |
| `lse-above` | `LIST 60-70` then `ERR` | ` 0 ` | ` 0 ` |
| `lse-empty` | `LIST 10`, empty program | ` 0 ` | ` 0 ` |
| `lse-comma` | `LIST 10,30` then `ERR` | ** 2 ** | ` 0 ` ← diverges |

🔴 **`lse-rev` IS THE ROW ROUND 1 NEEDED AND COULD NOT PRODUCE.** Six round-1
rows read `<nothing listed>`, so none of them could say whether the machine had
walked an empty range or refused. Under `DELETE` a reversed range is a **rule**
(`dlt-rev` ` 15  5 `) and not an empty walk — the one place the two verbs could
still have agreed. They do not: `ERR` is 0, so **there is no reversal check to
write**, and R-LS4 is one rule rather than a rule plus an exception.

`lse-comma` pins the numeric class behind round 1's `Syntax error` text: **2**.

### 5.2 🔴 `LIST` ends the line AND the program — both predictions were WRONG

| row | typed | refs | zerobas | predicted |
|---|---|---|---|---|
| `lse-tail` | `LIST 20:B=9` then `B`,`ERR` | ` 0  0 ` | ` 0  0 ` | ` 9  0 ` ❌ |
| `lse-tailctl` | `C=1:B=9` then `B`,`ERR` | ` 9  0 ` | ` 9  0 ` | ` 9  0 ` ✓ |
| `lse-inprog` | `20 LIST 40` inside a `RUN` | ` 1  0 ` | ` 13  0 ` | ` 13  0 ` ❌ |

**Both of the two rows flagged in `predictions-round2.md` as *genuinely open*
came back against the prediction, and in the same direction.** The reasoning
written down beforehand was that `DELETE` ends the run because it has just
memmoved the text `CURLINE` points into, while `LIST` moves nothing — a
mechanism story that sounded like a derivation and was not one. `LIST` ends both,
exactly as `DELETE` does.

`lse-tailctl` reads ` 9  0 ` on all three sides, so a `:`-separated second
statement demonstrably does run in general; it is `LIST` that ends the line. And
`ERR` is **0** in `lse-tail`, so the `:` is *accepted* and then abandoned, not
rejected.

⚠️ **`lse-tail` AGREES ON ZEROBAS TODAY, AND NOT FOR THIS REASON.** An
argument-ignoring `ex_list` also fails to run the tail. It is a `dlt-comma`-shaped
cell: it must go on reading ` 0  0 ` after the handler lands, which is a
different claim from never having moved.

### 5.3 `LIST` is not a program edit — and that is a POSITIVE requirement

| row | typed | refs | control |
|---|---|---|---|
| `lse-vars` | `… RUN : LIST 20 : PRINT A` | ` 1  0 ` | A survives |
| `lse-cont` | `… RUN : LIST 30 : CONT` | ` 5  0 ` | `lse-contctl` ` 5  0 ` |

`DELETE` clears the variables and invalidates `CONT` (D-DELETE R-D7). `LIST`
does neither. 🔴 **This matters precisely because R-LS7 makes `LIST` share
`ENDFLAG` with `DELETE`**: the implementation will sit next to `ex_delete`'s
`xor a / ld (CONTVALID),a` and must not copy it. `lse-cont` reading the same
` 5 ` as its control is the only thing standing between this slice and a
`CONT` that silently stops working after a `LIST`.

### 5.4 `.` is the line the editor LAST TOUCHED — the same mechanism as `DELETE`'s

| row | typed | refs |
|---|---|---|
| `lst-dot` | lines 10..40 in order, then `LIST .` | `40 REM D` |
| `lse-dotedit` | …then line **20 re-entered**, then `LIST .` | **`20 REM B`** |

The answer moves from `D` to `B`, so `.` is not "the highest line" — it is the
line the editor last touched, exactly what `dlt-dotedit` measured for `DELETE`.
D-DELETE's claim that this is **one** mechanism shared across the editor verbs
now has a second verb behind it rather than one verb and an assumption.

Still out of scope, still pinned — see
[`spec-basic-listrange.md`](spec-basic-listrange.md) §6.

## 6. Scoring the predictions

Both rounds' predictions were written before their runs
(`predictions-round1.md`, `predictions-round2.md`).

| round | rows | exact | wrong |
|---|---|---|---|
| 1 (crunch) | 4 new shapes | 4 | 0 |
| 1 (`lst`) | 20 | 20 | 0 |
| 2 (`lse`) | 14 | 12 | **2** (`lse-tail`, `lse-inprog`) |
| knives | 7 | 7 | 0 |

⚠️ **The two misses were both on the two rows the prediction document had
already flagged as the ones it was not confident about** — which is the useful
outcome: the uncertainty was located correctly even though the guess was wrong.
The twenty `lst` rows were predicted exactly, including the five where `DELETE`'s
measured rules would have given a different answer, because the prediction was
written as an explicit choice between two named hypotheses rather than as an
extrapolation from the neighbouring slice.
