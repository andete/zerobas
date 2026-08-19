# D-ROWSHAPE — one row GRAMMAR on every exit path

**Status:** ✅ CLOSED 2026-08-07. Spec written before implementation; §11 is as-built.
**Base:** `fca8799` (D-CASSAVE), branch `main`.
**Subject:** the probe-side half of the D-CASOPEN residual in
[`TODO.md`](../TODO.md) §"Open — standing residuals" — *"A KNIFE RUNNER READ A
COMPLETE 32-ROW EXIT-2 REPORT AS TRUNCATED, BECAUSE THE TWO REPORT SHAPES ARE
INDENTED DIFFERENTLY."*
**ROM bytes: ZERO, predicted and required.** This slice touches probe sources,
one new library module, one new checker and one new unit test. Nothing under
`basic/`, `sub/` or `disk/` is edited, so all four ROM hashes must come back
byte-identical. See §7.4 for which emulator gates are run anyway, and why.

---

## 1. What is already landed, and what is open

D-CASOPEN's K-CO1 was aborted by its own truncation guard on a **complete**
32-row report, and a later runner scored **every** row of the same report as
moved. Both faults were measured; the second cost a full re-measure of eight
knife runs. The **runner-side** rule landed the same day in
[`docs/dev-workflow.md`](dev-workflow.md) §Knives:

> Parse rows into `(label → the side-under-test's VALUE)` and diff THAT; never
> diff report LINES.

That rule makes *runners* correct. It does not remove the *reason* they have to
be careful, and the residual filed the probe-side question explicitly:

> should a probe print ONE row format on every exit path, so a runner cannot be
> caught by layout at all?

This spec answers it. The short answer is **no, not "one row format"** — §4 —
and the change that ships instead is **one row GRAMMAR**, gated.

⚠️ **The reason this class is invisible to the whole corpus** (already in
§Knives, restated because it is the load-bearing fact): a probe's
failure-formatting branch **only ever executes under a knife**. No green run and
no acceptance gate has ever printed the `....` shape. That is why four probes
carried it wrong for months, and why the fix needs a **static** gate — a
behavioural one would have to fail a control to see its own subject.

---

## 2. The denominator — walked, not hand-listed

The residual's own text guesses at scope (*"`cassave`, `runtail`, `lnblank`,
`fat-error`, `diskbasic`, `lptverb`, `dskmsg`, `editverb` all print report rows
and several have exit-2 paths"*). A hand-listed denominator is a scope claim
([[a-hand-listed-denominator-is-a-scope-claim]]), so it was walked instead:
every `.py` under `probes/`, parsed with `ast`, no name lists.

| measurement | value |
|---|---|
| probe `.py` files walked (excl. `__pycache__`) | **175** |
| failed to parse | **0** |
| print a **width-padded label** line (tabular prose) | **82** (52 Makefile-invoked) |
| …of those, disagree on LAYOUT between sites | 39 (29 gated) |
| …of those, disagree on VALUE ENCODING between sites | 21 (16 gated) |
| …of those, have a **runtime-variable** label column | 29 (20 gated) |
| print a **report row** as §3 defines it | **29** |
| print report rows on **an exit-2 path AND another path** | **5** ← **the contract** |

The five:

| probe | gate | verdict today |
|---|---|---|
| `probes/basic/basic_probe_castail.py` | `castail-acceptance` | **RED** — both faults |
| `probes/basic/basic_probe_cassave.py` | `cassave-acceptance` | **RED** — both faults |
| `probes/basic/basic_probe_runtail.py` | `runtail-acceptance` | **RED** — both faults |
| `probes/basic/basic_probe_dskmsg.py` | `dskmsg-acceptance` | **RED** — both faults |
| `probes/disk/disk_probe_fat_error_disposition.py` | `fat-error-acceptance` | 🟢 **GREEN — conforms already, and is not edited** |

### 2.1 The four RED ones are four COPIES of one report engine

They are not four independent bugs. `castail`/`cassave`/`runtail`/`dskmsg`
carry the same copy-pasted `main()` reporting block, differing only in the label
pad width (22 / 20 / 20 / 14) and in whether a PINNED block exists (only
`castail`). That is why the fix is an **extraction**, not four edits: a fifth
copy is otherwise one `cp` away, and this slice would be re-derived a sixth
time.

### 2.2 🟢 THE REMEDY ALREADY EXISTS IN THIS TREE, AND THE WALK FOUND IT

`disk_probe_fat_error_disposition.py` prints **nine** report rows across **five**
blocks including its exit-2 block, and every one of them is
`  <TAG4>  {key:14} {line:38} -> {value!r}<note>` — same column, same encoding,
on every exit path. D-FEVERB's and D-MOUNTROW's knives ran against that probe
and were caught by **neither** fault.

This is worth more than a design argument: the shape being proposed is not
speculative, it is **already load-bearing in the tree, under knives**. It also
gives the new gate a **positive control that requires no change** — a green row
whose greenness is not produced by this slice's own edit
([[apparatus-is-part-of-the-measurement]]).

### 2.3 What the walk found that the hand-list did not, in BOTH directions

* **The hand-list over-claimed.** `lnblank`, `diskbasic`, `lptverb` and
  `editverb` are named in the residual. **None of them prints a report row on an
  exit-2 path.** `editverb` prints exactly **one** report-row site in the whole
  file. Four of the eight guessed probes are simply not in the class.
* **The hand-list missed two.** `basic_probe_kwsweep.py` and
  `disk_probe_fat_error_disposition.py` print rows on an exit-2 path and were
  not on it. One of them turns out to be the green control (§2.2).

### 2.4 `kwsweep` — an out-of-contract case, recorded, not silently dropped

`basic_probe_kwsweep.py:485` prints `    {k:9} {n} chars` inside a block that
returns 2. It reaches the contract under a *loose* row definition and drops out
under §3's: neither that line nor `kwsweep`'s own scored rows
(`{state:5}  {key:9} {body}`) render their value with `repr()`, so **no line
`kwsweep` prints is a machine-parseable report row.**

⚠️ **This is a finding, not an exemption.** `kwsweep`'s exit-2 path prints a
table that is not its readings, so a runner holding a `kwsweep` baseline sees
**zero** rows under that knife and aborts. That abort is *correct* — the probe
genuinely measured nothing — and the landed runner rule ("enumerate the probe's
exit codes and parse all of them") already covers it. `kwsweep` is therefore
**left alone in this slice**, and the residual it carries — *a probe whose rows
are not machine-parseable at all* — is filed in `TODO.md` rather than fixed
here, because fixing it means re-running a 162-word emulator sweep to prove a
cosmetic change, and the fault it would prevent is one the runner rule already
prevents.

---

## 3. What a report ROW is — the definition the gate uses

A **report row** is a printed line a knife runner parses as
*(label → this reading's value)*. Mechanically, all three must hold:

1. a **width-padded label field** — `{lab:<22}`, `{key:14}`. A *string* pad;
   `{addr:04X}` pads a number and is prose, not a table;
2. at least one value in the tail rendered with **`repr()`** (`{v!r}`);
3. the line is printed by `print()` with the label field on the first argument.

**Condition 2 is the load-bearing one and it is not a convenience.** `repr()` is
what delimits a value that may itself contain spaces, `=`, or nothing at all —
it is precisely what lets a parser recover the value without knowing the
probe's layout. A row printing an undelimited body cannot be parsed by any
runner, uniform layout or not, so the contract cannot cover it and must say so
(§2.4) rather than pretend.

Under this definition: 29 of 175 probes print report rows; 5 print them on more
than one exit path.

---

## 4. THE DECISION: not "one row FORMAT" — one row GRAMMAR

The residual asks for *one row format on every exit path*. **Declined as
filed**, and the reason is in the code it would delete.

The exit-2 report deliberately prints, for every reading, **every side's value**
and the words `(not scored)`, because on that path a positive control failed and
**nothing was measured**. The exit-0 report prints an agreed value **once**
under an `ok` tag, because the sides agreed. Collapsing the first into the
second destroys the information the exit-2 report exists to carry; collapsing
the second into the first is not "one format" either, it is a different
question — see below, where it is answered YES.

The two things a runner is defeated by are **layout** and **value encoding**.
Neither is the same as "content". So the contract is:

> **Within one probe, every report row on every exit path must have the same
> LAYOUT and the same VALUE ENCODING. Only the TAG and the trailing NOTE may
> differ between paths.**

Concretely, three invariants:

* **I1 — fixed-width tag, constant label column.** The tag occupies a constant
  number of characters on every row, so the label field starts at the same
  column on every path. Today `castail` prints `{'ok ' if ok else 'DIFF'}` —
  **3 characters on an agreeing row and 4 on a diverging one** — so its label
  column moves *between two rows of the same run*, before any exit path is
  involved. That is the deepest version of fault 1 and the walk found it.
* **I2 — one value encoding.** A probe renders values as `side=value` pairs on
  every row, or as a bare `repr` on every row. Never both. This is the fault
  that does not abort.
* **I3 — a terminator on every exit path.** Every path that prints report rows
  ends with one `ROWS: <n> printed, <m> scored — <why>` line. A runner then
  detects truncation by a **positive** statement of the count, instead of by an
  `^`-anchored regex over a layout it had to guess. This is the invariant that
  makes the original abort impossible rather than merely unlikely: D-RUNTAIL
  recorded that the exit-2 path prints **no tally line at all**, and that
  absence is what the runner's "prefix?" heuristic was reaching for.

I2 forces a choice for the four RED probes, and the choice is **always print
every side**. The `ok` row loses its "print the agreed value once" affordance
and gains something better: it says *what both sides actually read*, instead of
asking the reader to trust that the single value shown was the value both gave.

---

## 5. The change

### 5.1 New: `probes/lib/probe_report.py`

One module, the single formatter, plus the parser a knife runner imports:

```python
row(tag, label, width, vals, note="")   -> f"{tag:<4} {label:<width}  " +
                                           "  ".join(f"{s}={v!r}" ...) + note
footer(printed, scored, why)            -> f"ROWS: {printed} printed, "
                                           f"{scored} scored — {why}"
parse(text)                             -> [Row(tag, label, vals, note), ...]
                                           raises ReportTruncated
```

`parse()` recovers values by positively matching `name=<python-repr>` pairs with
a regex that understands repr quoting — it never strips the note, never anchors
on a column, and never assumes an indent. It then **requires** the `ROWS:`
footer and **requires** the declared count to equal the number of rows parsed;
either failure raises `ReportTruncated`. That is the runner-side guard the
residual's fault defeated, moved into the tree where it is written once.

Exporting `parse()` is the concrete answer to *"so a runner cannot be caught by
the layout at all"*: a runner does
`sys.path.insert(0, "probes/lib"); import probe_report` and never sees a column.

### 5.2 Changed: the four probes

`basic_probe_castail.py`, `basic_probe_cassave.py`, `basic_probe_runtail.py`,
`basic_probe_dskmsg.py` — every report-row `print()` routed through
`probe_report.row()`, and `probe_report.footer()` printed on all three exit
paths (exit-2 controls-failed, single-side characterization, scored).

Tags become a closed, 4-wide set: `ok`, `DIFF`, `PIN`, `ROT`, `FAIL`, `....`,
`--` (single-side characterization). Notes are unchanged text.

### 5.3 NOT changed

`disk_probe_fat_error_disposition.py` — **its rows are not touched**, which is
the point: it conforms to I1 and I2 (§2.2) *without this slice's edit*, so it
remains a positive control for **the two measured faults**.

⚠️ **It does gain I3, and the honest version of §2.2 says so.** `fat_error`
prints no `ROWS:` terminator today, so under §4's contract it is RED on I3 and
"the green control needs no change at all" would have been a convenient
overclaim. It gets **one `footer()` line per report arm and nothing else** — no
row, no tag, no column and no encoding is edited. What it controls is exactly
what it controlled before: that a probe written independently of
`probe_report.row()` still satisfies the layout and encoding invariants, so a
green `rowshape-check` is not merely this slice grading its own homework.

`kwsweep` — §2.4.
The other 24 gated multi-shape probes — they print one shape *per exit path*;
a runner's baseline and its knifed run meet the same shapes, so the fault
cannot arise. Priced in §10.

### 5.4 New gate: `make rowshape-check` → `tools/check_report_shape.py`

Static, AST, no name lists — shaped after `tools/check_probe_preflight.py`:

* walks `probes/**/*.py`, prints the whole denominator of §2 every run;
* computes each report-row site's **effective label column**, resolving a
  constant-string tag: `{'PASS' if ok else 'FAIL'}` is 4 either way and is
  **fine**; `{'ok ' if ok else 'DIFF'}` is 3-or-4 and is **not**;
* an in-contract probe fails on any of I1/I2/I3;
* **0 in-contract probes ⇒ exit 3, "APPARATUS FAILURE"** — a gate whose answer
  is an error must not pass a dead subject
  ([[gate-whose-answer-is-an-error-passes-a-dead-subject]]).

### 5.5 New: `tests/test_probe_report.py`

`parse()` has a failure path, and a failure path nothing executes is exactly
this slice's subject. The test asserts a truncated report **raises** rather than
returning a short list, that a count mismatch raises, that the note never
contaminates a value, and that a value containing `=` and quotes round-trips.

---

## 6. Falsification — knives

Every knife runs **twice** and hashes nothing (no ROM is built; the subject is
`python3 tools/check_report_shape.py`, invoked directly, never `make`). Each
knife names both a predicted RED **set** and a predicted GREEN **set**; a knife
where nothing moves, greens included, is an apparatus result.

| # | cut | predicted RED | predicted GREEN (must not move) |
|---|---|---|---|
| **K-RS1** | `probe_report.row`: `{tag:<4}` → `{tag}` | ~~I1 fails on **4** probes~~ **REVISED before the run, see §6.1: `unit-test` RED** | `rowshape-check` **GREEN** — by design, not by luck |
| **K-RS2** | `castail` `....` site: restore the old inline f-string at indent 2 | I1+I2 fail on **castail only** (1) | the other 3 + `fat_error` PASS |
| **K-RS3** | `castail` scored site: restore bare-repr-when-agreeing | I2 fails on **castail only** (1) | the other 3 + `fat_error` PASS |
| **K-RS4** | delete `castail`'s exit-2 `footer()` call | I3 fails on **castail only** (1) | the other 3 + `fat_error` PASS |
| **K-RS7** | delete `fat_error`'s exit-2 `footer()` call | I3 fails on **fat_error only** (1) | the four `probe_report` users PASS — proves the gate reaches a probe that does NOT import the shared module |
| **K-RS5** | gut the checker's row detector (`site_shape` → `None`) | **exit 3**, APPARATUS FAILURE | *not* exit 0 — the dead-subject test |
| **K-RS6** | delete `probe_report.py`'s `ROWS_RE` count check in `parse()` | `tests/test_probe_report.py` FAILS | the other 58 test files PASS |

**K-RS2/3/4 are the ones that matter most**, because each reddens **exactly
one** probe. A gate that goes red on all five for a one-probe cut is not
measuring per-probe conformance, it is measuring that something moved
([[predicted-red-set-must-not-inherit-scope]]).

**K-RS5 is the delete-the-code-under-test falsification.** K-RS1 is its
byte-level twin: it deletes the *invariant* rather than the *detector*.

### 6.1 🔴 K-RS1's prediction was WRONG AS FILED, and writing the runner is what said so

K-RS1 was filed above as *"I1 fails on 4 probes"*. **It cannot.** The checker
models a `probe_report.row(...)` site's column as `TAG_W + 1` **by
construction** — it reads the constant, not the format string — so deleting the
pad *inside the shared formatter* changes what every migrated probe PRINTS while
the static gate goes on reporting ALL PASS.

That is not a bug to paper over; it is the honest division of labour, and it has
to be stated rather than discovered later by a runner:

* **`rowshape-check` proves each probe uses ONE grammar.** It cannot see inside
  the grammar.
* **`tests/test_probe_report.py` is the grammar's own oracle.**
  `test_row_is_one_grammar_whatever_the_tag` asserts the label lands in the same
  column for `ok`, `DIFF` and `....`, and is the ONLY thing in the tree that
  fails when the pad is removed.

So K-RS1's predicted RED is **`unit-test`**, and its predicted GREEN is
`rowshape-check` — a green that is a *result*, not an absence. The revision was
made while writing the runner and **before** it was run; recording it that way
matters, because a prediction quietly rewritten after the fact is
[[a-prediction-copied-into-the-result-column]].

⚠️ **Generalised: a gate that delegates to a shared module inherits a blind
spot exactly the width of that module, and the module needs its own oracle.**
Two gates, two subjects — neither alone covers the claim.

---

## 7. Predicted GREEN — exact values, fixed before the change

Predicted by **reading the line of Python that computes each count**
(`docs/spec-basic-cassearch.md` §7.5), never from narrative.

### 7.1 Unchanged, and required to be

Measured from clean at `fca8799` on 2026-08-07, immediately before this spec:

| | value |
|---|---|
| main low free | **3 B** |
| main page 1 free | **158 B** |
| sub page 0 free | **3843 B** |
| sub page 1 free | **1483 B** |
| `basic-reloc.rom` | `2acb25db3b0402cc…` |
| `sub.rom` | `b3761022363fc270…` |
| `disk.rom` | `2c630d3dfeec727b…` |
| `zerobas-main-eu.rom` | `fd0bfa213fcdf0e2…` |
| `preflight-check` | **181 / 86 / 95 / 95 / 0** |
| `deadcode` | main 1566 spans / 287 seeds → 0; sub 1517 / 102 → 0 (+1 allowlisted) |
| `latch-check` | 16/16 |
| page-1 closure | 585 routines + 43 data labels |

All ROM-side numbers must come back **identical**: this slice edits no assembly.
`preflight-check` counts `subprocess` spawn sites; the new files spawn nothing,
so 181/86/95/95/0 stands.

### 7.2 Changed by construction, predicted exactly

Four new files ship: `probes/lib/probe_report.py`, `tools/check_report_shape.py`,
`tests/test_probe_report.py`, `docs/spec-probe-rowshape.md`.

* **`unit-test`** — `tests/run.py:20` counts `glob("tests/test_*.py")`. One new
  `test_*.py` ⇒ **58 → 59**.
* **`audit-citations` files swept** — `audit_citations.sweep_files()` counts
  every file under the repo whose suffix is in
  `(.md .asm .inc .py .tcl .txt .bas .yml)` minus `SWEEP_SKIP`. All four new
  files qualify ⇒ **727 → 731**. `basic 107 files / 187 provenance-bearing` is
  scoped to `basic/` and is **unchanged**.
* **`injector-check` files scanned** — walks `.py` repo-wide minus `SKIP_DIRS`
  (which does **not** skip `scratchpad/`; this slice's scratch files live in
  `/private/tmp`, outside the repo). Three new `.py` ⇒ **332 → 335**. Exempt 4,
  RECORDs 3, offenders 0 — unchanged.
* **`rowshape-check`** (new) — `176 files walked · 0 unparseable · 82 padded-label ·
  29 report-row · 5 in contract · 5 conform · 0 violations`.
  🔴 **`82 padded-label` is a MISS, and the measured value is 78.** The four
  migrated probes leave that population entirely, because **every** width-padded
  print each of them had *was* a report row — none had a padded line that was
  merely prose. 82 − 4 = 78. The number was written from the *pre-change* walk
  without asking what the change does to it; the `29 report-row` figure beside it
  is unaffected for the same reason the padded one is not (a migrated row is
  still a row, it is just no longer an f-string). Recorded as a miss rather than
  quietly corrected — [[a-prediction-copied-into-the-result-column]].
  ⚠️ **176, not the 175 of §2** — `probes/lib/probe_report.py` lands *inside the
  walk's own subject directory*, so this gate's denominator counts it. The first
  version of this line said 175, from the scout's pre-change number; the gate
  itself corrected it. That is the same class of miss as
  [[a-count-is-predicted-by-reading-its-definition]], one level up: the
  definition was read correctly and the **input** was the stale thing.

  **Run against the UNCHANGED tree the gate reports `175 walked · 82 · 29 ·
  5 in contract · 0 conform · 5 VIOLATIONS, rc=1`** — measured before any probe
  was edited. A new gate that is green on the tree it was written for has not
  been shown to be able to fail.

### 7.3 The emulator gates — tallies must be IDENTICAL

This change alters no BASIC, no ROM and no reading. Every tally is computed from
`agree`/`dis` counters this slice does not touch, so:

`castail-acceptance` **31/31 + 1 pin** · `cassave-acceptance` **20/20** ·
`runtail-acceptance` **9/9** · `dskmsg-acceptance` **5/5** ·
`fat-error-acceptance` **8/8 FIND + 2/2 MOUNT + 5 directory checks**.

⚠️ **A tally that changes here is a REGRESSION, not a formatting difference.**

### 7.4 ⚠️ ZERO ROM BYTES — which emulator gates run, and why

No assembly is edited, so the ROM-side risk is nil and the four hashes are the
proof. **The emulator gates are still run, and not as a ritual**: the four
edited probes are the *instruments* of five acceptance gates, and a formatting
change that breaks a probe's own `--gate` path would be invisible to every
static check. The corpus proves the new format **runs and still scores**.

Gates run in full: the corpus in §8. Gates **skipped** and why: none — the
listed corpus is run sequentially from clean. What is **not** re-run is any
gate whose probe this slice does not touch *and* whose numbers are ROM-derived
(`subrom-*`, `graphics-*`, the trap batteries) — they cannot move without a ROM
byte moving, and the hashes cover that claim more tightly than a re-run would.

---

## 8. The corpus

Sequentially from clean, scored against §7:

`unit-test` · `audit-citations` · `preflight-check` · `injector-check` ·
`rowshape-check` (new) · `latch-check` (after `make repack-machine`) ·
`deadcode` · `lnblank-acceptance REPEAT=2` · `lnblank-say-acceptance` ·
`logicops-acceptance` · `float-acceptance` · `linemax-acceptance` · `dexp5-pin` ·
`editverb-acceptance` (61/61) · `lptverb-acceptance` (44/44) ·
`dskmsg-acceptance` (5/5) · `diskbasic-acceptance` (34/34) ·
`fat-error-acceptance` (8/8 + 2/2 + 5) · `runtail-acceptance` (9/9) ·
`castail-acceptance` (31/31 + 1 pin) · `cassave-acceptance` (20/20).

⚠️ `lnblank REPEAT` defaults to 1.

---

## 9. Cost, and what it buys

| item | measured |
|---|---|
| ROM bytes | **0** — no assembly edited |
| probes changed | **4** (one copy-pasted engine, extracted once) |
| probes in contract left unchanged | **1** (`fat_error`, the green control) |
| gated multi-shape probes NOT in contract | **25** — priced in §10 |
| new files | 4 |
| recorded tallies invalidated | **0** — tallies are footer counters, untouched |
| recorded sample ROWS invalidated | **0** — swept `docs/`, `TODO.md`, `basic/PROVENANCE.md`: **no** file records a literal row of these four probes |

That last line is the one that made this slice affordable, and it was measured,
not assumed: the residual warned that *"a format change that alters a tally line
breaks those records"*. It does not alter a tally line. The specs and
`PROVENANCE.md` record **labels** and **tallies**, never layout.

---

## 10. Priced and DECLINED in this slice: the other 25

25 gated probes print more than one row shape **within a single exit path** —
a `DIFF` row followed by indented `ref:`/`zb:` continuations, a summary line at
column 0 beside detail rows at column 2. A runner's baseline and its knifed run
both execute that same path, so both meet the same shapes; the D-CASOPEN fault
needs **two paths**, and these have one.

Bringing them to I1/I2 as well would be **25 bespoke edits across ~19,000 lines
of probe source** — only 6 of the 30 gated multi-shape probes share a data model
(`results[side][label]`), so 24 of them cannot use `probe_report.row()` without
first being restructured — plus a re-run of each one's emulator gate to prove
the probe still scores. **Declined**, with that number written down. If a runner
is ever caught by one of them, that is a measurement and it re-opens this with
evidence; until then it is a refactor bought with an argument.

---

## 11. As-built — 2026-08-07

**Shipped for ZERO ROM bytes.** Six files modified (`Makefile` + five probes),
four added. `git status` carried **no `.asm` and no `.inc`**, which is the tight
form of the claim; the hashes below are the loose one, and both hold.

### 11.1 The one number this slice is

`probe_report.parse()` run over the **actual** `make castail-acceptance` output,
before and after:

| | rows parsed | rows carrying a recoverable `zb` reading |
|---|---|---|
| **BEFORE** (`fca8799`) | 32 | **1** |
| **AFTER** | 32 | **32** |

Thirty-one of the thirty-two `ok` rows printed a **bare, unnamed** value — the
"the sides agreed, so print it once" affordance — so a value-parsing runner
recovered a reading from exactly **one** row, the pinned one. That is not a
cosmetic inconsistency; it is the report being unreadable to the guard the
runner-side rule tells you to write. All four migrated probes now parse whole:
`castail 32/32`, `cassave 20/20`, `runtail 9/9`, `dskmsg 5/5`.

And the guard fires on the old format, as it must:
`parse(castail-BEFORE.txt)` → `ReportTruncated: no `ROWS:` footer in 47 line(s)`.

### 11.2 Before / after, the same reading

```
BEFORE   ok  cas-run-hit            'ZQ9'   [CONTROL]              <- label at col 4
BEFORE   PIN  cas-load-plain:search  vg8020='Found:RT'  ...        <- label at col 5
BEFORE     ....  cas-run-hit  vg8020='ZQ9'  zb='ZQ9'  (not scored) <- label at col 8, exit 2

AFTER    ok   cas-run-hit             vg8020='ZQ9'  cf3300='ZQ9'  zb='ZQ9'   [CONTROL]
AFTER    PIN  cas-load-plain:search   vg8020='Found:RT'  cf3300='Found:RT'  zb='Found:RT'   [PINNED DIVERGENCE]
AFTER    ROWS: 32 printed, 31 scored — 31 agree, 0 diverge, 1 pinned
```

Three columns became one, one encoding replaced two, and the report now states
its own length.

### 11.3 Predicted vs measured

| | predicted | measured |
|---|---|---|
| main low / page 1 / sub p0 / sub p1 | 3 / 158 / 3843 / 1483 | ✅ **identical** |
| `basic-reloc.rom` | `2acb25db3b0402cc` | ✅ |
| `sub.rom` | `b3761022363fc270` | ✅ |
| `disk.rom` | `2c630d3dfeec727b` | ✅ |
| `zerobas-main-eu.rom` | `fd0bfa213fcdf0e2` | ✅ |
| `unit-test` | 58 → **59** | ✅ 59 |
| `audit-citations` swept | 727 → **731** | ✅ 731 (`basic` 107/187 unchanged) |
| `injector-check` | 332 → **335** | ✅ 335 |
| `preflight-check` | 181/86/95/95/0 | ✅ unchanged |
| `deadcode` | 1566/287→0, 1517/102→0 (+1) | ✅ |
| `latch-check` | 16/16 | ✅ |
| `rowshape-check` walked | **176** | ✅ 176 |
| `rowshape-check` report-row / contract / conform / violations | 29 / 5 / 5 / 0 | ✅ |
| `rowshape-check` padded-label | ~~82~~ | 🔴 **78** — miss, §7.2 |
| `castail-acceptance` | 31/31 + 1 pin | ✅ |
| `cassave-acceptance` | 20/20 | ✅ |
| `runtail-acceptance` | 9/9 | ✅ |
| `dskmsg-acceptance` | 5/5 | ✅ |
| `fat-error-acceptance` | 8/8 + 2/2 + 5 | ✅ |
| `editverb` / `lptverb` / `diskbasic` | 61/61 · 44/44 · 34/34 | ✅ |

Corpus (§8): **21/21 targets rc=0**, sequentially from clean.
One prediction missed, and it is written up rather than corrected in place.

### 11.4 Knives — 7 × 2 rounds, 14/14 EXACT

Subject: the tool invoked directly, never `make`. Restore in a `finally`,
verified by a **source hash** returning to baseline (no ROM is built, so the
ROM-hash guard's *reason* — "did the cut reach the artifact?" — is served by
hashing the eight touched sources instead; every cut was asserted to move it).

| # | measured, both rounds |
|---|---|
| K-RS1 | `rowshape-check` rc 0 (green **by design**, §6.1), `unit-test` rc 1 |
| K-RS2 | `rowshape-check` rc 1 — **castail only**; other 4 HELD |
| K-RS3 | `rowshape-check` rc 1 — **castail only**; other 4 HELD |
| K-RS4 | `rowshape-check` rc 1 — **castail only**; other 4 HELD |
| K-RS5 | `rowshape-check` rc **3 APPARATUS FAILURE** — not rc 0 |
| K-RS6 | `unit-test` rc 1; `rowshape-check` rc 0, all 5 HELD |
| K-RS7 | `rowshape-check` rc 1 — **fat_error only**; the four `probe_report` users HELD |

K-RS2/3/4/7 each redden **exactly one** probe, so the gate is measuring per-probe
conformance and not merely "something moved". K-RS7 matters most of those four:
`fat_error` does **not** import `probe_report.row()`, so it proves the gate
reaches a probe outside its own module.

### 11.5 Two findings this slice paid for

1. 🔴 **THE GATE'S FIRST CUT WENT BLIND BY HAVING ITS SUBJECT FIXED.** The
   detector recognised only inline f-strings, so migrating `castail` to the
   shared formatter dropped it **out of the contract** — 5 → 4 — and a fully
   migrated tree would have reported `0 in contract`. It was caught by watching
   the denominator move, not by any assertion. `site_of()` now recognises
   `probe_report.row(...)` explicitly, and the APPARATUS floor exists for the
   version of this that is not caught. [[readout-blind-to-its-own-subject]]
2. 🔴 **A GATE THAT DELEGATES TO A SHARED MODULE INHERITS A BLIND SPOT EXACTLY
   THE WIDTH OF THAT MODULE** — §6.1. Two gates, two subjects.

A third, smaller: `exits()` first matched only *constant* returns, so
`fat_error`'s `return 0 if ok else 1` exempted its success path from I3 — a rule
scoped by how someone spelled a return statement. Widened to any `Return`.

### 11.6 What was NOT done

`kwsweep` (§2.4) and the other 25 gated multi-shape probes (§10), both priced,
both filed in `TODO.md` as open with their numbers.
