<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

> **Status (2026-11-25):** the adversarial review Joost ruled on: *"fix all of these please, this is the biggest issue
> with zerobas development"*. Work is tracked per item in D-GATESPEED. Figures are arithmetic on the logs of that day.

# Gate-battery wall-time review (adversarial, read-only) — 2026-11-25

Method: read-only. Timings come from `scratchpad/AE_room_full.out` (FULL, 286 units), cross-checked
against `AE_full_r6.out`, `AE_kif_gatefull.out`, `AE_room_full2.out` and eleven SCOPED / four STATIC
logs (`AE_k*_gate.out`, `AE_*_static.out`). Per-unit detail (refcache tallies, spec-live rows) comes
from `scratchpad/gate_logs/*.log` of the battery that finished at 20:58 (`AE_room_full2`). Nothing was
run, so every "saves N s" below is arithmetic on those logs, not a measurement. Paths are relative to
the repo root.

## 0. The three findings that matter most

1. **The reported wall is wrong by about 105 s, and the hidden part is the serial part.**
   [tools/run_gates.py:917](tools/run_gates.py:917) and [:930](tools/run_gates.py:930) reassign `t0`
   (the battery's start, set at [:788](tools/run_gates.py:788)) inside the mutator phase. `ttot` at
   [:1122](tools/run_gates.py:1122) is therefore measured from the *post-mutator refresh*, not from
   the start. The same file warns about exactly this shadowing for the post-checks at
   [:1042-1046](tools/run_gates.py:1042) and uses `_t0` there. Check: `AE_room_full2` prints
   `wall 1450s`; `gate_logs/_warmup.log` was written 20:33:11 and the last retry log 20:58:59, which is
   1548 s after the warm-up *ended* (plus the 12 s warm-up itself). `AE_room_full`'s "728 s" is really
   about 11 (warm-up) + 94 (mutators) + 728 = **833 s**, before the untimed excluded-five suites.
2. **Per-commit tiers, not FULL, are where the day goes, and their wall is one unit: `spec-live`.**
   Of the last 150 commits (2.5 days), 46 are docs-only, 72 probe/tool-only, 28 ROM, 4 harness. In
   every probe-only SCOPED log (53 units) the wall is `spec-live` + about 57 s: 173 s wall with
   spec-live 115 s, 292 with 231, 276 with 218 (`AE_kgs/kdm/knl_gate.out`). spec-live has grown
   189 → 336 → 441 s across three FULL logs as D-KWSPEC adds pages, and it grows with every unit of
   the work that is currently top priority.
3. **FULL is throughput-bound, not tent-pole-bound.** Pool: 281 units, 5253 unit-seconds, J=8, so the
   floor is 657 s; the pool took about 678 s (728 − 10 refresh − ~40 retries). The longest unit
   (441 s) is well inside that. So in FULL a removed unit-second is worth 1/8 s, and parallelising
   *inside* a unit buys nothing. Only removing work, or adding real cores, does. In STATIC and SCOPED
   the opposite holds: they are critical-path-bound (spec-live, kwsweep, the serial mutators).

## 1. Where the time goes (`AE_room_full.out`, FULL)

| phase | seconds | note |
|---|---|---|
| warm-up build (`rm -rf build` + `make WARM`) | 11 | [run_gates.py:785-793](tools/run_gates.py:785) |
| 4 mutators, serial | 94 | `selftest-check` 88, `diskdep-check` 5, `switch-build-check` 1 |
| post-mutator refresh (second `make WARM`) | 10 | [run_gates.py:930-937](tools/run_gates.py:930) |
| pool, 281 units at J=8 | ~678 | 5253 unit-s, 97% of the 8-slot ideal |
| serial retry of 5 real reds | ~40 | units of 2 + 10 + 1 + 6 + 21 s |
| excluded-five suites, serial, after the battery | not timed | [pick_gates.py:714-723](tools/pick_gates.py:714); `lnblank-say` alone is documented at ~134 s |
| **true wall** | **~833 + excluded five** | reported: 728 |

Build + repack share: 21 s (2.5%). Serial phases outside the pool: about 155 s (19%).

Tier split of unit-seconds: STATIC 882, EMULATOR 4465. The "STATIC is 65 serial-seconds" comment
([Makefile:4812](Makefile:4812), [run_gates.py:62-66](tools/run_gates.py:62)) is 13x out of date.

Top 20 units (seconds; r6 = `AE_full_r6`, kif = `AE_kif_gatefull`, both FULL at 281 units):

| # | unit | room | r6 | kif | what the log shows |
|---|---|---|---|---|---|
| 1 | spec-live (STATIC) | 441 | 336 | 189 | 218 BIOS rows + 73 keyword groups on 4 threads, then ~301 screen cases serial |
| 2 | kwsweep | 401 | 371 | 376 | 17 zerobas calls, 27 references replayed, 5 references live every run |
| 3 | graphics-acceptance | 272 | 242 | 250 | 218 zerobas boots, 218 references replayed |
| 4 | ramfree-acceptance | 229 | 220 | 219 | 11 zerobas boots on 4 threads, zerobas only |
| 5 | unit-test (STATIC) | 143 | 128 | 128 | `os.cpu_count()` = 10 workers inside one slot |
| 6 | array-acceptance | 119 | 125 | 119 | |
| 7 | programs-acceptance | 115 | 188 | 191 | own launcher, 151 runs, about a third are references run live |
| 8 | biosregs-acceptance | 112 | 100 | 101 | 143 + 143, 4 threads |
| 9 | ctllim-acceptance | 110 | 143 | 102 | `step=180` emulated s per case, 4 threads |
| 10 | interval-trap-acceptance | 89 | 88 | 91 | |
| 11 | selftest-check (serial) | 88 | 86 | 85 | 90 selftests one after another |
| 12 | wszero-acceptance | 82 | 135 | 136 | 74 + 74 |
| 13 | intarg-acceptance | 82 | 80 | 87 | `run_case`: both sides live, no cache |
| 14 | abort-acceptance | 74 | 67 | 72 | `run_case`: both sides live, no cache |
| 15 | error-trap-acceptance | 73 | 76 | 74 | partly `run_case` |
| 16 | editverb-acceptance | 71 | 82 | 82 | 6 of 6 reference calls miss every run |
| 17 | namspc-acceptance | 64 | 127 | 126 | |
| 18 | clearpool-acceptance | 60 | 62 | 60 | |
| 19 | time-acceptance | 54 | — | — | |
| 20 | lptverb-acceptance | 54 | 89 | 94 | 20 of 20 reference calls miss every run |

Variance: the same 281 units summed 5347, 6265 and 6161 unit-s and took 728, 870 and 860 s reported.
`AE_room_full2` took 1450 s with something else loading the host, and single units swing 2x (programs
115 / 188, wszero 82 / 135, namspc 64 / 126). The battery is CPU-bound and very sensitive to host load.

## 2. Proposals, ranked

Savings are per FULL run unless marked. "unit-s ÷ 8" is the FULL conversion.

### A. Remove / dedupe

**A1. `spec-live`: stop re-measuring pages that cannot have moved; dedupe identical rows.**
- *Scope by input when the ROM is unchanged.* `tools/spec_live.py` already takes rules modules as
  arguments ([spec_live.py:258](tools/spec_live.py:258)), and `pick_gates.spec_live_inputs` already
  knows the changed spec files ([pick_gates.py:99-102](tools/pick_gates.py:99)). It is only used as
  all-or-nothing in STATIC mode ([pick_gates.py:698-705](tools/pick_gates.py:698)). In SCOPED mode
  spec-live always runs whole, because it sits in `STATIC`
  ([run_gates.py:74](tools/run_gates.py:74)) and the SCOPED exclude list only covers `EMULATOR`
  ([pick_gates.py:710](tools/pick_gates.py:710)). When the ROM hashes equal the last green and only
  page P's inputs changed, pass P's rules module(s); run everything when `tools/spec_*`, `ramrec.py`,
  `biosl_run.py` or `probes/lib/` changed.
  Saving: 115–300 s of critical path per probe-only SCOPED run, down to roughly 20 s. That is 48% of
  recent commits. FULL: none.
  Risk: a page whose result depends on a file the planner does not see. `evaluate()` already records
  the run files each page reads ([spec_live.py:66-93](tools/spec_live.py:66)); a probe-to-module
  import closure (`pick_gates.closure`) covers the rest. The daily FULL still runs every page.
  Verify: on 10 past probe-only commits, compare the full spec-live verdict with the scoped one; then
  plant a regression in an untouched page's probe and confirm the planner selects it.
- *Dedupe `disk` and `cf3300` rows.* Both rows boot zerobas on the same machine
  (`C-BIOS_MSX1_EU_REPACK_DISK`, [biosl_run.py:159-160](probes/bios/biosl_run.py:159)) with the same
  `.asm` and `disk=True` ([spec_live.py:137-145](tools/spec_live.py:137)); only the *reference*
  differs, and the reference is not re-run. 38 of the 218 BIOS rows are such repeats: 76 of 348
  worker-seconds in the log (22% of the BIOS half). Memoise on (asm, zerobas machine, disk).
  Saving: about 40 unit-s uncontended, about 5 s FULL, and 10–20 s off spec-live's own wall.
  Risk: none if the key includes every `settings()` field. Verify: assert the two captures are
  byte-equal for one battery before removing the second boot.

**A2. Reference readings that are re-measured every battery (three separate holes).** The battery
replays 2171 reference calls and measures 74–92 live; the holes are:
- *Temp paths in the cache key.* `_param_key` hashes media by bytes only for `diska / diskb /
  cassette / cart` and only when the file exists
  ([probe_refcache.py:364-384](probes/lib/probe_refcache.py:364)). A printer log or tape named in
  `prologue=` or `capture=("screen_printer", log)` is keyed by its fresh temp path, so it misses and
  stores a new entry every run: lptverb 20/20, cassave 16/16, caswbrk 8/8, outdlp 7/21, editverb 6/6,
  tapebios 6/7, kwsweep 5/32, lpterrnl 2/2 (see each unit's `N reference miss ... N stored` line).
  Sources: [basic_probe_cassave.py:200-206](probes/basic/basic_probe_cassave.py:200),
  [basic_probe_editverb.py:298](probes/basic/basic_probe_editverb.py:298),
  [basic_probe_outdlp.py:185-188](probes/basic/basic_probe_outdlp.py:185),
  [basic_probe_kwsweep.py:735-748](probes/basic/basic_probe_kwsweep.py:735). This is the 2026-11-03
  media-path bug again through a second channel. Fix: normalise paths under the probe temp root to a
  placeholder in the key.
  Saving: lptverb ~27, editverb ~47, cassave ~18, caswbrk ~10, outdlp ~8, tapebios ~8, kwsweep
  ~90 (5 of 22 live calls) = about 210 unit-s, 26 s FULL. kwsweep's 90 s is on the ROM-SCOPED
  critical path.
- *`run_case` / `run_batch` bypass the cache.* The cache wrapper lives only in `run_cases`
  ([omsx_repl.py:1842-1986](probes/lib/omsx_repl.py:1842)); `run_case`
  ([omsx_repl.py:1027-1033](probes/lib/omsx_repl.py:1027)) goes straight to `_run_batch`. intarg
  ([basic_probe_intarg.py:126](probes/basic/basic_probe_intarg.py:126)), abort
  ([basic_probe_abort_depth.py:240-244](probes/basic/basic_probe_abort_depth.py:240)), play, sound and
  about 15 sites in error-trap boot the VG-8020 live for every row; their logs carry no refcache line.
  Saving: about half of intarg 82 + abort 74 + play 19, plus ~10 of error-trap = about 100 unit-s,
  12 s FULL.
- *Own launchers never given `cached_run`.* D-REFBYPASS
  ([probe_refcache.py:708-723](probes/lib/probe_refcache.py:708)) converted 13 probes. Still live:
  `run_programs.py` ([:264](probes/programs/run_programs.py:264); 151 runs, 9260 emulated s, a third
  references), `run_sessions.py`, `omsx_session.py` (most disk probes), the lof / badfnum launcher
  ([diskbasic_probe_lof.py:763](probes/disk/diskbasic_probe_lof.py:763)).
  Saving: programs ~38, sessions ~16, lof + badfnum ~30, geteject / gcdi / diskascii / wrblkalt /
  seqmix / playqueue ~50 = about 130 unit-s, 16 s FULL.
- Risk for all three: the D-REFSONLY rule already accepts replaying references; the new risk is a key
  that is too coarse (a path that *is* semantically different). The 14-day expiry and
  `ZEROBAS_REFCACHE=verify` bound it.
  Verify: one `ZEROBAS_REFCACHE=verify` battery after the change must report 0 MISMATCH and 0
  reference miss on a second consecutive run.

**A3. Excluded-five: `lnblank-say-acceptance` runs serially after every FULL while its twin is
daily.** [battery-exclusions.txt:60](tools/battery-exclusions.txt:60) excludes it because it "doubles
~134 s for the same subject". `lnblank-acceptance` itself was moved to `DAILY_SUITES`
([run_gates.py:106-110](tools/run_gates.py:106)), yet `EXCLUDED5` still runs the `--say` variant
after every FULL, serially, with captured output and no timing
([pick_gates.py:66-67](tools/pick_gates.py:66), [:714-723](tools/pick_gates.py:714)). Move it to the
daily set with its twin. The other four are excluded for scope, not parallel-safety; put them in the
pool for FULL or at least time them.
Saving: ~134 s of serial wall per FULL by the documented figure (unmeasured today), more if the other
four join the pool. Risk: `--say` rows are checked daily instead of per FULL, the same trade already
accepted for the twin. Verify: time the five once.

**A4. `selftest-check` re-runs selftests that pool units also run.** It runs every script
advertising `--selftest` in four trees, serially
([check_selftests.py:37](tools/check_selftests.py:37), [:64-70](tools/check_selftests.py:64)). At
least 19 of those are run again by their own STATIC unit (ram-claim, ram-map, build-assert,
needle-case, dead-alias, alias-order, size, hostkill, session-path, temp-root, tracked-inputs,
todo-marker, disk-mount, battery-membership, fixture-integrity, refcache, knife-guard,
knife-rom-guard, deffn-selftest; found by matching `python3 X --selftest` in the recipes). Its job is
"no selftest is uncollected", so let it skip one whose battery recipe provably runs it.
Saving: roughly 15–25 s of *serial* wall on every tier (88 s ÷ 90 scripts × ~20; per-script times are
not logged, so print them first). Risk: a recipe stops running its selftest; the membership check
re-derives that from the recipe each run. Verify: break one deduped selftest; its own unit goes red.

**A5. Proof-skip `unit-test` and `selftest-check` when their inputs did not move.** D-GATESKIP proves
inertness for the emulator tier only ([run_gates.py:215-236](tools/run_gates.py:215)). A docs-only
commit (31% of recent commits) still pays `unit-test` (107–143 s, 10 processes) and `selftest-check`
(88 s serial), though neither reads `docs/` or `todo/`. Give each a fingerprint of its own (ROM
trees + `tests/` + `tools/` + Makefile for unit-test; the four selftest trees plus what they read for
selftest-check) recorded by a green run.
Saving: STATIC goes from about 250 s true wall (e.g. `AE_fff_static`: 140 reported + ~95 hidden) to
about 50 s. FULL: none (FULL should still run them).
Risk: a selftest that reads something outside its fingerprint; `check_probe_reach`, `todo-*` and
`citation` checks read docs and must stay outside the skip. Start with unit-test only, whose inputs
are closed. Verify: a reverse-dependency audit as `unfingerprinted_scripts` does for recipes
([run_gates.py:339-384](tools/run_gates.py:339)).

**A6. Re-run the suite census and apply the existing daily rule.** `scratchpad/suite_census.out`
(2026-11-01) is the evidence D-SUITESWEEP used: never red in a logged gate run and ≥ 60 s. By that
same rule `programs-acceptance` (145 s avg then, 115–191 now, 0 red) and `intarg-acceptance` (0 red in
696 runs, 82 s now) qualify today.
Saving: about 200 unit-s, 25 s FULL. Risk: exactly the one already accepted for the 14 daily suites; a
programs-ladder regression would sit up to a day unless the planner picks it. Verify: the same knife
check D-SUITESWEEP ran (`suitesweep_knives.out`): each must catch a knife in its own subject first.

Irreplaceable as far as the logs show: `graphics-acceptance` (8 reds in 703 runs, the only emulator
suite with a real red rate), `kwsweep` (the keyword net behind every SCOPED plan), `unit-test`
(28 reds in 1752), `ramfree-acceptance` (3 in 654, zerobas-only).

### B. Parallelise / cache / batch

**B1. `spec-live`: about 301 boot-per-case screen cases run serially after its pool.** Six keyword
probes define `live_copy` (kdata 29 cases, kerr 69, kdim 69, kstop 53, klist 39, ktron 42). spec-live
calls them one after another *outside* the thread pool
([spec_live.py:284-286](tools/spec_live.py:284)), and each runs `run_cases(..., batch=False)` per group
(e.g. [kdim.py:123-125](probes/basic/spec/kdim.py:123)). The pooled part is about 1070 worker-s on 4
threads in the contended log; the unit took 795 s, so roughly two thirds of spec-live's wall is this
tail. It is also why the unit grew 189 → 441 s as the screen-case pages landed.
Fix: submit the `own_live` files to the same executor. Second step: try `batch=True` with a `NEW:CLS`
reset; `scratchpad/batchcheck.py` exists to judge that.
Saving: about 225 s off spec-live's wall (300 s tail on 4 threads). That is the critical path of every
STATIC and SCOPED run that includes it. FULL: none from pooling; batching would remove about 250
unit-s (30 s FULL).
Risk: pooling, none (independent boots; D-SUITEWIN already did this for the RAM-record groups).
Batching can change answers when a case leaves state behind; the committed reference side was measured
boot-per-case. Verify: batched vs unbatched zerobas captures byte-equal across all 301 cases, plus a
knife per page.

**B2. The serial mutator phase costs ~105 s on every run of every tier.** `selftest-check` is serial
because some selftests plant into tracked files ([run_gates.py:521-522](tools/run_gates.py:521)), but
all 90 run serially for it. Classify once with the tool already here (`snapshot_tracked` /
`blame_windows`, [run_gates.py:533-577](tools/run_gates.py:533)): the planters stay serial, the rest
run on a pool inside `check_selftests.py` or as pool units. Separately, the 10 s refresh exists only
because restored plants moved mtimes ([run_gates.py:919-937](tools/run_gates.py:919)): restore the
mtime with the bytes (`os.utime`) for files whose content hash is unchanged, and skip the second
`make WARM`.
Saving: 60–80 s (selftests) + 10 s (refresh) per run, all tiers. With A4 the serial phase could fall
under 20 s.
Risk: a planter misclassified as clean is the torn-read class D-SELFMUT fixed; the pool-write detector
already fails the battery on that ([run_gates.py:1162-1175](tools/run_gates.py:1162)). For the mtime
restore: a genuinely changed file must still trigger the rebuild, so key on content hash. Verify: run
the classifier on three batteries; then the stale-ROM knife (plant, restore, check the preflight does
not refuse).

**B3. `kwsweep` is the critical path of every ROM-change SCOPED run** (`AE_resmiss_gate`: wall 530,
kwsweep 390). It makes 17 zerobas calls plus 5 live reference calls in sequence. After A2 (−90 s),
shard it with its existing `--only` ([Makefile:1320-1322](Makefile:1320)) the way lineerr is sharded
([run_gates.py:989-994](tools/run_gates.py:989)), or give it an inner pool as D-SUITEWIN did.
Saving: about 250 s per ROM-SCOPED run (19% of commits). FULL: none.
Risk: the verdict pin (`build/kwsweep-verdicts.json`) must be merged from the shards before
`tiers-md-check` reads it; a lost shard must read as red, not as fewer rows. Verify: the merged pin is
byte-identical to an unsharded run's; the 9 crunch-only words and the DIVERGENT=1 row survive.

**B4. One host-wide emulator budget instead of pools inside pools.** J is `min(8, cpu)`
([run_gates.py:735](tools/run_gates.py:735)) on a 10-core host (8P + 2E), but units bring their own
pools: unit-test `os.cpu_count()` = 10 ([tests/run.py:110](tests/run.py:110)) plus
`multiprocessing.Pool(10)` in two tests, spec-live 4, ctllim 4, ramfree 4, biosregs 4, lof 4,
badfnum 4. Most start in the first minutes, so the early pool runs 25+ busy processes on 10 cores,
which is the condition the stall watchdog and the serial retry exist for. Since D-SUITEWIN the
per-unit seconds also understate CPU.
Fix: a slot semaphore at the one chokepoint every launch passes (`omsx_preflight.guarded`,
[omsx_preflight.py:308](probes/lib/omsx_preflight.py:308)), e.g. an `flock` on one of N slot files
held across `exec`; then set J and the inner pools freely.
Saving: not computable from these logs. The evidence that there is something to win is the 2x unit
swings and the 140 s spread between FULL runs. Risk: a deadlock or a leaked slot; a slot count that is
too high re-creates the starvation flakes. Verify: A/B three batteries each way and compare wall,
retry count and stall-kill lines; record CPU per unit with `os.wait4` rusage in `sh()`
([run_gates.py:592-595](tools/run_gates.py:592)) so later decisions use CPU-seconds.

**B5. `repack-machine` as a stamp file.** It is PHONY, so each unit that names it re-runs
`install-repack-machine.py` twice ([Makefile:996-1000](Makefile:996)). 246 of the 301 listed units
name it now; the run_gates docstring still says 24 ([run_gates.py:15-20](tools/run_gates.py:15)).
Saving: about 0.15–0.3 s × ~230 units = 35–70 unit-s, 5–9 s FULL, and about 460 concurrent XML
re-publishes fewer. Risk: a stale machine XML after an installer change; make the stamp depend on the
installer and the three ROMs. Verify: `preflight-check` plus one edit to the installer.

**B6. Poll latency.** [omsx_repl.py:1332](probes/lib/omsx_repl.py:1332) sleeps 50 ms per watchdog
loop, so each boot returns on average 25 ms after openMSX exits. Use `proc.wait(timeout=0.05)`.
Saving: about 25 ms × several thousand boots = 75–125 unit-s, 10–15 s FULL. Risk: none (same loop,
earlier wake). Verify: `omsx-diag-teeth` and the watchdog selftests.

### Per-commit effect (the part FULL arithmetic hides)

| tier | today (true wall) | after A1 + A5 + B1 + B2 (+ B3) |
|---|---|---|
| STATIC, docs-only | ~250 s | ~50 s |
| SCOPED, probe-only | 270–400 s (spec-live 115–300 + ~57 + ~105 hidden) | ~100 s |
| SCOPED, ROM change | ~640 s (kwsweep 390, spec-live 298) | ~250 s with B3 |
| FULL | ~833 s + excluded five | ~720 s + nothing serial after (A2 −55, A3 −134, A6 −25, B2 −80, B6 −12) |

## 3. Slow because it is wrong

| # | defect | where | cost |
|---|---|---|---|
| W1 | `t0` reassigned in the mutator phase; the printed wall omits warm-up + mutators | [run_gates.py:917](tools/run_gates.py:917), [:930](tools/run_gates.py:930), [:1122](tools/run_gates.py:1122) | every wall figure ever quoted from a non-`--serial` run is ~105 s low |
| W2 | `gates-fast` documented as "~20 s", STATIC as "65 serial-seconds" | [Makefile:4812-4816](Makefile:4812), [run_gates.py:747](tools/run_gates.py:747) | logs show 140–443 s reported (plus W1); STATIC is 882 unit-s |
| W3 | `spec-live` boots emulators but sits in `STATIC`: the D-STATICEMU class, again | [run_gates.py:74](tools/run_gates.py:74), [Makefile:4595](Makefile:4595) | the SCOPED exclude list cannot drop it; it sets the wall of every probe-only run |
| W4 | refcache keys a temp path in `prologue` / `capture`: the same reference call misses and is stored again on every run | [probe_refcache.py:367-397](probes/lib/probe_refcache.py:367) | 74–92 live reference calls per battery; the store holds 121,705 entries (1.8 GB) for a battery that needs about 2,200 |
| W5 | `run_case` / `run_batch` skip the cache wrapper | [omsx_repl.py:1027-1033](probes/lib/omsx_repl.py:1027), [:1788](probes/lib/omsx_repl.py:1788) | intarg, abort, play, sound and parts of error-trap boot references live |
| W6 | spec-live runs six probes' screen cases serially after its own pool | [spec_live.py:284-286](tools/spec_live.py:284) | ~300 s of its 441 |
| W7 | spec-live measures zerobas twice for `disk` and `cf3300` rows of one `.asm` | [biosl_run.py:159-160](probes/bios/biosl_run.py:159), [spec_live.py:137-145](tools/spec_live.py:137) | 38 redundant boots |
| W8 | post-mutator rebuild triggered by mtimes of files whose bytes were restored | [run_gates.py:919-937](tools/run_gates.py:919) | 10 s per run |
| W9 | `repack-machine` PHONY; docstring says 24 dependants, there are 246 | [Makefile:996](Makefile:996), [run_gates.py:15-20](tools/run_gates.py:15) | 2 python launches per unit |
| W10 | banner prints "lineerr in 8 shards" when lineerr is a daily suite not in the run | [run_gates.py:1001-1003](tools/run_gates.py:1001) | cosmetic, but it misdescribes the run |
| W11 | excluded-five run serially after FULL with no timing; includes the twin of a daily suite | [pick_gates.py:714-723](tools/pick_gates.py:714) | unmeasured serial wall, ~134 s documented for one |
| W12 | any edit to `omsx_repl.py`, `omsx_run.py` or `omsx_preflight.py`, comments included, expires every reference entry | [probe_refcache.py:304-333](probes/lib/probe_refcache.py:304) | 3 edits in 14 days, each making the next battery re-measure ~2,200 reference calls; by design, noted only so the cost is known |

Not a lever, checked and dropped: the trailing `cap_gap` after the last capture
([omsx_repl.py:922-928](probes/lib/omsx_repl.py:922)) is about 2.5 emulated seconds at roughly 80x
real time (programs log: 9260 emulated s in 115 s), i.e. ~0.03 s per boot. Renderer and sound are
already off ([omsx_repl.py:1279](probes/lib/omsx_repl.py:1279)). The per-boot cost is process start,
which the savestate slice already measured as not worth chasing.

## 4. Suggested order

1. W1 (one-line fix) and per-unit rusage, so later numbers are true.
2. B1 + A1: spec-live's serial tail and input scoping. Largest daily saving, lowest risk.
3. B2 + A4: the serial mutator phase.
4. A2: the three reference-cache holes, checked by one `verify` battery.
5. A5, A3, B3.
6. B4 only with an A/B; A6 needs a ruling since it trades coverage.
