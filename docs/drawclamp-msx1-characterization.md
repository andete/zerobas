# DRAW obeys LINE's clamp, and the work area does not

D-DRAWCLAMP, 2026-08-17. Closes both residuals D-SPOKELINE filed
([`spokeline-msx1-characterization.md`](spokeline-msx1-characterization.md) §6):
*"`DRAW` with off-screen coordinates is unmeasured"* and *"the work area after
an off-screen LINE is unmeasured"*.

Baseline: `7310089`, `sub.rom` `d85a67dc`, `graphics-acceptance` 323/0.

---

## §1 The two answers

**`DRAW` obeys exactly the rule D-SPOKELINE measured for `LINE`: both endpoints
of every segment are clamped to the screen (X→0..255, Y→0..191) before
rasterising; the ideal line is never clipped.** Measured on 12 discriminating
whole-plane rows; the reference matched `clamp_both` on every one and uniquely
on two.

**The work area keeps the RAW coordinate — and zerobas was already right.**
`GRPACX/GRPACY` hold the unclamped p2 after every LINE, box, fill and DRAW move.
Nine rows, both machines agreeing, including `LINE(100,100)-(-50,-30)` reading
back as 65486/65506 and a fully off-screen `LINE(300,300)-(400,400)` reading
400/400. **Zero bytes** — the clamp call already sat below the work-area writes.

That second answer was a confirmation. The rows written to establish it found
something else.

## §2 🔴 What the rows found that nobody predicted

`GXPOS/GYPOS` — the *pending-target* pair, a different cell from `GRPAC` — does
**not** follow the same rule, and the split is not uniform across verbs:

| after | `GRPACX/GRPACY` | `GXPOS/GYPOS` |
|---|---|---|
| `LINE(0,0)-(300,250)` | raw 300/250 | raw 300/250 |
| `LINE(0,0)-(300,250),,B` | raw 300/250 | raw 300/250 |
| `LINE(200,150)-(300,250),,BF` | raw 300/250 | **255/191** |
| `DRAW"A0S4M300,250"` | raw 300/250 | **255/191** |
| `DRAW"A0S4BM300,250"` | raw 300/250 | untouched (blank move) |

I predicted raw/raw for `draw_m_off`. **That is a value-level miss inside a row
set whose shape was right** — the row was written to *confirm* G6's measured
`gdrw_gxpos` rule and instead refuted half of it. The other half survived: the
cells still take the endpoint with the greater y, ties to the target. Only the
*coordinate* is clamped.

Three rows pin the DRAW residue to `clamp_greatery` uniquely:

* `draw_up_off` — the target is *above* the start, so the greater-y endpoint is
  the on-screen start. Reference reports 100/150, killing "always the clamped
  target" and "the last pixel plotted".
* `draw_left_down` — x-major going left and down. The last pixel plotted is the
  greater-**x** end (200,100); the reference reports (0,191), the greater-**y**
  end. Kills "the last pixel plotted".
* `draw_m_off` — kills the raw reading, and alone cannot separate the other
  three.

And the fill residue is the **clamped box's bottom-right**, max on each axis,
*not* the last pixel painted: `LINE(200,150)-(-30,-20),,BF` fills bottom-to-top,
ending at y=0, and the reference reports 200/150.

## §3 🔴 The gate's only off-screen DRAW row is provably blind

G6 shipped `clip_left` (`PSET(5,5):DRAW"A0S4L100"`) as its off-screen coverage,
and G6 §5 concluded from it that DRAW *"clips by masking"*. The segment is
**horizontal**, and for an axis-aligned segment clamping the endpoint and
clipping the ideal line produce **the same pixels**. Re-run under this probe's
hypothesis scoring it prints `DISCRIMINATING POWER: 1`.

So the conclusion was never measured — a row that looked like coverage was
green under both rules for four months. It is kept in the gate as
`ctlD_clipleft`, relabelled as the three-way control it always was.

Every new band was scored against the banked pre/post planes
([`drawclamp_bands.py`](../scratchpad/drawclamp_bands.py)) before it was allowed
into the gate: seven must *see* the fix, the control must *not*.

## §4 The measurement

Whole 6144-byte planes, both machines, per-row hypothesis predictions with a
discriminating-power check printed before anything ran, a dead subject first,
and an exact zerobas prediction per row as the rig guard.

The line model is the tenant's own `gfx_bres_init`/`gfx_bres_next`, and it was
**calibrated 18/18 against the banked D-SPOKELINE planes on both machines**
before predicting a single DRAW row.

Four hypotheses, a cursor model × a drawing model:

| row | ref matched |
|---|---|
| `dm_off_r` / `dm_off_negy` / `dm_off_b` | clamp (target, three edges) |
| `dm_start_off_R` / `dm_start_off_L` | clamp_both — the START clamps too |
| `dm_both_off` | **clamp_both, uniquely** — the four-way row |
| `dm_alloff` | the **(255,191)** pixel again, this time from `DRAW` |
| `dm_rel_off` / `dm_scaled_off` / `dm_rot_off` | clamp — relative, scaled and rotated routes alike |
| `dm_dir_diag` | clamp — the direction-letter route (56 px → 101 px) |
| `dm_two_seg` | **clamp_both, uniquely** |

`dm_scaled_off` and `dm_rot_off` answer *typed vs transformed*: their operands
are nowhere near a screen bound, and only the scaled (×4) or rotated target
leaves the screen. **The clamp applies to the transformed target.**

`curclamp_clip` — "the cursor stores the clamped point" — is refuted twice
over: by `dm_both_off` and `dm_two_seg` on the planes, and independently by the
direct `GRPAC` readout, which is raw.

## §5 The fix: 38 bytes, three sites

* [`gdrw_move_abs`](../sub/graphics.asm) — one `call gfx_clamp_coords` before
  the rasteriser (**3 B**). The cursor write below it still reads the raw
  `GFX_DTX/GFX_DTY`, so `GRPAC` stays raw.
* [`gdrw_gxpos`](../sub/graphics.asm) — reads `GFX_X2/GFX_Y2` (the *clamped*
  endpoint cells, which `gfx_bres_init` only reads) instead of the raw
  `GFX_DTX/GFX_DTY`. **0 B.** Clamping is monotonic, so "clamp then pick the
  greater y" and "pick the greater y then clamp" agree, ties included.
* [`gfx_bf_gxpos`](../sub/graphics.asm) — new, called from `gfx_line_op`'s
  mode-2 arm only (**35 B**). Reads the corner *stash*, which the fill leaves
  intact; `GFX_Y1` by then holds the last row drawn, which is exactly the value
  the rule is not.

Sub p0 3454 → 3416. `sub.rom` `d85a67dc` → `81b952f6`; no other ROM moved.

## §6 Verified

* All **16 plane rows byte-identical** after the fix — every previously
  divergent row now reads the reference's plane byte for byte, and the three
  controls never moved.
* All **10 residue rows agree**, including both BF rows and all four DRAW rows.
* `graphics-acceptance` **344 PASS / 0 FAIL** — 21 new rows the gate now owns:
  8 plane rows in phase C and the 13-row phase R.
* `unit-test` — `gbf_max16` and `gfx_bf_gxpos` are pure RAM routines,
  host-tested on 12 cases including both corner orders and the mixed-axis case.
* `unit-test` 59/59, `rowshape-check` 26, `injector-check` 390,
  `preflight-check`, `latch-check` 16/16, `deadcode` 0/0, `audit-citations`
  clean.

### 6.1 Knives — 3 EXACT, 1 UNDELIVERABLE

Predictions written first, in
[`drawclamp_knives.md`](../scratchpad/drawclamp_knives.md); the runner asserts
the ROM hash **moves** on the cut and **returns** on the restore, so a patch
that silently failed to apply cannot score green.

* **K-DC1** (delete the clamp call) — **EXACT.** All 12 rows return to DIFF
  with zerobas reading the pre-fix planes **byte for byte** (all twelve sha1s
  as predicted), the three controls unmoved, and the two predicted knock-on
  residue rows reverting to `300 250` and `65436 250`.
* **K-DC2** (revert `gdrw_gxpos` to the raw cells) — **EXACT**, including the
  clause that mattered: **every plane row stayed green** (`DIFF rows: 0`). The
  residue and the rasterisation are independently sited, and that is now shown
  rather than asserted.
* 🔴 **K-DC3** (delete the `gfx_bf_gxpos` call) — **UNDELIVERABLE, scored as a
  miss.** The knifed tree does not build: the deletion leaves
  `gfx_bf_gxpos` and `gbf_max16` unreachable and `check_dead_code.py` fails
  `make basic-reloc` with exactly 2 dead spans. **I designed a knife I could
  not run.** It does establish that those routines have exactly one
  reachability path — a statement about the call graph, not the behaviour.
* **K-DC3b** (`gbf_max16` `ret c` → `ret nc`, max becomes min) — **EXACT** on
  all three values, and it makes a point the deletion could not: the on-screen
  control `bf_ctl_on` goes **red** here (`60 60 20 20`), because min ≠ max even
  on screen. **A control's greenness is a property of the cut, not a
  constant** — which is why it was predicted in advance rather than read off.

## §7 Filed, not folded in

* **zerobas's full-screen `BF` fill outruns a 20 s emulated step where the
  reference completes.** `LINE(0,0)-(300,250),,BF` returned no reading at all
  on zerobas boot-per-case at step 20; the reference answered. Unquantified —
  no gate measures time.
* **`DRAW` off-screen behaviour is now measured for `M` and the direction
  letters. `A`rc-like commands do not exist in DRAW, but the `X` substring and
  `=var;` routes reach the same `gdrw_move_abs`** and were not separately
  rowed — they are the same site, so this is a coverage note, not a doubt.

## §8 Apparatus

| file | what it does |
|---|---|
| [`drawclamp_wa.py`](../scratchpad/drawclamp_wa.py) | round 1: the work-area readout, 14 rows, two instruments |
| [`drawclamp_char.py`](../scratchpad/drawclamp_char.py) | the 16 whole-plane DRAW rows + the calibration |
| [`drawclamp_wa2.py`](../scratchpad/drawclamp_wa2.py) | round 2: pinning the GXPOS residue, 4 + 3 hypotheses |
| [`drawclamp_bands.py`](../scratchpad/drawclamp_bands.py) | proves each proposed gate band can see the fix |

The plane banks are **versioned** (`drawclamp_char.pre.json` /
`.post.json`) and the probe refuses to overwrite an existing bank without
`--force` — D-SPOKELINE's third residual, fixed in the pattern rather than
just noted.
