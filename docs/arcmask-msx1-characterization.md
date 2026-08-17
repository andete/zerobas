# The arc mask at large radii — the reference is the less accurate one

D-ARCMASK, 2026-08-17. Picks up the D-CIRCOVF residual *"THE ARC MASK DIVERGES
AT LARGE RADII, AND IT IS NOT THE PRODUCT BOUND"*
([`TODO.md`](../TODO.md), [`docs/circovf-msx1-oracle.md`](circovf-msx1-oracle.md) §6.1).

Baseline: `d404240`, `sub.rom` `bc7573df`, tree green.

**This slice ships a measurement and a retraction, not a fix.** The rule the arc
boundary rests on is now measured FALSE, the reference's real rule is
characterised to within a step, and a forward model of it scores 22/51 whole
planes — right in kind, not right enough to ship. Shipping it would redden 29
rows that are green today.

---

## §1 What the residual asked, and the one move that answered it

The residual listed three red rows and three unwalked candidates (the QTAB
lookup, the `brad` marshalling, the deferred spokes). None of them is the cause.

The move that worked was not walking any of them. It was building an **offline
model of zerobas's own arc mask** — `cpt_boundary_prep`'s `brad` and three
quadrant compares, QTAB + fold + `gfx_circ_bvec_mag` + the `±1` nudge,
`gfx_circ_arcbig_calc`, `gfx_circ_keep`'s two cross products, and the deferred
spokes — and calibrating it against every arc reading the tree holds
([`scratchpad/arcmask_model.py`](../scratchpad/arcmask_model.py)):

    zerobas offline model: 56 / 56 whole 6144-byte planes exact

That is 3 readings from §6.1 plus 53 measured this slice, at sha1 over the whole
pattern plane. With it, every later question is answered without booting
anything, and — the part that mattered — **the reference's plane can be inverted
instead of guessed at.**

⚠️ It was falsified before it was used: delete the mask and all three §6.1 rows
move; delete the spoke and `arc_big_r400` goes to 0 px; delete the nudge and
`arc_r700_a137` moves; flip ARCBIG and two of three move. No row is vacuous.

---

## §2 The reference's kept set is a WEDGE — inverted from its own plane, uniquely

The mask keeps `P` iff the direction of `P` lies in a closed angular window, so
the kept set of *any* wedge mask is a contiguous run of the figure's points in
angle order. [`arcmask_invert.py`](../scratchpad/arcmask_invert.py) enumerates
every contiguous run and keeps the ones whose whole plane hashes to the
reference's:

    arcctl_r200    170/170 px, sha1 386f8fb8   ONE run matches, uniquely
    arc_r700_a137  127/127 px, sha1 ebfd085b   ONE run matches, uniquely

So the mask *shape* is not the problem, and sharpening `S`/`E` can in principle
reach the reference. That is what made the next step worth taking. Had no run
matched, the finding would have been the opposite one.

---

## §3 🔴 The premise the arc boundary rests on is measured FALSE

[`spec-basic-graphics-g4.md`](spec-basic-graphics-g4.md) §5.2.1 and
[`sub/graphics.asm`](../sub/graphics.asm) both state the boundary vector as
`Sx = sign_c·round(r·|cos|)`, `Sy = −sign_s·round(r·|sin|)` — the *exact* ray —
and both cite **"host-fit reproduces every captured arc + boundary re-capture
EXACTLY"** as the evidence.

The fit is real and the citation is accurate. **Its corpus cannot see the
question.** [`g4_pointsets.json`](../scratchpad/g4_pointsets.json) holds radii
**4, 7, 8, 12, 15, 20**, and every ARC row in it is **r=15**. The divergence
below is **0.032 rad**, which at r=15 is **0.5 px** — under one pixel, on every
row the fit was ever scored against.

⚠️ **AN "ALL MATCH" IS A STATEMENT ABOUT A CORPUS, NOT ABOUT A RULE.** This is
the same shape D-CIRCDOM filed one arc earlier ("the gate's largest drawn radius
was 20"), and it survived a second slice because the citation was re-read and the
corpus was not.

---

## §4 What the reference actually does

53 rows measured on both machines across two runs
([`arcmask_sweep.py`](../scratchpad/arcmask_sweep.py),
[`arcmask_fine.py`](../scratchpad/arcmask_fine.py); planes dumped to JSON, so
every number below is re-derivable offline). Rig, both runs:

    dead subject (no CIRCLE at all)     1 px, both machines, identical
    ctl_full_r95 / ctl_full_r190        byte-identical
    ctl_arc_r15 (the gate's own row)    byte-identical
    zerobas predicted, whole plane      53 / 53 exact
    lad_r200 vs the §6.1 reading        170 px 386f8fb8 — replicated

### 4.1 It is angular, it is periodic in π/2, and it is a quantiser

Reading the boundary ray off each row as a bracket
([`arcmask_rays.py`](../scratchpad/arcmask_rays.py)), the reference's error is a
function of `θ mod π/2` alone — the same error recurs at the matching offset in
all four quadrants and at the same angle in different rows — and it **jumps**.
zerobas's rays land within one QTAB step (0.012 rad) of the true angle. The
reference's are off by up to **0.037 rad**, growing linearly in pixels with r:

| r | 24 | 48 | 95 | 190 | 200 |
|---|---|---|---|---|---|
| reference's boundary, steps off the true one | 1 | 2 | 2–3 | 4–5 | 5–6 |

### 4.2 🎯 The reference distributes the octant's steps LINEARLY over its angle

Fold the boundary angle to the nearest axis; let `f` be the distance to it,
`f ∈ [0, π/4]`. Read the reference's boundary as the octant loop's **step index**
`k = min(|dx|,|dy|)` of its extreme kept point. Then, over 44 samples at r=190
(brackets 0.0026 rad):

    k advances by a CONSTANT 6 steps per 0.035 rad of f, right across the
    octant, on the start side and the end side alike.

`k` is **linear in `f`**. The correct value, `r·sin f`, is not. The slope is
`r·(2√2/π)` — the linear map that is *exact at `f=0` and at `f=π/4`*, where
`r·sin(π/4) = 0.7071r` is the octant's own step count, and wrong in between.

**So the reference interpolates the angle across the octant, and zerobas
computes it. zerobas is the more accurate machine, and under a faithful-MSX1
charter that is precisely the defect.**

### 4.3 🔴 The CARDINAL control came back red, and it is a second defect

`ctl_card_r95` — `CIRCLE(128,96),95,15,0,1.5707963` — was written to be green:
at a cardinal boundary QTAB is exact and any shrink about π/2 is zero by
construction. It read **ref 135 px / zerobas 134**.

At `θ=1.5707963` the cosine magnitude rounds to 0, and because `θ ≠ HALF_PI` to
14 digits the quadrant sign is `+1`, so `gfx_circ_bvec_nudge` forces `Ex=+1`.
That rejects the top point `(0,−95)`; the reference keeps it. This is a **1-px,
r-independent** defect at near-cardinal angles, separate from §4.2 and *not*
explained by it — the `±1` nudge is pinned by G4-arcbnd at r=15, where it is
correct.

---

## §5 Why no fix ships

A forward model of §4.2, scored on all 51 measured reference arc planes
([`arcmask_refmodel.py`](../scratchpad/arcmask_refmodel.py)):

| model of the reference's boundary | whole planes exact |
|---|---|
| exact rays — what §5.2.1 asserts | 2–4 / 51 |
| step index linear in the in-octant angle (§4.2) | **22 / 51** |

The linear rule is right in kind — an order of magnitude better than the rule in
the source — and it is **not right enough to code**. The residual misses are ±1
px and they do not close under a single constant: solving the boundary interval
for `c` in `k = c·r·f` gives feasible ranges that conflict across radii
(r=24 needs `c < 0.888`, r≥95 needs `c > 0.895`), and the same is true for
`c·N·f/(π/4)` against the octant's own step count `N`. Something r-dependent
remains unmodelled.

💰 **A fix at 22/51 would redden 29 rows that are byte-identical today.** The
measurement is the deliverable; the retraction of §3 is the change.

---

## §6 Aside, measured on request: what CIRCLE costs

`TIME` is the VDP interrupt counter; both machines are EU/50 Hz, so the units
compare directly. Every row runs N iterations inside a `FOR` loop with the
**empty loop measured on the same machine at the same N and subtracted** —
BASIC's own `FOR`/`NEXT` costs different ticks on two different ROMs.
[`arcmask_time.py`](../scratchpad/arcmask_time.py) /
[`arcmask_time2.py`](../scratchpad/arcmask_time2.py), per single call:

| row | reference | zerobas | zb/ref |
|---|---|---|---|
| `r=0` (fixed per-call cost) | 10 ms | 13 ms | 1.30× |
| `r=20` | 105 ms | 71 ms | 0.68× |
| `r=48` | 234 ms | 152 ms | 0.65× |
| `r=95` | 445 / 448 ms | 289 / 292 ms | 0.65× |
| `r=95`, aspect .5 | 483 ms | 402 ms | 0.83× |
| `r=200`, centre off screen | 596 ms | 336 ms | 0.56× |
| **`r=95` ARC** | **224 ms** | **1272 ms** | **5.68×** |
| **`r=95` ARC + aspect** | **264 ms** | **1384 ms** | **5.24×** |
| **`r=200` ARC, off screen** | **436 ms** | **2600 ms** | **5.96×** |

zerobas draws full circles and ellipses **faster** than the reference. It draws
**arcs 5–6× slower** — and an arc is *cheaper* than its full circle on the
reference (224 ms vs 448) while costing *4.4× more* on zerobas (1272 vs 292).
The mask dominates: `gfx_circ_keep` runs two `gfx_cross_ge0` per emitted point,
and D-CIRCOVF widened each to two 16×16→32 multiplies plus a 32-bit compare —
eight times per octant step, plotted or not.

⚠️ **ROUND 1 REPORTED THREE `None`s AND THEY WERE A RIG FAILURE, NOT A READING.**
At N=20 the arc rows simply did not finish inside the capture window. They are
reported here from round 2 (N=5, step 45 s), whose `r95` row reproduces round 1
to within one frame — which is what makes the round-2 numbers usable at all.

---

## §7 Cost

No source logic changed. The edits are the §3 retraction, in the two places that
assert the false rule. Walls and ROM identity unchanged:
low **5 B**, main p1 **67 B**, sub p0 **3539 B**, sub p1 **1483 B**;
`basic-reloc 8e5391b3`, `sub bc7573df`, `disk 2c630d3d`, `zerobas-main-eu 01ab88f1`.

## §8 Apparatus, all re-runnable without an emulator

| file | what it does |
|---|---|
| [`arcmask_model.py`](../scratchpad/arcmask_model.py) | zerobas's arc mask offline; 56/56 whole planes |
| [`arcmask_invert.py`](../scratchpad/arcmask_invert.py) | inverts a reference plane into a wedge |
| [`arcmask_rays.py`](../scratchpad/arcmask_rays.py) | brackets both boundary rays of every measured row |
| [`arcmask_refmodel.py`](../scratchpad/arcmask_refmodel.py) | forward model of the reference, scored on 51 planes |
| [`arcmask_sweep.json`](../scratchpad/arcmask_sweep.json) / [`arcmask_fine.json`](../scratchpad/arcmask_fine.json) | 53 rows × 2 machines, whole planes, verbatim |
