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

## 5c. S-FCH-2 cost — ✅ MEASURED 2026-07-29 (built, measured, then reverted
except the free part)

**Built all four parts, measured each, kept the one that costs nothing.** Full
S-FCH-2 is **45 B of page 1 + 41 B of low region = 86 B**, against **0 B and
9 B free**. §5's ~100 B estimate was close — worth stating plainly, because the
two preceding estimates in this arc were off by 8× and by everything.

| part | page 1 | low region | gate rows it closes |
|---|---|---|---|
| **ERR 5** — `MAXFILES=16`/`255` → Illegal function call | **0** | 0 | `mf16`, `mf255`, `err_over` |
| **ERR 59** — `EOF`/`LOF` on a channel that is not open | +8 | 0 | `err_notopen` |
| **ERR 52** raiser + both message strings + the sparse table | +14 | +41 | `sem_zero`, `sem_hinum`, `err_badchan` |
| the sparse lookup in `raise_error` | +23 | 0 | makes 52/59 *print* (`sem_reopen`) |
| **total** | **45** | **41** | all 9 |

✅ **ERR 5 IS LANDED — it costs exactly ZERO bytes.** `gb_illegal`
([`basic/interp.asm`](../basic/interp.asm)) is already the ERR 5 raiser the
byte-argument domain checks use, and it is already in page 1, so each reject
site spends the same 3 bytes on `jp cc,gb_illegal` that `jp cc,stmt_error` spent.
Three of the gate's nine filed divergences closed for nothing. The remaining six
are the ERR 52/59 half plus the filed `LOF` bug.

⚠️ **THE REMAINDER IS 64/86 BYTES OF MESSAGE DATA AND A DATA-DRIVEN WALK** —
34 B of string text, a 7 B sparse table, and 23 B of table walk. That is the most
evictable shape there is. A page-0 sub-ROM tenant could own all of it and stage
the chosen message into the **208 B of page-3 RAM still free at `$EA30..$EAFF`**
(the window `FCH_CEIL=15` did not consume), leaving the resident side a shim.
If that holds, the main-ROM requirement drops from 86 B to roughly ERR 59's 8 +
ERR 52's 14 + a shim ≈ **35–40 B**. **Measure that before scouting a carve** —
this arc has now three times found the cost was siting.

### The sub-ROM eviction — ✅ ALSO MEASURED: the carve drops 77 B → 26 B

Built and measured rather than argued. The message table, both strings and the
table walk move to the **existing** string-heap tenant as **op 19** (no new
dispatch index, no new tenant file); it stages the chosen message into
`ERRMSG_BUF` in the page-3 RAM `FCH_CEIL=15` left free at `$EA30`, because a
pointer into the sub-ROM would be unreadable from the resident abort path.
The two raisers move to the low region, reached by an ordinary in-slot `jp`.

| | page 1 over | low over | **carve needed** |
|---|---|---|---|
| S-FCH-2 all-resident | 45 | 32 | **77 B** |
| S-FCH-2 with the message block evicted | **20** | **6** | **26 B** |

What is left resident is irreducible-looking: the 16 B tenant-call shim in
`rerr_unprintable`, 4 B of closed-channel test in the shared `EOF`/`LOF` helper,
and 15 B of low-region raisers. Moving the shim down as well only trades page 1
for low region — **the total stays 26 B over**, so only a carve closes it.

⚠️ **Both S-FCH-2 builds are COST PROBES: measured, never RUN.** ERR 5 is the
only part that has been executed and gated. Two things must be settled before
any of the rest lands:
* `err_bad_filenum` forces `ONEFLG=1` to reach `raise_error`'s abort arm (the
  measured non-trappability) and **leaves it set**. Whether the return to the
  REPL clears it is unestablished — a stale `ONEFLG` would force-abort the *next*
  error instead of trapping it.
* the ten repointed `jp` sites are unconditional in the probe, so the **lean cart
  would not assemble**; landing needs them gated per-site, or the lean cart
  retired.

Both probes are kept as patches (not committed) and apply to `d197f9b`.

### ⚠️ The measurement apparatus was wrong first, and read plausibly

The first reading said **77 B** of page 1. Relaxing the low region's overflow
guard means removing its `ds $4000 - $` pad — **and that pad is what puts the
cartridge header at `$4000`.** Without it the header, and every page-1 address
above it, slides down with the low region, so `__MEAS_PAGE1_END` was measuring
page 1 *plus* the low region's own size. The two walls are not independent
unless the header is pinned. **Pin it with an explicit `org $4000`** when
relaxing the low guard. The corrected page-1 figure is 45 B, not 77 —
[[measure-the-wall-from-clean]]'s sibling: *measure the wall from a FIXED datum.*

## 5d. S-FCH-2 ALL-RESIDENT — ✅ BUILT, MEASURED, RUN AND LANDED 2026-07-29

**The eviction in §5c was not needed and was not built.** D-MSGENC (`9a0300d`)
freed page 1 `0 → 24 B` and the low region `9 → 68 B`; against that, all-resident
S-FCH-2 costs **11 B of page 1 and 59 B of the low region** — not §5c's estimated
45 + 41. So there is no tenant op 19, no `ERRMSG_BUF` page-3 staging, no repointed
`jp` sites, and both of §5c's open correctness questions are gone rather than
gated.

| wall | before (`5a3e6f1`) | after | spent |
|---|---|---|---|
| page 1 `$4000-$7FFF` | 24 B free | **13 B free** | 11 B |
| low region `$2812-$3FFF` | 68 B free | **9 B free** | 59 B |

Clean `rm -rf build && make basic-reloc`, lean 16 KB `basic.rom` **byte-identical**.

### 5d.1 Why it was a placement problem, not a demotion one

§10/Q1 of [the msgenc carve](spec-basic-msgenc-carve.md) framed the 21 B page-1
shortfall as a demotion: move existing page-1 content down. **It never came to
that, and the scout is the reason.** Demotion is constrained only by **page-0
sub-ROM tenants**, which cannot see the low region — and walking the page-0
closure through to its main-side callees returns:

```
page-0 tenants reach 0 MAIN page-1 entry points
0 non-sub-local names in the page-0 closure (709 total)
```

Every one of the 709 routines a page-0 tenant reaches is **sub-local**. The
tenants rebind their own `pchar`/`print_string`/`div10` (`sub/detok.asm`), and
the only main-side import list in the whole sub-ROM is
`sub/basic-resident-abi.inc` — eleven page-1-*tenant* seeds, all already below
`$4000`. So **nothing in main page 1 is pinned there by tenancy at all**, and the
21 B could have come from anywhere.

⚠️ Worth recording because it also bounds `check_tenant_closure --page0`: that
gate walks the SUB call graph and stops at the boundary, accepting a main page-1
callee without following it into the main graph. It is sound **only while that
set is empty** — which it is today, and this is the measurement that says so.
A future page-0 tenant that calls main page 1 would need the gate extended to
walk *through* it, per [[carve-scout-walk-through-page1]].

Since nothing was pinned, the cheaper move was to site **S-FCH-2's own new
content** low rather than relocate existing code: same lever, no code motion, no
gate to re-argue. Page 1 keeps only what cannot leave it.

### 5d.2 What is where

| piece | region | bytes |
|---|---|---|
| `raise_error`'s range test `jr nc` → `jp nc,rerr_sparse` | page 1, `interp.asm` | **1** |
| closed-channel test in `fch_mode_class` (then `ev_chan_hasfile`; EOF/LOF) | page 1, `expr.asm` | **4** |
| `MSGESC_FILE` phrase-table entry | page 1, `program.asm` | **6** |
| `rerr_sparse` + both raisers + both messages | low, `main.asm` | **59** |

The two raisers (`oo_fail_bfn`, `err_notopen_raise`) live in the low region, so
files.asm's six bad-file-number rejects keep the same 3-byte `jp cc,<label>` they
already spent — the ERR 5 trick from §5c, applied again.

🔴 **The lean cart's `jp`-site blocker is dissolved by aliasing the LABEL, not by
gating the SITES.** §5c's probe repointed each site unconditionally at a symbol
the 16 KB build does not define, so the lean cart would not assemble. One `equ`
in files.asm fixes it for all six at once:

```
    IF ROM_BASE >= $4000
oo_fail_bfn     equ     oo_fail_syn
    ENDIF
```

In the lean build every `jp cc,oo_fail_bfn` assembles to the exact bytes
`jp cc,oo_fail_syn` did. Zero sites gated, zero bytes moved, `check_reloc.py`
byte-identity intact.

### 5d.3 🔴 §5c's "MEASURED non-trappability" WAS A CONFOUND

§5c read the gate's `err_badchan` row as *ERR 52 is not trappable* and specced a
raiser that forces `ONEFLG=1` to reach `raise_error`'s abort arm — which is what
raised the ONEFLG question. **Both halves of that were wrong.** Measured on the
CF-3300, 2026-07-29, three unconfounded ways:

| typed | reference |
|---|---|
| `10 ON ERROR GOTO 100 : 20 OPEN"HI.TXT" FOR INPUT AS #2` | handler runs, **ERR 52** |
| …`AS #0` (out of range for every `MAXFILES`) | handler runs, **ERR 52** |
| `20 B=EOF(1)` on a never-opened channel | handler runs, **ERR 59** |

`err_badchan` types **`MAXFILES=1` between the arm and the error**, and that
statement suppresses the handler on the reference. The row was never measuring
trappability; it was measuring the thing in the middle. So S-FCH-2 raises 52 and
59 as **ordinary trappable codes through the shared `raise_error_hl` decision**,
touches `ONEFLG` nowhere, and §5c's open ONEFLG question does not arise on this
path.

⚠️ **The lesson is [[chancost-slice]]'s own, one turn further: compare error
CLASSES, never wording — and then check what else the row typed.** A row with a
statement between the arm and the error measures the statement.

### 5d.4 The gate

`make chancost-characterize`: **39 cases** (was 31), **4 filed divergences**
(was 6). Four rows closed outright — `sem_zero`, `sem_hinum`, `sem_reopen`,
`err_notopen` — and eight rows were added:

* `bfn_trap` / `bfn_zero` / `fno_eof` — ERR 52 and 59 with **nothing** between
  the arm and the error, so they measure the code and not its neighbours;
* `bfn_ctl` — the two-sided control. A build where **no** handler ever fires
  would score the other three "agree" on the abort text alone; this row must
  read 7005 on both machines for them to mean anything;
* `mf_disarm`/`mf_ctl`, `clr_disarm`/`clr_ctl` — the disarm finding itself,
  each with its statement REMmed out in the twin.

Of the 4 that remain, `lof_new` is the pre-existing LOF bug and the other three
are **one** newly-measured error-handling defect (§5d.5), not this slice's.

`tests/test_msgenc.py` gained both messages, and its phrase count is now read
from the ROM's own `MSGESC_HI` instead of a hardcoded 4 — otherwise the fifth
phrase could have landed with the decoder bound un-bumped, which is exactly the
"one fact in two places" drift that left `err_msgtab`'s ERR 25 entry dead for a
whole arc ([[msgtab-bound-drift]]).

### 5d.5 What this slice FOUND and did NOT fix

Both are error-handling defects, both pre-date S-FCH-2, both are filed in
[`TODO.md`](../TODO.md) rather than absorbed here.

1. **`CLEAR`/`MAXFILES` do not suppress an armed `ON ERROR` handler in zerobas;
   on the reference they do.** ✅ **FIXED 2026-07-29 —
   [`docs/spec-basic-onelin-reset-scope.md`](spec-basic-onelin-reset-scope.md)**
   (14-row VG-8020 battery, net **0 B**, three rejected builds). The measured
   rule: a handler is disarmed exactly when the VARIABLE TABLE IS CLEARED — RUN,
   NEW, `CLEAR` (direct-mode *and* in-run, so `MAXFILES`) and **every program
   EDIT**. The zero moved from `run_prog` into `vars_reset`, the one routine all
   five reach. `err_badchan`, `mf_disarm` and `clr_disarm` all left this probe's
   `KNOWN_DIVERGE` the same day (4 filed divergences → 1).
   🔴 **TWO CLAIMS THIS SECTION MADE WERE FALSE, AND BOTH COST A WHOLE ARC.**
   (a) *"`reset_scope_clear` … the reference DOES fire the handler there"* — it
   does not. That row's marker was the literal `R<LEAKED>`, which appears in the
   case's **own source echo**, so the row read TRUE on every machine in every
   build and had never measured anything (new slice §2.1; now repaired and
   oracle-locked). (b) The conclusion drawn from it — *"the fix is `ONELIN`
   invalidation at relink, NOT `clear_vars`"* — is wrong too: the reference
   disarms on an **append that moves nothing**, so the trigger is the edit, not
   the move. `clear_vars` was indeed the wrong site, but for the opposite
   reason: not because `RUN` must not disarm (**`RUN` does disarm** — measured
   unconfounded), but because a program edit never reaches `clear_vars`.
   **A vacuous gate row does not merely fail to inform — it actively steers.**

2. **A stale `ONEFLG` survives the return to the REPL.** ✅ **FIXED 2026-07-29 —
   [`docs/spec-basic-oneflg-reset-scope.md`](spec-basic-oneflg-reset-scope.md)**
   (11 B, three sites, seven standing gate rows). The row filed here turned out
   to be **one of six** divergent rows: the reference clears `ONEFLG` on any
   abort *and* on any run termination, but keeps it across a `STOP` suspension.
   The battery also filed two unrelated defects it walked into (ERR 21
   `No RESUME` is never raised; `CONT` after `END` must continue).
   After a nested forced
   abort, zerobas force-aborted the *next* error instead of trapping it; the
   reference traps it. Two-sided (measured through the KEYBUF driver, which the
   `openMSX type` harness could not do — its first attempt doubled a keystroke
   into line `3300` and the resulting `undefined line` read exactly like a
   semantic failure, [[read-the-screen-when-a-probe-fails]]):

   | | reference | zerobas |
   |---|---|---|
   | after a nested forced abort, re-arm and re-raise | **traps** | **force-aborts** |
   | control: same, no prior abort | traps | traps |

   This is §5c's open question, answered — and answered *against* zerobas. It is
   reachable today through the ordinary nested-abort path; S-FCH-2 neither
   creates nor widens it, because the new raisers never write `ONEFLG`.

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

* ⚠️ **S-FCH-2 — ERR 5 / 52 / 59. NOW MEASURED (§5c): ERR 5 is FREE and is
  LANDED; the remainder is 86 B.** Its premise had moved adversely — it was
  costed at ~100 B against **6 B** free in page 1, and page 1 now stands at
  **0 B free** — S-FCH-1 spent 5 and §3.2 spent the last 1. Option
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

