<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-MOUNTROW — the mount arm of `KILL`/`NAME` gets a row, and two written-down predicted misses become cuts

Closes the `TODO.md` residual *"`KILL`/`NAME` at an unmounted or unreadable
volume has NO row"*, in the form D-DKNAME §3.4 sharpened it to.
Gate: `make fat-error-acceptance`
([`probes/disk/disk_probe_fat_error_disposition.py`](../probes/disk/disk_probe_fat_error_disposition.py)).

## 1. What was filed, and what this slice takes

Two slices filed the same hole from opposite sides. D-DSKMSG's **K-KILL2** and
D-DKNAME's **K-NAME2** each re-point their verb's mount arm at `df_notfound` and
redden **nothing** — written-down predicted misses
([[rule-gated-structurally-has-no-knife]]), because no row in this tree drives
either verb at an unmounted volume.

🎯 **The filed item has a cheap half and an expensive half, and this slice takes
only the cheap one** (D-DKNAME §3.4/§6.5). `fat-error-acceptance` is explicitly a
**self-check against zerobas's own pinned wording**, not an oracle differential,
so a row driving `KILL`/`NAME` at an **empty drive** and pinning zerobas's own
documented `load error` converts both knives into real cuts **with no reference
reading at all**. Changing what zerobas *prints* there is the expensive half: it
needs a reading, and that reading opens the `load error` wording divergence for
`LOAD`/`RUN`/`BLOAD`/`OPEN`/`APPEND`/`MERGE` — six verbs nothing has measured.
**Not opened here**, and §6 says so again.

## 2. The measurement this rests on, taken BEFORE the design

Scouted on `C-BIOS_MSX1_EU_REPACK_DISK` with **no `-diska` at all**:

| typed | empty drive | mounted (the existing row) |
|---|---|---|
| `KILL"A:NOSUCH.BAS"` | **`load error`** | `File not found` |
| `NAME"A:NOSUCH.BAS" AS "B.BAS"` | **`load error`** | `File not found` |
| `FILES"A:HI.TXT"` | `load error` | `HI      .TXT` (the precondition) |
| `PRINT 6*7` | **`42`** | `42` |

Two facts decide the whole design:

* 🎯 **The same verb answers DIFFERENTLY in the two configurations.** That is
  positive evidence available with no reference and no second instrument: a verb
  that always errors, and a dead disk ROM, both produce **one** answer.
* ⚠️ **The battery's own precondition cannot be reused in this boot.**
  `FILES"A:HI.TXT"` is exactly what an empty drive cannot do, so the mount group
  needs a different liveness control — `PRINT 6*7` → `42`, which needs no disk.

## 3. The change — a second group, never a widened first one

🔴 **THE EMPTY-DRIVE CONFIGURATION IS WHAT THIS BATTERY USED TO BE BY ACCIDENT,
AND THAT IS WHY THE GROUPS STAY SEPARATE.** Until 2026-07-31 the probe ran with
no disk mounted, so *every* case failed in `fat_mount` and never reached
`fat_find` — the battery measured the MOUNT miss while its docstring claimed the
FIND miss, and the two are indistinguishable by their answer (`load error`
either way). The fix was to mount a disk. Re-introducing an unmounted boot must
therefore be a **separate, explicitly-labelled group**, scored on its own terms;
folding these two rows into `CASES` would rebuild the exact conflation that
history removed.

* `MOUNT_CASES` — `(key, line, twin)` — run in a **second `run_cases` batch with
  no `diska`**, pinned to `WANT` (`load error`).
* `MOUNT_LIVE` — `PRINT 6*7` → `42`, injected first **in that same boot**, so a
  green liveness reading is evidence about the run the mount rows were measured
  in and not about a different one.
* Scoring order is load-bearing:
  1. tail ≠ pinned → **FAIL** (a real disposition regression, exit 1);
  2. tail = pinned **but the twin's tail is the same string** → **NOT MEASURED**
     (exit 2): the machine cannot distinguish mount-miss from find-miss, which is
     what a dead disk ROM looks like;
  3. otherwise **PASS**.

  ⚠️ The order is the difference between a cut and a shrug. Reversed, a knife
  that moves the mount arm to `File not found` would make both rows read alike
  and be reported as an *instrument fault* — exit 2 — when it is precisely the
  **regression** these rows exist to catch.
* The denominator line gains the mount group and its liveness control, printed
  every run ([[a-hand-listed-denominator-is-a-scope-claim]]).

**No `.asm` file is touched.** This is a TOOLING slice: the tree's behaviour is
already what the rows pin, and the deliverable is that two knives stop being
predicted misses.

## 4. Predicted GREEN, at exact values (fixed BEFORE the change)

| measurement | baseline `bc5d3f5` | predicted after |
|---|---|---|
| `fat-error-acceptance` | 8/8 scored + 5 dir checks, 8 of 8 verb controls | **8/8 FIND + 2/2 MOUNT scored**, 5 dir checks, 8 of 8 verb controls, 1 liveness control, exit 0 |
| all four ROM hashes | `2c630d3d…` / `6ea374de…` / `86ccd666…` / `7dfedd72…` | **all four UNCHANGED — no `.asm` file is touched** |
| walls | 3 / 165 / 3843 / 1540 | **unchanged** |
| `audit-citations` files swept | 719 | **720** — one new `.md` |
| `audit-citations` basic files / prov-bearing | 107 / 186 | **unchanged** — nothing under `basic/` moves |
| `injector-check` | 331 | **unchanged** — an existing probe is edited, no new file |
| `deadcode` main spans / seeds | 1566 / 287 | **unchanged** — no `.asm`, nothing under `sub/` or `tools/` |
| `unit-test` · `preflight-check` | 58 · 181/86/95/95/0 | **unchanged** |
| `dskmsg` / `diskbasic` / `runtail` / `castail` | 5/5 · 34/34 · 9/9 · 9/9+pin | **unchanged** |

⚠️ **THE ROM DOES NOT MOVE, SO MOST EMULATOR GATES CAN ONLY RE-DRIVE THE SAME
MACHINE.** Stated rather than folded into "corpus green": the gates below are run
because their *probes* or *counts* could move, not because the ROM could.

## 5. The knives — and two of them are the deliverable

The point of this slice is that **K-KILL2 and K-NAME2 stop being predicted
misses**, and a MISS here is now a failure of this slice rather than a fact about
the tree.

⚠️ **SAID PRECISELY, BECAUSE "WE RE-RAN THEIR KNIVES" WOULD BE AN OVERCLAIM.**
The two cuts below are sited where each verb's mount arm decides its MESSAGE.
D-DSKMSG's K-KILL2 as actually written sits elsewhere — it deletes the
**tenant's** mount separation (`tnt_kill`'s `call fat_mount / jp c,tf_ioerr`),
which is the residual's own "filed 0 B fix". That original is therefore run too,
as **K-KILL2-orig**. D-DKNAME's K-NAME2 as filed is the one that cannot be built
at all (§6.3), so for `NAME` the claim is: the filed siting is unbuildable, and
the equivalent cut at `nm_fail`'s body reds the new row.

| # | cut (byte-neutral) | predicted RED | predicted GREEN survivors | rc |
|---|---|---|---|---|
| **K-KILL2** | `basic/files.asm`: `do_kill`'s mount arm → `df_notfound` | **`kill-nodisk`** (reads `File not found`, ≠ pinned) | `name-nodisk`, all 8 FIND rows, every verb control, the liveness row | 1 |
| **K-NAME2** | `basic/files.asm`: `do_name`'s `jr c,nm_fail` → `jr c,nm_notfound` | **`name-nodisk`** | `kill-nodisk`, all 8 FIND rows, every control | 1 |
| **K-KILL2-orig** | `sub/dirverb.asm`: `tnt_kill`'s `call fat_mount / jp c,tf_ioerr` **deleted** — D-DSKMSG's cut exactly as filed | **`kill-nodisk`** | everything else | 1 |
| **K-LIVE** | the liveness row's want `42` → `43` — the group's own control lies | **nothing reddens; the MOUNT GROUP reports NOT MEASURED**, exit 2 | the 8 FIND rows still scored | 2 |
| **K-TWIN** | the contrast clause deleted (score (1) and (3) only) | **nothing** — a declared PREDICTED MISS on a green tree | everything | 0 |

⚠️ **K-KILL2 and K-NAME2 must each red exactly ONE row.** Both reddening, or
either reddening the other's row, would mean the two mount arms are not
separately wired — the same separation D-CASTAIL's A1/A2 pair established for the
tape sites.

⚠️ **K-TWIN IS A DECLARED PREDICTED MISS AND IS RUN ANYWAY.** The contrast clause
only fires when the two configurations agree, which on a green tree they never
do — so on *this* tree deleting it changes nothing. Its value is against a dead
disk ROM, which is not a state a knife on `files.asm` can produce. The honest
statement is that the clause is gated by **K-KILL2 + K-NAME2 reaching exit 1
rather than exit 2**, which is the scoring-order claim in §3 — that is what the
two real knives verify about it.

## 6. As-built

### 6.1 Predictions, scored

| prediction | outcome |
|---|---|
| `fat-error-acceptance` 8/8 FIND + 2/2 MOUNT + 5 dir checks + 8 of 8 verb controls, exit 0 | ✅ exactly that |
| all four ROM hashes UNCHANGED | ✅ `2c630d3d…` / `6ea374de…` / `86ccd666…` / `7dfedd72…`, verified by the knife runner on every iteration |
| walls unchanged | ✅ 3 / 165 / 3843 / 1540 |
| `audit-citations` 719 → **720** files swept | ✅ exact |
| `audit-citations` basic 107 / **186** unchanged | ✅ exact — the count D-CASTAIL missed one slice ago, predicted correctly here by asking whether anything under `basic/` moves (nothing does) |
| `injector-check` **331** unchanged | ✅ exact — an existing probe is edited, no new file |
| `deadcode` **1566 / 287** unchanged | ✅ exact |
| `unit-test` 58 · `preflight-check` 181/86/95/95/0 · `latch-check` 16/16 | ✅ unchanged |

⚠️ **THE ROM IS BYTE-IDENTICAL, SO MOST EMULATOR GATES WERE NOT RUN, AND THAT IS
STATED RATHER THAN FOLDED INTO "CORPUS GREEN".** Run: `unit-test`,
`audit-citations`, `preflight-check`, `injector-check`, `latch-check`,
`deadcode`, `fat-error-acceptance` — the ones whose probe or counts could move.
**Not run:** `dskmsg` · `diskbasic` · `runtail` · `castail` · `lnblank` ·
`logicops` · `float` · `linemax` · `dexp5` · `editverb` · `lptverb`. Every one of
them would re-drive a machine whose four ROMs hash identically to the ones they
were last green against, so a green from them would be evidence about openMSX,
not about this change.

### 6.2 🎯 The knives — 5 designed, 5 run, each TWICE, both rounds identical

| # | cut | rc | RED | note |
|---|---|---|---|---|
| **K-KILL2** | `do_kill`'s mount arm `jp nz,load_error` → `jp nz,df_notfound` | 1 | `kill-nodisk` | 🎯 **was a predicted MISS in D-DSKMSG** |
| **K-NAME2** | `nm_fail`'s body `jp load_error` → `jp df_notfound` | 1 | `name-nodisk` | 🎯 **was a predicted MISS in D-DKNAME** |
| **K-KILL2-orig** | `tnt_kill`'s `call fat_mount / jp c,tf_ioerr` deleted (D-DSKMSG's cut **as filed**) | 1 | `kill-nodisk` | 🎯 **the filed miss, at its own site, is now a cut** |
| **K-LIVE** | the group's liveness want `42` → `43` | 2 | `mount-live`, and both mount rows NOT MEASURED | the group's control is load-bearing |
| **K-TWIN** | the contrast clause → `differs = True` | 0 | nothing — the declared predicted miss | ROMs verified UNMOVED |

Each reddened **exactly one** row, so the two mount arms are separately wired.
Both rounds identical; the tree hashed back to baseline.

### 6.3 🔴 K-NAME2 could not be built as filed, and the reason is reusable

D-DKNAME filed the cut as `jr c,nm_fail` → `jr c,nm_notfound`. **That build
fails** — and not in the assembler, which is the failure mode `dev-workflow.md`
§Knives already warns about. `nm_fail` has exactly one reference, so re-pointing
it **orphans the label**, and `make` stops in `check_dead_code.py`:

```
FAIL: 1 unreachable span(s)
  [main] nm_fail    basic/files.asm   0x7091 PAGE1  ~4 B
```

A knife aimed at the *message* gate was refused by the *dead-code* gate, and a
build that fails is a knife that scored nothing. Re-sited at the label's **body**
(`jp load_error` → `jp df_notfound`) it is byte-neutral, orphans nothing, and
tests the identical claim. Added to `dev-workflow.md` §Knives.

### 6.4 🔴 And the runner hit the preflight guard, which is the same rule generalised

K-LIVE aborted with `tally=False, precond=False` — an empty report — while the
same cut run by hand was fine. Cause: after K-NAME2 the runner restored
`basic/files.asm`, which **touches its mtime**, so the ROMs were stale w.r.t.
sources and `omsx_preflight` **correctly refused** the next probe run. The runner
read that refusal as a truncated report.

`dev-workflow.md` §Knives already says *"Build BEFORE taking the baseline —
restoring a snapshot touches mtimes and `omsx_preflight` then correctly
refuses."* The rule is right and its scope was too narrow: it applies **before
every probe run that follows a restore**, not only before the baseline. Fixed in
the runner, and the general form is now in `dev-workflow.md`.

### 6.5 🔴 One prediction miss, and it is the SECOND slice running with the same shape

§5 predicted K-LIVE would redden **nothing**. It reddens `mount-live` — the row
the knife cuts. The substance was right (rc 2, both mount rows NOT MEASURED); the
RED set was under-enumerated by exactly the row being targeted.

**D-CASTAIL made the identical mistake one commit earlier** (K-ASC was predicted
to red four rows and reddened five — the fifth being the pinned row whose
subject the cut moved). Twice in a row, the omission is the row the knife acts
on most directly, because a control or a pin gets filed mentally as *apparatus*
rather than as *a scored row*. Recorded as
[[a-knife-reddens-its-own-target-row]].

## 7. Out of scope, said explicitly

* **What zerobas PRINTS at an unmounted volume.** These rows pin `load error`,
  zerobas's own documented wording for the whole no-disk / mount / I-O class.
  Moving it needs a CF-3300 reading and opens six unmeasured verbs. Still filed.
* **An UNREADABLE volume** (a mounted but corrupt image) as distinct from an
  empty drive. The filed item names both; only the empty drive is measured here,
  and the row keys say `nodisk` rather than `nomount` so the narrower claim is
  the one written down.
* **The `fat_find` / `fat_delete` I-O conflation.** Separating an I-O error
  *inside* the primitive from "nothing matched" still needs a status out of the
  primitive; unchanged by this slice.
