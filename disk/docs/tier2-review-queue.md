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

**[M11 / §8.81 — REFRAME: the M10 "render solved, residuals cosmetic" picture was OVER-ROSY. Ours runs
COMMAND.COM but its func-9 STROUT output is garbage + loops infinitely; never reaches the COMMAND
banner / date prompt / `A>` (2026-06-30). NO ROM CHANGE this turn — characterisation + reframe only.]**
· **what (ground truth, all test.dsk):** Direct `screen --machine both --settle 16`: STOCK renders
`MSX-DOS version 1.03` / `Copyright 1984 by Microsoft` / `COMMAND version 1.08` / `Current date is Sun
84-01-01` / `Enter new date: .` then blocks at BUFIN. OURS = EVERY row `Ø>@` (`$D8 3E 40`), an INFINITE
garbage loop that scrolls the sign-on OFF; no COMMAND banner, no date prompt, no `A>`. · **how proven
(anchored, decisive):** CHPUT ($00A2) char-stream diff — n=1..53 char-IDENTICAL (the sign-on, proving
alignment), then n=54 FORKS: stock `C=09 STROUT` walking `$C285` spelling `\r\nCOMMAND v…` (ret=$F392);
ours `C=00/02` spelling `Sun 84-01-…` (ret=$7934, our veneer). So stock STROUTs the COMMAND banner;
ours never does a clean func-9 STROUT — only the func-2 date VALUE leaks through, then garbage loops.
Ours DOES reach COMMAND.COM ($0100 arm fires) → handoff works; COMMAND.COM's EXECUTION output is the
break. · **this CORRECTS M10's residual framing:** the "stray @ / missing Current date is / headless
idle spam" were NOT cosmetics or a benign no-keyboard artifact — they are one INFINITE func-9 garbage
loop, THE blocker. "A clean `A>` needs a keystroke past BUFIN" is refuted: ours loops on garbage long
before any BUFIN. · **leading hypothesis (next to test, falsify-first):** our `$5454`/`conout_body`
CONOUT pages the main ROM into PAGE 0 for each char; COMMAND.COM's func-9 string walk reads its string
from page-0/TPA (DE pointer), so the per-char page swap may clobber the walk (reads ROM/garbage, never
hits `$` → infinite loop). OR func-9's DE/string setup is wrong from the start (relocation/work-area).
Step-1 probe pins read-vs-emit before any spec. · **judgment calls:** (a) STOPPED probing at a clean
reframe rather than grinding a fix — per deep-think + guardrails (over-rosy M10 came from trusting a
transient settle-12 frame, not steady state). (b) Did NOT touch ROM — the fix needs a spec + the
mechanism pinned ([[spec-before-implementation]]). (c) Overwrote STATE with the corrected picture;
extended NO new probe (used existing callseq/screen modes). · confidence: HIGH on the observed fork +
infinite loop (screen + char-identical anchor); MEDIUM on the func-9-page-swap mechanism (untested). ·
undo: docs-only; revert this commit to restore the prior STATE. See [tier2-STATE.md](tier2-STATE.md).

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

