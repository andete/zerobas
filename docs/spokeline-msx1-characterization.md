# The reference clamps line endpoints to the screen — it never clips the ideal line

D-SPOKELINE, 2026-08-17. Closes the D-ARCMASK residual *"the reference's spoke
line advances its minor axis before the midpoint"* — which turned out to be a
corner of something much larger.

Baseline: `8c46bc9`, `sub.rom` `e4fbf667`, `graphics-acceptance` 317/0.

---

## §1 Solved offline before any emulator booted

The residual's evidence was one row: `arc_big_r400`'s spoke, ref bbox
`(128,0,129,96)` vs ours `(128,0,128,96)`, sha1 `cd7e5368` vs `76352feb`. The
banked sha was enough to invert: the reference's 97-pixel plane is uniquely the
single-crossover column pair with the seam at **y=47**
([`spokeline_char.py`](../scratchpad/spokeline_char.py) §preamble), and that
plane is reproduced byte for byte by

    clamp the endpoint to the screen:  (129,-304) -> (129,0)
    draw the line

— per-pixel clipping of the true line **cannot** put column 129 on screen at
all (its crossover is at y=−104).

## §2 Two model errors found and owned along the way

* 🔴 **My python line model's direction convention was wrong about BOTH
  machines.** Round 1 flagged two on-screen rows "ZEROBAS != MODEL"; the
  machines agreed with each other, on the seam my model called "reversed".
  [`gfx_bres_init`](../sub/graphics.asm) *sorts so the major axis ascends* —
  direction was never a divergence.
* 🔴 **My first zline transcription guessed the stepping rule and was refuted
  8/16** against the banked planes. The real `gfx_bres_next` is
  `err += DMIN; if err >= DMAJ: err -= DMAJ, step minor` with `err = DMAJ>>1`.
  Corrected, the model calibrates **16/16** on both machines' banked planes —
  and only then was it allowed to predict
  ([`spokeline_char2.py`](../scratchpad/spokeline_char2.py)).

## §3 The measurement: 23 rows, three rounds, every edge

Whole 6144-byte planes, both machines, dead-subject and on-screen controls in
every round, an exact zerobas prediction per row as the rig guard. Hypotheses
per row with a discriminating-power check — two designed rows are *provably*
vacuous and serve as three-way controls.

**The rule, `clamp_both`, matched the reference on every discriminating row
and uniquely on nine:**

| row | geometry | ref matched |
|---|---|---|
| `top_r400` / `line_bare` | spoke and plain LINE, same geometry | clamp, uniquely — **the clamp is LINE's, not the spoke path's** |
| `top_wide` | endpoint (46,−296): clamp redraws the slope ~20 columns | clamp, uniquely |
| `bot/right/left_r400` | the other three edges | clamp |
| `both_off_diag` | LINE(−50,−50)-(305,241) | **clamp_both**, uniquely — both endpoints clamp |
| `alloff_corner` | LINE(300,300)-(400,400) | **one pixel at (255,191)** — a fully off-screen LINE draws on a VG-8020 |
| `start_off_L/R/B` | first endpoint off three edges | clamp_both, uniquely |
| `spoke_start_T/L` | the spoke's start (the CENTRE) off screen | clamp_both — the centre clamps like any endpoint |
| `box_off_L` | box outline, corner off-left | clamp — **the clamped left edge draws at x=0** |
| `box_alloff` | box fully off | the (255,191) pixel again |

### 3.1 🔴 Why G3 never saw any of this

All three G3 clip rows are blind, each its own way, and that is now *measured*,
not argued: `clip_negTL`'s diagonal passes exactly through (0,0), so clamp and
clip agree; `clip_frac` is **provably vacuous** (all three hypotheses predict
one plane — re-measured green as a three-way control); and `clip_alloff`
captures the **top-left** band while the clamp's one pixel lights the
**bottom-right corner**. The gate's new `clampL_corner` row captures the band
that can see it.

### 3.2 What is NOT this path

`DRAW` calls `gfx_draw_seg` directly, bypassing `gfx_line_op` — its off-screen
behaviour is unmeasured and deliberately unchanged. Box **fill** is
clamp-invariant by construction (the visible fill of a rectangle *is* the fill
of the clamped rectangle). Arc points still clip per pixel — D-CIRCOVF's whole
off-screen-centre oracle rests on that and stays byte-identical.

---

## §4 The fix: 52 bytes, one routine, one call

[`gfx_clamp_coords`](../sub/graphics.asm) — clamp `GFX_X1/Y1/X2/Y2` in place
(X→0..255, Y→0..191), called from `gfx_line_op` after the work-area writes
(which keep the RAW p2 — the measured-on-screen behaviour) and before any
drawing, covering segments, spokes and boxes in one site. Sub p0 3506→3454;
nothing else moved. `sub.rom` `e4fbf667` → `d85a67dc`.

## §5 Verified

* All **23 characterization rows byte-identical** after the fix, all three
  probes re-run — including the (255,191) corner pixel, all four edges, both
  spoke-start rows and both box rows.
* **`graphics-acceptance` 323 PASS / 0 FAIL** — six new rows the gate now
  owns: `clampL_diag`, `clampL_corner` (the pixel `clip_alloff` was blind
  to), `clampL_start`, `clampL_box`, `clampS_wide`, `clampS_start`.
* `unit-test` 59/59 — `gfx_clamp_coords` is pure RAM and host-tested on 10
  cases including the exact-bound and int16-extreme edges.
* **Knife K-SL1** (delete the call), prediction written first: the two box
  rows return to DIFF with zerobas reading the OLD planes byte for byte
  (`ddec567c`, blank) and both controls green — **exact**.

## §6 Filed, not folded in

* **`DRAW` with off-screen coordinates is unmeasured** and bypasses the clamp.
* **The work area after an off-screen LINE is unmeasured**: `GRPACX/GXPOS`
  keep the RAW p2 today; whether the reference stores raw or clamped there is
  unknown.
* 🔴 **A re-run probe that banks to a fixed JSON path overwrites its own
  pre-fix measurement** — round 1's pre-fix planes were clobbered by the
  post-fix verification re-run (recoverable from the parent commit; the
  reduced readings survive in the session log). Version the bank path or
  refuse to overwrite.

## §7 Apparatus

| file | what it does |
|---|---|
| [`spokeline_char.py`](../scratchpad/spokeline_char.py) | round 1: endpoint hypotheses, 4 edges + LINE-vs-spoke |
| [`spokeline_char2.py`](../scratchpad/spokeline_char2.py) | round 2: the calibrated `zline` + which-endpoint rows |
| [`spokeline_char3.py`](../scratchpad/spokeline_char3.py) | round 3: box outlines |
