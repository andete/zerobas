# D-CIRCDOM — predictions, written BEFORE the characterization run

Baseline: `graphics-acceptance` 290 PASS / 0 FAIL, rc=0, at `15b53bf`.

Denominator (machine-produced, `scratchpad/circdom_scan.py`): 357 python files
walked, 11 with a CIRCLE literal, **346 measured zeroes**; 119 CIRCLE statements;
largest radius drawn **anywhere** = 200 (a scratchpad error-funnel row), largest
a **gate** draws = **20**. No row in the tree compares the PIXELS of a circle
with r > 20. Max aspect literal = 100 (→ ASPS 3); max ASPS in the corpus = 256.

## The claim under test

`sub/graphics.asm:1362` (`gfx_circ_scale` header): *"Bounded-domain: `|v|*ASPS`
assumed `<=65535` (true for `|v|<=255`, ASPS<=256 — the blessed r<=255 domain)"*.
`sub/graphics.asm:1105` repeats it and adds *"A radius far outside that domain may
mis-rasterise the arc mask (never crash)"*.

Traced through the source, the enforcement is at **`sub/circleparse.asm:76-82`**
(`cpt_after_r`): it tests **only `r >= 0`** (`jp m,cpt_err5`). The upper bound is
whatever the resident's DREQ-2 int16 coercion allows → **0..32767**. There is no
`r <= 255` anywhere. So the stated bound should be FALSE for r in 256..32767.

## Phase 1 — is the radius accepted?

All 12 rows: **K on both** (every radius is in 0..32767, every aspect >= 0).

## Phase 2 — the whole 6144-byte pattern plane

Overflow of `gfx_mul16u` starts at `|v|*ASPS >= 65536`, `|v| <= r`.

| row | ASPS | max product | prediction |
|---|---|---|---|
| `r20_base`     | 256 |  5 120 fits | AGREE, non-blank |
| `r200`         | 256 | 51 200 fits | AGREE, **both blank** — vacuous by visibility, kept only as the corpus ceiling |
| `r255`         | 256 | 65 280 fits | AGREE, **both blank** — vacuous, same reason |
| `r256`         | 256 | 65 536 **OVF** | **DIFF** — ref blank; zb ≈33 px in a run at y=96, bbox ≈ (112,96,144,96) |
| `r257`         | 256 | 65 792 **OVF** | **DIFF** — ref blank; zb ≈66 px, at y=95 and y=97 |
| `r300`         | 256 | 76 800 **OVF** | **DIFF** — ref blank; zb hundreds of px, y spanning ≈52..140 |
| `r1000`        | 256 |        **OVF** | **DIFF** — ref blank, zb non-blank |
| `r300_a03`     |  77 | 23 100 fits | **AGREE, NON-BLANK** — key: r=300 is outside the stated r<=255 domain but the product fits |
| `r200_a03`     |  77 | 15 400 fits | AGREE, non-blank — green control proving `r300_a03` is not "both empty" |
| `r300_a09`     | 230 | 69 000 **OVF** | **DIFF** — ref blank, zb non-blank |
| `r700_a0137`   |  35 | 24 500 fits | **AGREE, NON-BLANK** — sharpest: r=700 is 2.7× outside the stated domain, product fits, ellipse visible |
| `r1900_a0137`  |  35 | 66 500 **OVF** | **DIFF** — ref blank, zb non-blank; only the radius moved from `r700_a0137` |

**Totals predicted: 6 DIFF / 6 AGREE.**

## The five `$8000` sites — predictions, traced through the source

| # | site | input range, and WHY | `$8000`? |
|---|---|---|---|
| 1 | `gfx_neg16_bc`/`gfx_neg16_de` (`:1551`/`:1559`) | called only from `gco_emit8` (`:1297-1322`) with `GFX_QX`/`GFX_QY`; `gfx_circ_init` seeds `QY=r`, `QY` only decrements, `QX` climbs while `QX<=QY` → `[−1, r]`, `r ∈ 0..32767` | **no** — by the int16 radius coercion, NOT by 255 |
| 2 | `gfx_circ_scale` `gfx_abs16` (`:1368`) | `GFX_PX`/`GFX_PY` = ±QX/±QY → `[−32767, 32767]` | **no** — same bound |
| 3 | `gfx_circ_scale` re-negate (`:1381`) | input is after `ld l,h / ld h,0` → **0..255 by construction** | **no** — independent of any domain |
| 4 | `gfx_circ_bvec_nudge` (`:1099`) | input is `gfx_circ_bvec_mag`'s output, same `ld l,h / ld h,0` → 0..255, or the literal 1 | **no** — by construction |
| 5 | `gcbv_y` (`:1166`) | nudge output (−255..255), optionally through `gfx_circ_scale` (±0..255) | **no** — by construction |

So the four verdicts should **hold**, and **none of them for the stated reason**:
three are safe by byte-truncation regardless of the domain, two by the int16
coercion at the radius eval. Predicted cost: citations, **zero bytes** for the
`$8000` question — but the re-derivation should show the *overflow* half of the
same comment is false and reachable.
