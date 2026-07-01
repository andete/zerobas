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

**[M16 DONE / M17 OPENED — CONIN buffer terminator signed off + landed; new post-SELDSK stall found,
not yet characterised.]**
· User signed off (quick AskUserQuestion, not a full stop) on the §6 fix in
[tier2-conin-spec.md](tier2-conin-spec.md): `cinl_done` writes `$0D` to `buf[2+count]`, matching
stock's observed (data-only) buffer behaviour. Implemented, validated (buffer 0/16 bytes differ, was
1; BDOS call n=21 now SELDSK matching stock, was SDATE), Tier-1 19/19, net-zero. Committed `81c4515`.
· **Found while validating, not yet fixed:** ours now stalls right after SELDSK — 21 BDOS calls vs
stock's 27+, no crash, `screen` shows the cursor advanced but no `A>`. Register/args at the SELDSK
dispatch are identical, so the fork is inside SELDSK's own execution in the loaded (shared) MSXDOS.SYS
kernel — not yet localised to a mechanism. Logged as M17 in [tier2-STATE.md](tier2-STATE.md).
· **judgment call:** did not attempt to characterise M17 in this session — handed to a fresh
Opus-driven investigation per [[opus-vs-sonnet-model-split]] (open-ended ABI-pinning class of work),
same rationale as the M15 hand-off that found the RES_PRINT root cause quickly. · **confidence:**
HIGH that M16's fix is correct and complete (byte-identical buffer + matching BDOS dispatch are
decisive). M17's cause is completely open — no hypothesis yet beyond "same class of gap as
M14/M15/M16." · **undo:** M16 is a committed, validated, low-risk 6-byte addition; clean. M17 is
docs-only so far (no asm). · **awaiting:** M17 characterisation + a fix spec once localised.

---

## Archived

Reviewed & re-levelled entries (M5–M10 history) have been split into
[tier2-review-archive.md](tier2-review-archive.md) to keep this live board lean.
Only **Open** (awaiting next sync) lives here.

