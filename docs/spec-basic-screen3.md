# SPEC — D-SCREEN3: MULTICOLOUR lands, minus PAINT

Status: **✅ LANDED 2026-08-22** (PAINT deliberately excluded, §5).
Scout: [`screen3-scout-2026-08-22.md`](screen3-scout-2026-08-22.md) — read it first;
every measurement this spec builds on is there.
Baseline `4aaa085`: low **46 B** / main page 1 **8 B** / sub page 0 **3299 B**.

---

## 1. What shipped

| statement | SCREEN 3 before | after |
|---|---|---|
| `PSET` / `PRESET` | ERR 5 | ✅ |
| `POINT` | 🔴 **silent wrong colour** | ✅ |
| `LINE` | ERR 5 | ✅ |
| `LINE ,B` / `,BF` | ERR 5 | ✅ |
| `CIRCLE` | ERR 5 | ✅ |
| `DRAW` | ERR 5 | ✅ |
| `PAINT` | ERR 5 | **ERR 5 — still, on purpose (§5)** |
| `SPRITE$=` / `PUT SPRITE` | already worked | unchanged |

## 2. 💰 Price — measured

| wall | before | after | spent |
|---|---|---|---|
| main page 1 | 8 B | **4 B** | **4** |
| main page-0 low | 46 B | 46 B | 0 |
| sub page 0 | 3299 B | **3156 B** | **143** |
| sub page 1 | 1624 B | 1624 B | 0 |

The scout estimated ~6 B main / ~170–280 B sub. Both came in **under**, and for the
reason the scout gave: multicolour has no colour table, so the MC arm replaces
*both* `gfx_calc_addr` and the clash RMW — one VRAM read and one write where the
SCREEN-2 path needs two of each.

🎯 **DRAW'S GATE PAID FOR PAINT'S.** DRAW carried 6 B of inline
`ld a,(SCRMOD) / cp 2 / jp nz,gfx_err5` — the shared gate's test, spelled out
again. Replacing it with a 3 B `call gfx_mode_gate` keeps D-DRAWERR's measured
ordering (the gate still runs *before* the argument) and freed the bytes for
PAINT's narrow entry. Main cost fell from 7 B to 4 B without touching anything
else.

## 3. The address model

`gfx_calc_addr_mc` (sub/graphics.asm), from the scout §6:

```
cx = x>>2   cy = y>>2                     the 4x4 HARDWARE cell
addr = (cy>>3)*256 + (cx>>1)*8 + (cy&7)   generator base $0000
high nibble when cx is EVEN, low when ODD
```

and `(cx>>1)*8` **is** `x & $F8` — the identical expression `gfx_calc_addr`
already uses, because a SCREEN-2 byte spans 8 pixels across and an MC byte spans
8 pixels across as two 4-wide cells. Only the row term and the mask differ.

## 4. Five dispatch points, one branch each

| site | covers |
|---|---|
| `gfx_plot` | PSET / PRESET |
| `gfx_point` | POINT — **and this is the silent-wrong-answer fix** |
| `gfx_rmw_at` | LINE, CIRCLE, DRAW (every one reaches VRAM here) |
| `gbf_row` | `LINE ,B/BF` → falls back to the per-pixel path (`gbf_rw_all`), which already existed for runs with no whole byte in them |
| — | `gfx_is_mc` is the single mode test, because a test spelled out five times is five chances to spell it differently |

🔴 **`POINT` HAD NO MODE GATE.** The plotting ops go through `gfx_point_gate`;
`gfx_point` does not. So in SCREEN 3 it read the G2 address model against MC VRAM
and returned a plausible wrong colour with **no error** — `1` where both
references say `4`. The same branch that implements the feature closes that
defect; it was found by the scout (§5 there) and is not a separate fix.

## 5. 🔴 PAINT is EXCLUDED, and the reason is ALGORITHMIC, not addressing

`gfx_rmw_at_mc` would write PAINT's cells perfectly well — PAINT's *write* side
already routes through it. The fill is what breaks:

> **Adjacent LOGICAL pixels share one 4×4 cell.** With the default border `B = C`
> (`ex_paint`'s `ep_default_b`), the first cell painted to `C` instantly reads as a
> **border** to its own neighbours, and the span walk stops dead.

This engine avoids that in SCREEN 2 through the **drawn/undrawn** distinction —
`gfx_paint_read` reports "the pattern bit is clear", and an undrawn pixel can
never be a border. **Multicolour has no pattern bit**, so that escape does not
exist.

**Measured, both references, before and after:**

| case | vg8020 | cf3300 | zerobas (MC arm tried) | zerobas (shipped) |
|---|---|---|---|---|
| `PAINT(10,10),9` → `POINT(10,10)` | 9 | 9 | 9 | ERR 5 |
| `PAINT(10,10),9` → `POINT(10,0)` | 9 | 9 | **4 — seed only** | ERR 5 |
| `PAINT(10,10),9` → `POINT(10,60)` | 9 | 9 | **4** | ERR 5 |
| `PAINT(10,10),9,7` → `POINT(10,60)` | 4 | 4 | 4 | ERR 5 |
| `PAINT(10,10),9,4` → `POINT(10,0)` | 4 | 4 | 4 | ERR 5 |

⚠️ **The two rows that "agreed" agreed for the WRONG REASON** — both sides simply
did nothing. Only the flood rows discriminate, and they say the MC arm painted its
seed and stopped.

**A loud ERR 5 beats a silent one-cell paint**, so PAINT keeps the narrow gate.
The fix is a flood engine that does not re-test painted cells (or that steps by
cell in MC) — its own slice, with its own measurement of what the reference's
span walk actually does. Filed in `TODO.md`.

⚠️ **No MC arm was left in `gfx_paint_read`.** It would be unreachable, and
`make deadcode` would say so — which is how the decision stays honest rather than
becoming a stub someone later mistakes for support.

## 6. What is NOT claimed

* `PAINT` — §5.
* The **contents** of the `$0800` name table are still unmeasured; `CHGMOD` writes
  them and all three machines were shown to agree (scout §6), which is why writing
  only the generator is sufficient — but nothing here pins what they must be.
* `CIRCLE`'s aspect ratio in a 4×4-cell surface is not separately measured; the
  row that passes drives a plain circle.
