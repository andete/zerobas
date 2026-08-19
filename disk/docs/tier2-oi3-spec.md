<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 OI-3 spec — clear the leftover BASIC banner before the DOS sign-on

**Status: CHARACTERISED (2026-07-03, Opus session), fix DESIGNED + pinned clean-room-safe;
NOT YET IMPLEMENTED — awaiting sign-off.** This is a **DIFFERENT-SHAPED fix** from M13–M18
(no un-wired `$50xx` kernel-entry veneer, no un-built work-area cell). Per
[[spec-before-implementation]] it needs its own explicit reasoning + sign-off, NOT the
self-approved-by-precedent veneer-class pattern. Resume board:
[tier2-STATE.md](tier2-STATE.md).

## 1. Goal
After M18, BDOS-call parity with stock is **FULL 27/27, zero divergence**, and a correct
visible `A>` renders. The **only** remaining gap to a pixel-perfect stock-matching screen is
cosmetic: ours retains BASIC's power-on banner (`MSX  system / version 1.0 / Copyright 1983
by Microsoft`, ROW10–13), so the DOS sign-on is scrolled down (ours `A>` at **ROW23** vs
stock **ROW09**). Goal: ours' DOS sign-on starts at ROW01 and `A>` lands at ROW09,
byte-for-byte matching stock's name table, WITHOUT regressing Tier-1 and while staying a
BIOS-agnostic replacement disk ROM. `disk.rom` == 16384 B.

## 2. Characterisation (this span, falsify-first, all clean-room — no stock/kernel decode)
All via `probes/disk/disk_probe_diff.py`, test.dsk, keyed `--keys '\r' --keys-at 20`.

- **Both machines are SCREEN 1 at DOS time** — `screen` reports `scrmod=01 linlen=1D r2=06
  namebase=1800` on BOTH. So this is **NOT a mode-switch difference**; the name table simply
  isn't cleared on ours. (Rules out any SCREEN-0/SCREEN-1 re-init as the mechanism.)
- **Stock does NOT clear via a CHPUT form-feed** — `callseq --arm-cond 1 --log 0x00A2
  --maxhits 120` shows **0** `A=$0C` chars in stock's CHPUT stream. So the clear is a
  **direct VRAM name-table fill** (spaces) done during the DOS boot handoff / MSXDOS.SYS init,
  before the sign-on STROUT — NOT a CHPUT `CLS`.
- **Stock's clear ALSO homes the cursor.** `capture --at 0x0100 --nth 1 --mem 0xF3DC:0x2`
  (COMMAND.COM `$0100` entry, a shared anchor well after the clear):
  - STOCK: `$F3DC`(CSRY)=**$01**, `$F3DD`(CSRX)=**$01** — cursor at HOME (1-based row 1,
    col 1). Its sign-on therefore starts at ROW01 (the sign-on string's own leading
    `\r\n` moves it there) → `A>` at ROW09.
  - OURS: `$F3DC`(CSRY)=**$0F** (row 15 — where BASIC left it after the banner), CSRX=$01.
    Ours' sign-on prints from row 15 downward → `A>` at ROW23.
  (CSRY/CSRX = `$F3DC`/`$F3DD` are documented MSX work-area sysvars, already in
  `basic/sysvars.inc` with public provenance — a data-region read here, clean-room-safe.)
- **Ours' disk-ROM boot path has NO screen-init / VRAM-clear step** — grep of
  `init.asm` / `runtime.asm dos_handoff`: none. Ours inherits BASIC's screen verbatim.

**Repro (arbiter), current state** — `screen --machine both --keys '\r' --keys-at 20
--settle 25`: stock `A>.` at ROW09 on a clean screen; ours `A>.` at ROW23 below the retained
BASIC banner (ROW10–13) with the DOS sign-on scrolled down to ROW15+.

**⇒ Stock's DOS boot handoff does: (i) a direct name-table fill of spaces over the SCREEN-1
name table, and (ii) a cursor-home (CSRY:=1, CSRX:=1), before the sign-on. Ours does
neither.** The fix must reproduce BOTH halves; the fill alone would blank the banner but
still print the sign-on from row 15.

## 3. Approach — chosen: FILVRM (`$0056`) via `pg0_mainrom_in` + cursor-home sysvar writes

### 3.1 Candidates considered
| Candidate | Verdict |
|---|---|
| **(a) INITXT `$006C`** (main-BIOS, via `pg0_mainrom_in`) | **REJECTED.** INITXT switches to **SCREEN 0** (40×24 text) — a MODE CHANGE. Both machines are SCREEN 1 at DOS time (§2); switching to SCREEN 0 diverges from stock's characterised behavior (no mode switch) and would break the 32×24 name-table geometry the sign-on renders into. Source: MSX BIOS reference (map.grauw.nl / MSX2 TH) — "INITXT #006C: switches to SCREEN 0". |
| **(a′) INIT32 `$006F`** (SCREEN-1 re-init, via `pg0_mainrom_in`) | **REJECTED.** INIT32 stays SCREEN 1 but does a **full mode re-init** — resets colours (T32COL), re-lays the pattern table (T32CGP/T32PAT), re-programs the name/attr bases, AND clears. That is far MORE than stock's characterised "direct name-table fill": it risks colour/pattern/attribute divergences from stock (which did NOT re-init the mode, only filled the name table). Overkill + side-effect risk. |
| **(b) FILVRM `$0056`** (main-BIOS "fill VRAM", via `pg0_mainrom_in`) + cursor-home | **CHOSEN.** FILVRM (A=byte, BC=length, HL=VRAM addr) writes A repeatedly across BC VRAM bytes — the EXACT documented primitive for stock's characterised "direct name-table fill". It does NOT touch screen mode, colours, the pattern table, or the cursor. Surgical AND standard: a documented BIOS entry, so it is the BIOS-agnostic "ask the BIOS" pattern (like `conout_body`'s CHPUT), yet it does ONLY what stock does. The cursor-home is two sysvar byte-writes (CSRY/CSRX). |
| **(b′) raw VDP name-table fill** (SETWRT `$0053` + port `$98` out-loop, or direct OUT) | Considered as the fallback. Equivalent effect but re-implements what FILVRM already gives us as a documented, register-safe BIOS call. FILVRM is preferred: fewer bytes, no hand-rolled VDP timing, same clean-room status. Keep this only as a fallback if FILVRM proves to clobber a register we cannot save (see §5 risk). |

**Rationale for FILVRM over INITXT/INIT32** (ties to [[cbios-target-cf3300-oracle]] — the
disk-ROM↔main-BIOS interface must stay BIOS-agnostic via standard documented BIOS entries):
FILVRM `$0056` **is** a standard documented MSX BIOS entry (the intended pattern), so it is not
a "raw poke" — it is exactly the "ask the BIOS to do the standard operation" approach the
guardrail favours. But unlike INITXT/INIT32 it does ONLY the name-table fill, matching stock's
characterised direct-fill behavior with no mode/colour/cursor side effects. It is both the
BIOS-agnostic AND the surgical choice — the best of both. The cursor reposition is done via the
documented CSRY/CSRX work-area sysvars (published contract), not a stock-derived routine.

### 3.2 The mechanism (proven pattern, identical to `conout_body`)
FILVRM lives in the main BIOS ROM at `$0056` (page 0). At the insertion point (§4) page 0 is
RAM, so — exactly as `conout_body` does for CHPUT `$00A2` — we page the main ROM into page 0
via the existing portable inter-slot helper `pg0_mainrom_in` (reads EXPTBL[0]=`$FCC1`, toggles
`$A8`; page 1 = our disk ROM keeps running, page 2 = stack survives), `call $0056`, then
`pg0_mainrom_out`. DI spans the half-mapped window (as with CHPUT/CHGET). This is the SAME
validated primitive already used for CONOUT/CONIN/KEYINT — no new inter-slot machinery.

**FILVRM args (SCREEN-1 name table):** `A=$20` (space), `BC=$0300` (768 = 32×24), `HL=$1800`
(name-table base, confirmed `namebase=1800` by the `screen` probe on BOTH machines).

**Cursor-home (after the fill):** `ld a,$01; ld ($F3DC),a` (CSRY:=1) `; ld ($F3DD),a`
(CSRX:=1). Pinned from stock (§2): stock has CSRY=CSRX=$01 at `$0100`. CSRX on ours is already
$01, but we set both for robustness/clarity. These are plain work-area byte-writes.

## 4. Insertion point — `dos_handoff` (runtime.asm), DOS-only path, before `BOOT_ENTRY`
The clear belongs in **`dos_handoff`** (runtime.asm:568), the existing DOS-only handoff
subroutine, inserted **before** the `scf; call BOOT_ENTRY` step-7 "load the system" call (i.e.
alongside the existing `$F338`/`$F30D` DOS-default writes). Reasons this is the right point:

- **DOS-only.** `dos_handoff` is reached ONLY from `boot_sig_ok` (init.asm:319) on a real boot
  disk (sig `$EB`/`$E9`). A non-system / data disk returns from `BOOT_ENTRY` and the caller
  tears the env down back to BASIC (init.asm:320–314). So clearing here NEVER touches a
  BASIC-only or data-disk boot — it is on the DOS path exactly like the `$F338`/`$F30D`
  defaults already there. BIOS-agnostic: runs on any host that boots a DOS disk.
- **Page-0 state is correct for `pg0_mainrom_in`.** By the time `dos_handoff` runs, init.asm
  has already `call page0_ram_in` (line 287) — page 0 is RAM, the BIOS ROM is out. That is the
  IDENTICAL state in which `conout_body` calls CHPUT during COMMAND.COM, and `pg0_mainrom_in`
  is designed for exactly it (it pages the main ROM back in from EXPTBL[0]). Proven safe.
- **Before the sign-on.** MSXDOS.SYS/COMMAND.COM emit the sign-on only AFTER `BOOT_ENTRY` jumps
  into MSXDOS.SYS (no return on a DOS disk). Clearing + homing before `call BOOT_ENTRY`
  guarantees the fill precedes every sign-on char, matching stock's ordering.

Insert the clear as the FIRST action in `dos_handoff` (before the `$F338` save), OR immediately
before the `scf`; either is pre-sign-on. Preferred: FIRST action, so register save/restore
(§5) wraps the smallest region.

### 4.1 Sketch (to be finalised at implementation, after sign-off)
```
dos_handoff:
                call    dos_clear_screen    ; OI-3: fill name table + home cursor (see below)
                ld      a, ($F338)          ; (existing) save host $F338 ...
                ...                         ; (existing $F338/$F30D defaults, scf, BOOT_ENTRY)

; dos_clear_screen — OI-3: blank the SCREEN-1 name table + home the cursor, so the DOS
; sign-on starts at ROW01 (matching stock). BIOS-agnostic: FILVRM ($0056) via the main-ROM
; inter-slot path (same as conout_body's CHPUT), plus CSRY/CSRX work-area sysvar writes.
; MUST preserve IX (= $F195 DRVA_DPB, required into MSXDOS.SYS) and whatever else BOOT_ENTRY
; needs; DI spans the half-mapped BIOS window.
dos_clear_screen:
                push    ix                  ; IX=$F195 must survive into MSXDOS.SYS
                di
                call    pg0_mainrom_in      ; main BIOS ROM -> page 0 (portable, EXPTBL[0])
                ld      a, $20              ; space
                ld      bc, $0300           ; 768 = 32*24 name-table cells
                ld      hl, $1800           ; SCREEN-1 name-table base
                call    $0056               ; FILVRM: fill VRAM[$1800..$1AFF] with $20
                call    pg0_mainrom_out     ; restore page 0 = RAM
                ei
                pop     ix
                ld      a, $01
                ld      ($F3DC), a          ; CSRY := 1 (home row, 1-based)
                ld      ($F3DD), a          ; CSRX := 1 (home col, 1-based)
                ret
```
(Byte budget: this is a small NEW routine in the free tail region; `disk.rom` must stay
16384 B — verify the pad shrinks, no §7.3-class overflow. Exact placement/labels finalised at
implementation. `$1800`/`$0300`/`$0056`/`$F3DC`/`$F3DD`/`$20`/`$01` may be promoted to named
equates for style parity with the rest of the tree.)

## 5. Risks / side-effect concerns (address at implementation)
1. **IX preservation (HIGH — must handle).** init.asm sets `ld ix,DRVA_DPB` ($F195) at
   line 299 BEFORE `call dos_handoff`, and IX must survive into MSXDOS.SYS (§8.31 / M18). MSX
   BIOS calls do NOT contractually preserve IX, and FILVRM may clobber it. **Mitigation:
   `push ix`/`pop ix` around the FILVRM call** (in the sketch). Falsify at implementation:
   `capture --at 0x0200 --machine ours --mem ...`/reg check that IX=$F195 still holds at the
   MSXDOS.SYS entry AFTER the fix. If FILVRM turns out to preserve IX anyway the push/pop is
   cheap insurance; keep it.
2. **Other live registers.** `dos_handoff`'s existing body only needs A/HL/the stack after the
   clear (it re-loads them). The clear runs FIRST, so it may freely clobber A/BC/DE/HL — the
   subsequent `ld a,($F338)` etc. re-establish them. Only IX (§5.1) is live across it.
3. **DI/EI window.** Interrupts must be OFF while the main ROM is half-mapped into page 0 (as
   in `conout_body`). The `di`/`ei` wrap the `pg0_mainrom_in … pg0_mainrom_out` span only; the
   surrounding init path is already DI at this point (init.asm:294 `di`), so confirm we don't
   prematurely EI before `BOOT_ENTRY` — SAFER to NOT `ei` here and let the existing path own
   interrupt state. **Open item:** decide at implementation whether the clear should `ei` at
   all, or stay DI (init.asm holds DI across the whole handoff until after MSXDOS.SYS). Leaning:
   do NOT `ei` inside dos_clear_screen — restore page 0 and leave IFF as the caller had it
   (DI), to avoid an interrupt firing mid-handoff with page 0 RAM and $0038 not yet the BIOS
   handler (the same hazard init.asm:292–285 guards). This differs from `conout_body` (which
   runs later, when EI is normal). **Falsify:** confirm no int-storm / derail after the fix via
   the `screen` arbiter + a `callseq` re-run (must stay 27/27).
4. **FILVRM VRAM-address width.** SCREEN 1 name table is at $1800 (14-bit VRAM, well within
   FILVRM's range). BIGFIL ($016B) is the 16-bit-address variant; FILVRM ($0056) is correct
   for $1800. No 16K-boundary concern.
5. **Colour / pattern untouched (intended).** FILVRM writes ONLY the name table; the pattern
   generator + colour table are already correct (the BASIC banner rendered, so SCREEN 1 is
   fully set up). We deliberately do NOT re-init them (that is why INIT32 was rejected). If a
   colour divergence surfaces vs stock, revisit — but stock did not re-init either.
6. **Fallback if FILVRM is unusable** (e.g. clobbers a register we cannot save cleanly, or the
   inter-slot FILVRM misbehaves): switch to the raw VDP fill (SETWRT $0053 then a `$1800`-based
   `out ($98),a` loop of 768 spaces) under the same `pg0_mainrom_in` window — same effect,
   documented VDP-port contract, no BIOS-call register surprises. Only fall back if §5.1 can't
   be satisfied.

## 6. Acceptance criteria (falsify-first — the cheapest disproving experiment first)
1. **Screen arbiter (primary):** `screen --machine both --keys '\r' --keys-at 20 --settle 25`
   → OURS shows the DOS sign-on starting at ROW01, `A>.` at **ROW09** on a CLEAN screen (no
   BASIC banner), matching stock. Ideally the ours vs stock name-table HEX rows match
   byte-for-byte (`FOUND-MSX at VRAM 1822` on ours, as stock).
2. **Cursor pin:** `capture --at 0x0100 --nth 1 --mem 0xF3DC:0x2` → ours now `$F3DC=01
   $F3DD=01` (matching stock), where before it was `$0F 01`.
3. **BDOS parity intact (regression):** `callseq --at 0x0100 --log 0x0005 --maxhits 40
   --keys '\r' --keys-at 20` → still **27/27 aligned, NO divergence** (the clear must not
   perturb the BDOS call sequence).
4. **IX intact:** IX = $F195 at MSXDOS.SYS entry ($0200) on ours after the fix (§5.1).
5. **No int-storm / derail:** `screen` steady-state stable (not a lucky early frame); no
   `$0038⇄` storm (the `dosboot_triage` classifier stays OK).
6. **Tier-1 green + size:** `make unit-test` 19/19; DSKIO/BLOAD/FILES == CF-3300; `disk.rom`
   == 16384 B; no canonical-address shifts. C-BIOS_*_BASIC_DISK boot on test720.dsk (data
   disk, sig $EB stub) unaffected — the clear is DOS-path-only and that disk returns from
   BOOT_ENTRY, but note: the clear runs BEFORE BOOT_ENTRY, so a returning data disk WILL have
   had its screen blanked. **Open item / check:** confirm this is acceptable for the data-disk
   regression (stock's disk ROM likely also clears before the custom-boot call; if the
   regression expects the pre-clear screen, gate the clear behind the DOS-disk-only path more
   tightly). This is the one behavioural question flagged for the sign-off discussion.

## 7. Clean-room status
- FILVRM `$0056`, WRTVRM/SETWRT, INITXT/INIT32 addresses + contracts: documented MSX BIOS ABI
  (MSX Assembly Page / map.grauw.nl BIOS list, MSX2 Technical Handbook). Cited, not decoded.
- CSRY/CSRX `$F3DC`/`$F3DD`: documented work-area sysvars (already in `basic/sysvars.inc`,
  public provenance). Home values (=1) confirmed by a ONE-SIDED DATA read of stock's work area
  (`capture --machine stock --mem 0xF3DC:0x2`) — a black-box data probe, NOT a code decode.
- The name-table geometry ($1800, 768) is the standard SCREEN-1 layout, confirmed by the
  `screen` probe reading VRAM (`namebase=1800`) on BOTH machines — not derived from stock code.
- `pg0_mainrom_in`/`out` are our own inter-slot code (runtime.asm), already clean-room.
- NO stock ROM / loaded-kernel CODE bytes were read to design this fix. The "what does stock's
  clear do" question was answered purely by: side-effect observation (`screen`), CHPUT-stream
  counting (`callseq --log 0x00A2` = 0 form-feeds), and one-sided sysvar DATA reads.

## 8. Status / next
**Spec complete; STOP for sign-off (per [[spec-before-implementation]] — this is a new
fix-shape, not covered by the standing veneer-class pre-approval).** Open items to resolve in
the sign-off discussion: (i) the EI-vs-stay-DI decision (§5.3); (ii) the data-disk pre-clear
behaviour (§6 item 6). On go-ahead: implement in runtime.asm `dos_handoff`, verify §6, commit.
