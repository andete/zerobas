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

