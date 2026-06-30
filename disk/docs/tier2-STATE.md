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

## Live thesis (2026-06-30 M11: ours runs COMMAND.COM but its func-9 STROUT output is garbage + loops)
After the byte-identical MSXDOS.SYS sign-on, **ours and stock execute divergent output**. Stock hands
off to COMMAND.COM, which STROUTs (BDOS func 9) `COMMAND version 1.08`, then `Current date is
Sun 84-01-01`, then `Enter new date:`, then blocks at the date BUFIN. Ours ALSO reaches COMMAND.COM
($0100 with COMMAND.COM loaded — handoff confirmed) but its console output is broken: only the func-2
date VALUE chars come through, every func-9 STROUT string comes out as garbage, and ours falls into an
**infinite loop** emitting `Ø>@` (`$D8 3E 40`) + CR/LF that scrolls the whole screen forever. Ours
never shows `COMMAND version 1.08`, the date prompt, or `A>`. **The render bug class is now: COMMAND.COM's
func-9 STROUT path (string output) is broken on ours; func-2 (single-char CONOUT) works.** Likely root:
something in our `$5454`/`conout_body` routing (page-0 main-ROM swap during CONOUT) corrupts func-9's
string walk so it never terminates on `$`, or DE/the read page is wrong — TO BE PINNED (falsify-first).

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
- **"conout_body should read the char from A"** — WRONG (that WAS the M10 bug). Contract is E.
- (Retained) older date-path dead ends: SDATE-is-next-blocker, FOPEN-return-value, register-only $0005
  intercept, M6 work-area pre-build, "skips MSXDOS.SYS init", "+2 clusters", "_GDATE is a clock bug",
  "init date cells alone", "the $80 render is a CHPUT-internal IX/IY/page-0 data divergence". All dead.

## Next action — pin the func-9 STROUT divergence (falsify-first), THEN spec a fix
The blocker is COMMAND.COM's BDOS func-9 (STROUT, string output) producing garbage + looping on ours,
while func-2 (single-char CONOUT) works. Steps:
1. **Falsify-first: is func-9 itself broken, or is it func-2's page-0 swap corrupting func-9's string
   walk?** Cheapest disproving experiment — capture a SINGLE func-9 STROUT on ours vs stock for the
   SAME string (e.g. `COMMAND version 1.08` at `$C285`): anchor on COMMAND.COM $0100, watch the func-9
   handler entry, dump DE (string ptr) + the bytes it reads + the per-char CONOUT it emits. If ours
   reads the right string bytes but emits garbage → the CONOUT/$5454 page swap is clobbering the read
   (DE points into page 0/TPA, which our veneer pages OUT to map the main ROM). If ours reads garbage
   from the start → DE/string-setup is wrong (relocation/work-area).
2. **Characterise the infinite loop** — what makes it never terminate? (func-9 never hits `$`? a CONOUT
   re-entrancy? the page swap leaving page 0 = main ROM so the string walk reads ROM not the string?)
   Watch where the `Ø>@` bytes are READ from.
3. **Spec the fix** (per [[spec-before-implementation]]) before editing ROM — net-zero, BIOS-agnostic.
   Candidate shapes: make `conout_body` preserve the TPA/page-0 mapping the kernel string-walk relies
   on, or route func-9 differently. Decide only after step 1 pins read-vs-emit.

**One-command repros for the next session (test.dsk):**
- The blocker, visually: `python3 probes/disk/disk_probe_diff.py screen --machine both --settle 16
  --diska ~/Documents/msx/msx/disks/test.dsk` → STOCK shows COMMAND+date prompt; OURS = `Ø>@` loop.
- The fork: `… callseq --at 0x00A2 --arm-cond "1" --log 0x00A2 --maxhits 240 --diska …` → n=1–53
  identical sign-on; n=54 stock=`C=09 STROUT "COMMAND v…"`, ours=`C=00/02 "Sun 84-01-…"`.
- Sign-on still renders on ours: `screen --machine ours --settle 12` (banner visible before scroll-off).

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
