<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# Savestate-restore-per-case — WITHDRAWN 2026-08-24, and why

> 🔴 **WITHDRAWN (user decision, 2026-08-24). The code is REVERTED — no
> `make_savestate`, no `state_load`, no `savestate-check`, no cache. This document
> is kept as the RECORD, because what it measured outlived what it built.**
>
> **The decision, on the measured numbers:** a same-session A/B of the full
> battery read **555 s with savestate vs 642 s without** — but the OFF run hit a
> flake whose serial retry alone cost ~124 s, *more than the entire difference*,
> so a single run per side cannot support that 13.5 %. The least-confounded
> figure is the same-gate one: `graphics-acceptance` **425 s vs 463 s, ~8 %**.
>
> **That is not worth the inherent risk.** The mechanism is a behaviour change to
> `omsx_repl`, the module every probe in the corpus depends on; it introduced four
> distinct failure modes, *every one of which presented as a hang* (§1); its
> eligibility rule was measured wrong twice in opposite directions (§4); and it
> needed a permanent 17 s gate in the battery to keep proving it safe. **~8 % on
> one gate does not buy that.**
>
> 🟢 **WHAT SURVIVES, and is the real yield of this arc:** §4b — the measurement
> that **refuted the premise the whole item was filed on** ("the per-case cold
> boot dominates the gate suite"; it does not). That refutation redirected the
> work to the emulated-time budgets, and from there to the `done`-sentinel item
> that supersedes them — see [`spec-probe-budget.md`](spec-probe-budget.md) and
> `TODO.md`. The openMSX API findings in §1 are kept because they are true of the
> tool regardless of whether this project uses it.
>
> ⚠️ **If anyone revisits this**: the value of skipping the boot RISES as the
> budget/sentinel work lands (an 8 s boot is ~1 % of a 676 s paint case today, but
> ~5 % of a 151 s one). Revisit it THEN, on fresh numbers — not on these.

---

## (historical) Savestate-restore-per-case — skip the cold C-BIOS boot, keep boot-per-case isolation

**Date:** 2026-08-24. **Files:** [`probes/lib/omsx_repl.py`](../probes/lib/omsx_repl.py)
(`make_savestate` + the `state_load` path in `_tcl`/`_run_batch`),
[`probes/lib/savestate_check.py`](../probes/lib/savestate_check.py) (the standing
correctness gate), [`Makefile`](../Makefile) (`savestate-check`),
[`tools/run_gates.py`](../tools/run_gates.py) (battery registration).

**Motive.** `make gates` is capped at ~2.5x because the PER-CASE cold boot
dominates: every `_run_batch` waits `boot` emulated seconds (8 for the repack disk
and Philips, 14 for the National) for C-BIOS to reach the ready prompt before the
first injection — and the ~8 boot-per-case gates (`batch=False`, chief among them
the un-shardable `graphics-acceptance` tent-pole) pay that boot ONCE PER CASE. A
ready-prompt openMSX savestate, taken once and `loadstate`d per run, gives each
run boot-per-case ISOLATION (a fresh identical state, no delivery race) at the
cost of a `loadstate` instead of a cold boot. This was the sanctioned next lever,
filed 2026-08-24 in `TODO.md` and deferred (with the load-bearing caveat) in
[`spec-rdblk-anchor-flake.md`](spec-rdblk-anchor-flake.md) §8:

> *"a restored state is a different initial condition on both the subject and the
> oracle side. Changing what the gate measures is not a licence a flake-fix
> carries. Worth its own item; noted, not smuggled in."*

🔴 **THE CORRECTNESS GATE IS THE DELIVERABLE, NOT THE SPEEDUP.** §3 proves a
restored snapshot byte-identical to a cold boot before it is allowed to replace
one, on the subject AND both oracles, across text/POINT AND raw-VRAM captures.

## 1. openMSX savestate mechanics (measured 2026-08-24, openMSX 21.0, headless)

Feasibility, all under `set throttle off` + `set renderer none; set sound_driver null`:

- **`savestate ?name?`**, not `savestate -f`. The name may be an ABSOLUTE PATH;
  openMSX appends `.oms` and returns the full path. A NON-absolute name is
  resolved against `~/.openMSX/savestates/`, **not the cwd** — so a relative name
  writes somewhere surprising and usually fails on a missing subdir.
  `make_savestate` therefore `abspath`s the name and `mkdir -p`s its parent.
- **`loadstate <name>` also appends `.oms`.** Passing the returned `<name>.oms`
  makes it look for `<name>.oms.oms` and **fail** — and a failed `loadstate`
  raises a Tcl error that **aborts the whole `-script`**, silently, leaving
  nothing scheduled: the run then hangs until the wall watchdog kills it. So the
  loadstate key is the BASE name (`.oms` stripped), and `_tcl` wraps `loadstate`
  in `catch` → writes a `loadstate.fail=` marker → `exit`, which `_run_batch`
  turns into a LOUD `SystemExit` (never a hang).
- **`loadstate` resumes emulated time at the SAVE-TIME** (a snapshot at t=8.0
  restores to t=8.0), and the Tcl interpreter's procs + open file handle SURVIVE
  the machine switch (they are interpreter-scoped, not machine-scoped).
- **`after time` is RELATIVE to the emulated time at registration.** The existing
  `_tcl` registers every callback during script parse at t≈0, so its
  `after time BOOT` fires at absolute BOOT. With a loadstate at the top, the same
  callbacks register at the restored save-time, so the caller passes `boot=0.0`
  and the first injection lands at the SAME absolute emulated instant a cold boot
  injects at — hence the SAME VDP/interrupt/CPU phase (§2).
- **`after realtime` fires under throttle-off** post-loadstate (the heartbeat
  watchdog keeps working across the machine switch).
- A savestate taken MID-BOOT can THROW (disk activity on the National); the
  snapshot must be a settled ready prompt. `make_savestate` catches and reports it.

## 2. The mechanism — phase-preserving by construction

`make_savestate(machine, path, boot=BOOT)` boots cold and, at `after time BOOT`
(the exact instant the cold path first injects), takes one snapshot. Every
subsequent `_run_batch(..., state_load=<key>, boot=0.0)`:

1. `loadstate <key>` at the very top of the generated Tcl (before the prologue,
   which is machine-scoped and would be wiped by the switch, and before every
   `after time` registration), restoring emulated time to BOOT;
2. schedules its injections at `after time 0.0, step, 2·step, …` — which, being
   relative to the restored BOOT, fire at absolute BOOT, BOOT+step, … — the
   IDENTICAL absolute schedule a cold boot at `boot=BOOT` produces.

So cold and restore differ only in the ROUTE to the t=BOOT machine state (cold
boot vs loadstate); everything after is a deterministic replay of the same
schedule from the same absolute time. Equivalence then reduces to a single
question — **is openMSX's savestate lossless for the state our captures read?** —
which §3 answers empirically rather than by assertion.

`_tcl`/`_run_batch` gain one optional `state_load` parameter, default `None`.
**When `None`, the generated Tcl is byte-identical to before** (verified inert:
`circmiss_probe` 17/17 0 DIFF, `make unit-test` 59/59, ROM images unchanged).

## 3. The correctness gate — `make savestate-check`

Per machine: one ready-prompt snapshot at t=BOOT, then for each case compare the
RAW capture of COLD (`boot=BOOT`, exactly what `run_cases`/`run_case` does) vs
RESTORE (`state_load`, `boot=0.0`). Cases span the readouts real gates take: a
text/error screen, a POINT-into-text draw, and two raw-VRAM SCREEN-2 draws
(a circle and a filled PAINT). Subject (`C-BIOS_MSX1_EU_REPACK_DISK`) + both
oracles (`Philips_VG_8020`, `National_CF-3300`).

🔴 **A 0-DIFF TALLY IS VACUOUS WITHOUT TEETH.** The gate also asserts, within each
run, `cold(draw) != cold(error)` — proof the raw comparison can tell two
genuinely different captures apart, so a green tally means "restore matched",
never "the comparison is blind" [[apparatus-is-part-of-the-measurement]].

### Results (2026-08-24, from clean-equivalent build `41b8c4ed`/`1922eaa0`/`7d27b871`)

- **`savestate-check`: 12/12 restore==cold, 0 DIFF; teeth OK** on all three
  machines (4 cases each: err, draw, vcircle, vpaint).
- The wider development differential (scratchpad) that this gate distils:
  **circmiss's 17 cases × 3 machines = 51/51 raw-identical**, and a raw-VRAM
  battery (full 6144-byte SCREEN-2 pattern table, 5 draws × 3 machines) **15/15,
  0 differing nibbles**. Teeth: `cold(draw)!=cold(err)` and
  `restore(draw)!=cold(err)`, `restore(draw)==cold(draw)`.
- Measured speedup on a single case: RESTORE ~0.2 s vs COLD ~0.9 s wall (the
  8-emulated-second boot skipped).

## 4. The wiring, and the eligibility rule that was measured wrong TWICE

`run_cases(batch=False)` and the self-heal re-run go through `_boot_per_case`,
which restores a cached snapshot where that is equivalent. `ZEROBAS_SAVESTATE=off`
disarms the whole mechanism and reproduces the old behaviour exactly (it is both
the operator escape hatch and the A/B baseline every timing below is against).

🔴 **NEITHER FAILED RULE IS VISIBLE IN THE CODE; BOTH TOOK A STOPWATCH.**

1. *"snapshot from the SECOND case of a call, or when already cached"* — INERT for
   every probe that calls `run_cases` with ONE case at a time (circmiss does, 51
   times): no call reaches a second case, so nothing ever warmed. **24 s on, 24 s
   off, byte-identical output** — which is exactly how a wired-but-inert
   optimisation reads if you only check that the verdicts still agree.
2. *"warm on the FIRST sighting"* — fixed that, bought a **pessimism**.
   `basic_probe_lineerr` copies a fresh disk image PER CASE (deliberately, for
   write isolation), so every case is a new key: **measured 6 snapshots for 6
   rows**, each paying a snapshot boot AND a restore where cold paid one boot.
   The A/B read **36 s vs 39 s** — a self-cancelling mechanism looks near-neutral
   in the total.
3. **The rule that survives both: warm on the SECOND SIGHTING of a key.**
   Self-tuning, needs no knowledge of what varies — a key used once is never
   snapshotted (pure cold, no thrash), a key used many times pays ONE learning
   boot and restores ever after. Verified: **lineerr 0 snapshots**, **circmiss
   24 s → 21 s, byte-identical**.

**A `prologue` DECLINES the snapshot**, and that is correctness, not a coverage
gap: `prologue` exists for machine-scoped `plug joyporta <device>` — a device the
cold path has plugged for the ROM's *whole boot* — while a snapshot is taken on an
unplugged boot and `loadstate` replaces the machine. `cart`/`diska` are part of
the cache identity for the same reason.

## 4b. 🔴 The item's PREMISE does not survive the measurement

This was filed as *"the per-case boot dominates, savestate gets batch speed with
boot-per-case isolation"*. **It does not dominate.** The boot is ~0.7 s of wall
per case; the gates that dominate the suite spend far more inside their own
EMULATED timelines:

| gate shape | per-case emulated timeline | boot's share |
|---|---|---|
| `graphics-acceptance` PAINT phases | `step` 45–90 emulated s | ~10–15% |
| circmiss-shaped | ~35 emulated s | ~20–25% |
| `lineerr` rows | `step` 2.5–4.5 emulated s | large — **but excluded**, per-case disk |

And the one gate where boot *should* have dominated — `lineerr`, 210 rows,
~46% of the serial suite — is excluded by its own per-case disk isolation (§4).

**Battery, measured:** 555 s 38/38 green with 0 flakes (this rule), 680 s 38/38
with one flake retry (the previous rule), against a **580–750 s baseline** — i.e.
**within run-to-run noise, not the multiple the item predicted.**
Single-gate: `graphics-acceptance` 269 s solo vs a ~304 s baseline (~12%).

🟢 **What IS durable is §3**: the capability, and a standing gate that re-proves
restore ≡ cold boot every run. 🎯 **The real remaining lever is the emulated-time
budgets** (`step`, `cap_gap`, `PAINT_STEP`) — every one of them a hand-picked
margin, several explicitly generous — which is a different item with its own
correctness question, and must not be trimmed by reasoning either.

## 5. Blast radius

| file | change | risk |
|---|---|---|
| `omsx_repl.py` | `make_savestate`; `state_load` in `_tcl`/`_run_batch`; loadstate-fail detection | `state_load=None` byte-identical to before — pinned by circmiss 17/17 + unit-test 59/59 |
| `savestate_check.py` | new gate | emulator-heavy, boot-per-case; carries its own teeth |
| `Makefile`, `run_gates.py` | register `savestate-check` | additive |
