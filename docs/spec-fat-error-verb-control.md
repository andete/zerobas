<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-FEVERB — `fat-error-acceptance`'s missing per-VERB control, and the denominator that comes with it

Predecessor: [`spec-basic-dkname.md`](spec-basic-dkname.md) §6.4/§6.7, which
filed this item and measured the consequence.
Lesson: [[one-positive-control-per-gated-verb]],
[[gate-whose-answer-is-an-error-passes-a-dead-subject]],
[[precondition-is-the-instrument]].

D-DKNAME's knife K-NAMECTL neutered `NAME` — `tnt_name_stamp` re-reads the
directory sector instead of writing it back, so the verb reports success and
renames nothing — and asked both instruments what they scored:

| instrument | verdict on a provably broken `NAME` |
|---|---|
| `basic_probe_dskmsg.py` | **red**, via the new `dsk-namehit` control (exit 2) |
| `disk_probe_fat_error_disposition.py` | 🔴 **8/8 ALL PASS, exit 0**, PRECONDITION green |

The second gate pins `name-missing` to `File not found` — a **reference-exact**
answer, measured on the CF-3300 — while nothing in it ever executes a `NAME`
that must succeed. This slice closes that, and states what is still open in the
same breath.

---

## 1. Why the existing PRECONDITION cannot cover it

`fat-alive` (`FILES"A:HI.TXT"`) proves the **FAT layer** reaches a success
disposition: the volume mounts, the root-directory walk runs, `fat_find` hits.
That is what it was written for (D-DSKJUDGE), and it is still exactly right for
what it claims.

It says nothing about any particular verb. `NAME`'s failure path
(`fat_mount` → `fat_find` miss → the new `nm_notfound` arm) and `NAME`'s success
path (the `DISKOP_SEL_NAME_STAMP` tenant: read the sector, `LDIR` the 8.3 field,
write it back) **share almost nothing**. A build in which only the second is
broken satisfies `fat-alive`, satisfies `name-missing`, and satisfies the
directory check — which cannot create a file it is asserting the absence of.

🔴 **The scope of a control is the scope of what it exercises.** A battery-level
control licenses battery-level claims ("the FAT layer is alive"); a row that
pins one verb's message needs that verb's own success path shown. Fixing it once
per verb is not the endless-instances trap [[precondition-is-the-instrument]]
warns about — it is the correct granularity, and §4 makes the *remaining* count
visible rather than leaving it to be inferred.

## 2. The change

### 2.1 A per-case VERB CONTROL, not a second precondition

A case may now name a control that must succeed for **that case** to be scored:

```
CASES  = [(key, line, want, verb_control_or_None), …]
```

* the control fails ⇒ its case prints **`NOT MEASURED`** (never PASS, never
  FAIL) and the run exits **2**;
* the other cases are still scored — a broken `NAME` does not blank what
  `LOAD`/`MERGE`/`OPEN` reported.

⚠️ **Exit-code precedence, stated:** `2` (instrument) dominates `1`
(regression). A run in which one row regressed *and* another row's verb control
failed exits 2, because part of the report is not a measurement and the reader
must know that before reading the rest. Unchanged from `fat-alive`'s existing
disposition, now with a second way to reach it.

Making it a **second PRECONDITION** was considered and rejected: that would blank
all eight rows on a `NAME` bug, which over-claims in the opposite direction. The
control's blast radius is its verb.

### 2.2 `name-alive`, on TWO instruments

```
NAME"A:PROG2.BAS" AS "REN2.BAS"
FILES"A:REN2.BAS"
```

| instrument | assertion | why it is not the other one |
|---|---|---|
| **screen** | the reading contains `REN2` **and** `BAS` | positive TEXT. A `NAME` that renamed nothing prints `File not found` here, which contains neither |
| **directory** (host parses the image after openMSX exits) | `REN2    BAS` **present** *and* `PROG2   BAS` **absent** | immune to every readout failure the screen half has; the same second-instrument shape `append-missing (directory)` already uses. A build that printed a convincing `REN2    .BAS` without writing the sector is caught only here |

**`PROG2.BAS`, not `HI.TXT`.** `fat-alive` lists `HI.TXT`, and the battery runs
**batched on one image**, so renaming `HI.TXT` would break the precondition on
the very run the control is evidence about. `PROG2.BAS` is on
`disk/test720.dsk` (`TEST.BIN`, `HI.TXT`, `PROG.BIN`, `PROG.BAS`, `PROG2.BAS`)
and no row in this probe reads it. The name `REN2` appears nowhere else in the
tree, so the screen assertion cannot match by accident.

⚠️ **A THIRD WRITING ROW ON THE MOUNTED IMAGE.** `append-missing` already writes
on a broken build, and `name-alive` writes on a *working* one — which is exactly
why the image is a `/tmp` copy and always has been. The `--diska` escape hatch
now mutates a caller-supplied image on **every** run, not only on a broken build;
the docstring says so.

### 2.3 The control runs FIRST, in the same batch

`specs = [fat-alive] + [name-alive] + [the eight cases]` — same machine, same
boot, same mounted image. A control measured in a different run is evidence
about a different run.

---

## 3. Predicted GREEN, at exact values

1. `make fat-error-acceptance` = **8/8 + 2 directory checks**, exit **0**:
   * `fat-alive` → `'HI      .TXT'` `[PRECONDITION]`
   * `name-alive` → contains `REN2` and `BAS` `[VERB CONTROL for name-missing]`
   * `kill-missing` and `name-missing` → `'File not found'`
     `[reference-exact: 'File not found']`
   * the other six → `'load error'`
   * `name-alive (directory)` → `REN2    BAS` present, `PROG2   BAS` absent
   * `append-missing (directory)` → `NOSUCH  DAT` absent
   * a printed line naming the denominator: **1 of 8** rows has a verb-success
     control.
2. **All four ROM hashes UNCHANGED** — `disk.rom 2c630d3d…`,
   `sub.rom 6ea374de…`, `basic-reloc.rom 849d661e…`,
   `zerobas-main-eu.rom 4952fb9e…`. This slice touches one probe and two
   documents; it assembles nothing.
3. Walls unchanged: low **3 B**, page 1 **186 B**, sub p0 **3843 B**,
   sub p1 **1540 B**; `deadcode` main 1565 / 287, sub 1512 / 102, 0 dead.
4. `audit-citations` **712 → 713** (this file is a new swept `.md`).
   `injector-check` unchanged at **329** — the probe gains no `subprocess` and
   composes no injector, it goes through `omsx_repl`. `preflight-check`
   unchanged at **181/86/95/95/0** for the same reason.
5. `unit-test` 58 files.

⚠️ **THE EMULATOR GATES THAT CAN ONLY RE-DRIVE THE SAME MACHINE ARE SKIPPED, AND
THAT IS STATED RATHER THAN FOLDED INTO "corpus green"** — prediction 2 is the
licence. `dskmsg-acceptance`, `diskbasic-acceptance`, `lptverb-acceptance`,
`editverb-acceptance`, `lnblank*`, `logicops`, `float`, `linemax`, `dexp5` and
`latch-check` all drive a byte-identical `zerobas-main-eu.rom` against a
byte-identical `disk.rom`, and none of them reads the file this slice edits.
`fat-error-acceptance` is the one emulator gate whose **subject** changed, and it
runs. §5.4 records the check that the licence is real.

---

## 4. 🔴 The denominator, which is the other half of the deliverable

Closing one hole and printing "ALL PASS" louder is how a gate stops describing
itself ([[a-hand-listed-denominator-is-a-scope-claim]]). So the count is
**measured, printed by the gate on every run, and filed**:

| rows | verb-success control | what a verb that ALWAYS errors scores |
|---|---|---|
| `name-missing` | ✅ `name-alive` | **red** (exit 2, NOT MEASURED) |
| `kill-missing` | ❌ none | **PASS** |
| `load-missing`, `run-missing`, `bload-missing`, `open-missing`, `append-missing`, `merge-missing` | ❌ none | **PASS** |

**1 of 8.** `kill-missing` is named first among the seven because it is the other
**reference-exact** row — pinned to a measured CF-3300 answer rather than to
zerobas's own quarantined `load error` — so it carries the same weight
`name-missing` does and has the same hole. It is one `CASES` tuple and one
control away, on machinery this slice builds; it is left out because the filed
item was `NAME`'s, and widening a residual while closing it is how a pickup list
stops being a pickup list.

`TODO.md` carries the remaining seven as one item, with `kill-missing` called out.

---

## 5. The knives

Subject: `probes/disk/disk_probe_fat_error_disposition.py`, invoked **directly**
— never `make fat-error-acceptance`, because `make` exits 2 for any failed
recipe and this slice's whole subject is the difference between the probe's own
rc 1 and rc 2 ([[injjudge-slice]]). Restore point: a **scratchpad snapshot**,
never `git checkout --`. Build before the baseline; a failed build **aborts**
rather than scoring. **Every knife run TWICE.**

| # | cut | predicted RED | predicted GREEN |
|---|---|---|---|
| **K-FE1** | `sub/dirverb.asm`: `tnt_name_stamp`'s `call fatprim_write_sector` → `call read_sector` — `NAME` reports success and renames nothing (D-DKNAME's K-NAMECTL, re-aimed at this instrument) | `name-alive` **FAIL** on both instruments (screen: `File not found`; directory: `REN2` absent, `PROG2` still present), `name-missing` printed **NOT MEASURED**, probe rc **2** | `fat-alive`; the other **seven** rows still scored and PASS; `append-missing (directory)` |
| **K-FE2** | `basic/files.asm`: `jr c,nm_notfound` → `jr c,nm_fail` — undo D-DKNAME, i.e. the **disposition** regresses while the verb still works | `name-missing` **FAIL** (`'load error'`), probe rc **1**, and the row **IS scored** | `fat-alive`, `name-alive` on both instruments, the other seven, both directory checks |
| **K-FE3** | `build/disk.rom` ← 16384 bytes of `$00`, written **after** the build (the D-DSKJUDGE dead-subject image, re-run against the new code) | `fat-alive` **FAIL**, probe rc **2**, **nothing** scored | nothing is scored, which is the verdict |

🎯 **K-FE2 IS THE GREEN CONTROL FOR K-FE1, AND IT IS THE POINT OF THE WHOLE
SLICE.** Both cuts break `NAME`. Only one of them means `name-missing` was not
measured. If `name-alive` reds under K-FE2 as well, the control is firing on
"anything about `NAME` changed" rather than on "the verb cannot succeed", and
the rc 1 / rc 2 split it exists to produce is noise
([[fixing-the-fault-silences-the-control]] — a control that cannot stay green is
not a control). The predicted pair is **rc 2 with the row unscored** against
**rc 1 with the row scored red**.

⚠️ **K-FE3 is a re-run, not a new claim.** D-DSKJUDGE measured 8/8 exit 0 on this
image. The prediction here is that it now exits 2 at `fat-alive` — which was
already true before this slice, and is re-measured because a change to the
control flow around the precondition is exactly the change that could silently
un-wire it.

### 5.4 The zero-ROM-bytes check

Before scoring the corpus, `rm -rf build && make basic-reloc && make
repack-machine` and compare all four hashes against §3.2. Equality is what
licenses skipping the emulator gates in §3; it is checked, not assumed.

---

## 6. As-built

### 6.1 Predictions, scored

| § | predicted | measured | |
|---|---|---|---|
| 3.1 | `8/8 + 2 directory checks`, exit 0, denominator printed | `8/8 scored (8 rows, 0 NOT MEASURED) + 2 directory checks`, `ALL PASS`, rc 0, and `VERB-SUCCESS CONTROLS: 1 of 8 rows` with the seven named | ✅ |
| 3.1 | `name-alive` → `REN2` + `BAS` on screen; directory `REN2    BAS` present / `PROG2   BAS` absent | `-> 'REN2    .BAS'   [VERB CONTROL for name-missing]` and `'REN2    BAS' present, 'PROG2   BAS' gone` | ✅ |
| 3.2 | **all four ROM hashes UNCHANGED** | `disk.rom 2c630d3d…`, `sub.rom 6ea374de…`, `basic-reloc.rom 849d661e…`, `zerobas-main-eu.rom 4952fb9e…` — byte-identical to D-DKNAME, from clean | ✅ |
| 3.3 | walls + deadcode unchanged | low **3 B**, page 1 **186 B**, sub p0 **3843 B**, sub p1 **1540 B**; main 1565/287, sub 1512/102, 0 dead | ✅ |
| 3.4 | citations **713**, injector **329**, preflight 181/86/95/95/0 | exactly those | ✅ |
| 3.5 | `unit-test` 58 files | 58 | ✅ |

**Skipped, and stated rather than folded into "corpus green"** (§3's licence,
checked in §5.4 and confirmed above): `dskmsg-acceptance`,
`diskbasic-acceptance`, `lptverb-acceptance`, `editverb-acceptance`,
`lnblank-acceptance`, `lnblank-say-acceptance`, `logicops-acceptance`,
`float-acceptance`, `linemax-acceptance`, `dexp5-pin`, `latch-check`. Every one
drives a byte-identical `zerobas-main-eu.rom` against a byte-identical
`disk.rom`, and none reads the edited file. They were **not run**.
(`dskmsg-acceptance` *was* driven repeatedly anyway — as the knife runner's
co-subject in §6.3 — and held 5/5 in every round.)

### 6.2 🔴 ROUND 2 DISAGREED WITH ROUND 1, AND THE RULE THAT CAUGHT IT IS "RUN IT TWICE"

The first knife pass scored **K-FE1 CUT in round 1 (rc 2) and MISS in round 2
(rc 0, nothing moved)**. The cut was identical; the reading was not.

The cause is `[[make-mtime-race-skips-subrom]]`: **GNU make 3.81 compares mtimes
at one-second granularity**, so an edit-then-build completing inside one tick is
silently skipped. Round 2's `sub/dirverb.asm` write landed in the same second as
the previous build's output, `make repack-machine` **exited 0 having rebuilt
nothing**, and the probe scored against the **pre-cut** `sub.rom`.

🔴 **The runner's "a failed build ABORTS" guard is the wrong guard.** The build
did not fail. It succeeded and did nothing, and the only visible symptom is a
knife that reads as a MISS — the reading that means *"the battery cannot see
this"*, which is precisely the conclusion a slice would then write down.

**Remedy, which that memory already prescribed and this runner did not have:**
hash all four ROMs after every cut build and require at least one to differ from
the baseline; on a match, `rm -rf build`, rebuild, and re-check; if it still
matches, the cut is byte-neutral and **abort**. With the guard, round 2 of K-FE1
reports `cut reached the ROM via: CLEAN REBUILD (make skipped it -- mtime race)`
and both rounds agree.

⚠️ **AND IT SENDS ME BACK TO THE PREVIOUS COMMIT.** D-DKNAME's **K-NAME2** was
recorded as a *predicted miss* — "nothing moved" — which is **the same reading a
stale build produces**. Its three knives were therefore re-run under the hash
guard: every cut reached the ROM incrementally in every round, and all three
verdicts stand unchanged (K-NAME1 CUT, K-NAME2 MISS, K-NAMECTL CUT). The
conclusion was right; the evidence for it now has the guard behind it, which it
did not before.

### 6.3 🎯 The knives — 3 designed, 3 run, each TWICE, both rounds identical (after §6.2)

| # | verdict |
|---|---|
| **K-FE1** | **CUT** — `name-alive` FAILs on **both** instruments (screen `'File not found'`; directory `REN2    BAS` ABSENT, `PROG2   BAS` STILL THERE), `name-missing` prints `NOT MEASURED (verb control 'name-alive' failed)`, probe rc **2**, tally `7/7 scored (8 rows, 1 NOT MEASURED)`. `fat-alive`, the other seven rows and `append-missing (directory)` all held |
| **K-FE2** | **CUT, and it is the GREEN CONTROL** — `name-missing` FAILs at `'load error'`, probe rc **1**, tally `7/8 scored (8 rows, 0 NOT MEASURED)` — **the row IS scored**, and `name-alive` holds green on both instruments |
| **K-FE3** | **CUT** — a 16384-byte all-`$00` `build/disk.rom` reds `fat-alive` (`'load error'`), probe rc **2**, `NOT MEASURED (precondition failed)`, nothing scored |

🎯 **K-FE1 against K-FE2 is the whole slice in two rows.** Both break `NAME`.
K-FE1 breaks the *verb* → rc 2, the row unscored. K-FE2 breaks the *disposition*
→ rc 1, the row scored red. If `name-alive` had also reddened under K-FE2 the
control would be firing on "anything about `NAME` changed" and the two exit
codes would carry no information. It did not.

### 6.4 The same knife, before and after — the number this slice exists to change

D-DKNAME's K-NAMECTL and this slice's K-FE1 are the **same cut**
(`tnt_name_stamp`'s `call fatprim_write_sector` → `call read_sector`). What this
gate reported:

| | `disk_probe_fat_error_disposition.py` under a `NAME` that renames nothing |
|---|---|
| before D-FEVERB | 🔴 **`8/8` ALL PASS, exit 0**, precondition green |
| after D-FEVERB | ✅ **`7/7 scored, 1 NOT MEASURED`, exit 2**, both `name-alive` instruments red |

Measured on both sides of the change by the same runner, in the same session.

### 6.5 What is left open

* **Seven of the eight rows still have no verb-success control** (§4), printed by
  the gate on every run. `kill-missing` is the one that matters most — the other
  reference-exact row, same hole, one `CASES` tuple and one control away on the
  machinery this slice built. Filed in `TODO.md`, not widened into this slice.
* **`run-missing`'s reading is `'load error|Illegal function call in 3346'`** —
  two messages on one row, unchanged by this slice and unexplained by any
  document. Noted where it was seen; not investigated.
* **The knife-runner ROM-hash guard lives in the scratchpad, not the tree.**
  Every future knife runner needs it and will be written without it unless it
  becomes shared. Filed.
