<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 STATE — resume here first

**This file is OVERWRITTEN, not appended.** It is the O(1) "where are we" board so a
new session doesn't have to re-read the 580-line audit log + do git archaeology.
History/provenance lives in [tier2-review-queue.md](tier2-review-queue.md); detail
specs are the `tier2-*.md` docs. Read this, then the one doc the next-action names.

_Last updated: 2026-07-04 (**consolidation sweep** — the Tier-2 DOS-boot track is COMPLETE and
was tidied). This pass: ran a whole-target clean-room **paper-trail audit** (1 doc-level break —
a decoded-listing in tier2-m20-spec.md §11.1 — found and remediated the SAME pass, so disk is
paper-trail CLEAN; logged in [../../docs/clean-room-audit.md](../../docs/clean-room-audit.md));
**batch-synced** the M19→M27 review-queue backlog (20 entries) into
[tier2-review-archive.md](tier2-review-archive.md); pruned this board from ~774 lines back to a
lean resume board. Prior: goal MET 2026-07-03 (OI-3). The full M13→M27 milestone history now
lives in the review-archive and the per-milestone tier2-*-spec.md docs — it is no longer
duplicated here._

## Goal — MET (2026-07-03, OI-3); track COMPLETE
Boot MSX-DOS 1 (`MSXDOS.SYS`+`COMMAND.COM`) to a **visible** `A>` on zerobas-disk without
regressing Tier-1, staying a BIOS-agnostic replacement disk ROM. **STATUS: MET** — full 27/27
boot-BDOS parity with stock (zero divergence), a correct visible `A>` on a cleared screen
byte-identical to stock, Tier-1 intact (19/19, `disk.rom` 16384 B). Beyond the boot goal:
**full BDOS surface coverage complete** (M26 closed; tier2-bdos-coverage.md 8/8 on the
mutation/random/absolute-I/O block) and **all four post-M26 residuals closed** (LSTOUT
characterised + wired to BIOS `$00A5`; `$2E` VERIFY resolved as a faithful no-op; M22b slice-2
CONOUT TAB-expansion landed). **Nothing gating remains on this track.**

## Live thesis — Tier-A test hardening (FAT12-core suite DONE 2026-07-04)
DOS-boot track is COMPLETE; a follow-on **Tier-A host-test hardening** pass (user-chosen) landed the
**FAT12-core host suite**. Fixed `coverage.py` (disk group was crashing) → first real number: disk
host coverage was **1%** (74/13849 instr) — the whole FAT12/BDOS engine had ZERO standing host
regression, carried only by the one-shot emulator probes. Added 5 tests (same FDC-mock pattern as
`test_getdpb`): `test_fat_next_cluster`, `test_fat_write_fat_entry`, `test_fat_find` (+name_cmp),
`test_fat_alloc_cluster`, `test_fat_dir_create`, `test_fat_read_file_sector`. Disk host coverage now
**4%** (580 instr, 52 blocks); `make unit-test` 25/25.
**✅ FOUND + FIXED a real bug:** the write test caught `fat_write_fat_entry` (fat.asm:579) straddling
at the wrong `byteidx` boundary — corrupting FAT entries at clusters 170/341/682 (byteidx 255/511)
on a 720 KB disk; invisible to the emulator probes (small disk, low clusters only). Fixed with a
1-byte address-neutral change (`or a`→`dec a`, ROM stays 16384 B), **oracle-confirmed** against 101
real stock disks via `probes/disk/disk_fat_straddle_oracle.py` (incl. the MSX-DOS 1.03 oracle).
Detail in the review-archive.
**Tier-B DONE (2026-07-04):** the BDOSX/2/3/0 one-shot differentials became a standing gate —
`make bdos-acceptance`. **⚠️ but the "6/6 green" baseline was VACUOUS** (see below).

## ✅ DONE — FDC-window P0 + write-path remediation (2026-07-04); OPEN follow-ons tracked
Tier-C case 1 (cluster-boundary EOF) LANDED (dc6ec07). Case 2 (disk-full) cascaded into a
vacuous-gate discovery + a live P0 + a second P1 — all now remediated across two signed-off specs
([tier2-remediation-spec.md](tier2-remediation-spec.md), [tier2-writepath-remediation-spec.md](tier2-writepath-remediation-spec.md)):
- **FDC-window P0 FIXED (Phase A/B/C, commits 2333609 → 2047822).** The National WD2793 registers
  mirror ×8 across the WHOLE **$7F80–$7FBF** (not just $7FB8–$7FBF). `fdc_entloop_body`/
  `fdc_useslot_body`/`p0_env_tab` had drifted into it (~M27) → create/write didn't persist. Fixed
  by a PROVEN byte-pure relocation into the kernel free-region corridor ($607E+); window is dead
  $00 pad; guard corrected to $7F80 with a tamper-tested `FDC_WINDOW_INTRUSION` assert. Create→
  reopen→read converged 17→0 vs CF-3300.
- **The vacuous gate is fixed (Phase A + F3).** De-vacuumed (armed anchors + buffer-diff parsing)
  and given an exact-address, anti-vacuous documented-divergence allowlist. Gate is 4/6, GREEN for
  the right reasons; BDOSX honestly RED (below).
- **RDRND/WRRND wrong-record P1 FIXED (F1, c557628).** `rrnd_recsector`/`rrnd_clussec_tmp` were
  `db` scratch cells IN ROM → runtime stores no-op'd → wrong record. Moved to RAM $E760/$E761
  (net-zero); disk-artifact round-trip verified (WRRND r0=1 → record 1 == CF-3300). Invisible to
  the RAM gate — same class as the FDC-window P0.
- **Harness soundness fixed (F4):** disk_probe_diff.py copies per-machine (write-exerciser
  soundness); BDOS name table corrected.
- **OPEN follow-ons (tracked in review-queue):** (1) `$26` WRBLK unimplemented; (2) bdosx.asm
  drives block ops out-of-contract (no FCB record-size) → BDOSX stays honestly RED until fixed;
  (3) `$23` FSIZE `A=3` uncharacterised (kernel shared call — F2 deferred); (4) WRSEQ disk-full
  onset lag (P2, case-2 D1). BDOSX4 disk-full exerciser BUILT, still OUT of the gate.

## Durable framing (outlives the active pass)
The milestone chain M13→M27 all landed (detail in the tier2-*-spec.md docs + the review-archive).
The framing that outlives this track — the two-interface rule, the **Settled facts** and **Dead
ends** below, and the **Method guardrails / Tooling / Invariants** at the bottom — is retained for
any future zerobas-disk work (e.g. the deferred multi-hardware variant layer,
[[disk-hardware-target-variants]]).

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
- **OI-3 (2026-07-03): DOS boot handoff now clears the SCREEN-1 name table + homes the cursor**
  (`dos_clear_screen` = FILVRM `$0056` fill of `$1800`/768 + CSRY/CSRX `$F3DC`/`$F3DD`:=1, first action
  in `dos_handoff`). Ours' screen is now BYTE-FOR-BYTE identical to stock (sign-on ROW01, `A>` ROW09).
  DO NOT re-add a screen-init/CLS or switch to INITXT/INIT32 (both rejected — they mode-switch/re-init;
  stock does only a direct name-table fill). STAY-DI is intentional (caller owns IFF). DO NOT re-litigate.
- **STOCK's real boot = sign-on → `COMMAND version 1.08` → `Current date is Sun 84-01-01` →
  `Enter new date:` → blocks at BUFIN, now matched by ours at the CHGET level (M13).**
- **M19 (2026-07-01): BDOS SFIRST `$11`/SNEXT `$12` dir-search wired** — `$4FB8`→`sfirst_body`,
  `$5006`→`snext_body`, `$5058`→`setdta_cache_body` (DTA cache at $F23D); cursor cell `BDOS_SRCHIDX`
  ($E55E). `DIR` lists all files byte-identical to stock (`41 files`, `A>`), no hang. Pinned facts DO NOT
  re-probe: entry DE→search-FCB (name pattern +1, `?`=$3F wildcard); DIR issues all-`?` FCB; runtime DTA
  = `($F23D)` (populated by the `$5058` SETDTA-cache); found entry written to the DTA as the MSX-DOS
  "found FCB" (drive+name+attr@+13+time/date/clus/size@+23..32); NO attr filter (return labels/subdirs,
  COMMAND.COM filters); exit A=$00 found/$FF exhausted. **The `bytes free` footer was a SEPARATE
  routine, now LANDED as M20 (see below).** DO NOT re-litigate the dir-search mechanism.
- **M20 (2026-07-02): `$505D` GETALLOC-time entry wired** (`jp getalloc_body` — own FAT scan via
  `read_sector`/`WBUF`, reusing fat.asm's `fac_entry_from_wbuf` unpack; counts free clusters instead
  of stopping at the first). Returns `A=sectors/cluster BC=$0200 DE=total-data-clusters
  HL=free-cluster-count`, AND clears dispatcher flag `$F306` before `ret` — **this clear is the
  load-bearing fix**: the RAM kernel's common BDOS-exit path (`$D8AA-$D8BD`) silently overwrites a
  handler's `HL` with `H:=B,L:=A` unless the handler clears `$F306` first (causally proven via a poke
  test). `gdate_handler` was ALREADY doing this (previously assumed "harmless stock parity" — it is
  not). `DIR`'s footer now renders `375808 bytes free` byte-identical to stock; `DIR` is 100%
  byte-parity with stock (file list + `41 files` + footer + fresh `A>`). DO NOT re-litigate: `IY`/a
  resident FAT buffer/a per-drive `DPB+19` field are NOT needed for this footer (two prior revisions
  tried and falsified that path — see [tier2-review-queue.md](tier2-review-queue.md) for the full
  falsification history) — **any future HL-returning page-1 entry must remember to clear `$F306`
  before `ret`**, this is now a GENERAL rule for this ROM, not GETALLOC-specific.
- **M21a+M21b (2026-07-02): typed-`.COM` load fully works.** `$4462` (kernel FOPEN dir-fill) now a
  real veneer (`fopen_fill_body`, disk/fat.asm) after relocating the colliding `fdc_di_save..getdpb`
  span to fat.asm's free tail; `$47B2` (kernel RDBLK) rewritten from a COMMAND.COM-only diagnostic
  loader into a generic body (`k_47B2`, disk/kernel.asm) that trusts the preceding FOPEN's
  FAT_FIRSTCLUS/FAT_FILESIZE and streams to EOF via `bdos_seqread`. **DO NOT re-litigate the fill
  contract** (uniform across calling instances, §0.1 of [tier2-m21-spec.md](tier2-m21-spec.md)) or
  the exit-register contracts (§5.5, both pinned and now verified byte-identical). **Remember:** our
  internal `BDOS_DTA` cell and the kernel's `DOS_DTAPTR` ($F23D) are SEPARATE — any future page-1
  body that streams via `bdos_seqread` for a caller OTHER than our own internal loader must reseed
  `BDOS_DTA` from `DOS_DTAPTR` at entry, or it will silently target a stale address.

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

## Next action — Phase B of the FDC-window P0 remediation (spec signed off; user paused before ROM edits)
**The FDC-window + write-path remediation is COMPLETE** (see the ✅ DONE section above). The next
step is a user-scoped pick from the tracked follow-ons or a parked direction. The follow-ons
(review-queue): implement `$26` WRBLK; fix bdosx.asm's out-of-contract block ops (unblocks BDOSX
gating); characterise `$23` F_SIZE; adjudicate the WRSEQ disk-full onset lag (P2). None is forced.

Other candidate directions (parked):
- **Docs-as-deliverable harvest** ([[dual-mission-docs-as-deliverable]]) — now the code is
  settled, consolidate the tier2-*-spec.md notebook into the product-spec genre (seed:
  spec-diskrom-kernel.md).
- **C-BIOS LPTOUT follow-up** ([[cbios-lptout-followup]]) — the one STANDING item: LSTOUT is
  wired to BIOS `$00A5`, but C-BIOS stubs `$00A5`, so list output won't print on the prime
  target until C-BIOS gains a real LPTOUT. A C-BIOS change, not a disk-ROM one.
- **Disk full-verify trail** — the heavier empirical audit back-half (docs/clean-room-audit.md),
  now unblocked by the settled surface; a deliberate tier-closure ritual, not a routine gate.
- **Multi-hardware variant layer** ([[disk-hardware-target-variants]]) — DEFERRED; one shared
  kernel + a swappable thin hardware-driver, if ever green-lit.

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
