<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 STATE — resume here first

**This file is OVERWRITTEN, not appended.** It is the O(1) "where are we" board so a
new session doesn't have to re-read the 580-line audit log + do git archaeology.
History/provenance lives in [tier2-review-queue.md](tier2-review-queue.md); detail
specs are the `tier2-*.md` docs. Read this, then the one doc the next-action names.

_Last updated: 2026-06-30 (RENDER BLOCKER SOLVED + FIXED + COMMITTED. The `$80` garbage was a
register-contract bug in our `$5454` CONOUT veneer: `conout_body` read the char from A, but the
`$5454` contract passes it in **E** (the relocated kernel sets E=char, A=$00). Early MSXDOS.SYS
sign-on passes char in BOTH A+E, which hid the bug. Fix = `ld a,e` (net-zero). Ours now renders real
ASCII: `MSX-DOS version 1.03` / `Copyright 1984 by Microsoft` / `Sun 84-01-01` + boot logo. Tier-1
19/19. Remaining = date-prompt residuals (`@`, missing `Current date is`/`Enter new date:`) + the
headless idle-loop spam; a clean *visible* A> likely needs a keystroke past the date BUFIN.).
Update the date + sections whenever state changes._

---

## Goal
Boot MSX-DOS to the `A>` prompt under zerobas-disk (Tier-2) **without regressing
Tier-1** (disk-BASIC / BLOAD / FILES) and while staying a **BIOS-agnostic replacement
disk ROM** (works on CF-3300, C-BIOS, any standards MSX1). "Reached `A>`" means a
**visible** `A>` on screen + accepts a command — not just the right BDOS call sequence.

## Live thesis (2026-06-30: RENDER BLOCKER SOLVED — real ASCII renders; residuals are date-prompt + headless)
The `$80`-garbage render was **a register-contract bug in our `$5454` CONOUT veneer**, now FIXED and
committed. `conout_body` ($7922) read the output char from **A**, but the `$5454` CONOUT contract
passes the char in **E**. The relocated MSX-DOS kernel's per-char console output (caller `$D88A`)
sets E=char and leaves **A=$00**, so ours emitted `$00`/garbage for every COMMAND.COM-phase glyph.
The EARLY MSXDOS.SYS sign-on (caller `$0320`) passes the char in **both A and E**, so the old A-read
worked there and HID the bug — exactly the "early works, COMMAND fails" discriminator. Fix = `ld a,e`
at conout_body entry (net-zero: 16384 B, free-tail pad, no canonical shift). **Ours now renders real
ASCII**: `MSX-DOS version 1.03` / `Copyright 1984 by Microsoft` / `Sun 84-01-01` + the boot logo.

### What this session PROVED (2026-06-30, all on test.dsk)
- **The prior thesis was WRONG** ("char correct at CHPUT entry, corrupted to `$80` by an identical-PC
  data divergence inside CHPUT"). That rested on `capture --at 0x00A2 --nth 5` showing A=correct —
  but nth=5 is the EARLY MSXDOS.SYS banner (which always worked), NOT a COMMAND-phase glyph. The
  alignment gap flagged by guardrail #1. The real divergence is UPSTREAM of CHPUT.
- **The char reaches our veneer in E, not A** (proven single-machine, clean — the decisive evidence):
  `callseq --log 0x7922` (conout_body entry, A now logged) on ours shows EVERY kernel call (ret=`$D88A`)
  with **A=$00** and register **E spelling the text**: n=1–12 E = `53 75 6E 20 38 34 2D 30 31 2D 30 31`
  = "Sun 84-01-01"; later E = `41 3E` = "A>". The EARLY sign-on (`--at 0x5454 --arm-cond 1`, ret=`$0320`)
  has A=char AND E=char (`0D 0A 4D 53 58…` = "\r\nMSX-DOS version 1.03"). So **E is the register common
  to BOTH callers** — `conout_body` reading A printed A=$00 (kernel) instead of E=char.
- **The fix renders** (`screen --machine ours --settle 12`): ROW15 `MSX-DOS version 1.03`, ROW16
  `Copyright 1984 by Microsoft`, ROW17 `Sun 84-01-01@`, plus the boot logo (`MSX system version 1.0` /
  `Copyright 1983 by Microsoft`). No `$80` tiles anywhere. Tier-1 `make unit-test` 19/19 green.
- **Tooling note:** the divergence was found by EXTENDING the one harness — `trace --regdump A` (the
  aligned-PC register-divergence walk, since PCs stay aligned through the shared CHPUT code so the
  fork logic is blind to a data divergence) + an `A=` field on the callseq logger. Not a 58th probe.

## Settled facts — DO NOT re-litigate or re-probe
- COMMAND.COM loads correctly; `$47B2` return contract done; `$0005`=`JP $D606` identical;
  `$F338`=0 DOS-handoff fix lands ours on the stock path; GDATE handler @ `$553C` returns the
  clock-less 1984-01-01 default; `$F30D=01/$F30E=00` format defaults set. (All prior settled facts
  about COMMAND.COM load / FOPEN-subset / date VALUE-is-the-gate still hold.)
- **Date path is DONE at the BDOS level** (n=1–18 byte-identical, no poke; SDATE returns).
- **CONOUT NOW RENDERS** ✅ (M10 fix): `conout_body` takes the char from **E** (the `$5454` contract),
  not A. Real ASCII renders (banner/date/logo). Re-UPGRADED from the ⚠ downgrade.
- **The `$5454` CONOUT char register is E, not A.** Both callers (early sign-on `$0320`, kernel
  `$D88A`) put the char in E; only the early one redundantly also sets A. DO NOT revert to reading A.
- **SDATE ($2B) is NOT a blocker** — it is called past BUFIN, returns, ours proceeds. (Refutes the
  prior next-action hypothesis that SDATE would be the next collision.)

## Dead ends / refuted — do NOT re-walk
- **"The `$80` render is a CHPUT-internal data divergence (IX/IY/page-0 map) at identical PC"** —
  REFUTED 2026-06-30. It was an UPSTREAM register-contract bug: our veneer read the char from A; the
  contract is E. Do NOT chase IX/IY/page-0 reads inside CHPUT for the render bug; do NOT re-run the
  `trace --resync` "PC-equivalent data divergence" analysis — the data differs because A≠E at the veneer.
- **"`conout_body` should read the char from A"** — WRONG (that WAS the bug). The contract is E.
- "SDATE ($2B) is the next blocker past BUFIN" — REFUTED 2026-06-30 (SDATE returns; ours proceeds).
- "Ours not-blocking at BUFIN is a bug" — NO, it's the headless no-keyboard artifact; stock blocks
  only because the emulator has no key to give. Both run the same kernel BUFIN.
- (Retained) the older date-path dead ends: FOPEN-return-value, register-only $0005 intercept, M6
  work-area pre-build, "skips MSXDOS.SYS init", "+2 clusters", "_GDATE is a clock bug", "init date
  cells alone". All still dead.

## Next action — NEW SLICE: date-prompt residuals + a clean *visible* A> (the render bug is fixed)
The `$80` blocker is gone; real ASCII renders. What's left between here and a clean *visible* `A>`:
1. **Characterise the date-prompt residuals (falsify-first, now that text renders).** At `settle 12`
   ours shows `Sun 84-01-01@` but stock shows `Current date is Sun 84-01-01` then `Enter new date:`.
   So ours is (a) missing the `Current date is ` prefix, (b) printing a stray `@` ($40), (c) not
   showing `Enter new date:`. The `@`/`$D8` come from kernel calls with A=$80/$0C, BC=$0000, DE=a
   POINTER (E = pointer low byte, NOT a char) — i.e. NOT every `$5454` call is a printable-char call.
   Open question: does the kernel gate those (a flag/Cy our veneer ignores), or are they the headless
   BUFIN-garbage path? Probe: `callseq --log 0x7922` (E + A + BC + the caller) across the date window,
   and compare the char STREAM to stock's CONOUT (`--log 0x0005 C=02` decode) for the same logical span.
2. **Get a clean visible `A>` (likely needs input past BUFIN).** Ours races through the date BUFIN
   headlessly (returns empty), so it never shows `Enter new date:` and floods the screen with idle
   spam. Inject a keystroke (CR) at the date BUFIN so ours blocks/advances like stock, then COMMAND.COM
   + `A>` should render cleanly. See [[openmsx-probing-toolbox]] for input injection; consider a
   `screen` capture timed right after COMMAND's banner.
3. **Spec any ROM change** (per [[spec-before-implementation]]) before editing; net-zero, BIOS-agnostic.

KEY: the render fix likely UNBLOCKS the visible-`A>` milestone; the remaining work is the date-prompt
correctness (the `@`/prefix/`Enter new date:`) and demonstrating `A>` with real input. The idle-loop
spam at `settle≥14` is the known headless BUFIN artifact ([[tier2-storms-are-downstream]]), not a bug.

**One-command repros for the next session (test.dsk):**
- Banner renders: `python3 probes/disk/disk_probe_diff.py screen --machine ours --settle 12 --diska
  ~/Documents/msx/msx/disks/test.dsk` → `MSX-DOS version 1.03` / `Sun 84-01-01@` + boot logo (real ASCII).
- The char-in-E proof: `python3 probes/disk/disk_probe_diff.py callseq --at 0x0100 --log 0x7922
  --maxhits 40 --diska …` → ours' conout_body calls (ret=$D88A) have A=00, E spells "Sun 84-01-01"/"A>".
- Early sign-on (A+E both): `… callseq --at 0x5454 --arm-cond "1" --log 0x7922 --maxhits 24 …`.

## Method guardrails (DURABLE — keep these when you overwrite this file)
Endorsed 2026-06-27 after a retrospective found ~half the Tier-2 reframes came from
premature/misaligned conclusions, not hard bugs. See [[harness-first-investigation-mo]].
1. **Anchor + alignment.** Every differential capture is anchored on a SHARED logical
   event; PROVE both sides are at the same logical point before trusting a diff. (This session:
   the `$00A2` trace was occurrence-aligned but NOT char-aligned — exactly the trap. The aligned
   `capture` was trustworthy only because A matched, confirming the same char.)
2. **Falsify first.** Step 1 of every milestone = the cheapest disproving experiment.
3. **Gate characterisation behind #2.** Don't map a full path until the cheap experiment confirms
   it's real.
4. **Right tool per question.** Settled facts → host unit-tests (`make unit-test`, no emulator);
   emulator only for genuinely emulator-dependent questions. **Observe outputs directly** — the
   `screen` mode (VRAM render) caught a garbage-output bug that 40 calls of byte-identical BDOS
   trace completely hid. Verify the SIDE EFFECT, not just the call.
5. **Terse logging.** Full prose queue entry only for hard-stop forks; routine calls get a one-liner.

## Tooling — use the ONE harness, don't write a 58th probe
**`probes/disk/disk_probe_diff.py`** (built on `omsx_session.py`) — the parameterized differential
probe. Modes: `callseq` (call-sequence divergence + `--poke/--poke-reg` falsify-first override; NOW
also prints the longer side's TAIL when one side blocks/diverges), `capture` (alignment-guarded
regs+mem diff at the Nth occurrence), `trace` (per-instruction PC fork + `--resync`, NOW with
`--window` to bridge long inter-slot detours), **`screen`** (renders the VDP text screen from the
VRAM name table — the direct-observation tool that caught the `$80` render bug; `--machine
ours|stock|both`, rows + HEX + banner-locate scan), and **`iowrite`** (logs the byte stream written
to a VDP/I-O port `$98` data + `$99` addr — the DATA-level tool that proved ours writes `$80`/clears
while stock writes text; shows the writer PCs and addresses). NEW (M10): **`trace --regdump REG`** =
aligned-PC register-divergence walk (when both sides run the SAME code so PCs never fork, it finds the
first step where REG diverges — the data divergence the fork logic is blind to); and the **callseq
logger now records `A=`** (so `--log 0x7922`/`0x00A2` shows the char register). **Extend this, don't fork a script.**
It copies the DOS disk to tmp (mutation-safe) and bakes in the alignment guard. **Extend this, don't
fork a new script.** The 57 legacy `disk_probe_dosboot_*.py` stay for provenance.

## Invariants for any change
- Tier-1 green: `make unit-test` 19/19; DSKIO/BLOAD/FILES == CF-3300.
- Net-zero: `disk.rom` == 16384 B; no canonical-address shifts.
- Probe machine = Philips_VG_8020 for bload-landmark; FILES runs on C-BIOS_MSX1_EU_BASIC_DISK.
- Clean-room: derive from DPB / public contracts / our own stubs; never copy stock bytes.
- Working mode = autonomous-span + [tier2-review-queue.md](tier2-review-queue.md); hard-stop
  on forks/irreversible/unresolvable.
