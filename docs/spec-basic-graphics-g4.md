# Spec — graphics Slice G4: `CIRCLE` (+ aspect ratio + start/end-angle arcs)

**Status: SIGNED OFF (2026-07-21).** All §9 decisions approved — G4-a…f + arcbnd on
the measured recommendations; **G4-rneg → ERR 5** (documented deviation) and **G4-work
→ match the `GXPOS=r,GYPOS=cy` quirk** confirmed by the user. Implementation may
proceed per the §9 order. Slice-design addendum to the arc
spec [`spec-basic-graphics.md`](spec-basic-graphics.md) (crux D1/D2/D4/D5 approved)
and the landed G1/G2/G3 specs
([g1](spec-basic-graphics-g1.md) / [g2](spec-basic-graphics-g2.md) /
[g3](spec-basic-graphics-g3.md)). **No asm is written until the decisions in §9 are
approved.** The **VG-8020 characterization pass is complete** (§11, three rounds) and
the exact rasteriser variants are **host-fit against the captured pixels** (§4/§11) —
the recurring arc lesson ([memory: error-handling-arc]) applied up front, because a
green build hides a wrong pixel as easily as a dead trap branch.

G3 delivered the first EI-during-draw op (`LINE`) with the DI-per-pixel VDP RMW. **G4
is the arc's first *curved* rasteriser and its first op with genuinely novel
sub-features** — a per-point-scaled ellipse and angular arcs with the classic
negative-angle radius spokes. It reuses G3's EI-loop discipline and pixel primitive
verbatim; the only new tenant code is the midpoint-circle generator, the per-point
minor scale, and the arc angle mask.

> **Three crux surfaces, all measured, not reasoned:**
> 1. **Circle pixel-exactness.** The own-design integer midpoint circle must reproduce
>    the reference pixel set **byte-for-byte**. Pinned by fitting against six captured
>    VG-8020 circles (r=4/7/8/12/15/20): **`d₀ = 1−r`; per step plot the 8 octant
>    points, `if d<0: d += 2x+3` else `d += 2(x−y)+5, y−−`; `x++` while `x≤y`.** All
>    six match exactly ([scratchpad/g4_circle_fit.py](../scratchpad/g4_circle_fit.py)).
> 2. **Ellipse model.** Aspect is **not** a two-semi-axis midpoint ellipse (that model
>    mismatches every captured shape). It is **the major-radius circle with the minor
>    coordinate scaled per-plotted-point** — matched on all five captured ellipses,
>    and matched again with an **8.8 fixed-point** scale (`(off·S+128)>>8`) so the
>    tenant needs no float (§4.2/§11.3).
> 3. **Arc = angle-masked circle + spokes.** The arc is the subset of the full-circle
>    octant points lying in the **CCW sweep from `|start|` to `|end|`**; a **negative**
>    start/end additionally draws a **radius spoke** centre→endpoint. Matched (to a ±1
>    boundary pixel, §5/§9 G4-arcbnd) on four captured arcs incl. the wrap case.

---

## 1. What lands in G4 vs. what defers

| Piece | G4 | Notes |
|---|---|---|
| `CIRCLE (x,y),r` full circle | ✅ | own-design integer midpoint (§4.1) |
| `CIRCLE [STEP](x,y),r` | ✅ | STEP resolved vs `GRPAC`, as G2/G3 (§3.2) |
| `CIRCLE (x,y),r,c` colour | ✅ | per-pixel clash RMW, reuses `gfx_color_rmw` (§4.4) |
| `…,r,c,start,end` arc | ✅ | CCW `|start|→|end|`; negative ⇒ radius spoke (§5) |
| `…,r,c,start,end,aspect` ellipse | ✅ | major circle + per-point 8.8 minor scale (§4.2) |
| Off-screen **clipping** (draw on-screen portion) | ✅ | measured: off-screen/neg centre = no error, clip (§3.3/§11) |
| `r = 0` ⇒ single centre pixel | ✅ | measured no-error (§11) |
| `PAINT` / `DRAW` / sprites | ❌ G5+ | — |
| Perfect aspect rounding at exact-half knife-edges | ❌ | float-repr-dependent; common aspects exact (§4.3/§9 G4-asprnd) |
| Bit-exact arc-endpoint inclusivity | ⚠️ | model exact to ±1 boundary pixel; pinned during impl (§9 G4-arcbnd) |

**New token + kwtable row (repack-only).** `CIRCLE=$BC` (arc §7, re-confirmed §11.1)
is **not yet** in [basic/kwtable.inc](basic/kwtable.inc); G4 adds one row
(`db 6,"CIRCLE",1,CIRCLE_TOKEN`) and one interp dispatch arm (`cp CIRCLE_TOKEN /
jp z,ex_circle`), the exact G2 `PSET` pattern
([basic/kwtable.inc:333](basic/kwtable.inc), [basic/interp.asm:274](basic/interp.asm)).
`$BC` collides with nothing (arc §7). The kwtable row + dispatch are **repack-only**
(guarded like PSET) so the lean cart stays byte-identical — the tenant op is
unreachable on lean, and `ex_circle` compiles only under the repack guard.

---

## 2. Placement + the EI-during-draw discipline (inherited from G3)

`CIRCLE` runs in the **page-0 graphics tenant** ([sub/graphics.asm](sub/graphics.asm))
as a new selector op **`GFX_OP=4`**, beside G1 self-test (0), G2 plot/point (1/2), and
G3 line/box (3). The interrupt discipline is **identical to G3** (arc §2, measured
JIFFY advancing mid-`CIRCLE` at §11.6/arc §11.6): **`ei` between pixels, a brief `di`
only around each pixel's read-modify-write**, whose reads carry the G2 **fetch-window**
settle in `gfx_rd_raw` ([memory: vdp-direct-port-read-fetch-window]). A large circle
(`CIRCLE(128,96),80`) is many frames of work; music must keep playing.

**Reuse, not re-derive.** The per-pixel primitive is G3's **`gfx_plot_cur`** verbatim
(clip-by-mask + DI-guarded clash RMW reusing `gfx_calc_addr`/`gfx_color_rmw`/
`gfx_rd_raw`, [sub/graphics.asm:438](sub/graphics.asm)). The only new tenant code is the
octant generator, the per-point minor scale, and the arc mask — each emitting pixels
through `gfx_plot_cur`. Spokes (§5) reuse the **landed G3 `GFX_OP=3` line op**, not new
code.

**BIOS-agnostic (inherited):** touches only `$98`/`$99`, never a VDP mode register.

---

## 3. `CIRCLE` grammar + semantics (measured §11)

**Grammar (VG-8020 crunch, §11.1):**
```
CIRCLE  [STEP] '(' x ',' y ')'  ',' r
        [ ',' [c] [ ',' [start] [ ',' [end] [ ',' aspect ] ] ] ]
```
- `CIRCLE`=`$BC`; the coordinate is `parse_coord` (G2/G3, reused verbatim). Radius,
  colour, and aspect are **numeric expressions**; start/end are **numeric expressions
  in radians** (stored as floats — `1D …` prefix; negatives are unary-minus `$F2`
  expressions, §11.1). Any trailing arg may be omitted with a placeholder comma
  (`CIRCLE(x,y),r,,,,aspect`).
- `STEP` = `$DC` prefix on the coordinate; resolved vs `GRPAC` (§3.2).

**3.1 Draw.** Plot the circle of integer radius `r` centred at `(x,y)` with colour `c`
(default `FORCLR` when omitted), using the per-pixel clash RMW (§4.4). **Default aspect
is pixel-round 1:1** — measured, not folklore: r=20 → width 41 = height 41 = 2r+1, same
for r=4/8/12 (§11.2). `r=0` lights the single centre pixel (§11.5).

**3.2 STEP / continuation.** `CIRCLE STEP(dx,dy),r` resolves the centre vs `GRPAC`
(the G2/G3 `parse_coord` STEP path). After a `CIRCLE`, **`GRPAC` = the centre**
(measured §11.4: `CIRCLE(30,40),10` → `GRPAC=(30,40)`), so a following continuation
references the centre.

**3.3 Off-screen ⇒ CLIP, not error (measured §11.5).** Like `LINE`: an off-screen or
negative **centre** draws the on-screen portion and raises no error
(`CIRCLE(300,300),10` / `CIRCLE(-5,-5),10` → no error). A `>int16` centre coord or
radius → **Overflow ERR 6** (`CIRCLE(32768,0),10` and `CIRCLE(0,0),32768` both ERR 6).
Clip = the same per-pixel mask as G3 (`gfx_plot_cur`). A huge on-screen radius walks
many octant steps (slow but EI) — the G3 perf caveat (§4.5).

**3.4 Errors (measured §11.5):** SCREEN 0/1 → **Illegal function call ERR 5**;
colour > 15 → **ERR 5**; aspect < 0 → **ERR 5**; centre/radius > int16 → **ERR 6**;
bad grammar (missing `,r`, stray token) → **Syntax error ERR 2**. **Negative radius**
→ see §9 G4-rneg (reference hangs; decision needed).

---

## 4. The rasteriser (own-design, host-fit) — crux 1 & 2

**4.1 Circle — exact variant (pinned by fitting, §11.3).** Integer midpoint circle,
generating one octant and mirroring to eight:
```
x = 0 ; y = r ; d = 1 − r
while x ≤ y:
    plot (±x,±y) and (±y,±x)          ; 8 octant points (via gfx_plot_cur)
    if d < 0:  d += 2·x + 3
    else:      d += 2·(x − y) + 5 ; y −= 1
    x += 1
```
Reproduces **all six** captured circles exactly (r=4/7/8/12/15/20; §11.3). The captured
point-sets become the host-unit-test oracle (§8). 16-bit-clean: `d`, `2x`, `2(x−y)` fit
int16 for r ≤ 255; `x,y ≤ 255`.

**4.2 Ellipse — the major circle with a per-point minor scale (Model A, §11.3).**
Aspect selects the **major** axis (the one that keeps radius `r`) and a **minor scale**
`S` applied to the other coordinate of **every** plotted octant point:
- `aspect ≤ 1`: **x is major** (offset kept), **y scaled**: `y' = round(y·aspect)`.
- `aspect > 1`: **y is major** (offset kept), **x scaled**: `x' = round(x/aspect)`.

The tenant applies `S` as **8.8 fixed-point** (`S = round(minor_ratio·256)`,
`minor_ratio = aspect` or `1/aspect`): for each octant offset `off`,
`off' = sign(off)·((|off|·S + 128) >> 8)`. This **matched all five** captured ellipses
(aspect 0.25/0.5/2/3, r=15/20; §11.3) and the two-semi-axis midpoint-ellipse model
(Model B) **mismatched every one** — so Model A is pinned. Default aspect (omitted) =
`S = 256` (ratio 1) ⇒ the pure circle path.

**4.3 Aspect knife-edge residual (§9 G4-asprnd).** At exact-half scaled values (e.g.
aspect 0.175, `20·0.175 = 3.5`) the reference tips on its BCD-float representation
(measured y-radius 3, i.e. rounds *down* there), while a clean `round-half-up` (8.8 or
real) gives 4. Common aspects (0.25/0.5/1/2/3) are exact both ways; the knife-edges are
unobservable-in-practice edges — matched-where-clean-room-achievable
([memory: bug-for-bug-compat-over-accuracy]), documented, gate uses common aspects.

**4.4 Per-pixel colour.** Each plotted pixel takes the **same clash RMW as PSET/LINE**
(§11.3: `CIRCLE(40,40),8,6` → colour bytes `$61` = fg 6 | bg 1). Reuses `gfx_plot_cur`
→ `gfx_color_rmw` verbatim.

**4.5 Clip = masking; perf note (inherited G3).** Octant points off-screen are masked
by `gfx_plot_cur`; a large radius still iterates every octant step (slow but EI). Same
documented edge as G3-perf; correctness before speed.

---

## 5. Arcs — start/end angle + negative-angle spokes (measured §11.4) — crux 3

**5.1 Angle convention (measured §11.4).** Angles are radians. **0 = +x (right, 3
o'clock); positive = counter-clockwise** (toward screen-top, −y). Measured:
`CIRCLE,…,0,1.57` fills the **upper-right** quadrant (right→top); `1.57,3.14` the
**upper-left**; `0,3.14` the whole **top** half. `0,6.28` (≈2π) = the full circle
(pixel-identical to no-arc, §11.4).

**5.2 Arc = CCW sweep from `|start|` to `|end|`.** The drawn pixels are the full-circle
octant points whose direction lies in the CCW sweep from `|start|` to `|end|` (mod 2π);
**`end < start` wraps through 0** (measured `3 → 1` covers left→bottom→right→up-to-1rad,
§11.4). The tenant keeps octant point `P` iff it is in the CCW wedge via **integer
cross-product sign tests** on the two boundary vectors `S`, `E` (`cross(S,P) ≤ 0 ∧
cross(P,E) ≤ 0` for `sweep ≤ π`, `∨` for `sweep > π` — both boundaries **inclusive**,
§5.4). The cross product is 16-bit-bounded, so `S`/`E` stay small (≈ ±r).

**5.2.1 Boundary vectors — TRIG-FREE (REVISED 2026-07-21, supersedes the SIN/COS
design).** The original design computed `S`/`E` via the float math-pack `SIN`/`COS`; that
**infinite-looped** inside the sincos series `fp_mul` in the CIRCLE call context (root-
caused dynamically: [scratchpad/g4_hang_probe.py](../scratchpad/g4_hang_probe.py) — the
spin is in the sub-ROM `fp_mul` during the series, not in the tenant). It is **replaced
by a lightweight integer method** (user decision 2026-07-21): the boundary component's
**sign** comes from a **quadrant comparison** of the angle (`θ` vs `π/2, π, 3π/2` — plain
float compares, *no multiply-series, cannot hang*), and its **magnitude** from a compact
**256-entry integer sine table** (8.8 fixed, `±256`): `Sx = sign_c·round(r·|cos|)`,
`Sy = −sign_s·round(r·|sin|)`, with a **±1 direction nudge** when a magnitude rounds to 0
but its quadrant sign is non-zero (the near-cardinal case: `1.57` is quad 0 ⇒ `cos > 0`,
distinguished from `π/2` — the reference distinguishes `1.57` from `1.58`, §5.4). The
angle→table-index is one bounded integer-range op (`brad = flt_to_int16(θ·256/2π)`, a
single clean `fp_mul` from post-eval state — *not* the sincos series). **Host-fit
reproduces every captured arc + boundary re-capture EXACTLY**
([scratchpad/g4_trigfree_fit.py](../scratchpad/g4_trigfree_fit.py): all 4 arcs + both
boundary re-captures MATCH).

> 🔴 **RETRACTED IN PART — D-ARCMASK, 2026-08-17**
> ([docs/arcmask-msx1-characterization.md](arcmask-msx1-characterization.md)).
> The host fit is real; **its corpus cannot see the question it is cited for.**
> [g4_pointsets.json](../scratchpad/g4_pointsets.json) holds radii **4, 7, 8, 12,
> 15, 20**, and every **arc** row in it is **r=15**.
> The premise above — *the reference's boundary vector is the exact ray
> `round(r·|cos|)` / `round(r·|sin|)`* — is **measured false**: against 51 whole
> reference pattern planes at radii up to 200 it reproduces **2–4**. Measured
> instead, with `o = ⌊θ/(π/4)⌋` the octant and `u` the fraction into it:
> `M = ⌊r/√2⌋`, `pos = ⌊u·M⌋`, and the boundary step index is `k = pos` in an
> **even** octant, `k = M − pos` in an **odd** one, both ends inclusive — no
> fitted constant, no per-side offset. Scored on whole 6144-byte planes:
> **52/54**, against **2–4/54** for the exact-ray rule above. So **the reference
> is the less accurate machine**: zerobas's rays land within one QTAB step
> (0.012 rad), the reference's are out by 0.037 — which at r=15 is **0.5 px**.
> **Not fixed, and not a constant to tweak**: matching it retires the
> cross-product wedge in `gfx_circ_keep` and stops `gfx_circ_bvec` computing a
> vector at all. Unpriced.
> A **second**, separate 1-px defect is filed with it: at a *near-cardinal*
> boundary the `±1` nudge below rejects the axis point the reference keeps
> (`CIRCLE(128,96),95,15,0,1.5707963` — ref 135 px, zerobas 134). **Placement:** the sine table + boundary math live in the
**sub-ROM tenant** (room for the table; also shrinks the tight resident); the resident
only evaluates each angle → `brad` + sign and marshals it. This drops the
`SUBROM_IDX_SIN`/`COS` dependency from the arc path entirely.

**5.3 Negative-angle radius spokes (measured §11.4).** A **negative** `start` and/or
`end` additionally draws a **radius line** from the centre to that endpoint (the classic
MSX pie-slice). The arc itself uses `|start|`/`|end|`; the sign only toggles the spoke.
Measured: `-1.57,0` = a 270° arc **plus** a spoke to the top point;
`-0.1,-1.57` = an upper wedge **plus two** spokes. **Implementation:** the resident
computes the endpoint pixel(s) `(cx+round(r·cos), cy−round(r·sin))` (major/aspect
applied) and, when the corresponding angle is negative, marshals a **`GFX_OP=3` line**
(centre→endpoint) — reusing the landed G3 op, no new tenant code — before/after the arc
op. (Draw order vs the arc affects only clash on the overlapped endpoint pixel — §9
G4-spoke.)

**5.4 Arc-boundary inclusivity — RESOLVED (2026-07-21).** Pinned with targeted VG-8020
boundary captures ([scratchpad/g4_arc_boundary_capture.py](../scratchpad/g4_arc_boundary_capture.py)):
**both** boundary tests are **inclusive** (`cross(S,P) ≤ 0 ∧ cross(P,E) ≤ 0`), and the
near-cardinal `±1` direction nudge (§5.2.1) is required — the reference distinguishes
`1.57` from `1.58` even though `r·cos` rounds to 0 for both. With the trig-free vectors +
inclusive tests + nudge, the host fit matches every captured arc and boundary re-capture
exactly (0 diffs). Locked by a host unit test (§8).

---

## 6. Work-area contract + marshalling ABI

**Work area (resident writes).** After `CIRCLE`, **`GRPACX/GRPACY` = the centre**
(measured §11.4) — the continuation point. The reference also leaves
**`GXPOS = r`, `GYPOS = cy`** (measured stable across three cases, §11.4) — a reference
internal-loop residue. **§9 G4-work:** match the quirk (`GXPOS=r, GYPOS=cy`) for
byte-faithful work-area, or set `GXPOS/GYPOS = centre` (sensible) — recommendation
below. `CLOC/CMASK` = the last drawn pixel (tenant-written, as G2/G3).

**Tenant ABI (append-only cells after G3's `$E126`).** New op `GFX_OP=4`. The resident
stub evaluates the coordinate/radius/colour/angles/aspect and marshals into own cells
(allocate `$E126+` after a live-map check — the G2/G3 discipline; the region is
LINEBUF, dead during any graphics statement, [g3 spec §8]):

| cell | bytes | meaning |
|---|---|---|
| `GFX_CXC/GFX_CYC` | 2+2 | centre X,Y (int16 LE) |
| `GFX_R` | 2 | radius (int16, ≥0) |
| `GFX_C` | (reuse $E031) | resolved colour 0..15 |
| `GFX_ASPMAJ` | 1 | 0 = x-major (aspect ≤ 1), 1 = y-major (aspect > 1) |
| `GFX_ASPS` | 2 | 8.8 minor scale S (256 = no scale) |
| `GFX_ARCF` | 1 | 0 = full circle, 1 = arc (use S/E vectors) |
| `GFX_SVX/GFX_SVY` | 2+2 | start boundary vector (int, screen offsets) |
| `GFX_EVX/GFX_EVY` | 2+2 | end boundary vector |
| `GFX_ARCBIG` | 1 | sweep > π flag |
| plot scratch | … | octant `x,y,d`; reuse G3 `GFX_CX/CY` for the plotted pixel |

The stub sets these, `push hl` (guard the token cursor — the `ex_play` lesson),
`subrom_call IX = SUBROM_ENTRY_BASE_P0 + 3·SUBROM_IDX_GRAPHICS`, `pop hl`; then, for
negative angles, marshals `GFX_OP=3` spoke line(s) the same way. `GRPAC`/`GXPOS`/`GYPOS`
are written **resident** (the stub holds centre/r).

---

## 7. Token dispatch

`CIRCLE=$BC` → new kwtable row + interp arm → **`ex_circle`** (new resident stub in
[basic/graphics.asm](basic/graphics.asm), repack-only). Exactly the G2 `PSET` shape
([basic/interp.asm:274](basic/interp.asm)): `cp CIRCLE_TOKEN / jp z,ex_circle`. On the
**lean** build the row + dispatch compile out (repack guard), so the lean cart is
byte-identical and `CIRCLE` keeps emitting verbatim as today. Unlike G3's `LINE`, there
is **no runtime disambiguation** — `CIRCLE` is unambiguous.

---

## 8. Gates (Definition of Done, G4)

- **`make graphics-acceptance` extended** — add a `CIRCLE` phase to
  [basic_probe_graphics.py](probes/basic/basic_probe_graphics.py): a **VG-8020
  differential** drawing each case on both machines, reading the **pattern AND colour**
  planes of the covered band, asserting byte-identical. Battery (each a §11 pin):
  - the six circles (r=4/7/8/12/15/20) — exact pixel set + default 1:1 aspect.
  - the five ellipses (aspect 0.25/0.5/2/3) — exact per-point scale + colour plane.
  - arcs: `0,1.57` / `1.57,3.14` / `0,6.28` (full) / wrap `3,1`; **negative-angle
    spokes** `-1.57,0` and `-0.1,-1.57`; plus the 3–4 boundary cases (§5.4).
  - clash colour `CIRCLE(40,40),8,6` → `$61`; `r=0` centre pixel.
  - continuation/STEP `PSET(10,10):CIRCLE STEP(5,5),8` centre `(15,15)`; `GRPAC`=centre.
  - errors: ERR 6 (`(32768,0)`, `r=32768`), ERR 5 (SCREEN 0/1, colour 16, aspect −1),
    clip no-error (`(300,300)`, `(-5,-5)`), and the G4-rneg decision case.
- **Host unit tests** (`make unit-test`) for the pure rasteriser: the §11 captured
  circle/ellipse point-sets as the oracle for `gfx_circle_octants` + the 8.8 minor
  scale + the arc cross-product mask (both from
  [scratchpad/g4_circle_fit.py](../scratchpad/g4_circle_fit.py)). Locks the math
  emulator-free — the crux de-risker, already prototyped.
- **Teeth / anti-green-build:** (a) perturb `d₀`/the decision update → circle cases
  fail; (b) drop the fetch-window settle in the circle read path → the differential
  regresses (the G2 Heisenbug's home, per pixel); (c) force `S` wrong → ellipses fail.
- **G1/G2/G3 gates still green** (`graphics-floor-acceptance`, G2/G3 phases,
  `unit-test`): the new `GFX_OP=4` arm must not regress `GFX_OP=0/1/2/3`.
- **Build wiring:** `sub/graphics.asm` already in `SUB_PARTS` — force-rebuild the
  sub-ROM (selector grows an arm); add the resident `ex_circle` + kwtable row + dispatch
  under the repack guard; **rebuild+reinstall the IPS** before the machine probe
  ([memory: makefile-subparts-stale-tenant], [memory: ips-rebuild-after-basic-change]).
- **Lean build byte-identical** — kwtable row + dispatch + `ex_circle` are repack-only.

---

## 9. Decisions — SIGN-OFF NEEDED

| # | Decision | Recommendation |
|---|---|---|
| **G4-a** | `CIRCLE` = page-0 tenant `GFX_OP=4`, EI between pixels / DI per-pixel RMW; reuse G3 `gfx_plot_cur` | **Yes** — arc D1/D2/D5; inherits G3 discipline |
| **G4-b** | Circle rasteriser = own-design integer midpoint (`d₀=1−r`, `2x+3`/`2(x−y)+5`); host-fit reproduces all 6 captured circles | **Yes** — measured exact (§4.1/§11.3) |
| **G4-c** | Ellipse = **major circle + per-point 8.8 minor scale** (Model A); Model B (two-semi-axis) ruled out | **Yes** — measured exact on 5 ellipses; asm needs no float (§4.2) |
| **G4-asprnd** | Exact-half aspect knife-edges tip on the reference's BCD float; common aspects exact | **Accept residual** — matched-where-achievable; gate uses common aspects (§4.3) |
| **G4-d** | Aspect rule: `≤1` ⇒ x-major/y-scaled, `>1` ⇒ y-major/x-scaled; default = 1:1 pixel-round | **Yes** — measured (§4.2/§11.2) |
| **G4-e** | Arc = CCW `|start|→|end|` (mod 2π, wraps) as an integer cross-product mask; resident computes S/E vectors via math-pack SIN/COS | **Yes** — measured (§5.2/§11.4); no tenant float |
| **G4-f** | Negative start/end ⇒ radius spoke (centre→endpoint) via the landed `GFX_OP=3` line op | **Yes** — measured (§5.3/§11.4); reuses G3, no new tenant code |
| **G4-arcbnd** | Arc-endpoint inclusivity (±1 boundary pixel) pinned during impl with targeted captures + host test | **Yes** — the G3-clip-residual method (§5.4) |
| **G4-spoke** | Spoke draw order vs arc (overlap-pixel clash) | Pin with a capture during impl; default spoke-after-arc |
| **G4-rneg** | Negative radius: the reference **hangs** (unsigned-wrap → gigantic). | ✅ **SIGNED OFF → ERR 5** (Illegal function call), documented deviation ([memory: bug-for-bug-compat-over-accuracy]); a clean-room engine must not infinite-loop. Guard in `ex_circle` after radius eval: `r < 0` → ERR 5. |
| **G4-work** | `GXPOS/GYPOS` after CIRCLE: reference leaves `(r, cy)` residue | ✅ **SIGNED OFF → match the quirk** (`GXPOS=r, GYPOS=cy`); byte-faithful work area, the differential gate asserts it. `GRPAC=centre` (unchanged). |

Implementation order (capture ✅ + fit ✅ done): kwtable row + dispatch + `ex_circle`
grammar walk (coord/r/c/start/end/aspect eval; ERR raises; aspect→major-flag+8.8 S;
angles→SIN/COS boundary vectors; spoke marshalling) → host unit tests for the circle
octants + 8.8 scale + arc mask (fast, emulator-free, from the captured oracle) → tenant
`GFX_OP=4` (midpoint circle + per-point scale + arc cross-product mask, reusing
`gfx_plot_cur`) → 3–4 arc-boundary captures to settle G4-arcbnd/G4-spoke → the
`graphics-acceptance` CIRCLE phase (pattern+colour differential incl. arcs/ellipses/
errors) → verify G1/G2/G3 + `unit-test` green → rebuild+reinstall IPS → commit.

---

## 11. Pinned VG-8020 characterization (black-box, 2026-07-21)

Method as arc §11 (KEYBUF-injection via [omsx_repl.py](probes/lib/omsx_repl.py) on
`Philips_VG_8020`; pattern/colour planes read back mid-`GOTO`-self with `vram_segs`;
behaviour via SCREEN-0-funnelled `ON ERROR`). Scripts (three rounds):
[g4_circle_char1.py](../scratchpad/g4_circle_char1.py),
[g4_circle_char2.py](../scratchpad/g4_circle_char2.py),
[g4_circle_char3.py](../scratchpad/g4_circle_char3.py); fit
[g4_circle_fit.py](../scratchpad/g4_circle_fit.py); point-set oracle
[g4_pointsets.json](../scratchpad/g4_pointsets.json). No ROM disassembly.

**11.1 Tokens / grammar** (stored-line crunch): `CIRCLE`=`$BC`. `CIRCLE(30,30),10` →
`BC 28 0F1E 2C 0F1E 29 2C 0F0A 00`. 6-arg form `…,c,start,end,aspect`: start/end are
floats (`1D …`), aspect is the 6th arg; negative angle = `F2`(minus) + literal
(`…,-1,-2` → `2C F2 12 2C F2 13`); `STEP`=`$DC` on the coord.

**11.2 Default aspect = pixel-round 1:1.** r=20 → width 41 = height 41 = 2r+1; same at
r=4/8/12. (The "round on a CRT" folklore does **not** hold for the pixel set.)

**11.3 Exact pixel sets + fit.** Circles r=4/7/8/12/15/20 (fg15/bg1) — the midpoint
variant (§4.1) reproduces each exactly. Ellipses aspect 0.25/0.5/2/3 (r=15/20):
`aspect≤1` ⇒ x-radius `r`, y compressed; `aspect>1` ⇒ y-radius `r`, x compressed; the
per-point **8.8 scale** reproduces each exactly; the two-semi-axis midpoint ellipse
does not. Clash: `CIRCLE(40,40),8,6` → colour bytes `01`/`61` (fg 6 | bg 1).

**11.4 Arcs + work area.** Angle 0 = +x, +CCW. `0,1.57` upper-right; `1.57,3.14`
upper-left; `0,3.14` top half; `0,6.28` = full circle (n = full-circle n). `end<start`
wraps through 0 (`3,1`). Negative endpoint ⇒ radius spoke (`-1.57,0` = 270° arc + top
spoke; `-0.1,-1.57` = wedge + 2 spokes). Work area: `GRPAC` = centre; `GXPOS=r`,
`GYPOS=cy` (residue, stable over 3 cases).

**11.5 Errors / clip.** `r=0` → centre pixel, no error. Off-screen/neg centre
(`(300,300)`, `(-5,-5)`) → clip, no error. `>int16` centre or radius (`(32768,0)`,
`r=32768`) → ERR 6. SCREEN 0/1 → ERR 5. colour 16 → ERR 5. aspect −1 → ERR 5.
**Negative radius (`-1`,`-5`) → hang** (unsigned-wrap; §9 G4-rneg).

---

## Appendix — sources

Inherited from the arc spec §0/§Appendix and G1–G3: TMS9918A datasheet (GRAPHIC-2
planes, VDP ports), MSX2 TH (work-area `GRPAC*`/`GXPOS`/`CLOC`/`CMASK`/`SCRMOD`),
public MSX-BASIC language reference (`CIRCLE` semantics: radius, colour, start/end
radians, aspect, negative-angle spokes), the math pack `SIN`/`COS`
([memory: mathpack-slice2-transcendentals]), and the G4 capture pass. **Own-design:**
the grammar walk, the integer midpoint circle (host-fit, not lifted), the per-point 8.8
ellipse scale, the integer cross-product arc mask, the spoke orchestration. No
reference-ROM disassembly ([memory: no-reference-rom-disasm]).
