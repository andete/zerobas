- [x] 🔴 **PAINT's SPAN STACK IS A FIXED ARRAY; THE REFERENCE'S GROWS DOWN FROM
      `STKTOP` — A DIVERGENCE NO ROW COVERS, AND THE BIGGEST RAM LEVER WE HAVE.**
      ✅ **SHIPPED 2026-09-27 (D-PAINTSP), per the ruling.** The span stack grows
      DOWN from `SP − GFX_PAINT_MARGIN` toward `ARYEND+2` — the free gap the GC's
      sort buffer already uses — with three 16-bit cursors (`GFX_PSP`/`PBASE`/
      `PFLOOR`) at the front of the old window; `gfx_pstk_addr` is gone. Sub page 0
      16 → 9 B. The margin is PAINT's OWN, MEASURED (breakpoints on our own sub-ROM
      routines): the fill's deepest call 10 B below the reset SP, the deepest
      interrupt entry 18 B; `GFX_PAINT_MARGIN` = 128. 🔴 The first cut used the
      general `CTL_STACK_MARGIN` (256) and a simple fill with ~266 B free raised
      ERR 7 where the VG-8020 completes — the probe caught it.
      📏 [`scratchpad/paintsp_probe.py`](scratchpad/paintsp_probe.py) →
      [`scratchpad/paintsp_run.out`](scratchpad/paintsp_run.out): combs at the
      default ceiling and under `CLEAR 200,&H8500`/`&H8800`, and simple fills with
      1200/600/300 B free — ERR 0 on BOTH machines in every row.
      ⚠️ **NO ROW YET DISCRIMINATES OLD FROM NEW, AND WHY IS MEASURED:** (1)
      zerobas's PAINT holds ≤ 2 spans at once on every comb/dotted pattern tried
      (a watchpoint on `GFX_PSP`), so the 120 cap was never the limit there; (2) in
      tight memory zerobas's own `DIM` refuses first (D-DIMRESERVE) before PAINT
      reaches the band where the reference runs out. The first comb rows were
      VACUOUS besides — colour 4 on the default colour-4 background paints
      nothing — and a knife on the OLD build is what exposed it.
      ⬇️ The original filing:
      🎚️ TIER 3 — COMMON ERRORS. The divergence only shows at the capacity edge
      or under a low `CLEAR ,addr`; no happy path depends on it.
      ~~🙋 **NEEDS-JOOST** — it re-architects a shipped, well-gated feature
      (`sub/graphics.asm` G5), and the reason to do it now is a RAM shortage in a
      different subsystem. Whether that is worth the risk is his call, not mine.~~
      🏗️ **RULED BY JOOST 2026-09-27: RE-ARCHITECT — GROW BELOW SP.** The span stack gets its
      own cursor below SP with an overflow test against the control-frame pool,
      the 360 B array goes, and the acceptance row is the same fill at two
      HIMEMs on both machines. 🤖 **AUTONOMOUS now**, sub-ROM carve first.
      🤖 **AUTONOMOUS** — ruled by Joost 2026-09-27 (above); a carve comes first.
      🎯 **RAISED BY JOOST 2026-09-20:** *"I was wondering about it because if
      we'd use the plain stack we wouldn't need a dedicated region."* Correct,
      and the record supports it more strongly than the question assumed.
      🔴 **WE MEASURED THE REFERENCE AND THEN DID SOMETHING ELSE.**
      `docs/spec-basic-graphics-g5.md:131` (D3, SIGNED OFF) records, measured:
      *"its stack grows down from `STKTOP` and only overflows under
      pathologically tight memory (box + ~73 full-height parallel channels
      completes at normal HIMEM and down to himem=`$8800`; only himem=`$8500`
      forces 'Out of memory in 60')"*. We shipped a FIXED 120-entry array at
      `GFX_PSTK $E3F2` instead.
      ➡️ **THE DIVERGENCE RUNS IN BOTH DIRECTIONS, AND NEITHER IS GATED.** Our
      cap is 120 spans **regardless of HIMEM**, so (1) a fill needing 121+ spans
      raises ERR 7 here at NORMAL himem where the reference completes, and (2) at
      `CLEAR ,&H8500` we SUCCEED where the reference raises *Out of memory*. No
      PAINT row sets HIMEM, so nothing can see either.
      ⚠️ And the shipped capacity is **below D3's own signed-off target**: the
      spec said *"size the stack generously (target ≥128 spans)"*; `GFX_PSTK_CAP`
      is 120, because the window is 376 B.
      💰 **THE RAM IT WOULD FREE IS THE LEVER STEP 9 NEEDS.** `GFX_PSTK` is
      **360 B** at `$E3F2..$E559`, inside the window disk's `SECTOR_BUF` wants
      and which §6.6al measured at **510 B of 512 occupied**. `TEMPPOOL` is the
      same shape — its own header calls it *"a downward-growing array of
      `[len:1][ptr:2]` entries"*, i.e. a stack implemented as a fixed array — and
      is 96 B more. Together ~456 B of the 510.
      🎯 **AND IT RETIRES A SAFETY ARGUMENT THAT IS ALREADY GOING STALE.**
      `GFX_PSTK`'s header licenses its overlap with disk's `SECTOR_BUF` by
      *"the STANDALONE MSX1 disk-ROM … only ever runs while booting/driving
      MSX-DOS, never while the BASIC interpreter (and so never a PAINT
      statement) is live"* — which is exactly the premise `hk_dpload` falsifies
      by construction (§6.6q). `PAINT` then `LOAD` in one program is the case.
      ⚠️ **THE HAZARD, SO IT IS PRICED HONESTLY:** the Z80 stack also carries
      return addresses, so a span-fill cannot simply `push` entries and then
      `call` a helper. It needs its own cursor into the region below `SP` (with
      an overflow test against the control-frame pool, which SP already merges
      with — Joost's 2026-09-11 ruling) rather than raw `push`/`pop`. That is the
      work, and it is why the fixed array was the easy answer first time.
      ➡️ **IF TAKEN, the acceptance row is the one that does not exist yet:** the
      same fill at two HIMEMs on both machines, asserting that overflow tracks
      HIMEM rather than a constant.
