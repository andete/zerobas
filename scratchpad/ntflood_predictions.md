# D-NTFLOOD — predictions, written BEFORE the R-FLOOD arm is built

STEP 1 (landed, verified): `gfx_paint_inside` refactored to `call
gfx_paint_passable` + the "already C" stop. 26 B -> 11 B, sub page 0 free
1348 -> 1363 B. `graphics-acceptance: PASS` and `ntwall_sep.py` reads the
documented pre-fix values exactly (`sep.b7` zb [9,4,4,4,4,4], `sep.b15` zb
[9,9,9,9,4,4]) — behaviour-identical, which is the point of doing it first.

STEP 2 (this arm): the DRAWN==B border test in `gfx_paint_passable` fires only
when `C == B`. R-FLOOD, measured by D-NTSEP: with `C != B` the reference walk
does not bound at all, in both wall arrangements, including a wall whose colour
is neither B nor C.

| row | now (zb) | predicted after |
|---|---|---|
| `sep.b7`    | `[9,4,4,4,4,4]`   | `[9,9,9,9,9,9]` — matches both refs |
| `sep.b15`   | `[9,9,9,9,4,4]`   | `[9,9,9,9,9,9]` — matches both refs |
| `sep.cb`    | `[7,4,4,4,4,4]`   | UNCHANGED — the `C == B` control, still bounded |
| `sep.noclr` | `[4,4,4,4,4,4]`   | UNCHANGED — no PAINT at all |

`ntwall_probe.py`: the six pinned DIFF rows (`wall.row solid.row h2 h4 hp3
vp.solid`) move to agreement; the thirteen that agree today must STILL agree.

`graphics-acceptance` PHASE H: the two GREEN PINS against an overshooting fix
(`plain_wall_cb_bounded`, `bf_wall_not_a_border`) must stay green. They are the
reason this is falsifiable rather than "more filling is more faithful".

## What this does NOT claim

⚠️ The WRITE divergence is untouched and stays open: the references write
`pattern := 0, bg := C` for a filled group and this engine writes
`pattern := $FF, fg := C`. Both `POINT`-read as C, so no row here can see it —
`VPEEK` can. The entry says matching the reference means changing
`gfx_plot_cur`'s contract, shared with PSET/LINE/CIRCLE/DRAW; **that is the
WRITE half, and the walk half measured here is separable from it.** If the rows
move as predicted, that separation is the finding.

⚠️ TERMINATION IS THE RISK. With `C != B` nothing but "already C" ends the walk,
which is what the sub's own header says the reference must also rely on — but a
whole-screen fill is slower than any row here has done before, so a gate TIMEOUT
is a possible outcome and would be a real result, not a flake.
