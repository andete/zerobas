<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-RUNTAIL — `RUN"file"` returns into the line that called it

Closes the residual filed as
[spec-fat-error-verb-control.md](spec-fat-error-verb-control.md) §8.6.
Reference reading: [runtail-msx1-characterization.md](runtail-msx1-characterization.md).
Gate: `make runtail-acceptance`
([`probes/basic/basic_probe_runtail.py`](../probes/basic/basic_probe_runtail.py)).

## 1. What was filed, and what it turned out to be

Filed: *"`run-missing` reads `'load error|Illegal function call in 3346'` — two
messages on one row, unexplained by any document."*

Measured: **the second message is not a property of the miss.** It follows
`RUN"A:RT.BAS"` with the file present, loaded and correctly run, and it follows
`LOAD"file",R` the same way. The residual named one row of a divergence that
covers **six**, three of them on the SUCCESS path of a shipped verb
(characterization §2).

🔴 **AND THE FILED READING WAS NOT THE WHOLE ODDITY EITHER.** After a *failed*
`RUN"missing"` zerobas **runs the program that is already resident**
(characterization §4). The CF-3300 prints its message and stops. That half was
invisible to `fat-error-acceptance` because no row there has a resident program
to run, and it directly contradicts `basic/PROVENANCE.md` §disk RUN, whose table
says `RUN"file"` *"always runs"*.

## 2. The mechanism, in one paragraph

`RUN"A:name"` is **not** the REPL's `RUN` command (`is_cmd` needs the next byte
to be end/space/`:`, and it is `"`). It is a crunched **statement**, so
`do_run`'s `jp run_prog` enters the run loop **nested inside the enclosing
line's own run loop** — and `run_prog` overwrites `CURLINE`. When the loaded
program ends, `run_prog`'s `ret` lands back in `exec`, the enclosing loop
resumes at `rp_run`, and "fall through to the next line" now walks off the
**loaded program's** end marker into `CURLINE := $0000`. `rp_lp` finds a
non-zero link there (`$C3F3`, the page-0 ROM's own `DI / JP`), so it does not
stop: it re-derives `DIRECTF` as run mode and dispatches the byte at `$0004` as
a BASIC statement. The `3346` is the word at `$0002` — `$0D12` — printed by
`print_in_lineno` as `CURLINE+2`. Full chain and its `END`-discriminator in
characterization §6.

**So there are two independent defects behind one symptom:**

* **A — the nested entry.** `run_prog` reached from a statement returns into a
  loop whose `CURLINE` it has destroyed. Affects every `RUN"file"` /
  `LOAD"file",R`, hit **and** miss.
* **B — the failed load runs anyway.** `load_error` **prints and returns**, and
  `do_run`'s next instruction is `jp run_prog`. Affects the miss rows only.

Fixing A alone leaves `ZQ1` printed after a failed load. Fixing B alone leaves
the stray error on all three hit rows. Both are required.

## 3. The change

### 3.1 A — enter `run_prog` at TOP LEVEL from a statement context

The REPL's own `RUN` already has the right shape: `dl_run`'s `jp run_prog` is
reached at `dispatch_line`'s depth, which is exactly the depth whose `ret`
returns **to the prompt**. `dispatch_line` records that depth in `SAVSTK`
before any statement runs, so the disk paths can adopt it verbatim:

```asm
run_prog_top:
                ld      sp,(SAVSTK)
                jp      run_prog
```

7 B, one new label in `basic/cload.asm`; the two call sites change `jp run_prog`
to `jp run_prog_top` at **zero** delta. `SAVSTK` is valid at both: a typed line
sets it in `dispatch_line`, and a stored line's `RUN"file"` inherits the
enclosing `run_prog`'s anchor — which is the same value, because that
`run_prog` was itself entered at `dispatch_line`'s depth. Discarding whatever
`GOSUB`/`FOR` context sat between is not a side effect to be tolerated; it is
what `RUN` means.

⚠️ **`autoexec_run` keeps its plain `jp run_prog` and that is deliberate.** It
is called from `init`, before the REPL, where `SAVSTK` has never been written —
`ld sp,(SAVSTK)` there would set SP from uninitialised RAM. It also has no
enclosing loop to corrupt, so it has no defect A to fix.

### 3.2 B — `disk_prog_load` gets a CF-out contract

`load_error` is reached by `jp` from inside `disk_prog_load`, so **its `ret` is
`disk_prog_load`'s return**. Making that return carry `CF=1` lets the two call
sites refuse to run, in one byte each.

🔴 **`load_error` ITSELF IS NOT TOUCHED, AND THAT IS THE POINT.** It has ~50
`jp`/`call` sites across `files.asm`, `save.asm`, `print.asm`, `field.asm`,
`format.asm`, `bload.asm` and `cload.asm`, several of which resume into their
caller on purpose (`save.asm` §bsave_opt4's header says so in as many words).
A `scf` inside `load_error` would change the returned CF for **all** of them.
The contract is therefore stated on `disk_prog_load`'s own exits:

| exit | was | becomes | Δ |
|---|---|---|---|
| `dpl_err` (EOF mid-program, bad marker, re-open failed) | `jp load_error` | `call load_error` / `scf` / `ret` | +2 |
| `dpl_oom` (store overflow) | `jp print_msg` | `call print_msg` / `scf` / `ret` | +2 |
| `dpl_done` (success) | `call relink` / `ret` | `call relink` / `or a` / `ret` | +1 |
| no disk slot; `fat_io_open` failed; the three `ascii_load` failures | `jp [z/c,]load_error` | `jp [z/c,]dpl_err` | 0 |
| `ascii_load` success | `ret` (CF already clear) | unchanged | 0 |

and consumed at the two call sites with `ret c` (+1 each). `autoexec_run`
ignores the new CF, unchanged.

### 3.3 The whole diff, priced

| site | change | bytes |
|---|---|---|
| `basic/cload.asm` `run_prog_top` | new | +7 |
| `basic/cload.asm` `do_run` disk arm | `ret c`; `jp run_prog_top` | +1 |
| `basic/cload.asm` `do_load` disk arm | `ret c`; `jp run_prog_top` | +1 |
| `basic/cload.asm` `dpl_done` | `or a` | +1 |
| `basic/cload.asm` `dpl_err` | `call`/`scf`/`ret` | +2 |
| `basic/cload.asm` `dpl_oom` | `call`/`scf`/`ret` | +2 |
| `basic/cload.asm` head + `ascii_load` | repoint to `dpl_err` | 0 |
| **total** | | **+14** |

## 4. Predicted GREEN, at exact values (fixed BEFORE the change)

| measurement | baseline `e98e77d` | predicted after |
|---|---|---|
| `runtail-acceptance` | *(new)* | **9/9 scored readings agree**, 8 cases, 3 positive controls, exit 0 |
| `fat-error-acceptance` | 8/8 + 5 dir checks, 8 of 8 verb controls | **unchanged**, exit 0 |
| …and its `run-missing` printed reading | `'load error\|Illegal function call in 3346'` | **`'load error'`** |
| main low region free | 3 B | **3 B** (no low-region code) |
| main page 1 free | 186 B | **172 B** (186 − 14) |
| sub p0 / p1 free | 3843 / 1540 | **unchanged** |
| `disk.rom` / `sub.rom` hash | `2c630d3d…` / `6ea374de…` | **unchanged** — no disk-ROM or sub-ROM source moves |
| `basic-reloc.rom` / `zerobas-main-eu.rom` hash | `849d661e…` / `4952fb9e…` | **both change** |
| closure | `122+4 / 718+15 / 582+41` | **unchanged** |
| `preflight-check` | 181/86/95/95/0 | **unchanged** |
| `injector-check` | 329 | **unchanged** |
| `unit-test` | 58 | **unchanged** |
| `deadcode` main spans / seeds | 1565 / **287** | 1565 / **287** — the slice writes no new words under `sub/` or `tools/`, which is what moves the seed count |
| `audit-citations` files swept | 713 | **716** — three new files, all swept suffixes (`.py`, `.md`, `.md`) |
| `dskmsg` / `diskbasic` / `lptverb` | 5/5 · 34/34 · 44/44 | **unchanged** |

## 5. The knives — predicted RED **and** predicted GREEN survivors

Every cut is **byte-neutral** (`dev-workflow.md` §Knives), the subject is the
probe invoked directly (never `make`), and each is run **twice**. The runner
hashes all four ROMs after every cut build: a cut that lands byte-identical is
**DID-NOT-HAPPEN**, not a miss.

| # | cut | predicted RED | predicted GREEN survivors |
|---|---|---|---|
| **K-TOP** | `run_prog_top`'s `ld sp,(SAVSTK)` → 4 × `nop` — defect A returns, defect B stays fixed | `run-hit`, `run-hit-res`, `loadr-hit` (3), exit **2** (`run-hit` is a control) | the 3 miss rows, `bare-run`, `load-plain`, `load-plain:listing` |
| **K-CF** | `do_run`'s `ret c` → `nop` — the RUN site stops consuming the contract | `run-miss`, `run-miss-res` (2), exit 1 | `loadr-miss-res` (do_load's own `ret c` survives — this is what separates the two consumers), all 3 hit rows, both controls |
| **K-PROD** | `dpl_err`'s `scf` → `or a` — the contract's PRODUCER lies; deterministic CF=0, not an accident of `print_msg` | all 3 miss rows, exit 1 | all 3 hit rows, `bare-run`, `load-plain`, `load-plain:listing` |
| **K-DONE** | `dpl_done`'s `or a` → `scf` — a SUCCESSFUL load reports failure | all 3 hit rows, exit **2** | the 3 miss rows, `bare-run`, `load-plain` **and** `load-plain:listing` — the program is still loaded, only the run is skipped |

⚠️ **K-DONE is also the proof that the positive controls are load-bearing.**
Under it `run-hit` reads `<nothing>` — which is a *perfectly agreeable* answer
for a machine that runs nothing — and it is caught only because that row's
agreed reading is required to contain `ZQ9`
([[gate-whose-answer-is-an-error-passes-a-dead-subject]]).

⚠️ **Coverage, stated exactly.** K-TOP covers defect A. K-PROD covers defect
B's producer, K-CF one of its two consumers. **No knife here separates
`do_load`'s `ret c` from `dpl_err`'s `scf`** — K-PROD reds `loadr-miss-res`
through the producer, and cutting `do_load`'s `ret c` alone would red the same
row. Not claimed as more than that.

## 6. As-built

### 6.1 The change, and the walls

**+14 B on main page 1, to the byte** — the §3.3 price was exact. Measured from
clean (`rm -rf build && make basic-reloc`):

| wall | before | after |
|---|---|---|
| main low region | 3 B | **3 B** |
| main page 1 | 186 B | **172 B** |
| sub page 0 | 3843 B | **3843 B** |
| sub page 1 | 1540 B | **1540 B** |

ROM hashes: `disk.rom 2c630d3d…` and `sub.rom 6ea374de…` **unchanged** as
predicted (no disk-ROM or sub-ROM source moves); `basic-reloc.rom`
`849d661e… → 9af44b5a…` and `zerobas-main-eu.rom` `4952fb9e… → e60a4248…`.
The ROM moves, so the emulator gates are meaningful and were run in full.

### 6.2 Predictions, scored

| prediction | outcome |
|---|---|
| `runtail-acceptance` 9/9, exit 0 | ✅ **9/9 scored readings agree**, 8 cases, 3 positive controls, exit 0 |
| page 1 186 → 172 B | ✅ exact |
| low / sub p0 / sub p1 unmoved | ✅ 3 / 3843 / 1540 |
| `disk.rom` + `sub.rom` hashes unchanged | ✅ |
| `fat-error-acceptance` unchanged, and `run-missing` reads `'load error'` | ✅ 8/8 + 5 dir checks, 8 of 8 verb controls; the row now reads **`'load error'`** — one message |
| `audit-citations` 713 → 716 files swept | ✅ exact |
| `deadcode` main **seeds** 287 | ✅ exact |
| `preflight-check` 181/86/95/95/0, `unit-test` 58 | ✅ unchanged |
| `injector-check` 329 · `deadcode` spans 1565 · `audit` basic 184 | ❌ **330 / 1566 / 185** — three misses, all the slice's own footprint (§6.5) |
| corpus otherwise unmoved | ✅ 18 gates, all PASS — see §6.5 |

### 6.3 🎯 The knives — 4 designed, 4 run, each TWICE, both rounds identical

| # | cut (all byte-neutral) | rc | RED | HELD |
|---|---|---|---|---|
| **K-TOP** | `run_prog_top`'s `ld sp,(SAVSTK)` → 4 × `nop` | 1 | `run-hit`, `run-hit-res`, `loadr-hit` | the 3 miss rows + both controls + `load-plain` |
| **K-CF** | `do_run`'s `ret c` → `nop` | 1 | `run-miss-res` | everything else, **`loadr-miss-res` included** |
| **K-PROD** | `dpl_err`'s `scf` → `or a` | 1 | `run-miss-res`, `loadr-miss-res` | all 3 hit rows + both controls |
| **K-DONE** | `dpl_done`'s `or a` → `scf` | **2** | `run-hit`, `run-hit-res`, `loadr-hit` | the 3 miss rows, both controls, **and `load-plain:listing`** |

All four reached the artifact (ROM hashes moved on every cut build; the runner's
hash guard never had to declare DID-NOT-HAPPEN), and the tree hashed back to
baseline after the restore.

🎯 **K-CF SEPARATES THE TWO CONSUMERS OF THE CF CONTRACT.** Cutting `do_run`'s
`ret c` alone reds `run-miss-res` while `loadr-miss-res` stays green on
`do_load`'s own `ret c`. K-PROD then reds **both** by lying at the producer.
That is the evidence the two sites are independently wired, which no single cut
could give.

🎯 **K-DONE IS THE PROOF THAT THE POSITIVE CONTROLS ARE LOAD-BEARING.** A
successful load reporting failure makes every hit row read `<nothing>` — a
perfectly agreeable answer for a machine that runs nothing — and it is caught
only because `run-hit`'s reading is required to contain `ZQ9`. It is also the
only knife that exits **2**, i.e. reports an instrument fault rather than a
regression, which is what a broken control is.

### 6.4 🔴 Two predictions were WRONG, and one of them is a fact about the battery

**(a) K-TOP's exit code.** Predicted 2, measured **1**. Under K-TOP `run-hit`
reads `'ZQ9 / Illegal function call in 3346'` — which *contains* `ZQ9`, so the
control holds and the row merely DIFFs. The control is a **containment** check
by design: it fires when the program produced no output at all, which is the
dead-subject case it exists for. A row can DIFF while its own control holds.

**(b) 🔴 `run-miss` HELD under both K-CF and K-PROD, and that is the finding.**
Predicted RED; measured GREEN, twice, under two different cuts. The reason is
structural: with defect A fixed, running an **empty** program is silent, so on a
row with nothing resident `load error` is the whole tail whether the machine
*refused* to run or *ran nothing*. **`run-miss` is a defect-A row only.**

⚠️ **`run-miss` is the row the filed residual actually named.** A battery
written from §8.6 alone — one row, `RUN"NOSUCH"`, no resident program — would
have gated defect A and shipped defect B green. The `-res` rows exist only
because the **reference reading** showed the CF-3300 printing its message and
*not* `ZQ1`. Recorded as [[an-empty-program-hides-a-wrong-run]].

**(c) And the knives found a bug in the RUNNER, not the tree.** K-DONE's first
round ABORTED: the runner scraped only the scored `ok /DIFF` rows, and the
exit-2 report is a **complete** report in a different shape (`....` rows, a
banner, no tally line). The one knife whose purpose was to fail a control was
the one the guard was blind to — and the abort fired *before* the restore,
leaving the tree cut. Both fixes are now in
[`dev-workflow.md`](dev-workflow.md) §Knives: parse every exit code's shape, and
put the restore in a `finally`.

⚠️ **Coverage, stated exactly.** K-TOP covers defect A; K-PROD covers defect B's
producer and K-CF one of its two consumers. **No knife separates `do_load`'s
`ret c` from `dpl_err`'s `scf`** — K-PROD reds `loadr-miss-res` through the
producer, and cutting that `ret c` alone would red the same row. Not claimed as
more than that.

### 6.5 Corpus — 18 gates, sequential from clean, all PASS

`unit-test` **ALL 58 files** · `audit-citations` CLEAN (**716** files swept —
predicted exactly; `basic` 107 files / **185** provenance-bearing) ·
`preflight-check` **181/86/95/95/0** · `injector-check` ALL PASS, **330** files ·
`latch-check` PASS · `deadcode` main **1566 spans / 287 seeds** → 0 dead, sub
1512/102 → 0 dead (+1 allowlisted) · `lnblank-acceptance REPEAT=2` ·
`lnblank-say-acceptance` · `logicops-acceptance` · `float-acceptance` ·
`linemax-acceptance` · `dexp5-pin` · `editverb-acceptance` ·
`lptverb-acceptance` **44/44** · `dskmsg-acceptance` **5/5** ·
`diskbasic-acceptance` **34/34** · `fat-error-acceptance` **8/8 scored + 5
directory checks, 8 of 8 verb controls** · `runtail-acceptance` **9/9**.

🎯 **THE RESIDUAL IS VISIBLY CLOSED IN THE GATE IT WAS FILED AGAINST.**
`fat-error-acceptance` now prints

```
  PASS  run-missing    RUN"A:NOSUCH.BAS"   -> 'load error'
```

where `e98e77d` printed `'load error|Illegal function call in 3346'`. Its
`run-alive` control still reads `123`, so the row is still a measurement.

⚠️ **Three corpus counts moved and §4 predicted them unchanged.** All three are
the slice's own footprint and all three were derivable before the run, so they
are misses, not surprises:

| count | predicted | measured | why |
|---|---|---|---|
| `injector-check` files | 329 | **330** | the new probe is a file under `probes/` |
| `deadcode` main spans | 1565 | **1566** | `run_prog_top` is a new span |
| `audit-citations` `basic` provenance-bearing | 184 | **185** | ~~`cload.asm`'s new blocks cite `spec-basic-runtail.md`~~ 🔴 **WRONG CAUSE — see below** |

🔴 **CORRECTION 2026-08-07 (D-CASSEARCH §7.5): the last row's NUMBER was right and
its EXPLANATION was wrong, which is worse than a plain miss** — it was scored ✅
and the wrong mechanism propagated. `provenance-bearing` does not count comment
blocks at all. `tools/audit_citations.py:141` `provenance_files()` returns a list
of **FILES**: the target's `.asm`, its `PROVENANCE.md`, and
`probes/<target>/*.py` + `**/*.asm`. Measured: `basic` = 107 sources + 1
`PROVENANCE.md` + 78 probe files. `cload.asm` was **already** in that list, so a
new comment block inside it cannot move the count by construction. The real cause
of 184 → 185 is `probes/basic/basic_probe_runtail.py` — **the same cause the row
directly above already names for `injector-check`**. D-CASTAIL inherited this
explanation, repeated it, and D-CASSEARCH then mispredicted in the *opposite*
direction from it ([[a-count-is-predicted-by-reading-its-definition]]).

The one that is genuinely hard to predict — `deadcode`'s main **seed** count,
which is a function of the WORDS a slice writes under `sub/` and `tools/` —
was predicted correctly at **287**: this slice writes under `basic/`, `docs/`,
`probes/` and the `Makefile`, and none of those feed the seed set.

## 7. Out of scope, said explicitly

* **The first message's wording.** `load error` where the CF-3300 says
  `File not found` is the quarantined no-disk / mount / I-O divergence recorded
  in `basic/PROVENANCE.md` and filed in `TODO.md`. The probe normalises exactly
  that one string per side so these rows can be scored on **shape**. Not
  re-opened.
* **`ERR` / `ERL` after the event.** They are read-back sysvars with no cold
  init, so a `PRINT ERR;ERL` reads whatever the previous case left. Screen text
  only.
* **The tape twins.** See §9.

## 9. Residual — the tape twins are the same defect, unmeasured here

> ✅ **CLOSED 2026-08-07 by D-CASTAIL** —
> [spec-basic-castail.md](spec-basic-castail.md), measured in
> [castail-msx1-characterization.md](castail-msx1-characterization.md).
> Both defects were present on both tape sites; fixed for **+7 B** and gated by
> `make castail-acceptance` (9/9 + 1 pinned divergence, three-sided).
> 🔴 **The first bullet below is WRONG and is left standing as written.**
> `omsx_repl` already mounts cassettes through its `prologue` seam — the claim
> is true of `run_cases`'s *signature* and false of the module, so **no library
> change was needed**. The real blocker was not the instrument: on an MSX1 a
> **missing tape file is not an error** (the reference searches past the end of
> the tape and waits forever), so there is no tape twin of `run-miss` and the
> only failure a reference reports and returns from is an operator Ctrl-STOP.

`basic/cload.asm`'s `dl_cas_close` (`LOAD"CAS:x",R`) and `dr_is_cas`
(`RUN"CAS:x"`) end in the identical `jp run_prog` from a statement context, so
defect A is structurally present there too. They are **not** changed by this
slice and the reason is a number, not a preference:

* This battery has **no cassette instrument** — `omsx_repl.run_cases` mounts a
  disk, not a `.cas`, so no row here can read them either before or after.
* Defect B's fix needs a **measured** CF-out contract on `do_tape_prog`, and
  `do_tape_prog`'s success exits have not been read. Pointing the tape sites at
  `run_prog_top` without it would fix half a defect on an unmeasured path.

Filed in `TODO.md`. The one-word edit is `jp run_prog` → `jp run_prog_top` at
both sites **once a cassette row exists to score it**.
