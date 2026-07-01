<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 M15 spec — DRAFT — restore BDOS func-9 (STROUT) console output

**Status:** DRAFT, no asm. Awaiting sign-off (spec-before-implementation).
Resume board: [tier2-STATE.md](tier2-STATE.md). History: [tier2-review-queue.md](tier2-review-queue.md) M14.

## 1. Goal
Make COMMAND.COM's banner/date-prompt lines render, so we can drive to a visible `A>`.
Concretely: BDOS func-9 (STROUT) must emit its `$`-terminated strings to the console on
ours the way func-2 (CONOUT) already does. Success = `screen --machine ours` shows
`COMMAND version 1.08` / `Current date is Sun 84-01-01` / `Enter new date: ` as distinct
lines matching stock's layout, with Tier-1 green and net-zero `disk.rom` (16384 B).

## 2. What M14 established (do not re-probe — all black-box, arbiter-backed)
Anchored at COMMAND.COM `$0100`, `disk_probe_diff.py`, test.dsk:
- **Dispatch is byte-identical.** `--log 0x0005` → ours == stock for all 18 BDOS calls
  (STROUT×3, FOPEN, GDATE, CONOUT×12, BUFIN). COMMAND.COM issues every STROUT correctly;
  the bug is downstream of dispatch.
- **func-2 CONOUT works; func-9 STROUT emits nothing.** `--log 0x00A2` (CHPUT) → stock 72
  chars, ours only the 12 date chars (the `C=02` CONOUT calls, via our `$5454` conout_body,
  `ret=7934`). Every `C=09` STROUT char is absent. `screen` (arbiter) confirms.
- **func-9's char-output loop never runs on ours.** `--log 0xF392` → ours 0 / stock 90;
  `--log 0x009C` (CHSNS per-char break-poll, B=char) → ours 0 / stock 72. So ours' func-9
  handler dispatches but never enters the output loop — the resident `$F392` routine
  (CHSNS-poll + CHPUT per char) is never reached. func-2 reaches CHPUT via a *different*
  path (`$5454`) that ours already wired.

**Interpretation (shape, not yet the exact cell):** the loaded MSXDOS.SYS kernel routes
func-9 output through a console/output routine that on stock is live (the `$F392` resident
routine) and on ours is unreached or a stub. This is the same class as the `$4462` FOPEN
gap (§8.66): a shared-kernel routine present on stock, not wired on ours. Ours wired the
func-2 CONOUT path (`$5454` conout_body, M10) and the CONIN path (`$50E0`, M13) but not the
func-9 STROUT output path.

## 3. Open pin — the ONE thing to nail before asm (spec step 1, no asm, clean-room-safe)
**Which cell/mechanism selects func-9's output routine, and why does ours skip the loop?**
Two shapes, distinguished by where the loaded kernel gets its output-routine address:
- **(P-vector)** the kernel calls its console-output routine through a WORK-AREA vector
  (a JP hook / device-handle / DOS pointer-block cell in `$F1xx-$F3xx`). On ours that cell
  is unbuilt (FF/00) or points to a `ret`/stub, so the loop body never runs.
- **(P-resident)** the kernel calls a fixed resident address (`$F38x`) that IS a disk-ROM-
  installed routine on stock (built during work-area construction) but that ours never
  installs, so the address holds no valid routine.

**How to pin it clean-room-safely (no kernel decode):**
1. `capture --at 0x0005 --nth 1 --mem <narrow work-area pointer region>` at the aligned
   first func-9 STROUT dispatch, diff ours vs stock — read only POINTER/FLAG cells (data,
   the allowed RAM-pointer-walk kind), NOT any resident-code region (`$F380-$F3A0` bytes are
   off-limits — reading them = reference disasm). A cell that is a valid pointer on stock and
   FF/00/self-`ret` on ours is the smoking gun (P-vector).
2. If no data cell differs, it is P-resident: confirm by reading ONLY ours' `$F38x` for
   FF/00 (one-sided, our own build's RAM — allowed); do not read stock's bytes there.
Candidate regions from prior mapping: DOS pointer block `$F34D-$F37F`, `$F368` jump table,
device/handle cells near `$F21C`/`$F2B8`. Keep the capture window narrow and pointer-only.

## 4. Fix approaches (choose after step 3 pins the mechanism)
- **(A) Wire func-9 to our existing CONOUT.** Point the pinned vector/resident slot at a
  small routine that loops the `$`-terminated string and calls our `conout_body` (`$5454`)
  per char — the SAME working routine func-2 uses. Reuses proven code; no new console
  primitive; clean-room (our own CONOUT + published func-9 contract). Preferred if P-vector.
- **(B) Build the resident output routine ours is missing.** If P-resident, install our own
  routine at the resident slot during DOS-path work-area construction (net-zero, DOS-only,
  BIOS-agnostic per [[cbios-target-cf3300-oracle]]), body = the same string loop → `$5454`.
- **Rejected:** copying stock's `$F392` routine bytes (reference-disasm ✗); a blanket
  redirect of `$0005`→our bdos_entry (the overturned fork-B, §8.66 — heavier, and func-2
  already works so a wholesale swap risks regressing it).

**Recommended default:** approach (A) — least code, reuses `conout_body`, and matches how
we already handle func-2. Confirm the vector is DOS-only so Tier-1 BASIC is untouched.

## 5. Clean-room firewall
- Derive from published BDOS func-9 (STROUT: print `$`-terminated string at DE) + CHPUT
  `$00A2` / CHSNS `$009C` BIOS contracts + our own `conout_body`. Never read/transcribe the
  loaded kernel's `$F392`/`$F2AC`/`$F237` console-routine bytes (M12c hazard).
- Black-box only for pinning: call-counts, register/pointer captures, one-sided reads of
  OUR RAM. No `trace` mnemonic decode on stock or on loaded-kernel PCs.

## 6. Invariants / acceptance test
- `screen --machine ours --settle 16` renders the three COMMAND.COM lines matching stock.
- `callseq --log 0x00A2` ours now emits the full ~72-char stream (was 12).
- `--log 0x009C` ours now fires per-char (was 0), matching stock's break-poll count.
- Tier-1 green: `make unit-test` 19/19; DSKIO/BLOAD/FILES == CF-3300 on C-BIOS + CF-3300.
- Net-zero: `disk.rom` == 16384 B; no canonical-address shifts. M13 CONIN regression intact
  (`--log 0x009F` 1 call idle).

## 7. §3 PIN RESULT (2026-07-01, no asm) — leans P-resident; SCOPE SHIFT flagged
`capture --at 0x0005 --nth 1 --mem 0xF340:0x40` (aligned first func-9 dispatch; **register diffs
NONE** ⇒ trustworthy). Ours' DOS work-area page-3 is **substantially unbuilt/divergent**:
- FF where stock has data: `$F345`, `$F347`, `$F358-$F367` (incl. stock `$F365`=`DB A8 C9`).
- pointer block `$F34D-$F356` diverges (stock → `$EF95`/`$F195`; ours → `$E8xx`).
- `$F368` JP-table half-stubbed on ours: stock → `$DF57/$DF59/$DF70/$F327/$F32C/$F331`; ours →
  `$E795/$E79B` (M5.6's two) then `$41AF`×5 stubs. (Established-clean pointer read, per M5.5.)
**⇒ NOT P-vector (a single settable cell). It is P-resident:** ours builds only part of the
resident DOS work area; func-9's output routine (`$F38x`, uncaptured for clean-room) is very
likely in this unbuilt block. This connects M15 to the **DOS work-area construction sub-track**
(§8.52/§8.65), so approach **(B)** — not (A) — is the likely shape, and the fix is heavier than a
one-line vector poke.
**CAVEAT (do NOT skip — §8.65 was a mis-conclusion of exactly this kind):** "unbuilt" is proven,
"unbuilt CAUSES func-9's skip" is NOT yet — I have not shown func-9 causally reads/calls a specific
stubbed/FF cell on its failing path. The clean confirming step (no asm) is a **read/call-through
watch on the func-9 path** (does it hit `$41AF`/read an FF cell before returning?), which needs a
small `disk_probe_diff.py` write/read-watch extension. **Gate the fix behind that confirmation.**

## 8. Open items (recommended defaults in bold)
- OI-1: P-vector vs P-resident → **RESOLVED: leans P-resident (§7); confirm causality first**.
- OI-2: is the func-9 output path DOS-only or shared with BASIC? → **must be DOS-only /
  BIOS-agnostic; validate FILES on C-BIOS + CF-3300 unchanged**.
- OI-3: does fixing func-9 also fix the un-cleared BASIC banner (secondary symptom)? →
  **treat as separate; defer, re-`screen` after M15 lands**.
- OI-4 (NEW): scope — is func-9's output path a TARGETED build (just its resident routine/hook) or
  does it drag in the broader work-area construction? → **needs the §7 causal confirmation to bound;
  hard-stop for user scope steer before committing to the sub-track**.
