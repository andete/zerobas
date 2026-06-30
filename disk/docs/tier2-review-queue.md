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

**[M10 / §8.80 — CONOUT $80 render SOLVED + FIXED + COMMITTED (2026-06-30)] The render blocker was a
register-contract bug in our `$5454` veneer, NOT a CHPUT-internal corruption. Real ASCII now renders.**
· **what:** `conout_body` ($7922) took the output char from **A**; the `$5454` CONOUT contract passes
the char in **E**. The relocated MSX-DOS kernel's per-char console output (caller `$D88A`) sets E=char
and leaves **A=$00**, so ours emitted `$00`/garbage for ALL COMMAND.COM-phase output. The early
MSXDOS.SYS sign-on (caller `$0320`) passes the char in **both A and E**, so the old A-read worked there
and HID the bug — the exact "early works, COMMAND fails" discriminator. Fix = `ld a,e` at conout_body
entry (1 byte, consumes free-tail pad; ROM still 16384 B, no canonical shift). · **how proven (clean,
single-machine):** `$7922`-entry callseq (NEW: A logged) shows register **E** spelling
`MSX-DOS version 1.03` (early, ret=$0320) and `Sun 84-01-01` / `A>` (kernel, ret=$D88A), with A=$00 on
the kernel calls. After the fix, `screen --machine ours --settle 12` renders real text:
`MSX-DOS version 1.03` / `Copyright 1984 by Microsoft` / `Sun 84-01-01` + the boot logo — no `$80`
tiles. · **this OVERTURNS the two entries below** (the "$80 written by an identical-PC data divergence
inside CHPUT" thesis): the prior "char correct at CHPUT entry" evidence was the EARLY phase (capture
nth=5), never a COMMAND-phase glyph — the alignment gap I'd flagged. The divergence is upstream of
CHPUT, in our veneer's char register. · **judgment calls:** (a) extended the ONE harness, not a 58th
probe: added `trace --regdump REG` (aligned-PC register-divergence walk — finds DATA divergence the
fork logic is blind to) and an `A=` field to the callseq logger. (b) Implemented + committed the ROM
fix autonomously — small, net-zero, reversible, gated by the screen-render oracle; Tier-1 19/19 green.
· confidence: HIGH (E spells the banner verbatim; screen renders). · undo: revert the `ld a,e` line.
· **RESIDUALS (next slice, NOT blockers to the render fix):** (1) stray `@` ($40) after the date and a
missing `Current date is `/`Enter new date:` around the date prompt; (2) the headless idle-loop spam at
settle≥14 (`A>@`+`$D8` scrolling) — likely the known BUFIN-never-blocks artifact ([[tier2-storms-are-
downstream]]). A clean *visible* `A>` likely needs a keystroke injected past the date BUFIN so ours
stops racing headlessly. See [tier2-STATE.md](tier2-STATE.md) "Next action".

---

## Archived

Reviewed & re-levelled entries (M5–M10 history) have been split into
[tier2-review-archive.md](tier2-review-archive.md) to keep this live board lean.
Only **Open** (awaiting next sync) lives here.

