<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 STATE — resume here first

**This file is OVERWRITTEN, not appended.** It is the O(1) "where are we" board so a
new session doesn't have to re-read the 580-line audit log + do git archaeology.
History/provenance lives in [tier2-review-queue.md](tier2-review-queue.md); detail
specs are the `tier2-*.md` docs. Read this, then the one doc the next-action names.

_Last updated: 2026-07-02 (ROOT CAUSE FOUND — HARD-STOP for asm sign-off) — M13 (CONIN) DONE.
M14/M15 = COMMAND.COM banner/prompt lines don't render because BDOS func-9 (STROUT) emits nothing.
**ROOT CAUSE PINNED THIS SESSION (no asm, clean-room-safe): our own `res_print_tmpl` (= `RES_PRINT`
at `$F1C9`, [init.asm](../init.asm):609) is a STUB that reads/consumes the `$`-string but never emits
the chars — its own source comment says so.** The entire §§3–7 wa_seg / `$F365` / page-1-paging thread
(prior 2 sessions) was a RED HERRING: a new `callwatch` probe mode shows func-9 executes ZERO of our
page-1 code, and a func-9-gated `readwatch` of the string (DE=`$C284`, identical on both) shows ours
reads ALL 27 bytes of "COMMAND version 1.08" via `$F1C9`=RES_PRINT — it traverses the whole string and
emits none. That matches M14 exactly (CHPUT gets 0 func-9 chars). §7.2's "caller is NOT RES_PRINT" and
§7.1's "bounded to wa_seg" are both refuted. **The fix is trivial + unambiguous: make `res_print_tmpl`
call our proven `conout_body` (`$5454`→CHPUT) per char — same as `conin_line_body` already echoes
(runtime.asm:165), approach (A).** Spec written: [tier2-m15-spec.md](tier2-m15-spec.md) §9 (read §9,
skip §§3–7). Committed this session: the `callwatch` probe mode + all doc updates. **HARD-STOP: the
fix is ROM asm → NEXT SESSION signs off then implements.** Two build options (§9.3): (i) grow the
template in place if pre-`$41FD` budget allows (verify with `--sym` object-file SIZE per §7.3), or
(ii, recommended) move `res_print_tmpl` to the free tail (like p1_blit/wa_seg templates) so budget is
a non-issue. **NEW SESSION STARTS HERE →** Next action: get sign-off on §9.2 fix (option i vs ii),
implement, validate against §9.4 (`screen` shows the 3 lines; `--log 0x00A2` ours≈72; Tier-1 19/19;
disk.rom 16384 B), then drive to visible `A>`. History: [tier2-review-queue.md](tier2-review-queue.md) M15._

## Goal
Boot MSX-DOS to the `A>` prompt under zerobas-disk (Tier-2) **without regressing
Tier-1** (disk-BASIC / BLOAD / FILES) and while staying a **BIOS-agnostic replacement
disk ROM** (works on CF-3300, C-BIOS, any standards MSX1). "Reached `A>`" means a
**visible** `A>` on screen + accepts a command — not just the right BDOS call sequence.

## Live thesis (M15 — ROOT CAUSE PINNED 2026-07-02; HARD-STOP for asm sign-off)
**Our own `res_print_tmpl` (`RES_PRINT` @ `$F1C9`, [init.asm](../init.asm):609) is a no-emit stub:
it reads/consumes the func-9 `$`-string but never calls CHPUT/CONOUT — so func-9 STROUT emits zero
chars.** Proven clean-room-safe this session: (1) `callwatch --machine ours` (new mode) → func-9
executes ZERO page-1 disk-ROM code (⇒ the `$F368`/`$F36B` page-1 paging of §§3–7 is CONCURRENT kernel
work, NOT func-9's output path — the whole wa_seg/`$F365` thread was a red herring); (2) `readwatch
--range 0xC284:0x40` gated to func-9 → ours reads ALL 27 bytes of the banner string via reader PC
`$F1C9`=RES_PRINT (stock reads via `$F1CC`, its equivalent). Ours traverses the whole string, emits
nothing. **FIX (approach A, §9.2): `res_print_tmpl` calls `conout_body` (`$5454`→CHPUT, char in E per
M10) per char before the `$` — exactly as `conin_line_body` echoes (runtime.asm:165). Preserves the
DE-past-`$`/A=`$24` return contract. Clean-room (published func-9 + our own CONOUT).** Only build
risk = the cramped pre-`$41FD` template budget (§7.3); §9.3 recommends moving the template to the free
tail. **HARD-STOP: ROM asm needs sign-off.** Detail [tier2-m15-spec.md](tier2-m15-spec.md) §9. The
§§below (old M14 CHARACTERISED thesis) is retained for the alignment/dispatch facts but its
"localised to `$F392`/wa_seg" conclusion is SUPERSEDED by §9.

### (superseded but factual) M14 characterisation — dispatch alignment + CHPUT diverge
**The blocker is a BDOS func-9 (STROUT) OUTPUT gap, not a scroll/clear cosmetic.** Decisive
evidence (all via `disk_probe_diff.py`, test.dsk, anchored at COMMAND.COM `$0100`):
- `callseq --log 0x0005` → ours == stock **BYTE-IDENTICAL for all 18 BDOS calls** (STROUT×3,
  FOPEN, GDATE, CONOUT×12, BUFIN; same C/A/B/DE/HL/ret). COMMAND.COM's control flow is CORRECT —
  it issues every STROUT. This is the guardrail's gold-standard alignment.
- `callseq --log 0x00A2` (CHPUT, the shared bottleneck) → stock emits all 72 banner/prompt chars;
  **ours emits ONLY the 12 date chars** (`Sun 84-01-01`), which are the `C=02` CONOUT calls
  (n=5-16), reaching CHPUT via `ret=7934` = our `$5454` conout_body. Every `C=09` STROUT char is
  ABSENT from CHPUT on ours. `--log 0x5454` → ours 12 (date) / stock 0.
- `screen` (arbiter) → ours shows only `Sun 84-01-01` + the un-cleared BASIC power-on banner.
**⇒ func-2 CONOUT works on ours; func-9 STROUT emits ZERO chars.** Stock funnels all console output
through the kernel `$F392` path; ours vectors func-2 to disk-ROM `$5454` and loses func-9.
**This CORRECTS the M12 refutation** (see Dead ends): M12's "func-9 chars DO reach CHPUT" cited the
`ret=$7934` chars — but those are the func-2 DATE (`C=02`), not func-9 STROUT (`C=09`); a mislabel.
**LOCALISED (black-box, no kernel decode):** `--log 0xF392` → ours **0** / stock **90**; `--log 0x009C`
(CHSNS per-char break-poll on the output loop) → ours **0** / stock **72**. So ours' func-9 handler
dispatches but **never enters the char-output loop** — the `$F392` resident routine (CHSNS-poll + CHPUT)
is never reached. func-2 works via `$5454` (a different, wired path); func-9's output routine is
unreached/stubbed on ours (same shape as the old `$4462` FOPEN gap). Do NOT `trace` into `$F392`/
`$F2AC`/`$F237` (M12c reference-disasm hazard). Secondary symptom (separate): the BASIC banner isn't
cleared before the DOS sign-on. Detail: [tier2-review-queue.md](tier2-review-queue.md) M14 +
[tier2-m15-spec.md](tier2-m15-spec.md).

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
- **"M15 func-9 is blocked by `wa_seg` / the `$F365` slot-read stub / a page-1 disk-ROM output routine"**
  — REFUTED 2026-07-02 (§9). func-9 executes ZERO page-1 code (`callwatch`); the `$F368`/`$F36B`/`$F365`
  paging is concurrent kernel work, not func-9's output path. The §7.3 "complete wa_seg+$F365" build
  was negative for exactly this reason. Root cause is our own `res_print_tmpl` no-emit stub (§9).
- **"func-9's caller/output routine is NOT `RES_PRINT` ($F1C9)"** (§7.2) — WRONG. `readwatch` of the
  string proves `$F1C9`=RES_PRINT is precisely what reads/consumes the func-9 string on ours.
- **"func-9 exits after one char/iteration on ours"** (§7.1/§7.2 framing) — WRONG. Ours reads all 27
  string bytes; it just never emits them.
- **"There are TWO independent console-I/O bugs (func-9 output + BUFIN block)"** — REFUTED M12.
  ONE root cause (the missing CONIN line routine at `$50E0`, falling into `$5454` CONOUT) explained
  both; M13 fixed it.
- ~~**"func-9 STROUT emits ZERO chars / its `$F398` CONOUT vector is unset on ours"** — REFUTED M12.~~
  **RE-OPENED M14 (2026-07-01):** the M12 refutation mislabelled the func-2 DATE chars (`C=02`,
  `ret=$7934`) as "func-9 chars reaching CHPUT." With 18/18 dispatch alignment + the screen arbiter,
  func-9 STROUT genuinely emits ZERO chars on ours. This IS the M14 blocker (see Live thesis).
- **"The `Ø>@`/`D8 19 3E 40 0A` spam is a benign idle artifact / date-prompt cosmetics"** — REFUTED M11;
  root-caused M12 (CONIN→CONOUT fall-through); FIXED M13 (spin no longer occurs).
- **"conout_body should read the char from A"** — WRONG (that WAS the M10 bug). CONOUT contract is E.
- **"func-9 STROUT garbage is a page-0-swap clobbering the string read"** — REFUTED M11.1.
- **"A-2/int_h (keyboard interrupt service) is the CONIN blocker"** — REFUTED M12/M13: A-3/A-5 already
  chains KEYINT correctly; M13's keystroke-injection probes prove keys ARE received during CHGET.
- (Retained) older date-path dead ends: SDATE-is-next-blocker, FOPEN-return-value, register-only $0005
  intercept, M6 work-area pre-build, "skips MSXDOS.SYS init", "+2 clusters", "_GDATE is a clock bug",
  "init date cells alone", "the $80 render is a CHPUT-internal IX/IY/page-0 data divergence". All dead.

## Next action — M15: emit func-9 STROUT chars (ROOT CAUSE PINNED — AWAITING ASM SIGN-OFF)
**Root cause (Live thesis / [tier2-m15-spec.md](tier2-m15-spec.md) §9): our `res_print_tmpl` reads the
`$`-string but never emits it.** Fix is unambiguous; only the asm sign-off gate remains.
1. **Sign off on the §9.2 fix** — add `push de / ld e,a / call conout_body / pop de` before the `jr` in
   `res_print_tmpl` (emit each char via our proven CONOUT). Pick build option §9.3: **(ii) move the
   template to the free tail** (recommended — sidesteps the pre-`$41FD` budget trap of §7.3) vs (i)
   grow in place (only if the `--sym` object-file SIZE confirms slack — NOT exit code).
2. **Implement + validate (§9.4):** `make unit-test` 19/19; `disk.rom` == 16384 B (net-zero — moving a
   template is net-zero); `screen --machine ours --settle 16` shows `COMMAND version 1.08` /
   `Current date is Sun 84-01-01` / `Enter new date: `; `callseq --log 0x00A2` ours ≈72 (was 12);
   `--log 0x009C` fires per-char (was 0); M13 CONIN regression `--log 0x009F` still 1 idle call.
3. **After M15 lands:** drive to visible `A>` (inject a command + Enter via `--keys`/`--keys-at`).
4. Secondary (defer): the un-cleared BASIC power-on banner. Separate cosmetic symptom.

**One-command repros (test.dsk) — the decisive M15 root-cause probes:**
- **String IS fully read but not emitted (root cause):** `python3 probes/disk/disk_probe_diff.py
  readwatch --machine both --range 0xC284:0x40 --maxhits 200 --diska ~/Documents/msx/msx/disks/test.dsk`
  → ours reads all 27 bytes `\r\nCOMMAND version 1.08\r\n\r\n$` via reader PC `$F1C9`=RES_PRINT.
- **func-9 uses ZERO page-1 code (wa_seg/$F365 is a red herring):** `... callwatch --machine ours
  --diska ~/Documents/msx/msx/disks/test.dsk` → 0 entries gated; `--no-gate` → normal page-1 activity.
- **CHPUT gap (M14):** `... callseq --at 0x0100 --log 0x00A2 --maxhits 80 ...` stock 72 / ours 12.
- **Screen arbiter:** `... screen --machine both --settle 16 ...` → ours shows only `Sun 84-01-01`.
- M13 regression (should still pass): `... callseq --at 0x0100 --log 0x009F --maxhits 12 ...` → 1 call.

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
