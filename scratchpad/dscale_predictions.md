# D-DSCALE — predictions, written BEFORE the first run (2026-08-11)

Baseline at HEAD `7693787`: `basic-reloc b37e5055 / sub c7d61d6d / disk 2c630d3d
/ zerobas-main-eu a122f666`. Gate `make lineerr-acceptance`, 189 rows, 185/185
+ 4 deferred.

Instrument: `[ ERR , GRPACX , GRPACY ]` over a `SCREEN 2 : PSET(7,4)` seed, so
the origin is (7,4) and every row below is arithmetic on that, mod 65536.

## The arithmetic each prediction is traced through (NOT analogy — D-DRAWERR §11.8)

Read off `sub/graphics.asm`:

* `gdo_dir` → `gdrw_arg_opt` (count, absent = 1) → `gdrw_scale` → `gdrw_axis`
  once per axis with the letter's unit sign → `gdrw_rotate` → `gdrw_move_rel`.
* `gdrw_scale`: `HL = 0; B = S; repeat B: HL += n` (so `n*S mod 65536`), then
  `>>2` on the magnitude with the sign restored — truncation toward zero.
* `gdrw_axis` for a `-1` sign NEGATES, so `U n` gives `DDY = -distance` and the
  cursor lands at `4 - distance` mod 65536.
* `gdrw_rotate` one step is `(dx,dy) -> (dy,-dx)`.

So for `BU n`:  `GRPACY = (4 - distance) mod 65536`,
where `distance = n` if the scale state is "never set" (the claimed reference
behaviour) and `distance = signed16(4n mod 65536) >> 2` at an explicit `S4`.

## New rows — the values predicted on each side, BEFORE the run

| row | statement | both refs | zb (BEFORE any fix) | verdict predicted |
|---|---|---|---|---|
| `d.def10` | `DRAW"BU10"` | ` 0 , 7 , 65530 ` | ` 0 , 7 , 65530 ` | agree |
| `d.def8k` | `DRAW"BU8192"` | ` 0 , 7 , 57348 ` | ` 0 , 7 , 8196 ` | **DIFF** |
| `d.s4.8k` | `DRAW"S4BU8192"` | ` 0 , 7 , 8196 ` | ` 0 , 7 , 8196 ` | agree |
| `d.defd40k` | `DRAW"BD40000"` | ` 0 , 7 , 40004 ` | ` 0 , 7 , 7236 ` | **DIFF** |
| `d.defr40k` | `DRAW"BR40000"` | ` 0 , 40007 , 4 ` | ` 0 , 7239 , 4 ` | **DIFF** |
| `d.a0.10` | `DRAW"A0BU10"` | ` 0 , 7 , 65530 ` | ` 0 , 7 , 65530 ` | agree |
| `d.a1.10` | `DRAW"A1BU10"` | ` 0 , 65533 , 4 ` | ` 0 , 65533 , 4 ` | agree |
| `d.a0.32k` | `DRAW"A0BU32767"` | ` 0 , 7 , 32773 ` | ` 0 , 7 , 5 ` | **DIFF** |
| `d.c1.32k` | `DRAW"C1BU32767"` | ` 0 , 7 , 32773 ` | ` 0 , 7 , 5 ` | **DIFF** |
| `d.prev32k` | `DRAW"S4":DRAW"BU32767"` | ` 0 , 7 , 5 ` | ` 0 , 7 , 5 ` | agree |
| `d.post32k` | `DRAW"BU32767S4"` | ` 0 , 7 , 32773 ` | ` 0 , 7 , 5 ` | **DIFF** |

`d.def8k` is the SMALLEST count that separates the two states: `8192*4 = 32768`
is the first product to reach bit 15. Every count below it is identity under
both states, which is the whole reason five correct measurements supported a
wrong rule.

## The design question these rows decide, stated as a fork

`d.a0.32k` and `d.c1.32k` are the rows that say WHERE the sentinel goes, and
they are the reason this is not a one-line edit:

* If both read ` 0 , 7 , 32773 ` (the same as `d.def32k`), then the boot state
  is a property of the SCALE CELL alone. The sentinel is `GFX_DSCALE = 0`
  (unreachable through `gdo_s`, which maps `S0` to 4 — measured, must stay) and
  `GFX_DANGLE` needs nothing: an explicit `A0` and never-set are the same state
  because rotate-by-zero is the identity in any implementation.
* If either reads ` 0 , 7 , 5 `, the boot state is a SHARED "no transform yet"
  flag that ANY `DRAW` command arms, and the sentinel must be a separate flag
  written by `gdo_s` **and** `gdo_a` (**and** `gdo_c`, if `d.c1.32k` is the one
  that moves). Then the cheap edit is wrong and the price changes.

⚠️ The angle has no wrap of its own — its domain is a CHECKED 0..3 and
rotate-by-0 is the identity — so `d.a0.32k` is the only way to ask the
`GFX_DANGLE` question at all: it borrows the scale's wrap as the readout.
Predicted: the cells are independent and `d.a0.32k` reads 32773.

`d.post32k` says the state is consulted AT THE COMMAND, not at statement entry;
`d.prev32k` says arming persists across statements (§4's persistence claim,
never before asked at the wrap, where it is observable).

## Predicted price

`ld a,4` deleted from the cold-boot hook (A is already 0 there) = **−2 B** main;
`jr z,gdrw_sc_div` → `ret z` in `gdrw_scale` = **−1 B** sub. Net **−3 B**, on
both sides of the slot boundary.

---

# ROUND 1 — SCORED. 10 of 11 exact, and the ONE miss is a second defect

Run on the HEAD build, hashes reproduced (`b37e5055 / c7d61d6d / 2c630d3d /
a122f666`), positive controls all green.

| row | refs | zb | predicted | |
|---|---|---|---|---|
| `d.def10` | 65530 | 65530 | exact | ✓ |
| `d.def8k` | 57348 | 8196 | exact | ✓ |
| `d.s4.8k` | **57348** | 8196 | predicted ` 0 , 7 , 8196 ` on ALL THREE | 🔴 **MISS** |
| `d.defd40k` | 40004 | 7236 | exact | ✓ |
| `d.defr40k` | 40007,4 | 7239,4 | exact | ✓ |
| `d.a0.10` | 65530 | 65530 | exact | ✓ |
| `d.a1.10` | 65533,4 | 65533,4 | exact | ✓ |
| `d.a0.32k` | 32773 | 5 | exact | ✓ |
| `d.c1.32k` | 32773 | 5 | exact | ✓ |
| `d.prev32k` | 5 | 5 | exact | ✓ |
| `d.post32k` | 32773 | 5 | exact | ✓ |

## The fork is RESOLVED, in the predicted direction

`d.a0.32k` and `d.c1.32k` both read the FULL count on the references, and
`d.post32k` says a trailing `S4` does not reach back over the `U`. So the boot
state is a property of the **scale cell alone**: an `A` command does not arm it,
a `C` command does not arm it, and only an `S` *already executed* does.
**`GFX_DANGLE` needs no sentinel** — an explicit `A0` and never-set are the same
state, and now that is measured rather than assumed. The cheap design stands.

## 🔴 The miss, and what it found

`d.s4.8k` was written as the GREEN CONTROL for `d.def8k`: "the divergence is
about the STATE, not about large counts". It is not green. Decomposing the three
explicit-`S4` readings into their 16-bit products:

| n | product | reference distance | signed16 ÷ 4 | logical ` >>2 ` |
|---|---|---|---|---|
| 8192 | `$8000` | **+8192** | −8192 | +8192 |
| 32767 | `$FFFC` | −1 | −1 | +16383 |
| 40000 | `$7100` | +7232 | +7232 | +7232 |

`$FFFC` is read as −4, so the product IS signed. `$8000` is read as **+32768**,
so the sign boundary is at `$8001`, not at `$8000` — and `$8000` is the ONE
16-bit value that is its own two's-complement negation, which is why nothing has
ever seen it. `gdrw_scale`'s `bit 7,h / jr nz,gdrw_sc_neg` puts it on the wrong
side, so zerobas answers −8192 where both references answer +8192.

⚠️ This is a defect in the EXPLICIT-`S` arithmetic. It has nothing to do with
the boot default and it is not what the residual filed.

🔴 **And it is why `d.def8k`'s stated justification was wrong even though its
three values were right.** 8192 is NOT the smallest count that separates the two
states: at `S4` the product is `$8000` and the reference passes the full 8192
through, so the two states COINCIDE there. The smallest discriminator is
**8193** (product `$8004`, the first one genuinely past the boundary). The row
designed as the sharpest instrument landed on the single count where the
instrument reads nothing — and only because a second defect lives there.

**The lesson one layer below D-DRAWERR §11.8:** the zb column was traced through
`sub/graphics.asm` and was exact; the reference column was extrapolated from
`g6_draw_notes.md` §3's fitted model and was wrong. **A MODEL has a blast radius
too** — twelve points fitted and falsified it, and `$8000` was outside all
twelve.

---

# ROUND 2 — predictions, written BEFORE the run

One data point is not a rule, so the `$8000` boundary is pinned from BOTH sides
and at FOUR different `(n, S)` pairs that reach the same product. Claimed rule:

> **`distance = f(n × S mod 65536) ÷ 4`, where the product is negative iff it is
> ≥ `$8001`.** `$8000` is `+32768`.

| row | statement | product | both refs | zb (BEFORE) | verdict |
|---|---|---|---|---|---|
| `d.def8193` | `DRAW"BU8193"` | — (unscaled) | ` 0 , 7 , 57347 ` | ` 0 , 7 , 8195 ` | **DIFF** |
| `d.p8.s2` | `DRAW"S2BU16384"` | `$8000` | ` 0 , 7 , 57348 ` | ` 0 , 7 , 8196 ` | **DIFF** |
| `d.p8.s8` | `DRAW"S8BU4096"` | `$8000` | ` 0 , 7 , 57348 ` | ` 0 , 7 , 8196 ` | **DIFF** |
| `d.p8.s1` | `DRAW"S1BU32768"` | `$8000` | ` 0 , 7 , 57348 ` | ` 0 , 7 , 8196 ` | **DIFF** |
| `d.p8.s4b` | `DRAW"S4BU24576"` | `$8000` | ` 0 , 7 , 57348 ` | ` 0 , 7 , 8196 ` | **DIFF** |
| `d.p8.neg` | `DRAW"S4BU-8192"` | `$8000` | ` 0 , 7 , 57348 ` | ` 0 , 7 , 8196 ` | **DIFF** |
| 🟢 `d.p7ffc` | `DRAW"S4BU8191"` | `$7FFC` | ` 0 , 7 , 57349 ` | same | agree |
| 🟢 `d.p8004` | `DRAW"S4BU8193"` | `$8004` | ` 0 , 7 , 8195 ` | same | agree |
| 🟢 `d.p0` | `DRAW"S4BU16384R5"` | `$0000` | ` 0 , 12 , 4 ` | same | agree |
| 🟢 `d.defneg` | `DRAW"BU-8192"` | — (unscaled) | ` 0 , 7 , 8196 ` | same | agree |

`d.p7ffc` and `d.p8004` are the two rows that make the claim a BOUNDARY rather
than a special case: one step below `$8000` is positive on both sides, one step
above is negative on both sides, and only `$8000` itself moves. `d.p0` carries
an `R5` after the no-op so "the `U` moved nothing" is distinguishable from "the
statement died" ([[an-empty-program-hides-a-wrong-run]]). `d.p8.neg` says the
sign of the COUNT is already gone by the time the product is judged.

## Predicted price, revised

The `$8000` fix: after `gdrw_sc_neg`'s negation, `bit 7,h` still set means the
value was `$8000`, so branch to the POSITIVE shift path (`$8000 >> 2 = $2000`).
`bit 7,h` (2 B) + `jr nz` (2 B) = **+4 B** sub, and one new label on a path that
already exists. Total sub **+3 B** (−1 from `ret z`), main **−2 B**.
