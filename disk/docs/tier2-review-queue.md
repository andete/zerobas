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

**[OI-3 / screen-clear · USER-SIGNED-OFF, not self-approved]** Landed `dos_clear_screen` (runtime.asm
free tail, first action in `dos_handoff`): FILVRM `$0056` fills the SCREEN-1 name table (`$1800`, 768)
with spaces via the `pg0_mainrom_in`/`out` inter-slot path (same as `conout_body`'s CHPUT), then homes
the cursor (`$F3DC`/`$F3DD`:=1) — reproduces stock's characterised direct name-table fill + cursor-home
so ours' `A>` lands at ROW09 on a cleared screen, byte-for-byte matching stock.
· **Sign-off:** this was NOT self-approved-by-precedent — it is a different-shaped fix from the M13–M18
`$50xx`-veneer / work-area-cell class, so per [[spec-before-implementation]] it got its own spec
([tier2-oi3-spec.md](tier2-oi3-spec.md)) and **explicit user go-ahead** before implementation, with BOTH
open items resolved by the user as the spec's own recommendation: (i) **STAY-DI** inside the clear (no
`ei`; caller owns IFF across the page-0-RAM handoff, matching the init.asm invariant); (ii) **accept the
data-disk pre-clear side effect** (a bootable data disk like test720.dsk gets its screen blanked before
`BOOT_ENTRY`; Tier-1 checks DSKIO/BLOAD/FILES correctness, not screen content — no extra gate).
· **Alternatives rejected in the spec:** INITXT `$006C` (mode-switches to SCREEN 0), INIT32 `$006F`
(full SCREEN-1 re-init — colour/pattern side effects); raw VDP fill kept only as a fallback. FILVRM is
the surgical AND BIOS-agnostic choice (does only what stock does).
· **Confidence:** HIGH — all 7 spec §6 acceptance criteria pass with concrete numbers (screen
ours==stock; CSRY/CSRX `01 01` was `0F 01`; BDOS 27/27 aligned zero divergence; IX=`$F195` at `$0200`;
steady-state stable no storm; unit-test 19/19; `disk.rom` 16384 B, 3-pass object verified).
· **Undo:** revert commit `dc2ac8d` (single self-contained 35-line addition in the free tail; no
canonical-address shifts, so a clean revert). **This entry CLOSES the Tier-2 DOS-boot-to-`A>` goal.**

---

## Archived

Reviewed & re-levelled entries (M5–M10 history) have been split into
[tier2-review-archive.md](tier2-review-archive.md) to keep this live board lean.
Only **Open** (awaiting next sync) lives here.

