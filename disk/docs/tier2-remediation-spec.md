<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Remediation spec — FDC-window P0 + vacuous acceptance gate (AWAITING SIGN-OFF)

Status: **DRAFT for sign-off. No source/gate/ROM changes until approved.** Written per the
spec-before-implementation rule after the Tier-C case-2 investigation uncovered a P0 regression
in `main` that our acceptance gate was structurally blind to. User chose "full remediation,
spec first" (2026-07-04).

## 1. What we know (evidence grade)

**VERIFIED IN THIS SESSION (own reruns, not agent-only):**
- **V1 — Vacuous gate.** The committed BDOSX3 capture (`--at 0x0333`, un-armed) fires occurrence
  #1 of `$0333` during BOOT at **t=0.31 s**, ~20 s before the `\rBDOSX3\r` keys (t=20) load the
  program. Result: "0/293 bytes differ" — a hollow PASS comparing COMMAND.COM idle state. The
  arm-gate that prevents this (`_capture_arm`, [disk_probe_diff.py:227](../../probes/disk/disk_probe_diff.py:227))
  is opt-in and NO `build_bdosx*_disk.py` emits it. The Tier-B "6/6 converged" baseline's
  capture rows are therefore not testing the exercised surface.
- **V2 — Live create-file regression in `main`.** The SAME BDOSX3 capture, honestly armed
  (`--arm-check-val 0x03`; anchor now at t≈31–38 s AFTER the program runs) → **17/293 bytes
  differ, `ours=FF` where `stock=00`** at the FOPEN/RDSEQ result fields. Ours fails to REOPEN a
  file it just FMAKE-created. A real regression in the M24–M26 mutation block.
- **V3 — Exerciser self-corruption (my bug).** `bdosx4.asm` walks `IX` across BDOS calls without
  reloading (bdosx3.asm reloads before every `snap`); the kernel returns FCB calls with IX
  clobbered, so our post-call `ld (ix+0),$15` stamped stock's page-3 RAM and killed it — the
  source of the bogus "stock terminates on disk-full" reading. The WRSEQ disk-full ONSET lag
  (ours defers allocation to the 512-B flush boundary; stock detects earlier) is separately real.
- **V4 — Body placement (local, from `build/disk.sym`).** `fdc_entloop_body`=$7F56,
  `fdc_useslot_body`=$7F85, `p0_env_tab`=$7FAC. The guard/equates declare the FDC window as
  $7FB8–$7FBF, so all three sit "below the hole" and are treated as safe today.

**AGENT-DIAGNOSED, SYMPTOM-CONFIRMED, MECHANISM NOT YET INDEPENDENTLY CHECKED:**
- **D1 — Real FDC window is $7F80–$7FBF (the 8 registers mirrored ×8), not just $7FB8–$7FBF.**
  If true, `fdc_useslot_body`@$7F85 (create's dir-slot claim) and `fdc_entloop_body`'s tail
  execute as FDC-register reads, so FMAKE never persists the dir entry and FCLOSE writes to a
  wrapped bogus sector. Regression landed ~M27 (bodies were safe at $55C5 pre-M22b).
  → **CONFIRMED (A1 done, 2026-07-04)** by TWO independent sources: (a) the openMSX
  `National_CF-3300.xml` machine config declares slot 3-1 as a `WD2793` with
  `<connectionstyle>National</connectionstyle>` (the CF-3300's specific FDC register decode);
  (b) a read-only slotted peek of our disk-ROM slot showed our assembled bytes matching
  everywhere EXCEPT exactly `$7F80–$7FBF`, which returns the register file `80 00 03 00 7F 7F 7F
  7F` repeating every 8 bytes (mirrored ×8 = 64 B). TRUE WINDOW = **$7F80–$7FBF**. Bodies inside:
  `fdc_entloop_body` $7F56 (tail), `fdc_useslot_body` $7F85 (fully), `p0_env_tab` $7FAC (partly).
  Phase-B watch-item: p0_env_tab partly-in-window yet boot survives today — clarify why during
  the re-pin (likely its in-window entries are boot-tolerant, per the existing guard comment).

## 2. Scope

**In:** confirm the true FDC window; relocate the create-file bodies out of it + correct the
guard/equates; de-vacuum every BDOSX capture in the gate + fix the bdosx4 IX bug + add an
anti-vacuity assertion; re-verify the whole mutation block honestly; adjudicate Tier-C case 2 on
clean data; update docs + memory.

**Out (unless the re-verify surfaces them):** new BDOS functions; Tier-C cases 3–5 (dir-full,
past-EOF random I/O, rename-collision) — resume after remediation; any hardware-variant work.

## 3. Plan — phased; each phase gated

### Phase A — SEE THE TRUTH (no ROM changes; test/probe only)
- **A1. Confirm the FDC window extent (falsify-first, read-only, clean-room-safe).** With the
  disk ROM paged into page 1, read `$7F40–$7FFF` via a slotted read and compare to the assembled
  `disk.rom` bytes at those addresses. Establish the TRUE mapped window (expect: $7F80–$7FBF reads
  as register mirror bytes, not our opcodes). This observes OUR ROM + hardware mapping (never stock
  ROM code) and is corroborated by the WD2793 partial-decode datasheet fact. **Gate: if the window
  is NOT $7F80–$7FBF, stop and re-diagnose before any fix.**
- **A2. De-vacuum the gate.** Make every `build_bdosx*_disk.py` emit an ARMED capture
  (`--arm-check-val <resident-signature>` at `--arm-check-addr 0x0102`, the convention already
  used by callseq/trace), so the anchor fires only once the exerciser is resident. Add an
  anti-vacuity guard to [disk_bdos_acceptance.py](../../probes/disk/disk_bdos_acceptance.py):
  reject/​fail any capture whose anchor time precedes `--keys-at` (a boot-time anchor is now an
  ERROR, not a silent pass). Fix `bdosx4.asm` to reload `IX` after every BDOS call (scratchpad
  proof exists).
- **A3. Establish the TRUE failure surface.** Re-run the full mutation block (BDOSX/2/3/0 +
  BDOSX4) with honest anchors and record which functions actually diverge (create? write? rename?
  delete? random? absolute?) and by which bytes. Output: the real blast radius — one bug or several.
  → **DONE 2026-07-04. Blast radius is coherent — ONE root cause.** De-vacuumed gate result:
  | Exerciser | recorded-buffer diff | reads back |
  |---|---|---|
  | BDOSX (M21 FCB read/write/close) | **18 + 127 B differ** | `ours=00` where stock has data |
  | BDOSX2 (console + VERIFY) | **0 B** ✓ (AF-at-`done` differs, benign epilogue) | — |
  | BDOSX3 (create/write/rename/delete/random/abs) | **17 + 127 B differ** | `ours=00` where stock has data |
  | BDOSX0 (console/CONIN) | callseq aligned ✓ | — |
  Everything that PERSISTS or READS BACK file data diverges (ours reads zeros — e.g. `057C:
  stock=76 ours=00`); everything console-only converges. Signature of a single create/write
  persistence break (the FDC window), not several independent bugs. NOTE the gate also had a
  SECOND latent vacuity fixed in A2: `mode_capture` returns rc=0 even with byte diffs (no
  --expect), so the old `rc==0` gate would have passed a real diff regardless of the anchor;
  the gate now parses the buffer diff + enforces anti-vacuity + treats live-register deltas as
  informational (the recorded buffer is the evidence, as M24-M26 used).

### Phase B — FIX (ROM changes; only after A1 confirms + A3 scopes)
- **B1. Relocate `fdc_entloop_body` + `fdc_useslot_body`** (and any code whose span enters the
  true window) to known-safe free space, reached unchanged by label (the M21a relocation
  convention). Re-pin `p0_env_tab` entirely ABOVE or BELOW the true hole so every DATA entry reads
  back correctly.
- **B2. Correct the window declaration + guard.** Update `equates.inc` and the
  [runtime.asm](../../disk/runtime.asm:706) guard to the TRUE window bounds, and turn the
  build-time assert into one that fails if ANY executable/PINNED-data byte lands in the real
  window (not just past $7FB8).

### Phase C — RE-VERIFY
- **C1.** Honest gate goes GREEN across the mutation block (ours == stock byte-for-byte at armed
  anchors). **C2.** Tier-1 invariants: `make unit-test` green; `disk.rom` == 16384 B; no
  canonical-address shifts; DSKIO/BLOAD/FILES == CF-3300. **C3.** A create→close→reopen→read
  lifecycle round-trips on ours (the direct P0 regression test).

### Phase D — ADJUDICATE + RECORD
- **D1.** Re-adjudicate Tier-C case 2 (WRSEQ disk-full onset lag + the 712-vs-714 cluster-cap gap
  the agent flagged) on clean data — fix-vs-accept, its own mini-decision.
- **D2.** Docs: STATE board, tier2-bdos-coverage.md (note the vacuity fix + true baseline),
  review-queue (resolve), clean-room-audit run-log. Memory: update
  [[readonly-artifact-oracle]] / add a gate-vacuity lesson.

## 4. Invariants & clean-room
- ROM stays 16384 B; canonical addresses unshifted; Tier-1 green; derive from DPB / public
  contracts / our own code only; stock stays a black box (no ROM-code decode); test disks are
  /tmp copies. The A1 window check reads OUR ROM + hardware mapping, not stock code.

## 5. Risks / rollback
- **Relocation risk:** moving page-1 bodies can collide with other pinned canonical entries (this
  is exactly how the M27 regression happened). Mitigation: A1's corrected build-time assert makes
  any future window intrusion a LOUD failure; C2 re-checks net-zero + Tier-1 each build.
- **Every change is source-level and git-reversible; no irreversible/outward-facing action.**

## 6. Open questions for sign-off
- OK to make the anti-vacuity anchor guard a HARD gate error (may fail other historical captures
  until re-armed)?
- Relocation target for the FDC bodies — reuse the fat.asm free-tail corridor (as M21a did), or a
  specific preferred region?
- Should D1 (Tier-C case 2 disk-full adjudication) block sign-off of the remediation, or ride as a
  follow-on?
