- [x] ✅ **ARC: CONTROL FRAMES BELONG IN ONE HIMEM-BOUNDED POOL, NOT THREE FIXED
      ARRAYS.** 🟢 **LANDED 2026-09-04** (D-CTLPOOL, spec §17): depth **8 -> 2866**,
      linear in `CLEAR` at 8.0 B/frame, `CLEAR ,himem` responds, all three
      D-CTLCROSS rows close, `d.selfarm` unmoved, **146 B of page-3 RAM
      recovered**, 105/105 gates + 59/59 unit files. ✅ **AND THE STORED-FLOOR
      RESIDUAL IS GATED** (D-CTLLIM, spec §18): `make ctllim-acceptance` fills
      memory, drives the pool to its floor and counts corrupted cells -- 0 on all
      three machines, both allocators exercised, knives **3/3 and orthogonal**.
      🔴 Its first matrix scored **0/3** and found two defects IN THE GATE: the
      two refresh hooks cover for each other, and a blank reading on zerobas alone
      -- what a stale floor actually produces, because the machine dies -- was
      reported as an instrument fault instead of as the finding.
      ⚠️ **STILL NOT COVERED:** that no THIRD growth path exists. That would need
      the derivation back, not a cache. Opened 2026-09-04 (Joost) out of D-TRAPSVC, after D-TRAPDEPTH and
      D-STACKPOOL measured what the references actually do
      ([`docs/spec-basic-trapsvc.md`](docs/spec-basic-trapsvc.md) §10–§11).

      **THE MODEL, MEASURED — not inferred.** `CLEAR n` resizes the string space
      and `CLEAR n,addr` sets HIMEM:

          row                     vg8020   cf3300   zb
          baseline, no CLEAR        4080     3311    8
          CLEAR 2200  (+2000 B)     3793     3024    8
          CLEAR 4200  (+4000 B)     3508     2738    8
          CLEAR 200,&HC000          2195     2195    8

      • **+2000 B of string space costs 286 frames on BOTH references**, and the
        next +2000 costs 285/286 — **7.0 B per frame, linear, four times over.**
        One shared pool.
      • **Pinning HIMEM makes the references agree EXACTLY (2195 = 2195).** They
        differed only because Disk BASIC had taken RAM. A fixed array cannot
        produce that.
      • **zerobas reads 8 in every row.** `CLEAR` and HIMEM change nothing.
      • And an abandoned trap dispatch costs ~1 frame on the references too
        (D-TRAPDEPTH) — **nothing is reclaimed anywhere.** `SP` simply moves.

      🎯 **SO THE GAP IS AN ALLOCATION MODEL, NOT A NUMBER**, which is why both
      options the trap item had left were the wrong shape: one added a reclaim the
      reference does not do, the other swapped a fixed array for a bigger fixed
      array — still insensitive to `CLEAR` and HIMEM.

      **WHAT WE HAVE — 154 B of page-3 RAM in three arrays:**

          GOSUB_STK  $E050   8 x 6 B  = 48    GOSUB_DEPTH=8, GOSUB_FRAME=6
          FOR_STK    $EA3A   8 x 11 B = 88    FOR_DEPTH=8,   FOR_FRAME=11
          TRAPSTK    $E20D   6 x 3 B  = 18    TRAPSTK_MAX=6

      🟢 **THE GROUNDWORK EXISTS.** `HIMEM` ($FC4A) is live, `CLEAR` already
      records its second argument, and `basic/str-engine.asm` already computes
      `FRETOP := min(HIMEM,TXTMAX)`. The ceiling concept is there; the control
      frames are what do not use it.

      **THE CHANGE:**
      1. `GSP` / `FSP` / `TRAPSVC` become pointers into one DESCENDING pool
         instead of indices into three arrays.
      2. Overflow stops being "index >= DEPTH" and becomes "collided with the
         variable / string area" — **one check replacing three**.
      3. `CLEAR` resets the pool; that is what makes depth respond to `CLEAR` and
         HIMEM at all, which is rows 2–4 above.
      4. Callers: [`basic/program.asm`](basic/program.asm),
         [`basic/traps.asm`](basic/traps.asm), [`basic/vars.asm`](basic/vars.asm),
         plus the FOR/NEXT path.
      🟢 It also RECOVERS the 154 B and deletes two of the three overflow paths.

      🔴 **AND THE MECHANISM QUESTION RE-OPENED ON 2026-09-04 (D-CTLSTACK §14,
      D-CTLFRE §15, D-EVALDEPTH §16), MEASURED RATHER THAN ARGUED.** The oracles
      were asked WHERE their stack is, not just how deep:
      • `CLEAR n` lowers the published `STKTOP` by exactly n; `MEMSIZ` does not
        move. `(STKTOP-STREND)/depth` = **7.0**, and `FRE(0)` falls **7 B per
        GOSUB level** (7/70/140) — **three independent routes to one number.**
      • 🔴 `CLEAR n,addr` does NOT set `MEMSIZ` to addr: it sets
        `addr - 269 - MAXFILES*267`, so **`MAXFILES` moves the stack top** (the
        ⚠️ filed here as "measure it before assuming it is benign" — it is not).
      • 🎯 **`STKTOP` and zerobas's `strheap_varceil` ARE THE SAME FORMULA.** We
        already compute the reference's stack top and put nothing there.
      • 🔴 **THE EVALUATOR NESTS OUT OF THAT POOL TOO** — 25 B per `DEF FN`
        level, 6 B per parenthesis, both references — **and zerobas caps `DEF FN`
        nesting at THREE** (`FN_STK_FLOOR` `$F200` against `SP` from `$F380` =
        384 B). A separating row proves it is DEPTH, not definition count.
      ⇒ **SO THERE ARE TWO CAPS WITH ONE CAUSE** (GOSUB 8, DEF FN 3), and a
      software pointer running down from `varceil` fixes only the first: `SP`
      stays at `$F380`. Relocating `SP` fixes both, which is why the reference
      has ONE stack — and the honest cost of merging is the per-frame type tag a
      `NEXT` then needs. **The design below is the software-pointer option;
      it is no longer the only candidate. Decide before building.**

      🟢 **THE SHAPE IS SETTLED (2026-09-04), and it is cheap in the SCARCE ROM.**
      Read against the walls (`make basic-reloc`: the main low region and page 1
      are the scarce halves; the sub ROM has ~1.4 KB of page-0 island):

          CTLTOP   the pool's high boundary = `strheap_varceil()`, the SAME cell
                   the string pool already derives from. DERIVED sub-side, never
                   stored -- strheap_floor's own rule and the reason
                   `CLEAR ,himem` falls out for free.
          CSP      the allocation frontier, descending. Empty pool -> CTLTOP.
          GSP      the newest GOSUB frame's address 🎯 AND THEREFORE THE FLOOR OF
                   THE `FOR` RUN -- that is what D-CTLCROSS buys: the FOR frames
                   a NEXT may match are exactly the contiguous run above it, so
                   NO PER-FRAME TAG AND NO WALK.
          TRAPSVC  stays a BYTE COUNT (`ex_return` gates on it with one RAM load
                   on every RETURN; a pointer would cost a 16-bit compare there),
                   beside a new 2-byte `TSP`. 18 B of array -> 2 B.

      🟢 **THE SYMMETRIC HALF IS ONE LINE IN THE SUB ROM.** The variable/array
      allocator already calls `strheap_varceil` for its ceiling (a sub-LOCAL
      call, not a CALSLT) — it becomes `min(varceil, CSP)`, and `sh_free_vars`
      then reports FRE(0) counting down past the live control frames, which is
      what the reference does (`basic_probe_clearpool.py`'s docstring records
      `FRE(0)` falling ~6 B per nesting level there).
      🔴 **THE PUSH SIDE MUST NOT CALSLT.** `GOSUB` push is hot and the
      interpreter is already 2.5–3.8× slow; the collision floor is `ARYEND+2`,
      which lives sub-side. Cache it in a RAM cell the sub-ROM allocator writes
      when it moves `ARYEND` (it is walking the region anyway) so the main ROM's
      check is a plain 16-bit compare. ⚠️ That is a STORED derivation and
      therefore a staleness hole of exactly the kind `strheap_floor`'s comment
      warns about — it needs a gate, not a comment.
      ⚠️ **`MAXFILES=n` MOVES THE POOL TOP** (the channel table is carved below
      the string pool floor). With frames live that is a hazard the string pool
      already has; measure what the references do before assuming it is benign.
      ⚠️ **AND `clear_vars` IS ALREADY THE RIGHT HOOK** — cold boot, RUN, NEW and
      CLEAR, exactly four sites, and `ex_clear` stores POOLSIZE and HIMEM BEFORE
      falling into `clr_done`, so a pool reset sited there picks up the new
      ceiling for free. Point 3 needs no new plumbing.

      ✅ **STEP 1 LANDED 2026-09-04 — THE ACCEPTANCE IS GATED.** All three probes
      are promoted, collected in `tools/run_gates.py`, pinned BY FACE
      (D-NAMEGATE) and **falsified by planting**
      ([`scratchpad/ctlpool_knives.py`](scratchpad/ctlpool_knives.py), 9 cells,
      9 as predicted):

          make stackpool-acceptance   probes/basic/basic_probe_stackpool.py   29 s
          make trapdepth-acceptance   probes/basic/basic_probe_trapdepth.py   52 s
          make ctlcross-acceptance    probes/basic/basic_probe_ctlcross.py    22 s

      ⚠️ **`stackpool-acceptance` GATES A RELATION, NEVER AN ABSOLUTE DEPTH** —
      the two machines have different memory maps by construction, the same rule
      `basic_probe_clearpool.py` states for `FRE(0)`. It asserts sensitivity,
      linearity, the stopping `ERR`, and — between the two REFERENCES, where it
      means something — that pinning HIMEM makes them agree exactly. 🎯 Knife
      K-CP1 (`GOSUB_DEPTH` 8→7) is the control that proves it: the depth moves,
      the MODEL does not, and stackpool correctly stays **green** while trapdepth
      goes red.
      🟢 The filed claims were RE-RUN before any of this was built on: §10's and
      §11's tables reproduce exactly, and `d.selfarm` reads `9 0` on all three.

      🔴 **AND A NEW DIVERGENCE CAME OUT OF DESIGNING IT — D-CTLCROSS
      ([`docs/spec-basic-trapsvc.md`](docs/spec-basic-trapsvc.md) §12).** Three
      fixed arrays make a whole class of question INVISIBLE: a `NEXT` can always
      reach its `FOR` frame, because no GOSUB frame can ever be between them.
      Both references raise **`NEXT without FOR`** whenever it is:

          row         vg8020   cf3300   zb     what the row does
          x.nxgos      0 1      0 1    1 0     NEXT inside a sub, FOR outside
          x.nxdeep     0 1      0 1    1 0     NEXT I across [FOR J][GOSUB][FOR I]
          x.nxagain    0 1      0 1    2 0     ...and the loop-CONTINUES arm

      🎯 **A single pool whose `NEXT` search stops at the first non-`FOR` frame
      closes all three for free** — they diverge BECAUSE the stacks are separate.
      Pinned as known-divergent; **the pins come out in the commit that lands the
      pool.**

      🟢 **AND THE ROWS SETTLE THE FRAME LAYOUT, so it is not a taste question:**
      • **no per-frame type tag** — the `FOR` frames a `NEXT` may match are
        exactly the contiguous run newer than the newest GOSUB frame, and `GSP`
        IS that run's floor;
      • D-FORRET's `FSP-at-push` field becomes **`GSP-at-push`** (`x.retfor`, the
        mirror direction, is already faithful and must stay so);
      • a trap's service record is pushed **before** its GOSUB frame, so it lands
        below it and stays out of the run a `NEXT` walks.

      ⚠️ **GUARDS THAT MUST NOT MOVE:** `d.selfarm` (a handler that re-enables its
      own trap then RETURNs) reads `9 0` on all three TODAY — the case
      `spec-basic-trapsvc.md` §6 warns a fix must not break. And `gosub_push`'s
      `FSP-at-push` field (`GOSUB_FRAME` = `[CURLINE][resume][FSP-at-push]`, from
      D-FORRET) is a cross-stack invariant: a pooled design still has to restore
      the FOR stack on RETURN.
      ⚠️ **`CLEAR` RESETS THE ERROR VECTOR** — measured while writing these rows.
      Any probe that arms `ON ERROR` before a `CLEAR` reads `<NO OUTPUT>`.
      🏗️ ARC — its own slice, its own knives, per verb (GOSUB/RETURN, FOR/NEXT, traps) plus the CLEAR interaction.
