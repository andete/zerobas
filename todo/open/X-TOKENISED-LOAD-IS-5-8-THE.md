- [ ] 🔴 **TOKENISED `LOAD` IS 5.8× THE REFERENCE PER BYTE, AND THAT IS NOT THE
      INTERPRETATION GAP.**
      🎚️ TIER 5 — on-par speed, on `LOAD`.
      📏 **RE-MEASURED 2026-11-08, AFTER D-LOADDIRECT + D-KEYSKIP** ([`loadclock_ab_persec.out`](../../scratchpad/loadclock_ab_persec.out), both
      machines, outside the guest): **0.188 ms/byte here, 0.119 on the CF-3300 -- 1.58x, down
      from 5.8x**; fixed cost 0.37 s here against 1.23 there, so the TOTALS are on par up to
      14 KB (1 KB 0.57 / 1.36 s, 7 KB 1.65 / 2.39, 14 KB 3.07 / 2.94) and fall behind beyond.
      What is left per byte is the lever already filed under the LOAD item above: sectors
      missed on the disk's turn (ours 11 of 28 gaps, the CF-3300's LOAD 4 of 26) and the
      lost-data retries under D-FDCDI's windows (the CF-3300 waits masked: 0 ISRs in 77
      read waits). Open on that, not on the per-byte loop.
      📏 **EXPERIMENT 2026-11-08 -- THE CF-3300's MASKED WAITS, HERE: SLOWER.** FDC_WINMAX = 0 (no
      windows at all; [`loadclock_nowin.out`](../../scratchpad/loadclock_nowin.out)): 1 KB 0.57 -> 0.77 s, 7 KB 1.65 -> 2.05, 14 KB
      3.07 -> 3.27, and TIME ran 51 ticks where it ran 154 (D-LOADDI's regression). 🔮 Predicted
      ~2.6-2.8 s (no retries): MISSED, the wrong way. A masked wait does not remove the
      interrupt, it DEFERS it to the transfer's end -- exactly where the next command
      should leave -- so more sectors are missed than the windows' retries cost. Reverted;
      the windows pay for themselves. The lever is a SHORTER ISR (D-KEYSKIP was one) or a
      window placed away from the data start, not no window.
      🔴 **D-LOADHOLD (2026-11-11): LOAD HAD SLIPPED BACK, AND A PUT-CACHE CHECK WAS ALL OF IT.**
      Re-measured before starting here: 7 KB **1.65 -> 2.65 s**, 14 KB **3.07 -> 3.47 s** (1 KB
      unchanged). Bisected in the gate worktree ([`loadhold_bisect.out`](../../scratchpad/loadhold_bisect.out)): L to 3c2709ad
      (D-PUTCACHE: read_sector's first act is `call rh_check`), M to a6c09b83 (CRTCNT UNDER KEY
      ON -- no disk code; it only moved where the misses fell). Blanking the call put both
      back exactly (1.653 / 3.071 s): ~85 T a sector in rh_check's fast path cost 2 and 5
      disk revolutions -- the per-sector loop sits on the edge of the next sector's arrival.
      Fixed at 0 B: frs_to (a file's data sector: LOAD and every sequential reader) enters
      read_sector past the check (read_sector_nh); the held sector lives in FAT_MBUF and
      every FAT_MBUF reader still passes it. [`loadhold_after.out`](../../scratchpad/loadhold_after.out): 0.568 / 1.654 / 3.070 s.
      🔴 Lesson: a speed item's baseline ROTS -- re-measure before the first experiment; an
      unrelated ~85 T moved this loop by a second.
      🔬 **WHERE THE MISSES ARE (2026-11-11, [`loadgap_drq.out`](../../scratchpad/loadgap_drq.out); `FDC_DRQ=1 scratchpad/fdccmd_probe.py`,
      C = a command, D = its first data byte, J = an interrupt taken):** sectors 1-3 read back
      to back (command -> data in 2-8 ms); sector 3's transfer ends ~164.448, a J lands at
      164.4487 -- IN the ~3.5 ms gap before sector 4 -- and sector 4's command leaves at
      164.4531, too late: its data starts 200 ms later. The 50 Hz interrupt drifts across the
      22 ms sector slots and lands in the gap every few sectors: that is the miss, not the
      FAT walk (a cluster boundary is not where they fall). It also explains the 11-08
      experiment: a MASKED wait defers the interrupt to the transfer's end, i.e. INTO the gap.
      💰 **THE SHAPE, PRICED (not built):** while LOAD chains sectors (hd_full), fdc_io_done
      skips its `ei` and fdc_di_save keeps FDC_IFF "enabled", so a pending interrupt is
      taken in the NEXT command's rotational-wait window (fdc_fdrq's) -- never between a
      transfer's end and the next command; LOAD's end restores EI. ~20 B over fdc_io_done /
      fdc_di_save (disk/fat.asm, $4C29 slack 1 B) and hd_full, plus a flag bit (FDC_IFF's
      bit 7?): a carve first. 🔮 to score when built: misses well under 11 of 28, and TIME
      still advancing during a LOAD (D-LOADDI's guard).
      ⚠️ **BUT MEASURE BEFORE CARVING (noted the next day's pass, 2026-11-11):** D-LOADRUNS's
      multi-sector DSKIO already had this shape -- no `ei` between sectors, interrupts only in
      the waits -- and measured SLOWER (14 KB 3.45 s against 3.07, hd_full's comment). Build
      the chain flag first in a throwaway tree with room borrowed from anything (it never
      ships), score the 🔮, and carve only if it pays.
      🔭 **SCOUT-THEN-ASK** — profiling `dpl_*`'s per-byte path is free;
      SPENDING BYTES on it is not, and the byte budget is Joost's call.
      Measured 2026-09-18 by
      `scratchpad/loadrun_probe.py` (D-LOADRUN), three program sizes per machine,
      linearity checked: **zerobas 0.2178 ms/byte, CF-3300 0.0376**
      ⚠️ **BOTH FIGURES WERE READ FROM `TIME`, AND BOTH CLOCKS LOSE TIME DURING A
      LOAD (2026-10-10):** the CF-3300's runs ~50 % of a load, zerobas's did not
      run at all (D-LOADDI). Timed outside the guest
      ([`loadclock_after.out`](../../scratchpad/loadclock_after.out)): **0.104 ms/byte
      there, 0.55 here (S→L slope), 8.3 s against 2.7 for 14 KB** — the old
      ratio's direction holds, its numbers do not. `loadrun_probe.py`'s own
      control now refuses on zerobas before the fix ("the large load did not
      exceed the small one"), which is how it was found.
      (`disk/docs/spec-diskcode-eviction.md` §6.2c). A 16 KB program is **3.57 s
      here against 0.62 s there**.
      🔴 **THE USUAL EXCUSE DOES NOT COVER IT.** The same probe's own delay
      control prices this machine at **3.0×** the reference on a bare `FOR..NEXT`
      — consistent with D-SPEEDPROF's 2.5–3.8× — and `dpl_*` is ROM code with no
      interpretation per byte, so roughly **2× of the 5.8× is this loop's own**.
      🟢 And the shapes differ in the other direction too: the reference spends
      **0.85 s** of FIXED cost before the first payload byte where we spend
      **0.32 s**, so we win on small files and lose on large ones.
      ⚠️ **NOT THE EVICTION'S BUSINESS** — §6.2c measured this only to price step
      9's inter-slot question, and step 9's answer does not depend on it. Picking
      this up means profiling `dpl_*`'s per-byte path in `basic/cload.asm:1027`
      onwards, which is a TIER 4 slice of its own.
      ⚠️ **AND WHATEVER IS FOUND, RE-MEASURE — DO NOT QUOTE THE FIGURES ABOVE.**
      They were taken before step 9 moved `dpl_*` anywhere, and step 9 adds an
      inter-slot call at the top of exactly this path.
