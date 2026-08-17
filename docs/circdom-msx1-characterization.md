# The CIRCLE radius/aspect domain — one comment, five verdicts, and what was actually enforced

D-CIRCDOM, 2026-08-16. Closes the D-NEG8K residual *"FOUR `$8000` VERDICTS REST
ON ONE COMMENT, AND IT IS AN OVERFLOW BOUND, NOT A `$8000` BOUND"*
([`TODO.md`](../TODO.md), [`docs/fixpoint8000-msx1-sweep.md`](fixpoint8000-msx1-sweep.md) §4.2).

Baseline: `15b53bf`, `graphics-acceptance` 290 PASS / 0 FAIL.

---

## §1 The claim, and why one comment was doing five rows' work

`sub/graphics.asm`'s `gfx_circ_scale` header read:

> Bounded-domain: `|v|*ASPS` assumed `<=65535` (true for `|v|<=255`, ASPS<=256
> — the blessed r<=255 domain).

D-NEG8K's sweep classified **five** negate sites `$8000`-unreachable by citing
it, plus a sixth group (`gfx_cross_ge0`'s four `gfx_abs16` calls) in §4.1:

| # | site | sweep's stated reason |
|---|---|---|
| 1 | `gfx_neg16_bc` / `gfx_neg16_de` | "callers are the circle/arc vectors, same bound" |
| 2 | `gfx_circ_scale`'s `gfx_abs16` | "bounded domain, `\|v\| <= 255`" |
| 3 | `gfx_circ_scale`'s re-negate | "same bound" |
| 4 | `gfx_circ_bvec_nudge` | "magnitude is `round(r*QTAB/256)`, `r <= 255`" |
| 5 | `gcbv_y` | "same bound" |
| 6 | `gfx_cross_ge0` ×4 | "same bounded domain" |

Two separate claims were riding on one sentence — an **overflow** bound
(`|v|*ASPS <= 65535`) and a **`$8000`** bound — and the sweep never re-derived
where `r <= 255` is enforced. This slice re-derived it.

---

## §2 The denominator, machine-produced

Scanner: [`scratchpad/circdom_scan.py`](../scratchpad/circdom_scan.py) (kept,
re-runnable). It walks every `.py` file in the tree and extracts every literal
`CIRCLE` statement positionally, so an omitted field does not shift the aspect
column. Nothing is hand-listed.

    python files walked                        357
      with >= 1 CIRCLE literal                  11
      with ZERO (scanned, no match)            346
    CIRCLE statements extracted                119
      in a gate (probes/ or tests/)             47
      in scratchpad/ only                       73

    distinct numeric radii                      15
      refused before any draw                    4    -5, -1, 32768, 40000
      reach the geometry                        11    max = 200
    >>> LARGEST RADIUS DRAWN ANYWHERE            200   (a scratchpad ERROR-FUNNEL
                                                       row: it only asks "K or E",
                                                       it never looks at a pixel)
    >>> LARGEST RADIUS DRAWN BY A GATE            20

    distinct aspect literals                     12   max = 100 (-> ASPS 3)

**No row anywhere in the tree has ever compared the pixels of a circle with
r > 20.** The `dexp5-pin` Makefile comment already said so in as many words —
*"graphics-acceptance's CIRCLE corpus tops out at coordinate 80"* — so the gap
was written down and unread. A bound claimed at 255 was tested at 20.

⚠️ The scanner's own first draft had a defect: it filtered empty fields out of
the optional list, so `CIRCLE(80,80),20,15,,,.25` reported its aspect as `15`.
Fixed before use; the aspect column above is from the corrected run.

---

## §3 Where the domain is ACTUALLY enforced

Traced from the resident marshalling through to the tenant. It is **two tests,
in two files**, and neither mentions 255:

| bound | site | test | result |
|---|---|---|---|
| upper | [`basic/graphics.asm`](../basic/graphics.asm) `cp_req_int` | `call gfx_eval_int16` | **ERR 6** (Overflow) for `\|r\| >= 32768` |
| lower | [`sub/circleparse.asm`](../sub/circleparse.asm) `cpt_after_r` | `ld a,h / or a / jp m,cpt_err5` | **ERR 5** for `r < 0` |

**`GFX_R` is therefore any value in `0..32767`.** There is no `r <= 255` rule in
the tree, and there never was. `ASPS` is `0..256` by construction
(`minor_ratio = aspect` if `aspect<1`, else `1/aspect`).

Measured, boot-per-case, both references (§4 phase S): `CIRCLE(128,96),1000`,
`,1900,,,,.137` and `,900,,,,.3` all answer **K** — accepted, drawn, no error —
on VG-8020 *and* zerobas. The domain really is that wide on both sides.

---

## §4 What the references actually do

Instrument: [`scratchpad/circdom_char.py`](../scratchpad/circdom_char.py) and
[`scratchpad/circdom_char2.py`](../scratchpad/circdom_char2.py). Each case draws on
a `COLOR15,4,7:SCREEN2` plane, holds it in a `GOTO`-self loop, and reads back
**the entire 6144-byte pattern plane** — no hand-picked window, so the readout
cannot be blind to its own subject — reduced to (popcount, bounding box, sha1).

### 4.1 The product bound is FALSE, and reachable

`gfx_mul16u` truncates at 16 bits, so `|v|*ASPS >= 65536` wraps.

| row | ASPS | max product | VG-8020 | zerobas | verdict |
|---|---|---|---|---|---|
| `r20_base` | 256 | 5 120 fits | 112 px | 112 px, same sha1 | agree |
| `r200` | 256 | 51 200 fits | 0 px | 0 px | agree (**both blank** — see §4.2) |
| `r255` | 256 | 65 280 fits | 0 px | 0 px | agree (both blank) |
| `r256` | 256 | **65 536 OVF** | **0 px** | **31 px**, bbox (113,96,143,96) | **DIFF** |
| `r257` | 256 | **65 792 OVF** | **0 px** | **88 px**, bbox (101,95,155,97) | **DIFF** |
| `r300` | 256 | **76 800 OVF** | **0 px** | **512 px**, bbox (0,52,255,140) | **DIFF** |
| `r1000` | 256 | **256 000 OVF** | 0 px | 0 px | agree — **a predicted DIFF that missed**, §4.2 |
| `r300_a09` | 230 | **69 000 OVF** | **0 px** | **376 px**, bbox (33,82,223,110) | **DIFF** |
| `r900_a03` | 77 | **69 300 OVF** | **0 px** | **512 px**, bbox (0,81,255,111) | **DIFF** |
| `r1900_a0137` | 35 | **66 500 OVF** | **0 px** | **512 px**, bbox (0,92,255,100) | **DIFF** |
| `r300_a03` | 77 | 23 100 fits | 512 px | 512 px, ±1 px | DIFF — a *different* defect, §5 |
| `r200_a03` | 77 | 15 400 fits | 512 px | 512 px, ±1 px | DIFF — same, §5 |
| **`r700_a0137`** | **35** | **24 500 fits** | **421 px** | **421 px, sha1 `2f6257f6` IDENTICAL** | **agree** |

**`r700_a0137` is the row that settles it.** r=700 is 2.7× outside the retired
"blessed r<=255 domain" and the two machines agree **byte for byte** across a
visible, full-screen ellipse — because its product fits. The bound that governs
is the **product**, not the radius. Every DIFF row above has a product ≥ 65536;
every agreeing row has one below it, with no exception either way.

The failure mode is not subtle: at these radii **the reference draws nothing on
the screen at all** (every point of the true figure is off-screen and clipped)
while zerobas wraps the scale and paints spurious pixels in the middle of it.

⚠️ The old note in `gfx_circle_op`'s header understated its own blast radius: it
said a large radius *"may mis-rasterise the **arc mask**"*, i.e. `gfx_cross_ge0`.
But `gfx_circ_scale` runs on **every point of every circle** — arc or not, aspect
or not — and four of the six DIFF rows above are plain full circles with no arc
and no aspect. **A rule's blast radius is a claim too.** The "never crashes" half
of the old note survived: all 13 rows returned K on both machines.

### 4.2 Three predictions missed, and the misses are the finding

Predictions were written before the run
([`scratchpad/circdom_predictions.md`](../scratchpad/circdom_predictions.md)):
6 DIFF / 6 AGREE. Scored **9 exact, 3 missed, 1 partial**.

* ✅ `r256` was predicted "≈33 px in a run at y=96, bbox ≈ (112,96,144,96)" and
  measured **31 px, bbox (113,96,143,96)**. `r300` was predicted "y spanning
  ≈52..140" from `scale(300)` wrapping to 44, and measured **exactly (…,52,…,140)**.
  Both were computed **from the source arithmetic**.
* ◐ `r257` was predicted ≈66 px, measured 88. Direction right, count wrong.
* 🔴 **`r1000` was predicted DIFF and AGREED — both blank.** The model *"the
  product wraps, therefore pixels appear on screen"* does not follow. With
  ASPS=256 the wrap is exactly `v mod 256`; wherever that lands on screen the
  **unscaled major-axis offset** is already off screen, so the clip eats it.
  That model was reached by **analogy from `r300`**, not traced. Everything
  traced through the source was exact; the one thing reached by analogy was
  wrong — the same split D-NEG8K measured.
* 🔴 **`r300_a03` and `r200_a03` were predicted AGREE and DIFFERED** — by exactly
  one pixel of minor half-axis, at radii where the product **fits**. That is a
  second defect with nothing to do with the overflow, and nothing in this
  slice's design was looking for it. See §5.

⚠️ `r200` and `r255` agree because **both machines draw nothing** — they are
vacuous as evidence about the scale, and are kept only as the corpus ceiling.
The row that carries the "large radius is fine when the product fits" claim is
`r700_a0137`, which is *visible* on both sides. A case that agrees can agree for
the wrong reason.

⚠️ Round 1's phase 1 scored four rows `DIFF` on `ref=None zb=None`. **Both-None
is a NO READING, not a divergence** — the batched step budget is too short for a
long draw. Re-asked boot-per-case at `step=25.0` they are all **K/K agree**
(§3). `r32767` still times out and is reported **NOREAD**, not agreement.

---

## §5 The second defect: `GFX_ASPS` rounds where the reference truncates

`cpt_asp_scale256` computed `S := round(minor_ratio*256)`. The reference
**truncates**. Five rows, all `CIRCLE(128,96),r,15,,,aspect`, minor half-axis
read off the bounding box:

| row | aspect | `aspect*256` | floor | round | VG-8020 | zerobas (before) | |
|---|---|---|---|---|---|---|---|
| `a03_r128` | .3 | 76.80 | 76 → **38** | 77 → 39 | **38** | 39 | **DIFF** |
| `a055_r128` | .55 | 140.80 | 140 → **70** | 141 → 71 | **70** | 71 | **DIFF** |
| `a01_r255` | .1 | 25.60 | 25 → **25** | 26 → 26 | **25** | 26 | **DIFF** |
| `a07_r128` | .7 | 179.20 | 179 → 90 | 179 → 90 | 90 | 90 | control, **sha1 identical** |
| `a025_r128` | .25 | 64.00 | 64 → 32 | 64 → 32 | 32 | 32 | control, **sha1 identical** |

**3/3 discriminating aspects say TRUNCATE. 2/2 controls — where floor and
round-half-up predict the *same* picture — came back byte-identical**, which is
what makes the three DIFFs attributable to the rounding rule rather than to the
rig, the radius, or the clip. Two data points would have been an inference;
five rows with two controls is a measurement.

### 5.1 Round 3 — the other branch, because the fix shipped where the rule was never read

The five rows above are **all `aspect < 1`**: the `cpt_asp_le1` branch, where
`minor_ratio = aspect` lands in `ARGA` directly. `aspect >= 1` reaches the *same*
`cpt_asp_scale256` call, but only after `minor_ratio = 1/aspect` through
`fp_div` — and the gate's two such rows were `,,,2` (1/2 → 128.0) and `,,,3`
(1/3 → 85.33), **both `floor == round`**. So the fix went in at a caller where
its rule had never been read. Filed as a residual, then measured
([`scratchpad/circdom_char3.py`](../scratchpad/circdom_char3.py)) — with
`ASPMAJ=1` the scaled axis is **X**, so the half-axis read off the box is
horizontal:

| row | aspect | `1/a*256` | floor | round | VG-8020 | zerobas | |
|---|---|---|---|---|---|---|---|
| `a17_r128` | 1.7 | 150.59 | 150 → **75** | 151 → 76 | **75** | **75** | agree |
| `a13_r128` | 1.3 | 196.92 | 196 → **98** | 197 → 99 | **98** | **98** | agree |
| `a11_r128` | 1.1 | 232.73 | 232 → **116** | 233 → 117 | **116** | **116** | agree |
| `a2_r128` | 2 | 128.00 | 128 → 64 | 128 → 64 | 64 | 64 | control, sha1 identical |
| `a4_r128` | 4 | 64.00 | 64 → 32 | 64 → 32 | 32 | 32 | control, sha1 identical |

**0/5 divergences; prediction EXACT.** Three independent discriminators all land
on **floor**, so the truncation is right on this branch too — **and** `fp_div`'s
precision matches the reference at three non-trivial reciprocals, which was a
separate claim riding along and is now measured rather than assumed.

These rows also say something about the *pre-fix* tree that no earlier row
could: round-half-up would have given 76 / 99 / 117, so **zerobas was wrong on
the `aspect >= 1` branch as well**, and had been all along. That is a
measurement, not an inference — K-CD1 reverts the fix and reddens exactly these
three alongside the three from §5 (see §9).

**Why the corpus could not see it.** Every aspect the tree had ever drawn has
`floor == round`: `.25`→64, `.5`→128, `2`→1/2→128, `3`→1/3→85.33, and
`dexp5-pin`'s `.01`/`1`/`100`. `.3` is the first value in the tree's history
where the two models come apart — **and it needs r ≥ 128 for the 1/256 to reach
a whole pixel, while the gate's largest drawn radius was 20.** Two independent
blind spots had to line up, and they did.

Note this defect is **inside** the retired "blessed" domain: r=128, aspect .3.
The `r <= 255` claim would not have protected against it even if it had been true.

### The fix — 0 B

    -                call    cpt_round
    +                call    flt_to_int16        ; DE := TRUNC(...) -- not cpt_round

`cpt_round` is `abs → +0.5 → flt_to_int16 → reapply sign`; calling
`flt_to_int16` directly is the truncation, and it is the routine `cpt_round`
itself tail-uses, so the swap is **byte-neutral**. Safe unsigned because
`cpt_after_aspect` has already refused `aspect < 0` and `1/aspect` is positive.

⚠️ **`cpt_round` itself was NOT changed.** It is shared with
`cpt_boundary_prep`, whose `brad = round(|angle|*128/pi)` is separately pinned
(spec §5.2.1 REVISED) and gated green by the arc rows. Only the ASPS caller
truncates.

---

## §6 The five `$8000` verdicts, re-derived

All five **hold**. **None of them holds for the stated reason.**

| # | site | why `$8000` is unreachable | class |
|---|---|---|---|
| 1 | `gfx_neg16_bc` / `gfx_neg16_de` | only callers are `gco_emit8`'s eight mirror emits, passing `GFX_QX`/`GFX_QY`; `gfx_circ_init` seeds `QY=r`, `QY` only decrements, `QX` climbs while `QX<=QY` → both in `-1..r`, `r ∈ 0..32767` | **radius bound** (the real one, §3) |
| 2 | `gfx_circ_scale`'s `gfx_abs16` | input is `GFX_PX`/`GFX_PY` = ±`QX`/±`QY` → `[-32767, 32767]` | **radius bound** |
| 3 | `gfx_circ_scale`'s re-negate | input is post-`ld l,h / ld h,0` → **0..255 by construction** | **byte truncation** |
| 4 | `gfx_circ_bvec_nudge` | input is `gfx_circ_bvec_mag`'s output (same `ld l,h / ld h,0`) or the literal 1 | **byte truncation** |
| 5 | `gcbv_y` | nudge output (−255..255), optionally through `gfx_circ_scale` (±0..255) | **byte truncation** |
| 6 | `gfx_cross_ge0` ×4 | components all arrived via 4 or 5 above → \|value\| ≤ 255 | **byte truncation** |

**Three of the six are safe for a reason that needs no domain claim at all** —
a `ld l,h / ld h,0` pair keeps only a high byte, so `$8000` is not representable
at those inputs *however large the radius gets*, and would still not be if the
domain widened tomorrow. The other three are bounded by the int16 coercion at
`cp_req_int`, which is 128× looser than the bound that was cited.

Cost of the `$8000` half: **six citations, zero bytes**, exactly as the residual
priced it — but every one of the six now names a site instead of a sentence.

🔴 **And the two halves are coupled in the direction nobody expected.** Site 3 is
safe *because the multiply truncates*. Fixing the §4.1 overflow — computing
`|v|*ASPS` exactly — makes `$8000` **reachable there for the first time**:
`v = 32767, ASPS = 256 → (32767*256 + 128) >> 8 = 32768 = $8000`, and the
re-negate would meet the fixed point. The residual asked whether a `$8000` arm
was needed and the answer today is no — **but the arm becomes necessary the
moment the overflow it was conflated with is repaired.** Recorded in
`gfx_circle_op`'s header and filed in `TODO.md`.

> 🔴 **SUPERSEDED 2026-08-16 by D-CIRCOVF**
> ([`circovf-msx1-oracle.md`](circovf-msx1-oracle.md) §5.1). The arithmetic in
> the paragraph above is right and the conclusion is **design-dependent, which
> this paragraph does not say**. `ASPS` is 0..256, and `ASPS = 256` is the only
> value that can reach 32768 — it is also the only value for which the scale is
> the **identity**, so four bytes of branch skip the multiply altogether. On
> that arm the result is `|v| ≤ 32767`; on the multiply arm `ASPS ≤ 255` gives
> at most `(32767*255+128)>>8 = 32639`. **The overflow was repaired and no
> `$8000` arm was needed** (600 000-case sweep,
> `scratchpad/circovf_asmsim.py`).
>
> A coupling *does* bind, at a site this table does not name. Row 6,
> `gfx_cross_ge0`, is charged here to "byte truncation" — correctly — and that
> is exactly why its two 16-bit **products** stop being safe when the truncation
> is removed. It was not broken before D-CIRCOVF and would have been broken *by*
> it. Right structural claim, wrong site, opposite direction: what the fix makes
> reachable is not a fixed point in a negate, it is an overflow in a multiply.

---

## §7 Gate rows

Eleven rows added to `CIRCLE_CASES` / phase E of
[`probes/basic/basic_probe_graphics.py`](../probes/basic/basic_probe_graphics.py):
`ell_a03r128`, `ell_a055r128`, `ell_a01r255` (the three §5 DIFFs, now green),
`ell_a07r128`, `ell_a025r128` (the two §5 controls, green before *and* after),
and `ell_r700a0137` (the §4.1 product-bound row).

and five more from §5.1 covering the `aspect >= 1` branch: `ell_a17r128`, `ell_a13r128`, `ell_a11r128` (discriminators) and `ell_a2r128`, `ell_a4r128` (exact controls).

**This raises the gate's largest drawn radius from 20 to 700**, and takes `graphics-acceptance` from 290 to **301 PASS / 0 FAIL**.

`band_segs` gained a clamp to the 32×24 plane: an unclamped band for a figure
wider than the screen walks off the pattern plane and reads the **name table**
at `$1800` as if it were pixels. The clamp is asserted to be a **no-op for every
row that predates it** by `_assert_band_clamp_is_noop`, run from `main()` —
proved rather than claimed.

---

## §8 Price and walls

| | predicted | measured |
|---|---|---|
| bytes | 0 (a call-target swap) | **0** |
| low region | 5 B unchanged | **5 B** |
| main page 1 | 67 B unchanged | **67 B** |
| sub page 0 | 3604 B unchanged | **3604 B** |
| sub page 1 | 1483 B unchanged | **1483 B** |
| `basic-reloc.rom` | unchanged | **`8e5391b3`** unchanged |
| `disk.rom` | unchanged | **`2c630d3d`** unchanged |
| `zerobas-main-eu.rom` | unchanged | **`01ab88f1`** unchanged |
| `sub.rom` | **moves** (page-1 tenant edit) | `c2292117` → **`8161c1a2`** |

4/4 hash predictions exact. A page-1 sub-tenant edit leaves every main-ROM image
alone — the converse of D-NEG8K's "a low-region edit is never sub-ROM-neutral".

---

## §9 Knives

Runner: [`scratchpad/circdom_knives.py`](../scratchpad/circdom_knives.py). Subject
is the probe invoked directly (never `make`); snapshot restore in a `finally`;
build before the baseline; each cut site asserted to occur **exactly once**; the
probe's footer required on every run so a crashed prefix cannot read as a cut;
baseline refused unless it is green with ≥250 rows and `sub.rom` is the
post-slice image. All four cuts are **byte-neutral opcode swaps**.

### Predictions, written before the run

| knife | cut | predicted |
|---|---|---|
| **K-CD1** | `call flt_to_int16` → `call cpt_round` in `cpt_asp_scale256` — the exact inverse of the slice's only functional edit | **3 rows**: `ell_a03r128`, `ell_a055r128`, `ell_a01r255`. The two controls and `ell_r700a0137` (aspect .137 → 35.07, floor == round) must **stay green**. And `sub.rom` must rebuild to the **pre-slice `c2292117`, byte for byte** |
| **K-CD2** | `call flt_to_int16` → `ld de,256` — pin ASPS, no scaling at all | **11 rows**: all six new rows plus the five pre-existing aspect rows `ell_a025`, `ell_a05`, `ell_a2`, `ell_a3`, `ell_a05r15`. Falsifies that these rows read `GFX_ASPS` at all |
| **K-CD3** | `ld de,128` → `ld de,0` in `gfx_circ_scale` — round down instead of half-up | **exactly 5 rows**: `ell_a3`, `ell_a05r15`, `ell_a01r255`, `ell_a07r128`, `ell_r700a0137`. Hand-computed per row from `(v*ASPS)>>8` vs `(v*ASPS+128)>>8`, so this predicts **which** rows move, not just how many — `ell_a03r128`, `ell_a055r128`, `ell_a025r128`, `ell_a025`, `ell_a05`, `ell_a2` must **not** move |
| **K-CD4** | band clamp `min(23,…)` → `min(5,…)` | **no rows at all**: `_assert_band_clamp_is_noop` must fire and abort the probe with an `AssertionError` and **no footer**. The subject is the gate's own guard — a knife that reddens nothing here would mean the guard is decorative |

K-CD3 is the one that earns `ell_r700a0137` its place: it proves the r=700 row
is a live detector of `gfx_circ_scale`'s arithmetic, not merely a row that
happens to agree.

🔴 **A LIMITATION OF THIS RUNNER, FOUND BY READING ITS OWN BASELINE.** It reports
`rows=289` where the probe prints **296** `PASS` lines, because it keys rows by
label into a dict and **five labels are duplicated across phases** — `Philips`
and `C-BIOS` (the JIFFY teeth rows), and `after`, `colour16_err`, `scr0_err`
(error-funnel rows that appear in both `CIRCLE_BEHAV` and `DRAW_BEHAV`). A move
confined to one instance of a duplicated label would be **silently under-reported**.
It does not affect this scorecard — every predicted row is a uniquely-labelled
`ell_*` pixel row, and no aspect-scale cut can reach an error-funnel row — but
the next runner should key on `(phase, index, label)`, not on the label alone.
The `>= 250 rows` short-report guard is what makes the discrepancy visible at
all; a runner without one would never have printed the number to notice.

### Results — **3/4 EXACT, 1 MISS**

| knife | predicted | measured | |
|---|---|---|---|
| **K-CD1** | 3 rows | `ell_a03r128`, `ell_a055r128`, `ell_a01r255` — footer `FAIL (3)`, rc 1 | **EXACT** |
| **K-CD2** | 11 rows | exactly those 11 — footer `FAIL (11)`, rc 1 | **EXACT** |
| **K-CD3** | **5 named rows** | **11 rows** — all 5 predicted moved (`missing = []`), plus 6 more | 🔴 **MISS** |
| **K-CD4** | abort in the guard, no footer | `AssertionError`, no footer, rc 1 | **EXACT** |

**K-CD1 also rebuilt `sub.rom` to `c2292117` — the pre-slice hash, byte for
byte.** The slice's only functional edit is one call target, and reverting it
reproduces the previous ROM exactly; that is the cheapest correctness proof
available and it cost one hash comparison.

Tree restored from the snapshot and rebuilt: `sub.rom 8161c1a2` (OK).

### 🔴 Why K-CD3 missed — I predicted against my own summary, not against the row

K-CD3 (`ld de,128` → `ld de,0` in `gfx_circ_scale`) was predicted to move
**exactly five** named rows. It moved **eleven**, a strict superset: every row I
named did move, and six more went with them.

The error is not in the arithmetic. It is that **I computed the prediction from
the bounding box** — `scale(r)` at the single extreme point of each figure —
**while the gate compares the entire 6144-byte plane.** For `ell_a03r128` the
extreme is unchanged (`(128*76)>>8` and `(128*76+128)>>8` are both 38, which is
what I checked and why I put it in the "must not move" list), but an *interior*
point at v=100 goes `(100*76)>>8 = 29` against `(100*76+128)>>8 = 30`. The row
sees that; my prediction did not.

**The reduced readout I built to make the characterization legible — popcount,
bbox, sha1 — is not the comparison the gate makes, and I reasoned about the row
using the summary instead of the artifact.** The apparatus was part of the
measurement in the one place I forgot to look: my own reporting layer. The
`missing = []` line is the tell — the model was not wrong, it was scoped to one
pixel per figure when the row reads all of them.

The consequence is in the slice's favour: K-CD3 is a **stronger** knife than
designed. It shows that *every* aspect row in the gate, old and new, is a live
detector of `gfx_circ_scale`'s rounding constant — which is more than
`ell_r700a0137` was recruited to prove.

### §9A Round 3 — all four re-run, because the row set grew

Adding five rows invalidates every prediction written against the old set, so
the whole knife battery was re-run rather than just the one that changed.
Baseline 301 PASS / 0 FAIL (294 keys after the label collapse noted above).

| knife | predicted | measured | |
|---|---|---|---|
| **K-CD1** | **6 rows** — three per branch of `cpt_asp_scale256` | exactly those 6: `ell_a03r128`, `ell_a055r128`, `ell_a01r255`, `ell_a17r128`, `ell_a13r128`, `ell_a11r128` — footer `FAIL (6)` | **EXACT** |
| **K-CD2** | 15 rows (hand-typed) | **16** — `missing = []`, `extra = ['ell_a2r128']` | 🔴 **MISS by one** |
| **K-CD3** | the round-2 measured set (11), round-3 rows deliberately excluded | 16 — the round-2 half reproduced **exactly**, and all five round-3 rows moved | **not a prediction** — see below |
| **K-CD4** | abort in the guard, no footer | `AssertionError`, no footer, rc 1 | **EXACT** |

**K-CD1 again rebuilt `sub.rom` to `c2292117`, the pre-slice hash, byte for
byte** — and this time it carries the round-3 finding: the three `aspect >= 1`
rows go red under the reverted fix, so **the pre-fix tree was wrong on that
branch too**. That was an inference in §5.1 and is a measurement here.

🔴 **K-CD2's miss has no modelling content, and that is the lesson.** The model
— *"every row carrying an aspect field moves"* — is right, and the 16 rows
measured are **exactly** the set derived mechanically from `CIRCLE_CASES`. What
failed was that the prediction was a **hand-typed list that I extended by hand**
when the five round-3 rows landed, and I dropped `ell_a2r128` while remembering
`ell_a4r128`. A hand-maintained prediction set is a pure transcription risk, and
it fails **in the direction that looks like a real finding** — an "extra" row
reads as a discovery when it is a typo. K-CD2's prediction is now **derived from
the probe** (`_aspect_rows()`), so adding a gate row can no longer leave it
stale. The miss stands as scored; the runner was fixed for the next reader
rather than re-run until the prediction looked right.

⚠️ **K-CD3 should not be scored EXACT or MISS at all.** Its prediction was
deliberately the round-2 *measurement* copied forward — a regression check on a
known answer — with the round-3 rows left out so that whatever they did was new
information. They all moved. The runner's binary EXACT/MISS verdict has no
meaning for a knife of that shape and reported "MISS" for a knife that did
exactly what it was designed to do; it needs a third state.
