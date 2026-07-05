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
- **Follow-on (3) $23 F_SIZE — CHARACTERISED, verdict CONFIRMED BUG (Fable-solo + re-verified here).**
  Ours' `$23` is a found-BLIND stub: constant `A=L=$03`, random-record field (fcb+33..35) never set.
  Refutes the "valid CP/M dir code" theory — stock returns `A=L=0`+r0=ceil(size/128) on found,
  `A=L=$FF` on not-found (map.grauw.nl `_FSIZE`); ours returns `$03` for found, not-found (re-ran:
  absent file → stock `$FF` / ours `$03`), any slot, any size. A is not a dir code (dir codes are
  F_OPEN/CLOSE/SFIRST/SNEXT per seasip). **Fix is FEATURE-SCALE** (real dir-search + record-count),
  same class as the user-excluded `$26` — needs its own spec + sign-off, not net-zero. HARD-STOP:
  surfaced to the user as a scope decision (do NOT implement unilaterally). Docs (coverage row +
  summary, writepath-spec F2) corrected to the characterised truth.
- **Still open:** (1) implement `$26` WRBLK (user-excluded feature); (3-fix) implement a real `$23`
  FSIZE (feature-scale, pending user decision); (4) WRSEQ disk-full onset lag (P2).

**RESOLUTION 2026-07-04 — M28 block/random pass DONE (real `$23` FSIZE + `$26` WRBLK; user chose
"bundle $23 + $26").** Signed-off spec [tier2-m28-blockrandom-spec.md](tier2-m28-blockrandom-spec.md)
(APPROVED: defer `$27`, full past-EOF extend, sane shrink, Sonnet 5 impl). Implemented + Opus-verified:
- **`$23` FSIZE** — `fsize_body`@`$501E` (dead-pad wire). Gate-converged (BDOSX `$0300` 15→11 diffs;
  the 4 removed are all FSIZE stub artifacts). RAM-visible result, so the gate is its oracle.
- **`$26` WRBLK** — `wrblk_body`@`$47BE`. **The trace agent's "repoint the `$D8BE` table" advice was
  CORRECTED in the Opus verification pass** to a **3b relocation** of `ff_secloop` (the `$D8BE` table
  is the fixed shared-kernel ABI, not ours; `$47BE` collided with live `ff_secloop`) — committed
  5fe8d41 before any code. **Verified byte-identical to the CF-3300 by disk-artifact round-trip**
  (probes/disk/disk_probe_wrblk_roundtrip.py + wrblk_rt.asm — the RAM gate is BLIND to disk writes):
  within-EOF, past-EOF extend, and a 24-bit-RR 33-cluster extend all match stock (size/FAT/data).
- **Sane-shrink divergence (signed off §6 Q3):** ours frees the tail + EOC-marks (FCLOSE succeeds,
  1-cluster consistent chain); stock leaks the tail (verified: 4 clusters under size=384). Documented
  in tier2-bdos-coverage.md — INTENTIONAL, correct-where-stock-is-broken, not a regression.
- **Tier-1 green:** disk.rom=16384; net-zero canonical (baseline sym diff: 0 `k_*` moved); veneers
  correct; FDC window clean; unit-test 28/28 (3 new: test_wrblk_fsize/extend/body_e2e).
- **Two honest edge-case notes (NON-blocking):** (a) `fat_alloc_cluster` is O(n²) so large
  multi-cluster extends are slow but correct (§4 non-goal tradeoff — a 33-cluster extend needed
  >46 s emulated; NOT a bug — initially mistaken for one until re-run with budget); (b) the mod-64K
  `(HL×RS)` transfer-byte wrap on pathological HL (e.g. 513 records/call) is host-multiply-tested
  but not separately round-tripped (ours writes HL records literally; extreme/unrealistic input).
- **Still open (unchanged):** (A) `$27` RDBLK stream-from-0 un-simplification — now the ONLY thing
  keeping BDOSX RED in the gate; deferred with its own COMMAND.COM-boot regression check. (B) WRSEQ
  disk-full onset lag (P2). Neither forced.

**RESOLUTION 2026-07-04 — M29 WRBLK position cursor DONE (perf; user directive "the O(n²) should
be investigated for improvement").** [tier2-m29-wrblk-position-cursor-spec.md](tier2-m29-wrblk-position-cursor-spec.md),
signed off after TWO scope rounds (C+P → narrowed to **P only**). Investigation found the M28
"O(n²)" was actually THREE costs; scope resolved after measuring each:
- **P — positioning re-walk (FIXED):** `wrblk_position_ext` re-`fat_open`'d + re-walked from the head
  every record. Now keeps an incremental cursor (`WRBLK_CURVALID`/`WRBLK_CURSEC`, 3 B in the free
  `$E7F8` tail); same-sector records (¾) do ZERO positioning I/O (`wpe_same`), next-sector = one step
  (`wpe_adv`). `fat.asm`/shared kernel untouched. Measured: K=32 single-call extend **2592 → 131**
  FAT reads (quadratic → linear, ~4/cluster); redundant intermediate data-reads gone.
- **C — no FAT-sector cache (DROPPED):** a `SECTOR_BUF`-keyed cache is clobbered by a data read
  EVERY hop (kernel.asm:1044 then 1100-1101), so ~0 benefit; and P makes the remaining walk a
  once-per-call amortized cost. A useful C needs a dedicated FAT buffer — low value, deferred.
- **A — allocator rescan-from-2 (DEFERRED):** `fat_alloc_cluster` restarts the free-scan at cluster 2
  each call → K-cluster extend still O(K²). Carries a next-free-hint + free-invalidation correctness
  surface; reopen if a workload needs it. **This is why the `rr24` single-record 33-cluster extend
  is UNCHANGED by M29** (one position call, allocation-bound) — still needs `--end 150`, verified
  byte-identical there (no regression). An earlier spec draft wrongly claimed M29 speeds rr24 up;
  corrected in §6.
- **Verification:** existing tests pass with NO expected-value edits (artifact byte-identical);
  new `test_wrblk_cursor.py` asserts O(N) shape (16-rec call ≤28 reads vs old ≥136); Tier-1 green
  (16384 B, 0 `k_*` moved); round-trip byte-identical incl. a NEW `multi` case (8 records/call,
  `checkrec=6`) that directly exercises the cursor path against the CF-3300 oracle.

**RESOLUTION 2026-07-04 — M30 fat_alloc_cluster next-free hint DONE (perf; A, user "continue with A").**
[tier2-m30-alloc-hint-spec.md](tier2-m30-alloc-hint-spec.md). Per-operation hint (`FAT_ALLOCHINT`
`$E7FB`) reset in `fat_mount`, scan-from-hint + advance-on-success in `fat_alloc_cluster`. The feared
**free-invalidation correctness surface does not exist**: only 2 free sites (`wrblk_shrink`, `fdel_body`),
`$16` create orphans, and NO single operation frees-low-then-allocates — so per-operation reset makes it
provably byte-identical to today with ZERO free-site changes.
- **Win is CPU-only (honest correction):** the allocation quadratic was in FAT-entry RAM scans, NOT I/O —
  `fat_alloc_cluster`'s existing `FAT_WRTMP2` intra-call cache already made alloc I/O linear. Measured
  M29→M30 (`wrblk_perf.py --alloc`): CPU **4.4×** (K=32, free 64 in) → **9.2×** (free 400 in); **I/O 1.0×**.
  So modest real-hardware benefit (unlike M29's P, which cut actual sector accesses). `rr24` unchanged.
- **PRE-EXISTING finding surfaced (not M30):** ours is lowest-free-first (reuses freed low clusters); the
  CF-3300 is NOT (`del_realloc`: ours `[340,336]` vs stock `[340,339]`; a HEAD ROM gives the SAME ours
  chain). Round-trip `del_realloc` case is `kind="divergence"` (documents, asserts ours self-consistent).
  **New open item (D):** characterise the CF-3300's post-delete allocation order; decide if matching it is
  worthwhile (spawned follow-up). Not forced.
- **Verification:** 30/30 unit tests, NO expected-value edits (the 2 test edits are FIXTURE seeding of
  `FAT_ALLOCHINT=2`); new `test_fat_alloc_hint.py` (behaviour-identity vs from-2 incl. holes, invariant,
  reset, O(N), disk-full); Tier-1 16384 B + 0 `k_*` moved; byte-identical to a HEAD ROM on `del_realloc`.

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

