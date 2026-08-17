# A box fill writes whole bytes as BACKGROUND, and that is why it is 23× faster

D-BFPERF (measurement) + D-BFBYTE (implementation), 2026-08-17. Opened from the
residual D-DRAWCLAMP filed the same day — *"zerobas's full-screen `BF` fill
outruns a 20 s emulated step where the reference completes"* — which said
**"not priced, measure it first"**. Measured, and it was not a performance
residual: it is a fidelity defect whose faithful fix is also the fast one.

Baseline: `5d9f1d8`, `sub.rom` `81b952f6`, `graphics-acceptance` 344/0.
Shipped: `sub.rom` `aeed6276`, **355/0**, sub p0 3416 → 3263 (**153 B**).

---

## §1 The timing, and the control that makes it mean something

`TIME` is the VDP frame counter; an empty `FOR` loop of the same iteration
count is measured on the same machine and subtracted, at **every** distinct
iteration count used ([`bfperf_time.py`](../scratchpad/bfperf_time.py)).

| row | px | reference | zerobas | ratio |
|---|---|---|---|---|
| `bf_dead` (1×1) | 1 | 4.0 ms | 7.0 ms | 1.75× |
| `bf_1row` (256×1) | 256 | **7.5 ms** | 112.5 ms | **15.00×** |
| `bf_1col` (1×192) | 192 | 92.5 ms | 120.0 ms | 1.30× |
| `bf_64` | 4096 | 115 ms | 1685 ms | 14.65× |
| `bf_full` (whole screen) | 49152 | **860 ms** | **20040 ms** | **23.30×** |
| `bf_off` (the residual's row) | 49152 | 860 ms | 20040 ms | 23.30× |
| `box_full` (outline) | 896 | 350 ms | 370 ms | 1.06× |
| **`line_diag`** | 256 | 117.5 ms | 117.5 ms | **1.00×** |

**`line_diag` at 1.00× is the whole reason this is diagnosable.** Our segment
rasteriser is not slow — it is *exactly* the reference's speed, to the frame.
The box outline is 1.06×. The entire gap is the fill, and 20040 ms explains the
20 s step that returned nothing.

`bf_1row` against `bf_1col` localises it further: the same routine, 256 px in
one scanline versus 192 scanlines of one pixel. zerobas costs ~410–460 µs/px in
*every* row of the table. The reference costs ~460 µs/px on a line, ~480 on a
one-pixel-wide fill — and **29 µs/px on a filled scanline**. The reference has
a second, byte-wise path; we have one cost model.

`bf_off` matching `bf_full` to the millisecond is an independent confirmation
of D-DRAWCLAMP's clamp, in time rather than in pixels: a *clipped* fill would
have done strictly more work.

## §2 🔴 The fast path is not an optimisation — it writes different bytes

Captured through the debugger with SCREEN 2 still up
([`bfperf_colour.py`](../scratchpad/bfperf_colour.py)):

| row | ref pattern / colour | zerobas pattern / colour |
|---|---|---|
| `full_cell` (`…,15,BF`) | `00` / `0f` | `ff` / `f4` |
| `full_cell_c6` (`…,6,BF`) | `00` / `06` | `ff` / `64` |
| `half_cell` (4 px wide) | `f0` / `f4` | `f0` / `f4` — **agree** |
| `line_not_fill` (8 px as a LINE) | `ff` / `f4` | `ff` / `f4` — **agree** |
| `span_partial_ends` | `1f`·`00`·`f8` / `f4`·`0f`·`f4` | `1f`·`ff`·`f8` / `f4`·`f4`·`f4` |

**The rule: when a fill covers all 8 pixels of a cell row, the reference writes
pattern `$00` and puts the colour in the BACKGROUND nibble (`fg = 0`).** Two
colours pin the encoding — 15 gives `$0f`, 6 gives `$06`; one colour could not
have. `full_cell_stained` shows the foreground nibble is *forced* to 0, not
inherited: a cell pre-stained to fg 6 still ends at `$0f`.

Partial runs keep the ordinary per-pixel path, and both machines agree there.
`span_partial_ends` shows all three cases in one row: partial, whole, partial.

Two blind writes per byte instead of eight read-modify-writes, each of which
costs two VDP reads and two VDP writes. That is the 15×.

## §3 ⚠️ It is VISIBLE, so this is a correctness defect

Both machines render the fill identically — 8 white pixels either way, one via
foreground and one via background. The divergence appears on the **next** draw
into that cell:

`LINE(0,0)-(7,7),15,BF : PSET(0,0),6`

| | pattern | colour | what you see |
|---|---|---|---|
| VG-8020 | `80` | `6f` | one pixel in 6, **seven still 15** |
| zerobas | `ff` | `64` | **all eight pixels turn 6** |

On the reference the cell was all-background, so the `PSET` sets one bit and
claims the free foreground nibble. On ours the cell was all-foreground, so the
`PSET` collides with the existing foreground and repaints the whole cell. This
is the SCREEN 2 colour clash behaving differently because the *storage* differs.

So the fix is not a speed-up that risks fidelity; **the faithful implementation
is the fast one**, the same shape as D-ARCMASK.

## §4 🔴 The gate's only BF row cannot see any of this

`box_bf` is `LINE(1,1)-(14,10),15,BF`. It spans x 1..14: cell 0 gets x1..7 and
cell 1 gets x8..14 — **seven pixels each, so not one whole byte is covered.**
The fast path never engages, and the row is green under both rules. It is also
pattern-plane only (`col=False`), so even a covered byte would have hidden the
colour half.

That is the third gate row this week found blind by re-deriving it rather than
trusting it — after G3's three clip rows (D-SPOKELINE) and G6's `clip_left`
(D-DRAWCLAMP). The common shape: **a row written to cover a case, whose
geometry cannot reach the case.**

## §5 The fix: 153 bytes, three routines

Priced at 120–180 B before it was written; **spent 153 B**, sub p0 3416 → 3263.

* [`gbf_split`](../sub/graphics.asm) — the per-scanline split, `fl = (xl+7)>>3`
  and `fr = ((xr+1)>>3)-1`, returning the whole-byte count in `B` and the first
  whole cell's x in `D`. **Pure**, so it is host-driven in
  `tests/test_graphics.py`.
* [`gbf_row`](../sub/graphics.asm) — whole bytes first (two blind writes each,
  no reads, `di` once per byte rather than once per bit), then the two partial
  ends through the landed per-pixel rasteriser. The fast pass runs first
  because the split is a pure function of `TX1/TX2` but `gfx_draw_seg` clobbers
  every register, so running it last would mean computing it twice.
* [`gfx_box_fill`](../sub/graphics.asm) — sorts the corners (`gfx_box_stash`
  does not, and the old code did not care because `gfx_draw_seg` sorts
  internally) and no longer preloads `GFX_X1/X2`, which `gbf_row` now rewrites
  per partial.

### 5.1 ⚠️ Both halves of the split are 16-bit ON PURPOSE

`xl+7` overflows a byte for `xl > 248` (255+7 = 262) and `fr` reaches −1 for
`xr < 7`. Computed in 8 bits, `LINE(255,0)-(255,0),,BF` would report `fl=0`,
`fr=31` and blind-fill the entire scanline — **one pixel asked for, 256
destroyed.** That row is in the gate as `bfbyte_x255` and in the host tests as
`gbf_split (255,255) -> 0`.

## §6 Verified

* **355 PASS / 0 FAIL** (344 + 11 new rows), including the teeth row and both
  splitter controls. Every previously divergent reading is now byte-identical.
* All 7 edge rows and all 9 colour rows agree; the 6 that were DIFF are gone.
* `unit-test` — 19 new host cases over `gbf_split` and `gbf_shr3`, covering
  both 8-bit traps directly.
* Simulated before a line of Z80 was written
  ([`bfbyte_sim.py`](../scratchpad/bfbyte_sim.py)): the model reproduced **all
  11 measured reference readings** first, and the first build was green.

### 6.1 ⏱️ And the speed, which was the consequence

| row | before | after | reference |
|---|---|---|---|
| `bf_full` (whole screen) | 20040 ms | **560 ms** | 860 ms (**0.65×**) |
| `bf_1row` (256×1) | 112.5 ms | 10.0 ms | 7.5 ms |
| `bf_64` | 1685 ms | 290 ms | 115 ms |
| **`bf_1col` (1×192)** | **120 ms** | **145 ms** | 92.5 ms |

**35.8× on the full screen, and we are now faster than the VG-8020 — but
`bf_1col` got 21% SLOWER and that is reported, not buried.** A 1-pixel-wide
fill has no whole byte in any of its 192 rows, so every row pays `gbf_split`
(~130 µs) and gets nothing back. It is a real, measured regression on the
narrowest case, accepted against 35.8× on the common one.

## §7 Knives — 3 predicted, 3 exact

Predictions in [`bfbyte_knives.md`](../scratchpad/bfbyte_knives.md), written
first. 🔴 **Every cut corrupts a value in place rather than deleting a call** —
K-DC3 one commit earlier taught that lesson the hard way: removing the only
call to a routine leaves it unreachable, `check_dead_code.py` fails the build,
and the knife scores nothing because no ROM exists.

* **K-BB1** (`pattern := $FF`) — reddens the three pattern rows and **leaves
  every colour twin green**, including `bfbyte_teeth_c`.
* **K-BB2** (colour from `GFX_TX1`) — reddens the five colour rows, leaves the
  pattern rows green, and leaves **`bfbyte_c0` green by coincidence** (its
  colour and its `xl` are both 0). Predicted as a coincidence in advance.
* **K-BB3** (invert the corner sort) — reddens all nine discriminating rows,
  leaving only the two splitter controls green.

## §6 Apparatus, and one retraction

| file | what it does |
|---|---|
| [`bfperf_time.py`](../scratchpad/bfperf_time.py) | the timing table, empty-loop control at every N |
| [`bfperf_colour.py`](../scratchpad/bfperf_colour.py) | the plane rule, the encoding, the boundary, the teeth |

🔴 **Round 1 of the colour probe was invalid and its DEAD SUBJECT said so.** It
read the cells with `SCREEN0:PRINT"C";VPEEK(0);…` — which switches to SCREEN 0,
where `$0000` is the name table, and then prints into that table before the
later `VPEEK`s are evaluated. The readout was overwriting what it read, and
`dead_nofill` diverged (32 vs 67 — a space against the letter `C`) with **no
fill in the program at all**. Every "finding" in that round was the apparatus.
Round 2 captures VRAM through the debugger with SCREEN 2 still up.
