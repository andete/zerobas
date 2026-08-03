# D-DOTGAPS — the three `.` questions D-DOTLINE answered by reasoning

**Scope.** Close the three gaps D-DOTLINE explicitly recorded as CHOICES rather
than readings ([`spec-basic-dotline.md`](spec-basic-dotline.md) §5.1/§10.4,
[`dotline-msx1-characterization.md`](dotline-msx1-characterization.md) §5.1),
and leave each one **gated** rather than argued.

Measurement: [`dotgaps-msx1-characterization.md`](dotgaps-msx1-characterization.md)
— 23 rows, `--repeat 2`, vg8020 + cf3300 + zb, taken before this spec was
written and before any `basic/`/`sub/` edit.

| gap | the answer | what it costs |
|---|---|---|
| **1** ASCII LOAD/MERGE | **writes `.`, per stored line, last line in FILE order** — zerobas already agrees | **no code**; 6 rows + 2 disk rows to gate it |
| **2** the one-reference ASCII SAVE | **confirmed on a second reference and a second device** — the 12 B design point stands | **no code**; 4 + 3 rows, and a per-row capability lock so a cf3300-only reading can gate |
| **3** a refused store | **the reference WRITES it**; zerobas does not — a divergence | **0 B**: the write instruction MOVES |

---

## 1. Why now

All three were named in D-DOTLINE's own sign-off text, and one of them
(`sub/lineedit.asm:155`) carries the word UNMEASURED in the shipped source. Gap 3
turned out to be a real divergence, and gaps 1 and 2 turned out to be correct —
which is exactly the distribution that makes "we reasoned about it" an unsafe
place to leave three items: **the reasoning was 2-for-3, and nothing in the tree
could tell which one was the miss.**

## 2. The rules

Restated from the characterization §5, which supersedes
`dotline-msx1-characterization.md` §5 R-DOT3/R-DOT4:

* **R-DOT3a** (widened, measured) — storing a line records the line number
  **TYPED**, per line, whatever drove the store: the line editor, an ASCII
  `LOAD`, or an ASCII `MERGE`, over cassette or disk. The **last line in FILE
  order** wins (`cld-desc` = 10, not 40). A tokenised load stores no lines and
  writes nothing.
* **R-DOT3a′** (new — the rule zerobas does not implement) — the write happens
  **after the line number is validated** and **regardless of whether the line is
  stored**. An `Out of memory` store writes it (`crf-oom` = 20 with nothing
  stored); a line number past the 65529 ceiling does not (`crf-ovr` = 10).
* **R-DOT3b** (second reference) — the **ASCII output walk** records the last
  line it emitted, driven by `LIST`, by `SAVE",A"` on disk, **or by
  `SAVE"CAS:name"`, which is an ASCII save on MSX1 with or without `,A`**. A
  tokenised write (`CSAVE`, disk `SAVE"file"`) writes nothing.
* **R-DOT4** (added non-writers) — `CLOAD`, `CSAVE`, and a mounted cassette.

## 3. What changes, and what it costs

### 3.1 The edit list

| # | file | change | cost |
|---|---|---|---|
| **E1** | [`sub/lineedit.asm`](../sub/lineedit.asm) | move the 6-byte `ld hl,(SL_NUM) / ld (DOT),hl` from `le_ok` to the **head of `le_store`**, before the `TXTMAX` bounds check | **0 B** (relocation; both the store and the bare-delete arm still pass through it) |
| **E2** | [`tests/test_program.py`](../tests/test_program.py) | `store_line` OOM test + its success control: with `PRGEND` set near `TXTMAX`, the store is refused **and** `DOT` holds the typed line number | +2 unit rows |
| **E3** | [`probes/basic/basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py) | the 23 rows (`cld` `csv` `dsk` `crf`), the cassette/disk device seam, the per-row capability lock, the variable-free readout, the `0/0 is not a pass` guard | probe only |
| **E3b** | [`probes/lib/omsx_repl.py`](../probes/lib/omsx_repl.py) | `@WAIT<seconds>` pseudo-lines (advance the emulated timeline, type nothing) — a tape row must wait out a 10–30 s cassette operation, and doing it with pad lines cost screen rows the 24-row display did not have (characterization §1.4b) | shared, additive and inert unless the sentinel appears |
| **E3c** | [`tests/msxtest.py`](../tests/msxtest.py) | widen the sub-ROM bridge's copy-back window to `[$8000,$F300) + [$F380,$10000)` — it stopped at `$F300`, so **every sub-side write to a work-area sysvar above the stack was invisible to the unit harness** (`DOT`, and D-REHOME's `ERRFLG`/`ERRLIN`/`ONELIN`/`ONEFLG`/`DEFTBL`) | shared; all 56 unit files still pass |
| **E4** | [`Makefile`](../Makefile) | widen `lnblank-say-acceptance`'s default `ONLY=` with `cld-,csv-,dsk-,crf-` | — |
| **E5** | probe `KNOWN_DIVERGE` + [`TODO.md`](../TODO.md) | pin the three rows that diverge for reasons this slice does **not** own (§3.2) | 3 pins |

🔴 **E1 IS PLACED BY A MEASUREMENT AND NOT BY TASTE.** The 65529 ceiling is
checked in the RESIDENT head ([`basic/program.asm:99`](../basic/program.asm:99)
`dl_store`), long before `store_line` marshals to the sub-ROM — so `le_store`'s
head is reached only for line numbers that were accepted, which is precisely
where R-DOT3a′ puts the write. One instruction earlier (in `dl_store`) would
make `crf-ovr`/`crf-huge` read 65530/34463; one instruction later (today's
`le_ok`) makes `crf-oom` read 99. The rule names the gap between two checks and
there is exactly one place in the tree that is inside it.

### 3.2 What is deliberately NOT touched — three findings this slice does not own

Each is pinned to its exact zerobas value, so the pin goes stale (loudly) the
day it is fixed.

| | finding | why not here | pin |
|---|---|---|---|
| **D2** | `SAVE"CAS:name"` writes a **tokenised** tape; both references write **ASCII** (tape decoded, characterization §3.2) | a SAVE-FORMAT change: it re-specifies a shipped verb, and [`basic_probe_tape_save.py`](../probes/basic/basic_probe_tape_save.py) asserts the tokenised form as its oracle. Fixing a save format inside a `.` slice would blur both | `csv-tok` = ` 5  0 ` |
| **D3** | `LOAD"CAS:"` accepts a tokenised tape; the reference searches past it and **never returns** | the faithful behaviour is a HANG, which cannot be gated by any row | none (no row can carry it) |
| **D4** | a line store is bounded by the **constant `TXTMAX`**, not by HIMEM/`CLEAR`, so zerobas accepts lines both references refuse | a memory-map question, and the reason gap 3 has no emulator gate at all | `crf-oomsay` = `<nothing listed>`, `crf-oomlst` = `20 REM …\|99 REM Z` |

## 4. Rows and pins

* **23 new rows**, all `--say`: `cld-` 6, `csv-` 4, `dsk-` 5 (capability-locked
  to cf3300 + zb), `crf-` 8.
* **20 of 23 are green today**; the three above are pinned. **No row is retired.**
* Controls, named: `cld-ctl` `cld-cload` `csv-ctl` `csv-csave` `dsk-ctl`
  `dsk-savtok` `crf-ovrctl` `crf-oomctl` — four of them **non-writer** controls,
  which in this battery is the load-bearing kind: every positive row says "a
  value moved", and only the contrast says the rule is about **storing lines**
  and **ASCII output** rather than about the verbs `LOAD` and `SAVE`.
* 🔴 **`crf-oom` AGREES ON ZEROBAS FOR THE WRONG REASON AND MAY NEVER BE READ AS
  COVERAGE** (characterization §1.5/§4.2). Its companions `crf-oomsay` and
  `crf-oomlst` are the rows that say so, and they are pinned RED for D4.

## 5. Predicted RED and predicted GREEN

Derived from the **edit list**, not from the scope list
([[predicted-red-set-must-not-inherit-scope]]).

**Predicted RED — the emulator corpus: EMPTY. Zero rows may move.**

That is not a hedge, it is the prediction, and it follows from D4: no typed row
on zerobas can reach `le_store`'s OOM path, so relocating the write inside
`le_store` is invisible to all 788 rows and to every acceptance gate. **A row
that DOES move is a finding about the edit** — it would mean the write now fires
somewhere R-DOT3a does not put it.

**Predicted RED — the unit corpus: exactly the two new `test_program.py` rows**,
and only the OOM one (`store_line` refused ⇒ `DOT` = the typed number) fails
before E1 and passes after. Its control (an accepted store ⇒ `DOT` = the typed
number) passes on both sides of the edit and is what says the test is wired to
the right cell.

⚠️ **AN EMPTY PREDICTED-RED SET IS THE SHAPE D-DOTLINE'S OWN §9.1 WARNS ABOUT**
([[knife-that-reddens-nothing-is-the-finding]]): a green run proves nothing here,
because a green run is also what *doing nothing at all* produces. K1 below is the
only thing that separates them, and it is scored on the unit corpus.

**Predicted GREEN (must not move).** All 788 probe rows including the 23 new
ones; `lnblank-acceptance` 536/536; `lnblank-say-acceptance` 181 → **204**;
`unit-test` 56 → **58**; every other standing gate; **both ROM images
byte-identical except for the 6 relocated bytes** (walls unchanged: low 23 B,
main page 1 301 B, sub p0 3913 B, sub p1 2411 B).

## 6. The whole corpus

The standing list in `TODO.md` — `unit-test` · `deadcode` both builds ·
`msgexact --gate` + `--relock` · `lnblank-acceptance REPEAT=2` ·
`lnblank-say-acceptance` · `lnblank-echo` · `logicops` · `array` · `sysvarsweep` ·
`error-trap`/`error`/`abort`/`stop-trap` · `direct-ctrl` · `kwsweep` · the rest.

⚠️ **`lnblank-echo` IS NOT A FORMALITY THIS TIME.** 22 new payloads, including
the 33-character `20 REM BBB…` and the `PRINT"[";PEEK(63157);PEEK(63158);"]"`
readout at 36 characters — two columns under the wrap that returns `<none>`. The
echo guard is what says they were typed verbatim on all three machines.

## 7. Knives — each with a predicted RED set **and** predicted GREEN survivors

| # | cut | predicted RED | predicted GREEN |
|---|---|---|---|
| **K1** | put the `DOT` write back at `le_ok` (revert E1) | the new `test_program.py` OOM row, and **only** it | its success control; **all 788 probe rows** |
| **K2** | move the write EARLIER, into `dl_store` before the ceiling check | `crf-ovr` → ` 250  255 ` (65530 = $FFFA), `crf-huge` → ` 159  134 ` (99999 wraps to 34463 = $869F in BC) | `crf-oom`, `crf-oomctl`, every `cld`/`csv`/`dsk` row — this is the knife that says the placement is *between two checks*, not merely *early* |
| **K3** | drop the `dsk` entry from `SIDE_LOCK` | all 5 `dsk-` rows on a three-side gate (the VG-8020 has no `A:` and answers something else) | every other row — scores the capability lock itself |
| **K4** | put `99 REM Z` back BEFORE the shrink in the `crf` rows | `crf-oomsay` (`Out of memory` → the shrink's own message), `crf-oomlst` (both lines listed) **on the references** | **`crf-oom` stays ` 20  0 `** — the knife aimed at this slice's own justification: it shows the value row cannot tell a refusal from a success and the companions can |
| **K5** | revert `cld-cload` to a bare `CLOAD` | `cld-cload` on zb → ` 40  0 ` | every other row; ⚠️ **not scoreable on the references** — the bare form searches past the end of the tape and does not return |
| **K6** | delete the `DOT` write from `le_store` entirely | `cld-asc` `cld-desc` `cld-mrg` `cld-list` `dsk-load` `dsk-mrg` + D-DOTLINE's `cln-store` `cln-edit` `cln-ins` `cln-sdel` `clp-*` store rows | `cld-ctl` `cld-cload` `csv-*` `dsk-savasc` `dsk-savtok` `crf-ovr*` — says the NEW load rows have teeth, and that writer (b) is a separate mechanism |

Every knife rebuilt from clean (`rm -rf build`), **ROM-hash-checked as actually
different before scoring**, reverted against the build it cut, and both ROMs
re-hashed to baseline afterwards ([[make-mtime-race-skips-subrom]] — `make`
skips a rebuild when source and output share an mtime, and only the hash check
catches it).

## 8. Open questions for sign-off

1. **D2 — fix or file?** `SAVE"CAS:name"` writing a tokenised tape is a measured
   MSX1 divergence, and it is the direct cause of the one `csv-` row that goes
   red. **Recommendation: file + pin.** It changes a shipped save format and
   inverts an assertion in `basic_probe_tape_save.py`, which is a save slice's
   work, not a `.` slice's.
2. **Is a host unit test an acceptable instrument** for R-DOT3a′, given D4 puts
   the OOM path out of reach of every emulator row? **Recommendation: yes** —
   and say so in the source, so the next reader does not mistake a green
   acceptance run for coverage of this rule.
3. **The gate gets longer.** The 23 rows are `--say`, i.e. boot-per-case: adding
   them to `lnblank-say-acceptance`'s default `ONLY=` costs roughly **1.5–2 h**
   on top of the ~2 h that target already takes. Accept, or leave the four
   prefixes out of the default and run them by `ONLY=`?
   **Recommendation: accept** — a row nobody runs is the `dir-name` defect.
4. **D3/D4 pins** — confirm they are filed rather than fixed here.

**Signed off 2026-08-03**: implement E1 + E2; D2 filed and pinned; the say gate's
default widened; D3/D4 filed.

---

## 9. Results

### 9.1 Walls — clean `rm -rf build && make basic-reloc`

| | HEAD `638a141` | as built | §3.1 predicted |
|---|---:|---:|---:|
| main page 1 free | 301 B | **301 B** | 301 B ✅ |
| main page-0 low free | 23 B | **23 B** | 23 B ✅ |
| sub page 1 free | 2411 B | **2411 B** | 2411 B ✅ |
| sub page 0 free | 3913 B | **3913 B** | 3913 B ✅ |

**Zero bytes, as predicted** — the write is the same six bytes at a different
address. A rule that was wrong on both references cost nothing to make right;
what it cost was the measurement.

### 9.2 Gates

| | |
|---|---|
| `make unit-test` | **56/56 files** — `test_program.py` grows from 8 groups to 10 |
| `deadcode`, both builds | **0 dead** |
| `msgexact --gate` / `--relock` | **55/55** / all 41 locked values reproduce |
| `lnblank-acceptance REPEAT=2` | **536/536**, allowlist EMPTY |
| `lnblank-echo` | **green** — only the three standing informational rows (`dec-eol`, `dec-eolctl`, `num-tab`) report MANGLED, on all three sides, as before. **No new mangle on any of the 23 new payloads**, after §9.4 |
| `logicops` · `array` · `string` · `kwsweep` · `sysvarsweep` | green (`array` 151/151) |
| `error` · `error-trap` · `abort` · `stop-trap` · `direct-ctrl` | green (`abort` 49/49, `direct-ctrl` 40/40) |
| `linemax` · `arrdim` · `clearpool` · `float` | green (`linemax` 60/60) |
| `lnblank-say-acceptance` | **204/204 gating rows agree** across all three sides (181 → 204), pins 2 → **5** |

⚠️ **`msgexact --gate` FAILED 55/55 THE FIRST TIME AND THE CAUSE WAS THE
APPARATUS, NOT THE BUILD.** It ran first in the corpus script, after
`rm -rf build && make basic-reloc` — which rebuilds the relocated image but not
the merged repack ROM the installed machine points at. Every row read `<none>`
against a machine whose ROM file did not exist. Re-run after any
`repack-machine` target it is 55/55. [[stale-machine-reads-as-unimplemented]],
and the reason the corpus script now runs a `repack-machine` target first.

### 9.3 Knives

Scored against the battery on zerobas unless noted; every cut rebuilt from clean,
ROM-hash-checked as actually different before scoring, reverted against the build
it cut, both ROMs re-hashed to baseline afterwards.

| knife | predicted RED | measured | verdict |
|---|---|---|---|
| **K1** write back at `le_ok` | the unit OOM row and **only** it | **1 red**: `.` = 99 not 20; its control, the ERR-7 check, the nothing-stored check and all 788 probe rows green | ✅ exact |
| **K2** write in `dl_store`, before the ceiling check | `crf-ovr` ` 250  255 `, `crf-huge` ` 159  134 `; every other row green | **exactly those 2 red**, every other `crf` row green — but `crf-huge` read ` 255  255 `, not ` 159  134 ` (below) | ✅ set exact, 🔴 one value wrong |
| **K3** drop the `dsk` capability lock | all 5 `dsk-` rows answer something other than the CF-3300's values on the VG-8020 | all 5 read **`NOCAPTURE`** — stronger than predicted: the run would abort as an APPARATUS FAILURE, not quietly mis-measure | ✅ |
| **K6** delete the `DOT` write from `le_store` | `cld-asc` `cld-desc` `cld-mrg` `cld-list` `dsk-load` `dsk-mrg` + `cln-store` `cln-ins` `cln-sdel`; the controls and `csv-*` GREEN | the `cln`/`cld` reds landed — **and 8 predicted-GREEN rows went red, while 2 predicted-RED rows stayed green** (below) | 🔴 finding |

🔴 **K2's PREDICTED-RED SET WAS EXACT AND ONE OF ITS PREDICTED VALUES WAS NOT.**
`crf-huge` (`99999 REM B`) was predicted ` 159  134 ` — 34463, the wrapped value
`basic/program.asm:91` records — and read ` 255  255 `. The prediction was read
off a comment describing the **pre-fix** behaviour: D-LNBLANK added `pl_sat`
([`basic/program.asm:303`](../basic/program.asm:303)) precisely because *a bound
tested after a lossy step tests the wrong number*, so `parse_lineno` **saturates
at 65535** and 34463 has not been reachable since. The row still went red, and the
direction of the finding (the write must sit AFTER the ceiling check) is
unaffected — but the value written down in advance was wrong, and it is the
knife that says so rather than any gate.

🔴 **K6 REFUTED MY OWN PREDICTED-GREEN SET, AND THE REASON IS A PROPERTY OF THIS
BATTERY WORTH STATING.** Eight rows I predicted green went red — `cld-ctl`,
`cld-cload`, `csv-ctl`, `csv-csave`, `csv-tok`, `dsk-ctl`, `dsk-savtok` and every
`crf-ovr*` row — all reading ` 0  0 `. Each of them establishes its pre-state by
**storing a line**, so deleting writer (a) removes the value they are the control
*for*. **They are controls for the VERB (does `CLOAD` write? does `CSAVE`?), not
for the CELL** — a knife on the cell reddens them by construction, and reading
them as independent of writer (a) would have been wrong.

🔴 **AND TWO PREDICTED-RED ROWS STAYED GREEN: `dsk-load` and `dsk-mrg` HELD AT
` 40  0 ` WITH WRITER (a) DELETED.** Both rows perform a `SAVE",A"` as their own
setup, and that walk writes 40 — the same value the load is expected to write.
**Their reading has two sufficient causes** ([[row-with-two-candidate-causes]]),
and only `dsk-ctl` (a stored line writes on this side) plus the cassette rows
`cld-asc`/`cld-desc` (no save in the row at all) make the disk load attributable.
Said here rather than repaired: a disk file always reloads in ascending order, so
the descending-file separator that makes `cld-desc` decisive cannot be built over
`SAVE",A"`. **The disk rows are the DEVICE control; the cassette rows are what
establish the load writer.**

🎯 **K6 ALSO CONFIRMED THE TWO WRITERS ARE SEPARATE MECHANISMS, MEASURED.**
`csv-asc` and `dsk-savasc` stayed at ` 40  0 ` with writer (a) gone: the ASCII
walk writes on its own. This is D-DOTLINE's K2/K3 mutual control, extended to the
new devices.

⚠️ **K4 AND K5 WERE SCORED DURING CONSTRUCTION, NOT RE-RUN, AND THAT IS SAID
RATHER THAN IMPLIED.** Both cuts were made accidentally — by writing the row the
wrong way round the first time — and their readings are recorded where they
happened (characterization §1.4, §1.5): K4 (setup before the shrink) reddened
`crf-oomsay`/`crf-oomlst` on **both references** while `crf-oom` stayed
` 20  0 `, which is the whole argument for the companion rows; K5 (a bare
`CLOAD`) read ` 40  0 ` on zerobas, the value its positive row carries. Neither
was re-cut against the final build.

### 9.5 What the three gaps cost, and what they bought

**0 bytes, one instruction, and 23 rows.** Two of the three reasoned answers were
right; the tree could not tell which. What it can tell now:

* an ASCII `LOAD`/`MERGE` writes `.` **per stored line, in file order** — gated on
  cassette (both references) and disk (`dsk-` capability-locked);
* the ASCII-SAVE walk writes it, on **two** references and **two** devices, so
  D-DOTLINE's 12 B design point is no longer one machine's word;
* a **refused** store writes the line number typed — the one reasoned answer that
  was wrong, now the tree's behaviour and gated by a unit test, because no
  emulator row on this side can reach the path at all.

🔴 **And the gate that found the most was the ECHO GUARD, which is not about `.`
at all** (§9.4). Three of the four apparatus findings in this slice —
[[refusal-row-needs-a-refusal-proof]], [[controls-for-the-verb-not-the-cell]],
[[subrom-bridge-copyback-window]] — were found by a **control** or a **companion**
reading something impossible, never by the row carrying the answer.

### 9.4 🔴 The gate that found the most in this slice was the ECHO GUARD, twice — and the second time by DISAGREEING WITH ITSELF

Neither failure was about `.`. Both were about whether the rows measuring `.`
had been *delivered*, and the second one is the finding:

| run | flagged | what had changed |
|---|---|---|
| corpus | `csv-asc` `csv-tok` `csv-csave` on **cf3300** — `['10 REM A', '20 REM B']` | nothing; first run of the new rows |
| after shortening the save rows | `cld-desc` `cld-mrg` `cld-cload` `cld-list` on **cf3300**, `cld-cload` on **vg8020** — `['60 REM Y', …]` | the LOAD rows, which the previous run had **passed**, unchanged |

Every one of those rows read the right value, on every side, stably at
`--repeat 2`. What they could not do is prove the payload reached the machine:
each pad line spent two rows of a 24-row screen, and the case's own text scrolled
off the top. **Sitting exactly on the boundary, the same case passed in one run
and failed in the next.**

🔴 **A GUARD THAT PASSES INTERMITTENTLY IS WORSE THAN ONE THAT FAILS.** Tuning the
pad count — the obvious repair, and one that would have produced a green run
immediately — buys a *green run*, not a *verified payload*: the next slice to add
a line anywhere in these cases would have re-crossed the boundary silently. The
repair went into the harness instead (E3b): `@WAIT<seconds>` advances the
emulated clock and types nothing, so a tape row costs **zero** screen rows and
the guard has nothing to lose. Re-measured after the change, all 10 tape rows
read exactly what they read with padding — the mechanism is inert to the
measurement, which is the other thing that had to be shown.
