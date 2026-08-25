<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-PAINTSCAN — the scan cache was built, measured, and DECLINED

**2026-08-25**, on [`spec-basic-paintvram.md`](spec-basic-paintvram.md) §7's filed
residual. **No ROM change shipped.** `sub.rom` is `ae796ccb` before and after,
sub page 0 free 2464 B both sides.

Instruments (all committed): `scratchpad/paintscan_scout.py` (hit-rate pricing),
`scratchpad/paintscan_ramclaim.py` (the aliasing verification),
`scratchpad/paint_stopwatch.py` (the emulated-time stopwatch).

## 1. What was built

D-PAINTVRAM left `PAINT` 2.02× slower than both references and counted the
cause: `gfx_paint_scan_row` tests every column one pixel at a time, and the scan
is 76.9 % → 89.0 % of all VDP accesses as the fill grows. The named candidate was
a **one-entry read cache** — eight consecutive columns of a row share one pattern
byte and one colour byte, and the scan never writes.

It was implemented in full: a tag/pattern/colour cache in `gfx_paint_read`'s
SCREEN-2 arm, invalidated by every VRAM write inside a PAINT
(`gfx_paint_plot`, `gfx_paint_row`'s byte fill, and once at `gfx_paint_op`
entry). **42 B of sub page 0.** All correctness held: unit-test 59/59,
PHASE H-V 12/12, `vram_fidelity.py` 0 divergent cases.

## 2. The two things that were measured first, and were right

🟢 **The hit rate.** `paintscan_scout.py`, against the real `gfx_paint_op` in the
host Z80 sim, over three box sizes, **modelling the invalidation the real thing
would need** (so these are post-invalidation rates, not an upper bound):

| box interior | tests | distinct (row,cell) | 1-entry hit rate | unbounded ideal |
|---|---|---|---|---|
| 4,4-36,28 | 1505 | 125 | 79.5 % | 91.7 % |
| 4,4-68,52 | 6081 | 441 | 83.5 % | 92.7 % |
| 4,4-132,100 | 24449 | 1649 | **85.5 %** | 93.3 % |

🟢 **The RAM.** The cache needs 4 B and the usual regions are exhausted
(`sysvars.inc`: *"SQRT_POW10 took the last free byte"*), so it aliased
`GFX_CX`/`GFX_CY`. **That is a claim, and this project has been bitten by
aliasing claims, so it was verified two independent ways** — neither of which
was allowed to be vacuous:

* **STATIC** — the gate's own fallthrough-aware call-graph walker
  (`tools/check_tenant_closure.py`): the **62-routine closure of
  `gfx_paint_op`** over 67 sources mentions neither cell. Control: **10 routines
  elsewhere in the sub image DO** (`gbi_start_p1/p2`, `gbn_*`), so the scan is
  not silently matching nothing.
* **DYNAMIC** — the real `gfx_paint_op` run twice with the cells seeded to
  different poison values: **identical 3185-pixel fill** (so PAINT never READS
  them) and **both seeds intact afterwards** (so it never WRITES them).

**That verification stands and is reusable** — it is the expensive part of any
future design that wants these 4 bytes.

## 3. 🔴 THE PROJECTION WAS FALSIFIED BY THE STOPWATCH

Predicted, from the access counts: removing 85.5 % of the scan's read pairs takes
the largest box from ~54.9 k accesses to ~13 k — **24 % of today** — so the flood
should land far under the references' 14.7 s.

Measured (mark stopwatch; emulated time, deterministic):

| operation | vg8020 | cf3300 | zb before | zb with cache | |
|---|---|---|---|---|---|
| `PAINT(128,96),15` flood | 14.736728 | 15.536890 | 29.742824 | **26.193087** | 2.02× → **1.78×** |
| `CIRCLE:PAINT` bounded | 3.885463 | 4.097390 | 7.403163 | **6.622417** | 1.91× → **1.70×** |

**1.14×, not 4×.**

🎯 **AND THE MISS IS THE FINDING: TIME IS NOT PROPORTIONAL TO VDP ACCESSES.**
Removing ~85 % of what was ~89 % of all accesses bought 12 % of the time. If the
reads had dominated, that same removal would have bought ~76 %. So the reads are
a **minority** of PAINT's cost, and the arithmetic says where the rest is:
`gfx_rd_raw` is two `out`s, a three-`nop` fetch-window settle and an `in` —
**~85 T-states** — while the per-column loop around it (`gpsr_loop`/`gpsr_test`
bookkeeping, `gfx_paint_inside`'s four RAM loads and two stores, `gfx_calc_addr`,
`gfx_point_extract`, and the `call`/`ret` overhead) is **comparable or larger**,
and the cache does not remove any of it. It even adds the tag compare to every
read, hit or miss.

🟢 **`PAINT` IS Z80-LOOP-BOUND, NOT VDP-BOUND.** That is the durable result of
this slice, and it retargets the residual: the fix must reduce the **per-column
iteration cost**, not the read count.

## 4. Why it was DECLINED rather than shipped

It works, it is measured, and every gate is green — and it was still reverted:

1. **The justification was falsified.** It was designed for ~4× and delivers
   1.14×.
2. **It does not close the item.** 1.78× is still "significantly slower than both
   references", which is the user's stated threshold. Shipping it would change
   the number in the TODO without changing its status.
3. **It is not free.** 42 B is cheap, but the real price is a permanent
   invariant — *every VRAM write inside a PAINT must invalidate the cache* — plus
   an aliasing coupling to the Bresenham cells. A future change that let PAINT
   share `gfx_plot_cur` with LINE would corrupt silently.
4. **The right fix subsumes it.** Testing eight columns from one fetched pair
   *inside* `gfx_paint_scan_row` removes the reads **and** the per-column call
   and RAM traffic. Shipping the cache now is shipping the wrong half.

💰 **DECLINED WITH NUMBERS**, the same way D-PAINTMC declined its draft.

## 5. What the successor should do

Restructure `gfx_paint_scan_row` so the unit of work is a **cell, not a column**:
fetch the pattern/colour pair once, then answer up to eight columns from
registers without leaving the loop — no `call gfx_paint_inside` per column, no
`GFX_PTESTX`/`GFX_PTESTY` round trip, no `gfx_calc_addr` per column. Keep the
partial cells at the span ends on the existing per-column path, exactly as
`gfx_paint_row` already does for the write side.

⚠️ **SCREEN 2 only** — MULTICOLOUR has no colour table and a pitch of 4.
⚠️ **The host unit test cannot see any of this**: `tests/test_graphics.py` traps
`gfx_paint_read` wholesale, so a cache or a restructure below that trap is
invisible to it. The emulator differential is the only gate with teeth here.
⚠️ **An apparatus note, not a result**: the stopwatch run that produced §3 ended
with a `TIMEOUT running Philips_VG_8020` on its third row, so the `circle` and
`line` control rows were not re-measured in that pass. The two PAINT rows — the
subject — completed and are the figures quoted.
