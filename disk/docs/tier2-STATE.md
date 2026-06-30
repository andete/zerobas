<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 STATE — resume here first

**This file is OVERWRITTEN, not appended.** It is the O(1) "where are we" board so a
new session doesn't have to re-read the 580-line audit log + do git archaeology.
History/provenance lives in [tier2-review-queue.md](tier2-review-queue.md); detail
specs are the `tier2-*.md` docs. Read this, then the one doc the next-action names.

_Last updated: 2026-06-30 (M12 UNIFY — the M11 "two-bug" model (Bug A func-9 output + Bug B BUFIN)
COLLAPSES into ONE root cause: **the kernel's `$544E` CONIN entry has no veneer on ours — it is `$00`
padding that falls through into `$5454` (`jp conout_body`, CONOUT).** So a console-INPUT request is
serviced by the console-OUTPUT veneer: it emits one garbage char (E = stale pointer-low) and RETURNS
immediately, never calling CHGET, never blocking. COMMAND.COM's prompt loop then spins forever, and the
`D8 19 3E 40 0A` garbage IS conout_body mis-invoked by that spin. DECISIVE PROOF: **CHGET (`$009F`) is
called 1× on stock (it blocks there), 0× on ours.** "func-9 emits zero chars / `$F398` vector unset"
is REFUTED (regs+sysvars byte-identical at func-9 entry; func-9 output works). A-2/int_h is NOT the
blocker (A-3/A-5 already chains KEYINT; the `$0038` trace fork re-converges = benign). **SCOPE UPDATE
(M12):** the fix is NOT a 1-line `$544E` veneer — the kernel delegates the WHOLE BDOS func-`$0A` line
read to a disk-ROM console routine (entered ~`$50E0`, black-box PC trace), and **our `build/disk.rom` is
`$00` across `$50B7–$5453`** (our artifact) → ours NOP-slides into the `$5454` CONOUT veneer. ABIs
(clean sources): CONOUT→E (M10, black-box); CONIN→A (published CHGET `$009F` contract). **M12b PROVENANCE
CORRECTION:** the first ABI-pin draft read+decoded stock CF-3300 ROM *code* bytes = disassembly-class (✗);
quarantined & re-grounded on clean sources (conclusions unchanged); logged in
[clean-room-audit.md](../../docs/clean-room-audit.md). NEXT = sign-off on
[tier2-conin-spec.md](tier2-conin-spec.md) v2 Option A (clean-room buffered-line veneer from the documented
func-`$0A` contract). **HELD by user: "provenance first" — done; awaiting go-ahead to implement.**)_

---

## Goal
Boot MSX-DOS to the `A>` prompt under zerobas-disk (Tier-2) **without regressing
Tier-1** (disk-BASIC / BLOAD / FILES) and while staying a **BIOS-agnostic replacement
disk ROM** (works on CF-3300, C-BIOS, any standards MSX1). "Reached `A>`" means a
**visible** `A>` on screen + accepts a command — not just the right BDOS call sequence.

## Live thesis (2026-06-30 M12: ONE root cause — the `$544E` CONIN veneer is missing, falls into CONOUT)
**The relocated kernel has two adjacent console entries: `$5454` CONOUT (output) and `$544E` CONIN
(input), 6 bytes apart in the shared ASCII-kernel block.** We veneered `$5454` (`jp conout_body` →
inter-slot CHPUT `$00A2`; M8/M10) but **NEVER implemented `$544E`** — it is `$00` (NOP) padding from
`ds $5454 - $, $00`. So COMMAND.COM's BUFIN (`CALL $544E` to read a console line) executes 6 NOPs and
**falls through into `$5454` = CONOUT**: it emits one garbage char (`ld a,e`, E = stale buffer-pointer
low byte) and RETURNS immediately — never CHGET, never blocks. COMMAND.COM's prompt loop then spins
forever; the `D8 19 3E 40 0A` screen garbage IS `conout_body` mis-invoked by that spin. ONE fault, both
old "bugs": the spin (old Bug B) AND the garbage output (old Bug A) are the same CONIN→CONOUT
fall-through. **Fix = add a `$544E` CONIN veneer (parallel to CONOUT): `pg0_mainrom_in → call $009F
CHGET → pg0_mainrom_out`.** Spec drafted: [tier2-conin-spec.md](tier2-conin-spec.md), awaiting sign-off.

### What this session PROVED (2026-06-30 M12, all on test.dsk, direct ground-truth — `disk_probe_diff.py`)
- **CHGET (`$009F`) called 1× on stock, 0× on ours** (`callseq --log 0x009F`). THE decisive proof:
  ours' BUFIN never reaches console input → returns instead of blocking. (Old "Bug B," now root-caused.)
- **`$544E` has no veneer:** `grep -i '544E\|conin\|CHGET\|009F' disk/*.asm` → nothing; `kernel.asm:50`
  `ds $5454 - $, $00` makes `$544E–$5453` NOP padding before `conout` at `$5454`.
- **func-9 entry is byte-identical ours==stock** (`capture --at 0xC238 --mem 0xF390:0x10`): all regs +
  the `$F390:0x10` sysvar block (incl. `$F398`) match. → REFUTES "func-9 `$F398` CONOUT vector unset."
- **func-9 chars DO reach CHPUT on ours** (wide-window `trace --resync`): the print loop runs
  `$F36B→read→$F368→…→$00A2`; the ret=$7934-vs-$F392 difference RE-CONVERGES = benign relocation, not a
  broken route. (Old "Bug A — func-9 emits zero chars" is REFUTED.)
- **The garbage = E = DE-low from a SPIN, not a string walk** (`callseq --log 0x00A2`): ours cycles
  `D8 19 3E 40 0A` = low bytes of DE `D3D8/D319/D33E/DA40/D30A` re-read in a loop; conout_body has a
  SINGLE caller (ret=$D88A) with char-in-E ABI — func-2 (date "Sun 84-01-01") renders correctly via it
  (entry log n=1–12), THEN ours derails into the spin.
- **A-2/int_h is NOT the blocker:** the `$0038` trace fork (stock `$0C3C` / ours `$DDAE`) RE-CONVERGES =
  benign; A-3/A-5 (`int_h_hiram_tmpl`, runtime.asm:160) already inter-slot-chains the main-BIOS KEYINT,
  so the keyboard scan runs. (Means injected keys WILL be received once CONIN reaches CHGET.)
- **STOCK screen (settle 16):** full boot blocked at `Enter new date: .`. **OURS:** `D8 3E 40` scrolling
  diagonally forever (the spin). Arbiter = `screen --machine both`.
- **BDOS ($0005) seq IDENTICAL n=1–18** then n=18 BUFIN diverges (stock blocks, ours spins) — consistent
  with the CONIN fall-through (COMMAND.COM/BDOS interface is innocent; only the kernel CONIN veneer).

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
- **"There are TWO independent console-I/O bugs (func-9 output + BUFIN block)"** — REFUTED 2026-06-30
  M12. ONE root cause (the missing `$544E` CONIN veneer falling into `$5454` CONOUT) explains both.
- **"func-9 STROUT emits ZERO chars / its `$F398` CONOUT vector is unset on ours"** — REFUTED M12.
  func-9 entry regs + `$F390` sysvars are byte-identical; func-9 chars DO reach CHPUT (the ret=$7934-vs-
  $F392 difference re-converges = benign). func-9 OUTPUT works; the apparent "missing banner" is the
  spin scrolling it off-screen.
- **"The `Ø>@` spam is a benign idle artifact / date-prompt cosmetics"** — REFUTED M11 (still true):
  it is the infinite prompt SPIN; root-caused in M12 to the CONIN fall-through.
- **"conout_body should read the char from A"** — WRONG (that WAS the M10 bug). CONOUT contract is E.
  (CONIN's return-register contract is OPEN — pin it before coding; don't assume, per the M10 lesson.)
- **"func-9 STROUT garbage is a page-0-swap clobbering the string read"** — REFUTED M11.1 (DE ptrs
  identical). The garbage is conout_body emitting E (stale ptr-low) when mis-invoked by CONIN.
- (Retained) older date-path dead ends: SDATE-is-next-blocker, FOPEN-return-value, register-only $0005
  intercept, M6 work-area pre-build, "skips MSXDOS.SYS init", "+2 clusters", "_GDATE is a clock bug",
  "init date cells alone", "the $80 render is a CHPUT-internal IX/IY/page-0 data divergence". All dead.

## Next action — FIRST a paper-trail audit of the M12 span (user-deferred here), THEN CONIN Option A
**GATE (user decision 2026-06-30): run the wider provenance audit BEFORE any CONIN code.** A method
breach was self-caught in M12 (ABI-pin read+decoded stock ROM CODE bytes = disassembly; see
[clean-room-audit.md](../../docs/clean-room-audit.md) incident + [[no-reference-rom-disasm]]). Remediated
in the docs (commit `6482036`), but the user wants assurance nothing else in the M12 span leaned on the
same shortcut before building on it.
1. **Paper-trail audit (next session, FIRST).** Use the brief in
   [clean-room-audit.md](../../docs/clean-room-audit.md) "Brief template — Paper trail." Scope: the M12
   span — the `tier2-*` docs touched this span + the `disk_probe_diff.py` modes used (capture/callseq/
   trace/screen). Confirm: (a) no surviving finding rests on reading reference-ROM bytes; (b) the probe
   is genuinely black-box on RAM/registers/call-targets, not ROM-code reads; (c) the M12b remediation
   actually scrubbed the disassembly-derived restatements. Deliver verdict + any BREAKS. Note: the breach
   text persists in git HISTORY (commit `971fc78`); flag for the public-release gate (history squash).
2. **THEN, if clean → CONIN Option A** (only after the audit passes). See
   [tier2-conin-spec.md](tier2-conin-spec.md) v2. Ground ONLY on clean sources: published CHGET `$009F`
   (char in A) + CHPUT `$00A2` + BDOS func-`$0A` buffer layout; pin the `~$50E0` entry address + register
   contract BLACK-BOX (call-target trace + published func-`$0A` DE=buffer), never by reading the body.
   Shape: `jp conin_line_body` at the entry → free-tail body running the documented buffered-line loop
   (CHGET per char / CR-done / BS-edit / CHPUT-echo / fill `DE` buf, set `buf[1]=count`) via the existing
   `pg0_mainrom_in/out` inter-slot bridge.
3. **Validate:** `callseq --log 0x009F` → ours now 1 call (was 0); `screen --machine ours --settle 16`
   → matches stock (`Enter new date:`, no garbage); `make unit-test` 19/19; `disk.rom` == 16384 B.
4. **Then inject a keystroke** past BUFIN to drive a visible `A>` (GOAL's final step). A-3/A-5 keyboard
   interrupt service is already live, so injected keys should land.

**One-command repros for the next session (test.dsk):**
- THE proof: `python3 probes/disk/disk_probe_diff.py callseq --at 0x0100 --log 0x009F --maxhits 12
  --diska ~/Documents/msx/msx/disks/test.dsk` → STOCK 1 CHGET call (blocks), OURS 0. After the fix, ours
  should reach 1.
- The blocker visually: `… screen --machine both --settle 16 …` → STOCK = COMMAND+date prompt; OURS =
  `D8 3E 40` spin. Where CONIN should be: `… trace --at 0x0100 --anchor 0x0005 --nth 18 --resync
  --window 3000 --steps 9000 …` → stock branches into the disk-ROM console routine (~`$50E0`/`$544E`
  call-targets); ours NOP-slides past (our ROM is `$00` there). (Observe call-targets/PCs only — NOT the
  stock body bytes; see [[no-reference-rom-disasm]].)
- Source of the fault: `grep -i '544E\|conin\|CHGET\|009F' disk/*.asm` → nothing; `kernel.asm:50`
  `ds $5454 - $, $00` leaves `$544E` as NOP padding into `conout` at `$5454`.

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
