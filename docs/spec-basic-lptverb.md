<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-LPTVERB — `LPRINT` / `LPOS` / `LFILES`: the rest of the printer surface

Measurement: [`docs/lptverb-msx1-characterization.md`](lptverb-msx1-characterization.md).
Predecessors: [`spec-basic-editverb.md`](spec-basic-editverb.md) (`LLIST`, and
this slice's whole apparatus), [`spec-basic-kwgap4.md`](spec-basic-kwgap4.md)
(the token half), [`spec-basic-listrange.md`](spec-basic-listrange.md).

---

## 0. The question

`TODO.md`'s residual, as narrowed while scouting this slice:

> `LPRINT` / `LPOS` / `LFILES` — the rest of the printer surface. All three lack
> a `kwtable.inc` entry, so they are `Syntax error` on zerobas.

* **Q1** — is the refutation D-EDITVERB filed for these three actually good for
  all three? (**No — for two.** §1.1)
* **Q2** — what do the references do? (**Measured, 38 rows.** The
  characterization; summarised in §2.)
* **Q3** — do they fit? (§1.2 and §4.1. **This is the open one**, and unlike
  D-EDITVERB the honest prediction is that not all three do.)

---

## 1. The denominator

### 1.1 🔴 Three words, TWO reasons, and the refutation covers only two words

D-EDITVERB refuted *"printer-bound with the known unplugged-`LSTOUT` hang
hazard"* and its residual said that covers the remaining three. It does not cover
`LFILES`: [`probes/basic/basic_probe_kwsweep.py`](../probes/basic/basic_probe_kwsweep.py)
carries `lfiles` among the **Disk-BASIC** words with **two** reasons,
`NEEDS-DISK` *and* printer-bound, and only the second fell. The VG-8020 has no
disk ROM.

| word | kind | reference sides | in-tree shape |
|---|---|---|---|
| `LPRINT` | statement | vg8020 + cf3300 | re-point an existing sink |
| `LPOS` | function | vg8020 + cf3300 | **new hot-path state** |
| `LFILES` | statement (Disk BASIC) | **cf3300 only** | **surgery on `do_files`** |

Three words, three different costs. §3 prices them and §4.1 predicts the
consequence.

### 1.2 The wall, measured from clean at `a89e43f`

| region | free |
|---|---|
| main page-0 low | **23 B** |
| main page 1 | **94 B** |
| sub page 0 | 3869 B |
| sub page 1 | 1824 B |

🔴 **CORRECTED 2026-08-07 (D-SUBWALL).** At `a89e43f` the sub walls are
**3869 / 1821**. The `1824` was copied from D-EDITVERB, not measured here, despite
this section's heading — and this slice then *moved* sub page 0 to **3852** and
recorded it as unchanged (§4.2 / §6.1). See
[`spec-subwall-readout.md`](spec-subwall-readout.md) §3.3. Both figures are left as
written, because they are the evidence for that finding.

Page 1 binds, and it binds *hard*: D-EDITVERB spent 262 B of the 356 B it
inherited. There is no sub-ROM escape for any of this — `pchar`, `repl`,
`ex_print` and `do_files` are all main-resident, and a page-1 tenant cannot reach
main page 1.

### 1.3 Files this slice ADDS, against the sweep filters

* `docs/spec-basic-lptverb.md` — `docs/` is in `audit_citations.py`'s
  `SWEEP_DIRS`, `.md` is in `SWEEP_EXTS`. **+1 swept file: 704 → 705.**
* `docs/lptverb-msx1-characterization.md` and
  `probes/basic/basic_probe_lptverb.py` already landed with the measurement
  (704).
* ⚠️ **Seed prediction.** `check_dead_code.py`'s `external_names` reads `sub/`
  and `tools/` **comments**, and this slice writes no `sub/` prose, so main seeds
  should stay at **286** and sub at **102**. That is a prediction this project
  has now got wrong once ([`spec-basic-editverb.md`](spec-basic-editverb.md)
  §6.7.1), so it is stated as a number to be checked rather than assumed.

---

## 2. What the measurement settled

Full rules in the characterization. The four that drive the design:

* **R-LP9** — `LPRINT` does **not** end the line or the program. Unlike `LLIST`,
  the statement after it runs. So the sink must be per-statement, which
  `exec_stmt`'s existing `xor a / ld (PRDEST),a` already gives for free.
* **R-LP16** — 🎯 **a partial printer line is FLUSHED on the return to command
  level.** Within a line the head stays put (`LPOS` reads 3 mid-line); by the
  time control reaches the prompt a CR/LF has been sent. This is the rule that
  makes `LPRINT` cost more than `LLIST` did.
* **R-LS1..R-LS7** — `LPOS` is a printer **column**, per byte actually sent,
  zeroed by CR/LF, argument a true dummy with no domain check, parentheses
  required.
* **R-LF1** — 🎯 `LFILES` is **not** `FILES` with the sink moved. The screen form
  packs three 12-char fields per row; the printer form is **one entry per line**.

---

## 3. Design

⚠️ **Every byte figure in this section is an ESTIMATE from instruction counting,
not a measurement.** A size from arithmetic is not a measurement
([[linemax-slice]]); §6 replaces all of them with `build/basic-reloc.sym`.

### 3.1 `LPRINT` — the `LLIST` pattern, plus the flush

`pchar`'s sink is **two** cells and `ex_print`'s own `exp_dev_lpt` arm already
uses them, so the head is small:

```
ex_lprint:  inc hl ; ld a,1 ; ld (PRDEV),a ; ld (PRDEST),a
            call skip_spaces ; cp USING_TOKEN ; jp z,ex_print_using
            jp exp_loop
```

* the `USING` check is kept, because **R-LP11** says `LPRINT USING` formats like
  `PRINT USING`;
* the `'#'` check is **dropped**, because **R-LP14** says `LPRINT#1` is a
  `Syntax error` — and falling into `exp_loop` with `'#'` in A should produce
  exactly that from the expression parser. ⚠️ *Should*: that is an assumption
  about `exp_loop`, and `lpr-hash`/`scr-lprhash` are the rows that check it.
* no sink restore is needed, and that was **verified rather than assumed**:
  `exec_stmt` ([`basic/interp.asm`](../basic/interp.asm)) resets `PRDEST` at the
  top of every statement. D-EDITVERB credited `repl` alone for the same property,
  which is only the prompt-level half.

**≈23 B** (20 B body + a 3 B `stmt_table` row).

### 3.2 The printer column, and why both other words need it

`LPTPOS`, one byte, maintained **in the sink** and not in the statement — because
**R-LS6** says `TAB`/`SPC` padding moves it, and that padding is emitted through
`pchar`, not by `ex_lprint`:

* `pch_lpt` increments it per byte sent, and zeroes it on CR;
* `repl` flushes: if `LPTPOS` is non-zero, send CR/LF and zero it (**R-LP16**).

⚠️ **`LPRINT` alone cannot skip this.** `lpr-trsemi` expects `A\r\n` in the log
for `LPRINT"A";`, and that trailing CR/LF *is* the flush. A one-bit "printer line
dirty" flag would serve `LPRINT`; a full column is needed the moment `LPOS`
lands, and both are wanted, so the column serves both.

⚠️ **A lone LF is UNMEASURED.** Zeroing on CR alone and not counting LF both
satisfy R-LS3 (after CR/LF the count is 0 either way); they differ only for a
bare LF, which no row asks. Choice recorded in §6, not claimed as a rule.

**≈30 B** (≈15 B in `pch_lpt`, ≈15 B in `repl`, 1 B of RAM).

### 3.3 `LPOS` — `ev_ff_pos` with a different source

[`basic/expr.asm`](../basic/expr.asm)'s `ev_ff_pos` is an exact template, and its
comment already documents the *same* measured facts this slice found for `LPOS`
(dummy argument, no domain check, parens required). So `LPOS` joins
`ev_ff_argtab`, gets a `cp`/`jr z` dispatch row, and its body is:

```
ev_ff_lpos: ld a,(LPTPOS) ; ld e,a ; ld d,0 ; ret
```

**≈20 B** (7 B body + 4 B dispatch + 1 B table + 8 B `kwtable.inc` entry).

⚠️ **`kwtable.inc` ordering is load-bearing here**, and `LPOS` has more
neighbours than usual: `LPRINT`, `LOCATE`, `LOF`, `LSET`, `LINE`, `LLIST`, and
`POS` itself. `match_kw` compares the FULL keyword so there is no prefix hazard
by construction, but the two new words go in the same file as `POS`, whose own
comment already flags the question.

### 3.4 🔴 `LFILES` — NOT a sink re-point, and this is the expensive one

`do_files`'s emit path ([`basic/files.asm`](../basic/files.asm)) blocks a sink
re-point twice over:

* `df_emit` and `de_sep` call **`CHPUT` directly**, not `pchar`. With
  `PRDEST`/`PRDEV` set, the bytes would still go to the screen.
* the separator/wrap decision reads **`CSRX` and `LINLEN`** — the *screen*
  cursor and the *screen* width. Printing to a printer moves neither, so the
  column arithmetic is not merely wrong for the printer, it is reading an
  unrelated device. `df_end`'s "terminate the final line" test reads `CSRX` too.

**R-LF1 makes the printer path simpler, not harder** — one entry per line means
no separator and no wrap arithmetic at all. So the shape is a mode flag
(`FILES_LPT`) that selects, per entry, `field + CRLF` instead of
`separator-or-wrap + field`, with the `CHPUT` calls routed through `pchar` (which
for `PRDEST=0` calls `CHPUT` anyway, so the screen path is behaviour-preserving
and the same 3 bytes per call site).

**≈42 B** (9 B `kwtable.inc` + 3 B `stmt_table` + ≈12 B head + ≈18 B of mode
branches), plus 1 bit of RAM.

### 3.5 The total, and the prediction it forces

≈23 + 30 + 20 + 42 = **≈115 B against a 94 B wall.** LPRINT + the column + LPOS
is ≈73 B and fits; adding LFILES does not.

⇒ **§4.1 predicts LFILES will not fit without a carve**, and the slice is
sequenced so that is discovered against a measured number rather than an
estimate: land `LPRINT` + `LPOS` first, measure, then price `LFILES` against
what is actually left. If it does not fit, the disposition is a carve or a
re-file **with the measured number**, not a silent narrowing.

---

## 4. Predicted GREEN, at exact values — fixed BEFORE the change

1. `LPRINT` + `LPTPOS` + `LPOS` land; page 1 **94 B → between 15 and 40 B**.
2. Low region **23 B unchanged**; sub page 0 **3869** and sub page 1 **1824**
   unchanged (nothing lands sub-side).
3. 🔴 **`LFILES` does NOT fit in what remains**, and the measured shortfall is
   reported rather than absorbed by narrowing the item.
4. `audit-citations`: **705** files swept, self-tests 10/10 11/11 12/12 14/14,
   4 advisory all acknowledged.
5. `deadcode`: main **286** seeds → 0, sub **102** → 0 (+1 allowlisted) — no
   movement, because this slice writes no `sub/` or `tools/` prose.
6. `injector-check`: **327** files, 4 exempt, 3 RECORDs, 0 offenders.
7. `test_stmt_dispatch.py`: **78 → 80** entries (LPRINT, LFILES if it lands;
   79 if it does not), all dispatching.
8. `lptverb-acceptance` green on the sides each battery can measure: the `lpr-`,
   `lps-` and `scr-` batteries on three sides; `lfl-` on two, and **red until
   LFILES lands** — a gate that is red for a named, filed reason, not green by
   omission.
9. Every existing corpus gate at its recorded value. ⚠️ **`float-acceptance` and
   `logicops-acceptance` are named explicitly** because §3.3 touches `ev_f`'s
   `$FF` dispatch chain, which is the common path of every numeric literal — a
   tokeniser regression once sat unread for two slices because
   `logicops-acceptance` was in no spec's list (D-EXPKW).
10. All four ROM hashes change **except `build/disk.rom`**, which
    [`spec-basic-editverb.md`](spec-basic-editverb.md) §6.7.2 established cannot
    move for a `basic/`-only slice.

## 5. Predicted RED, with knives

Each knife names a predicted RED set **and** predicted GREEN survivors; a knife
that reddens everything has localised nothing. Run twice.

| # | cut | predicted RED | predicted GREEN |
|---|---|---|---|
| **K1** | delete the `LPRINT` `stmt_table` row | every `lpr-` subject row → empty log | `lpr-ctl` (the sink still works), every `lps-` row |
| **K2** | `ex_lprint` sets `PRDEST` but not `PRDEV` | every `lpr-` subject row → empty log **and** a file-sink write | `lpr-ctl`, `lps-init` — the knife that proves the sink is TWO cells |
| **K3** | drop the `repl` flush | `lpr-trsemi` (log loses its trailing CR/LF) | `lpr-str`, `lpr-all`, and every `lps-` row read on ONE line — the knife that isolates R-LP16 from `;` |
| **K4** | `pch_lpt` counts the byte but never zeroes on CR | `lps-crlf` (reads 3, not 0) | `lps-after` (still 3), `lps-init` (still 0) |
| **K5** | increment `LPTPOS` in `ex_lprint` instead of `pch_lpt` | `lps-tab` (TAB padding uncounted → reads 0, not 10) | `lps-after` — the pair that proves the counter belongs in the SINK |
| **K6** | `ev_ff_lpos` reads `CSRX` (i.e. copy `ev_ff_pos` and forget to change the source) | `lps-after`, `lps-tab`, `lps-multi` | `lps-init` — ⚠️ **this survivor prediction is WRONG, see §6.7.1**: `CSRX` is 1-BASED and `ev_ff_lpos` carries no compensating `dec a`, so the knifed body reads 1 where a correct one reads 0, and `lps-init` moves too |
| **K7** | add `LPOS` to the domain-check chain | `lps-argneg` (`LPOS(-1)` raises) | `lps-arg1`, `lps-argbig` |
| **K8** | `LFILES` (if it lands) re-points the sink without the mode flag | `lfl-all` (three-per-row layout on the printer) | `lfl-ctlf`, `lfl-ctlp` — the knife for R-LF1 |

⚠️ The restore point is a **scratchpad snapshot** taken after the change and
before the first cut, never `git checkout --`
([[knife-cleanup-restores-from-head]]). The runner reads the **probe's** exit
code, not `make`'s — `make` exits 2 for any failed recipe and would flatten a
tree fault into an instrument fault ([[injjudge-slice]]).

🔴 **K6 is the knife this slice exists to have.** `LPOS` is being written by
copying `ev_ff_pos`, whose body reads `CSRX`. The single most likely defect is
that the copy keeps its source, and on a fresh machine **both columns read 0** —
so `lps-init` cannot see it, and neither can any row taken before the first
`LPRINT`. `lps-after`/`lps-tab`/`lps-multi` are the rows that can.

---

## 6. As-built

### 6.1 Predictions, scored

| § | predicted | measured |
|---|---|---|
| 4.1 | page 1 **94 → 15..40 B** | **94 → 7 B** ⚠️ — over the estimate, and §6.3 is why |
| 4.2 | low **23 B unchanged**; sub p0 3869 / p1 1824 unchanged | 🔴 **low 23 → 3 B** — the prediction was WRONG (§6.3); sub sides unchanged ✅ |
| — | 🔴 **CORRECTED 2026-08-07 (D-SUBWALL): "sub sides unchanged" is FALSE.** Sub page 0 went **3869 → 3852**, and the −17 is the `kwtable` row three lines below in this very table: `LPRINT` (9 B) + `LPOS` (8 B), in `basic/kwtable.inc`, whose sole include site is `sub/sub.asm` — so they land on sub **page 0**. The 17 B were measured here and connected to nothing; "unchanged" was the prediction copied into the result column. [`spec-subwall-readout.md`](spec-subwall-readout.md) §3.3 | |
| 4.3 | **`LFILES` does not fit** | ✅ — not implemented; the shortfall is measured, not assumed (§6.4) |
| 4.5 | `deadcode` main **286** → 0, sub **102** → 0 | **286 / 102**, 0 dead both ✅ — no movement, as predicted |
| 4.7 | `test_stmt_dispatch` **79** entries if LFILES does not land | **79 entries, 79 dispatch OK** ✅ |
| 4.8 | `lptverb-acceptance` green on the sides each battery can measure | **31/31 rows agree across all three sides** ✅ (`lpr-` 16, `lps-` 10, `scr-` 5) |
| — | `kwtable` pin bump | **1041 → 1058 B**, and **+17 is exactly** the 9 B `LPRINT` + 8 B `LPOS` entries — the delta itself says the table gained nothing else ✅ |
| — | the `lfl-` exclusion is PRINTED, not silent | ✅ `NOT GATED: lfl- (LFILES) — NOT IMPLEMENTED this slice … Re-run with ONLY=lfl-` on every run |

### 6.2 🔴 Three defects, and the CONTROL row found the worst one

The implementation was wrong in three places on its first build. All three were
found by the probe, and two of them by rows that are not about their subject.

**1. `LPTPOS` was never cold-started, and `lpr-ctl` caught it.** The cell is plain
RAM, so at power-on it holds garbage; `repl`'s R-LP16 flush fires whenever it is
non-zero, so the machine emitted a **spurious CR/LF to the printer on the very
first prompt**. Every printer log read `\r\n` + the expected bytes — including
`lpr-ctl`, which drives the sink through `OPEN"LPT:"` and executes **none of this
slice's code**. A control that exists to make other rows attributable was the row
that localised a defect in the new code. Fixed in `init_filechan`.

**2. `print_comma_zone` counted the zone from the SCREEN cursor.** It read `CSRX`
unconditionally, and printing to a printer moves neither `CSRX` nor `LINLEN`. So
`LPRINT"A","B"` padded to **14** spaces where both references pad to **13** — the
screen cursor sat at column 0 while the printer head was at 1. R-LP5 says the
zones are `PRINT`'s, and that means `PRINT`'s arithmetic *over the active sink's
column*. Fixed with a sink test; ⚠️ the width comparison still uses `LINLEN`,
which for the printer is a **choice, not a measured rule** — the printer's own
margin is unmeasured (§7 of the characterization) and no row in this battery can
see the difference.

**3. 🔴 The spec's own flagged assumption was false.** §3.1 dropped the `'#'` test
on the reasoning that falling into the item loop with `'#'` in A "should produce
exactly that [Syntax error] from the expression parser", and marked it *"Should:
that is an assumption"*. It is not what happens: `LPRINT#1,"A"` printed a run of
several **hundred** ` 0` values to the printer. The parser read `'#'` as something
evaluable and looped. `lpr-hash` alone could not have said so — an empty log is
equally consistent with a silent accept, and this log was not empty — so
`scr-lprhash`, the screen partner, is what named the missing message. An explicit
`cp '#' / jp z,exp_pos_syn` now costs 5 B.

⇒ the pattern worth keeping: **an assumption written down as an assumption got
checked.** Had §3.1 asserted it instead, the row would have been written to match
the implementation rather than the reference.

### 6.3 🔴 The low-region prediction was wrong, and the walls are COUPLED

§4.2 predicted the low region unchanged at 23 B. It is **3 B**, because the R-LP16
flush would not fit in page 1 at all: inline in `repl` the block cost ~20 B and the
image **overran the `$8000` ceiling by ~9 B**, which the assembler reported as
`BASIC_IMAGE_OVERRAN_8000_CEILING__TRIM_IT_OR_EVICT_TO_SUBROM`.

The body moved to `lpt_flush` in [`basic/str-engine.asm`](../basic/str-engine.asm)
— the low region — with `repl` reaching it by a 3 B in-slot call. That is the
mechanism [`basic/main.asm`](../basic/main.asm) already documents: page 1 and the
low region are **co-mapped slot-0 pages**, so a pressure-placed leaf moves between
them freely and the two walls are coupled. `print_strval`, three lines above the
new routine, is there for exactly the same reason and says so.

⇒ **the prediction treated two coupled walls as independent.** "Nothing lands
low-side" was true of the *design* and false of the *build*, and the honest form of
§4.1/§4.2 is a single budget across both regions: **94 + 23 = 117 B available, 107
B spent, 10 B left in total.**

### 6.4 `LFILES` — not implemented, with the number

Not a narrowing of the item: the measured shortfall is **≈42 B needed against 10 B
of combined headroom**, and `LFILES` is the one of the three that needs `do_files`
surgery rather than a sink re-point (§3.4 — `df_emit` calls `CHPUT` directly and
its wrap reads `CSRX`/`LINLEN`).

What landed anyway, so the next slice starts from a measured position:

* `LFILES_TOKEN equ $BB` in `basic/sysvars.inc` — oracle-locked from D-LNREF's
  crunch walk, recorded now so it is not re-derived;
* **all seven `lfl-` rows**, measured on the CF-3300 (R-LF1..R-LF5), including
  R-LF1 — the rule that a sink re-point alone would violate;
* the exclusion **printed by the gate**, not inferred: `NOT GATED: lfl- (LFILES)`
  with its reason on every run, and `ONLY=lfl-` to pick it up.

⚠️ `test_stmt_dispatch.py` is what holds the line: `$BB` must stay absent from
`stmt_table`, and that file now says so in a comment.

### 6.5 The `lnrx-lprint` trip-wire fired, on purpose

`basic_probe_lnblank.py`'s `lnrx-lprint` existed to go off if "a fifth entry crept
in" beside D-KWGAP4's four editor verbs. A fifth entry was added deliberately, so
`20 LPRINT 10` went from `L<91> <0F><0A>` — the same stray-`L`-plus-real-keyword
shape as the old `LLIST` mangle — to the reference's own `<9D> <0F><0A>`. It
**agrees** now, so it left `INFORMATIONAL` for the ordinary gating set, together
with `lnrx-lpos`; the same graduation D-KWGAP4 gave `lna-renum3`/`lna-auto2`.

`lnrx-wait` stays as the surviving control of that shape, and `lnrx-lfiles`
**stays informational and diverging** — which makes it the standing trip-wire for
"someone added `LFILES` without the rest of the work".

### 6.6 ⚠️ Both walls are now at single digits

Page 1 **7 B**, low **3 B**. Anything further in main needs a carve first, and
[`docs/rom-region-structure-review.md`](rom-region-structure-review.md) is the
scout. This is recorded as the slice's most consequential side effect: the next
slice to touch main BASIC has 10 B of combined headroom and should assume it must
carve before it can add.

### 6.7 Knives — 7 run, each TWICE, both rounds byte-identical

| # | verdict |
|---|---|
| K1 | **CUT** — repointing the dispatch token kills every `LPRINT` row (`<nothing printed>`, and `lps-after` becomes `Syntax error` because it uses `LPRINT`); `lpr-ctl`/`lps-init`/`lps-arg1` survive |
| K2 | **CUT** — `PRDEST` without `PRDEV` empties the log while `lpr-ctl` and `lps-init` hold. The sink really is two cells |
| K3 | **CUT** — neutering the flush leaves `lpr-trsemi` reading `A` with **no trailing CR/LF**, and `lpr-str`/`lps-after`/`lps-tab` untouched. R-LP16 isolated from `;` |
| K4 | **CUT** — never zeroing on CR makes `lps-crlf` read **4** instead of 0, with `lps-after` still 3 |
| K5 | **CUT** (re-aimed, §6.7.2) — uncounted padding makes `lps-tab` read **0** instead of 10, `lps-after` still 3 |
| K6 | **MISS, and the miss is a correction to §5** — §6.7.1 |
| K7 | **MISS, and the cut is unsound** — §6.7.3 |
| K8 | **NOT RUN** — it cuts `LFILES`'s mode flag and `LFILES` is not implemented (§6.4). Recorded, not silently skipped |

Both rounds were byte-identical, which — openMSX being deterministic — is not evidence
of soundness. That is what the named GREEN survivors are for.

#### 6.7.1 🔴 K6 reddens its own control, because `CSRX` is 1-BASED

K6 is the knife this slice was written to have: `ev_ff_lpos` is a copy of
`ev_ff_pos`, and the likely defect is that the copy keeps reading `CSRX`. §5
predicted `lps-init` would be the survivor, reasoning that *"a fresh screen column
and a fresh printer column are BOTH 0"*.

They are not. `CSRX` is **1-based** — `ev_ff_pos` compensates with a `dec a`, and
`ev_ff_lpos` deliberately omits it because `LPTPOS` is 0-based. So the knifed body
reads **1** at line start where the correct one reads 0. Measured: all three
predicted RED rows moved to `1`, **and `lps-init` moved to `1` as well**.

⇒ two things, and the second is the useful one:

* as a **localising** knife K6 fails — it reddens the whole battery including its
  named survivor, and a knife that reddens everything has localised nothing;
* but the defect it targets is **more** detectable than the spec claimed, not less.
  Every `LPOS` row catches a `CSRX` copy. The spec's worry that `lps-init` would be
  blind to it was wrong, and the reason it was wrong is a one-line fact about the
  BIOS variable's base that the prediction did not check.

Recorded as a MISS with the reason rather than re-aimed into something that would
pass — the same disposition as D-EDITVERB's K3
([[rule-gated-structurally-has-no-knife]]).

#### 6.7.2 K5 was re-aimed, and it is recorded as re-aimed

§5's K5 was *"increment `LPTPOS` in `ex_lprint` instead of `pch_lpt`"*, which is not
a small edit. The **claim** under test is "padding emitted through the sink must be
counted", so the cut stops counting SPACES: `TAB` padding is spaces, so `lps-tab`
loses its 10 while `lps-after` (`"ABC"`, no spaces) keeps its 3. Same predicted
pair, same claim, a 4-byte edit.

#### 6.7.3 🔴 K7 is an UNSOUND cut, and its own survivors said so

K7 routes `LPOS` through an existing byte-domain arm to test R-LS4's *"no domain
check"*. Its RED rows moved as intended — `lps-argneg` and `lps-argbig` both became
`Illegal function call`. But the GREEN survivors came back as **`lps-arg1` = 195**
and **`lps-init` = 243**: garbage, not columns.

So the cut does not merely add a range test, it changes how the argument is
**consumed**, and the knifed build is broken beyond the intended cut. A knife whose
survivors return nonsense is not measuring the claim it names.

⇒ **R-LS4 is left UNKNIFED in this slice, and that is stated rather than papered
over.** The rule itself is measured on both references (`LPOS(-1)`/`LPOS(255)`
answer normally, three sides, `lps-argneg`/`lps-argbig` green in the gate); what is
missing is a *falsification* that isolates it. Filed.

✅ **CLOSED 2026-08-07 by D-DSKMSG** ([`spec-basic-dskmsg.md`](spec-basic-dskmsg.md)
§2). The fault was the **cut site**: the `ev_ff_ck*` chain runs *before*
`flt_int_result` and its arms re-coerce FAC. Cutting instead at `ev_ff_lpos`,
where the argument is already consumed and sits in DE, gives two sound knives —
K-LS4a (argument as a selector with domain {0}) and K-LS4b (byte domain only) —
which CUT at exactly their predicted sets while the survivors return **3, 10 and
14**, real columns rather than 195 and 243.

⚠️ **And R-LS4's own "out-of-byte" clause had no row**: `255` is IN byte range.
`lps-argover` (`LPOS(300)`) was added and measured `0` on both references before
either knife ran.

#### 6.7.4 ⚠️ Two apparatus faults in the knife runner itself

* 🔴 **The first runner compared hand-written baselines against `repr()` output**,
  which doubles every backslash — so `X\r\n` was compared with `X\\r\\n`, no
  `lpr-` row could ever "hold", and K1 and K2 scored MISS for a defect in the
  *runner*. Fixed by capturing the baseline through the identical parse path, which
  also makes it an in-run control: an empty baseline row now refuses the whole run
  rather than scoring every cut a CUT.
* ⚠️ **And an incremental rebuild moved the wall by 4 B.** After the knives, an
  in-place `make basic-reloc` reported page 1 at **3 B** with a ROM hash that
  matched no clean build. `rm -rf build` restored **7 B** and the corpus run's own
  hash `fdb88aaa…`. Every wall figure in §6.1/§6.3 is from clean
  ([[measure-the-wall-from-clean]]); the knife runs' in-place rebuilds are exactly
  the condition that rule exists for.
