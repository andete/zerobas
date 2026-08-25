# D-PAINTVRAM -- predictions written BEFORE the rows ran

Mechanism hypothesis (from the source, not from the divergence): PAINT paints
its spans PIXEL BY PIXEL (`gfx_paint_plot` -> `gfx_rmw_at`), where `LINE ,BF`
already splits each scanline into [left partial][WHOLE BYTES][right partial] and
writes a whole byte BLIND as `pattern := $00, colour := C` (fg forced 0) --
D-BFBYTE, `gbf_row`/`gbf_split`, docs/bffill-msx1-characterization.md. The
references apply that same byte-fill to PAINT's spans; zerobas does not.

If that is right, then:
  * a cell WHOLLY inside a painted span diverges (whole-byte path),
  * a cell only PARTLY covered agrees (both machines run per-pixel there),
  * and the divergence is VISIBLE THROUGH `POINT` after a second draw into a
    painted cell -- refs leave the cell all-background so a later PSET claims
    the free fg nibble for ONE pixel; here the cell is all-foreground so the
    same PSET recolours ALL EIGHT.

## Row-by-row, on TODAY's build (all five are new rows)

| row | ref (predicted) | zb (predicted) | verdict today |
|---|---|---|---|
| `flood_wholebyte`   (128,96) after `PAINT(128,96),15` | pat `00` col `0f` | pat `ff` col `f4` | 🔴 FAIL |
| `box_whole`         (24,30) inside the box fill        | pat `00` col `09` | pat `ff` col `94` | 🔴 FAIL |
| `box_left_partial`  (16,30), span starts x=21          | pat `0f` col `94` | pat `0f` col `94` | ✅ PASS (control) |
| `box_right_partial` (56,30), span ends x=59            | pat `f8` col `94` | pat `f8` col `94` | ✅ PASS (control) |
| `paint_then_pset` POINT row                            | `R 6 15 15`       | `R 6 6 6`         | 🔴 FAIL |

Two controls on the SAME program as `box_whole`: if the partial cells went red
too, the diagnosis "PAINT lacks the whole-byte split" would be wrong -- it would
mean the per-pixel path itself differs, which the 6 green primitives already
refute.

## Second prediction, about the SPEED

`gbf_row`'s own header prices the byte path at "two blind writes per byte
instead of eight read-modify-writes, each of which costs two VDP reads and two
VDP writes -- and it is the whole 23x". If PAINT adopts it, the flood's
46.25 emulated s should fall FAR below the references' ~14.7-15.5 s, not merely
to it: zerobas would then do the byte fill AND the per-pixel extend_lr walk,
while the references do whatever they do. Predicted: flood lands under 15 s.
I do NOT predict it matches; I predict the 2.98x is gone.
