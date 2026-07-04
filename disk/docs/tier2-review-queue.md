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

**RESOLUTION 2026-07-04 — FDC-window P0 FIXED (commit 2047822) + write-path residual root-caused:**
- **FDC-window mechanism CONFIRMED + FIXED.** True window is $7F80–$7FBF (×8 mirror); the three
  position-free tail blocks (fdc_entloop_body/fdc_useslot_body/p0_env_tab) relocated OUT into the
  kernel free-region corridor. PROVEN byte-pure (old-vs-new ROM = 5 clusters: 2 veneer jp operands
  + 1 `ld hl,p0_env_tab` operand + bodies moved verbatim $7F5F→$607E). Window now dead $00 pad;
  guard corrected to $7F80 with a tamper-tested `FDC_WINDOW_INTRUSION` build assert. BDOSX3
  create→reopen→read region converged 17→0 B. Net-zero canonical; disk.rom=16384; unit-test green.
- **De-vacuumed gate residuals ROOT-CAUSED (Fable, 2026-07-04; relocation EXONERATED — all
  reproduce fresh-vs-fresh).** Breakdown: **(c) documented/accepted divergences the gate has no
  allowlist for** — date-stamp (we intentionally don't stamp; fat.asm:16) + dirloc/devid cosmetic;
  **(b) exerciser out-of-contract** — bdosx.asm drives $24/$26/$27 without setting FCB record-size,
  so it compares implementation-defined garbage; **(a) real ROM items** — $23 FSIZE returns A=$03
  not A=0 (return-contract nit); $27 RDBLK (k_47B2) is a documented stream-from-0 simplification;
  $26 WRBLK is UNIMPLEMENTED (feature gap, not a regression).
- **NEW CONFIRMED P1 (independently verified in source):** RDRND/WRRND ($21/$22) position to the
  WRONG record. `rrnd_recsector` ($7C83) and `rrnd_clussec_tmp` ($7CAD) are `db` scratch cells
  INSIDE the ROM (kernel.asm:1699/1729), written at runtime (`ld (…),a`, :1655/:1709) → the stores
  no-op (ROM is read-only), reads always return 0 → BDOS_RECIDX≡0 and the WRRND absolute sector is
  wrong. **Same CLASS as the FDC-window P0** (silent store into ROM address space); NOT in the FDC
  window; latent since M26. Invisible to the RAM-only gate — caught only by disk-artifact inspection
  (ours wrote wrpat to BDOSX.BIN record 0, stock to record 1). Fix = move the 2 cells to RAM.
- **Harness landmines to fix (Fable):** (1) disk_probe_diff.py copies `--diska` ONCE and runs OURS
  then STOCK on that same image (:324/:1246) → unsound for write-exercisers (stock boots an
  ours-mutated disk); didn't drive today's diffs but is a landmine. (2) the BDOS name table
  mislabels $25/$26/$27 ($26=WRBLK, $27=RDBLK). (3) gate needs an allowlist for documented
  divergences + on-disk evidence (RAM capture is blind to wrong-record writes); the exerciser
  fixture ramp has period 256, so buffer bytes cannot prove positional correctness.
- **RESOLVED 2026-07-04 (user chose "spec + fix P1 now" + follow-ons).** Signed-off spec
  [tier2-writepath-remediation-spec.md](tier2-writepath-remediation-spec.md):
  - **F1 DONE (c557628):** RDRND/WRRND P1 fixed (scratch cells ROM→RAM $E760/$E761, net-zero);
    disk-artifact round-trip PASS (WRRND r0=1 → BDOSX.BIN record 1 == CF-3300).
  - **F4 DONE:** disk_probe_diff.py copies per-machine (write-exerciser soundness); BDOS name
    table $26=WRBLK/$27=RDBLK.
  - **F3 DONE:** exact-address anti-vacuous allowlist; BDOSX3 GREEN (documented date/dirloc +
    undefined-return regs cited), gate 4/6. Coverage doc's vacuous $23/$26/$27 claims corrected.
  - **F2 DEFERRED:** $23 FSIZE is a kernel shared call (no disk-ROM handler); A=3 may be a valid
    CP/M dir code — needs its own contract characterisation, not a forced edit.
  - **OPEN tracked follow-ons (next syncs):** (1) implement $26 WRBLK (unimplemented feature);
    (2) fix bdosx.asm to set FCB record-size before block ops so BDOSX is validly gatable;
    (3) characterise the true $23 F_SIZE return-in-A; (4) adjudicate the WRSEQ disk-full onset
    lag (P2, least severe). BDOSX stays honestly RED in the gate until (1)+(2).

**RESOLUTION 2026-07-04 (follow-ons (2) DONE + (3) dispatched):**
- **F5 DONE (follow-on (2)) — bdosx.asm out-of-contract fixed.** `bdosx.asm` now sets FCB+14..15=128
  (word) immediately BEFORE the `$27 RDBLK`/`$26 WRBLK` block ops (NOT after FOPEN — an earlier
  placement corrupts position state the sequential path relies on and breaks stock's RDSEQ; measured
  both ways). Result: the block-op differential is now WELL-FORMED — both machines transfer a defined
  128-B record; the residual is exactly one record's positional offset (`$27` stream-from-0 vs stock's
  random-record position) + the `$26` gap + the `$23` A=3 nit. **Characterisation bonus:** setting
  FCB+14=128 made STOCK read a real block (was `00`), confirming stock MSX-DOS-1 uses FCB+14..15 as
  record size = our `driver.asm:578` interpretation (retires a latent divergence worry). **BDOSX
  still cannot go green from this fix alone** — the premise that the record-size fix "unblocks BDOSX
  to green" was optimistic; green needs the `$26` implementation (explicitly excluded by the user)
  AND the `$27` un-simplification. Gate unchanged at 4/6; BDOSX RED is now diagnostic, not garbage.
- **Follow-on (3) $23 F_SIZE — dispatched (Fable-solo, in flight).** Black-box characterisation of the
  true MSX-DOS-1 F_SIZE return-in-A (is `A=3` a valid CP/M dir code or a bug?). Investigation only,
  no source edits; verdict pending.
- **Still open:** (1) implement `$26` WRBLK (user-excluded feature); (4) WRSEQ disk-full onset lag (P2).

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

