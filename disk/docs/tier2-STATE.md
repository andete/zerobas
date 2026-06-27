<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 STATE — resume here first

**This file is OVERWRITTEN, not appended.** It is the O(1) "where are we" board so a
new session doesn't have to re-read the 580-line audit log + do git archaeology.
History/provenance lives in [tier2-review-queue.md](tier2-review-queue.md); detail
specs are the `tier2-*.md` docs. Read this, then the one doc the next-action names.

_Last updated: 2026-06-27 (GDATE slice LANDED — ours reaches BUFIN; next = past-BUFIN to A>). Update the date + sections whenever state changes._

---

## Goal
Boot MSX-DOS to the `A>` prompt under zerobas-disk (Tier-2) **without regressing
Tier-1** (disk-BASIC / BLOAD / FILES) and while staying a **BIOS-agnostic replacement
disk ROM** (works on CF-3300, C-BIOS, any standards MSX1).

## Live thesis (RESOLVED 2026-06-27: GDATE collision FIXED — ours reaches BUFIN; see Next action)
_The root-cause analysis below is retained for context; the fix landed (gdate_handler @ `$553C` +
`$F30D/$F30E` defaults). The active blocker is now PAST BUFIN — see "Next action"._

### Root-cause record (the date blocker WAS a CANONICAL-ADDRESS COLLISION)
The date-prompt hang is **not** a clock/inter-slot bug and **not** a work-area-DATA bug.
It is a **page-1 ROM canonical-address collision**: the disk-loaded MSXDOS.SYS BDOS
dispatcher (identical on both machines) services `_GDATE` ($2A) by paging in the disk ROM
(via the `$F368` hook) and calling the canonical date-math routine at **`$553C`** (which
chains `$54C0`→`$4179` `ld a,($F338); ld hl,($F33B)` and the 16-bit divide at `$492F-$494A`).
Stock's CF-3300 ROM has the **MSX-DOS date kernel** there; **ours' zerobas-disk ROM has
`bdos_create_body` (a relocated BDOS/Disk-BASIC body, the `$5456-$5FE4` "3b" region) at the
SAME address `$553C`** → `_GDATE` executes unrelated code → returns garbage (HL=`0000` vs
stock `07C0`=1984).

**FALSIFY-FIRST PROOF (`callseq --poke`, 2026-06-27):** poking ours' date regs (BC=`0101`
DE=`1354` HL=`0054`) + the `$F30E` ordering byte to stock's at `$CDA7` makes ours converge
**byte-for-byte with stock from n=9 through n=18** — the entire date print, then STROUT (n=17)
and **BUFIN (n=18) = the date-input wait**, exactly where stock parks. So **the date VALUE is
the SOLE gate** past the date prompt; the value is garbage purely because ours' canonical date
CODE is overwritten. (Trust check: un-poked baseline reproduces the n=5 CONOUT divergence with
the date digits forking at n=9 — stock prints "1984-01-01", ours "  3-00-00".)

**The reframe reconciles every prior thread:**
- The work-area-DATA falsification (poking `$F100-$F3FF` didn't fix the date) — **vindicated**:
  the CODE at `$553C` is wrong, so the `$F33B` date data stock reads is garbled regardless.
- "_GDATE returns garbage" — **localised**: garbage originates AT the GDATE return `$CC04`
  (ours HL=`0000` DE=`0003` vs stock HL=`07C0` DE=`0101`), i.e. inside the broken handler.
- The DOS-BDOS / work-area-construction scope ([tier2-workarea-map.md](tier2-workarea-map.md))
  is **vindicated as the real path to `A>`** — but via canonical **CODE** collision, not data.

**Strategic consequence:** the date is NOT a cheap standalone fix. It needs the DOS date-math
routines present at canonical page-1 addresses (`$553C`, `$54C0`, `$4179`, `$492F`) that ours
currently uses for Tier-1 Disk-BASIC/BDOS bodies. This IS the core Tier-2 problem — a 16KB ROM
that cannot host both Tier-1 bodies and Tier-2 DOS-BDOS routines at their fixed canonical
addresses. **HARD-STOP — user strategy decision (see Next action).**

## Settled facts — DO NOT re-litigate or re-probe
- COMMAND.COM **loads correctly**: ours reads sectors 134–146 (cluster 62–68),
  byte-identical to stock at `$0100` entry. ("+2 clusters wrong read" was RETRACTED.)
- `$47B2` return contract done (commit 9573a4c): COMMAND.COM runs its **real startup**,
  no longer spins at `$050D`. Sets HL=BC=FAT_FILESIZE, IX=`$F195`, IY=entry DE.
- The **banner prints byte-identically** (53-char "MSX-DOS version 1.03 …", conout `$5454`).
  Garbage CONOUT only starts AFTER COMMAND.COM launches.
- `$0005` = `JP $D606` (kernel BDOS dispatch), identical ours/stock. **All `$0005`
  callers are COMMAND.COM; ZERO in the kernel `$D606-$DDFF`** (fork-B viability gate PASS).
- A **register-only FOPEN intercept is INSUFFICIENT** (fopenoverride): forcing A=`$FF` /
  AF=`$FF45` still mis-branches → the branch input is work-area **memory**, not registers.
- **Work-area PRE-BUILD does not fix the hang** (M6/§8.65): ours reads none of the stale
  cells before looping; loaded COMMAND.COM byte-identical. Forcing `$F338`=00 alone also
  did not fix it.
- The **n=3 BDOS fork is data-driven by `$F338`** (COMMAND.COM `ld a,($F338);and a;jr nz`
  @ `$C26B`): 00=STROUT/prompt (stock), ≠0=SELDSK/loop (ours). **FIXED** 2026-06-27 (`dos_handoff`
  defaults `$F338`=0 DOS-only); ours now follows stock to `$D885` (blocker #2 = `$F368` hook).
- The MSX-DOS-1 **file-ops BDOS (FOPEN / dir-search / file-read) lives INSIDE the disk ROM**
  (shared kernel). Our 14 veneers cover only the COMMAND.COM-LOAD subset; real DOS file ops
  call the rest of the shared BDOS, which in our ROM is FDC/DSKIO code, ds-pad, or bare `ret`.
- **Date VALUE is the SOLE gate past the date prompt** (`callseq --poke` 2026-06-27): supply
  stock's date regs at `$CDA7` and ours converges byte-identically to stock to **BUFIN (n=18)**.
- **`_GDATE` ($2A) garbage originates AT the BDOS return `$CC04`** (ours HL=`0000`/DE=`0003`
  vs stock HL=`07C0`/DE=`0101`) — the handler itself, not COMMAND.COM post-processing.
- **The `_GDATE` handler = canonical page-1 ROM `$553C`** (chain `$54C0`→`$4179`→`$492F`);
  ours has **`bdos_create_body`** there (collision) so it runs unrelated code. Stock reads the
  date from `$F338`/`$F33B` cells; the n=4 GDATE call input is byte-identical, only the result
  differs. **The date work used `test.dsk`** (NOT msxdos103-cmd111.dsk — its COMMAND.COM never
  hits `$CDA7`).

## Dead ends — do NOT re-walk
- "Fix FOPEN return code" (fork-A first step) — value isn't the branch input.
- "Intercept `$0005`, register-only contract" (fork-B lightweight) — work-area mem, not regs.
- M6 full work-area pre-build — does not fix the hang.
- "Ours skips MSXDOS.SYS init" — refuted (entry0100seq).
- "+2 clusters / wrong-sector load" — retracted (mid-stream snapshot artifact).
- **"The date is a `_GDATE`/clock inter-slot-path bug"** (the prior most-recent framing) —
  REFUTED. No clock is involved: stock reads `$F33B`/`$F338` work-area cells + ROM date math,
  not the RTC (CF-3300 is clock-less; the 1984 default IS the cell value). The bug is the
  canonical-address CODE collision at `$553C`.
- **"Init the date work-area cells to fix the date"** — would NOT fix it alone: ours' CODE at
  `$553C` (`bdos_create_body`) garbles any `$F33B` data. Code first, then data.

## Next action — GDATE slice DONE; next slice = PAST BUFIN to `A>`
**GDATE slice LANDED + VALIDATED 2026-06-27** ([tier2-gdate-spec.md](tier2-gdate-spec.md) §9):
`gdate_handler` at canonical `$553C` (kernel.asm, `fac_loop_body` relocated net-zero) returns the
clock-less default 1984-01-01, AND `dos_handoff` now defaults the date-FORMAT cells `$F30D=01 /
$F30E=00` (runtime.asm — the value handler alone was NOT enough; COMMAND.COM reads `$F30E` at
`$CDA7` to format). **Result: ours converges with stock through BUFIN (n=18), the date-input
wait** — `$CC04` diff NONE, callseq n=1–18 identical, no poke. Validated: test_gdate.py (suite
19/19), net-zero 16384 B / no canonical shift, DSKIO/FILES/APPEND == CF-3300. `$2A` GDATE = ✅ on
the [tier2-bdos-coverage.md](tier2-bdos-coverage.md) scoreboard.

**NEXT SLICE — past BUFIN to `A>`:** ours now parks at BUFIN (n=18) like stock; the post-BUFIN
divergence (callseq n=19) is the next blocker. Reaching `A>` needs a CR fed to the date prompt
+ likely `_SDATE` ($2B, accepting the date) — its own dispatch-table entry → own canonical handler
(probable collision; possibly a no-op `ret`). Characterise `$2B`'s handler address (the `$D8BE +
3*$2B` table entry) and whether COMMAND.COM calls it after BUFIN. Same method: callseq to find the
fork, capture the handler return contract, falsify-first, then a spec. Headless BUFIN never blocks
([[tier2-storms-are-downstream]]) so feeding the key needs care (probe-inject or a key event).

### Superseded framing (kept for context) — the broader collision
The date blocker is the **first concrete instance
of the central Tier-2 problem**: ours' 16KB disk ROM cannot host both the Tier-1 Disk-BASIC/BDOS
bodies **and** the Tier-2 DOS-BDOS routines at their **fixed canonical page-1 addresses**, because
the disk-loaded MSXDOS.SYS dispatcher calls those canonical addresses directly. For the date,
`$553C`/`$54C0`/`$4179`/`$492F` collide with `bdos_create_body`/relocated Disk-BASIC bodies.

**Why this is a fork, not a grind:** every prior "just one more cell / one more veneer" framing was
too small. The verified scope to make a single DOS BDOS function (`_GDATE`) work is *clean-room
DOS date routines living at canonical addresses ours currently uses for Tier-1*. That is a
**layout/relocation design decision**, the same one [tier2-workarea-map.md](tier2-workarea-map.md)
and [tier2-bdos-scope.md](tier2-bdos-scope.md) reach from the data/file-ops side. The threads have
converged: **reaching `A>` = reproducing the disk-ROM-resident DOS BDOS at canonical addresses,
without displacing Tier-1.**

**Options for the user (recommend B→A as a staged path):**
- **(A) Full DOS-BDOS canonical reproduction.** Build the resident DOS BDOS (date math + the
  work-area construction in [tier2-workarea-map.md](tier2-workarea-map.md)) at canonical page-1
  addresses, relocating Tier-1 bodies that collide. Deepest Tier-2 work, multi-session, needs a
  layout/relocation spec FIRST (which Tier-1 bodies move, where; net-zero; BIOS-agnostic).
- **(B) Date-path slice first (proof of method).** Provide ONLY the canonical date chain
  (`$553C` date handler + `$54C0`/`$4179`/`$492F` + the `$F33B`/`$F338` date cells) clean-room,
  relocating just the colliding Tier-1 body(s). Smaller, gets PAST the date prompt to the next
  real blocker, and de-risks the relocation approach before committing to (A). Falsify-first has
  already PROVEN a correct date converges ours to BUFIN — so (B) is known to advance.
- **(C) Bank as documentation + pause the `A>` build.** The collision is now cleanly mapped
  (dual-mission deliverable); pause implementation.

**Spec-before-code (per [[spec-before-implementation]]):** whichever of A/B, write the
layout/relocation spec (which canonical addresses host DOS code, which Tier-1 bodies relocate
where, net-zero proof, both-host acceptance) and get sign-off before any ROM edit.

**Falsify-first repro of the whole chain (one command, for the next session):**
`python3 probes/disk/disk_probe_diff.py callseq --maxhits 20 --poke-at 0xCDA7 --poke-nth 1 \
  --poke-reg BC:0x0101 --poke-reg DE:0x1354 --poke-reg HL:0x0054 --poke 0xF30E:0x00 \
  --diska ~/Documents/msx/msx/disks/test.dsk` → ours converges to stock through BUFIN (n=18).

## Method guardrails (DURABLE — keep these when you overwrite this file)
Endorsed 2026-06-27 after a retrospective found ~half the Tier-2 reframes came from
premature/misaligned conclusions, not hard bugs. See [[harness-first-investigation-mo]].
1. **Anchor + alignment.** Every differential capture is anchored on a SHARED logical
   event; before trusting a stock-vs-ours diff, PROVE both sides are at the same logical
   point (same Nth call/occurrence — not same PC or wall-clock, esp. when one side loops).
   `disk_probe_diff` enforces this (flags MISALIGNED rather than printing a false diff).
2. **Falsify first.** Step 1 of every milestone = the cheapest experiment that would
   DISPROVE the hypothesis (register-override, force-the-value, "do we even read this?"),
   BEFORE any characterise/spec/build. `capture --expect same|diff` makes it a one-liner.
3. **Gate characterisation behind #2.** Don't map the full scope of a path until the cheap
   experiment confirms the path is real (avoids mapping paths-not-taken, e.g. the 23-addr
   BDOS scope / 96-routine work-area maps built on later-parked theses).
4. **Right tool per question.** Settled facts → host unit-tests (`make unit-test`, no
   emulator). Emulator only for genuinely emulator-dependent questions; reuse savestates /
   reverse-timeline at the anchor instead of cold double-boots.
5. **Terse logging.** Full prose queue entry (why/alt/confidence/undo) only for hard-stop
   forks; routine judgment calls get a one-liner.

## Tooling — use the ONE harness, don't write a 58th probe
**`probes/disk/disk_probe_diff.py`** (built on `omsx_session.py`) is the parameterized
differential probe: `callseq` (call-sequence divergence, e.g. the BDOS seq), `capture`
(alignment-guarded regs+mem diff at the Nth occurrence of an address), and `trace`
(per-instruction PC fork + `--resync`). It copies the DOS disk to tmp (mutation-safe) and
bakes in the alignment guard. Validated 2026-06-27: it reproduces the n=3/date divergences
exactly. **NEW 2026-06-27: `callseq --poke/--poke-reg --poke-at --poke-nth`** — the
falsify-first register/memory override (ours-only, stock stays oracle): inject a value at an
anchor and see if ours' BDOS sequence CONVERGES to stock's. This is what proved the date value
is the sole gate. **Extend this, don't fork a new script.**
The 57 legacy `disk_probe_dosboot_*.py` stay for provenance; new work goes through the harness.

## Invariants for any change
- Tier-1 green: `make unit-test` 18/18; DSKIO/BLOAD/FILES == CF-3300.
- Net-zero: `disk.rom` == 16384 B; no canonical-address shifts.
- Probe machine = Philips_VG_8020 for bload-landmark; FILES runs on C-BIOS_MSX1_EU_BASIC_DISK.
- Clean-room: derive from DPB / public contracts / our own stubs; never copy stock bytes.
- Working mode = autonomous-span + [tier2-review-queue.md](tier2-review-queue.md); hard-stop
  on forks/irreversible/unresolvable.
