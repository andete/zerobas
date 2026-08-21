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

✅ **AND `BLOAD` FOLLOWED THE NEXT DAY — see §6 (D-BLNF, 2026-08-21).** What
this section said about it stays true and always will: its loader is the sub-ROM
page-1 tenant, where the shared `fatio-body.inc` binds to the REAL sub-side
primitives and `DISKOP_OP` is never written, so the §2 test can never see it.
The half that was wrong was the conclusion — it did not need that cell, only the
same *distinction*, which `fat_io_open` draws internally at its own mount/find
boundary. `dsk-bloadmode` still needs a second face (`Bad file mode`) that no arm
in the tree produces; that is a different question, not a smaller one.

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
`kill-missing`'s pin did in D-DSKMSG. `bload-missing` **kept** `load error` that
day, because its reference reading existed and its fix did not, and a pin that
drifts on a neighbour's evidence stops being a pin. ✅ It moved on 2026-08-21,
with its own code (§6) — which is the rule working, not an exception to it.

`runtail-acceptance`'s per-side normalisation (`missmsg`) also collapsed: both
sides now normalise the same string. Kept rather than deleted, because the
cassette / mount / I-O class still diverges. (It named BLOAD too until §6.)

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

⚠️ **Main page 1 was at 6 B when this section was written (2026-08-20,
`make basic-reloc`); §6 spent 4 more of it.** Do not read any figure here as
current without re-running the target — it prints all four walls.

---

## 6. D-BLNF — the sixth verb, 2026-08-21

`BLOAD"missing"` now raises **ERR 53 `File not found`** and stops, like the other
five. **4 bytes of main page 1 (6 → 2 B) and 12 bytes of sub page 1
(1631 → 1619 B)**; low region 22 B and sub page 0 3299 B unchanged
(`make basic-reloc`, 2026-08-21).

### 6.1 🎯 The tenant did not need the cell, only the distinction

§2's test is `DISKOP_OP == DISKOP_SEL_FAT_FIND`, and everything §1 said about why
BLOAD cannot use it is still true: its loader is a sub-ROM page-1 tenant that
calls the REAL `fat_find` as a plain in-page call, so nothing writes that cell.
What was wrong was reading *"cannot use the test"* as *"cannot make the
distinction"*. `fat_io_open` **is** the mount-then-find sequence:

```
fat_io_open:    call    fat_mount
                ret     c
fat_io_find:                        ; <- D-BLNF, a ZERO-BYTE label
                ld      hl,DISK_FCB_NAME
                call    fat_find
                ret     c
                call    fat_open    ; the tail ends `or a` -- it CANNOT set Cy
```

A carry out of `fat_io_find` means precisely *"the volume mounted and the 8.3
name is not in the directory"* — the same proposition `DISKOP_OP == FAT_FIND`
carries on the resident side, read off the control flow instead of out of RAM.
The label costs **0 bytes on both sides**, because it splits no code: it only
names a boundary `fat_io_open` already had.

The tenant then unrolls the one call it makes
([`basic/bload-body.inc`](../basic/bload-body.inc)):

```
                call    fat_mount
                jp      c,bl_load_error        ; no volume / I-O -> `load error`
                call    fat_io_find
                jp      c,bl_notfound          ; -> BL_STAT = 2
```

`BL_STAT` becomes three-valued (`0` loaded / `1` `load error` / `2` not found)
and the resident stub ([`basic/bload.asm`](../basic/bload.asm)) raises the third
at `df_notfound` — the same routine §2's helper jumps to. So `df_notfound` now
has **two callers that found out in two different ways**, which is the point: a
routine's correctness must not depend on how its caller knew.

### 6.2 💰 Priced first, and the 0-byte design was DECLINED

There is a **0-byte** main-page-1 shape: have the tenant write
`DISKOP_OP = DISKOP_SEL_FAT_FIND` itself and retarget the stub's existing
`jp nz,load_error` at `df_or_loaderr`, a pure retarget like §2's other five.
**Declined, with the reason.** BLOAD's **tape** arm reaches that same stub, so a
cassette failure would then be adjudicated by the freshness of a *disk*
marshalling cell — the exact class that broke the cassette in §3, one slice
after §3 was written. Paying for that twice to save four bytes is not a trade
this project makes, and the shared tail's default must stay the safe one.

⚠️ **Main page 1 is at 2 B (2026-08-21, `make basic-reloc`).** The next page-1
slice needs a carve before a byte moves, not after.

### 6.3 🎯 The fix opened a hole, and the row that closes it ships with it

BLOAD's **mount** arm had no row anywhere. Before the fix that did not matter —
every BLOAD failure answered one string, so nothing could be wrong about which
arm it came from. The moment one arm raises ERR 53, moving the *other* one there
is a defect no gate in the tree could see: with `jp c,bl_load_error` re-pointed
at `bl_notfound`, `dskmsg-acceptance` stays **11/11** and `bload-missing`
**passes**.

So `bload-nodisk` joins `kill-nodisk` / `name-nodisk` in
[`disk_probe_fat_error_disposition.py`](../probes/disk/disk_probe_fat_error_disposition.py)'s
MOUNT group, in this commit. 🎯 **A new arm needs its own mount row the day the
arm lands, not the day someone breaks it** — and the row could not have existed
a day earlier, because before the split its twin answered the same string and the
group's own honesty check would have reported it NOT MEASURED.

### 6.4 Gates

`dskmsg-acceptance` **10/10 + 2 reported → 11/11 + 1 reported**
(`dsk-bloadnone` graduated; `dsk-bloadmode` stays printed).
`fat-error-acceptance` 8/8 FIND + **3/3** MOUNT (was 2/2) + 5 directory checks.
`castail-acceptance` **31/31** unchanged — the §3 cassette guard holds, which is
the class check, not a courtesy. `runtail-acceptance` 9/9,
`diskbasic-acceptance` 34/34, `unit-test` 59/59, `deadcode`, `audit-citations`,
`wall-assertion-check`, `redundant-load-check` all clean.

🎯 **AND A DEFERRED ROW IN AN UNRELATED BATTERY WAS THE FREE CROSS-CHECK AGAIN**
(§4's `f.loadlit` trick, one verb over). `namspc-acceptance` stays **58/58 + 22
deferred**, and inside the deferred block `f.bloadlit` — a **literal** missing
filename — moved `<load error>` → `<File not found>` and now agrees with the
CF-3300, while `f.bloadvar` — the same verb with a **string-expression**
argument — is untouched at `<load error>`. That is exactly right: this slice
fixed the missing-file face and did nothing to D-FNARG's argument-shape defect,
and a battery that owns neither said so without being asked.

### 6.5 Knives — 4 of 4 EXACT

Baseline and restored ROM ids both `670b8d4a` (main) / `6a493e36` (sub), so no
knife outlived its run. Every cut is a **VALUE**, and every discriminator is the
**message**: each row errors on both sides of every cut here.

| knife | cut | predicted red | measured |
|---|---|---|---|
| K-BN1 | `bl_notfound`'s `ld a,2` → `ld a,1` (un-split the status) | `dsk-bloadnone`, `bload-missing` | **EXACT** |
| K-BN2 | the body's `jp c,bl_notfound` → `jp c,bl_load_error` (the ROUTE, not the value) | the same two | **EXACT** |
| K-BN3 | the body's mount-arm `jp c,bl_load_error` → `jp c,bl_notfound` | **`bload-nodisk` alone**; the other two stay green | **EXACT** |
| K-BN4 | the stub's `dec a` → `inc a` (both statuses raise) | `bload-nodisk` alone | **EXACT** |

Each knife moved exactly the ROM its file predicts — K-BN1/2/3 `sub.rom` only,
K-BN4 the main ROM only.

⚠️ **K-BN1 AND K-BN2 EXIT 2, NOT 1, ON `fat-error-acceptance`, AND THAT IS THE
RIGHT ANSWER.** With the status un-split, `bload-nodisk` reads the same string as
its mounted twin, so the group reports it **NOT MEASURED** — a machine that
cannot tell a mount miss from a find miss is the dead-disk-ROM signature, and
this battery says *the instrument could not measure* before it says *the tree
regressed*. The regression is still reported, by `bload-missing` and by
`dskmsg`'s `dsk-bloadnone`.

### 6.6 What is NOT fixed, stated rather than folded in

`dsk-bloadmode` — `BLOAD` of a file that **exists and is not a BSAVE binary** —
is `Bad file mode` on the CF-3300 and `load error` here. It is untouched by this
slice and asserted so on every run: `fat_find` **succeeds**, the `$FE` marker
check rejects, and the arm is `bl_load_error`. It needs a **face the tree does
not have**, not a re-route of one it does, and it stays printed-not-gated.

> ✅ **CLOSED THE NEXT DAY — see §7.** The last clause is the one that was
> wrong: the face **did** exist. `Bad file mode` is ERR 61, its text has shipped
> sub-hosted since D-MSGMIGRATE, and three `FIELD`/`GET` sites already raise it.

---

## 7. D-BLMODE — the seventh face, 2026-08-21, **+1 B main page 1**

`dskmsg-acceptance` **11 gated + 1 printed → 15 gated + 0 printed**. The holding
pen is EMPTY, and it was emptied by fixing all seven, not by deleting them.
Walls: main page 1 **13 B → 12 B**, sub page 1 **1619 B → 1615 B**; low region
22 B and sub page 0 3299 B unmoved.

### 7.1 🔴 The disposition was measured FIRST, and it is half the divergence

The filed item warned that whether the reference **raises** `Bad file mode` or
**prints** it was unmeasured, and that "it raises" was a
plausible-and-therefore-dangerous assumption. Every row in `dskmsg` is a typed
DIRECT-MODE line, and a direct-mode line stops either way — which is exactly how
`load error` ran on into the next line at six verbs for a year without a row
noticing (§1). So the reading was taken before anything was designed, as a stored
program with a marker on the next line, **calibrated in both senses by two rows
whose answer was already known**:

| program | cf3300 | zb (before) |
|---|---|---|
| 🟢 `10 BLOAD"PROG.BIN"` | **RAN ON**, `[RANON]` | **RAN ON**, `[RANON]` |
| 🟢 `10 BLOAD"NOSUCH.BIN"` | **STOPPED**, `File not found in 10` | **STOPPED**, idem |
| 🔴 `10 BLOAD"PROG.BAS"` | **STOPPED**, `Bad file mode in 10` | **RAN ON**, `load error\|[RANON]` |
| 🔴 `10 BLOAD"TEST.BIN"` | **STOPPED**, `Bad file mode in 10` | **RAN ON**, `load error\|[RANON]` |

It raises. The assumption was right and is now a reading — and the divergence is
**two things**, a message AND a disposition, of which the shipped battery could
see only the first.

🎯 **AND THE FOURTH ROW IS THE ONE THAT MAKES IT A RULE.** `TEST.BIN` is data
with a `.BIN` name, and it is rejected identically. So the reference is checking
the **`$FE` header marker**, not the extension — which `BLOAD"PROG.BAS"` alone
could never say, because a machine that simply refused `.BAS` would match it.
Both rows ship (`dsk-bloadmode`, `dsk-bloadmodbin`).

### 7.2 🔴 The filed price was wrong in both halves, and one grep said so

The item said the shape is *"a fourth `BL_STAT` value plus a new error face,
i.e. a message-table entry"*, that **"zerobas has neither the message nor an ERR
code for it"**, and that the code is **54**.

* The **message ships**: [`sub/errmsg.asm`](../sub/errmsg.asm) `em_bad_filemode`,
  `db "Bad file mode",0`, migrated by D-MSGMIGRATE.
* The **ERR code ships and is already raised** — `ld a,61` at
  `basic/strvar.asm` and twice in `basic/field.asm`, and `raise_error`'s sparse
  fall-through routes 61 to the sub-hosted text with no main-side membership
  test at all.
* **It is 61, not 54.** In this tree 54 is `File already open`.

So the entire "new error face" half of the price was **already paid**, and what
remained was a jump target and a status value.

### 7.3 🎯 The fourth value is a CODE, not an index — which is why it costs one byte

`BL_STAT` was `0 = loaded, 1 = load_error, 2 = not found`. Adding `3 = bad mode`
would have needed, in the resident stub, `dec a` + `jp z,df_notfound` +
`ld a,61` + `jp raise_error` — **+6 B of main page 1**. Instead the cell now
carries **the MSX ERR code itself**: 0 = loaded, 1 = `load error` printed,
**anything else = raise ERR n**. The stub becomes

```
                cp      1                   ; was `dec a`          +1 B
                jp      z,load_error
                jp      raise_error         ; was `jp df_notfound`  +0 B
```

because `A` is already the code. **+1 B**, hand-counted before the build and
confirmed by it. Sub-side, `bl_notfound` files 53 instead of 2 and a new
`bl_badmode` files 61 through a shared store: **+4 B of sub page 1**, where 1619
were free.

⚠️ **THE HAZARD IS NAMED, NOT DISCOVERED LATER: BLOAD CAN NEVER RAISE ERR 1**
through this cell, because 1 means "printed". Written down at the cell
(`basic/sysvars.inc`), at both arms (`sub/bload.asm`) and at the stub.

⚠️ **AND ONLY ONE ARM MOVED.** `bload-body.inc`'s `jp nz,bl_badmode` is the `$FE`
mismatch alone; the `jp c,bl_load_error` two lines above is an I/O failure on the
very first byte, whose reference face is **unmeasured**, so it keeps the shared
tail's safe default — the same discipline `bl_notfound` was built with, and the
lesson D-LOADERR-FIX paid for with the cassette.

### 7.4 🔴 The control could have been spoofed by its own echo

`dsk-bloadbinrun` asserts the literal `[RANON]`, because "the marker is absent"
is satisfied by a machine that cannot print, by a lost anchor, and by a program
that never ran. But the marker is TYPED as well as printed, so an echo inside the
window would spell it. Two guards, and **K-BM3 shows they catch different
failures**:

* the marker is printed as `PRINT"[RAN";"ON]"`, so **the echo cannot spell it**;
* the control's must-NOT-contain list carries `PRINT`, which appears **only** in
  an echo — that is what pins the `ANCHOR` override itself.

### 7.5 Knives — 3 of 3 EXACT, two rounds each, byte-identical red sets

| knife | cut | predicted | measured |
|---|---|---|---|
| **K-BM1** | `bl_badmode`'s `ld a,61` → `ld a,53` (a VALUE; the discriminator is the MESSAGE) | the three wrong-kind rows read `File not found`; `dsk-bloadnone` GREEN | ✅ **EXACT**, rc 1, 12/15 — and **`sub.rom` only** moved |
| **K-BM2** | the stub's `jp raise_error` → `jp load_error` | **four** rows: the three plus `dsk-bloadnone`, and `dsk-bloadmoderun` reads `load error / [RANON]` | ✅ **EXACT**, rc 1, 11/15 — **the pre-fix reading reproduced verbatim**; main ROM only |
| **K-BM3** | probe-side: `ANCHOR = {}` | rc **2** on the must-NOT-contain `PRINT` | ✅ **EXACT**, rc 2, and the reading is `20 PRINT"[RAN";"ON]" / RUN / [RANON]` |

🎯 **K-BM1 IS WHAT SAYS THE NEW ARM IS REACHED RATHER THAN THE OLD ONE
RE-LABELLED**: `dsk-bloadnone` stays green under it, because that row files its
own 53 at a different arm. 🎯 **K-BM2 is the stronger of the two** — it reproduces
the exact string this slice was filed against, on the exact row that could not
see it before.

⚠️ **AND K-BM3's READING CONTAINS `[RANON]`.** The split marker alone would not
have caught it; the `PRINT` assertion did. Two guards, two failure modes, and the
knife is what separated them rather than an argument.

### 7.6 Gates

`dskmsg-acceptance` **15/15**, 0 printed-not-gated · `fat-error-acceptance` ·
`diskbasic-acceptance` · `runtail-acceptance` · `castail-acceptance` ·
`cassave-acceptance` · `namspc-acceptance` · `unit-test` 59/59 · `deadcode`
(`df_notfound` keeps four callers) · `audit-citations` · `wall-assertion-check` ·
`redundant-load-check` · `rowshape-check` · `injector-check` ·
`preflight-check` · `latch-check`.
