# D-SPRITE5 — PUT SPRITE's 5th-argument error is the statement boundary; place THEN raise

**Date:** 2026-08-24. **Fix:** delete PUT SPRITE's trailing-token check in
[`basic/graphics.asm`](../basic/graphics.asm) (site after the pattern number) and
let `exec_stmt`'s boundary reject the leftover. **Cost: −8 B — a MAIN page-1
CARVE** (page-1 free 99 → 107 B). References: Philips VG-8020, National CF-3300.
The **third** verb from the generic error-layer seam (after D-SWAP3, D-PAINT4),
picked out by the one-pass classifier (`scratchpad/seam_classify.py`).

## 1. The divergence

`PUT SPRITE p,(x,y),c,n,<trailing>` — a trailing token on a complete argument
list — PLACES the sprite on both references and THEN raises `Syntax error`;
zerobas raised ERR 2 **before** the placement via a bespoke `gfx_syntax` check
(`:1250`) above `pspr_go`. Same class as SWAP and PAINT.

## 2. The mechanism

After the pattern number is parsed and its flag set, the code raised its own ERR 2
for a trailing `,`. Deleting that `call skip_spaces / cp ',' / jp z,gfx_syntax`
lets a complete `PUT SPRITE p,(x,y),c,n` fall into `pspr_go`, which places the
sprite (`GFX_OP = 9`, the attribute merge, via `spr_tenant`) with the cursor
guarded (`push hl` / tenant / `pop hl`) and `jp exec_stmt`s. The leftover token
lands on `es_noentry` → trappable ERR 2, after the placement. `pspr_go` has no
post-tenant check at all (unlike PAINT's `ep_overflow`), so the delegation is
even cleaner.

The incomplete-arg sites keep their `gfx_syntax`: `PUT SPRITE 0` (`:1198`) and
`PUT SPRITE 0,` (`:1210`) raise before the placement (sp.barep / sp.incomp
`2 209`) and agree on both references — the per-site oracle split, same shape as
PAINT's `:748`.

## 3. The measurement — 3 DIFF → 0, references unanimous on 8 rows

`scratchpad/sprite5_probe.py`. Readout `[ERR P]`, P = `VPEEK(&H1B00)` = sprite-0
Y attribute (SCREEN 2 attribute table): **30** when placed at y=30, **209** when
the plane is untouched (the hidden-sprite Y). `SPRITE$(0)=STRING$(8,255)` defines
the pattern first. No slow flood here, so `step=6`.

| row | statement | refs | zb before | zb after |
|---|---|---|---|---|
| sp.ok | `PUTSPRITE0,(20,30),1,0` | `0 30` | `0 30` | `0 30` |
| sp.noc | `PUTSPRITE0,(20,30)` | `0 30` | `0 30` | `0 30` |
| sp.none | (place plane 1, read plane 0) | `0 209` | `0 209` | `0 209` |
| **sp.5comma** | `PUTSPRITE0,(20,30),1,0,` | `2 30` | **`2 209`** | `2 30` |
| **sp.5arg** | `PUTSPRITE0,(20,30),1,0,9` | `2 30` | **`2 209`** | `2 30` |
| **sp.5colon** | `PUTSPRITE0,(20,30),1,0,:X=1` | `2 30` | **`2 209`** | `2 30` |
| sp.incomp | `PUTSPRITE0,` | `2 209` | `2 209` | `2 209` |
| sp.barep | `PUTSPRITE0` | `2 209` | `2 209` | `2 209` |

The three subject rows go `2 209` → `2 30`: ERR 2 unchanged, but the sprite is now
PLACED (attribute = 30) before the raise, matching the references. `sp.none`
(place a different plane, read plane 0) pins `209` as "not placed".

## 4. Knives — `scratchpad/sprite5_knives.py`

* **K-SP1** re-adds the deleted check (revert): the three subject rows go
  `2 30` → `2 209` — they detect the place-then-raise ordering.
* **K-SP2** points `pspr_go`'s `GFX_OP` at POINT (a read, no attribute write): every
  value row that reads a placed sprite drops to `209` (unplaced) — the `30`
  readings are genuine placements.

## 5. Seam status after three verbs

SWAP, PAINT, SPRITE are the three DELETABLE members shipped (−23/−8/−8 B). The
one-pass classifier (`seam_classify.py`) put **CIRCLE** in RESTRUCTURE (tenant
parse, result tested before the draw op) and **PLAY**'s 4th voice in KEEP (raises
before any voice plays — the reference ordering is already correct). It also found
zerobas lacks the **`PLAY(n)` function** (queue status) — filed separately.
