- [ ] 🔬 **THE HARNESS'S WALL TIME HAS A ~5.7 s PERIODIC STALL THAT COSTS ~50 % OF
      AN EMULATOR GATE — AND IT MUST BE RE-MEASURED ON AN IDLE HOST BEFORE ANYONE
      ACTS ON IT.** Measured 2026-08-25, `scratchpad/harness_walltime.py`
      (attribution over a real probe) and `scratchpad/harness_tail.py` (minimal
      reproducer, phase-split).

      📏 **THE SHAPE, MEASURED.** `basic_probe_graphics` = 463 openMSX
      invocations, 216.7 s wall, 23209 emulated s scheduled. Median invocation
      **0.117 s**; a stall of **~5.7 s** recurs and the slowest 10 % are **~55 %
      of all wall**. It is **TIME-periodic, not count-periodic** — proven by
      changing the invocation size:

      | invocation | stall period (count) | × median wall | = period in TIME |
      |---|---|---|---|
      | 1 case | 44.6 | 0.117 s | **5.2 s** |
      | 8 cases | 20.0 | 0.276 s | **5.5 s** |
      | 1 case, diskless VG-8020 | 31.3 | 0.168 s | **5.3 s** |

      🔴 **RULED OUT BY MEASUREMENT, EACH ITS OWN RUN** — harness Python
      (preflight 0.000 s, spawn 0.001 s; the stall is entirely elsewhere);
      emulated-time length (the 40 LONGEST timelines are 42 % of emulated time
      but only 21 % of wall); temp-file Spotlight indexing (a `.noindex` TMPDIR
      changes nothing); the disk image and the machine (diskless VG-8020 shows
      the identical signature); process spawning in general (`/bin/echo` at the
      same rate: **0 stalls**); and launching the binary (`openmsx --version` at
      20/s: **0 stalls**, max 42 ms). A plain compute+file-I/O Python loop shows
      **1 %** in its tail, so the host is not globally freezing.
      🎯 **WHAT IS LEFT: openMSX INITIALISING AND RUNNING A MACHINE.** Sampled
      during a stall, openMSX is at **0.0 % CPU, state `Ss` — sleeping, BLOCKED,
      not starved** — while `WindowServer` (~50 %) and `Claude Helper`
      (~40 %) saturate the host.

      🔴 **AND THAT IS WHY THE NUMBER IS NOT ACTIONABLE YET.** The contention is
      with the GUI rendering the session that MEASURED it. On an idle host or in
      CI it may be absent or entirely different, and a harness redesign priced
      against it would repeat D-PAINTSCAN's mistake — optimising against an
      unvalidated model. **RE-RUN `python3 scratchpad/harness_tail.py` ON AN IDLE
      MACHINE FIRST** (~3 min, N=250); it prints the stall positions and the
      count/time period directly. If the stall survives an idle host, the lever is
      to spawn FEWER emulators (batching where a probe's hold allows it), since
      the cost attaches to running a machine and not to the timeline's length —
      NOT to trim budgets, which are only ~35 % of wall.
      ⚠️ Every wall figure quoted anywhere in this repo was taken in this
      environment, including the battery's 476 s / 502 s and
      `graphics-acceptance`'s 347–373 s.
      🎚️ APPARATUS — harness stall
