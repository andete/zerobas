# D-PAINTVRAM knives — predicted sets, written BEFORE any of them ran

Rows in play: PHASE H-V (`flood_wholebyte.0/.1`, `flood_c_ne_b`,
`box_span_cells.0/.1/.2/.3`), PHASE H's `paint_then_pset`, and
`vram_fidelity.py`'s whole-plane cases `linebf` / `paint` / `flood`.

`gfx_span_bytes` is now shared by `LINE ,BF` **and** `PAINT`, so a cut there must
redden BOTH — that is itself a claim worth scoring.

| knife | cut | predicted RED | predicted GREEN (controls) |
|---|---|---|---|
| **K-PV1** | `gfx_span_bytes`: `ld c,0` → `ld c,$FF` (pattern not cleared) | H-V `flood_wholebyte.0/.1`, `flood_c_ne_b`, `box_span_cells.0`; `paint_then_pset`; fidelity `linebf` **and** `paint`/`flood` | H-V `box_span_cells.1/.2/.3` |
| **K-PV2** | `gfx_paint_row` left partial: `sub (hl)` → `sub d` (count 0 → no left partial) | H-V `box_span_cells.1`; fidelity `paint` | H-V `.0/.2/.3`, both floods, `paint_then_pset`, fidelity `linebf`+`flood` |
| **K-PV3** | `gfx_paint_row` right partial: `ld a,(GFX_PXR)` → `ld a,(GFX_PXL)` | H-V `box_span_cells.2`; fidelity `paint` | H-V `.0/.1/.3`, both floods, `paint_then_pset`, fidelity `linebf`+`flood` |
| **K-PV4** | `gfx_span_bytes`: colour from `GFX_B` instead of `GFX_C` | H-V `flood_c_ne_b`; fidelity `linebf` | H-V `flood_wholebyte.*`, all `box_span_cells`, `paint_then_pset`, fidelity `paint`/`flood` |

**Why K-PV2 and K-PV3 spare the floods:** an unbounded fill runs every span the
full 0..255, which is 32 cell-aligned whole cells with no partial at either end
— so a knife that removes a partial cannot touch it. That is also the fact that
made `box_span_cells` necessary at all.

**Why K-PV4 is the sharp one:** it is the knife that `flood_c_ne_b` was added
for. Every other row in the phase has `B == C` and would score a fill that wrote
the BORDER colour as correct. If `flood_c_ne_b` fails to redden here, the row
does not do the job it was added to do.

⚠️ K-PV4's fidelity `linebf` prediction is the least certain: it assumes
`GFX_B` is NOT marshalled for a `LINE` and therefore holds something other than
15 on a fresh boot. If `linebf` stays green, that is what it means — and the
prediction is scored as a miss either way.
