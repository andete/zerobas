<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 STATE — resume here first

**This file is OVERWRITTEN, not appended.** It is the O(1) "where are we" board so a
new session doesn't have to re-read the 580-line audit log + do git archaeology.
History/provenance lives in [tier2-review-queue.md](tier2-review-queue.md); detail
specs are the `tier2-*.md` docs. Read this, then the one doc the next-action names.

_Last updated: 2026-06-27 (decision: pivot to BDOS-loop). Update the date + sections whenever state changes._

---

## Goal
Boot MSX-DOS to the `A>` prompt under zerobas-disk (Tier-2) **without regressing
Tier-1** (disk-BASIC / BLOAD / FILES) and while staying a **BIOS-agnostic replacement
disk ROM** (works on CF-3300, C-BIOS, any standards MSX1).

## Live thesis (DECIDED 2026-06-27: pivot to the BDOS-loop — option b)
The immediate hang is a **kernel BDOS-service loop**, not a work-area-init failure
(§8.65 / [tier2-m6-spec.md](tier2-m6-spec.md), Jun 25). First BDOS divergence is call
**n=3**: stock→STROUT (ret `$CBA6`), ours→SELDSK (ret `$C30A`); ours then loops
CONOUT/CURDRV/CONOUT/CONOUT/BUFIN forever (the `$D858`/`$DA23` "prompt" loop).
**ROOT-CAUSED 2026-06-27** (`disk_probe_diff trace`, anchored on the FOPEN return `$C24E`):
the n=3 fork is COMMAND.COM's `ld a,($F338); and a; jr nz` at `$C26B-$C26F`.
- stock `$F338`=**00** → Z set → STROUT (`$CBEF`, prints cmd tail `$0081`) → the prompt path.
- ours  `$F338`≠0 → `jr` taken → `$C300 ld sp,$D52B` → SELDSK / loop.
**Falsification (poke `$F338`=0 into ours):** advances ours **54 instrs** along stock's exact
path, to `$D885 call $F368`. So `$F338`=0 is **NECESSARY and effective** (overturns the old
"forcing `$F338`=0 didn't help" — that set it inconsistently; set cleanly at the read it works).
**New next blocker:** at `$F368`, stock `jp $DF57` vs ours `jp $E795` — but that is ours'
**INTENTIONAL relocated-kernel hook** (flags identical, AF=0044). Needs a BEHAVIORAL equivalence
check of our `$E795` hook, NOT a PC-diff (PC-diffing trips on by-design relocation).
**Convergence:** the "BDOS-loop" IS the unbuilt `$F338` default → phase-1 (DOS work-area
clear/default) is **VINDICATED as necessary**, not dead. See open question below.

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

## Dead ends — do NOT re-walk
- "Fix FOPEN return code" (fork-A first step) — value isn't the branch input.
- "Intercept `$0005`, register-only contract" (fork-B lightweight) — work-area mem, not regs.
- M6 full work-area pre-build — does not fix the hang.
- "Ours skips MSXDOS.SYS init" — refuted (entry0100seq).
- "+2 clusters / wrong-sector load" — retracted (mid-stream snapshot artifact).

## Current literal blocker
After COMMAND.COM startup, a kernel loop `$D858-$D87F` (`$D87F` = 130-byte LDIR
`$D34E→$DA40` + CONOUT at `$D887`); screen blank, CONOUT fed `$00/$80`. Tied to the
n=3 STROUT-vs-SELDSK BDOS divergence above.

## Phase-1 thread (the last thing worked on)
[tier2-phase1-spec.md](tier2-phase1-spec.md): boot-time DOS work-area clear/default.
- Option A (clear first in `init`, all boots) was **built, DOS-validated, then REVERTED**
  — it regresses Tier-1 BASIC `FILES` (blanket-zero turns C-BIOS's `$C9` RET stubs into
  `00`/garbage). See §7/§7a.
- Construction must be **DOS-only AND BIOS-agnostic** (host `$F1C9-$F37F` layout differs:
  C-BIOS `$C9`-fills, CF-3300 is mostly `$FF`). Validate acceptance on BOTH hosts. §7b.
- Next step *if continuing phase-1*: **Option B** = move the DOS work-area build chain
  (RES_PRINT/RES_STUBS/DRVTBL/WA_JMPTAB/SYSTEM/set_ramad fall-through) into the DOS-boot
  path after a DOS-only `wa_clear`, keeping the BASIC-needed minimum on the BASIC path.
  Needs its own design spec (map BASIC's work-area deps first). NOT a one-liner.

## Next action — blocker #2 (the `$F368`→`$E795` relocated hook)
Blocker #1 (`$F338`=0) is **BUILT + VALIDATED** (2026-06-27): `dos_handoff` in the free tail
([runtime.asm](../runtime.asm)), called from `boot_sig_ok` — defaults `$F338`=0 for DOS,
stack-save/restores the host stub for a returning data disk. Re-trace moved ours' fork step 7 →
61; Tier-1 green (unit 18/18, FILES==CF-3300 on C-BIOS, BLOAD ok); net-zero. Spec:
[tier2-f338-default-spec.md](tier2-f338-default-spec.md) (§7 = the pasmo-overflow lesson).
**Next:** resume `disk_probe_diff trace --anchor 0xC24E --steps ~80` and look at the new fork —
`$D885 call $F368` → `$F368` is ours' relocated wa_seg hook (`jp $E795` vs stock `jp $DF57`).
This is a **behavioral-equivalence** question (does our `$E795` hook do the same job as stock's
`$DF57`?), NOT a PC-diff bug. Needs a way to diff *effects* across the relocation (the harness's
PC-diff trips on by-design relocation — candidate harness extension). Falsify-first: first
confirm the hook even diverges in effect (it may rejoin downstream).

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
differential probe: `callseq` (call-sequence divergence, e.g. the BDOS seq) and `capture`
(alignment-guarded regs+mem diff at the Nth occurrence of an address). It copies the DOS
disk to tmp (mutation-safe) and bakes in the alignment guard. Validated 2026-06-27: it
reproduces the n=3 BDOS divergence exactly. **Extend this, don't fork a new script.**
The 57 legacy `disk_probe_dosboot_*.py` stay for provenance; new work goes through the harness.

## Invariants for any change
- Tier-1 green: `make unit-test` 18/18; DSKIO/BLOAD/FILES == CF-3300.
- Net-zero: `disk.rom` == 16384 B; no canonical-address shifts.
- Probe machine = Philips_VG_8020 for bload-landmark; FILES runs on C-BIOS_MSX1_EU_BASIC_DISK.
- Clean-room: derive from DPB / public contracts / our own stubs; never copy stock bytes.
- Working mode = autonomous-span + [tier2-review-queue.md](tier2-review-queue.md); hard-stop
  on forks/irreversible/unresolvable.
