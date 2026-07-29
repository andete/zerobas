# D-FCH — dynamic file-channel allocation

Make `MAXFILES` mean what it means on the reference: channel blocks **carved out
of the pool at `MAXFILES` time**, so the ceiling reaches 15, nothing is charged
for channels a program never asks for, and `FRE(0)` actually moves.

Measurement this is written from:
[`chancost-cf3300-characterization.md`](chancost-cf3300-characterization.md);
probe [`probes/disk/diskbasic_probe_chancost.py`](../probes/disk/diskbasic_probe_chancost.py)
(`make chancost-characterize`). Every number below is measured on the real
National CF-3300 unless it says otherwise.

✅ **Status 2026-07-29: SIGNED OFF; S-FCH-1 (§3.1), §3.3 and §3.2 are BUILT
AND GATED.** What remains is **S-FCH-2** — the ERR 5 / 52 / 59 codes — whose
premise has since moved adversely (§7). §5b records §3.2's measured cost, §5a
S-FCH-1's, and §5 the rest.

## 1. What is wrong

✅ **FIXED by §3.2** — kept here as the statement of what was wrong.
zerobas reserved its channel contexts **statically and permanently**:
`FCH_CTX $EA00..$EE63` = `FCH_CEIL`(2) × `FCH_CTXSZ`(562) = **1124 B**, held
whether or not a channel is ever opened. Of each 562 B, **512 B is nothing but a
save copy** of the single global `FSECTOR_BUF` — `fch_save_active` /
`fch_load_ctx` `memcpy` it in and out
([`basic/files.asm:994`](../basic/files.asm:994)).

Measured consequences:

| | reference | zerobas (before) | zerobas (now, ✅) |
|---|---|---|---|
| per channel | **267 B** | 562 B | **50 B** |
| ceiling | **15** | 2 | **15** |
| `FRE(0)` vs `MAXFILES` | −267/channel | **does not move** (13875 at 0, 1 and 2) | **−50/channel** (14899 → 14149) |
| charged when | at `MAXFILES` time | always | **at `MAXFILES` time** |

The reference's 267 is **less than 512**, so its sector staging is not in it: it
keeps **one shared sector buffer** and a small per-channel block. zerobas
already *has* that shared buffer; it just also pays for N private copies of it.

## 2. The contract to implement — MEASURED

### 2.1 Allocation

* `MAXFILES=n` reserves n channel blocks **up front**; `OPEN` claims one and
  costs **nothing further** (measured: `FRE(0)` identical before and after a
  successful `OPEN`).
* The charge lands in the **variable/program pool** (`FRE(0)`), never the string
  pool (`FRE("")` reads 200 at `MAXFILES` 0 and 8 alike).
* `TXTTAB` and `HIMEM` are **constant** across the ladder, so the carve is
  **downward from the top** — it is `SP` that moves, which is what `FRE(0)`
  counts down to ([`binfre-vg8020-characterization.md` §3.1](binfre-vg8020-characterization.md)).
* Legal domain **0..15**. `16` and `255` raise **ERR 5 Illegal function call**
  (code read via `ON ERROR`/`ERR`, not inferred from wording).

### 2.2 Side effects — all measured, all currently absent in zerobas

| row | reference | zerobas before | zerobas now |
|---|---|---|---|
| `A=5 : MAXFILES=2 : PRINT A` | **0** — variables are CLEARed | `5` | **0** ✅ |
| `A=5 : REM MAXFILES=2 : PRINT A` — *control* | `5` | `5` | `5` ✅ |
| `A=5 : MAXFILES=1 : PRINT A` (**value unchanged**) | **0** — clears anyway | `5` | **0** ✅ |
| `A$="XY" : MAXFILES=2 : PRINT LEN(A$)` | **0** | `2` | **0** ✅ |
| `A$="XY" : REM MAXFILES=2 : PRINT LEN(A$)` — *control* | `2` | `2` | `2` ✅ |
| `CLEAR 500 : MAXFILES=2 : PRINT FRE("")` | **500** — pool size SURVIVES | `500` | `500` ✅ |
| `OPEN…AS #1 : MAXFILES=2 : PRINT LOF(1)` | **`File not OPEN`** | `-1` | `-1` (S-FCH-2) |

⚠️ The `A$` row was `PRINT A$` when this spec was written, and in that form it
was **unmeasurable on either machine** — see §6. `LEN(A$)` is the measured
replacement, and the reference answers **0**, confirming the string clear.

⚠️ **`MAXFILES` clears unconditionally — even when the value does not change.**
The `sem_same` row is the one that pins this; without it the natural reading is
"clears only when it reallocates", which is wrong. It is also convenient: since
the statement moves the pool ceiling, clearing is required for *safety* anyway,
so the faithful behaviour and the implementation need coincide.

`MAXFILES` also **closes every open channel** (zerobas already does this —
`ex_maxfiles` calls `fch_close_all`; what it gets wrong is only how a
subsequently-touched channel reports itself, below).

### 2.3 Error codes — measured, with the whole disk block mapped

`ERROR n` prints its own message, which maps code → message black-box on the
CF-3300:

| code | message | | code | message |
|---|---|---|---|---|
| 50 | FIELD overflow | | 58 | Sequential I/O only |
| 51 | Internal error | | **59** | **File not OPEN** |
| **52** | **Bad file number** | | 60 | Bad FAT |
| 53 | File not found | | 61 | Bad file mode |
| 54 | File already open | | 62 | Bad drive name |
| 55 | Input past end | | 63 | Bad sector number |
| 56 | Bad file name | | 64 | File still open |
| 57 | Direct statement in file | | 65 | File already exists |

The three this slice needs:

| situation | reference | zerobas today |
|---|---|---|
| `MAXFILES=16` | **ERR 5** Illegal function call | `syntax error` (ERR 2) |
| `OPEN…AS #2` with `MAXFILES=1` | **ERR 52** Bad file number | `syntax error` (ERR 2) |
| `LOF(1)` on a channel that is not open | **ERR 59** File not OPEN | returns `-1` |

⚠️ **`Bad file number` is NOT trappable on the reference.** With
`10 ON ERROR GOTO 100` active, `MAXFILES=16` and the closed-channel `LOF` both
trap cleanly (`ERR` reads 5 and 59), but the bad-channel `OPEN` prints
`Bad file number in 30` and never reaches the handler. That is why §2.3's 52
comes from the `ERROR n` map rather than from `ERR` — and it is a behaviour the
gate should pin rather than quietly "fix".

⚠️ [`basic/files.asm:332`](../basic/files.asm:332) **already says
`; 0 or > MAXF -> bad file number`** and then jumps to `oo_fail_syn` →
`stmt_error`. The comment names an error the code does not raise; four sites do
the same (`files.asm` 329/332/496/499/584/587, `field.asm` 154/157).

## 3. The design

### 3.1 Retire the per-channel save copy

Make `FSECTOR_BUF` a true **shared cache** rather than a thing that is copied:

* on switching **away** from a channel, flush it if dirty (the write path
  already tracks `FWR_BUFLEN`);
* on switching **back**, re-read the sector from its recorded location.

Per-channel state becomes `FCH_STATESZ`(50) plus the cache bookkeeping the
switch needs (which sector is resident, and whether it is dirty) — call it
**`FCH_BLKSZ` ≈ 52 B**, to be pinned by the implementation, not by this
sentence.

This is what the reference does, and it is why its block is 267 rather than 779.

### 3.2 Carve the table out of the pool — ✅ BUILT + GATED 2026-07-29

Today the ceiling for program text is `min(HIMEM,TXTMAX)`, and D-CLP already
established the single-moving-boundary model with the string pool below it
(`min(HIMEM,TXTMAX) − POOLSIZE`, derived sub-side — S-CLP-2). D-FCH adds one
more term:

```
channel table base = min(HIMEM,TXTMAX) − POOLSIZE − MAXF × FCH_BLKSZ
```

so `MAXFILES=n` moves a boundary that `FRE(0)` already reports, and the
statement's measured `CLEAR` (§2.2) is exactly the invalidation that move needs.

#### What was built

The map, repack build only (the lean cart keeps the static `FCH_CTX` table and
stays byte-identical):

```
[PRGEND+2 .. varceil)   variables + arrays        FRE(0) reports this gap
[varceil  .. floor)     THE CHANNEL TABLE          = MAXF x FCH_CTXSZ (50 B)
[floor    .. C)         string pool                FRE("") reports this gap
                                       C = min(HIMEM,TXTMAX), floor = C - POOLSIZE
```

* **`strheap_varceil`** ([`sub/strheap.asm`](../sub/strheap.asm)) — the new
  boundary, `strheap_floor() - MAXF*FCH_CTXSZ`, clamped at 0. **Derived, never
  stored**, exactly as S-CLP-2 derives the pool floor and for the same reason:
  the inputs (`MAXF`, `POOLSIZE`, `HIMEM`) are all RAM cells, so `CLEAR n`,
  `CLEAR ,himem` and `MAXFILES=n` are picked up for free by the next
  derivation — no cell to keep fresh, no hook at three sites, no staleness hole.
* Its **three consumers**: `sh_free_vars` (so `FRE(0)` moves), and
  `scv_ceil_try` + `aal_ceil_try` in [`sub/arrays.asm`](../sub/arrays.asm) (so
  the space is actually *reserved*). The string pool's own floor and
  `heap_alloc` are deliberately **unchanged** — that is what keeps `FRE("")`
  at 200 across the ladder.
* **op 18 `sh_chan_addr`** — `SH_LEN` = channel → `SH_PTR` = block base.
  `fch_ctx_addr` ([`basic/files.asm`](../basic/files.asm)) is now that call.
* **`FCH_CEIL` 2 → 15** (repack), which forces `FCH_MODES` (16 B) and
  `FCH_RECLENS` (32 B) out of their old cramped slots into the `$EA00..$EAFF`
  page-3 window S-FCH-1 freed. `$EA30..$EAFF` (208 B) is still free.
* **`MAXFILES` now `CLEAR`s**, unconditionally (§2.2's `sem_same` row).

⚠️ **Boot order was checked, not assumed.** `strheap_varceil` reads `MAXF`,
which `init_filechan` seeds — and `init` calls `clear_vars` *before* it, so on
power-on hardware `MAXF` is RAM garbage for that window. Nothing in it derives
the ceiling: `clear_vars` → `vars_reset` → `heap_reset` writes `FRETOP`/`ARYTAB`
and the array sentinel without ever allocating. No seed hoist was needed.

### 3.3 What the freed RAM buys

Retiring `FCH_CTX` frees the whole **1124 B** at `$EA00`. `TXTMAX` can then rise,
but **only contiguously**, and the page-2 stack above it is:

| region | size | movable? |
|---|---|---|
| `TOKBUF` `$B700..$B93F` | 576 B | yes |
| gap `$B940..$B9FF` | 192 B | — |
| `LINEBUF` `$BA00..$BAFE` | 255 B | yes, but **must stay page-aligned** (`ld h,high LINEBUF`, `INP_CURSOR` is a single low byte) |
| `DETOKBUF` `$BB00..$BFFF` | 1280 B | does not fit in 1124 B |

Moving `TOKBUF` **and** `LINEBUF` into the freed window (832 B of 1124 B, and
`$EA00` is page-aligned so `LINEBUF`'s constraint is satisfiable) lifts
`TXTMAX` `$B700` → `$BB00` = **+1024 B**.

⚠️ **`TOKBUF` must move first or nothing moves at all** — `LINEBUF` sits *above*
it, so relocating `LINEBUF` alone lifts `TXTMAX` by zero.

Net program space, default `MAXFILES=1`: **13875 + 1024 − ~52 ≈ 14847**, against
15667 before D-LINEMAX. `MAXFILES=15` would then cost ~780 B **visibly, out of
`FRE(0)`** — which is the point.

### 3.3a — ✅ BUILT 2026-07-29

`LINEBUF` `$BA00` → **`$EB00`** (page-aligned, so the single-low-byte cursor idiom
is untouched), `TOKBUF` `$B700` → **`$EC00`**, `TXTMAX` `$B700` → **`$BB00`**.

**`FRE(0)` 13875 → 14899**, measured on the built machine — exactly the predicted
+1024. **Zero ROM cost**: these are address constants, so page 1 stayed at 1 B
free and the lean cart stayed byte-identical.

Usability was checked rather than assumed: `CLEAR 200 : DIM A%(7000)` needs
14002 B — impossible against the old 13875, and it now succeeds with **both ends
of the array written and read back** (11 / 22) and 889 B still free. A `DIM` that
merely *succeeds* would not have witnessed real storage.

⚠️ **The ceiling is now bounded by `DETOKBUF`, not by free RAM.** At 1280 B it
does not fit in the 1024 B window, so `$BB00` is where `TXTMAX` stops until
`DETOKBUF` is dealt with. Of D-LINEMAX's 1792 B, **1024 B is recovered and 768 B
is still charged** to page 2.

⚠️ Page 3 is always-mapped RAM and is **not** paged out by a sub-ROM `CALSLT`
(the tokenise tenant takes page 0; fatprim/detok take page 1), so both moved
buffers stay addressable from the tenants that fill them. No code referenced
`$B700`/`$BA00` literally — every use goes through the equates, verified by grep.

## 4. Scope boundary

**In:** the shared-cache switch, the dynamic table, `FCH_CEIL` 2 → 15, the
`MAXFILES` `CLEAR` side effect, ERR 5 / 52 / 59, and the `TOKBUF`+`LINEBUF`
relocation that turns the freed RAM into program space.

**Out:** `LOF(#n)` returning −1 on a freshly-created OUTPUT channel (reference:
0) — filed separately in [`TODO.md`](../TODO.md), it is a `LOF` bug rather than
an allocation one, and its fix should not ride on this slice's carve. Also out:
raising `FCH_CEIL` beyond 15, and any change to `DETOKBUF`.

## 5a. S-FCH-1 cost — ✅ MEASURED AND BUILT, 2026-07-29

**§3.1 alone costs 5 B of main page 1 and 0 B of low region. It NEEDS NO CARVE** —
it fits the existing 6 B with 1 B to spare — and it frees **1024 B** of page 3
(`FCH_CTX` 1124 B → 100 B at `FCH_CEIL=2`).

The number moved twice, and only building it showed that:

| siting | page-1 end | cost | verdict |
|---|---|---|---|
| detach half RESIDENT | `$8025` | **43 B** | 37 B over — would have forced a carve |
| detach half in the SUB-ROM | `$8003` | 9 B | 3 B over |
| + the IX guard hoisted into `fch_select` | **`$7FFF`** | **5 B** | **fits, 1 B spare** |

⚠️ **A carve scouted from the first row would have been scouted for a
requirement that was 8× too big.** The whole cost was siting, not substance:
`fat_detach_channel` calls `fat_flush_data_sector`, which is *already* a sub-ROM
primitive, so keeping the caller resident bought nothing and cost 34 B.

⚠️ **The IX contract was a live hazard, not a formality.** `fch_save_active` /
`fch_load_ctx` had no CALSLT before this change and their header promises IX/IY
survive, because the `EOF`/`LOF` factors and `INPUT$` hold their token cursor
there. Guarding inside both routines cost 8 B; hoisting a single guard into
`fch_select` — which every IX-critical caller enters through, while `fch_claim`'s
only caller keeps its cursor in HL and already guards for CALSLT — cost 4 B and
saved the slice.

**Gated, and the gate was falsified.** `disk_probe_maxfiles.py`'s interleaved
two-channel write is the one row that exercises a mid-stream switch on an OUTPUT
channel; it is byte-identical to the CF-3300. Stubbing `fat_restage_channel` to
`ret` makes `A.TXT` come back holding **B's** bytes and the row FAILS both
functionally and against the oracle — so the row has teeth
([[gate-can-be-green-while-measuring-nothing]]). Full corpus green: unit 53/53,
`diskbasic-acceptance` 34/34, linemax 60/60, arrdim 73/73, clearpool 52/52, bdos
12/12, fat-error 7/7, array 149/151 (the standing `ifc.instr.*` baseline).

⚠️ **Repack-only.** The lean 16 KB cart is byte-full — ungated,
`fat_restage_channel` overran its `$8000` ceiling outright — so it keeps the
memcpy path and stays byte-identical. Exactly the co-maintenance cost RETIRE THE
LEAN CART exists to remove.

⚠️ **Known gap, deliberately left:** `fch_save_active` ignores the detach's `Cy`.
Switching channels could never fail under the memcpy design and now can (disk
full while flushing). Propagating it means a disposition at every `fch_select`
caller — filed rather than smuggled in.

## 5b. §3.2 cost — ✅ MEASURED AND BUILT, 2026-07-29

**1 B of main page 1, 0 B of low region, NO CARVE.** Page 1 now stands at
**0 B free** (`__MEAS_PAGE1_END` = `$8000` exactly); the low region is unchanged
at 9 B. Measured by relaxing the `$8000` guard, reading the symbol, and
restoring it — not estimated.

| what | page 1 |
|---|---|
| `fch_ctx_addr` → op 18 (`ld hl,FCH_CTX` → three stores + a call) | **+1 B** |
| `MAXFILES`'s `CLEAR`, written out inline | +8 B |
| …the same `CLEAR`, as `jp clr_done` | **0 B** |
| **total** | **+1 B** |

⚠️ **THE COST WAS SITING AGAIN — the third time in this slice.** The first
build overran by 8 B, and every one of those 8 was the `CLEAR`:
`push hl / call clear_vars / call vars_reset / pop hl`. But that sequence *is*
`ex_clear`'s own tail (`clr_done`, [`basic/clear.asm`](../basic/clear.asm)),
entered with `HL` = the statement cursor — exactly `ex_maxfiles`' state. Jumping
to it costs the 3 bytes the `jp exec_stmt` it replaced already spent. Same
lesson as S-FCH-1's 43 → 5: **check whether the code you are about to write
already exists somewhere its callee lives.**

The dynamic allocation was near-free for the reason §3.2 predicted: the whole
arithmetic chain (`strheap_varceil` → `strheap_floor` → `strheap_ceiling`) was
**already sub-ROM**, so nothing resident had to learn it.

## 5. Cost of the REST — ⚠️ STILL NOT MEASURED

**This is the section that decides whether the slice is affordable, and it
cannot be written from reading code.** The tree stands at **9 B free in the low
region and 6 B free in page 1**. Known cost drivers, none of them sized:

1. flush-and-re-read replacing `memcpy` in the context switch (`files.asm`) —
   plausibly near-neutral, *plausibly* being the operative word;
2. the pool-ceiling arithmetic of §3.2 at every consumer of the ceiling;
3. **ERR 52 and 59.** `err_msgtab` currently stops at **25**
   ([`basic/interp.asm:997`](../basic/interp.asm:997)). Reaching index 59 as a
   dense table is 34 more words = **68 B** plus the two message strings, ~100 B
   total — an order of magnitude more than the free space. §7's S-FCH-2 is about
   this.

Per [D-ARR-C §7a](../TODO.md), a risk assessment written from reading code is a
hypothesis: §7a's "rewrites the column-major address math" was wrong, and so was
its cost. **The cost must be built to be known**, on a branch, before the ceiling
and error-code decisions are final.

## 6. The gate — ✅ BUILT 2026-07-29

`make chancost-characterize` is now an acceptance **gate**: it returns non-zero
on oracle drift, on any divergence not in an explicit `KNOWN_DIVERGE` allowlist
(9 rows, each naming the item that owns it — S-FCH-2 and the filed `LOF` bug),
and on the mechanism assertions below. 31 cases, boot-per-case, both machines.

🔴 **THIS SECTION'S FIRST BULLET WAS WRONG, AND THE CORRECTION IS THE
INTERESTING PART.** It asked the gate to assert **267 on both sides**. But §3.1
left the block size "to be pinned by the implementation", and S-FCH-1 pinned it
at **50 B** — because a zerobas block genuinely *is* 50 B of state, its sector
staging being the shared `FSECTOR_BUF` cache. Asserting 267 would have meant
padding every block with 217 B of reserved-and-unused RAM purely to make a
number match: `MAXFILES=1` would have cost 267 B of a user's program space
instead of 50, and `MAXFILES=15` 4005 B instead of 750 — *less* faithful in
effect, since the charter is a working BASIC and zerobas's pool is already
9 KB smaller than the reference's. **User decision 2026-07-29: charge what we
use.** What the gate asserts instead:

* the ladder asserted as a **linear per-channel slope with a ceiling of 15, on
  both sides**, with each machine's own constant reported (**reference 267,
  zerobas 50**) — the *mechanism* is what must match, and it now does. Before
  the change zerobas's line read `statically reserved (MAXFILES does not move
  FRE(0))`, which the gate now rejects outright;
* ⚠️ **the RESERVATION asserted separately from the REPORT** — `dim_fits` /
  `dim_over`, added by this slice. The slope alone **can be perfectly green
  while nothing is reserved**: a build that subtracts the table from
  `sh_free_vars` but not from the array ceilings produces the identical
  50 B/channel ladder and lets arrays grow straight through the channel table.
  **Falsified, not assumed** — with the array ceilings reverted to
  `strheap_floor`, `mf0`/`mf2`/`mf15` still read 14899 / 14799 / 14149 (a
  flawless slope) while `dim_over` returned `7777` instead of `Out of memory`.
  Both rows size themselves from the machine's *own* `FRE(0)`, so they are a
  real differential; the +400 B overshoot is chosen against the 750 B of slack
  the failure would create, not for roundness;
* `FRE(0)` **at identical expression depth on every row** — it counts to `SP`,
  and a row that nests differently is measuring a different thing;
* boot-per-case retained: `MAXFILES` clears state by design, so a shared boot
  would let one row's `CLEAR` explain the next row's reading;
* ⚠️ the ceiling asserted **only when the full ladder ran** — a subsetted run's
  "largest surviving n" is the largest n *asked about*, not a measured ceiling
  (already guarded in the probe);
* ⚠️ `MAXFILES=1` kept **out** of the load-bearing set: 1 is the default, so it
  agrees whether or not the statement executed;
* error comparisons by **class**, never wording — zerobas's lowercase strings
  are deliberate provenance policy (PROVENANCE §851), and a raw-text gate emitted
  15 false divergences on the first run and buried both real findings.

⚠️ **One row was UNMEASURABLE and had to be rewritten.** `sem_str` typed
`A$="XY" : MAXFILES=2 : PRINT A$`. A *cleared* `A$` prints an empty line, which
this probe's readout scores `<none>` — and an *uncleared* `A$` prints `XY`,
which is not a bare integer and also scores `<none>`. The row compared equal and
passed **whatever either machine did**, on both sides, forever. It now reads
`PRINT LEN(A$)` (0 vs 2) and has a two-sided `REM` control. Falsified with the
rest: removing `MAXFILES`' `CLEAR` flips `sem_var`/`sem_str`/`sem_same` to
5 / 2 / 5, and in its old form `sem_str` would have stayed green through it.

## 7. Sign-off questions

* **S-FCH-1 — the carve.** The slice needs an unknown number of ROM bytes
  against 9 B / 6 B free, so a carve is near-certain and its scouting has
  repeatedly been the expensive part of a slice. **Recommended: build §3.1
  alone first, on a branch, and measure.** It is common to every version of this
  slice, it is the change that frees the 1124 B, and its measured size is the
  input every remaining decision needs. Do not scout a carve for a requirement
  that is still a guess.

* **S-FCH-3 — `FCH_CEIL` 15 vs the free-RAM trade. ✅ RESOLVED: 15.** The blocks
  are dynamic, so unused channels cost nothing and the ceiling was free. Built,
  and the gate measures it on both sides (a full ladder plus a rejected `mf16`,
  never "the largest n we asked about").

* **S-FCH-4 — the extra disk I/O on channel switch. ✅ NO RE-TIMING NEEDED.**
  The predicted flake did not appear: `diskbasic-acceptance` 34/34 and the
  interleaved-write fixture converge unchanged at the existing capture windows.

* **S-FCH-5 — `MAXFILES` now clears variables. ✅ TAKEN, corpus re-run.** No
  fixture set a variable and then called `MAXFILES`: unit 53/53, linemax 60/60
  + 3/3 `--cas`, arrdim 73/73, clearpool 52/52, diskbasic 34/34, bdos 12/12,
  fat-error 7/7, array 149/151 (the standing `ifc.instr.*` baseline).

* ⚠️ **S-FCH-2 — ERR 5 / 52 / 59. ITS PREMISE HAS MOVED, AND THE MOVE IS
  ADVERSE.** It was costed at ~100 B against **6 B** free in page 1. Page 1 now
  stands at **0 B free** — S-FCH-1 spent 5 and §3.2 spent the last 1. Option
  (b)'s sparse side-table costing is stale for the same reason. This is a
  sign-off premise that changed *after* the sign-off, and it is reported rather
  than absorbed: **S-FCH-2 needs a carve, and the carve must be scouted against
  a requirement that has itself been built and measured** — the one thing this
  whole slice has now demonstrated three times. Nine of the gate's ten filed
  divergences are S-FCH-2's.

* **S-FCH-2 — ERR 52 / 59 vs a dense `err_msgtab`.** Reaching code 59 densely
  costs ~100 B for two messages. Options: (a) extend the table (simple, dear);
  (b) a small **sparse** side-table for the disk block, which the file verbs are
  the only users of; (c) land the allocation work and leave both codes raising
  today's `syntax error`, filing the codes separately. ⚠️ (c) leaves
  [`files.asm:332`](../basic/files.asm:332)'s comment still naming an error it
  does not raise, at six sites. **Recommended: (b)**, but only after S-FCH-1
  gives a real budget.

