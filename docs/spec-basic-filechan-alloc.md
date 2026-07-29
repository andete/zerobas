# D-FCH — dynamic file-channel allocation

Make `MAXFILES` mean what it means on the reference: channel blocks **carved out
of the pool at `MAXFILES` time**, so the ceiling reaches 15, nothing is charged
for channels a program never asks for, and `FRE(0)` actually moves.

Measurement this is written from:
[`chancost-cf3300-characterization.md`](chancost-cf3300-characterization.md);
probe [`probes/disk/diskbasic_probe_chancost.py`](../probes/disk/diskbasic_probe_chancost.py)
(`make chancost-characterize`). Every number below is measured on the real
National CF-3300 unless it says otherwise.

⚠️ **Status: SPEC, awaiting sign-off. No code written.** §5 (cost) is the part
that is *not* measured, and §7 is the fork it opens.

## 1. What is wrong

zerobas reserves its channel contexts **statically and permanently**:
`FCH_CTX $EA00..$EE63` = `FCH_CEIL`(2) × `FCH_CTXSZ`(562) = **1124 B**, held
whether or not a channel is ever opened. Of each 562 B, **512 B is nothing but a
save copy** of the single global `FSECTOR_BUF` — `fch_save_active` /
`fch_load_ctx` `memcpy` it in and out
([`basic/files.asm:994`](../basic/files.asm:994)).

Measured consequences:

| | reference | zerobas |
|---|---|---|
| per channel | **267 B** | 562 B |
| ceiling | **15** | 2 |
| `FRE(0)` vs `MAXFILES` | −267/channel | **does not move** (13875 at 0, 1 and 2) |
| charged when | at `MAXFILES` time | always |

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

| row | reference | zerobas today |
|---|---|---|
| `A=5 : MAXFILES=2 : PRINT A` | **0** — variables are CLEARed | `5` |
| `A=5 : REM MAXFILES=2 : PRINT A` — *control* | `5` | `5` ✅ |
| `A=5 : MAXFILES=1 : PRINT A` (**value unchanged**) | **0** — clears anyway | `5` |
| `A$="XY" : MAXFILES=2 : PRINT A$` | empty | empty ✅ |
| `CLEAR 500 : MAXFILES=2 : PRINT FRE("")` | **500** — pool size SURVIVES | `500` ✅ |
| `OPEN…AS #1 : MAXFILES=2 : PRINT LOF(1)` | **`File not OPEN`** | `-1` |

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

### 3.2 Carve the table out of the pool

Today the ceiling for program text is `min(HIMEM,TXTMAX)`, and D-CLP already
established the single-moving-boundary model with the string pool below it
(`min(HIMEM,TXTMAX) − POOLSIZE`, derived sub-side — S-CLP-2). D-FCH adds one
more term:

```
channel table base = min(HIMEM,TXTMAX) − POOLSIZE − MAXF × FCH_BLKSZ
```

so `MAXFILES=n` moves a boundary that `FRE(0)` already reports, and the
statement's measured `CLEAR` (§2.2) is exactly the invalidation that move needs.

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

## 4. Scope boundary

**In:** the shared-cache switch, the dynamic table, `FCH_CEIL` 2 → 15, the
`MAXFILES` `CLEAR` side effect, ERR 5 / 52 / 59, and the `TOKBUF`+`LINEBUF`
relocation that turns the freed RAM into program space.

**Out:** `LOF(#n)` returning −1 on a freshly-created OUTPUT channel (reference:
0) — filed separately in [`TODO.md`](../TODO.md), it is a `LOF` bug rather than
an allocation one, and its fix should not ride on this slice's carve. Also out:
raising `FCH_CEIL` beyond 15, and any change to `DETOKBUF`.

## 5. Cost — ⚠️ NOT MEASURED

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

## 6. The gate

`make chancost-characterize` already carries the batteries and self-checks the
reference's recorded answers for drift. To become an acceptance gate it needs:

* the ladder asserted as a **slope**, both sides — reference 267, zerobas 267
  after the change (today: 0, statically reserved);
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

## 7. Sign-off questions

* **S-FCH-1 — the carve.** The slice needs an unknown number of ROM bytes
  against 9 B / 6 B free, so a carve is near-certain and its scouting has
  repeatedly been the expensive part of a slice. **Recommended: build §3.1
  alone first, on a branch, and measure.** It is common to every version of this
  slice, it is the change that frees the 1124 B, and its measured size is the
  input every remaining decision needs. Do not scout a carve for a requirement
  that is still a guess.

* **S-FCH-2 — ERR 52 / 59 vs a dense `err_msgtab`.** Reaching code 59 densely
  costs ~100 B for two messages. Options: (a) extend the table (simple, dear);
  (b) a small **sparse** side-table for the disk block, which the file verbs are
  the only users of; (c) land the allocation work and leave both codes raising
  today's `syntax error`, filing the codes separately. ⚠️ (c) leaves
  [`files.asm:332`](../basic/files.asm:332)'s comment still naming an error it
  does not raise, at six sites. **Recommended: (b)**, but only after S-FCH-1
  gives a real budget.

* **S-FCH-3 — `FCH_CEIL` 15 vs the free-RAM trade.** 15 is the measured
  reference ceiling and the charter is faithfulness, so 15 is the answer *if*
  the blocks are dynamic — because unused channels then cost nothing and the
  ceiling is free. This question only reappears if S-FCH-1 shows dynamic
  allocation is unaffordable and the slice falls back to a static table, where
  15 costs the entire +1024 B (see the decision table in `TODO.md`).

* **S-FCH-4 — the extra disk I/O on channel switch.** Flush-and-re-read makes a
  channel switch cost real sector traffic where today it is a `memcpy`. The
  reference accepts exactly this. Interleaved-write fixtures
  (`disk_probe_maxfiles.py`) will get slower and, per D-CLP's experience with
  O(n) collections, **a slower row can outrun the capture window and read back
  as its own echo**. Budget for re-timing that probe rather than discovering it
  as a flake.

* **S-FCH-5 — `MAXFILES` now clears variables.** This is measured-faithful
  (§2.2) but it is a real behaviour change: any fixture that sets a variable and
  then calls `MAXFILES` will see it reset. Same class of change as D-CLP's
  200-byte default. **Recommended: take it, and re-run the full corpus** —
  `diskbasic-acceptance`, `array-acceptance`, `clearpool-acceptance` — rather
  than trusting that no fixture does this.
