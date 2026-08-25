<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-PAINTVRAM — `PAINT` wrote the wrong VRAM, and every graphics gate was blind

**2026-08-25.** Subject: `sub/graphics.asm` `gfx_paint_row` / `gfx_span_bytes`.
Gate: `probes/basic/basic_probe_graphics.py` **PHASE H-V** (new) and PHASE H's
new `paint_then_pset`. Scope instrument: `scratchpad/vram_fidelity.py`.
Stopwatch: `scratchpad/paint_stopwatch.py`, method in
[`spec-probe-budget.md`](spec-probe-budget.md) §6.

## 1. The finding

After `SCREEN 2 : PAINT(128,96),15` on a blank screen, holding the screen and
reading both SCREEN-2 tables live:

| | pattern `$0000-$17FF` | colour `$2000-$37FF` |
|---|---|---|
| Philips VG-8020 | all `$00` | all `$0F` |
| National CF-3300 | all `$00` | all `$0F` |
| zerobas (pre-fix) | all `$FF` | all `$F4` |

Both references fill by rewriting the colour byte's **background** nibble and
never touch the pattern; zerobas filled via the **foreground** path — one pixel
at a time through the colour-clash RMW, exactly as eight `PSET`s would.

Both render colour 15 everywhere, `POINT(128,96)` reads 15 on all three, and
`PAINT` completes with `ERR 0` on all three.

## 2. Why 372 green rows saw nothing

🔴 **Every PAINT row in the module reads through `POINT`, and `POINT` collapses
the pattern bit and both colour nibbles into one number.** Two engines can agree
on every visible pixel while storing the screen completely differently. The same
blindness was recorded once before, by the ntwall scout
([`ntwall-scout-2026-08-22.md`](ntwall-scout-2026-08-22.md)): *"the two engines
write different bytes … `POINT` is blind to it"* — filed, and the gate row that
could see it was never written. This slice is that row.

Under the faithful-MSX1 charter the bytes are part of the contract, for two
independent reasons: **`VPEEK` is a BASIC statement**, so a program can read
them; and SCREEN 2's colour clash makes the **next** write into a cell depend on
which nibble currently holds what.

## 3. Scope was MEASURED, and it is PAINT-only

`scratchpad/vram_fidelity.py`, eight primitives × three machines, **both** tables
captured live (12288 bytes per side):

| primitive | pre-fix |
|---|---|
| blank SCREEN 2, PSET, PSET c=1, LINE, LINE `,BF`, CIRCLE | ✅ byte-identical |
| `PAINT` bounded by a circle | 🔴 2592 of 12288 differ |
| `PAINT` whole-screen flood | 🔴 12288 of 12288 differ |

🟢 **So the shared pixel-write path is faithful** — colour-clash behaviour
included (`,BF` matches across 2882 colour cells). The defect was PAINT's own
span write, which is what made the fix local.

## 4. The rule, and this ROM already had it

D-BFBYTE ([`bffill-msx1-characterization.md`](bffill-msx1-characterization.md))
measured it for `LINE ,BF` a slice earlier: **a run that covers all eight pixels
of a cell row is written blind as `pattern := $00`, `colour := C` — the colour in
the BACKGROUND nibble, foreground FORCED to 0** (measured for two colours, and
over a pre-stained cell, so the fg really is forced and not inherited).

`PAINT` fills by horizontal spans, so the identical split applies:

```
       [ left partial ] [ whole bytes ] [ right partial ]
```

The two partials stay on the per-pixel clash RMW — that is what both machines do
there — and every wholly covered cell is written blind.

## 5. What changed

* `gfx_span_bytes` — the blind whole-byte loop, **extracted** from `gbf_row` and
  now shared by `LINE ,BF` and `PAINT`. Unchanged behaviour for its old caller.
* `gfx_paint_row` — new: splits the span with the existing pure `gbf_split`,
  runs the partials through `gpr_part` (per-pixel `gfx_paint_plot`), tail-calls
  `gfx_span_bytes` for the whole cells. **SCREEN 2 only** — in MULTICOLOUR a byte
  is two cells and there is no colour table, so the pre-existing per-pixel loop
  (`gpr_pixels`, moved but not changed) still runs, and it is also the only one
  that honours `GFX_PPITCH`'s 4.
* `gfx_paint_extend_lr` is **untouched**: it still paints each newly discovered
  pixel inline as it walks, which is what lets the walk cross a chain of
  clash-"eaten" wall pixels in one pass (its own header). Those writes are then
  overwritten by the span's byte fill, which is the reference's own end state.

💰 **99 B of sub page 0** (2563 → 2464 free). `basic-reloc.rom` byte-identical —
a `sub/` tenant edit, exactly as the two-ROM rule predicts.

⚠️ **`GFX_TX1`/`GFX_TX2` are `gbf_split`'s inputs and are borrowed here.** They
are the BOX corner stashes and are dead for the whole of a `PAINT`: a PAINT is
marshalled through `GXPOS`/`GYPOS` + `GFX_C`/`GFX_B`, which `gfx_paint_flood`
reads once, before any of this runs.

🔴 **The carry test in `gpr_mul` is load-bearing.** 32 cells starting at x=0 end
at 256, which wraps to 0 in 8 bits and would "start" a right partial at column 0
— i.e. repaint the entire row per-pixel. It is the same 8-vs-16-bit trap
`gbf_split`'s own header records for `LINE(255,0)-(255,0),,BF`.

## 6. The gate

**PHASE H-V** (byte-level, PHASE A's shape: explicit one-byte VRAM segments,
reference vs zerobas, with the oracle asserted on the **reference**):

| row | cell | ref | pre-fix zb |
|---|---|---|---|
| `flood_wholebyte.0` | (128,96) | `00`/`0f` | 🔴 `ff`/`f4` |
| `flood_wholebyte.1` | (8,8) | `00`/`0f` | 🔴 `ff`/`f4` |
| `flood_c_ne_b` | (128,96) | `00`/`09` | 🔴 — |
| `box_span_cells.0` | (24,30) WHOLE | `00`/`07` | 🔴 `ff`/`74` |
| `box_span_cells.1` | (16,30) left partial | `0f`/`74` | ✅ `0f`/`74` |
| `box_span_cells.2` | (56,30) right partial | `f8`/`74` | ✅ `f8`/`74` |
| `box_span_cells.3` | (8,30) outside | `00`/`04` | ✅ `00`/`04` |

**PHASE H `paint_then_pset`** — the same divergence through `POINT`, and the row
that says this is a bug and not cosmetics:
`PAINT(128,96),15 : PSET(128,96),6` then `POINT` at (128,96), (129,96), (135,96)
→ references `6 15 15`, pre-fix zerobas `6 6 6`. The references leave the cell
all background, so the `PSET` claims the free foreground nibble for its ONE
pixel; the old encoding left it all foreground, so the same `PSET` rewrote the
shared fg nibble and recoloured **all eight**. `gbf_row`'s header states the
identical consequence for `,BF`.

### 6.1 Two things the gate's own design had to learn

🔴 **A `C != B` FIXTURE HAS NO BOUNDED FILL, SO IT HAS NO PARTIAL CELLS.**
Draft 1 of `box_span_cells` used the module's standard `BOX` (drawn in 15) with
`PAINT(30,30),9,15`, and all three cells came back identical **on both sides** —
the fill had escaped and flooded the screen everywhere, so the two "partial"
controls were reading whole-byte territory and controlled nothing. That is the
references' own measured dichotomy, not an accident: **`C == B` is bounded,
`C != B` floods the entire screen whatever is drawn**
([`ntwall-scout-2026-08-22.md`](ntwall-scout-2026-08-22.md)). Hence `C = B = 7`,
and hence the fourth cell, **outside** the box: without it the case cannot tell a
bounded fill from a flood, which is exactly how draft 1 fooled itself.

⚠️ **DENOMINATOR, because it is a real hole and not a choice:** the partial-cell
controls therefore exist **only** with `C == B`. A bounded fill requires `C == B`
on the references, and an unbounded one runs every span the full 0..255 — 32
whole cells with no partial at either end. No fixture on these machines puts a
partial cell and `B != C` together. `flood_c_ne_b` carries the *which colour*
question alone, and it exists because every other row here has `B == C` and would
have passed a fill that wrote the **border** colour.

## 7. Speed: HALVED, NOT CLOSED — and the second factor is named

Exact emulated-time durations (mark stopwatch; deterministic, repeats
bit-identically). "ref" = the faster of the two references.

| operation | vg8020 | cf3300 | zb before | zb after | |
|---|---|---|---|---|---|
| `PAINT(128,96),15` flood | 14.736728 | 15.536890 | 46.252527 | **29.742824** | 🔴 2.98× → **2.02×** |
| `CIRCLE:PAINT` bounded | 3.885463 | 4.097390 | 10.874419 | **7.403163** | 🟠 2.65× → **1.91×** |
| `CIRCLE(128,96),80,15` | 0.409343 | 0.430918 | 0.253305 | 0.253305 | ✅ 0.62× (faster) |
| `LINE(0,0)-(255,191),15` | 0.135319 | 0.142345 | 0.122553 | 0.122553 | ✅ 0.91× |

🔴 **A PREDICTION MISSED, AND IT IS THE USEFUL KIND.** Before the run I predicted
the flood would land *under* 15 s — reasoning from `gbf_row`'s own "two blind
writes per byte instead of eight read-modify-writes … and it is the whole 23×".
It did not. The 23× applies to the **write**, and the write is no longer where
PAINT spends its time. The filed item said *"expect a SECOND factor and do not
stop at the first explanation that fits one row"*; it was right.

📏 **CANDIDATE FOR THE RESIDUE, then measured in §7.1.** Per span, `gfx_paint_process` now writes 32 blind cells (64 VDP writes) — but
`gfx_paint_scan_row` still tests **every column one pixel at a time**, and it
runs on **two** neighbour rows: 512 `gfx_paint_inside` calls, each a
`gfx_calc_addr` plus two fetch-window VDP reads. That would be far more traffic
than the fill it feeds, and removing the per-pixel fill would then remove about
half the total work — which is what 46.25 → 29.74 (1.56×) says. **But a number
that fits one row is exactly what the filed item warned against**, so §7.1
counts it instead of arguing it.

### 7.1 Counted, not argued

`scratchpad/paint_callcount.py` drives the REAL `gfx_paint_op` in the host Z80
sim (tests/msxtest) with the three VDP-touching leaves trapped and counted, over
three box sizes so the SCALING is measured rather than assumed. `gfx_paint_read`
= 2 VDP reads (pattern + colour, each with the fetch-window settle);
`gfx_paint_plot` = 2 reads + up to 2 writes; `gfx_span_bytes` = 2 blind writes
per whole cell.

| box interior | painted px | `_read` | `_plot` | whole cells | VDP reads | VDP writes | scan share |
|---|---|---|---|---|---|---|---|
| 4,4-36,28 | 713 | 1505 | 191 | 69 | 3392 | 520 | **76.9 %** |
| 4,4-68,52 | 2961 | 6081 | 391 | 329 | 12944 | 1440 | **84.6 %** |
| 4,4-132,100 | 12065 | 24449 | 791 | 1425 | 50480 | 4432 | **89.0 %** |

🎯 **THE SCAN IS THE RESIDUE, AND ITS SHARE RISES WITH AREA — 76.9 % → 89.0 %.**
At the largest box, 48898 of 54912 total VDP accesses are neighbour-row/walk
pixel TESTS; the blind byte fill this slice installed is 2850 of them, ~5 %.
There are ~2 `gfx_paint_read` calls per painted pixel, which is exactly "two
neighbour rows per span". **The write is no longer where PAINT spends its time,
which is why the 23× did not appear in the stopwatch.**

🎯 **THE CANDIDATE FIX IS PURE CACHING, NOT A SEMANTICS CHANGE.** Eight
consecutive columns of a row share ONE pattern byte and ONE colour byte, and
`gfx_paint_scan_row` only TESTS — it never writes — so the row's VRAM is stable
across its own pass: read the pair once per cell and answer eight columns from
it. Its own slice, its own measurement.
