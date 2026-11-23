- [x] ⚠️ **ZEROBAS DRAWS ARCS 5–6× SLOWER THAN THE REFERENCE, AND FULL CIRCLES
      1.5× FASTER.** Filed 2026-08-17 by D-ARCMASK (§6), measured in VDP frames
      via `TIME` with the empty `FOR` loop measured per machine and subtracted
      (`scratchpad/arcmask_time.py`, `arcmask_time2.py`):

          r=95  full  ref 445/448 ms  zb 289/292 ms   0.65x
          r=95  ARC   ref     224 ms  zb    1272 ms   5.68x
          r=200 ARC   ref     436 ms  zb    2600 ms   5.96x

      An arc is CHEAPER than its full circle on the reference (224 vs 448 ms)
      and **4.4× DEARER** on zerobas (1272 vs 292). `gfx_circ_keep` runs two
      `gfx_cross_ge0` per emitted point and D-CIRCOVF widened each to two
      16×16→32 multiplies + a 32-bit compare — eight times per octant step,
      plotted or not. ⚠️ The widening is FORCED (without it the products wrap,
      `docs/circovf-msx1-oracle.md` §5.2); the question is whether the 32-bit
      path can be gated on a cheap 16-bit precondition rather than always taken.
      💰 Not priced. ⚠️ **NO GATE MEASURES TIME AT ALL** — this is invisible to
      `graphics-acceptance`, which only compares planes.
      🔴 Round 1 of this measurement reported three `None`s at N=20; they were
      the CAPTURE WINDOW, not the machine. Re-run at N=5/step 45 s, with the
      `r95` row reproducing round 1 to within one frame as the cross-check.
      ✅ **CLOSED 2026-08-17 by the wedge rewrite, re-measured**
      (`arcmask_time2.py` on `sub.rom e4fbf667`): r=95 arc **1272 → 204 ms**
      (0.91× the reference), r=200 arc **2600 → 368 ms** (0.84×), arc+aspect
      **1384 → 236 ms** — arcs now beat the reference like every other CIRCLE
      form. The full-circle control rows are unchanged (292/340 ms), which is
      what says the win is the mask and not the rig. ⚠️ Still true: **no gate
      measures time** — this closure is a hand-run probe, not a standing gate.
