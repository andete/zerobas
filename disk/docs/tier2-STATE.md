<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 STATE — resume here first

**This file is OVERWRITTEN, not appended.** It is the O(1) "where are we" board so a
new session doesn't have to re-read the 580-line audit log + do git archaeology.
History/provenance lives in [tier2-review-queue.md](tier2-review-queue.md); detail
specs are the `tier2-*.md` docs. Read this, then the one doc the next-action names.

_Last updated: 2026-07-01 (M13 — CONIN Option A IMPLEMENTED, user go-ahead. The M12 root
cause — CONIN falling through into CONOUT, the infinite `D8 19 3E 40 0A` garbage spin — is FIXED.
A `jp conin_line_body` veneer now sits at the pinned CALL target `$50E0` ([kernel.asm](../kernel.asm)),
consuming our own `$00` dead region (net-zero, `disk.rom` still 16384 B); `conin_line_body`
([runtime.asm](../runtime.asm)) is a clean-room reimplementation of the published BDOS func-`$0A`
buffered-line read: per-char inter-slot CHGET (`$009F`) via the existing `pg0_mainrom_in/out` bridge,
CR ends the line, BS edits back one char, else echo via the reused `conout_body` + store; result lives
in the buffer (`[DE+1]`=count), matching the pinned no-return-register contract. `make unit-test` 19/19.
**VALIDATED:** `callseq --log 0x009F` now matches stock call-for-call (1 call idle; 10 calls with a
9-char+CR keystroke injection, was stock-1/ours-0 before); `screen --machine both --settle 16` shows
ours holds a STABLE frame (blocked at CHGET) instead of scrolling forever. **NEW OPEN ITEM (M14, not
started):** even with an injected keystroke driving CHGET through the date prompt, ours never renders
`COMMAND version 1.08` / `Current date is ...` / `Enter new date: ` as separate lines — and this is
reproducible in the NO-KEYS baseline too (i.e. BEFORE any CONIN call fires), so it predates and is
independent of the M13 fix; the old infinite spin previously masked it since ours never held a stable
frame to inspect. M14 starts fresh on this new symptom (COMMAND.COM banner/prompt rendering — a CONOUT/
newline/scroll question, not CONIN). Full M12 root-cause narrative retained below for context/citation.
Logged: [tier2-review-queue.md](tier2-review-queue.md) M13.)_

## Goal
Boot MSX-DOS to the `A>` prompt under zerobas-disk (Tier-2) **without regressing
Tier-1** (disk-BASIC / BLOAD / FILES) and while staying a **BIOS-agnostic replacement
disk ROM** (works on CF-3300, C-BIOS, any standards MSX1). "Reached `A>`" means a
**visible** `A>` on screen + accepts a command — not just the right BDOS call sequence.

## Live thesis (M14, OPEN — not yet investigated)
**Symptom:** ours never shows `COMMAND version 1.08` / `Current date is Sun 84-01-01` /
`Enter new date: ` as distinct lines the way stock does — `screen --machine ours --settle 16`
(no keys) instead shows the BASIC power-on banner (`MSX system version 1.0` / `Copyright 1983`)
still on screen, then a compressed `Sun 84-01-01` with no visible prompt label, several rows
lower than stock's layout. This is BEFORE any console-input call (CONIN untouched at this
point), so it is a CONOUT/newline/scroll-region question, not a CONIN regression from M13.
**Not yet characterised** — no probes run on this specific symptom yet; start falsify-first
(§ Method guardrails) rather than assuming a cause. Candidate angles (unconfirmed): a missing
screen-clear before MSXDOS.SYS sign-on, a CR/LF handling gap in `conout_body`'s caller chain,
or COMMAND.COM printing to a stale cursor position left by the BASIC boot banner.

## Settled facts — DO NOT re-litigate or re-probe
- COMMAND.COM **loads AND reaches $0100** (handoff works); `$47B2` return contract done; `$0005`=`JP
  $D606` identical; `$F338`=0 DOS-handoff fix; GDATE @ `$553C` returns 1984-01-01 default; date path is
  byte-identical at BDOS level (n=1–18, no poke). (All prior COMMAND.COM-load / FOPEN-subset / date
  facts hold.)
- **M10 (still true):** `conout_body` ($5454 veneer) takes the char from **E** (the `$5454` contract),
  not A. The sign-on renders real ASCII because of this. DO NOT revert to reading A.
- **M13 (new, 2026-07-01): CONIN is implemented and working at the BDOS/CHGET level.** The `$50E0`
  veneer (`conin_line_body`) reaches CHGET once per char, matches stock's call count exactly (idle:
  1 call; with keys: N-chars+1), and the old infinite garbage spin is GONE — ours now holds a STABLE
  screen frame while blocked at CHGET, same as stock. Keystrokes echo correctly (reuses `conout_body`).
  DO NOT re-implement or second-guess this veneer without a concrete new probe result — the CHGET-count
  and no-spin evidence is decisive.
- **The sign-on (n=1–53) renders byte-correct on ours** (both reach CHPUT with identical chars).
- **STOCK's real boot = sign-on → `COMMAND version 1.08` → `Current date is Sun 84-01-01` →
  `Enter new date:` → blocks at BUFIN, now matched by ours at the CHGET level (M13).**

## Dead ends / refuted — do NOT re-walk
- **"There are TWO independent console-I/O bugs (func-9 output + BUFIN block)"** — REFUTED M12.
  ONE root cause (the missing CONIN line routine at `$50E0`, falling into `$5454` CONOUT) explained
  both; M13 fixed it.
- **"func-9 STROUT emits ZERO chars / its `$F398` CONOUT vector is unset on ours"** — REFUTED M12.
- **"The `Ø>@`/`D8 19 3E 40 0A` spam is a benign idle artifact / date-prompt cosmetics"** — REFUTED M11;
  root-caused M12 (CONIN→CONOUT fall-through); FIXED M13 (spin no longer occurs).
- **"conout_body should read the char from A"** — WRONG (that WAS the M10 bug). CONOUT contract is E.
- **"func-9 STROUT garbage is a page-0-swap clobbering the string read"** — REFUTED M11.1.
- **"A-2/int_h (keyboard interrupt service) is the CONIN blocker"** — REFUTED M12/M13: A-3/A-5 already
  chains KEYINT correctly; M13's keystroke-injection probes prove keys ARE received during CHGET.
- (Retained) older date-path dead ends: SDATE-is-next-blocker, FOPEN-return-value, register-only $0005
  intercept, M6 work-area pre-build, "skips MSXDOS.SYS init", "+2 clusters", "_GDATE is a clock bug",
  "init date cells alone", "the $80 render is a CHPUT-internal IX/IY/page-0 data divergence". All dead.

## Next action — M14: characterise the missing COMMAND.COM banner/prompt lines
**M13 (CONIN) is DONE and validated — do not re-open without new evidence.** The next blocker to
`A>` is a NEW symptom, not yet probed:
1. **Falsify first (§ Method guardrails).** Cheapest disproving experiment: `screen --machine ours
   --settle N` at increasing settle values from N=2 upward, to see WHEN the banner text appears/
   disappears — is it ever rendered correctly and then overwritten/scrolled, or never rendered at all?
2. **Anchor + align:** use `callseq`/`capture` anchored on the CONOUT calls (`$5454`/`conout_body`)
   around the `COMMAND version` / `Current date is` / `Enter new date:` strings specifically — confirm
   ours reaches those CHPUT calls with the SAME chars as stock (like the M10/M12 sign-on check), rather
   than assuming the veneer is broken.
3. **Right tool:** `screen` is the arbiter (per the guardrails — it caught what byte-identical BDOS
   trace hid before). Don't build a new probe script; extend `disk_probe_diff.py` if a new mode is
   needed.
4. Once characterised, THEN drive to the visible `A>` goal (inject a full command + Enter once the
   prompt itself renders correctly).

**One-command repros for the next session (test.dsk):**
- M13 regression check (should still pass): `python3 probes/disk/disk_probe_diff.py callseq --at 0x0100
  --log 0x009F --maxhits 12 --diska ~/Documents/msx/msx/disks/test.dsk` → both sides 1 call.
- M14 starting point: `python3 probes/disk/disk_probe_diff.py screen --machine both --settle 16
  --diska ~/Documents/msx/msx/disks/test.dsk` → compare stock's clean `Enter new date: .` against
  ours' compressed/offset banner (no keys needed to see the symptom).
- With keystrokes: `python3 probes/disk/disk_probe_diff.py screen --machine ours --settle 25 --keys
  $'12-25-99\r' --keys-at 8 --diska ~/Documents/msx/msx/disks/test.dsk` → date echoes inline but no
  `A>` yet.

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
blocks; logs `A`/`DE`/`B`/`ret`; `--keys/--keys-at` inject emulated keystrokes), `capture` (alignment-
guarded regs+mem diff at the Nth occurrence), `trace` (per-instruction PC fork + `--resync` + `--window`;
`--regdump REG` = aligned-PC register divergence walk; clean-room disasm guard: decodes only our own
code, PC>=0x4000, and auto-suppresses on the STOCK machine), **`screen`** (renders the VDP text screen
from VRAM — the arbiter that caught the M10 `$80` bug, the M11 garbage loop, and the M13 no-spin
confirmation; `--machine ours|stock|both`), and **`iowrite`** (VDP port byte-stream). **Extend this,
don't fork a script.** It copies the DOS disk to tmp (mutation-safe) and bakes in the alignment guard.
The 57 legacy `disk_probe_dosboot_*.py` were pruned 2026-06-30 (in git history if needed for provenance).

## Invariants for any change
- Tier-1 green: `make unit-test` 19/19; DSKIO/BLOAD/FILES == CF-3300.
- Net-zero: `disk.rom` == 16384 B; no canonical-address shifts.
- Probe machine = Philips_VG_8020 for bload-landmark; FILES runs on C-BIOS_MSX1_EU_BASIC_DISK.
- Clean-room: derive from DPB / public contracts / our own stubs; never copy stock bytes.
- Working mode = autonomous-span + [tier2-review-queue.md](tier2-review-queue.md); hard-stop
  on forks/irreversible/unresolvable.
