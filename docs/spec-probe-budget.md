<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# ACTUAL-vs-BUDGET — instrumenting the probe harness's emulated-time budgets

**Date:** 2026-08-24. **Files:**
[`probes/lib/omsx_repl.py`](../probes/lib/omsx_repl.py) (`settle_n` / `settle_out`,
inert when off), [`scratchpad/budget_probe.py`](../scratchpad/budget_probe.py)
(the driver). **Parent item:** [`TODO.md`](../TODO.md) *"the real gate-suite lever
is the emulated-time budgets"*, filed out of
[`spec-probe-savestate.md`](spec-probe-savestate.md) §4b — which found the
per-case COLD BOOT is **not** the suite's dominant cost, and that `step` /
`cap_gap` / `PAINT_STEP` are.

The item says to **instrument first, and cut only what the data licenses**. This
is the instrument and its first readings. **No budget is changed here.**

## 1. What a "budget" is, exactly

`_tcl` schedules each injected line one `step` apart and the capture one `step`
after the last line, so:

* **the window a case's budget buys between `RUN` and its capture is exactly
  `step`** — not `step + cap_gap`;
* **`cap_gap` is the gap AFTER the capture** (inter-case spacing) and buys the
  case that owns it nothing.

🔴 **AND THAT SECOND BULLET IS NOW PINNED BY A ROW, BECAUSE PROSE DID NOT HOLD
IT** ([`tests/test_capture_budget.py`](../tests/test_capture_budget.py), 8 rows +
a knife, emulator-free). It was stated here in bold and repeated in `_tcl`'s own
comment, and **D-TWOFILE still spent five wrong diagnoses on it** — a hang, a
silent abort, a dead screen, a slow `OPEN` — because a probe passed
`cap_gap=70.0` to buy a 4.4-second program some room and actually bought it the
3.0 seconds its `step` was worth. The capture landed between two `PRINT`s and a
half-drawn screen read as a defect. **Both places that carried the fact are
places a CALLER never looks**, so it is now also on `_run_cases_impl`'s
docstring, and [`scratchpad/gapscan.py`](../scratchpad/gapscan.py) ranks the
sites that tuned the wrong knob. ⚠️ Its hits are an **advisory**: a wide
`cap_gap` is legitimate as inter-case spacing, and only `settle_n` below can
say whether a case was still drawing when its capture fired.

🔴 **`step` therefore does DOUBLE DUTY, and that is the constraint that shapes any
cut.** It is simultaneously (a) the inter-line injection spacing that guarantees
the previous chunk has been consumed — *"measured drained before 1794/1794
injections"*, the property the whole D-LATCH/D-DELIVER delivery-race apparatus
rests on — and (b) the RUN→capture completion budget. **Lowering `step` to reclaim
(b) tightens (a)**, i.e. pays for wall time with the one race this harness has
been bitten by repeatedly. A cut wants a *separate knob*, not a smaller `step`.

## 2. The instrument

`_run_batch(..., settle_n=N, settle_out=d)` schedules `N` **log-spaced** samples
across `(RUN, capture]`, each emitting the emulated instant and **the capture
region itself**. The host finds the last sample at which the region still
changed: everything after it is margin.

🔴 **LOG-SPACED, NOT EVEN — the first cut was a resolution artefact.** An even
grid over a 90 s window first samples at 2.25 s, but these operations finish far
inside that, so every sample came back identical and the readout printed *"used
2.25 s / 2.5 %"* for a circle draw **and** for a text error — the grid's own
spacing, reported as a measurement. Log spacing puts the first sample at
`window/1000` and keeps ~3 decades of resolution where fast cases settle.

🔴 **AND NO OBSERVED CHANGE IS A BOUND, NOT A VALUE.** When every sample agrees,
all that is known is `used < first-sample offset`; the driver prints `<x`, never
`x`.

### 2.1 Two controls, because an instrument is part of the measurement

* **It must not move what it measures.** openMSX `after time` callbacks are
  atomic w.r.t. the emulated CPU and cost zero emulated time — *asserted*:
  `budget_probe.py --inert` compares each case's capture with sampling on and
  off (**identical**), and the generated Tcl with `settle_n=0` is **byte-identical
  to the committed pre-instrument version** across every capture shape and hold
  combination.
* 🔴 **THE SAMPLED REGION MUST BE THE REGION THE WORK WRITES.** The first sweep
  watched only the SCREEN-2 **pattern** table and reported the PAINT flood
  settling in **0.254 s on both references** — because they fill by writing the
  **colour** table alone. Measured, holding the screen: reference pattern all
  `0x00` / colour all `0x0F`; zerobas pattern all `0xFF` / colour all `0xF4` —
  the *same visible screen* (`POINT` reads 15 on all three, `PAINT` completes
  with `ERR 0` on all three), different bytes. That is the filed *"the two
  engines write DIFFERENT BYTES"* fact ([[ntwall-scout-slice]]) arriving as an
  instrument fault: **a sampler pointed at a region a machine never touches
  reports "settled immediately" for every machine that does the work elsewhere**,
  and a budget cut made on that reading would be cut on nothing. Sampling both
  tables moved the references from 0.254 s to **16.0 s**.

## 3. First readings (2026-08-24, ROMs `41b8c4ed`/`1922eaa0`/`7d27b871`)

`used` = to the last change in the capture region; `margin` = the rest;
resolution `window/40`, log-spaced.

| case | window | vg8020 | cf3300 | zerobas | worst used |
|---|---|---|---|---|---|
| `paint.flood` — whole-screen fill | 90.00 | 16.005 | 16.005 | **53.610** | **59.6 %** |
| `paint.circle` — bounded fill | 90.00 | 4.778 | 4.778 | 11.330 | 12.6 % |
| `circle` — draw, no fill | 90.00 | 0.715 | 0.715 | 0.426 | 0.8 % |
| `text.err` — error + PRINT readout | 2.50 | 0.094 | 0.094 | 0.024 | 3.8 % |

## 4. What the data licenses — and what it forbids

🟢 **`PAINT_STEP = 90.0` IS EARNED, NOT PADDING.** Its worst case needs **53.6
emulated seconds on zerobas** — a margin of only **1.68×**. The comment calling it
*"generous"* is wrong about the number: it is the tightest budget in the table.
**Do not cut it.** (A cut to 45 s would fire the capture MID-FILL on the subject —
which reads as a hang or a wrong partial result, i.e. as semantics.)

🎯 **THE WASTE IS NOT THE BUDGET, IT IS ITS SCOPE.** `PAINT_STEP` is applied to a
whole phase, while only the flood needs it: `paint.circle` uses 12.6 % of it and a
plain `circle` **0.8 %**. Per-case budgets — or an adaptive capture that fires
when the region settles — is where the wall time is, and neither requires making
any budget tighter than its own measured need.

⚠️ **zerobas is the slowest on every fill row** (53.6 s vs 16.0 s; 11.3 s vs
4.8 s) because it writes both tables where the references write one. That is a
performance observation about the implementation, **not** a divergence — the
visible result and the error code agree on all three. Any budget must be sized on
the *slowest* machine, so zerobas sets the floor.

🔴 **AND ANY CUT MUST KEEP `step`'S OTHER JOB.** See §1: a separate RUN→capture
knob, defaulting to `step` (hence inert), is the shape that can be cut safely.
A gate that would go RED if the margin were too thin is required before any
budget moves — the obvious subject being the `graphics-acceptance` fill rows,
whose failure mode under a thin budget is a *partial* result, not an error.

## 5. Results — the fix was the budgets' SCOPE, and it shipped

`run_gap` (commits `c04606b`, `f9afec1`) applies a phase's budget to RUN→capture
**only**; line spacing keeps the 2.5 s default. **No budget is tighter than its
measured need** — the fix is to stop charging the completion budget to the typing.

| | before | after |
|---|---|---|
| one bounded-PAINT case (VG-8020) | 2.9 s | **0.5 s** (5.5×), capture byte-identical |
| one bounded-PAINT case (zerobas) | 1.9 s | **0.5 s** (3.6×), capture byte-identical |
| `graphics-acceptance` solo | 269 s | **218 s** |
| `graphics-acceptance` in the battery | 465 s | **347 s** |
| **full battery** | **664 s** | **476 s**, 37/37 green, 0 flakes, ROMs unchanged |

⚠️ **CONVERTED ONLY WHERE THE GAPS ARE PURE TYPING** — `("stored", …)` specs, or a
single line. A DIRECT-mode line executes AS IT IS TYPED, so its gap genuinely is a
completion budget: `deffn` (8 s), `arrays` (6/150 s) and `namspc` (12 s — whose own
comment records that the value exists so `OPEN`/`CLOSE`/`KILL` disk work completes
BETWEEN lines) are deliberately left alone. Cutting those is the mid-fill failure
in another costume.

📏 **`wall ≈ 0.003 s per emulated second`, UNIFORMLY.** A hypothesis that
prompt-idle costs more per emulated second than tight-loop-idle was tested and
**REFUTED** (measured 0.21 s vs 0.36 s per 100 emulated s, inside a ±0.2 s noise
floor). So emulated seconds convert to wall at a flat rate, and the table above is
just that arithmetic — which is also why the SENTINEL saves so little (§6).

## 6. What the sentinel turned out to be for

Capturing on a program-written `done` sentinel instead of at a guessed time was
built and measured (`docs/spec-probe-mark.md`, `TODO.md`). It has **two** uses,
and this section used to record only the first because the second had been
weighed wrong.

🟢 **A. An exact, DETERMINISTIC emulated-time stopwatch.** Marks either side of
an operation give its precise duration on any machine, repeating bit-identically
across runs — the only basis on which a performance differential can be gated
without flaking. That is what produced §4b's exact PAINT figures.

🟢 **B. A CAPTURE TRIGGER, which turns every budget on this page into a pure
FAILURE DETECTOR** (`sentinel_capture=True`; adopted 2026-08-25, D-SNCAP /
D-SNCAP2, now on `graphics-acceptance` plus six more gates). A budget that fires
whether or not the work finished is the hazard §1 is about; a budget that fires
only when the case never signalled is not a guess at all.

⚠️ **THE TWO RESULTS THAT USED TO RETIRE (B) — WHAT SURVIVED AND WHAT DID NOT.**

* *"It reclaims ~0.3 s wall, under the noise floor"* — **STILL TRUE, AND STILL
  NOT THE POINT.** Recomputed deterministically over the six error-shaped gates
  (`scratchpad/sncap/emutotal.py`, off `_tcl`'s own generated timeline):
  **71 104 → 63 927 emulated s, −10.1 %**, ≈ 21 s of wall at §5's flat
  0.003 s/emulated s. No wall claim is made from it — in the environment that
  measured it, the emulator-free warm-up control moved 7 s → 14 s between the two
  batteries and two identical converted runs differed by 59 s. **(B) is adopted
  for the failure-detector property, not for speed.**
* *"It is not safe for screen captures"* — **THE MEASUREMENT STANDS, THE
  CONCLUSION WAS WRONG.** Text captures do differ by exactly 2 characters on all
  three machines — the `Ok`/`ZB` PROMPT, unprinted when the program signals — and
  that is *also* the proof the sentinel fired. But those 2 characters are what
  every text readout already throws away. The blanket refusal is replaced by a
  **BURDEN**: a probe converting a `capture="screen"` row must show ITS OWN
  readout is prompt-independent. `result_span` (last `[`..`]`) and `deffn.face`
  (first such span) are, by construction; **`screen_tail`, which TERMINATES at
  the prompt, is not, and no row reading through it may be converted.**

📏 **AND A MARK IS NOT FREE, WHICH IS THE PART THE 0.3 s FRAMING HID.** It is
BASIC text. `screenerr`'s reclaim is only −5.1 % against −11-13 % elsewhere
because `POKE&HE000,255` pushes its printing line from 36 to 51 characters, past
the 38-char KEYBUF chunk boundary, buying an extra typing slot that gives half
the reclaim straight back. And a longer program moves `VARTAB`, so a readout that
IS a RAM address moves with it — see `docs/spec-probe-mark.md` §3, rule 3.
