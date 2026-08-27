# SAVESTATE-RESTORE-PER-CASE — predictions

## Feasibility (SCORED)
- savestate/loadstate work headless throttle-off — HIT (rc=0)
- `savestate -f path` syntax — MISS (it's `savestate ?name?`; a name may be an abspath, appends `.oms`) 
- loadstate resumes emulated time at save-time, not 0 — HIT (t=6.0)
- `after time` is relative to registration-time — HIT (registered 7.0 at t=6.0 → fired 13.0)
- procs + open file handle survive loadstate — HIT

## Correctness differential (ss_diff.py) — BEFORE running
Claim under test: RESTORE (loadstate a t=BOOT snapshot, inject at t=0) is
byte-identical to COLD (boot-per-case, inject at t=BOOT), because the absolute
emulated schedule is identical and only the route to the t=BOOT state differs.

- P1 module imports, make_savestate writes a .oms — conf HIGH
- P2 cold faces match circmiss expected (cold-path inertness) — conf HIGH
- P3 restore captures non-None — conf HIGH
- P4 restore raw == cold raw, ALL zb cases — conf MEDIUM (the real unknown:
  savestate losslessness + whether `after time 0` fires phase-aligned with
  cold's `after time BOOT`). Lean YES for screen captures (text, robust).
- P5 same holds on vg8020 and cf3300 — conf MEDIUM (cf3300 boot=14, Disk BASIC;
  larger boot, more state; watch it)
- P6 a timing-sensitive VRAM mid-draw capture also matches — conf LOWER (not yet
  built; VDP phase is where a lossy savestate or a one-tick injection offset
  would first show)

## SCORED (screen differential)
- P1 HIT — make_savestate writes .oms, module imports
- P2 HIT — cold faces match circmiss (24 4 / 0 15 / 2 5 / etc.)
- P3 HIT — restore captures non-None
- P4 HIT — zb 17/17 raw-identical
- P5 HIT — vg8020 17/17, cf3300 17/17 (boot=14 Disk BASIC included)
- TOTAL screen: 51/51 cases, 0 raw-DIFF. RESTORE ~0.2s vs COLD ~0.9s per case.

## MISSES found & fixed this arc (apparatus bugs in the NEW code, caught before wiring)
1. `savestate -f path` is not the API — it's `savestate ?name?` (name may be abspath).
2. DOUBLE `.oms`: savestate returns `<name>.oms`, loadstate ALSO appends `.oms`
   → `<name>.oms.oms` not found → a FAILED loadstate silently ABORTS the whole
   Tcl script → host-clock HANG (read as 90s/1800s timeout). Fixed: make_savestate
   returns the base key; _tcl wraps loadstate in catch→marker→exit; _run_batch
   raises LOUD on the marker.
3. openMSX writes no savestate if the target dir is absent → 90s "no snapshot"
   hang. Fixed: make_savestate mkdirs the parent.
4. A RELATIVE savestate name resolves against ~/.openMSX/savestates/, not cwd.
   Fixed: make_savestate abspaths.

## WIRING step (run_cases boot-per-case → snapshot restore) — BEFORE running
- W1 circmiss_probe 17/17 0 DIFF, and FASTER than the ~4min cold run — conf HIGH
  on verdicts, MEDIUM-HIGH on speed (circmiss is 1 case per run_cases call, so
  it benefits only via the per-process CACHE; each side's 17 calls share one
  snapshot after the first)
- W2 `make graphics-acceptance` green and materially faster (the tent-pole, all
  boot-per-case, many cases per call) — conf MEDIUM (biggest behavior change)
- W3 unit-test 59/59 unaffected (no emulator) — conf HIGH
- W4 full `make gates` all-green, ROM hashes unchanged — conf MEDIUM
- W5 wall: expect a MATERIAL cut vs the ~580-750s baseline, driven by
  graphics-acceptance's ~304s solo floor shrinking — conf MEDIUM; the floor is
  memory-bandwidth-bound too, so boot removal may not translate 1:1
- W6 ZEROBAS_SAVESTATE=off restores exactly the old behavior — conf HIGH

## WIRING scored
- W1 HIT (verdicts) — circmiss 17/17 0 DIFF, output BYTE-IDENTICAL to the
  ZEROBAS_SAVESTATE=off run. Speed 24s → 17s (~1.4x). Modest because circmiss's
  per-case emulated timeline (~35 emu-s at step=3.0/cap_gap=8.0) dominates the
  8 emu-s boot, so the ceiling for THIS probe was ~19-25%.
- W6 HIT — off-switch reproduces the old behavior exactly (it was the cold
  baseline for the comparison above).
- 🔴 MISS FOUND BY MEASURING, NOT BY READING: the first gating rule ("snapshot
  only from the 2nd case, or if already cached") left the mechanism INERT for
  every probe that calls run_cases with ONE case at a time — circmiss does, 51
  times. Both runs came back 24s with byte-identical output, which is exactly
  how a wired-but-inert optimisation reads. Fixed: warm whenever there is no
  prologue; the marginal cost is one boot, the cost of not warming is the whole
  speedup. (Class: an optimisation that does nothing is indistinguishable from
  one that works, unless you TIME it against its own off-switch.)
