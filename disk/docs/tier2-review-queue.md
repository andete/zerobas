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

**[Tier-A test-hardening / FAT12-straddle-write bug]** A new host unit test
(`tests/test_fat_write_fat_entry.py`) found a real latent defect in
`fat_write_fat_entry` (fat.asm:579-581): its straddle test checks the `byteidx`
HIGH byte `== 0`, but the straddle case `byteidx == 511 = 0x01FF` has high byte 1
(comment "impossible for 512" is false). So a FAT12 entry whose low byte sits at
sector offset 511 (and, inversely, offset 255) is packed into the wrong sector,
disagreeing with the already-validated reader `fat_next_cluster`. · **Reachable**
on a 720 KB disk at clusters 170 (byteidx 255), 341 & 682 (byteidx 511) — any
file that allocates them corrupts its FAT chain. Invisible to the BDOSX3 emulator
probes because their small test disk only ever touches low clusters (byteidx 3,
4, 6…), never 255/511 — a boundary blind-spot. · **Fix in hand:** 1-byte,
address-neutral (`or a` → `dec a`; ROM stays 16384 B); makes all 4 pack cases +
the write→read round-trip pass. Clean-room: boundary from 512-byte geometry +
FAT12 spec, mirrors our validated reader — no stock disassembly. · **HELD** per
user (2026-07-04): commit fix only after an emulator differential confirms stock
MSX-DOS straddles at byteidx 511 (the oracle). · **Undo:** test committed as
XFAIL (`STRADDLE_FIXED=False`); flip to strict + land the fat.asm fix together
once oracle-confirmed. · confidence: HIGH on the defect (root-caused + empirically
reproduced), MED on needing the oracle step (spec makes it near-certain).

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

