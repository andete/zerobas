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

## 7.1 CAUSAL CONFIRMATION (2026-07-01, no asm) — BOUNDED to wa_seg, not the broad work area
New `readwatch` mode (`disk_probe_diff.py`, gated to during-func-9, DATA-region only, no code
decode): reads of `$F340:0x40` while a `C=09` BDOS call is in flight.
- **STOCK func-9 output loop pages via the segment-switch hooks:** `$F368`→`JP $DF57` executed
  **46×**, `$F36B`→`JP $DF59` **45×**; those read slot bytes `$F342`(=83, PC `$DF5A`) /
  `$F348`(=87, PC `$DF60`); the `$F365` `in a,($A8)` slot-read stub executed **12×**.
- **OURS:** `$F368`→`JP $E795` / `$F36B`→`JP $E79B` (our M5.6 `wa_seg_rom`/`wa_seg_ram`) executed
  only **3× each, then the loop aborts** — `$F365` is FF/unbuilt (never executed), CHPUT never
  reached.
**⇒ CAUSAL (passes the §8.65 guard): func-9's output loop demonstrably routes through the
`$F368`/`$F36B` segment hooks on BOTH machines; ours' `wa_seg` can't sustain the paging pattern
(≈1 switch per STROUT then gives up).** This is the **§8.57 "M5.6 `wa_seg` is an INCOMPLETE `$DF57`"**
thread, now tied to func-9 output. **Scope is BOUNDED: complete `wa_seg` (+ the `$F365` slot-read
stub), NOT the broad work-area construction.**
**HONESTY on the §8.61 tension:** M5.8/§8.61 judged the `$F368` hook "returns register-identical /
rejoins" and moved on — but that was in the earlier-blocker context; func-9 output exercises the hook
in a 45×-iteration paging pattern ours can't sustain (3×). So this is a NEW manifestation, not a blind
re-walk. Still-open (needs asm to test, hence sign-off): the EXACT reason ours aborts at 3 (wa_seg
wrong result vs a downstream check) — pin by tracing OUR OWN `wa_seg` (`$E795`, decodable=ours) once
signed off, or by a falsify-first "complete wa_seg → does CHPUT fire" build.

## 8. Open items (recommended defaults in bold)
- OI-1: P-vector vs P-resident → **P-resident (§7 stands), but the "+`$F365` stub is the
  bounded fix" half is FALSIFIED — see §7.3. The fix shape is (B) but LARGER than `$F365`.**
- OI-2: is the func-9 output path DOS-only or shared with BASIC? → **`wa_seg` is DOS-path; must stay
  BIOS-agnostic + net-zero; validate FILES on C-BIOS + CF-3300 unchanged**.
- OI-3: does fixing func-9 also fix the un-cleared BASIC banner (secondary symptom)? →
  **treat as separate; defer, re-`screen` after M15 lands**.
- OI-4: scope → **REOPENED (§7.3): completing `wa_seg`+`$F365` alone does NOT unblock func-9
  (falsify-first build, real asm, negative result) — the bound claimed in §7.1 was premature.
  Scope is larger than "wa_seg + one 3-byte stub"; likely still short of the full broad
  work-area sub-track, but not yet re-sized.**

## 7.3 Falsify-first build (2026-07-02) — NEGATIVE: `$F365` completion does not unblock func-9
Implemented exactly the §7.1/OI-5 bounded fix and rebuilt: `install_f365` (kernel.asm) LDIRs a
clean-room `IN A,($A8); RET` stub (i8255 PPI primary-slot-select register, MSX2 TH ch.2 /
docs/allowed-sources.md class A — never read from the stock ROM) to the fixed address `$F365`,
called via a 3-byte `call install_f365` from `build_resident` (init.asm). Net-zero (`disk.rom` =
16384 B), Tier-1 green (`make unit-test` 19/19 incl. `test_getdpb`/`test_gdate`).

**Harness gotcha hit while building this (not a clean-room issue, a pasmo one):** the cramped
pre-`$41FD` region `build_resident` lives in (§M5.6) has ZERO slack — inlining a second
ld/ld/ld/ldir there (11 B) silently overflows the `ds $41FD - $` canonical anchor in
pageenv.asm. Symptom: pasmo's 3-pass/symbol-table (`--sym`) mode emits a valid symbol file but
an EMPTY (0-byte) object file, no error printed; plain 2-arg mode "succeeds" at the right file
size but the content past the overflow point is not to be trusted either. Fixed by moving the
copy to a real `install_f365` routine in the free tail (no budget limit) and calling it with a
single 3-byte `call` instead of inlining the 11-byte sequence. **Lesson: after ANY change that
adds bytes to a `build_*` routine before `$41FD`, rebuild with `--sym` (3 positional args) and
check the object file size, not just exit code — 2-arg mode does not surface this class of
overflow.**

**Result — the stub is live but never reached:** rebuilt, re-ran the OI-5 caller probe
(`$F368`/`$F36B`/`$F365`/`$0038`, gated to `C==9`). **Identical to before the fix**: `$F368`/
`$F36B` still fire exactly 3 times total (one round-trip per STROUT call, at BDOS call-index
1/3/17 — unchanged), and `$F365` is **never hit** (0 occurrences, same as pre-fix). `screen
--settle 30` renders identically to before (only the pre-existing sign-on + date line; no
COMMAND.COM banner/prompt lines). `callseq --log 0x00A2`: ours still 12 calls (all pre-COMMAND.COM
date/sign-on chars) vs stock 72 — CHPUT count unchanged.
**⇒ Completing `wa_seg` + `$F365` does NOT unblock func-9 output.** The early-exit-after-one-
round-trip happens BEFORE the kernel ever reaches a call to `$F365` (stock only calls it 16× across
LATER iterations); whatever decides to stop after iteration 1 is upstream of `$F365` entirely. §7.1's
"BOUNDED to wa_seg + $F365" claim is falsified — this is genuinely useful negative information
(the cheap experiment the guardrails call for), not wasted work, but it means OI-5's real
mechanism is still open and likely larger than a single 3-byte stub. The `$F365` stub itself is
harmless/correct (published contract, net-zero, Tier-1 green) and was left in the tree since it's
still part of the eventual real fix, but it does NOT close M15 on its own.
**Next (unresolved):** find what, immediately after the `$F368`/`$5454`-adjacent window (caller
`$D888`/`$D88E`/`$D88A`; see §7.2), makes the kernel exit after exactly one char/iteration on ours
but continue ~15-45× on stock. `$D88A` is the SAME call site `conout_body`'s own doc (runtime.asm)
already names for CONOUT's per-char output — meaning CONOUT and STROUT likely share this exact loop,
so the fault is probably NOT in the shared loop body itself (CONOUT works) but in whether/how STROUT's
caller reaches or re-enters it per char. This needs either a decode-free structural hypothesis test
(a further falsify-first build) or reopening the broader work-area-construction framing
(tier2-workarea-map.md) that OI-4 had prematurely set aside.
- OI-5: the exact reason ours' `wa_seg` aborts func-9 → **PARTIALLY PINNED (§7.2, no asm, all
  black-box/no-decode). Still needs a falsify-first build (sign-off gate unchanged) to nail the
  exact read.**

## 7.2 OI-5 partial pin (2026-07-02, no asm) — corrects the "3 iterations" framing; caller identified
**Harness prerequisite:** this session's trace also fixed a clean-room gap in the harness itself
(`probes/disk/omsx_session.py`'s `DISOK` gate was a blanket `PC >= 0x4000` on the ours-host, which
decoded the loaded MSXDOS.SYS kernel's own resident code whenever a trace on ours returned into it —
a breach of the same class as the 2026-06-30 one. Fixed with an `OWN_RAM_RANGES` allowlist +
`own_code` Tcl proc; that decoded kernel trace was discarded, never used for any conclusion below).

New black-box facts (call-site + register capture, zero instruction decode):
- **The `wa_seg` (`$F368`/`$F36B`) calls during func-9 are NOT routed through `RES_PRINT` ($F1C9).**
  A caller probe (breakpoints at `$F368`/`$F36B`, gated to `C==9`, logging the return address off the
  stack) shows the caller is a FIXED kernel site: `$F368`→ret `$D888`, `$F36B`→ret `$D88E`, every time.
  `$D8xx` is outside `RES_PRINT`'s 7-byte range — func-9 has its own dedicated loop in the loaded
  kernel; `RES_PRINT` (built by `build_resident`, §8.28) is a DIFFERENT call path (the $50A9-time
  message), not func-9's. **This corrects the working assumption in §2/§4 that `RES_PRINT`'s stub
  body is on the STROUT path — it is not; leave `RES_PRINT` alone, it is unrelated to this bug.**
- **Corrects the "3 iterations in one STROUT call" framing (§7.1).** The 3 hits are one
  `$F368`+`$F36B` pair each, at BDOS call-index 1, 3, and 17 (i.e. the 3 SEPARATE `C=9` STROUT calls
  COMMAND.COM issues) — **every single STROUT call manages exactly ONE segment-switch round-trip,
  never more**, not "one call does 3 then aborts." Matches CHPUT never firing (M14): the loop exits
  before ever reaching output, every time, on the very first iteration.
- **No register divergence at the shared entry point.** `capture --at 0xD88E --nth 1` (first-ever hit
  on either machine): AF/BC/DE/HL/IX/IY/SP **byte-identical** ours vs stock. `wa_seg` itself
  introduces no register-level effect beyond contract (confirms §8.58's transparency claim still
  holds); the divergence is a MEMORY read in the next few instructions, not a register.
- **Page-1 low window is not it.** `readwatch --range 0x4000:0x20` (gated func-9) → **zero reads**,
  both machines. Whatever `$F368`'s "run a page-1 disk-ROM routine" step touches, it is not the first
  32 bytes of page 1; narrowing the exact cell needs a wider/relocated `readwatch` sweep or the
  falsify-first build below — do not assume the low window and move on blind.
- **A direct forward PC-trace from `$D88E` is confounded by interrupt timing**, not useful as-is:
  stock takes a hardware interrupt (`$0038`→`$DDAE`) at the very next step, ours doesn't; `--resync`
  found no reconvergence in a 200-instr window. This is very likely benign 60 Hz timing jitter (ours
  and stock reach this logical point at wildly different wall-clock instants: t=7.88s vs t=11.45s), not
  a real fork — but it makes naive PC-stream diffing at this exact instant unreliable. Do not read this
  as "the interrupt is the bug" without more evidence; it just breaks the diff mechanism locally.

**Net:** OI-5 is narrowed (dedicated kernel loop, not `RES_PRINT`; one round-trip per call, not three;
no register-level fault) but NOT closed — the exact wrong-byte/wrong-check has not been pinned. The
next black-box step (still no asm) would be a broader `readwatch` sweep beyond `$4000:0x20` for the
byte the loop actually compares against `$` around `$D88E`+few instrs; failing that, this is the
falsify-first-build gate the spec already called for (§7.1: sign-off before ANY asm).
