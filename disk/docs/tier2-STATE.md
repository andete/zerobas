<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 STATE — resume here first

**This file is OVERWRITTEN, not appended.** It is the O(1) "where are we" board so a
new session doesn't have to re-read the 580-line audit log + do git archaeology.
History/provenance lives in [tier2-review-queue.md](tier2-review-queue.md); detail
specs are the `tier2-*.md` docs. Read this, then the one doc the next-action names.

_Last updated: 2026-06-30 (BIG reframe: date path fully solved — ours reaches the A> command
loop with NO poke. New blocker found by direct screen observation: CONOUT renders every char as
tile $80; the screen is garbage. "Banner byte-identical" was call-verified only, never VRAM-
verified.). Update the date + sections whenever state changes._

---

## Goal
Boot MSX-DOS to the `A>` prompt under zerobas-disk (Tier-2) **without regressing
Tier-1** (disk-BASIC / BLOAD / FILES) and while staying a **BIOS-agnostic replacement
disk ROM** (works on CF-3300, C-BIOS, any standards MSX1). "Reached `A>`" means a
**visible** `A>` on screen + accepts a command — not just the right BDOS call sequence.

## Live thesis (2026-06-30: date path DONE at BDOS level; the remaining blocker is RENDERING)
With the GDATE slice in the ROM, **ours' BDOS call sequence is byte-identical to stock for
n=1–18 with NO poke**, ending at BUFIN (the date-input wait), and **past BUFIN ours reaches the
`A>` command-interpreter idle loop** (SDATE→SELDSK→CURDRV→print `A>`→BUFIN, repeating). So at the
control-flow level ours reaches `A>`. **But the actual screen is garbage**: ours' console output
renders **every printable character as constant tile `$80`** in VRAM (banner, prompts, and `A>`
all invisible). The real ASCII text is **nowhere** in ours' VRAM. So a *visible* `A>` is NOT yet
achieved — the last blocker is a **CONOUT/CHPUT rendering bug** in ours' inter-slot output path.

### What this session PROVED (2026-06-30, all on test.dsk)
- **No-poke convergence through BUFIN** (`callseq --maxhits 40`): ours == stock for n=1–18
  (STROUT/FOPEN/STROUT/GDATE/CONOUT×banner/STROUT/BUFIN). The date prompt is fully solved; the
  prior `--poke-at 0xCDA7` repro is no longer needed.
- **Ours reaches the `A>` command loop** (callseq OURS-only tail, new `--tail` print): n=19,20
  CONOUT (CR LF echo of Enter); **n=21 `$2B` SDATE DE=0101 HL=07C0** (correct 1984-01-01 default)
  → SDATE RETURNS, ours proceeds → **SDATE is NOT the next blocker** (the prior hypothesis is
  REFUTED); n=22 SELDSK, n=23–27 CR LF + CURDRV + `A` + `>`, n=28 BUFIN, then a clean idle loop
  (LF→CURDRV→`A`→`>`→BUFIN). Stock blocks at its BUFIN (n=18) for a real key; ours' headless BUFIN
  returns empty immediately, so ours runs ahead into the prompt loop. That asymmetry is a headless
  artifact, NOT a bug ([[tier2-storms-are-downstream]]: headless BUFIN never blocks).
- **NEW: the screen is garbage** (new `screen` mode reads the VRAM name table at R2-derived base).
  Stock renders perfectly (`  MSX-DOS version 1.03` / `Current date is Sun 84-01-01` / `Enter new
  date:`). **Ours' name table is all tile `$80`** (`HEX01 = 2020 80 80 … 80`; spaces `$20` survive,
  every letter → `$80`). The `MSX` byte-sequence is found in stock VRAM, **never in ours' VRAM**.
  Mode = SCREEN 1 (scrmod=01, 32-col, namebase $1800) on BOTH; same renderer; so this is real, not
  a tool/renderer artifact.
- **Root cause = inter-slot CHPUT register-context divergence** (capture + trace):
  - CHPUT *receives the correct char*: aligned `capture --at 0x00A2 --nth 5` for `'X'` shows A=$58
    on BOTH (alignment-guard PASS, same char confirmed by A matching).
  - But the *register context* differs at CHPUT entry: **stock BC=$0980, ours BC=$0000** (C=$80 vs
    $00); IX/IY also differ (stock IX=$00A2 IY=$0000 — the CALSLT signature; ours IX=$F195 IY=$0314).
  - CHPUT's internal dispatch then **forks at $08F1 `jr c`** (`ld a,c; cp $20; jr c`): stock's C is
    the printable char → carry clear → glyph path ($08F3); ours' C is wrong → carry set → control
    path ($0914). I.e. CHPUT reads the char from **C**, and ours' C is not the char.
  - Mechanism: ours' `conout_body` (runtime.asm) reaches CHPUT via a hand-rolled `pg0_mainrom_in`
    page-in + **direct `call $00A2`**, bypassing stock's documented chain
    **`$5454→$408F→$001C CALSLT→resident kernel→$F398→$00A2`** (see kernel.asm:34). CALSLT / the
    `$F398` hook establish the register context (notably BC) CHPUT needs; ours doesn't → mis-render.

## Settled facts — DO NOT re-litigate or re-probe
- COMMAND.COM loads correctly; `$47B2` return contract done; `$0005`=`JP $D606` identical;
  `$F338`=0 DOS-handoff fix lands ours on the stock path; GDATE handler @ `$553C` returns the
  clock-less 1984-01-01 default; `$F30D=01/$F30E=00` format defaults set. (All prior settled facts
  about COMMAND.COM load / FOPEN-subset / date VALUE-is-the-gate still hold.)
- **Date path is DONE at the BDOS level** (n=1–18 byte-identical, no poke; SDATE returns).
- **CONOUT "banner byte-identical" was CALL-sequence-verified ONLY, never VRAM-verified.** The
  screen tool reveals ours' CONOUT writes tile `$80` for every glyph. CONOUT is therefore **⚠
  (renders garbage)**, not ✅, on the coverage board — DOWNGRADED 2026-06-30.
- **SDATE ($2B) is NOT a blocker** — it is called past BUFIN, returns, ours proceeds. (Refutes the
  prior next-action hypothesis that SDATE would be the next collision.)

## Dead ends / refuted — do NOT re-walk
- "SDATE ($2B) is the next blocker past BUFIN" — REFUTED 2026-06-30 (SDATE returns; ours proceeds).
- "Ours not-blocking at BUFIN is a bug" — NO, it's the headless no-keyboard artifact; stock blocks
  only because the emulator has no key to give. Both run the same kernel BUFIN.
- (Retained) the older date-path dead ends: FOPEN-return-value, register-only $0005 intercept, M6
  work-area pre-build, "skips MSXDOS.SYS init", "+2 clusters", "_GDATE is a clock bug", "init date
  cells alone". All still dead.

## Next action — NEW SLICE: make CONOUT render real glyphs (spec-first)
The ONLY thing between ours and a **visible** `A>` is the CHPUT rendering bug. Plan:
1. **Char-aligned re-confirm (falsify-first, cheap).** The `$08F1` carry-fork trace was anchored on
   `$00A2` occurrence-count, which is NOT char-aligned (CHPUT hit-counts differ ours vs stock). Re-
   anchor on a char-aligned event (e.g. the BDOS CONOUT `$0005 C=02` call, which callseq PROVED is
   aligned) and trace into CHPUT, to confirm the BC/C divergence at the SAME logical char. (The
   `screen` 0x80 fact and the aligned `capture` BC diff are already robust; this just pins the path.)
2. **Characterise stock's path.** Trace stock `$5454→$408F→CALSLT→$F398→$00A2` and capture what sets
   BC (and whether IX/IY/CALSLT state matter) before CHPUT. Identify the minimal register context
   CHPUT's glyph path needs.
3. **Spec the conout_body fix** (per [[spec-before-implementation]]): either route ours' CONOUT
   through CALSLT ($001C) / the `$F398` hook like stock, or replicate the needed register setup
   before `call $00A2`. Net-zero, BIOS-agnostic (EXPTBL-driven, no CF-3300 hardcode), no canonical
   shift. Get sign-off BEFORE editing the ROM.
4. **Falsify-first for the fix:** confirm that supplying stock's BC (or routing via CALSLT) makes
   ours' VRAM render real ASCII (re-run `screen --machine ours` → expect `MSX-DOS version 1.03`).
5. Once CONOUT renders, re-run `screen --machine ours` at settle — ours should DISPLAY `A>` (the
   control flow already reaches it). That would be the visible-`A>` milestone.

Likely the same `int_h_body`/`conout_body` family of "faithful inter-slot main-ROM call" work — the
fix may also want to confirm int_h isn't masking a related context issue. Note the silver lining:
the rendering fix is plausibly the LAST blocker to a visible `A>`.

**One-command repros for the next session (test.dsk):**
- BDOS path to A> loop: `python3 probes/disk/disk_probe_diff.py callseq --maxhits 40 --diska
  ~/Documents/msx/msx/disks/test.dsk` → identical n=1–18, OURS-only tail shows SDATE/SELDSK/`A>`/BUFIN.
- The garbage screen: `python3 probes/disk/disk_probe_diff.py screen --machine ours --diska
  ~/Documents/msx/msx/disks/test.dsk` → all-`$80` name table (stock renders the banner).
- CHPUT gets the right char: `… capture --at 0x00A2 --nth 5 --diska …` → A=$58 both, BC differs.

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
regs+mem diff at the Nth occurrence), `trace` (per-instruction PC fork + `--resync`), and **NEW
`screen`** (renders the VDP text screen from the VRAM name table — the direct-observation tool that
caught the `$80` render bug; `--machine ours|stock|both`, dumps rows + HEX + a banner-locate scan).
It copies the DOS disk to tmp (mutation-safe) and bakes in the alignment guard. **Extend this, don't
fork a new script.** The 57 legacy `disk_probe_dosboot_*.py` stay for provenance.

## Invariants for any change
- Tier-1 green: `make unit-test` 19/19; DSKIO/BLOAD/FILES == CF-3300.
- Net-zero: `disk.rom` == 16384 B; no canonical-address shifts.
- Probe machine = Philips_VG_8020 for bload-landmark; FILES runs on C-BIOS_MSX1_EU_BASIC_DISK.
- Clean-room: derive from DPB / public contracts / our own stubs; never copy stock bytes.
- Working mode = autonomous-span + [tier2-review-queue.md](tier2-review-queue.md); hard-stop
  on forks/irreversible/unresolvable.
