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

## ⚠ FALSIFICATION 2026-06-27 — the date is NOT a work-area-clear issue
Falsify-first poke (the `$F338` playbook at scale): injected stock's values into ALL uninit cells
across the **full `$F100-$F3FF`** DOS work area on ours at COMMAND.COM `$0100`, then captured the
date regs at `$CDA7`. **Result: BC=0003 DE=0000 UNCHANGED** (stock BC=0101 DE=1354). So **the date
VALUE is not sourced from the DOS work area** — building/clearing work-area cells will NOT fix the
date. This DISPROVES the "incremental date subset of the work area" plan for the date itself.
(The work-area construction is still real and needed — see below — just not the date's cause.)

**CORRECTED: n=4 is `_GDATE` (GET date, `$2A`), NOT SDATE** — the harness BDOS table was shifted
by one (`$2A`=GDATE/`$2B`=SDATE/`$2C`=GTIME/…; fixed in disk_probe_diff.py). So COMMAND.COM **calls
`_GDATE` to GET the date for display**, the "identical params" were ignored input regs, and it's the
**GDATE _result_ that differs** (stock returns 1984-01-01, ours garbage). Combined with the
work-area falsification: **ours' `_GDATE` BDOS returns a garbage date.** `_GDATE` reads the clock
(SUBROM/inter-slot) and defaults to 1984-01-01 when there's no valid clock (MSX1); stock gets the
default, ours gets garbage → likely **ours' clock-read / inter-slot path in the boot env**
(`lay_page0_env` / page-0 handlers) doesn't service `_GDATE`'s clock access, OR ours' relocated
`_GDATE` routine is broken. **Next:** examine ours' `_GDATE`/clock path (our own code — the page-0
env + the relocated kernel's date routine) vs the contract; this is the date's real root, not the
work area. Falsify-first: poke the GDATE return regs to stock's and confirm the date renders.

## Earlier framing (date-as-work-area) — SUPERSEDED by the falsification above
## Next action — blocker #2: ours' MALFORMED DATE-PROMPT (loops, doesn't reach `A>`)
Blocker #1 (`$F338`=0) is **BUILT + VALIDATED + COMMITTED** (2026-06-27, 164b857): `dos_handoff`
in the free tail. It advanced ours materially — `callseq` now matches stock **through n=1–4**
(STROUT, FOPEN, STROUT, SDATE) and ours begins the MSX-DOS date prompt.

**Boundary lesson (harness):** at `$F368` ours jumps into its deliberately-**relocated high-RAM
kernel** (`$E795` vs stock `$DF57`); the new `trace --resync` walk correctly classified this as a
PERMANENT PC-divergence (no rejoin) — i.e. **instruction-level PC-diff is exhausted past the
kernel-relocation boundary; compare at the BDOS-call level (`callseq`) instead** (calls are at the
canonical `$0005`).

**Blocker #2 (characterise next, DELIBERATELY — not by reflex probing):** at the date prompt ours
prints a **malformed date** — stock prints `"84-01-01"` (the MSX-DOS 1984 default, 8 chars, then
STROUT+BUFIN at the input wait), ours prints garbage (`" 3-00-00…"`, 10+ chars) and **loops**
(callseq call-count is nondeterministic 18 vs 60 across boots; ours does NOT cleanly reach `A>`).
Likely ours' **GDATE/clock read or date-string formatting** in the relocated kernel, and/or the
headless-BUFIN re-prompt ([[tier2-storms-are-downstream]] noted "BUFIN never blocks → re-prompts").

**Characterised 2026-06-27 (deliberate, anchored):**
- The n=4 **SDATE call is byte-identical** on both (B=C9 DE=D2C4 HL=C924) → the date being *set*
  is the same; the bug is in the **readback/format**, after SDATE.
- `trace --anchor 0xCC04 --resync` (SDATE return): the date readback **forks first at `$F368`**
  (the segment-switch hook into ours' relocated `$E795` kernel) and does NOT re-converge → the
  date path runs **inside the relocated kernel**, so PC-diff is exhausted (use BDOS-level/effect).
- Reviewed ours' `wa_seg_rom`/`wa_seg_ram` bodies ([kernel.asm:431](../kernel.asm:431)): RMW only
  the page-1 subslot bits (mask `$F3`) of slot-3 `$FFFF`+SLTTBL, register-transparent. **Looks
  contract-correct for the CF-3300 expanded-slot layout** — so blocker #2 is probably NOT a naïve
  wa_seg error. Suspects, in order: (1) the date DATA the kernel reads from under page-1 RAM is
  uninitialised/wrong in ours (a work-area cell, $F338-style); (2) a relocated date-format routine
  bug; (3) the wa_seg EFFECT differs subtly on a non-CF-3300 host (BIOS-agnostic concern).
- **LOCALISED 2026-06-27** (`capture --at 0xCE5C --nth 5 --mem`): the date-digit string buffer
  differs — stock `$D349+` = `31 39 38 34 2D 30 31 2D 30 31` = **"1984-01-01"** (the MSX-DOS
  default), ours = `20 33 2D 30 30 2D 30 30` = **"  3-00-00"** garbage. So ours builds a **garbage
  date VALUE** (year≈3, month 00, day 00) where stock has the 1984-01-01 default. (Not a pointer
  bug — the string data itself is wrong.) **This is the `$F338` pattern again:** an uninitialised
  DOS work-area region (the system date cells) that stock's disk-ROM boot defaults and ours leaves
  garbage. NB the n=4 SDATE params were identical, so the SET is fine — the DISPLAY reads a
  separate (uninit) date source.
- **PINPOINTED 2026-06-27** (`omsx_session.write_watch($D349)`): the diverging write is **W06 at
  PC=`$CE4A`** (COMMAND.COM canonical, `ld (hl),a` in the date-format loop). Inputs there: stock
  DE=`$0101` (month 1 day 1) → stores `'9'`; ours DE=`$0000` → stores `'3'`, then **re-writes
  `$D349` repeatedly (W07-W09) = the loop**. So **ours' date value is ZERO at format time** where
  stock's is the valid default. (W01 @ `$036A` had BC=`0101` on BOTH early — the date was fine
  early, ours reads zero at format time.)
- **ROOT-CAUSED 2026-06-27 → hypothesis (b), at scale.** Decoded COMMAND.COM's date formatter
  ($CDA0-$CE4F: `$CE24` converts regs B,C,D,E via the ÷10 routine `$CE41`; `$CDA7 ld a,($F30E)`
  selects date ordering). `capture --at 0xCDA7 --mem 0xF300:0x20`: **`$F300-$F31F` is 29/32 bytes
  `$FF` in ours vs `$00` in stock** (`$F30E`=`$FF` ours / `$00` stock; `$F30D`=`$01` stock). The
  date regs are already wrong on entry (ours DE=`$0000`/BC=`$0003` vs stock `$1354`/`$0101`). So
  **ours leaves a whole DOS work-area swath uninitialised ($FF)** that stock's disk-ROM boot zeroes
  — the `$F338` pattern AT SCALE. Note `$F300-$F31F` ⊂ the `$F1C9-$F37F` range the **original
  phase-1 clear/default** targeted → **blocker #2 VINDICATES phase-1's clear thesis**: `$F338` was
  one cell of a broader need.
- **EXTENT CHARACTERISED 2026-06-27** (region-diff `$F1C9-$F37F`, classified — user chose
  "characterize first"). 439 B: **137 match, 32 ours-built (preserve: hooks/RAMAD/SYSTEM/DRVTBL/
  RES_*), 270 uninit ($FF ours / defined stock)**. The 270 split:
  - **128 = stock `$00`** → memset.
  - **142 = stock real CONTENT** → not defaults but CONSTRUCTED code+data: executable RAM-resident
    routines (`$F1D0-$F216` CD/C3/EDB0; `$F327`=`3E 1A C9`; `$F365`=`DB A8 C9`=`in a,($A8);ret`),
    data tables (`"PRN LST NUL AUX CON"` device names, `1F 1D 1F 1E…` days-per-month, `"AUTOEXEC
    BAT"` FCB @ `$F2B8`), pointers/flags (`$F30D=01`, `$F37E=31`, `$F195` ptr).
- **STRATEGIC: blocker #2's true extent = the FULL DOS work-area construction** (resident code +
  structures stock's disk-ROM builds), NOT a clear/default — exactly the deferred big sub-track in
  [tier2-workarea-map.md](tier2-workarea-map.md) ("~250 B resident code"), now concretely motivated
  (it's what's between us and `A>`; the date is just its first reader). `$F338` + the date were the
  visible tips. **HARD-STOP — user decision needed:** (A) commit to building the work-area
  construction (270 cells: 128 memset + 142 clean-room code/data, DOS-only, BASIC-protected — the
  deepest Tier-2 work, multi-session); (B) narrow to the minimal subset the DATE path reads (needs a
  read-watch to enumerate; smaller but likely whack-a-mole); (C) reconsider. Recommend (A) but it's
  a big commit; this connects to the parked phase-1 + workarea-map — revisit those as the spec base.

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
