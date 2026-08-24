<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# Savestate-restore-per-case — skip the cold C-BIOS boot, keep boot-per-case isolation

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

## 4. Status and what is NOT yet done

- **LANDED (inert):** `make_savestate`, the `state_load` path, the defensive
  loadstate, and the `savestate-check` gate (in the `make gates` battery). No
  existing probe passes `state_load` yet, so behavior is unchanged; the capability
  and its correctness control ship first.
- **NEXT (the speedup):** wire `state_load` into `run_cases`/`run_differential`
  so the boot-per-case gates take one snapshot per machine and loadstate per run.
  That is a behavior change to the shared harness and is gated by re-running the
  whole battery green with ROM images unchanged, on top of `savestate-check`.

## 5. Blast radius

| file | change | risk |
|---|---|---|
| `omsx_repl.py` | `make_savestate`; `state_load` in `_tcl`/`_run_batch`; loadstate-fail detection | `state_load=None` byte-identical to before — pinned by circmiss 17/17 + unit-test 59/59 |
| `savestate_check.py` | new gate | emulator-heavy, boot-per-case; carries its own teeth |
| `Makefile`, `run_gates.py` | register `savestate-check` | additive |
