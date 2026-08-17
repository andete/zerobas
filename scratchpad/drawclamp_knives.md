# D-DRAWCLAMP knife predictions — WRITTEN BEFORE ANY KNIFE RAN

Three edits shipped, so three knives, one per edit. Each prediction names the
rows that must go RED, the rows that must stay GREEN, and the exact values the
red rows must read — a knife that only predicts "something breaks" cannot miss.

## K-DC1 — delete `call gfx_clamp_coords` from `gdrw_move_abs`

The DRAW-clamp edit itself.

* RED, reading the OLD `clip` planes BYTE FOR BYTE (the `pre` bank's `zb` side):
  all 12 discriminating rows of `drawclamp_char.py` —
  `dm_off_r 2dc150af`, `dm_off_negy 7da0836c`, `dm_off_b fe197343`,
  `dm_alloff 350ff131` (1 px: the marker alone), `dm_start_off_R d8879d37`,
  `dm_start_off_L 44862aaa`, `dm_both_off 84eea989`, `dm_rel_off 35a200f5`,
  `dm_scaled_off 178bc7cd`, `dm_rot_off 9329edf6`, `dm_dir_diag 85830f38`,
  `dm_two_seg a412c843`.
* GREEN and UNMOVED: `dead_nodraw`, `ctl_draw_on`, `gate_clip_left` (the
  vacuous one — it CANNOT move, and if it does the rig is lying).
* ALSO RED, as a knock-on: `draw_m_off` and `draw_left_down` in
  `drawclamp_wa2.py`. With no clamp, GFX_X2/GFX_Y2 hold the raw target again,
  so `gdrw_gxpos` reports 300/250 and 65436/250 — the pre-fix values.
* GREEN: `draw_up_off` (the START wins there and it is on screen either way).

## K-DC2 — revert `gdrw_gxpos` to read `GFX_DTX`/`GFX_DTY`

The residue edit, with the clamp left in place.

* RED: `draw_m_off` → `W 300 250 300 250`; `draw_left_down` →
  `W 65436 250 65436 250`. Both are the raw target, because DTX/DTY are never
  clamped.
* GREEN: `draw_up_off` (start wins, unchanged), `ctl_draw_on`,
  `draw_blank_off`, and EVERY plane row in `drawclamp_char.py` — this edit
  cannot touch a pixel.

That last clause is the point of the knife: it must prove the residue and the
rasterisation are independently sited.

## K-DC3 — delete `call gfx_bf_gxpos` from `gfx_line_op`

* RED: `bf_small_off` → `W 300 250 300 250`; `bf_p2_topleft` →
  `W 65506 65516 65506 65516`. Both revert to the raw p2.
* GREEN: `bf_ctl_on` (`W 60 60 60 60` — on screen, so max/max IS p2),
  `box_off` (`W 300 250 300 250` — the outline arm, never touched by this
  edit and the control that proves the knife cut the fill arm only).

`bf_ctl_on` staying green under the knife is what stops "I deleted the call and
BF broke" from being read as evidence for the max/max rule specifically.

### 🔴 K-DC3 AS WRITTEN IS UNDELIVERABLE — scored as a MISS

The cut does not build. Deleting the only call makes `gfx_bf_gxpos` and
`gbf_max16` unreachable and `check_dead_code.py` fails `make basic-reloc` with
**exactly 2 unreachable spans**, so no ROM is produced and no row is scored.
I designed a knife I could not run.

What it does establish, for free, is that those two routines have **exactly one
reachability path** — the call this slice added. That is a statement about the
call graph, not about the behaviour, and it is not a substitute for the knife.

## K-DC3b — the repaired cut: `gbf_max16` `ret c` → `ret nc`

One byte, all code reachable, so the tree builds. The routine now returns the
per-axis **minimum**, which is the sharpest available negation of "max on each
axis" — it keeps `gfx_bf_gxpos` running and only changes which corner it picks.

* RED: `bf_small_off` → `W 300 250 200 150` (min of x 200/255 and y 150/191);
  `bf_p2_topleft` → `W 65506 65516 0 0`.
* RED, **and this differs from K-DC3's prediction**: `bf_ctl_on` →
  `W 60 60 20 20`. Under the deletion the on-screen control would have stayed
  green; under a min it cannot, because min ≠ max even on screen. Stating it
  in advance is the point — a control's greenness is a property of the cut,
  not a constant.
* GREEN: `box_off` (`W 300 250 300 250`, the outline arm) and every DRAW row.
