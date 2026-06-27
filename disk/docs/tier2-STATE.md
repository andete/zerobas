<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 STATE — resume here first

**This file is OVERWRITTEN, not appended.** It is the O(1) "where are we" board so a
new session doesn't have to re-read the 580-line audit log + do git archaeology.
History/provenance lives in [tier2-review-queue.md](tier2-review-queue.md); detail
specs are the `tier2-*.md` docs. Read this, then the one doc the next-action names.

_Last updated: 2026-06-27 (session resume). Update the date + sections whenever state changes._

---

## Goal
Boot MSX-DOS to the `A>` prompt under zerobas-disk (Tier-2) **without regressing
Tier-1** (disk-BASIC / BLOAD / FILES) and while staying a **BIOS-agnostic replacement
disk ROM** (works on CF-3300, C-BIOS, any standards MSX1).

## Live thesis (⚠ UNRECONCILED — this is open question #1)
The immediate hang is a **kernel BDOS-service loop**, not a work-area-init failure
(§8.65 / [tier2-m6-spec.md](tier2-m6-spec.md), Jun 25). First BDOS divergence is call
**n=3**: stock→STROUT (ret `$CBA6`), ours→SELDSK (ret `$C30A`); ours then loops
CONOUT/CURDRV/CONOUT/CONOUT/BUFIN forever (the `$D858`/`$DA23` "prompt" loop).
**BUT** the literal last activity (Jun 26, *after* §8.65) is **phase-1 work-area
clear/default** — a work-area tactic. These two are in tension (see open Q1).

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

## Open questions for the user (blocking "what does *continue* mean")
1. **Reconcile phase-1 vs §8.65.** If work-area construction is NOT the fix for the hang
   (§8.65), is phase-1 still worth the option-B design effort (as faithful-reproduction
   foundation), OR should effort pivot to the BDOS-loop (the n=3 STROUT-vs-SELDSK
   divergence)? **This decides the next milestone.** My read: needs your call.

## Invariants for any change
- Tier-1 green: `make unit-test` 18/18; DSKIO/BLOAD/FILES == CF-3300.
- Net-zero: `disk.rom` == 16384 B; no canonical-address shifts.
- Probe machine = Philips_VG_8020 for bload-landmark; FILES runs on C-BIOS_MSX1_EU_BASIC_DISK.
- Clean-room: derive from DPB / public contracts / our own stubs; never copy stock bytes.
- Working mode = autonomous-span + [tier2-review-queue.md](tier2-review-queue.md); hard-stop
  on forks/irreversible/unresolvable.
