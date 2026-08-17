# D-CIRCOVF — predictions, written before the runs

Kept because a prediction that is only written down after the measurement is a
description. Scored in `docs/circovf-msx1-oracle.md`, misses included.

## Round 1 — the positive oracle (`circovf_char.py`)

Whole-plane (popcount, bbox, sha1) per row, per hypothesis, printed by the probe
itself before it booted anything. Four hypotheses: `H_EXACT`, `H_SAT`,
`H_WRAP`, `H_BLANK`. **Predicted: the reference implements one of them and the
same one on all three code paths.** No prediction was made about *which* — that
was the open question the residual raised.

Also predicted, and this one was a forecast: **zerobas reads `H_WRAP` on all
eight rows.** Result: 8/8 exact.

## Round 2 — the fix (`circovf_asmsim.py`, before any build)

* `gfx_mul16r` reproduces `(v*ASPS+128)>>8` exactly for all `v` in 0..32767,
  `ASPS` in 0..255 — **predicted exact, measured exact** (200 054 cases).
* **`$8000` is NOT reachable** once `ASPS=256` is an identity arm: the multiply
  arm tops out at 32639 and the identity arm at 32767. This CONTRADICTS the
  filed residual, which says the `$8000` arm becomes necessary in this slice.
  Predicted before the sweep; measured 32639/32767.
* `gfx_mul16u32` — **the first draft was PREDICTED CORRECT AND WAS NOT.** It
  used a shift direction that never brings the product into the low word:
  200 037 of 200 049 cases wrong. Caught before a build existed.

## Round 3 — the walls

Predicted: `sub.rom` moves, the other three ROMs byte-identical. Predicted cost
"≈ +56 B". Measured: **+65 B**, and it lands in **sub page 0**, not the sub page
1 the residual priced it against.

## Round 4 — the knives (`circovf_knives.py`)

Every set below is DERIVED from the probe's own `CIRCLE_CASES` at run time, from
each row's `ops` string — never hand-typed. D-CIRCDOM's K-CD2 was scored a miss
for exactly that, with zero modelling content in the error.

| knife | kind | cut | predicted to redden |
|---|---|---|---|
| K-CO1 | predict | `ld h,c` → `ld h,b` in `gfx_mul16r` (B=0 after `djnz`) — narrows the result to a byte, the old defect | rows with `ASPS != 256` whose largest scaled offset > 255 → **2**: `ell_ovf_a05r528`, `ell_ovf_a2r528` |
| K-CO2 | predict | `or a` → `xor a` at the `ASPS=256` test — kills the identity arm | every row with `ASPS == 256` and `r > 0` → **19** |
| K-CO3 | **nothing** | `ld b,4` → `ld b,2` in `gfx_cmp32` — undoes the 32-bit widening | **nothing, and that is the finding** — no green row can see this compare |
| K-CO4 | predict | `gfx_circ_bvec_mag` tail → `gfx_mul16u32` — boundary vectors ~256× too long | arc rows that draw and are not a full sweep → **5** |
| K-CO5 | predict | band clamp `min(23,…)` → `min(5,…)` | **nothing** — the probe's own guard must abort with no footer |

Two of these are honest coin-flips and are expected to be scored, not defended:

* **K-CO2 may over-predict.** `clash_circle` reads the colour plane, not the
  pattern plane; if the colour plane is unchanged by a collapsed scale it stays
  green and the knife is a MISS by one row.
* **K-CO4 may under- or over-predict.** The arc mask tests the SIGN of a cross
  product, and sign is invariant under a positive rescale — so a 256×-longer
  boundary vector moves a row only where the rounding difference flips an edge
  point. The prediction is "all five", and "none" is entirely possible.
