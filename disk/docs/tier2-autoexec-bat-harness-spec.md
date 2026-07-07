<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# BDOS harness: `AUTOEXEC.BAT` auto-run replacing typed launch — implementation spec

**Status:** DRAFT, awaiting sign-off. No harness code changed yet (verify-first probe only,
in `scratchpad/`, not committed).
**Goal:** the `make bdos-acceptance` gate (primary 11/11 standing guard) currently launches
every `BDOSX*` exerciser by **typing** into the emulator (`disk_probe_diff.py capture --keys
'\rBDOSX\r' --keys-at 20`, across all 8 `build_bdosx*_disk.py` scripts). The leading `\r`
answers the MSX-DOS date prompt; `BDOSX\r` types the run command. This is the same openMSX
key-injection flakiness class (first-keypress doubling in narrow emutime windows,
[openmsx-probing-toolbox.md](openmsx-probing-toolbox.md) §8) that caused the SAVE/BSAVE
false-positive on the Disk-BASIC gate. Parked idea (user, 2026-07-05,
[tier2-review-queue.md](tier2-review-queue.md)): drop an `AUTOEXEC.BAT` on the throwaway DOS
disk next to each `.COM` and drop the typed keys entirely — zero typed input into the gate
that matters most. **No ROM change** — `AUTOEXEC.BAT` is stock `COMMAND.COM`'s job
(disk-resident, identical on ours + the CF-3300), unlike `AUTOEXEC.BAS` which we had to build
into our own Disk-BASIC ROM.

## 1. Verify-first result (black-box, both machines)

Built a throwaway disk = `test.dsk` + `BDOSX.COM`/`BDOSX.BIN` (existing `build_bdosx_disk.py`
fixtures) + a new `AUTOEXEC.BAT` file containing `BDOSX\r\n`. Captured with
`disk_probe_diff.py capture --at <done> --arm-check-val <sig> --settle 40 --machine both`
and **no `--keys` at all**:

```
ALIGNED: both hit occurrence #1  (stock t=17.8416, ours t=18.2618, dt=0.4202)
```

Both machines reach `BDOSX`'s own self-loop anchor with **zero typed keystrokes** — confirming
MSX-DOS 1 (a) auto-runs `AUTOEXEC.BAT` and (b) skips the date prompt, identically on the
CF-3300 oracle and ours. Control: the same disk **without** `AUTOEXEC.BAT`, same zero-keys
capture, times out `MISALIGNED — stock reached anchor: NO, ours reached anchor: NO` — so the
positive result is attributable to `AUTOEXEC.BAT`, not some other boot-timing artifact. (The
residual `AF`/4-byte memory diffs seen in the positive run are the same undefined-register /
date-field noise already allowlisted elsewhere in the BDOSX gate family — unrelated to launch
mechanism.)

This fully closes the "verify-first" gate the parked note required before touching the
primary standing guard.

## 2. Scope — the 8 build scripts

| Script | Current launch | Extra timing dependency |
|---|---|---|
| `build_bdosx_disk.py` | `--keys '\rBDOSX\r' --keys-at 20 --settle 40` | none |
| `build_bdosx0_disk.py` | `--keys '\rBDOSX0\r' --keys-at 20 --settle 30` | none |
| `build_bdosx2_disk.py` | `--keys '\rBDOSX2\r' --keys-at 22` + **`--keys2 'xyz' --keys2-at 32`** | `--keys2` feeds CONIN/DIRIN/INNOE test input (bdosx2.asm records 8-10) — this is functional test data, NOT part of the launch mechanism, and must be preserved; only its **timing anchor** shifts |
| `build_bdosx3_disk.py` | `--keys '\rBDOSX3\r' --keys-at 20 --settle 60` | none |
| `build_bdosx4_disk.py` | `--keys '\rBDOSX4\r' --keys-at 20 --settle 90` | none |
| `build_bdosx5_disk.py` | `--keys '\rBDOSX5\r' --keys-at 20 --settle 90` | none |
| `build_bdosx6_disk.py` | `--keys '\rBDOSX6\r' --keys-at 20 --settle 90` | none |
| `build_bdosx7_disk.py` | `--keys '\rBDOSX7\r' --keys-at 20 --settle 90` | none |

**Common change (7 of 8 scripts, mechanical):**
1. Add `fat12_add(img, "AUTOEXEC", "BAT", b"<NAME>\r\n")` alongside the existing `.COM`/`.BIN`
   injection (reuses the same `fat12_add` already imported from `disk_probe_bdos`).
2. Drop `--keys '\r<NAME>\r' --keys-at NN` from the printed `disk_probe_diff.py` command.
3. Re-verify the anchor still fires at the **same or an earlier** wall-clock time (boot is
   now typing-free, so `done` should hit no later than today — `--settle` values are current
   upper bounds and don't need to shrink, but re-running each is how we prove convergence
   didn't regress; a script that now finishes faster is free to shrink `--settle` but that's a
   cosmetic follow-on, not required for this pass).

**`build_bdosx2_disk.py` (the one non-mechanical case):** `--keys2-at 32` is tuned against
the OLD timeline (banner → date-prompt-answer at ~20-22s → typed command → CONIN wait by
~32s). With `AUTOEXEC.BAT`, BDOSX2 launches immediately after boot, so the CONIN-wait point
lands **earlier** in wall-clock time — `--keys2-at` must be re-measured empirically (differential
capture, watching for the CONIN/DIRIN record boundary) rather than guessed. This is the one
script where "drop the keys" isn't a pure subtraction.

## 3. Rollout plan

- One script at a time, in the table's order (simplest → the keys2 case last).
- Per script: edit, rebuild, run the printed differential, confirm the SAME convergence
  verdict as today's committed gate (byte-identical modulo the already-allowlisted
  undefined-register/date noise) — then move to the next.
- After all 8: full `make bdos-acceptance` (must stay 11/11) + `make unit-test` (34/34,
  unaffected — this is harness-only, no `disk.rom`/`basic.rom` change) + `disk.rom` md5
  unchanged (sanity: this pass touches zero assembly).
- Commit granularity: open to either one commit per script or a single batched commit —
  no preference recorded; will do one commit per script (matches "one TODO item" granularity
  and makes a bad re-anchor easy to `git revert` in isolation) unless told otherwise.

## 4. Risk / why this needs sign-off before starting

This is the **primary 11/11 standing guard** — the thing every other disk-ROM change is
checked against. A bad re-anchor that silently under-verifies (e.g. an anchor that fires on
a boot-time coincidence rather than the real exerciser run, the same vacuous-anchor class
documented in [tier2-remediation-spec.md](tier2-remediation-spec.md)) would be worse than the
flakiness it's meant to fix. Mitigation is the per-script incremental verification in §3, plus
the `--arm-check-val` resident-program-signature guard already in place (guards against the
exact vacuous-anchor bug on re-anchor).

## 5. Open decisions for sign-off

1. **Proceed with all 8, in the §3 order?** Or scope this pass to the 7 mechanical scripts and
   park `build_bdosx2_disk.py`'s `--keys2` re-tuning as its own follow-on (smaller, safer
   per-pass diff)?
2. **Commit granularity** — one commit per script (default above) or a single batched commit
   for all 8?
3. **`--settle` shrinkage** — leave current `--settle` values untouched (upper bounds only,
   safe) even where boot is now faster, or trim them opportunistically per script? Default:
   leave untouched this pass (cosmetic, not required for the fix).
