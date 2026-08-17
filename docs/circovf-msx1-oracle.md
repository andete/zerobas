# The CIRCLE product overflow — finding an oracle before writing a fix

D-CIRCOVF, 2026-08-16. Closes the D-CIRCDOM residual *"THE PRODUCT BOUND IS REAL
AND REACHABLE: `CIRCLE` WITH r ≥ 256 DRAWS PIXELS THE REFERENCE DOES NOT"*
([`TODO.md`](../TODO.md), [`docs/circdom-msx1-characterization.md`](circdom-msx1-characterization.md) §4.1).

Baseline: `b602eac`, `sub.rom` `8161c1a2`, `graphics-acceptance` **300** PASS / 0 FAIL.

📏 **That 300 is measured, and the figure carried forward was 301.** The slice
adds ten rows and the gate reported 310, which against a baseline of 301 is one
short. Rather than round it off, the pre-slice probe was checked out and re-run:
it prints **300** `PASS`/`FAIL` lines. 300 + 10 = 310. The 301 was an estimate
that had been copied into a result column — the same failure mode this project
has filed before, found here by an arithmetic check that took one gate run.

---

## §1 The residual said the fix had no oracle. It was right, and that was the slice

D-CIRCDOM measured six DIFF rows and every one of them has the **reference
drawing 0 px on screen**. They establish that zerobas is wrong. They cannot
establish what right looks like — they say only *"zerobas paints where the
reference paints nothing"*. A fix written against that is written against an
absence, and would have been graded by rows that go green when zerobas draws
**nothing at all**.

So the first deliverable was a measurement, not a patch.

### 1.1 Why no previous row could have carried it

Overflow needs `|v|*ASPS >= 65536`, i.e. a **scaled minor offset ≥ 256**. The
screen is **192 pixels tall**. So *no overflowing point can ever be on screen
while the centre is on screen* — and every CIRCLE row in the tree's history,
D-CIRCDOM's included, is centred at (128,96).

That is also the retrospective explanation of D-CIRCDOM's `r1000` miss (predicted
DIFF, measured blank on both). It was scored there as a modelling failure reached
by analogy. It is that, but the underlying geometry is a *theorem*: at `ASPS=256`
the wrap is exactly `v mod 256`, and wherever that lands, the unscaled major-axis
offset is off screen.

**The one move that unblocks it: put the centre off screen along the MINOR axis.**
Then the overflowing part of the figure lands on the visible band.

---

## §2 The instrument, calibrated before it was trusted

[`scratchpad/circovf_calib.py`](../scratchpad/circovf_calib.py) models the
tenant's own octant loop (`gfx_circ_init` / `gfx_circ_next` / `gco_emit8`) and
both scale arithmetics, and rebuilds the **whole 6144-byte pattern plane**, not a
summary — D-CIRCDOM's K-CD3 missed precisely because a prediction was computed
off the bounding box while the row compares every byte.

It was run against every reading D-CIRCDOM §4.1 published, before it was used
for anything:

    11 rows x 2 machines = 22 readings
    22 exact / 0 missed          -- model CALIBRATED

Including **the two readings D-CIRCDOM's own hand-written predictions missed**:
`r257` (predicted ≈66 px, measured 88 — the model says 88) and `r1000` (predicted
DIFF, measured blank — the model says blank). A model that reproduces the misses
as well as the hits is worth more than one fitted to the hits.

⚠️ The calibration is **one-sided in the regime that matters**. Every reference
reading it reproduces is either blank or a row whose product fits. Nothing in
D-CIRCDOM constrains what the reference does when the product overflows *and the
figure is visible* — which is the whole question. §3 is that measurement.

---

## §3 The positive oracle: four hypotheses, one survivor

[`scratchpad/circovf_char.py`](../scratchpad/circovf_char.py). Rows derived by
[`circovf_search.py`](../scratchpad/circovf_search.py), never hand-typed.
Predictions written and printed **before any boot**, as whole-plane
(popcount, bbox, sha1), for four hypotheses:

| | scale model |
|---|---|
| `H_EXACT` | `(\|v\|*ASPS + 128) >> 8`, full-width product |
| `H_SAT` | product saturates at 65535 |
| `H_WRAP` | `(((\|v\|*ASPS & 0xFFFF) + 128) >> 8) & 0xFF` — zerobas before this slice |
| `H_BLANK` | the reference refuses / draws nothing |

Every row was checked for **discriminating power** before it ran; two rows
separate all four hypotheses, and no row is vacuous.

| row | statement | VG-8020 | zerobas (pre-fix) |
|---|---|---|---|
| `ovf_r284_top` | `CIRCLE(128,445),284` | 256 px `05f66505` = **H_EXACT** | 9 px `430587a2` = H_WRAP |
| `ovf_r300_top` | `CIRCLE(128,445),300` | 256 px `328ae002` = **H_EXACT** | 0 px = H_WRAP |
| `ovf_a05_r528` | `CIRCLE(128,448),528,,,,.5` | 253 px `2f2dda11` = **H_EXACT** | 0 px = H_WRAP |
| `ovf_a2_r528` | `CIRCLE(262,96),528,,,,2` | 71 px `345fa7bd` = **H_EXACT** | 121 px `c05010e4` = H_WRAP |
| `ctl_r255_top` | `CIRCLE(128,445),255` | 55 px `72c98b29` | **identical** |
| `ctl_r200_top` | `CIRCLE(128,352),200` | 239 px `22c9a8d8` | **identical** |
| `ctl_a05_r500` | `CIRCLE(128,346),500,,,,.5` | 256 px `722d4c19` | **identical** |
| `ctl_a2_r500` | `CIRCLE(260,96),500,,,,2` | 192 px `19ec7ee1` | **identical** |

**8 of 8 whole-plane predictions exact.** `H_SAT` and `H_BLANK` are both refuted
at the sha1 level. The answer to *"does the reference use a wider product, or
clamp, or wrap differently?"* — a question the residual raised and nobody had
asked — is: **it computes the product at full width and rounds half-up.**

Three independent code paths carry it: the default aspect (`ASPS=256`), the
`cpt_asp_le1` branch (aspect<1, x-major), and the `fp_div` branch (aspect>1,
y-major). `ovf_a2_r528` is the one where **zerobas painted MORE than the
reference**, not less — the opposite direction to all six of D-CIRCDOM's rows.

---

## §4 🔴 The rig failed one-sidedly, and only the controls could see it

Round 1 of §3 returned **8/8 DIFF**, with the reference reading ~5115 px and bbox
`(0,0,255,127)` on *every row* — including all four controls.

The cause: `run_cases`'s first tuple element is the **delivery mode**, and the
row *label* had been passed there. Anything that is not `"stored"` is DIRECT
mode, so each line was typed at the prompt and `prog()`'s trailing `GOTO` became
`Undefined line number`. On the VG-8020 an error at the prompt drops SCREEN 2
back to text, and the font overwrites the pattern plane — 5115 px of *font*.

Three things make this worth writing down:

* **It is one-sided.** zerobas is insensitive to it and read correctly
  throughout, matching the offline model on all 8 rows. A rig fault that breaks
  only one machine is indistinguishable from a finding, and it arrives wearing a
  finding's clothes: "every overflow row diverges".
* **Only the controls could catch it.** Four rows written to be byte-identical
  came back divergent. Without them the run reads as a spectacular confirmation.
* **The known-answer row is what located it.**
  [`circovf_rigcheck.py`](../scratchpad/circovf_rigcheck.py) re-asked
  D-CIRCDOM's `CIRCLE(128,96),700,,,,.137` (421 px, `2f6257f6`) under four
  driving parameters. The reference failed **all four, including D-CIRCDOM's
  own** — which ruled out my `step=25.0` immediately and pointed at delivery.
  [`circovf_refdiag.py`](../scratchpad/circovf_refdiag.py) then asked what a
  **dead subject** scores: a program with no `CIRCLE` at all read 5007 px.

📏 **A blank subject that scores 5007 is the cheapest possible diagnosis, and it
took three tool calls.** Ask it first, not fourth.

---

## §5 The fix, and the coupling that actually bound

Three sites, one new primitive.

| site | before | after |
|---|---|---|
| `gfx_circ_scale` | `gfx_mul16u` + `ld l,h / ld h,0` | `ASPS=256` identity arm, else `gfx_mul16r` |
| `gfx_circ_bvec_mag` | same shape, wraps for r ≥ 258 | tail-call `gfx_mul16r` |
| `gfx_cross_ge0` | two 16-bit products, 16-bit compare | `gfx_mul16u32` + `gfx_cmp32`, 32-bit |
| `gfx_mul16u` | — | **deleted**, unreferenced |

`gfx_mul16r` computes `(DE*A + 128) >> 8` in a 24-bit accumulator.
`gfx_mul16u32` is the full 32-bit product; `gfx_cmp32` a borrow-propagating
4-byte compare. All three were simulated instruction-for-instruction over
**600 000 cases** before a single build
([`circovf_asmsim.py`](../scratchpad/circovf_asmsim.py)) — which is how the first
draft of `gfx_mul16u32` was caught: it used a shift direction that never brings
the product into the low word, and it was wrong on 200 037 of 200 049 cases.

### 5.1 🔴 The predicted coupling does not bind

D-CIRCDOM recorded, in `TODO.md`, in
[`circdom-msx1-characterization.md`](circdom-msx1-characterization.md) §6, in
[`fixpoint8000-msx1-sweep.md`](fixpoint8000-msx1-sweep.md) §4.2 and in two source
headers:

> **WHOEVER FIXES THIS MUST ADD THE `$8000` ARM AT `gfx_circ_scale`'s RE-NEGATE
> IN THE SAME SLICE**: an exact `(32767*256+128)>>8` is `32768` = `$8000`.

The arithmetic is right and the conclusion is **design-dependent**. `ASPS` is
`0..256`, and `ASPS=256` is the *only* value that can reach 32768 — it is also
the value for which the scale is the **identity**, so it costs 4 bytes to branch
around the multiply entirely. On that arm the result is `|v| ≤ 32767`; on the
multiply arm `ASPS ≤ 255` gives at most `(32767*255+128)>>8 = 32639`.

    max over ASPS 0..255 at |v|=32767 : 32639 ($7F7F)
    the ASPS=256 identity arm         : 32767 ($7FFF)
    -> $8000 NOT reached              (600k-case sweep, circovf_asmsim.py)

**No `$8000` arm was needed.** The cheaper design dissolved the coupling.

### 5.2 🔴 An unpredicted coupling does bind, in the opposite direction

`gfx_cross_ge0`'s two products **were not broken before this slice** — and are
broken *by* it if left alone. Their inputs were byte-bounded by exactly the
`ld l,h / ld h,0` truncation being removed, so `|v| ≤ 255` and no product could
exceed 65025. With the scale computed exactly, components reach 32767 and the
products reach 2³⁰.

So the arc mask had to be widened **in the same slice, because fixing the scale
would have broken it** — the same structural claim the residual made, at a site
it did not name, in the direction it did not expect. §6 measures that instead of
asserting it.

⚠️ The 32-bit magnitudes need 8 contiguous bytes and the G3/G4/G5 sysvar window
has 6 left. They **alias the PAINT span stack** (`GFX_PSTK`) on the same
one-tenant-at-a-time argument DRAW's frame buffer already uses. CIRCLE's parse
co-routine borrows `GFX_DPTR` from the same window — 256 bytes clear of these 8,
and `basic/graphics.asm` reads `GFX_DPTR` again *after* the draw, so the two must
not and do not overlap.

---

## §6 After the fix

`scratchpad/circovf_char.py`, re-run against `sub.rom` `bc7573df`:

    divergences: 0 / 8

All four overflow rows are **byte-identical to the reference at sha1 level** on
all three code paths, and all four controls held. The planes match the
predictions written before the fix existed.

---

### 6.1 🔴 The arc rows found a *second* defect, and a green control is what scoped it

The arc rows written to exercise the widened cross product came back mostly
red — and four of the first eight were **both blank**, which is not agreement
(D-CIRCDOM §4.2: `r200`/`r255` agreed for exactly that wrong reason). Replaced
with rows that actually draw, the picture is:

| row | VG-8020 | zerobas |
|---|---|---|
| `arcctl_r200` `CIRCLE(128,352),200,15,1.1,2.04` | 170 px `386f8fb8` | 181 px `7956e005` |
| `arc_r700_a137` `CIRCLE(128,96),700,15,0,1.57,.137` | 127 px `ebfd085b` | 126 px `752131e6` |
| `arc_big_r400` `CIRCLE(128,96),400,15,-1.57,0` | 97 px `cd7e5368` | 97 px `76352feb` |

**`arcctl_r200` was written as a GREEN CONTROL.** At r=200 every cross product
is 40000 — inside 16 bits on *both* arithmetics — and `ASPS=256` makes the scale
the identity on both, so nothing in this slice can reach it. It came back red.

That is the row that scopes the finding: the divergence is **angular, not
arithmetic**, and it is pre-existing. [`circovf_prefix.py`](../scratchpad/circovf_prefix.py)
reverts the slice's source edits, rebuilds the pre-slice `sub.rom` **`8161c1a2`
byte for byte**, and re-asks every row:

    arcctl_r200    pre 7956e005   post 7956e005   -> byte-identical, red on both
    arc_r700_a137  pre DIFF       post DIFF       -> PRE-EXISTING
    arc_big_r400   pre DIFF       post DIFF       -> PRE-EXISTING
    arc_r260_ovf   pre DIFF       post agree      -> FIXED by this slice
    arc_wrap_r300  pre DIFF       post agree      -> FIXED by this slice

So the slice **fixed two arc rows** (zerobas painted 47 px and 447 px of wrapped
arc where the reference draws nothing) and **introduced none**. The remaining
three are filed in `TODO.md`, not folded in.

⚠️ **The consequence for §5.2 is uncomfortable and is stated rather than
buried: the 32-bit widening has no green row that can see it.** Every row that
would exercise it is red for the reason above. It is forced by arithmetic —
without it the products wrap — and untested by the gate. K-CO3 exists to give
that gap a number instead of a sentence: it undoes the widening and is declared
`kind="nothing"`, predicted to redden nothing, with the missing row as the
finding.

---

## §7 Cost

| wall | before | after | delta |
|---|---|---|---|
| page-0 low region | 5 B | 5 B | 0 |
| main page 1 | 67 B | 67 B | 0 |
| **sub page 0** | **3604 B** | **3539 B** | **−65 B** |
| sub page 1 | 1483 B | 1483 B | 0 |

⚠️ **The residual priced this against sub page 1 (1483 B free). It lands in sub
page 0.** `graphics_tenant` is a **page-0** tenant — it is in the page-0 closure
list `subrom-closure-check` prints on every build. The budget was never wrong by
enough to matter (3604 B available against 65 B spent), but the wall that was
quoted is not the wall that moved.

ROM identity: `sub.rom` `8161c1a2` → `bc7573df`. `basic-reloc.rom` `8e5391b3`,
`disk.rom` `2c630d3d`, `zerobas-main-eu.rom` `01ab88f1` — **all three byte-identical**,
as predicted for a sub-tenant edit.

---

## §8 Knives

[`scratchpad/circovf_knives.py`](../scratchpad/circovf_knives.py) — the
D-CIRCDOM runner with both of its filed defects fixed (rows keyed on
`(phase, index, label)` **with the key count asserted against the probe's own
PASS/FAIL line count**, and a `kind` field carrying the scorer state). Every
prediction set is derived from the probe's own `CIRCLE_CASES` at run time, from
each row's `ops` string — nothing hand-typed, which is what cost D-CIRCDOM's
K-CD2 a miss with no modelling content in it.

Baseline: `sub.rom` `bc7573df`, **310 rows, footer `PASS`, no fails**.
Gates re-run this slice, all rc=0: `graphics-acceptance` **310 PASS / 0 FAIL**,
`graphics-floor-acceptance` PASS, `unit-test` 59, `rowshape-check` 26,
`injector-check` 372, `preflight-check` 95 guarded / 0 unguarded,
`latch-check` 16/16, `deadcode` 0/0 (+1 allowlisted), `audit-citations` clean.
⚠️ `make graphics` is **not a target** — it answers `No rule to make target`,
and piping it through `tail` hides that behind rc 0. The target is
`graphics-acceptance`.

| knife | cut | predicted | measured | |
|---|---|---|---|---|
| K-CO1 | `ld h,c` → `ld h,b` in `gfx_mul16r` (B=0 after `djnz`) — reinstates the byte narrowing | 2 | 2 | **EXACT** |
| K-CO2 | `or a` → `xor a` — kills the `ASPS=256` identity arm | 19 | 19 | **EXACT** |
| K-CO3 | `ld b,4` → `ld b,2` in `gfx_cmp32` — undoes the 32-bit widening | **nothing** | nothing | **as predicted — §6.1** |
| K-CO4 | `gfx_circ_bvec_mag` tail → `gfx_mul16u32` — boundary vectors ~256× too long | 5 | 6 | **MISS** |
| K-CO5 | band clamp `min(23,…)` → `min(5,…)` | abort, no footer | abort, `AssertionError` | **EXACT** |

Each cut is a **byte-neutral opcode swap**, so a knifed build differs from the
shipped one only in the bytes under test; each produced a distinct `sub.rom`
hash, and the restore rebuilt `bc7573df` exactly.

🔴 **K-CO4 MISSED, and the miss is the useful part.** It over-excluded
`arc_full628` on the model *"a full sweep keeps every point regardless of which
way the boundary vectors point"*. That model is wrong for a reason visible in
the row itself: the statement is `0,6.28`, and 6.28 is **not** 2π — the sliver
between 6.28 and 6.2832 is excluded, so the sweep is not full and its boundary
vectors do matter. A row named `arc_full628` is named for what it was *meant* to
be, and the exclusion was reasoned from the name rather than from the number.

K-CO2 is the knife that matters for §5.1: it proves the `ASPS=256` identity arm
is **load-bearing for correctness, not just for size**. Deleting it reinstates
the `$8000` fixed point the residual warned about — the arm is the reason the
warning does not apply.
