<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `.bas`-on-disk test harness — pilot spec (SAVE/BSAVE)

**Status:** DRAFT, awaiting sign-off. Nothing implemented yet.
**Why:** the `type`-injection probes drive the REPL by emulated keystrokes at fixed
emutimes; openMSX doubles the first keypress in narrow machine-specific windows, which cost
a full false-positive bug hunt (SAVE/BSAVE — [diskbasic-verb-coverage.md](diskbasic-verb-coverage.md)
§0, [openmsx-probing-toolbox.md](openmsx-probing-toolbox.md) §8 GOTCHA). This harness removes
the failure class: the test logic runs from a **`.bas` program on a disk image**, not from
keystrokes. Pilot scope = SAVE/BSAVE (signed off); prove the pattern, then generalize.

## 1. Shape

1. **Test program** = a small `.bas` (source, in-repo) that executes the verb(s)
   deterministically and writes a **"done" sentinel** to a fixed RAM address when finished.
   For SAVE/BSAVE it: POKEs a known pattern to a buffer, `BSAVE`s it to `A:`, wipes RAM,
   `BLOAD`s it back to a second buffer, POKEs the done-sentinel.
2. **Disk builder** = extend `tools/make_test_dsk.py` (it already tokenises `PROG.BAS` onto
   FAT12) to place our test `.bas` + set up **auto-run** (see §3).
3. **Runner/probe** = boots the image (per §3), waits for the done-sentinel, then captures —
   and does ALL assertions itself (the `.bas` only *executes*; the probe *judges*):
   - **RAM sentinel** — the done marker (verb ran to completion), and the two buffers
     (BLOAD'd data vs the original pattern → read-path fidelity).
   - **On-disk artifact** — parse the `.dsk` offline and verify the BSAVE'd file's dir
     entry + data bytes = the pattern → write-path fidelity, independent of BLOAD.
   This is the "both" capture: RAM verdict + on-disk evidence.
4. **Differential (optional, later)** = boot the identical image on `National_CF-3300`,
   capture the same state, diff. The `.bas` + boot stub are disk-resident, so both machines
   run byte-identical logic.

## 2. Why capture beats the old probe

The `.bas` does no `type`-timed multi-command dance — one deterministic program run. No
first-key-double window. The probe reads final state, so there is no per-command timing at
all. The nonzero-sentinel lesson is baked in: a no-op verb leaves the sentinel unset → fail,
never a false green.

## 3. The auto-run mechanism — DECISION NEEDED

The launch is the only hard part. Options, with the clean-room + BIOS-agnostic constraint
(must work on our ROM *and* the CF-3300; no ROM-internal entry points):

- **(A) Boot-stub keyboard-buffer pre-fill (the zero-typing goal).** Replace the `$C01E`
  `RET NC` stub with a small **own-design** boot program that writes `RUN"A:TEST.BAS"`+CR
  into the standard BIOS keyboard buffer (`KEYBUF`/`GETPNT`/`PUTPNT`, documented work-area
  addresses) and returns; BASIC then consumes it as if typed. Deterministic (filled once at
  boot, no emutime window), disk-resident → identical on both machines. **RISK:** must verify
  the buffer survives the disk-ROM-boot → BASIC-cold-start transition (BASIC init may clear
  it). Empirical check required before committing.
- **(B) One safe typed `RUN` (robust fallback).** Keep the boot stub inert; have the probe
  issue a *single* openMSX `type "RUN\"A:TEST.BAS\"\r"` at an early, known-safe emutime
  (outside the ~t=26-27 window, leading-space-guarded). Not zero-typing, but one command vs a
  fragile multi-command sequence — 95% of the robustness for ~0 boot engineering.
- **(C) Boot stub jumps into BASIC's RUN via ROM internals.** REJECTED — ROM-version-specific,
  violates BIOS-agnostic; would differ between our ROM and CF-3300.

**Recommended sequencing:** build the harness (§1 program + builder + capture + assertions)
first with launch **(B)** so first-green isn't blocked on boot-loader research and the
capture/differential machinery is proven; then prototype **(A)** and, once verified on both
machines, swap it in for true zero-typing. If (A) proves flaky, (B) is already a large
robustness win over the status quo and can stand as the shipped mechanism.

## 4. Deliverables (pilot)

- `probes/disk/basfiles/save_bsave.bas` (or similar) — the test program source.
- `tools/make_test_dsk.py` extension — tokenise + place the `.bas`; auto-run setup per §3.
- `probes/disk/diskbasic_bas_probe.py` — boot + capture + assert (RAM sentinel + `.dsk`
  artifact); self-asserting, exit-code verdict (fits the existing `diskbasic-acceptance`
  registry so it can replace `disk_probe_save`'s entry).
- Verify: new probe green on our machine; then wire into `make diskbasic-acceptance`
  (retire/park `disk_probe_save`'s type-injection version once the `.bas` one covers it).

## 5. Open decisions for sign-off

1. **Launch mechanism / sequencing** — accept the recommended (B)-first-then-(A)? Or go
   straight for (A) (zero-typing) accepting the boot-loader research up front? Or (B) only?
2. **Tokenisation** — `make_test_dsk.py` builds tokenised lines from our own oracle token
   values (allowed for fixtures). Confirm the `.bas` source → tokenised-on-disk path reuses
   that, so the program is authored as readable BASIC text, not hand-assembled token bytes.
