- [x] ⚠️ **`DEF FN`: a STRING formal's shadow slot is not a GC root.** Filed
      2026-08-22 by D-DEFFN,
      [`docs/deffn-impl-2026-08-22.md`](../../docs/deffn-impl-2026-08-22.md) §8. The
      slot holds a `[len][ptr]` descriptor and `strheap_gc`'s walk enumerates
      the variable chain and the temp-descriptor stack, not this area. No
      measured row provokes a collection inside an FN call (all three string
      rows concatenate into a temp), so this is a hole in the ROW SET as much as
      in the code — the fix is either a `sg_walk_fnframe` or a snapshot at bind
      time, and the ROW that would catch it does not exist yet.
      ✅ **THE ROW EXISTS, IT WENT RED, AND THE LIVE FRAME IS FIXED (2026-08-27,
      D-FNGCROOT),** [`docs/spec-deffn-gcroot.md`](../../docs/spec-deffn-gcroot.md).
      Both halves of the premise re-ran true on the SHIPPED code. `sg_walk_fnframe`
      walks `[FN_PAREA, FN_FEND)` — **30 B of sub page 0** (2464 → 2434); main ROM
      does not move (low 39 B, page 1 89 B, identical). `o.gcroot` **`376A` →
      `ABCD`**; four rows now gate under `deffn-strict`.
      🔴 **TWO ROUNDS OF GREEN PROVED NOTHING FIRST.** Round 1's "does the heap
      move" arm used `VARPTR`, which is the DESCRIPTOR address and never moves —
      blind, and kept as a negative control. Reading the descriptor's PTR field
      instead showed the body moves **UPWARD** (47851 → 47868), and the dead copy
      is the LOWEST allocation — so a collection alone moves everything AWAY from
      it. The catching row needs THREE things: a formal, a collection, and an
      **allocation after it**. Three controls each remove exactly one.
      🔴 **A CONTROL CAUGHT A CONFOUND BEFORE THE SUBJECT DID** — at `CLEAR 100`
      the no-FN variable control failed on zerobas with `Out of string space`
      while both references returned ABCD. Filed separately below.
      ⚠️ **RESIDUAL, MEASURED NOT IMPLIED:** the walk covers the LIVE frame only;
      an OUTER frame is parked on the Z80 stack where no walk can reach it.
      `n.outer` → zb `q75AB` vs ref `qABCD`, control green. **Same root cause as
      D-FNALIAS** — `fn_enter` resets `FN_SLOTP` and stacks the caller — so both
      want frames that coexist in the shadow area, which needs page-3 RAM.
      🔭 **SCOUTED 2026-09-11 (D-FNGCNEST) — IT BITES ON TODAY'S TREE, AND THE
      SHAPE THAT NEEDS NO SHADOW AREA IS BELOW.** `n.outer` re-run
      ([`scratchpad/deffn_gcnest_probe.py`](../../scratchpad/deffn_gcnest_probe.py),
      [`.out`](../../scratchpad/gcnest_now.out)): zb **`qLMNO`** vs `qABCD` on BOTH
      references, `n.outer.ctl` (same nesting, no collection) `qABCD` on all
      three. So a string `FN` whose body calls another string `FN` that collects
      returns the wrong text — `S$` was read from a slot whose descriptor was
      saved on the Z80 stack and pointed at a body the collection moved. A happy
      path (nested string functions plus ordinary string traffic), not an edge.
      🎯 **THE MECHANISM IS THE SAVE, NOT THE WALK.** `fn_call`
      ([`basic/deffn.asm`](../../basic/deffn.asm)) reserves a block BELOW `SP` and
      `ldir`s the whole `FN_BASE` prefix into it; `fn_leave` copies it back.
      `sg_walk_fnframe` walks `[FN_PAREA, FN_FEND)` — the live frame — and can
      never address a block under `SP`. The filed cure ("frames that coexist in
      the shadow area, page-3 RAM") is one shape; there is another that needs
      NO page-3 RAM beyond one pointer cell:
      **park the saved prefix in the control-frame pool.** The pool (D-CTLPOOL)
      already descends from `CTLTOP` into the variable/string gap, already sizes
      itself by `CLEAR`, and already refuses on collision at `CTLLIM`. An FN
      frame there is `[prevFNSP:2][size:1][the block]`, chained through a new
      `FNSP` cell (2 B; page $E0 has 72 B free since D-FORVAR); `fn_call` becomes
      `ctl_alloc` + the same `ldir`, `fn_leave` the reverse, `fn_deep`'s
      hand-rolled `FN_STK_FLOOR` check becomes the pool's own collision (ERR 7
      either way), and `sg_walk_fnframe` walks the chain after the live frame
      (~30 B of sub page 0, which has ~800 B). D-FNALIAS (formals aliasing, TIER 5)
      wants the same frames and would ride along.
      ⚠️ Priced so far: `ctl_alloc` is in the low region and `fn_call` in main
      page 1, so the call is free of any tenant boundary. An FN body is an
      expression, so no `FOR`/`GOSUB` frame can ever sit ABOVE an FN frame —
      except through an ERROR inside the body: the abort resets SP to SAVSTK
      and never runs `fn_leave`, so a pool frame would be LEAKED (CSP left
      below it until RUN/CLEAR) where the stack shape simply discards it. The
      abort path would need to unwind `FNSP` to its value at statement start
      (one more cell, or re-derive it from CSP) — that is the one real cost the
      pool shape adds, and it is unmeasured.
      🎯 **RULED (Joost, 2026-09-11): the CONTROL-FRAME POOL — option 2.** `fn_call`
      stops reserving its block below `SP` and takes it from the pool (`ctl_alloc`),
      chained through one new 2 B cell (`FNSP`); `sg_walk_fnframe` walks that chain
      after the live frame, so an OUTER frame's string formal is a GC root at last
      (the scout above measured it corrupting: `qLMNO` vs `qABCD` on both
      references). `fn_deep`'s hand-rolled `FN_STK_FLOOR` test becomes the pool's
      own collision (ERR 7 either way), and D-FNALIAS (TIER 5) rides on the same
      frames. No page-3 shadow band is needed — the one real cost is the abort
      path: an error inside an FN body resets `SP` without running `fn_leave`, so
      `FNSP` must be unwound there (one cell, or re-derived from `CSP`) or a frame
      leaks until the next `RUN`/`CLEAR`.
      🤖 AUTONOMOUS — the shape is ruled (Joost, 2026-09-11: the control-frame pool) and the measurements are done.
      🟢 **SHIPPED 2026-09-11 (D-FNPOOL, [`docs/spec-basic-fnpool.md`](../../docs/spec-basic-fnpool.md)) —
      `n.outer` READS `qABCD` ON ALL THREE MACHINES.** Joost ruled the shape the
      same day (*"go for 2 control-frame pool"*): the frame is
      `[prevFNSP:2][size:1][the saved prefix]` taken from the control pool, so one
      past it IS the `CSP` the call started with and `sg_walk_fnframe` walks the
      `FNSP` chain after the live frame — an outer call's string formal is a GC
      root at last. `fn_deep`'s hand-rolled `cp high FN_STK_FLOOR` is gone (ERR 7
      from the pool's own collision, the same answer), `FN_STK_FLOOR` retires, and
      **`SP` is not touched at all any more** — which is what unblocks D-SPMERGE,
      whose relocation that absolute `$F2` compare would have broken on every FN
      call. The three ops ride in the existing DEF FN tenant (sub page 0) because
      main page 1 had ONE byte and the inline version needs ~38.
      🔴 **THREE THINGS THE MACHINE SAID, NOT THE DESIGN:** `FNSP` is power-on
      garbage and the collector now WALKS it (the first GC of a fresh machine was
      a wild read — zeroed in `sh_ctl_reset`, not `clear_vars`, because page 1 had
      five bytes and that needed six); the abort unwind must be GUARDED, because
      unconditional its CALSLT killed four `parennest` rows outright — they reach
      `raise_error` with the stack already wrecked and a slot crossing needs stack
      they no longer have (knifed: removing the call restored all nine pins); and
      `parennest`'s pins are pinned to the CLASS now, not the face, because past
      the cap the trap reports whatever byte the corruption left and two unrelated
      changes walked the same rows through `ERR 50` → dead → `ERR 34` → `ERR 244`.
      ➡️ **NEXT IN THE ARC: D-SPMERGE** — the base into the gap, Joost's MERGE
      ruling, with the nine `parennest` pins as its subject.
      🎚️ TIER 1 (latent) — happy path: a string `FN` formal is not a GC root, so a GC mid-call corrupts a program that did nothing wrong (measured live 2026-09-11: nested string FN + a collection = wrong text)
      🎯 **RULED (Joost, 2026-09-10): scout first** — DONE 2026-09-11, see 🔭 above. The original wording: measure whether a GC
      mid-call actually corrupts a string `FN` result on this tree, then bring the
      fix shape. TIER 1 (latent).
      ✅ **THE RESIDUAL'S 🙋 IS ANSWERED (Joost, 2026-09-11): the pool, not the
      page-3 band** — so "page-3 RAM below LINEBUF, shared with D-FNALIAS" is no
      longer what this needs; `FNSP` is 2 B and the frames come from `ctl_alloc`
      (see the ruling above and [`docs/spec-basic-fnpool.md`](../../docs/spec-basic-fnpool.md)).
      The live-frame half has been shipped and gated since 2026-08-27.
