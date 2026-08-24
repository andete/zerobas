# D-PAINT4 — PAINT's 4th-argument error is the statement boundary; fill THEN raise

**Date:** 2026-08-24. **Fix:** delete PAINT's trailing-token check in
[`basic/graphics.asm`](../basic/graphics.asm) (site after border B) and let
`exec_stmt`'s boundary guard reject the leftover. **Cost: −8 B — a MAIN page-1
CARVE** (page-1 free 91 → 99 B). References: Philips VG-8020, National CF-3300.
The second verb from the generic error-layer seam (after D-SWAP3); the filed
CIRCLE trailing-comma residual is the cross-ABI hard case and is NOT this slice.

## 1. The filed divergence

`TODO.md` (D-DUPSPAN §6.1): `SCREEN 2:PAINT(10,10),9,15,` — a trailing comma on a
complete argument list — FILLS on both references (a pixel reads the paint
colour) and THEN raises `Syntax error`; zerobas raised ERR 2 **before** the fill.
Same class as D-SWAP3: a bespoke trailing-token check (`ep_syntax`) raising above
`ep_draw`, where the generic `exec_stmt` boundary would reject the leftover after
the draw. The residual called the fix *"not obviously cheap … ep_parse_b's
grammar test would have to move below the tenant call"* — an unrun assumption:
the check already sat above `ep_draw`, and `ep_draw` already guards the cursor
(`push hl` / tenant call / `pop hl`) and ends in `jp exec_stmt`. So the check is
DELETED, not moved.

## 2. The mechanism

`PAINT (x,y) [,[C][,[B]]]`. After border B is evaluated, range-checked against
the mode's domain (`gfx_chk_dom` — D-PAINTBORD) and stored, the code raised its
own ERR 2 for a trailing `,`. Deleting that `call skip_spaces / cp ',' /
jp z,ep_syntax` lets a complete `PAINT(x,y),C,B` fall into `ep_draw`, FILL, and
`jp exec_stmt`; the cursor (guarded across the tenant) lands on the leftover
token, which `es_noentry` rejects as a trappable ERR 2 — after the fill.

The domain check stays ABOVE the fill, so an out-of-domain border still gives
ERR 5 before the ERR 2 (D-PAINTBORD `od2.b256c`, unchanged — the graphics gate
covers it). The `:748` site keeps `ep_syntax`: a doubled comma (`PAINT(x,y),C,,`)
raises before B is complete — ERR 2, no fill, and it AGREES on both references
(pa.ccomma). So only the after-complete-args site moves.

## 3. The measurement — 3 DIFF → 0, references unanimous on 8 rows

`scratchpad/paint4_probe.py`. ⚠️ **Timing is part of the measurement**: a PAINT
flood is slow in emulated time, so the fill is BOUNDED to a 10×10 box
(`LINE(10,10)-(20,20),15,B`) and the seed (15,15) is read back; the proven
`step=90` gives the reference fill enough emulated budget (a first pass at
`step=7` starved it and every fill read `<NO OUTPUT>` — the apparatus, not the
subject). Readout `[ERR P]`, P = `POINT(15,15)`.

| row | statement (in the box) | refs | zb before | zb after |
|---|---|---|---|---|
| pa.color | `PAINT(15,15),9,15` | `0 9` | `0 9` | `0 9` |
| pa.plain | `PAINT(15,15)` | `0 15` | `0 15` | `0 15` |
| pa.nopnt | (box only, no PAINT) | `0 4` | `0 4` | `0 4` |
| **pa.4comma** | `PAINT(15,15),9,15,` | `2 9` | **`2 4`** | `2 9` |
| **pa.4arg** | `PAINT(15,15),9,15,7` | `2 9` | **`2 4`** | `2 9` |
| **pa.4colon** | `PAINT(15,15),9,15,:X=1` | `2 9` | **`2 4`** | `2 9` |
| pa.3comma | `PAINT(15,15),9,` | `24 4` | `24 4` | `24 4` |
| pa.ccomma | `PAINT(15,15),9,,` | `2 4` | `2 4` | `2 4` |

The three subject rows go `2 4` → `2 9`: ERR 2 is unchanged (the code was always
right), but now the pixel is PAINTED (P=9) before the raise, matching the
references. `pa.nopnt` (`0 4`, same box, no PAINT) vs `pa.color` (`0 9`) pins that
`9` is a genuine fill and `4` is unpainted. `pa.3comma`/`pa.ccomma` confirm
incomplete-arg cases still raise before any fill — the fix touched exactly the
after-complete-args site.

## 4. Knives — `scratchpad/paint4_knives.py`

* **K-PA1** re-adds the deleted check (revert): the three subject rows go
  `2 9` → `2 4` (raise before fill) — they detect the fill-then-raise ordering.
* **K-PA2** points `ep_draw`'s `GFX_OP` at POINT (a read, no VRAM write): every
  value row that reads a painted pixel drops to the background `4` — the `9`/`15`
  readings are genuine fills, not stale VRAM. (The ERR column becomes `7`, not
  `0`/`2`: the POINT op leaves `GFX_POVF` set so `ep_draw`'s overflow check fires
  — incidental; the load-bearing column is the pixel, and it is `4` on all five.)

## 5. Scope

* Only the site after a COMPLETE `,C,B`. The `:748` doubled-comma and the ERR-24
  dangling-border cases raise before the fill and already agree — left alone.
* The out-of-domain-border ordering (ERR 5 before the boundary ERR 2) is
  preserved by `gfx_chk_dom` staying above `ep_draw`.
* CIRCLE's trailing-comma residual is the cross-ABI case (parse in a sub-ROM
  tenant reporting through `GFX_RES`, the resident tests it before the draw op) —
  a restructure, not a delete, and NOT attempted here.
