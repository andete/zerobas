<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 STATE — resume here first

**This file is OVERWRITTEN, not appended.** It is the O(1) "where are we" board so a
new session doesn't have to re-read the 580-line audit log + do git archaeology.
History/provenance lives in [tier2-review-queue.md](tier2-review-queue.md); detail
specs are the `tier2-*.md` docs. Read this, then the one doc the next-action names.

_Last updated: 2026-07-03 (M18 CHARACTERISED + falsify-first fix LANDED; only OI-3 screen-clear left —
Opus span) — M13/M15/M16/M17 DONE (git history). **M18 (drive letter `C>` vs `A>`) root-caused +
fixed.** Root cause: during BDOS CURDRV (func `$19`) the loaded kernel CALLs page-1 `$50C4`; on ours
that address was `$00` NOP-padding (same un-wired-`$50xx`-entry class as M13's `$50E0` / M15's
`res_print_tmpl` / M17's `$50D5`) → NOP-slid and never read the current drive, so the kernel's
`'A'+drive` letter math used a bogus index and printed `C>` (index 2). Pinned clean-room-safe (no
kernel decode): register-identical `callseq --log 0x50C4` CALL-boundary pin (`AF=0044 BC=C419 DE=D3FF
HL=D502 SP=DBFE`, ret `$D88A`) + CAUSAL `readwatch --in-func 0x19` showing `$50C4` reads exactly one
cell, `$F247` (=current drive), which was `$FF` (unbuilt) on ours / `$00` on stock. **Fix (falsify-
first build, validated):** (a) `$50C4: jp curdrv_body` veneer (`ld a,(CURDRV_CELL); ret`, net-zero pad
in `$50B8–$50D4`); (b) `build_drvtbl` writes `$F247`:=`$00` (MSX-DOS boot logs in drive A:). **Result:
FULL 27-call BDOS parity with stock, ZERO divergence** (was: first divergence at n=25). `screen`
renders a **correct visible `A>.`** — the drive letter is now right. Tier-1 19/19; `disk.rom` 16384 B;
M13/M15/M17 regressions intact. Detail: [tier2-m18-spec.md](tier2-m18-spec.md). Commit `2d1ba5c`.
**NEW SESSION STARTS HERE → only OI-3 (cosmetic screen-clear) remains before a pixel-perfect `A>`:**
BDOS-call parity is COMPLETE and `A>` is on-screen and correct, BUT ours still shows the leftover BASIC
power-on banner (`MSX system / version 1.0`) at the top, so the DOS sign-on + `A>` are scrolled down
(ours ROW23 vs stock ROW09) instead of on a cleared screen. This is **OI-3, a DIFFERENT-SHAPED fix from
M13–M18** (not an un-wired `$50xx` entry / work-area cell): stock's DOS boot handoff clears VRAM via a
DIRECT name-table fill — NOT a CHPUT `$0C` (confirmed: 0 form-feeds in stock's `$00A2` stream) and NOT
a screen-mode switch (both are `scrmod=01 r2=06 namebase=$1800`). Ours' boot handoff never clears the
name table. See the OI-3 section below for the repro + candidate fix. History:
[tier2-review-queue.md](tier2-review-queue.md) (M14/M15 archived in
[tier2-review-archive.md](tier2-review-archive.md); M16/M17/M18 pending archive)._

## Goal
Boot MSX-DOS to the `A>` prompt under zerobas-disk (Tier-2) **without regressing
Tier-1** (disk-BASIC / BLOAD / FILES) and while staying a **BIOS-agnostic replacement
disk ROM** (works on CF-3300, C-BIOS, any standards MSX1). "Reached `A>`" means a
**visible** `A>` on screen + accepts a command — not just the right BDOS call sequence.

## Live thesis (M18 — DONE 2026-07-03; only OI-3 left)
**M18 drive-letter bug = the missing `$50C4` kernel entry (current-drive read), now fixed** — see the
top summary + [tier2-m18-spec.md](tier2-m18-spec.md). Full 27-call BDOS parity with stock (ZERO
divergence) and a correct visible `A>`. **Only OI-3 (cosmetic) remains:** the DOS boot handoff does not
clear the BASIC banner from VRAM (stock does a direct name-table fill, not a CHPUT `$0C`). This is a
different-shaped fix than the M13–M18 `$50xx`-veneer + work-area-cell class. The M15 thesis below is
retained as that fix-shape template.

### (superseded — M17 DONE 2026-07-03) SELDSK-time stall = missing `$50D5` entry
Root-caused + fixed: `$50D5: jp seldsk_drv_body` (`ld a,(DRVCNT); ret`) + `build_drvtbl` writes
`$F347`:=`$02`. Full detail: [tier2-m17-spec.md](tier2-m17-spec.md). M18 (above) is the identical-shape
fix one BDOS call later (`$50C4`/`$F247`).

## Live thesis (M15 — DONE, CLOSED 2026-07-02)
**Our own `res_print_tmpl` (`RES_PRINT` @ `$F1C9`) was a no-emit stub: it read/consumed the func-9
`$`-string but never called CHPUT/CONOUT — so func-9 STROUT emitted zero chars.** Root cause pinned
clean-room-safe: (1) `callwatch --machine ours` (new mode) showed func-9 executes ZERO page-1
disk-ROM code (⇒ the `$F368`/`$F36B` page-1 paging of §§3–7 is CONCURRENT kernel work, NOT func-9's
output path — the whole wa_seg/`$F365` thread was a red herring); (2) `readwatch --range 0xC284:0x40`
gated to func-9 → ours read ALL 27 bytes of the banner string via reader PC `$F1C9`=RES_PRINT, then
emitted nothing. **FIX IMPLEMENTED (approach A, §9.2, §9.3 option (ii) signed off): `res_print_tmpl`
moved to the free tail (kernel.asm) and now calls `conout_body` (`$5454`→CHPUT, char in E per M10)
per char before the `$` — exactly as `conin_line_body` echoes (runtime.asm:165). Preserves the
DE-past-`$`/A=`$24` return contract. Clean-room (published func-9 + our own CONOUT).** `build_resident`
now calls `install_res_print` (3 B) instead of the old inline LDIR, so the cramped pre-`$41FD` region's
budget only shrank — no §7.3-class overflow risk (verified: `--bin ... out.sym` object file 16384 B).
**Validated: `screen` renders all 3 COMMAND.COM lines; CHPUT 72/72; CHSNS full stream; M13 regression
intact; Tier-1 19/19; disk.rom 16384 B.** Detail [tier2-m15-spec.md](tier2-m15-spec.md) §9–§10. The
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
- **M17 (2026-07-03): `$50D5` SELDSK-time entry wired** (`jp seldsk_drv_body` = `ld a,(DRVCNT);ret`)
  + `$F347`:=`$02` built. SELDSK stall gone; BDOS calls continue to n=27 BUFIN. DO NOT re-litigate.
- **M18 (2026-07-03): `$50C4` CURDRV-time entry wired** (`jp curdrv_body` = `ld a,(CURDRV_CELL);ret`)
  + `$F247`:=`$00` built. **FULL 27-call BDOS parity with stock, ZERO divergence; correct visible `A>`.**
  The drive-letter bug is CLOSED. DO NOT re-probe the `$50C4`/`$F247` path without a new concrete result.
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

## Next action — OI-3: clear the leftover BASIC banner before the DOS sign-on
M13/M15/M16/M17/M18 are all landed. BDOS-call parity is now **COMPLETE** (27/27, zero divergence) and
`A>` is on-screen with the correct drive letter. The **only** gap to a pixel-perfect stock-matching
screen is cosmetic: ours retains the BASIC power-on banner (`MSX system / version 1.0`, ROW10-13) so
the DOS sign-on is scrolled down (ours `A>` at ROW23 vs stock ROW09) instead of a cleared screen.

**OI-3 characterisation (this span, falsify-first, clean-room):**
- Both machines are SCREEN 1 at DOS time (`scrmod=01 r2=06 namebase=$1800`) — **NOT a mode-switch
  difference**; the name table simply isn't cleared on ours.
- Stock does **NOT** clear via a CHPUT form-feed: `callseq --arm-cond 1 --log 0x00A2 --maxhits 120`
  shows **0** `A=0C` chars in stock's CHPUT stream. So the clear is a **direct VRAM name-table fill**
  (spaces) done by the DOS boot handoff / MSXDOS.SYS init, before the sign-on STROUT.
- Ours' disk-ROM boot path (`init.asm`/`runtime.asm dos_handoff`) has **no screen-init / VRAM-clear**
  step (grep: none). So ours inherits BASIC's screen.

**Next (candidate fix, DOS-path-only, BIOS-agnostic):** in the DOS boot handoff (near `dos_handoff`,
runtime.asm, or the boot-sig-OK path that enters DOS), clear the SCREEN-1 name table to spaces before
handing off — either by calling the main-BIOS `INITXT`/screen-init (via the `pg0_mainrom_in` inter-slot
path we already use for CHPUT) OR a direct VDP name-table fill of `$20` over `$1800:0x300`. Prefer the
BIOS call if a clean-room-safe standard entry exists (INITXT `$006C` / DISSCR-then-fill); a raw VRAM
fill is the fallback. **Falsify-first:** confirm the chosen clear lands ours' `A>` at ROW09 matching
stock via `screen --machine both`. This is DIFFERENT-SHAPED from M13–M18 (no `$50xx` veneer / work-area
cell) — treat as its own small milestone; do NOT force it to look like the veneer class.

**Decisive repro (keyed run):** `python3 probes/disk/disk_probe_diff.py callseq --at 0x0100 --log
0x0005 --maxhits 40 --keys '\r' --keys-at 20 --diska ~/Documents/msx/msx/disks/test.dsk` → now **27/27
calls, ALIGNED, NO DIVERGENCE**. Arbiter: `screen --machine both --keys '\r' --keys-at 20 --settle 25`
→ stock `A>.` at ROW09 (clean screen); ours `A>.` at ROW23 (correct text, but below the retained
BASIC banner at ROW10-13).

**Harness note (M17/M18):** `callwatch`/`readwatch` take `--in-func N` (default 9) to gate on any BDOS
function in flight (used `--in-func 0x19` for CURDRV, `0x0E` for SELDSK); `capture` takes `--machine
ours|stock` for one-sided black-box contract dumps. Use `--arm-cond 1` to arm a callseq unconditionally
(used to sweep the full CHPUT stream for OI-3).

**One-command repros (test.dsk) — the M15 root-cause + fix-validation probes (all still pass):**
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
