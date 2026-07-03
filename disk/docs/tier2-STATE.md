<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 STATE — resume here first

**This file is OVERWRITTEN, not appended.** It is the O(1) "where are we" board so a
new session doesn't have to re-read the 580-line audit log + do git archaeology.
History/provenance lives in [tier2-review-queue.md](tier2-review-queue.md); detail
specs are the `tier2-*.md` docs. Read this, then the one doc the next-action names.

_Last updated: 2026-07-02 (**M21a+M21b LANDED — Tier-2 can now load and run an arbitrary named
`.COM`, not just COMMAND.COM itself.** Built while wiring the BDOS-exerciser `BDOSX.COM` tool
([[bdos-exerciser-com-test]]): typing any other program name silently no-op'd. Root cause was
TWO independent broken page-1 entries (full detail [tier2-m21-spec.md](tier2-m21-spec.md)):
**RC-1** — the kernel's FOPEN dir-fill entry `$4462` landed mid our own `fdc_di_save` body (a
byte-count collision, not a canonical clash); fixed by relocating `fdc_di_save..getdpb` (153 B)
to fat.asm's free tail and wiring a real `fopen_fill_body` veneer at `$4462` (fills FCB
+14(high)..+31 from the SFIRST/SNEXT-found dir entry — record count, size, date/time, devid,
cluster chain; miss-path exits `A=$FF` matching stock exactly). **RC-2** — the kernel's RDBLK
entry `$47B2`'s body (`k_47B2`) was a COMMAND.COM-only diagnostic loader (its own private FCB,
its own mini-BDOS open-by-name); rewritten into a generic body that trusts the FAT_FIRSTCLUS/
FAT_FILESIZE already seeded by the preceding FOPEN and streams to EOF via the existing
`bdos_seqread`, reproducing the pinned exit contract exactly (`AF=$0142 HL=BC=`bytes
transferred). A real bug was found and fixed along the way: our internal `BDOS_DTA` cell is
SEPARATE from the kernel's real DTA pointer (`DOS_DTAPTR`, $F23D, M19) — the kernel's SETDTA only
ever writes `DOS_DTAPTR`, so `BDOS_DTA` went stale after boot's own COMMAND.COM load and had to
be reseeded from `DOS_DTAPTR` at `k_47B2`'s entry. **First attempt was reverted** (a third,
uncharacterised `$4462` calling instance broke the core boot regression) and a falsify-first
`writewatch` isolation pass on stock resolved it before the successful second attempt — see
[tier2-m21-spec.md](tier2-m21-spec.md) §0/§0.1 for the full hard-stop story; this is a good
example of the project's harness-first discipline paying off. **Verified end-to-end:** `make
unit-test` 19/19; boot `callseq` 27/27 aligned; `capture --at 0xC51D` (the runtime RDBLK's exit)
ZERO register diffs vs stock; a full typed `BDOSX\r` run aligns all 47 shared BDOS calls
(n=37-47 = the exerciser's own FSIZE/FOPEN/RDSEQ×2/SETRND/RDBLK/WRBLK/FCLOSE), its 384-byte data
buffer and FCB/register-snapshot buffer both 0-byte-diff vs stock; DIR byte-identical; `make
probe` green; `disk.rom` == 16384 B throughout. The BDOS-exerciser tool itself
([tier2-bdos-exerciser-spec.md](tier2-bdos-exerciser-spec.md)) is now UNBLOCKED and was used as
part of this milestone's own verification. Prior: 2026-07-02 (**M20 LANDED — DIR's `nn bytes free` footer now matches stock,
closing DIR to 100% byte-parity.** Two revisions were built and falsified first (Revision 1:
register-only, correct A/BC/DE/HL but the footer stayed wrong; Revision 2: + resident FAT buffer +
`IY`/`DPB+19`, from a one-time Opus+Fable dual-dispatch trial, wired correctly but STILL wrong,
identically so). **Revision 3 (LANDED), from a Fable-SOLO follow-up investigation** (no Opus — the
user's deliberate test of Fable alone after the dual-dispatch trial): root-caused and CAUSALLY PROVED
(poke test, not inference) that the RAM kernel's common BDOS-exit path (`$D8AA-$D8BD`) gates `HL`
passthrough on dispatcher flag `$F306` — a handler that leaves it set has `HL` silently overwritten
with `H:=B,L:=A` (CP/M single-byte-result mirror) instead of passed through. Stock's `$505D` clears
it; ours never did, explaining the identical wrong `$0202`(514)-mirror value seen in BOTH falsified
revisions regardless of what they did internally. **Fix: Revision 1's original register-only body
(unchanged, it was correct all along) plus one store — clear `$F306` before `ret`.** No buffer, no
`IY`, no `DPB+19` — Revision 2's whole premise (downstream reads a pointer we control) was a red
herring; those reads are stock's OWN handler's internal scratch. Verified: `capture --at 0xC6C5` →
`A=$02 BC=$0200 DE=$02C9 HL=$016F` byte-identical to stock; screen arbiter → `375808 bytes free`
byte-identical to stock; 27/27 boot BDOS parity zero divergence; `make unit-test` 19/19; `make probe`
(DSKIO/BASIC/tape) all pass; `disk.rom` 16384 B. Full detail: [tier2-m20-spec.md](tier2-m20-spec.md)
§11; [tier2-review-queue.md](tier2-review-queue.md) M20 LANDED entry (top of file, plus the two
preceding hard-stop entries for the full falsification history). **Model-split note:** Fable-solo, no
cross-check, found in one dispatch what a prior Opus+Fable DUAL dispatch missed — strong evidence for
the open question in [[opus-vs-sonnet-model-split]] about whether investigation depth matters more
than which model/how many. Prior: 2026-07-01 (**M19 LANDED —
MSX-DOS `DIR` now lists files (was: hung forever)** — Opus
span, user-signed-off spec [tier2-m19-spec.md](tier2-m19-spec.md); commits `45fd9be` docs, `5225a29`
impl, docs-update follows). Root cause: kernel dir-search entries `$4FB8` (SFIRST `$11`)/`$5006` (SNEXT
`$12`) were `$00` NOP-pad → CALL slid into the `$50A9` stub → phantom "entry found" → endless
SETDTA/SNEXT loop, blank screen. **FIX (net-zero veneers + free-tail bodies):** `$4FB8`→`sfirst_body`,
`$5006`→`snext_body` walk our own root dir (reuse `fat_mount`/`fat_find` structure), match the search
FCB's 8.3 name with the `?` wildcard (`name_cmp_wild`; NO attr filter — surface labels/subdirs too, DIR
filters), copy the found entry to the runtime DTA as the MSX-DOS "found FCB" (drive + name + attr@+13 +
time/date/clus/size@+23..32, byte-matched to stock in every field DIR reads), persist the scan cursor in
new cell `BDOS_SRCHIDX` ($E55E); `$5006` resumes from it, returns A=$00 found/$FF exhausted. Also wired
`$5058`→`setdta_cache_body` (the SETDTA-time entry stock uses to cache the DTA ptr at $F23D — un-wired on
ours meant the found entry went to a garbage DTA). **RESULT: `screen` renders the file list + `41 files`
+ fresh `A>` BYTE-IDENTICAL to stock; no hang.** Build items pinned black-box first (no stock code
decoded): DTA source = $F23D (via $5058), exit A=$00/$FF, DIR issues all-`?` FCB. Tier-1 19/19; disk.rom
16384 B (3-pass obj); 27/27 boot BDOS parity + OI-3 `A>`-screen intact; no storm. **ONE OPEN ITEM (NOT a
regression, NOT dir-search): the footer `nn bytes free` reads `0` (stock: `375808`).** That is a separate
free-cluster FAT-scan routine (stock does +3 `$4010` DSKIO reads ours doesn't; reached via a kernel
dispatch path ours doesn't complete — ours diverges to the `$75A5` stub / a spurious LSTOUT at BDOS n=63)
that the M19 dir-search design (spec §4-§6) never characterised. **NEEDS ITS OWN SPEC + SIGN-OFF** before
implementing (do NOT improvise). See "Next action". Prior: 2026-07-01 (**BDOS untested-func VERIFY SWEEP**
— verification-only: 7 boot-path funcs re-confirmed incl. `$2B` SDATE; console tier UNTESTABLE-HERE).
Prior: 2026-07-03 (**OI-3 LANDED — Tier-2 DOS-boot-to-`A>` goal MET** — Opus span, explicit
user sign-off). M13/M15/M16/M17/M18 DONE (git history). **OI-3 (leftover BASIC banner not cleared
before the DOS sign-on) FIXED.** Root cause: ours' DOS boot handoff had no screen-clear step, so it
inherited BASIC's power-on banner + cursor (CSRY=`$0F`), printing the sign-on from ROW15 → `A>` at
ROW23 (stock: cleared screen, `A>` at ROW09). Characterised clean-room (no kernel decode): stock does
a DIRECT name-table fill (0 CHPUT form-feeds, no mode switch, both `scrmod=01 namebase=$1800`) + a
cursor-home (stock CSRY/CSRX = `$01/$01`). **Fix (user-signed-off spec, validated):** new
`dos_clear_screen` in runtime.asm free tail, called as the FIRST action in `dos_handoff` — FILVRM
(`$0056`) via the `pg0_mainrom_in`/`out` inter-slot path (same pattern as `conout_body`'s CHPUT) fills
the SCREEN-1 name table (`$1800`, 768) with spaces, then homes the cursor (`$F3DC`:=1, `$F3DD`:=1).
STAY-DI (spec §5.3 — caller holds DI, no `ei` here); IX (=`$F195`) guarded by push/pop; data-disk
pre-clear side effect accepted (spec §6.6). **Result: ours' screen now BYTE-FOR-BYTE matches stock**
(sign-on ROW01, `A>.` ROW09, `FOUND-MSX at VRAM 1822`; CSRY/CSRX `01 01`; BDOS 27/27 aligned zero
divergence; IX=`$F195` at `$0200`; steady-state stable no storm; unit-test 19/19; `disk.rom` 16384 B,
3-pass object verified). Detail: [tier2-oi3-spec.md](tier2-oi3-spec.md). Commit `dc2ac8d`.
**THE TIER-2 DOS-BOOT-TO-`A>` GOAL IS NOW MET:** full BDOS-call parity with stock (27/27), a correct
VISIBLE `A>` prompt on a cleared screen matching stock pixel-for-pixel, and Tier-1 intact. Nothing
cosmetic or functional remains open on the DOS-boot track. History:
[tier2-review-queue.md](tier2-review-queue.md) (M14/M15 archived in
[tier2-review-archive.md](tier2-review-archive.md); M16/M17/M18/OI-3 pending archive)._

## Goal — MET (2026-07-03, OI-3)
Boot MSX-DOS to the `A>` prompt under zerobas-disk (Tier-2) **without regressing
Tier-1** (disk-BASIC / BLOAD / FILES) and while staying a **BIOS-agnostic replacement
disk ROM** (works on CF-3300, C-BIOS, any standards MSX1). "Reached `A>`" means a
**visible** `A>` on screen + accepts a command — not just the right BDOS call sequence.
**STATUS: MET.** Full BDOS-call parity with stock (27/27, zero divergence), a correct
visible `A>` prompt on a CLEARED screen that byte-for-byte matches stock's name table
(sign-on ROW01, `A>` ROW09, `FOUND-MSX at VRAM 1822`), Tier-1 intact (19/19, `disk.rom`
16384 B). The DOS-boot-to-`A>` track is complete; no cosmetic or functional gap remains.

## Live thesis — none (goal met); track complete
The DOS-boot-to-`A>` goal is MET (see Goal). The full milestone chain landed:
M13 (CONIN) → M15 (func-9 STROUT emit) → M16 → M17 (`$50D5` SELDSK) → M18 (`$50C4` CURDRV,
full 27/27 BDOS parity + correct `A>` text) → **OI-3 (screen-clear, pixel-perfect `A>`)**.
The M15 / veneer-class theses below are retained as fix-shape templates for any future
sub-track (e.g. the BDOS-exerciser `.COM` idea), but nothing on THIS track is open.

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
  **[2026-07-03 correction, tier2-m22b-conout53a7-spec.md §4]:** the "ours 12 / stock 0" gap is now
  explained, not just observed — stock's func-2 handler CALLs its own canonical entry (`$53A7`) and
  RETURNS before ever reaching `$5454`; ours' 12 date chars only ever reached `$5454` via a NOP-slide
  from that same un-wired `$53A7` CALL. Nothing ever legitimately called `$5454` for func-2 on either
  machine. `$53A7` is now wired directly (M22b slice 1); the slide no longer occurs.
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

## Next action — M21a+M21b CLOSED; the console tier is next (2026-07-02)

> **M22b slice 1 LANDED (2026-07-03) alongside M22a.** The kernel dispatches EVERY
> BDOS `$02` char to page-1 `$53A7` (was un-wired pad; pre-M22a a lucky NOP-slide into
> `$5454`/`conout_body` was accidentally correct, M22a's `$543C` veneer then intercepted
> it → all func-2 output dropped, DIR corrupted). Fix: `k_53A7: jp conout_body`
> (net-zero, 3 bytes). Re-verified after the fix: DIR `screen` byte-identical, 18/18 +
> 27/27 boot `callseq`, BDOSX2 14-record zero-diff, BDOSX Phase-1 zero-diff,
> `$F237` parity, `make unit-test`/`make probe` green, ROM 16384 B. Spec + pinned
> contracts (char in E, `A:=E`, TAB→8-col stops, column cell `$F237`):
> [tier2-m22b-conout53a7-spec.md](tier2-m22b-conout53a7-spec.md). **Slice 2 (TAB
> expansion + `$F237` maintenance in `conout_body`) is DEFERRED** — a real,
> pre-existing gap, not a regression; not yet implemented.
`DIR` is 100% byte-parity with stock (M19+M20) and Tier-2 can now load and run an arbitrary named
`.COM` (M21a+M21b) — the BDOS-exerciser `BDOSX.COM` tool ([[bdos-exerciser-com-test]]) is UNBLOCKED
and confirmed running end-to-end (all 47 shared BDOS calls aligned, 0-byte-diff data/FCB buffers).
This closes the FCB read/write cluster's `$0F/$10/$14/$1A/$23/$24/$26/$27` funcs (all now
BDOSX-exercised and matching stock).

**HIGHEST — the CONSOLE tier, now reachable via BDOSX.COM.** `$01 CONIN / $06 DIRIO / $07 DIRIN /
$08 INNOE / $0B CONST / $0C CPMVER` were UNTESTABLE-HERE (2026-07-01 sweep) because no COMMAND.COM
builtin calls them and the harness could only inject one keystroke burst — BDOSX.COM can now call
them directly (extend bdosx.asm with a Phase-2 console-call block, per
[tier2-bdos-exerciser-spec.md](tier2-bdos-exerciser-spec.md)'s own "Phase 2" placeholder if one
exists, else a small spec addendum). Expectation (unverified by direct probe): these ride the
already-proven CHGET/CHSNS/`$5454` CONOUT primitives, since the shared kernel dispatches them.
`$75A5` and the 82 spurious per-file `C=05 LSTOUT` calls (BDOS n=63 fork, first noticed during
M19/M20) remain confirmed OUT OF SCOPE for `DIR` (don't block `$1B`/`$505D`/`$4FB8`/`$5006`) but are
still an open, uncharacterised divergence — pick up if/when a milestone touches that area.

**GENERAL RULE learned from M20, applies to ANY future page-1 entry that returns a real `HL`:** the
RAM kernel's common BDOS-exit path (`$D8AA-$D8BD`) silently overwrites a handler's `HL` with
`H:=B,L:=A` unless the handler clears dispatcher flag `$F306` before `ret`. `gdate_handler` already
does this; `getalloc_body` now does too. Any NEW handler that needs its `HL` to survive to the
caller must clear `$F306` before `ret` — check this FIRST if a future milestone shows a
correctly-computed `HL` not reaching its caller (same symptom class M20 hit twice).

### (archived) BDOS untested-func verify sweep — DONE 2026-07-01 (no asm changes)
A **verification-only sweep** checked the "trivial-verify" tier of untested MSX-DOS-1 BDOS funcs.
**RESULT: nothing falsified; nothing to commit for asm.**

**Sweep verdicts (evidence = `disk_probe_diff.py`, test.dsk):**
- **7 boot-path funcs re-confirmed in the same run (all byte-identical, zero divergence):**
  `$02` CONOUT, `$09` STROUT, `$0A` BUFIN, `$0E` SELDSK, `$19` CURDRV, `$2A` GDATE via the 27/27
  `callseq ... --keys '\r'` repro; **`$2B` SDATE CONFIRMED** by typing a real date
  (`--keys '85-3-27\r'` → n=21 `C=2B A=00 B=2D DE=031B HL=07C1 ret=CC85` ours==stock, and `screen`
  shows both reach `A>` at ROW09 with `85-3-27` echoed). The transient n≥22 D-high-byte/timing reg
  diff on the typed-date run is a keyboard-buffer scratch artifact, NOT a functional divergence
  (screen arbiter identical).
- **`$01` CONIN, `$06` DIRIO, `$07` DIRIN, `$08` INNOE, `$0B` CONST, `$0C` CPMVER → UNTESTABLE-HERE**
  (not falsified — cannot be reached by the current harness/disk image). Root reason (architectural,
  clean-room): these funcs are dispatched entirely by the **shared RAM MSX-DOS-1 kernel** and bottom
  out at the SAME two disk-ROM resident primitives already proven byte-identical — CHGET/CHSNS (input)
  and `$5454` CONOUT→CHPUT (output); `$0C` returns a constant ($22) wholly inside the kernel with NO
  disk-ROM routine. COMMAND.COM's boot + date-prompt + `A>` command reader use only `$02/$09/$0A/
  $0F/$2A/$2B/$0E/$19` — a full callseq to `--maxhits 60` past the `A>` prompt shows the flow blocks at
  BUFIN `$0A` (n=27/28, the command reader) and NEVER issues $01/$06/$07/$08/$0B/$0C. Reaching them
  needs a driver `.COM` that calls them (the [[bdos-exerciser-com-test]] idea) or a second interactive
  keystroke at `A>` (the harness injects only ONE `--keys` burst — a real limitation, not built around
  per the "don't build new infra" guardrail). **Expectation stands: they should ride the proven
  primitives, but that is UNVERIFIED by direct probe here.**

**Recommended next (per the ranked order): the FCB read cluster.** The console tier is verified-or-
untestable; the next batch is the file-read FCB funcs (`$0F` FOPEN already boot-exercised; `$10`
FCLOSE, `$14` RDSEQ, `$1A` SETDTA, and the search/random-read funcs). These have a real disk-ROM
surface (`bdos_entry` in driver.asm implements a read subset for Tier-1 BLOAD) and a differential
oracle path — the natural next verification/implementation target. The BDOS-exerciser `.COM` idea is
the tool that would also unblock the UNTESTABLE-HERE console tier above.

**OI-3 (screen-clear) — LANDED, all 7 acceptance criteria pass (commit `dc2ac8d`,
[tier2-oi3-spec.md](tier2-oi3-spec.md)):**
- `dos_clear_screen` (runtime.asm free tail), first action in `dos_handoff`: FILVRM (`$0056`) via
  `pg0_mainrom_in`/`out` fills SCREEN-1 name table (`$1800`, 768) with `$20`, then homes cursor
  (`$F3DC`:=1, `$F3DD`:=1). STAY-DI (no `ei`); IX (=`$F195`) push/pop-guarded; data-disk pre-clear
  accepted per spec §6.6. User-signed-off (not self-approved-by-precedent).
- Validation: screen ours==stock; CSRY/CSRX `01 01` (was `0F 01`); BDOS 27/27 aligned zero divergence;
  IX=`$F195` at `$0200`; steady-state stable no storm; unit-test 19/19; `disk.rom` 16384 B (3-pass obj).

**Decisive repros (still current, all pass):** `callseq --at 0x0100 --log 0x0005 --maxhits 40 --keys
'\r' --keys-at 22 --settle 35 --diska ~/Documents/msx/msx/disks/test.dsk` → 27/27 ALIGNED. `screen
--machine both --keys '\r' --keys-at 22 --settle 35` → ours == stock (both `A>.` at ROW09, cleared
screen). **GOTCHA (verify sweep 2026-07-01):** pass `--keys` as the LITERAL 2-char string `'\r'`
(single-quoted), NOT a shell CR byte (`$'\r'`) — openMSX `type` needs the `\r` escape to map to Enter;
a raw CR does NOT complete BUFIN and the callseq stalls at n=18. Type a real date to fire `$2B` SDATE:
`--keys '85-3-27\r' --keys-at 22`.

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
