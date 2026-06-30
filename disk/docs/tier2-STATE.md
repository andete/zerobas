<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 STATE — resume here first

**This file is OVERWRITTEN, not appended.** It is the O(1) "where are we" board so a
new session doesn't have to re-read the 580-line audit log + do git archaeology.
History/provenance lives in [tier2-review-queue.md](tier2-review-queue.md); detail
specs are the `tier2-*.md` docs. Read this, then the one doc the next-action names.

_Last updated: 2026-06-30 (M11 REFRAME — the M10 "render solved, residuals are cosmetic" picture was
OVER-ROSY. Direct `screen` observation at settle 16 shows OURS in an INFINITE garbage loop (`Ø>@` =
`$D8 3E 40`, scrolling) — the sign-on renders then SCROLLS OFF; there is NO `COMMAND version 1.08`, NO
date prompt, NO `A>`. STOCK reaches `COMMAND version 1.08` / `Current date is Sun 84-01-01` /
`Enter new date:` and blocks at BUFIN. The CHPUT char-stream forks right after the identical sign-on
(n=53): stock emits **func-9 STROUT** strings (the banners/prompts), ours emits only the func-2 date
value then garbage. Ours DOES reach COMMAND.COM ($0100) so the handoff works — **COMMAND.COM runs but
its string-output (func-9 STROUT) path produces garbage and loops infinitely**. The "headless idle
spam" was NOT a benign artifact; it is THE blocker. NEXT = pin the func-9 STROUT divergence,
falsify-first, then spec a fix.)_

---

## Goal
Boot MSX-DOS to the `A>` prompt under zerobas-disk (Tier-2) **without regressing
Tier-1** (disk-BASIC / BLOAD / FILES) and while staying a **BIOS-agnostic replacement
disk ROM** (works on CF-3300, C-BIOS, any standards MSX1). "Reached `A>`" means a
**visible** `A>` on screen + accepts a command — not just the right BDOS call sequence.

## Live thesis (2026-06-30 M11.1: COMMAND.COM runs IDENTICALLY; TWO bugs in our relocated kernel console I/O)
**COMMAND.COM runs perfectly on ours — the BDOS call sequence is BYTE-IDENTICAL to stock for all 18
calls** (STROUT banner @ $C284, FOPEN, STROUT `Current date is` @ $D2B3, GDATE, CONOUT `Sun 84-01-01`,
STROUT `Enter new date:` @ $D2D3, BUFIN). Same C/A/B/DE/HL/ret on both. So the bug is NOT in COMMAND.COM
or the BDOS interface — it is squarely in OUR relocated resident kernel's console I/O. TWO distinct bugs:
- **Bug B (the spin):** at call n=18 BUFIN (func $0A, read console line), **stock BLOCKS waiting for a
  key (18 calls, done); ours RETURNS immediately**, so COMMAND.COM re-runs the date-prompt loop forever
  (n=19+ = the `Ø>@` garbage scroll). Ours' BUFIN does not wait for input.
- **Bug A (missing strings):** func-9 STROUT (n=1,3,17 — banner / `Current date is` / `Enter new date:`)
  emits **ZERO** chars to CHPUT on ours, while func-2 CONOUT (n=5–16, the date VALUE) DOES render. The
  routes differ: func-2 → CHPUT via our M10 `$5454` veneer (ret=$7934); stock's func-9 → CHPUT via a
  DIFFERENT resident-kernel route (ret=$F392; cf. `$F398→$00A2` in kernel.asm §8.38) that ours never set
  up. So M10 fixed only the func-2 route; func-9's output route is unrelocated/broken on ours.
LEADING HYPOTHESIS (verify falsify-first): the resident kernel's func-9 char-output vector (~$F392/$F398)
is not initialised on ours, so STROUT chars are dropped. Bug B (BUFIN) is likely the same class — a
console-INPUT primitive (CHGET/keyboard-status) route not set up — TO BE PINNED.

### What this session PROVED (2026-06-30 M11, all on test.dsk, direct ground-truth)
- **STOCK reference (screen, settle 16):** rows = `MSX-DOS version 1.03` / `Copyright 1984 by
  Microsoft` / (blank) / `COMMAND version 1.08` / (blank) / `Current date is Sun 84-01-01` /
  `Enter new date: .` (cursor) — then blocks at the date BUFIN. 125 CHPUT calls.
- **OURS (screen, settle 16):** EVERY row is `Ø>@` (`$D8 3E 40`) repeating diagonally/scrolling. The
  sign-on (which DOES render ~settle 12) has scrolled OFF. No COMMAND banner, no date prompt, no `A>`.
  240+ CHPUT calls — an unbounded garbage loop. This is THE blocker, not a cosmetic.
- **CHPUT ($00A2) char-stream fork (callseq, the decisive diff):** n=1..53 char-IDENTICAL on both =
  the sign-on (`\r\nMSX-DOS version 1.03\r\nCopyright 1984 by Microsoft\r\n`). At **n=54 the rendered
  output forks**: STOCK `C=09 STROUT` walking a string at `$C285`, A spelling `\r\nCOMMAND v…`
  (ret=$F392); OURS `C=00/02`, A spelling `Sun 84-01-…` (ret=$7934, our veneer). So stock STROUTs the
  COMMAND banner; ours never does a clean STROUT.
- **Ours reaches COMMAND.COM** — the `--at 0x0100 --arm-check 0x0102==0x05` arm fires on ours (then the
  date/garbage stream follows). So MSXDOS.SYS→COMMAND.COM handoff is NOT the break; COMMAND.COM's
  EXECUTION output is.
- **`$5454` is reached by TWO callers with different ABIs:** the sign-on (ret=$0320, C=$80, A=E=char,
  MSXDOS.SYS loader) and the post-sign-on resident kernel/COMMAND path (ret=$D88A, C=BDOS-fn-number).
  Our veneer treats every entry as "emit E" — correct only for clean C=$02 char calls.
- **BDOS ($0005) call seq is IDENTICAL ours==stock for n=1–18** (callseq --at 0x0100 --log 0x0005):
  STROUT($C284)/FOPEN/STROUT($D2B3)/GDATE/12×CONOUT/STROUT($D2D3)/BUFIN — all C/A/B/DE/HL/ret match.
  First divergence is n=18 BUFIN: stock blocks, ours continues. COMMAND.COM is NOT the problem.
- **func-2 CONOUT renders, func-9 STROUT does NOT** (CHPUT route ret=$7934 vs $F392). Two output routes
  to CHPUT in the resident kernel; M10 fixed only the func-2 one.

## Settled facts — DO NOT re-litigate or re-probe
- COMMAND.COM **loads AND reaches $0100** (handoff works); `$47B2` return contract done; `$0005`=`JP
  $D606` identical; `$F338`=0 DOS-handoff fix; GDATE @ `$553C` returns 1984-01-01 default; date path is
  byte-identical at BDOS level (n=1–18, no poke). (All prior COMMAND.COM-load / FOPEN-subset / date
  facts hold.)
- **M10 (still true, but PARTIAL):** `conout_body` ($7922) takes the char from **E** (the `$5454`
  contract), not A. The sign-on renders real ASCII because of this. DO NOT revert to reading A.
- **The sign-on (n=1–53) renders byte-correct on ours** (both reach CHPUT with identical chars).
- **STOCK's real boot = sign-on → `COMMAND version 1.08` → `Current date is Sun 84-01-01` →
  `Enter new date:` → blocks at BUFIN.** (Confirmed by screen; reconciles the old STATE date-prompt
  claim WITH the CHPUT "COMMAND v" — COMMAND.COM prints BOTH, banner first.)

## Dead ends / refuted — do NOT re-walk
- **"The post-sign-on `Ø>@` spam is a benign headless idle-loop artifact / just date-prompt cosmetics"**
  — REFUTED 2026-06-30 M11. It is an INFINITE garbage loop that scrolls away the sign-on and prevents
  ANY progress to COMMAND.COM's banner / date prompt / `A>`. It is THE current blocker.
- **"A clean visible `A>` just needs a keystroke injected past the date BUFIN"** — REFUTED (premature):
  ours never even renders `COMMAND version 1.08` or the date prompt; it loops on garbage long before
  any BUFIN. Input injection is irrelevant until the func-9 STROUT output is fixed.
- **"func-9 STROUT garbage is a page-0-swap clobbering the string read"** — REFUTED 2026-06-30 M11.1.
  The BDOS DE pointers are IDENTICAL ours==stock; func-9 emits 0 chars (not garbage from a bad read).
  The bug is the OUTPUT route (func-9's resident-kernel CONOUT vector), not the string read.
- **"conout_body should read the char from A"** — WRONG (that WAS the M10 bug). Contract is E.
- (Retained) older date-path dead ends: SDATE-is-next-blocker, FOPEN-return-value, register-only $0005
  intercept, M6 work-area pre-build, "skips MSXDOS.SYS init", "+2 clusters", "_GDATE is a clock bug",
  "init date cells alone", "the $80 render is a CHPUT-internal IX/IY/page-0 data divergence". All dead.

## Next action — pin Bug A (func-9 output route) & Bug B (BUFIN block), falsify-first, THEN spec
COMMAND.COM is innocent (BDOS seq identical). Two relocated-kernel console-I/O bugs to fix:
1. **Bug A — verify the func-9 char-output route is unset on ours (falsify-first).** Trace func-9's
   per-char emit on ours vs stock from the n=1 STROUT (banner, caller ret=$C23B, call site ~$C238):
   where do func-9's chars go on ours? Compare the resident-kernel CONOUT vector (~$F392/$F398, the
   route stock's func-9 uses) ours vs stock — is it initialised on ours? `capture --at 0xC238 --nth 1
   --mem 0xF390:0x10` (and trace func-9 internals). Expected: stock's $F39x route reaches CHPUT; ours'
   is wrong/empty so STROUT chars are dropped.
2. **Bug B — characterise why ours' BUFIN (func $0A) returns instead of blocking.** Trace BUFIN
   (n=18, caller ret=$CD6C) internals ours vs stock: stock loops on CHGET/keyboard; ours falls
   straight through. Likely the same class as Bug A — a console-INPUT primitive route not relocated.
   (Note: even fixed, the GOAL's visible `A>` will require INJECTING a keystroke past the date BUFIN —
   stock blocks there too. Key injection is step 3 of the eventual demo, AFTER A+B.)
3. **Spec the fix(es)** (per [[spec-before-implementation]]) before editing ROM — net-zero,
   BIOS-agnostic. Likely: initialise/relocate the resident-kernel console I/O vectors during our init
   the way stock's MSXDOS.SYS does. Decide shape only after 1–2 pin the exact vector(s).

**One-command repros for the next session (test.dsk):**
- The two bugs, at the interface: `python3 probes/disk/disk_probe_diff.py callseq --at 0x0100 --log
  0x0005 --maxhits 50 --diska ~/Documents/msx/msx/disks/test.dsk` → n=1–18 IDENTICAL (COMMAND.COM ok);
  n=18 BUFIN: stock blocks, ours spins (n=19+ garbage). func-9 STROUT @ n=1/3/17.
- The blocker, visually: `… screen --machine both --settle 16 …` → STOCK = COMMAND+date prompt; OURS =
  `Ø>@` loop. (Ours' sign-on still renders early: `screen --machine ours --settle 12`.)
- Output-route fork: `… callseq --at 0x00A2 --arm-cond "1" --log 0x00A2 --maxhits 240 …` → func-2
  chars reach CHPUT via ret=$7934 (ours, M10 veneer); stock's func-9 via ret=$F392.

## Method guardrails (DURABLE — keep these when you overwrite this file)
Endorsed 2026-06-27 after a retrospective found ~half the Tier-2 reframes came from
premature/misaligned conclusions, not hard bugs. See [[harness-first-investigation-mo]].
1. **Anchor + alignment.** Every differential capture is anchored on a SHARED logical event; PROVE
   both sides are at the same logical point before trusting a diff. (M11 win: the CHPUT stream is
   char-identical n=1–53, proving alignment, so the n=54 fork is REAL — and direct `screen` caught what
   40 calls of byte-identical BDOS trace hid. The M10 thesis was over-rosy precisely because it trusted
   a transient settle-12 render instead of observing the steady state.)
2. **Falsify first.** Step 1 of every milestone = the cheapest disproving experiment.
3. **Gate characterisation behind #2.** Don't map a full path until the cheap experiment confirms it.
4. **Right tool per question.** Settled facts → host unit-tests (`make unit-test`, no emulator);
   emulator only for emulator-dependent questions. **Observe the SIDE EFFECT directly** — `screen`
   (steady state, not a lucky early frame) is the arbiter for "what renders".
5. **Terse logging.** Full prose queue entry only for hard-stop forks; routine calls get a one-liner.

## Tooling — use the ONE harness, don't write a 58th probe
**`probes/disk/disk_probe_diff.py`** (on `omsx_session.py`) — the parameterized differential probe.
Modes: `callseq` (call-seq divergence + `--poke/--poke-reg`; prints the longer side's TAIL when one
blocks; logs `A`/`DE`/`B`/`ret`), `capture` (alignment-guarded regs+mem diff at the Nth occurrence),
`trace` (per-instruction PC fork + `--resync` + `--window`; `--regdump REG` = aligned-PC register
divergence walk), **`screen`** (renders the VDP text screen from VRAM — the arbiter that caught both
the M10 `$80` bug and the M11 garbage loop; `--machine ours|stock|both`), and **`iowrite`** (VDP port
byte-stream). **Extend this, don't fork a script.** It copies the DOS disk to tmp (mutation-safe) and
bakes in the alignment guard. The 57 legacy `disk_probe_dosboot_*.py` were pruned 2026-06-30 (in git
history if needed for provenance).

## Invariants for any change
- Tier-1 green: `make unit-test` 19/19; DSKIO/BLOAD/FILES == CF-3300.
- Net-zero: `disk.rom` == 16384 B; no canonical-address shifts.
- Probe machine = Philips_VG_8020 for bload-landmark; FILES runs on C-BIOS_MSX1_EU_BASIC_DISK.
- Clean-room: derive from DPB / public contracts / our own stubs; never copy stock bytes.
- Working mode = autonomous-span + [tier2-review-queue.md](tier2-review-queue.md); hard-stop
  on forks/irreversible/unresolvable.
