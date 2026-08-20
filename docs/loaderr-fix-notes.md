<!-- Copyright (c) 2026 Joost Yervante Damad -- SPDX-License-Identifier: 0BSD -->

# D-LOADERR-FIX — a missing file raises `File not found`, at five verbs, for 16 bytes

Shipped 2026-08-20, the same day
[`loaderr-msx1-characterization.md`](loaderr-msx1-characterization.md) measured
the class. **16 bytes of main page 1 (22 → 6 B free).** No other wall moved.

---

## 1. What changed

`LOAD"missing"`, `RUN"A:missing"`, `MERGE"missing"`, `OPEN"missing"FOR INPUT`
and `OPEN"missing"FOR APPEND` now **raise ERR 53 `File not found`** and stop,
matching both references. They printed a lowercase `load error` and carried on.

🔴 **`BLOAD` IS NOT FIXED AND ITS ROWS STAY UN-GRADUATED.** Its loader is the
sub-ROM page-1 tenant, where the shared `fatio-body.inc` binds to the REAL
sub-side primitives and `DISKOP_OP` is never written. It reports through
`BL_STAT` and needs a value of its own. `dsk-bloadmode` additionally needs a
second face (`Bad file mode`) that no arm in the tree produces.

---

## 2. 🎯 The split needed no new status, because one already existed

`fatprim_bounce` ([`basic/fat.asm`](../basic/fat.asm)) writes `DISKOP_OP` with
the selector of the primitive it is about to marshal. `fat_io_open` and
`fat_io_append` reach the disk through exactly two of them — `fat_mount` then
`fat_find` — so **`DISKOP_OP == DISKOP_SEL_FAT_FIND` on a failure means
precisely "mounted fine, the name is not there"**. One shared helper:

```
df_or_loaderr:  ld      a,(DISKOP_OP)
                cp      DISKOP_SEL_FAT_FIND
                jp      z,df_notfound       ; ERR 53, raised
                jp      load_error          ; unchanged, printed, returns
```

11 bytes once; every consumer is a **0-byte retarget** of an existing `jp`. The
`dpl_nf` tail is the other 5.

⚠️ Each non-INPUT open mode was checked per path, not assumed: `FOR OUTPUT` uses
`fat_dir_create`, not `fat_find`; RANDOM's `fat_rand_open` is itself a tenant
selector whose internal find runs sub-side and never touches `DISKOP_OP`; a
successful open ends at `call fat_open`, so EOF paths read `FAT_OPEN`.

---

## 3. 🔴 The first draft broke the cassette, and an existing gate ran the knife

`dpl_err` — where the draft put the test — **is shared with the whole cassette
path**: `do_tape_prog` has nine `jp c,dpl_err` sites. No cassette op writes
`DISKOP_OP`, so a broken TAPE read whatever the last *disk* statement left
there, and when that was a `fat_find` the machine answered `File not found` to a
tape fault.

`castail-acceptance` caught it on the first run: `cas-run-brk` read
`vg8020='<load-failed>'  cf3300='<load-failed>'  zb='File not found'`.

🎯 **AN EXISTING GATE RAN A KNIFE NOBODY WROTE.** I had identified this exact
hazard for the `DISKSLOT_OK == 0` arm and guarded that one — and then missed the
same hazard on nine sites of a path I had not thought about. Guarding *an*
instance of a class is not guarding the class.

**The default is now inverted.** `dpl_err` is the safe tail; reading the stale
cell is **opt-in** at `dpl_nf`, reachable only from an arm whose CF came
directly out of a main-side `fat_io_open`. A future caller that lands on the
default gets the unchanged behaviour rather than a wrong message. Byte-neutral.

---

## 4. 🔴 Five pinned rows were a green oracle for the defect

`disk_probe_fat_error_disposition.py` pins zerobas's **own** wording, and five
of its rows asserted `load error` for exactly these verbs. They passed for as
long as the defect lived; **the fix is what turned them red.**

That is not a criticism of the pin, and the file says why: the pins were honest,
marked *"not measured on the reference"*, and the stated remedy was to measure.
That is what happened, so they moved in the same commit as the code — exactly as
`kill-missing`'s pin did in D-DSKMSG. `bload-missing` **keeps** `load error`,
because its reference reading exists and its fix does not, and a pin that drifts
on a neighbour's evidence stops being a pin.

`runtail-acceptance`'s per-side normalisation (`missmsg`) also collapsed: both
sides now normalise the same string. Kept rather than deleted, because BLOAD and
the cassette class still diverge.

---

## 5. Gates

`dskmsg-acceptance` **5/5 + 7 reported → 10/10 + 2 reported** (five rows
graduated the day they were filed). `castail-acceptance`, `fat-error-acceptance`,
`runtail-acceptance`, `namspc-acceptance` re-run. Knives in §6 of the
characterization.

### Knives — 5 of 5 EXACT

Baselines `dskmsg` 10/10, `castail` 31/31; ROM `e303acc6` before and after, so
no knife outlived its run. The discriminator is the **message** throughout: every
row here errored both before and after the fix, so a did-it-error gate is green
under the defect.

| knife | cut | gate | predicted red | measured |
|---|---|---|---|---|
| K-LE1 | `cp DISKOP_SEL_FAT_FIND` → `…FAT_MOUNT` (a VALUE) | dskmsg | all **5** | **EXACT** 5/10 |
| K-LE2 | `oo_fail`'s `jp df_or_loaderr` → `jp load_error` | dskmsg | `opennone`, `appnone` | **EXACT** 8/10 |
| K-LE5 | `mrg_ioerr`'s, same cut | dskmsg | `mergenone` | **EXACT** 9/10 |
| K-LE3 | `dpl_nf`'s `call df_or_loaderr` → `call load_error` | dskmsg | `loadnone`, `runnone` | **EXACT** 8/10 |
| K-LE4 | one cassette arm `jp c,dpl_err` → `jp c,dpl_nf` | **castail** | `cas-run-brk` | **EXACT** 30/31 |

K-LE2/K-LE5/K-LE3 between them separate all three consumers of the helper, so
no site rides on another's coverage. 🎯 **K-LE4 is the one worth keeping:** it
re-introduces the exact cassette regression the first draft shipped, and it
reddens a row in a battery this slice does not own. The guard is now pinned by a
knife rather than by my having remembered it.

🔴 **K-LE2's first draft matched TWO sites and the runner refused it** rather
than cutting whichever came first — `oo_fail` and `mrg_ioerr` both `jp
df_or_loaderr`. Splitting it into K-LE2 + K-LE5 is strictly better coverage than
the ambiguous single knife would have been, so the assertion earned its keep.

⚠️ **Main page 1 is at 6 B (2026-08-20, `make basic-reloc`).** The next page-1
slice needs a carve; do not read this figure as current without re-running it.
