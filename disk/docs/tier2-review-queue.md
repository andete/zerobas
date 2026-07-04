<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 review queue — decisions taken without per-step sign-off

Running log for the **autonomous-span** working mode (2026-06-25). During a span I
chain `characterise → spec → implement → validate → commit` across milestones
without bouncing back; every judgment call I'd normally have asked about lands here.
When the user is back we do **one batched review** of the open entries, then I
archive them (move the resolved block under "Archived").

**Hard-stops (I pause the span and wait):** a design fork that hinges on user taste;
a clean-room legitimacy call I'm unsure of; anything irreversible/outward-facing;
a regression I can't get green or a blocker I can't crack; a scope surprise that
changes a signed-off plan.

Entry format: **[Mx.y / §8.zz]** what I decided · why · alternative · confidence ·
undo. Newest first.

---

## Open (awaiting next sync)

**[Tier-C → BIGGER] HARD-STOP: the case-2 dig uncovered a vacuous acceptance gate + a live
create-file regression in `main`. Surfaced to user 2026-07-04 (2nd time this thread).**
The Fable-solo root-cause investigation (dispatched after the user chose "investigate root
cause first") returned a much larger result. Two claims INDEPENDENTLY VERIFIED here (own reruns,
not the agent's word):
- **VACUOUS GATE (verified):** the committed BDOSX3 capture (`--at 0x0333`, un-armed) fires
  occurrence #1 during BOOT at **t=0.31 s** — ~20 s before the `\rBDOSX3\r` keys (t=20) load the
  program. "0/293 bytes differ" is a hollow PASS comparing COMMAND.COM idle state, not the
  exercised BDOS surface. The Tier-B "6/6 converged" baseline included these. The arm-gate that
  fixes it (`_capture_arm`, disk_probe_diff.py:227-235) is opt-in and NO builder emits it.
- **LIVE create-file DIVERGENCE (verified):** same BDOSX3 capture, HONESTLY armed
  (`--arm-check-val 0x03`, anchor now at t≈31–38 s AFTER the program runs) → **17/293 bytes
  differ, `ours=FF` where `stock=00`** at the FOPEN/RDSEQ results: ours fails to REOPEN a file it
  just FMAKE-created. A real regression in the M24–M26 mutation block, hidden by the vacuous anchor.
- **CORRECTION to the earlier case-2 note:** the "stock terminates the program on disk-full"
  reading was an ARTIFACT of a bug in our OWN exerciser — `bdosx4.asm` walks `IX` across BDOS
  calls without reloading (bdosx3.asm reloads before each `snap`); the kernel returns FCB calls
  with IX clobbered, so our post-call `ld (ix+0),$15` corrupted stock's page-3 RAM and killed it.
  A scratchpad exerciser that reloads IX runs to completion on BOTH machines. The WRSEQ disk-full
  ONSET lag is still real (ours defers allocation to the 512-B flush boundary; stock detects at
  the first unwritable record) — but it is now the LEAST severe of the findings.
- **Agent's root-cause DIAGNOSIS (symptom verified, mechanism NOT yet independently checked):**
  the National FDC register window is $7F80–$7FBF (mirrored ×8), not just $7FB8–$7FBF as the
  guard assumes (runtime.asm:706-726); `fdc_useslot_body` (create's dir-slot claim, ~$7F8E–$7FB5)
  sits IN it → FMAKE stops persisting the dirent; regression landed ~M27. NEEDS a targeted
  independent check before it's trusted as the fix target.
- **Decision PENDING user:** this is now a P0-in-`main` + verification-gap situation, far beyond
  the Tier-C scope the user greenlit. No source touched; nothing committed for case 2; BDOSX4
  stays OUT of the gate. · confidence: gate-vacuity + live-divergence HIGH (reproduced here);
  FDC-window mechanism MEDIUM (agent-only).

_**Batch-synced 2026-07-04** (consolidation sweep) — the M19→M27 block (20 entries) was
reviewed and moved to [tier2-review-archive.md](tier2-review-archive.md). The Tier-2
DOS-boot-to-`A>` goal is **MET**, full BDOS surface coverage is complete (M26 closed), and
all four post-M26 residuals (LSTOUT characterise+wire, `$2E` VERIFY, M22b slice-2) are
closed. **Nothing is currently open.** A clean-room finding surfaced by the 2026-07-04
whole-target paper-trail audit — a decoded-listing quarantine in tier2-m20-spec.md §11.1 —
was remediated the same pass and logged in
[clean-room-audit.md](../../docs/clean-room-audit.md), not carried as an open item._

---

## Archived

Reviewed & re-levelled entries (M5–M10 history) have been split into
[tier2-review-archive.md](tier2-review-archive.md) to keep this live board lean.
Only **Open** (awaiting next sync) lives here.

