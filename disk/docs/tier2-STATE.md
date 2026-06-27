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
**Next milestone = root-cause the n=3 STROUT-vs-SELDSK divergence.** Re-measured
2026-06-27 via `disk_probe_diff callseq` (n=1/2 byte-identical, confirming the anchor):
- stock n=3 = **STROUT** DE=`$D2B3` **HL=`$0081`** ret=`$CBFF` → n=4 SDATE → n=5/6 CONOUT
  (prints from the command tail at `$0081`; the normal "no AUTOEXEC → prompt" path).
- ours  n=3 = **SELDSK** DE=`$D6FF` HL=`$0021` ret=`$C30A` → CONOUT/CURDRV loop.
COMMAND.COM is the SAME program on both at this point, so the branch input that sends ours
to SELDSK vs stock to STROUT is set between the n=2 FOPEN return (`$C24E`, identical) and
n=3. **Next step (falsify-first):** `capture --at <COMMAND.COM PC between $C24E and the
n=3 dispatch> --mem <suspect work cell>` to find the exact cell/branch ours reads
differently — anchored, NOT a mid-stream snapshot. Phase-1 (work-area construction) is
**PARKED** — not the fix for the hang; revisit only if this resurfaces a real work-area dep.

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

## Open questions for the user
_(none open — Q1 resolved 2026-06-27: pivot to the BDOS-loop, option b.)_

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
