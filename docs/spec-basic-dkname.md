<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-DKNAME — R-DK2: `NAME`'s missing-old-file message, and the arm that had to be split first

Measurement: [`dskmsg-msx1-characterization.md`](dskmsg-msx1-characterization.md)
§2 (**R-DK2**), taken on the National CF-3300 on 2026-08-07 by D-DSKMSG.
Predecessor: [`spec-basic-dskmsg.md`](spec-basic-dskmsg.md) §4.5 + §6.6 (the
residual, and the three reasons it was not acted on then).

R-DK2 is the one reading D-DSKMSG took and deliberately did **not** act on:

> `NAME"NOSUCH.BAS" AS "ZZ.BAS"` → **`File not found`** on the CF-3300.
> zerobas answers **`load error`**.

Two of the three reasons for deferring it were about *evidence*, and both are
spent — the reading for `NAME` itself now exists, and it is this slice's whole
subject rather than a neighbour's. The third was about the **code**, and it is
the work:

🔴 **`nm_fail` (`basic/files.asm`, in `do_name`) is a SHARED EXIT** for the
`fat_mount` failure *and* the `fat_find` miss — both reach it via `jr c,nm_fail`.
Re-pointing it at `df_notfound` would re-point the mount failure too. That is the
same conflation D-DSKMSG found in `do_kill`
([[a-filed-zero-byte-fix-can-hide-a-conflation]] — a fix priced by its edit is a
claim about the call graph).

⚠️ **And the conflation goes ONE LEVEL DEEPER than the residual said.** §2.2.

---

## 1. The wall, measured from clean at `0238de5`

`rm -rf build && make basic-reloc` ([[measure-the-wall-from-clean]]). All four
walls print on every run (`tools/check_reloc.py` + `tools/check_sub_walls.py`,
D-SUBWALL), so this table is a **transcript**, not a figure copied out of a
document ([[a-prediction-copied-into-the-result-column]]):

| region | free |
|---|---|
| main page-0 low | **3 B** |
| main page 1 | **190 B** |
| sub page 0 | 3843 B |
| sub page 1 | 1540 B |

🔴 **The two main regions are ONE co-mapped budget of 193 B**, not two of 3 and
190. Everything this slice adds lands in **page 1** (`basic/files.asm` is
included after `__MEAS_LOW_END` in `basic/main.asm`), so the low region is
untouched by construction.

Other gate figures at the baseline, run rather than grepped: closure
`122+4 / 718+15 / 582+41`; `preflight-check` 181 sites / 86 exempt / 95 require /
95 guarded / 0 UNGUARDED; `audit-citations` **711** files swept; `injector-check`
**329**; `deadcode` main 1564 spans / **287** seeds, sub 1512 / 102, 0 dead
(+1 allowlisted). ROM hashes: `disk.rom 2c630d3d…`, `sub.rom 6ea374de…`,
`basic-reloc.rom 48d04294…`, `zerobas-main-eu.rom 857d1d51…`.

### 1.1 Files this slice ADDS, against the sweep filters

* `docs/spec-basic-dkname.md` — `.md`, swept. **+1.**
* No new probe, no new fixture: `basic_probe_dskmsg.py` and
  `disk_probe_fat_error_disposition.py` both already exist and both already
  carry a `NAME` row.

⇒ `audit-citations` **711 → 712**; `injector-check` unchanged at **329**;
`preflight-check` unchanged at **181/86/95/95/0**.

⚠️ **Seed prediction, stated as a number to be checked.** `check_dead_code.py`
seeds the main walk with every identifier appearing anywhere under `sub/` and
`tools/`, **comments included** — which is how D-DSKMSG's prediction of 286 came
back 287 (its own `sub/dirverb.asm` comment named the main label `df_notfound`,
§6.2 there). **This slice touches no file under `sub/` or `tools/` at all**, so
seeds stay **287** and sub spans/seeds stay **1512 / 102**. Main spans go
**1564 → 1565**: one new label, `nm_notfound`, and a span is exactly "a label to
the next label in the same file".

---

## 2. The call graph, which is what prices the fix

### 2.1 The shared exit

`basic/files.asm`, `do_name`, at `0238de5`:

```
                push    hl                  ; guard the text cursor
                call    fat_mount
                jr      c,nm_fail           ; (a) no disk / mount / I-O
                ld      hl,DISK_FCB_NAME
                call    fat_find
                jr      c,nm_fail           ; (b) old not found
                …
nm_fail:        pop     hl
                jp      load_error
```

(a) and (b) are **two dispositions with one exit**. R-DK2 measures (b) only.
(a) is the quarantined class `basic/PROVENANCE.md` records for the whole no-disk
/ mount / I-O surface, and nothing has ever measured what the CF-3300 says there.
So the fix is an **arm split**, not a target swap: give (b) its own exit and
leave (a) exactly where it is.

Unlike `do_kill`, no sub-ROM change is needed. `NAME`'s tenant
(`tnt_name_stamp`) is the **stamp only**; `fat_mount` and `fat_find` are both
main-resident in the head (spec-evict-diskfile-cluster §12: NAME is a
"stamp-only" split). The two dispositions are therefore already separate *at the
call site* — they were merged only by the jump target.

### 2.2 🔴 AND THE CONFLATION IS DEEPER THAN THE RESIDUAL SAID — `fat_find`'s OWN Cy

The filed item stops at "`nm_fail` is a shared exit". It is, and splitting it is
not sufficient, because **arm (b) is itself two dispositions.**
`basic/fat-prim-body.inc` documents `fat_find` as:

```
;   out: Cy = 0 found  -> FAT_FIRSTCLUS, FAT_FILESIZE set; Cy = 1 not found / error
…
                call    read_sector
                ret     c                   ; propagate FDC error
```

So `Cy=1` out of `fat_find` means **"the root-directory scan completed and
matched nothing"** *or* **"a `read_sector` failed mid-scan"**. Pointing (b) at
`df_notfound` therefore moves **two** dispositions to ERR 53, and only one of
them is measured.

**It is accepted, and named, rather than hidden** — for the same reason and with
the same shape as `do_kill`'s residual (`spec-basic-dskmsg.md` §4.2: *"an I-O
error inside `fat_delete` after the mount succeeded and before anything was
deleted still returns C=0 and reads as 'nothing matched'"*). Separating it needs
a status **out of `fat_find` itself** — a primitive-layer change touching every
caller in the tree (`LOAD`, `RUN`, `BLOAD`, `MERGE`, `OPEN`, `NAME`, and
`fat_delete`'s own body), which this slice does not make.

🎯 **What the split DOES buy is the half a target swap would have broken.** The
mount failure — the one with a documented, quarantined answer and no reading —
keeps `load error`. `FILES`/`LFILES` are the sibling that separates all three
(`tnt_files`: `jp c,tf_ioerr` on the mount **and** on every `read_sector`), and
`NAME` after this slice lands in `KILL`'s class, not `FILES`'s. Written down so
that the divergence register still describes the tree.

### 2.3 The filed cost was ≈5 B. Measured against the code it is **4**

```
nm_notfound:    pop     hl                  ; 1 B — balance the guarded cursor
                jp      df_notfound         ; 3 B — ERR 53 through raise_error
```

and `jr c,nm_fail` → `jr c,nm_notfound` at the `fat_find` site, which is
**byte-neutral** (2 B either way, and `nm_notfound` is 31 B ahead of it — well
inside `jr` range). `nm_fail` and `nm_fail2` are untouched, and stay two labels
with the same body because after this change they name **different
dispositions** (the mount failure and the tenant's I-O error), not one.

**+4 B of main page 1** (190 → 186; the co-mapped budget 193 → 189).
**0 B of sub-ROM**, and `basic/files.asm` is not in the sub build
(`sub/sub.asm`'s include list), so `sub.rom` should not move either — a sharper
hash prediction than D-DSKMSG could make.

---

## 3. The gate

### 3.1 The row moves from CHARACTERIZE to CASES, and the exclusion line goes with it

`probes/basic/basic_probe_dskmsg.py` prints `dsk-namenone` every run as
`[CHARACTERIZATION, not gated — DIVERGES]`, followed by a `NOT GATED:` line
explaining why. Both go. **A list of exclusions that contains a non-exclusion
stops being read as a list of holes** — the same disposition D-LFILES applied to
`lptverb`'s printed `NOT GATED` line when the last `lfl-` row was gated.

`CHARACTERIZE` becomes empty and is **deleted with its printing block** rather
than left as an empty list: an empty list is a hole in the report that nothing
reports.

### 3.2 🔴 A NEW POSITIVE CONTROL, because every subject row here still expects an ERROR

`make fat-error-acceptance` scored **8/8 on a 16384-byte all-`$00`
`build/disk.rom`**, and on five further corruptions — red in 0 of 6
([[gate-whose-answer-is-an-error-passes-a-dead-subject]]). A gated
`dsk-namenone` is squarely in that class: a build whose `NAME` was a no-op that
always errored would score it green.

The probe's two existing controls do **not** cover it. `dsk-ctl` proves the
volume mounts and `FILES` finds a file; `dsk-killhit` proves `KILL` reached the
FAT layer and succeeded. Neither says anything about `NAME` — under a `NAME`
that silently renames nothing, both stay green and `dsk-namenone` stays green
too, because it errors, which is the want.

So a third control, on the same mounted image, in the same invocation,
asserted on **positive text** rather than on the absence of an error string:

| control | types | asserts |
|---|---|---|
| `dsk-namehit` | `NAME"HI.TXT" AS "BYE.TXT"` then `FILES` | `BYE` **and** `TXT` **and** `TEST` **present**, `HI      .TXT` **absent** |

The survivors (`TEST`) are what make it positive evidence: *"`HI` is gone"* alone
is satisfied by a machine that cannot list a directory at all — the same
reasoning `dsk-killhit`'s docstring already carries, applied to the verb it was
not applied to. Knife **K-NAMECTL** (§5) is the row that proves this control is
not vacuous.

⚠️ `dsk-namehit` **WRITES**, so it joins `WRITES` and gets a private copy of the
image. Boot-per-case reboots the machine but keeps handing openMSX the same file;
shared with the read-only rows it would rename `HI.TXT` out from under `dsk-ctl`
on a `--repeat 2` second pass.

⚠️ `anchor_for` derives the anchor from this probe's own `VERBS` list, `NAME`
included, so `dsk-namehit` anchors on its **`NAME` line** and the reading spans
everything the trailing `FILES` printed. Borrowing `lptverb`'s list would have
anchored on `FILES` and hidden the subject — the blindness D-EDITVERB documented
([[readout-blind-to-its-own-subject]]). Nothing to change: the list already
starts `KILL, NAME`.

### 3.3 The `fat-error` pin moves in the same commit as the code

`probes/disk/disk_probe_fat_error_disposition.py` already takes a per-case
`want` (the third tuple element, added by D-DSKMSG for `kill-missing`).
`name-missing` (`NAME"A:NOSUCH.BAS" AS "B.BAS"`) becomes `File not found` and is
printed with `[reference-exact: …]`. **The other six stay `load error`** — they
are the quarantined divergence and nothing here measured them.

⇒ two of the eight rows now carry their own want. The battery is still 8/8.

### 3.4 What this slice does NOT do, decided explicitly

**`KILL`/`NAME` at an unmounted or unreadable volume stays filed.** It has no
row; D-DSKMSG's K-KILL2 is the written-down predicted miss that proves it, and
K-NAME2 below reproduces that verdict for `NAME`. Keeping `load error` there is
by design. Acting on it needs a new reference reading, and that reading opens the
whole `load error` wording divergence for `LOAD`/`RUN`/`BLOAD`/`OPEN`/`APPEND`/
`MERGE` — six verbs nothing has measured. Out of scope, left in `TODO.md`.

🎯 **But the filed item can be SHARPENED, and is** (§7.4): the *reference* half
needs a reading, and the *zerobas* half does not. `fat-error-acceptance` is
explicitly a **self-check against zerobas's own pinned wording**, not an oracle
differential — so a row driving `NAME`/`KILL` at an **empty drive** and pinning
zerobas's own documented `load error` would need no reading at all, and would
convert K-NAME2/K-KILL2 from predicted misses into real cuts. That is a strictly
better description of the residual than "it needs a reading", and it is recorded
in `TODO.md` rather than done here.

---

## 4. Predicted GREEN, at exact values

1. `make dskmsg-acceptance` = **5/5 gated rows agree**, zero characterization
   rows, and **no `NOT GATED:` line printed at all**.
   Row values, identical on `cf3300` and `zb`:
   * `dsk-ctl` = `HI      .TXT`
   * `dsk-killhit` = `FILES / TEST    .BIN PROG    .BIN PROG    .BAS / PROG2   .BAS`
   * `dsk-namehit` — the `FILES` echo, then the five entries with `BYE     .TXT`
     in `HI      .TXT`'s directory slot and `HI      .TXT` **absent**
   * `dsk-killnone` = `File not found`
   * `dsk-namenone` = **`File not found`** ← the subject
2. `make fat-error-acceptance` = **8/8 + directory check**, with `name-missing`
   printing `-> 'File not found'   [reference-exact: 'File not found']` beside
   `kill-missing`'s, the PRECONDITION green, and the other six at `load error`.
3. `make diskbasic-acceptance` = **34/34 ALL CONVERGED**. `disk_probe_name.py`
   is one of the 34 and asserts a byte-identical image after a **successful**
   `NAME`, which this slice does not touch.
4. Walls, from clean: main low **3 B**, main page 1 **186 B**, sub page 0
   **3843 B**, sub page 1 **1540 B**.
5. Closure `122+4 / 718+15 / 582+41` unchanged (`df_notfound` is main page 1,
   and so is `do_name`).
6. `deadcode` main **1565** spans / **287** seeds, sub 1512 / 102, **0 dead**
   (+1 allowlisted).
7. `preflight-check` 181/86/95/95/0; `injector-check` **329**;
   `audit-citations` **712** files.
8. `unit-test`, `latch-check`, `lnblank-acceptance REPEAT=2`,
   `lnblank-say-acceptance`, `logicops-acceptance`, `float-acceptance`,
   `linemax-acceptance`, `dexp5-pin`, `editverb-acceptance`,
   `lptverb-acceptance` (**44/44**) all unchanged.
9. **Two of the four ROM hashes move, and two do NOT.** `basic-reloc.rom` and
   `zerobas-main-eu.rom` change; **`disk.rom` stays `2c630d3d…`** (built from
   `basic/`-independent sources) and **`sub.rom` stays `6ea374de…`** (this slice
   touches no file in the sub build's include list). If `sub.rom` moves, §2.3's
   reading of the include list is wrong and the as-built says so.

---

## 5. The knives

Subject: `probes/basic/basic_probe_dskmsg.py --gate --sides cf3300,zb` and
`probes/disk/disk_probe_fat_error_disposition.py`, both invoked **directly** —
never `make <gate>`, because `make` exits 2 for any failed recipe and would
flatten a tree fault into an instrument fault ([[injjudge-slice]]). Restore
point: a **scratchpad snapshot** taken after the change and before the first cut,
never `git checkout --` ([[knife-cleanup-restores-from-head]]). The runner
**builds before it takes its baseline** (restoring a snapshot touches mtimes and
`omsx_preflight` correctly refuses a stale ROM), captures the baseline through
the probe's own parse path so a short baseline refuses the run, and **aborts on a
failed build rather than scoring** ([[stale-machine-reads-as-unimplemented]]).
**Every knife is run TWICE.**

⚠️ All three cuts are **byte-neutral** (a `jr` target change, and a `call`
target change), so nothing moves and no nearby `jr` can go out of range —
D-DSKMSG lost two knife sitings to exactly that (§6.4 there).

| # | cut | predicted RED | predicted GREEN |
|---|---|---|---|
| **K-NAME1** | `basic/files.asm`: the `fat_find` arm's `jr c,nm_notfound` → `jr c,nm_fail` — undo the split, i.e. the pre-slice tree | `dsk-namenone` (probe rc 1, `zb` back to `load error` beside cf3300's `File not found`); `fat-error`'s `name-missing` alone | `dsk-ctl`, `dsk-killhit`, `dsk-namehit`, `dsk-killnone`; `fat-error`'s other seven rows, its PRECONDITION and its directory check |
| **K-NAME2** | `basic/files.asm`: the `fat_mount` arm's `jr c,nm_fail` → `jr c,nm_notfound` — i.e. **the target swap §2.1 exists to prevent** | ⚠️ **NOTHING — a PREDICTED MISS, written down as one.** No row in this tree drives `NAME` at an unmounted or unreadable volume (§3.4), so the arm the split protects is unexercised | everything, on both instruments |
| **K-NAMECTL** | `sub/dirverb.asm`: `tnt_name_stamp`'s `call fatprim_write_sector` → `call read_sector` — the dir sector is re-read instead of written back, so **`NAME` reports success and renames nothing** | `dsk-namehit` (probe rc **2** — a failed positive control means nothing below it was measured) | `dsk-ctl`, `dsk-killhit`, `dsk-killnone`, `dsk-namenone`; all eight `fat-error` rows, its PRECONDITION and its directory check |

🎯 **K-NAMECTL is the knife this slice exists to run.** It is the dead-subject
question asked directly: under a `NAME` that silently does nothing,
**`dsk-namenone` stays GREEN** — it still prints `File not found`, for a reason
that has nothing to do with the disposition under test. If `dsk-namehit` does not
go red there, the new control is decoration and the gated row is measuring
`NAME`'s existence, not its no-match message.

⚠️ **K-NAME2's green will be evidence, not reassurance** — the disposition
D-DSKMSG gave K-KILL2, D-LFILES gave K7 and D-LPTVERB gave K6
([[rule-gated-structurally-has-no-knife]]). It says out loud that §2's separation
rests on the call graph plus the divergence register, and §3.4 records what it
would take to change that.

---

## 6. As-built

### 6.1 Predictions, scored

| § | predicted | measured | |
|---|---|---|---|
| 4.1 | `dskmsg-acceptance` **5/5**, no characterization rows, no `NOT GATED:` line | **5/5 gated rows agree**; `dsk-namenone` = **`File not found`** on both sides; nothing printed below the tally but the SIDES note | ✅ |
| 4.1 | `dsk-namehit` = the five entries with `BYE     .TXT` in `HI      .TXT`'s slot | `FILES / TEST    .BIN BYE     .TXT PROG    .BIN / PROG    .BAS PROG2   .BAS`, identical on `cf3300` and `zb` | ✅ |
| 4.2 | `fat-error-acceptance` 8/8 + directory, `name-missing` reference-exact | **8/8 ALL PASS**, `name-missing -> 'File not found'   [reference-exact: 'File not found']` beside `kill-missing`'s, PRECONDITION green, other six at `load error` | ✅ |
| 4.3 | `diskbasic-acceptance` 34/34 | **34/34 ALL CONVERGED** | ✅ |
| 4.4 | low **3 B**, page 1 **186 B**, sub p0 **3843 B**, sub p1 **1540 B** | exactly those, from clean | ✅ |
| 4.5 | closure `122+4 / 718+15 / 582+41` | unchanged | ✅ |
| 4.6 | `deadcode` main **1565** / **287**, sub 1512 / 102, 0 dead | exactly those | ✅ |
| 4.7 | preflight 181/86/95/95/0, injector **329**, citations **712** | exactly those | ✅ |
| 4.8 | the untouched gates | `unit-test` 58 files, `latch-check` 16/16, `lnblank` **539/539** at `REPEAT=2`, `lnblank-say` 204/204, `logicops` 193/193, `float` ALL PASS, `linemax` 60/60, `dexp5` 16 ALL PASS, `editverb` 61/61, `lptverb` **44/44** | ✅ |
| 4.9 | `basic-reloc.rom` + `zerobas-main-eu.rom` move; **`disk.rom` AND `sub.rom` do not** | `disk.rom 2c630d3d…` and **`sub.rom 6ea374de…` both byte-identical**; `basic-reloc.rom 48d04294… → 849d661e…`, `zerobas-main-eu.rom 857d1d51… → 4952fb9e…` | ✅ |

🎯 **The seed prediction held, and for the reason §1.1 gave.** Main seeds stayed
**287** because this slice touches no file under `sub/` or `tools/` — the
mechanism that surprised D-DSKMSG (a comment naming a main label) could not fire.
Main spans went 1564 → **1565**: one new label, `nm_notfound`, one new span.
Fourth slice running that this number was predicted rather than assumed, and the
first in three where it came back right.

### 6.2 The cost: filed ≈5 B, measured **4 B**, and the low region never in play

`+4 B of main page 1` (190 → **186**; the co-mapped budget 193 → 189), `0 B` of
sub-ROM. `basic/files.asm` is included after `__MEAS_LOW_END` in
`basic/main.asm`, so the 3 B low region was never a constraint — checked before
the edit rather than discovered after it.

The `sub.rom` half of prediction 4.9 is the one worth keeping: `basic/files.asm`
is not in `sub/sub.asm`'s include list, so a `NAME` fix that would have needed a
tenant change (as `KILL`'s did) is distinguishable from one that does not **by a
hash**, not by an argument.

### 6.3 🎯 The knives — 3 designed, 3 run, each TWICE, both rounds byte-identical

| # | verdict |
|---|---|
| **K-NAME1** | **CUT** on both instruments, exactly the predicted set — `dsk-namenone` splits to `cf3300='File not found'  zb='load error'` (probe rc **1**) and `fat-error`'s `name-missing` alone goes `FAIL … 'load error'`. All three controls, `dsk-killnone`, the other seven `fat-error` rows, its PRECONDITION and its directory check **held** |
| **K-NAME2** | **PREDICTED MISS, as filed** — re-pointing the `fat_mount` arm at `df_notfound` (the target swap §2.1 exists to prevent) moved **NOTHING**, on either instrument, in both rounds. rc 0 / rc 0 |
| **K-NAMECTL** | **CUT** — `dsk-namehit` reads `… HI      .TXT …` (the rename never happened) and the probe exits **rc 2**. §6.4 is what it found |

### 6.4 🔴 K-NAMECTL is the finding, and it is bigger than the row it reds

Under a `NAME` that reports success and renames nothing:

* **`dsk-namenone` still reads `File not found`, on both sides.** Its *value* is
  untouched by a provably broken `NAME` — the subject row cannot see its own
  subject die. That is the whole of
  [[gate-whose-answer-is-an-error-passes-a-dead-subject]], reproduced on the row
  this slice was asked to gate.
* **`dsk-ctl` and `dsk-killhit` also hold**, byte-for-byte. Neither pre-existing
  control executes `NAME` at all, so a `NAME` row gated behind them would have
  been gated behind nothing.
* **`make fat-error-acceptance` scores 8/8 ALL PASS, exit 0**, with its own
  PRECONDITION green — a second, independent instrument reporting a clean run
  over a broken `NAME`. Its `name-missing` row passes for a reason unrelated to
  the disposition it names.

Only `dsk-namehit` reds, and the probe then correctly refuses to score the four
rows below it (`(not scored)`, exit **2** = the instrument was broken, not the
tree). ⇒ the control is not decoration; it is the only thing in the tree that
can see this build.

⚠️ **And the honest reading of the same result from the other side:** K-NAMECTL
says `fat-error-acceptance` still has no positive control for `NAME`. Its one
PRECONDITION (`FILES"A:HI.TXT"`) proves the FAT layer is alive, which is what it
was written for, but its `name-missing` row is now reference-exact and rests on
a control that never runs the verb. Filed in `TODO.md` rather than fixed here —
adding a *writing* row to that battery changes what it mounts and is a separate
piece of work.

### 6.5 K-NAME2's green, stated rather than smoothed over

No row in this tree drives `NAME` at an unmounted or unreadable volume, so the
arm split in §2 rests on the **call graph plus the divergence register**, not on
a measurement — the disposition D-DSKMSG's K-KILL2 got, one verb over
([[rule-gated-structurally-has-no-knife]]). It is now confirmed empirically for
`NAME` too rather than only argued.

🎯 **§3.4 is what would change that, and it needs no reference reading.**
`fat-error-acceptance` is explicitly a self-check against zerobas's own pinned
wording. A row driving `NAME`/`KILL` at an **empty drive**, pinned to zerobas's
own documented `load error`, would turn K-NAME2 and K-KILL2 from predicted
misses into real cuts without measuring the CF-3300 at all. That is a sharper
statement of the filed residual than *"it needs a reading"*, and it is what
`TODO.md` now says.

### 6.6 ⚠️ One apparatus refusal, by a guard this project already had

`make latch-check` has no `repack-machine` prerequisite, so running the corpus
straight after `rm -rf build` hit `omsx_preflight`:
`APPARATUS FAILURE — NOTHING WAS MEASURED`, naming both missing ROMs and the fix,
at **exit 2**. Correct behaviour and no wrong reading — a probe booted against
that machine would have reported the absence of the ROM as the absence of the
feature. Re-run after `make repack-machine`: **16/16**. Recorded because it is
the third slice running in which a preflight/stale-artifact guard fired during
routine work ([[stale-machine-reads-as-unimplemented]]).

### 6.7 What is left open

* **`KILL`/`NAME` at an unmounted or unreadable volume** — still no row;
  K-NAME2 joins K-KILL2 as a written-down predicted miss. §3.4/§6.5 say what
  would close it cheaply, and `TODO.md` carries it.
* **An I-O error during `fat_find`'s root-directory scan now reads as
  `File not found` for `NAME`** (§2.2) — the second half of arm (b), accepted
  and named. `KILL`'s equivalent (an I-O error inside `fat_delete`) has the same
  disposition. Separating either needs a status out of the primitive.
* **`fat-error-acceptance` has no positive control that executes `NAME`**
  (§6.4).
* **The `load error` wording divergence for `LOAD`/`RUN`/`BLOAD`/`OPEN`/
  `APPEND`/`MERGE`** — six verbs, six unmeasured messages, untouched here.
