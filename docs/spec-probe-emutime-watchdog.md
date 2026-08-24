<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# The emulated-time watchdog — making the probe harness parallel-safe

**Date:** 2026-08-24. **Files:** [`probes/lib/omsx_repl.py`](../probes/lib/omsx_repl.py)
(the watchdog), [`tests/_tmp.py`](../tests/_tmp.py) + 54 test files (temp-path
isolation). **Motive:** the 38-gate battery is ~24 min serial and the
many-small-fixes phase runs it constantly; it would not parallelize reliably.

## 1. Why wall-clock deadlines are the wrong instrument

Every probe boots openMSX with **`set throttle off`** — emulate as fast as the
host allows — and schedules its captures and its `exit` at **emulated** times
(`after time {t}`), fired by openMSX's own event scheduler. The emulated timeline
is therefore *deterministic*; only the **wall** time to run through it varies,
and it varies with how much host CPU the process gets.

The harness, however, killed the process at a **fixed wall-clock deadline**
(`deadline = time.time() + timeout`, SIGKILL). Solo that never fires. Under
contention — 8 emulators competing, or a job scheduled onto a slow **E-core** —
the same run needs *more wall seconds* to reach the same emulated capture point,
and the deadline kills it first. The capture never gets written, and the probe
reads `None` (a *wedge* — empty, never "wrong" data, because the emulation itself
is identical either way).

This is what broke the parallel battery: `graphics-acceptance` (the heaviest —
full CIRCLE/PAINT/spoke renders captured as raw VRAM, one boot per case) wedged on
`spoke_wedge2` under load; a different heavy gate (`tmfp`, `clearpool`) wedged on
other runs. The flakes were **stochastic and non-monotonic in J** — the signature
of an unlucky per-boot scheduling race, not smooth contention.

## 2. The fix — gate the kill on emulated-time PROGRESS, not wall time

The run emits an **emulated-clock heartbeat**: `__hb` rewrites a heartbeat file
with `machine_info time` at `HB_EMU_STEP` (2.0) emulated-second intervals across
the whole timeline. The host watchdog watches that file's **mtime** and kills
only when it **stops advancing** for `HB_STALL` (90) wall-seconds — i.e. when the
*scheduled timeline itself* stopped progressing — never for merely running slow.
A generous `HB_ABSCAP` (1800 s, floored by any caller `timeout`) is a final
paranoia backstop; env `ZEROBAS_OMSX_STALL` / `ZEROBAS_OMSX_ABSCAP` override.

### Why mtime-of-heartbeat, not the emulated-time value

Watching *mtime* (did a beat arrive in wall-time?) rather than the emulated-time
*value* is deliberate, because it catches every way a run can fail to finish:

| failure | emulated clock | heartbeat file | caught by |
|---|---|---|---|
| normal completion | reaches `t`, `exit` fires | stops (process gone) | — (self-exits) |
| **slow / E-core / contended** | advances slowly | keeps advancing in wall-time | **not killed** ✅ (the whole point) |
| **host freeze / crash** | stops | stops updating | mtime stall (90 s) |
| **guest infinite loop** | keeps advancing | keeps advancing | — `after time {t}` exit fires anyway |
| **guest reset loop dropping callbacks** | races ahead | stops (beats were dropped too) | mtime stall (90 s) |

The two guest-runaway rows are the subtle ones. A BASIC/ROM infinite loop **cannot
hang the run**: the capture and `exit` are openMSX scheduler events keyed to
absolute emulated time, fired independently of guest code — the loop just keeps
the CPU busy until emulated `t`, then `exit` fires. A guest that *escapes* the
timeline (e.g. jumps to $0000 in a way that drops the pending `after` callbacks)
would race the emulated clock ahead with nothing scheduled — but then the
**heartbeat callbacks were dropped too**, so beats stop arriving in wall-time and
the mtime-stall watchdog kills it. A value-based "emu-time exceeded budget" check
would miss the host-freeze row (value stops, never exceeds); mtime catches both.
A **redundant emulated-time safety-exit** at `t + 30` is added as belt-and-suspenders
for a dropped primary exit — bounding the run in emulated time regardless of host
speed.

## 3. Temp-path isolation (the second parallel hazard)

`unit-test` runs each `tests/test_*.py` as its own subprocess. ~54 of them
hard-coded `/tmp/zb_*.rom` build artifacts, several sharing a name
(`zb_io` ×4, `zb_vars`/`zb_print`/`zb_wrblk_e2e_ut` ×2) — fine sequentially, but a
collision the moment two test processes touch one concurrently (it surfaced as a
stochastic `pasmo … exit status 1`). All are routed through
[`tests/_tmp.py`](../tests/_tmp.py)'s `tp()`, whose base is `$ZB_TEST_TMP` when set
(the battery sets a unique dir per invocation) and `/tmp` otherwise — so behavior
is **byte-identical when unset**, cross-process build-sharing within one
invocation is preserved, and concurrent invocations no longer collide.

## 4. Validation

- Harness change is inert on results: `circmiss_probe.py` still 17/17, 0 DIFF.
- `unit-test` (all 59 files) green with the transform, `ZB_TEST_TMP` unset.
- Parallel battery at J=8 with the watchdog: see the slice note for the wall time
  and the green count (the whole point — reliable at high J, where wall-deadline
  runs flaked).
