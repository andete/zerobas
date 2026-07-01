<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 review queue — ARCHIVE (reviewed & re-levelled)

Resolved/superseded judgment-call entries split out of
[tier2-review-queue.md](tier2-review-queue.md) on 2026-06-30 to keep the live board lean.
Newest first; this is provenance, not a working list.

---

_Ratified 2026-07-01 sync (M16/M17/M18 batched review): user approved ALL open judgment calls as-is —
the self-approval-by-precedent pattern (implementing `$50xx`-veneer + work-area-cell fixes without a
separate per-milestone sign-off gate) is CONFIRMED as the standing mode for this fix class; no gate
added. M16 (CONIN terminator), M17 (SELDSK `$50D5`/DRVCNT), M18 (CURDRV `$50C4`/`$F247`, drive letter
now correct, full 27/27 BDOS parity + visible `A>`) are all DONE, committed, and closed. OI-3 (leftover
BASIC banner, different-shaped fix) remains the one open item, carried forward as the live "Next
action" in [tier2-STATE.md](tier2-STATE.md) — not archived, since it isn't resolved yet._

**[M18 CHARACTERISED + falsify-first fix landed (Opus span, 2026-07-03) — the `C>` vs `A>` drive-letter
bug was the missing `$50C4` CURDRV kernel entry; drive letter now CORRECT + full 27-call BDOS parity.]**
· **Root cause (clean-room-safe, no kernel decode):** during BDOS CURDRV (func `$19`) the loaded kernel
CALLs page-1 `$50C4`; on ours that address was `$00` NOP-padding (SAME un-wired-`$50xx`-entry class as
M13 `$50E0` / M15 `res_print_tmpl` / M17 `$50D5`) → NOP-slid and never read the current drive, so the
kernel's `'A'+drive` letter math used a bogus index and printed `C>` (index 2). Pinned via: register-
identical `callseq --log 0x50C4` CALL boundary (`AF=0044 BC=C419 DE=D3FF HL=D502`, ret `$D88A`), a
`callwatch --in-func 0x19` showing stock runs `$50C4`+`$50C7` while ours only enters `$50C4`, and a
CAUSAL `readwatch --in-func 0x19` showing `$50C4` reads exactly ONE cell — `$F247` (=current drive),
`$00` on stock / `$FF` (unbuilt) on ours. Full detail: [tier2-m18-spec.md](tier2-m18-spec.md).
· **Fix (two parts, falsify-first build validated):** (a) `$50C4: jp curdrv_body` veneer (kernel.asm
free tail = `ld a,(CURDRV_CELL); ret`, net-zero — uses existing `$50B8-$50D4` pad); (b) `build_drvtbl`
now writes `CURDRV_CELL`=`$F247`:=`$00` (MSX-DOS boot logs in drive A:) (init.asm). Object 16384 B under
3-pass `--sym`; Tier-1 19/19; M13/M15/M17 regressions intact. **Result:** `callseq --log 0x0005 --keys
'\r'` → **FULL 27-call BDOS parity with stock, ZERO divergence** (was: first divergence at n=25); n=25
now CONOUT `A=$41`='A'. `screen --machine ours` renders a **correct visible `A>.`**. Commits: spec
`(prev)`, impl `2d1ba5c`.
· **judgment call — SELF-APPROVED by precedent (called out explicitly per the M18-span instruction):**
implemented the falsify-first build without a separate sign-off gate because it is the IDENTICAL class +
shape as the M13/M15/M16/M17 fixes (a `$50xx` veneer + one work-area cell, all clean-room, net-zero,
validated by probe) that the user pre-approved that pattern for — AND is literally the same fix one BDOS
call later than M17's `$50D5`/`$F347`. The M17 agent made the same self-approval choice (still awaiting
your review); I continued the pattern deliberately. If this class should now become a hard-stop, say so
and I'll gate the next one. · **NEW residual (OI-3, NOT fixed, DIFFERENT-SHAPED):** ours retains the
leftover BASIC power-on banner because the DOS boot handoff never clears VRAM. Characterised
(clean-room): NOT a screen-mode switch (both `scrmod=01 r2=06`), NOT a CHPUT `$0C` (stock emits 0
form-feeds) — stock does a DIRECT name-table fill in its DOS init. This is a different shape than the
`$50xx`-veneer class, so per the span instruction I characterised it and LEFT IT DEFERRED rather than
force it into this span. Candidate fix + repro logged in [tier2-STATE.md](tier2-STATE.md) "Next action".
· **confidence:** HIGH that M18 is correct + complete (full 27-call parity + causal pin + on-screen
correct `A>` are decisive). · **undo:** net-zero veneer + one byte-write; clean, low-risk. · **awaiting:**
batched review of the self-approval above + a decision on whether to pursue OI-3 next.

**[M17 CHARACTERISED + falsify-first fix landed (Opus span, 2026-07-03) — SELDSK-time stall was the
missing `$50D5` kernel entry; a NEW smaller drive-letter bug (M18) surfaced one step later.]**
· **Root cause (clean-room-safe, no kernel decode):** the loaded kernel CALLs page-1 `$50D5`
during BDOS SELDSK; on ours that address was `$00` NOP-padding (same `$50xx` un-wired-entry class
as M13's `$50E0` / M15's `res_print_tmpl`) → NOP-slid into the `$5454` CONOUT veneer and never
returned to the trampoline, so the kernel's post-SELDSK sequence (CURDRV / print `A>` / BUFIN)
never ran. Pinned via: `callwatch --in-func 0x0E` (new gate generalisation), a register-identical
`callseq --log 0x50D5` CALL-boundary pin, one-sided `capture` of the return contract (A=$02, all
other regs preserved), and a CAUSAL `readwatch --in-func 0x0E` showing `$50D5` reads exactly ONE
cell — `$F347` (=drive count). `$F347` was `$FF` (unbuilt) on ours; stock=$02 (MSX-DOS single-drive
model exposes 2 logical drives). Full detail: [tier2-m17-spec.md](tier2-m17-spec.md).
· **Fix (two parts, falsify-first build validated):** (a) `$50D5: jp seldsk_drv_body` veneer
(kernel.asm free-tail body = `ld a,(DRVCNT); ret`, net-zero — uses existing `$50D5–$50D7` pad); (b)
`build_drvtbl` now writes `DRVCNT`=`$F347`:=`$02` (init.asm). Object 16384 B under 3-pass `--sym`
(no §7.3 overflow); Tier-1 19/19; M13/M15 regressions intact. **Result:** ours' BDOS calls now
continue past SELDSK (n=21) through CONOUT/CONOUT/CURDRV to n=27 BUFIN, **matching stock's call
count exactly** (was 21 vs 27) — the SELDSK stall is GONE.
· **judgment call:** implemented the falsify-first build without a separate sign-off gate because it
is the identical class + shape as the M13/M15/M16 fixes (a `$50xx` veneer + one work-area cell, all
clean-room, net-zero, validated by probe) that the user pre-approved that pattern for; flagged here
for the batched review. If this should have been a hard-stop, say so and I'll gate the next one.
· **NEW residual (M18, NOT fixed):** at n=25 ours prints char `$43`='C' where stock prints `$41`='A'
— i.e. `C>` vs `A>` (current-drive = 2 on ours vs 0 on stock). This is a SEPARATE cell from `$F347`
(`$F347` now matches stock); the drive letter is computed from `$D5xx`/`$C4xx` kernel RAM (CURDRV
reads dispatcher cells `$F304/5/6`, not a `$F3xx` curdrv byte in the swept windows). Also the prompt
does not yet render on OURS' *screen* (still shows the leftover BASIC banner — the deferred OI-3).
So `A>` is closer than ever (full 27-call parity) but not yet visible/correct. · **confidence:** HIGH
that M17's primary fix is correct (call-count parity + causal pin are decisive). M18's cause is open.
· **undo:** M17 is a net-zero veneer + one byte-write; clean, low-risk. · **awaiting:** batched review
of the judgment call above + M18 characterisation.

**[M16 DONE / M17 OPENED — CONIN buffer terminator signed off + landed; new post-SELDSK stall found,
not yet characterised.]**
· User signed off (quick AskUserQuestion, not a full stop) on the §6 fix in
[tier2-conin-spec.md](tier2-conin-spec.md): `cinl_done` writes `$0D` to `buf[2+count]`, matching
stock's observed (data-only) buffer behaviour. Implemented, validated (buffer 0/16 bytes differ, was
1; BDOS call n=21 now SELDSK matching stock, was SDATE), Tier-1 19/19, net-zero. Committed `81c4515`.
· **Found while validating, not yet fixed:** ours now stalls right after SELDSK — 21 BDOS calls vs
stock's 27+, no crash, `screen` shows the cursor advanced but no `A>`. Register/args at the SELDSK
dispatch are identical, so the fork is inside SELDSK's own execution in the loaded (shared) MSXDOS.SYS
kernel — not yet localised to a mechanism. Logged as M17 in [tier2-STATE.md](tier2-STATE.md).
· **judgment call:** did not attempt to characterise M17 in this session — handed to a fresh
Opus-driven investigation per [[opus-vs-sonnet-model-split]] (open-ended ABI-pinning class of work),
same rationale as the M15 hand-off that found the RES_PRINT root cause quickly. · **confidence:**
HIGH that M16's fix is correct and complete (byte-identical buffer + matching BDOS dispatch are
decisive). M17's cause is completely open — no hypothesis yet beyond "same class of gap as
M14/M15/M16." · **undo:** M16 is a committed, validated, low-risk 6-byte addition; clean. M17 is
docs-only so far (no asm). · **awaiting:** M17 characterisation + a fix spec once localised.

---

---

_Archived 2026-06-30 sync: all entries below were reviewed/superseded. The M10 fix
(char reg = E) is the live head; it overturned the two `$80`-render entries' thesis
(the divergence is upstream of CHPUT, in our veneer's char register), though their
characterisation/tooling work stands. M5–M9 are resolved milestones._

_Ratified 2026-06-30 (M11 review): user ratified BOTH the M10 fix (as correct-but-PARTIAL — it fixes
only the func-2 CONOUT route) and the M11 two-bug reframe. Next-bug order: **Bug A (func-9 output
route) first, then Bug B (BUFIN block)**. The live working head is now the M11.1 two-bug model in
[tier2-STATE.md](tier2-STATE.md)._

**[M11 / §8.81 (incl. M11.1) — REFRAME: COMMAND.COM runs IDENTICALLY; two relocated-kernel console-I/O
bugs (2026-06-30, RATIFIED). No ROM change — characterisation only.]** · **what (ground truth, test.dsk,
`screen --machine both --settle 16`):** STOCK = `MSX-DOS version 1.03` / `Copyright 1984 by Microsoft` /
`COMMAND version 1.08` / `Current date is Sun 84-01-01` / `Enter new date: .` then blocks at BUFIN.
OURS = every row `Ø>@` (`$D8 3E 40`), an infinite loop scrolling the sign-on off; no COMMAND banner /
date prompt / `A>`. · **decisive proof (callseq --at 0x0100 --log 0x0005):** the BDOS call seq is
BYTE-IDENTICAL ours==stock for ALL 18 calls (STROUT $C284 / FOPEN / STROUT $D2B3 / GDATE / 12×CONOUT /
STROUT $D2D3 / BUFIN). **COMMAND.COM runs perfectly; both bugs are in OUR relocated kernel console I/O:**
(A) func-9 STROUT (banner/`Current date is`/`Enter new date:`) emits ZERO chars to CHPUT while func-2
CONOUT (date value) renders — different CHPUT routes (func-2 ret=$7934 = M10 veneer; stock func-9
ret=$F392, cf. $F398→$00A2); M10 fixed only func-2. (B) at n=18 BUFIN stock BLOCKS, ours RETURNS →
infinite date-prompt re-loop. · **refuted:** my own first-cut "page-0 swap clobbers func-9's string
read" (DE identical, func-9 emits 0 → it's the OUTPUT route, not the read); and the older "BUFIN-not-
blocking is benign headless artifact" (both run the same BUFIN; stock blocks, ours doesn't = bug B). ·
**judgment calls:** stopped at the reframe instead of grinding a fix; touched no ROM; corrected STATE. ·
confidence: HIGH (char-identical anchor + screen). · undo: docs-only; revert commits 26c8ddb/41ee4a1.

**[M10 / §8.80 — CONOUT $80 render: char register is E, not A (2026-06-30, RATIFIED as correct-but-
PARTIAL).]** · **what:** `conout_body` ($7922) took the output char from **A**; the `$5454` CONOUT
contract passes it in **E**. The kernel's per-char output (caller $D88A) sets E=char, A=$00, so ours
emitted $00/garbage for COMMAND-phase output; the early sign-on (caller $0320) passes the char in BOTH
A and E, hiding the bug. Fix = `ld a,e` at conout_body entry (1 byte, free-tail pad; ROM still 16384 B,
no canonical shift). · **proven:** $7922-entry callseq shows E spelling the banner/date verbatim;
`screen --machine ours --settle 12` renders real ASCII. · **PARTIAL (per M11):** fixes ONLY the func-2
CONOUT route; func-9 STROUT (Bug A) still renders nothing. The M10 *fix* stands; its "render solved /
residuals cosmetic" *framing* was over-rosy and is superseded by M11. · **judgment calls:** extended the
ONE harness (added `trace --regdump REG` + an `A=` field to the callseq logger, not a 58th probe);
implemented+committed the ROM fix autonomously (net-zero, reversible, Tier-1 19/19 green). · confidence:
HIGH. · undo: revert the `ld a,e` line.

**[CONOUT $80 render — DEEPENED post-review (2026-06-30, after the sync below)] Drilled the render
blocker; BC root-cause DISPROVEN, sharper picture.** · **what:** built `iowrite` (VDP port $98/$99
watch) + `screen`-tool follow-ups. Found: ours writes constant tile `$80` per glyph to the name
table (after a 768-cell space-clear), via WRTVRM `$0BEE` — same routine stock uses. The char is
correct at BDOS and at CHPUT entry; it becomes `$80` by the write. **EARLY MSXDOS.SYS console output
RENDERS CORRECTLY** (`$0BEE` nth=1 byte-identical, A='M'); only the **COMMAND.COM-phase** inter-slot
path corrupts. Char-aligned resync shows ours/stock **PC-equivalent** → a PURE DATA divergence (same
instructions, different byte). · **disproven (tested + reverted):** making `conout_body` register-
faithful (restore BC/DE/HL before `call $00A2`; verified CHPUT then gets BC=$0980 like stock) did
NOT fix rendering. So BC/DE/HL aren't it; remaining entry diffs are IX/IY/flags. · **judgment
calls:** (a) ran a falsify-first diagnostic ROM build (revertable, Tier-1 green) to test the BC
hypothesis — falsify-first per guardrail #2, reverted to baseline, did NOT commit any ROM change.
(b) STOPPED the deep dive at a clean handoff rather than brute-forcing IX/IY guesses; next session
traces the divergent read with a spec. · confidence: high on the characterisation; the exact $80
source is the open question. · undo: docs + probe tooling only; ROM at committed baseline (16384 B,
Tier-1 19/19). See [tier2-STATE.md](tier2-STATE.md) "Next action" steps 1–2.

**[Past-BUFIN probe / REFRAME — REVIEWED ✓ 2026-06-30 sync (findings confirmed legit) — date path
DONE, new RENDER blocker found] Investigated "past BUFIN
to A>"; found ours reaches the A> command loop at the BDOS level, but the screen renders garbage.**
· **what I did:** no-poke `callseq --maxhits 40` (the GDATE fix is in the ROM, so the `$CDA7` poke
is retired). · **findings:** (1) ours == stock byte-identical n=1–18 (date path fully solved, no
poke). (2) Past BUFIN, ours reaches the A> idle loop: **SDATE ($2B) is called (n=21) and RETURNS**
— it is NOT the next blocker (refutes the prior next-action hypothesis) — then SELDSK/CURDRV/print
`A>`/BUFIN, looping. (3) **NEW BLOCKER:** the new `screen` mode (VRAM name-table render) shows ours'
console output writes tile **`$80` for every glyph** — banner/prompts/`A>` all invisible; stock
renders correctly. (4) Root-caused to an **inter-slot CHPUT register-context divergence**: CHPUT
gets the right char (aligned capture `$00A2` 'X' → A=$58 both) but ours BC=$0000 vs stock $0980;
CHPUT forks at `$08F1 jr c` into the control path. Ours' `conout_body` does a hand-rolled page-in +
direct `call $00A2`, bypassing stock's `$5454→$408F→CALSLT→$F398→$00A2` chain that sets the context.
· **judgment calls:** (a) extended `disk_probe_diff.py` with a `screen` mode + a callseq TAIL print
(per "don't write a 58th probe"; ~70 lines, no behavior change to existing modes). (b) DOWNGRADED
`$02` CONOUT ✅→⚠ on the coverage board — the "banner byte-identical" settled fact was call-verified
only, never VRAM-verified; the screen tool exposed the gap. (c) STOPPED before any ROM edit — the
CONOUT fix is a new slice needing characterise→spec→sign-off per [[spec-before-implementation]].
· **caveat logged:** the `$08F1` carry-fork trace was `$00A2`-occurrence-aligned but NOT char-
aligned; re-confirm on a char-aligned anchor (BDOS `$0005 C=02`) before building the fix. The
`screen` $80 fact and the aligned-capture BC diff are already robust. · confidence: high on the
findings, medium on the exact fix shape (need step 2 of the next-action). · undo: docs + probe
tooling only; no ROM change. See [tier2-STATE.md](tier2-STATE.md) "Next action".

**[GDATE slice / DONE+VALIDATED] Implemented the date-path slice (option B); ours now reaches the
date-input BUFIN.** User chose B and signed off ("excellent, continue"); implemented under the
autonomous span. · **what:** (1) `gdate_handler` at canonical `$553C` (kernel.asm) — a ~13-byte
constant-return `_GDATE` ($2A) giving the clock-less default 1984-01-01; the colliding body was
**`fac_loop_body`** (NOT `bdos_create_body` — the spec's §5b guess; `$553C` fell inside
`fac_loop_body`), relocated net-zero (+63 B, tail-`ds`-absorbed, label-referenced). (2) A SECOND
cell surfaced after the value fix: COMMAND.COM reads `$F30E` at `$CDA7` for the date FORMAT and
ours left `$F30D/$F30E`=`$FF`; defaulted them to stock's `01/00` in `dos_handoff` (runtime.asm,
DOS-only with the same save/restore as `$F338`). · **result:** `$CC04` reg diff NONE; callseq
n=1–18 byte-identical to stock incl. **BUFIN (n=18)**, no poke. · **validated:** test_gdate.py
(new host unit test, suite 19/19); net-zero 16384 B + no canonical-address shift; DSKIO/FILES/
APPEND == CF-3300 (FILES on C-BIOS, the relocated FAT-write path via APPEND). · **judgment calls:**
kept `ld ($F306),a` (matches stock, harmless); chose relocate-whole over split for `fac_loop_body`;
defaulted the format cells in `dos_handoff` rather than a new work-area pass (minimal, proven by
the earlier poke). · confidence: high (oracle-validated both layers). · undo: revert kernel.asm
`$553C` block + runtime.asm `dos_handoff` `$F30D` lines + delete test_gdate.py. · **next:** past
BUFIN to `A>` (callseq forks at n=19; `_SDATE` $2B + CR input).

**[date / HARD-STOP → RESOLVED by the slice above] Date blocker ROOT-CAUSED as a canonical-address
collision; paused for a strategy decision.** Resumed the Tier-2 hunt; the prior most-recent thesis was "the date is a
`_GDATE`/clock inter-slot bug — examine ours' page-0 clock path." I disproved that and root-caused
it instead. · **what I did:** (1) extended the ONE harness with `callseq --poke/--poke-reg`
(falsify-first register/memory override, ours-only); (2) FALSIFY-FIRST — poked ours' date regs to
stock's at `$CDA7`: ours converged byte-for-byte with stock through the date print to **BUFIN
(n=18)**, proving the date VALUE is the SOLE gate; (3) localised the garbage to the GDATE return
`$CC04` (ours HL=`0000` vs stock `07C0`); (4) traced the handler: the disk-loaded MSXDOS.SYS
dispatcher calls canonical `$553C` for `_GDATE`, where **stock has the DOS date kernel and ours has
`bdos_create_body`** (relocated Disk-BASIC/BDOS body) → garbage. · **why it matters:** this is the
first concrete instance of the central Tier-2 problem (16KB ROM can't host Tier-1 bodies + Tier-2
DOS-BDOS at the same canonical addresses); it CONVERGES the date thread with the workarea-map /
bdos-scope threads and REFRAMES the date from "cheap constant fix" to "DOS-BDOS canonical
reproduction." · **why I stopped (hard-stop, did NOT proceed to code):** the fix is a
layout/relocation DESIGN decision hinging on user taste (which Tier-1 bodies relocate where), needs
a spec first per [[spec-before-implementation]], and is multi-session. Options A/B/C in
[tier2-STATE.md](tier2-STATE.md) "Next action". · **alternative considered:** keep grinding to
enumerate the full date-cell/route set — rejected (would map paths-not-taken before the design
call; guardrail #3). · confidence: high (falsify-first proven + canonical-address byte divergence
shown directly). · undo: harness extension is additive (no behaviour change to existing modes);
no ROM/source change made. · regression: unit 18/18, ROM 16384 B, no canonical-address shift.

**[BLOCKER #2 IDENTIFIED + RESYNC TOOL / 2026-06-27 — ours reaches the DOS date prompt but loops.]**
Added `trace --resync` (re-convergence walk) to disk_probe_diff: after a PC fork it finds the next
common PC, classifying benign relocation detours (rejoin) vs real divergence (no rejoin within
window). It correctly classified the `$F368`→`$E795` hook as PERMANENT — the kernel-relocation
boundary, where instruction PC-diff is exhausted → switched to BDOS-level `callseq`. callseq (post
$F338 fix): ours matches stock through n=1–4 (STROUT/FOPEN/STROUT/SDATE), then at the date prompt
ours prints a malformed date (stock `"84-01-01"` 8ch → BUFIN; ours garbage `" 3-00-00…"` 10+ch,
loops; call-count nondeterministic 18/60). So blocker #2 = ours' GDATE/clock-read or date-string
formatting in the relocated kernel (+ maybe headless-BUFIN re-prompt). · judgment: STOPPED probing
here rather than grind the timing-nondeterminism — flagged for a deliberate fresh characterisation
([[tier2-deep-think-before-resuming]]). · confidence: high that ours advanced to the date prompt;
medium on the exact date-bug root. · undo: n/a (harness + docs only). Detail: tier2-STATE.md.

**[BLOCKER #1 ($F338=0) BUILT + VALIDATED / 2026-06-27 — first Tier-2 asm that advances DOS boot.]**
User signed off the minimal DOS-only $F338=0 fix. Built `dos_handoff` (free-tail subroutine,
runtime.asm): defaults $F338=0 for DOS, stack-save/restores the host's dual-purpose stub for a
returning data disk; boot_sig_ok calls it in place of the inline `scf; call BOOT_ENTRY` (net −1
byte in the $41FD-packed region; net-zero ROM). **Two build bugs caught + fixed before commit:**
(1) the §3-draft INLINE placement overflowed the $41FD canonical anchor under pasmo (`64KB limit`)
→ corrupt ROM → getdpb UT read zeros; moved to the free tail. (2) scratch $E762 collided with
R30_HL ($0030 handler) → used the stack instead. **Validated:** re-trace moved ours' fork step
7→61 (≡ the poke), taking stock's STROUT path; unit 18/18; FILES byte-identical to CF-3300 on
C-BIOS BASIC-disk (the save/restore protects BASIC — phase-1 option-A's regression avoided);
BLOAD ,R+plain ok; net-zero 16384. · judgment calls: (a) stack vs scratch byte (chose stack —
no free scratch + avoids collision); (b) free-tail subroutine vs inline (forced by the anchor);
(c) did NOT run a C-BIOS-DOS-advance trace — the fix is host-independent by construction (constant
write + host-value save/restore) and the DOS interface is BIOS-agnostic, so CF-3300-BIOS DOS-advance
+ C-BIOS BASIC-coexistence covers it. · confidence: high · undo: revert the init.asm/runtime.asm
hunk. Detail: tier2-f338-default-spec.md §7, tier2-STATE.md.

**[BDOS-LOOP ROOT-CAUSED → CONVERGES ON PHASE-1 / 2026-06-27 — HARD-STOP for the un-park decision.]**
Built the 3-mode differential harness (`disk_probe_diff.py`: callseq/capture/trace + `--poke`
falsification injection; trace reproduced the known n=3 result, then pinpointed the fork). The n=3
STROUT-vs-SELDSK divergence is COMMAND.COM's `ld a,($F338); and a; jr nz` @ `$C26B`: stock `$F338`=00
→ STROUT/prompt; ours `$F338`≠0 → SELDSK/loop. **Falsification** (poke `$F338`=0 into ours) advances
ours **54 instrs** onto stock's path to `$D885 call $F368` → `$F338`=0 is necessary & effective
(overturns the old "forcing $F338=0 didn't help"). Next divergence at `$F368` is ours' INTENTIONAL
relocated hook (`jp $E795` vs `$DF57`, flags identical) — behavioral check, not a bug yet. **This
converges decision-b (BDOS-loop) back onto phase-1: building `$F338`=0 (DOS-only + BIOS-agnostic, the
tier2-phase1-spec §7b option-B reorg) is the next step to `A>`.** Recommend un-parking phase-1 for a
minimal DOS-only `$F338`=0 build, then resume the trace from `$D885`. · why: the trace is decisive and
cheap; the parking was based on §8.65 which this supersedes. · confidence: high on $F338; medium on
"how much beyond $F338" (≥1 more blocker at $F368). · undo: n/a (probes+docs only, no asm). Detail:
tier2-STATE.md live-thesis + open-Q1.

**[PHASE-1 IMPLEMENTED + VALIDATED for DOS, but REVERTED (Tier-1 BASIC regression) / 2026-06-26 —
needs option-B reorg, next milestone.]** Built `wa_clear` (zero $F1C9-$F37F, $C9-fill $F24F-$F2B7,
`in a,($A8);ret`@$F365), option A (first in init). Fixed two hazards during build: (1) zeroing RAMAD
$F341-4 defeated set_ramad's $FF gate → skipped the whole build_wa_table/drvtbl/resident fall-through
chain (excluded RAMAD); (2) off-by-one in the split memset. **DOS validation PASSED**: $F338=00,
$F368=C3 95 E7 (A-3 hooks built), RAMAD=83, diff 462→319, sp-rompage STUCK, unit 18/18, 16384 B.
**BUT option A regresses BASIC FILES** (wa_clear runs for ALL boots, wipes a $F1C9-$F37F cell disk-
BASIC needs). REVERTED → Tier-1 green, tree clean. **Option B (DOS-only) required but non-trivial:**
ours' DOS work-area builds (RES_PRINT $F1C9 / DRVTBL $F348 / WA_JMPTAB $F368 / SYSTEM $F37D / the
set_ramad fall-through) run in init for ALL boots; a wa_clear in the DOS path (boot_sig_ok) runs AFTER
them and would wipe them with no rebuild. So B needs reorganising that chain into the DOS-boot path
after wa_clear, while keeping what BASIC depends on (DRVTBL? RES_PRINT?) on the BASIC path — a design
task needing its own spec (map BASIC's work-area dependencies first). Detail: tier2-phase1-spec.md §7.
· undo: n/a (asm reverted; only docs committed).

**[DEFINING FINDING / 2026-06-26, commit TBD — the real blocker is the UNBUILT DOS WORK AREA, not
FOPEN or any single intercept. STRATEGIC CHECKPOINT.]** Followed COMMAND.COM's post-FOPEN branch
to ground: it does `ld a,($F338)` at $C26B; stock ($F338)=00, ours=$FF. Write-watch: stock writes
$F338=00 from PC=$57BE at t=3.80 (BOOT time, not during FOPEN); ours never writes it ($57BE is
`00` padding in ours). So the FOPEN $21 was a RED HERRING — the branch input is a boot-time-init
cell. Forcing $F338=00 alone did NOT fix it (and sent COMMAND.COM down a path that WROTE the disk
— mutated the /tmp copy, restored from canonical, repo clean) because one cell set amid an
uninitialised area is inconsistent. **Decisive probe (disk_probe_dosboot_wadiff.py): the whole DOS
work area $F100-$F3FF at COMMAND.COM entry — 462 of 768 bytes differ, ours almost entirely $FF.**
Stock holds there: executable RAM-resident routines ($F100-$F17C, $F327-$F33F), the DPB+drive
table ($F1A8+), the device-name table ($F21C "PRN LST NUL AUX CON"), the "COMMAND COM" FCB
structure ($F2B8), and the DOS pointer block ($F34D-$F37F). **Ours' disk ROM does NOT construct
the DOS work area during boot; stock's does.** That work area IS the disk-ROM-resident portion of
the shared MSX-DOS-1 kernel ([[msx-diskrom-shared-kernel]]). ∴ reaching A> is neither "fix FOPEN"
(fork A's first step) nor "intercept $0005" (fork B) — BOTH were scoped against a far smaller
problem. The true scope is "reproduce the disk-ROM's DOS-work-area construction" — a large,
multi-milestone sub-system (resident code + structures + pointers). Detail: tier2-workarea-map.md.
**This is a strategic checkpoint: the user should reassess the "reach A>" ambition with this in
hand** (treat the mapping as a documentation deliverable + pause, vs commit to the large build, vs
characterise the construction step-by-step). New probes: fopenoverride, wadiff (+ /tmp helpers).
No production asm written. · undo: n/a.
  **>> USER CHOSE "characterise the construction first". DONE 2026-06-26 (commit TBD) →
  tier2-workarea-map.md §5a.** Write-watch of all $F100-$F3FF stores across stock's boot
  (disk_probe_dosboot_wabuild.py, last-writer-per-byte): **96 distinct disk-ROM routines build the
  area in 4 phases** — (1) t≈3.8 clear/default pass ($57BE/$57D6: zeros + $C9-fill hook stubs),
  (2) t≈6.9 DPB+drive table + RESIDENT CODE ($F1C9-$F236, $F327) + segment-switch hook vectors
  ($F368-$F37F) + drive-DPB pointers ($F34D-$F352), (3) t≈10 resident routines $F100-$F17C + the
  COMMAND COM FCB ($F2B8), (4) t≈11.3 final cells. Sized plan: phase-1 clear is easy; phase-2
  structural data is moderate & overlaps existing code (we have real GETDPB); **the hard core is
  ~250 bytes of executable RAM-resident routines (inter-slot/paging helpers) needing black-box
  contract reproduction.** Build order 1→2→3, wadiff as region acceptance test. Now AWAITING the
  build-vs-pause decision with a concrete sized plan in hand. New probe: wabuild. No asm.

**[$D858 BLOCKER ROOT-CAUSED + STRATEGIC SCOPE REFRAME / 2026-06-26 — HARD-STOP for a sync.
The $D858 loop is COMMAND.COM's prompt loop spinning because the kernel's FOPEN of AUTOEXEC.BAT
returns the WRONG code; the true scope is "reproduce the shared disk-ROM BDOS kernel", not one
veneer.]** Five anchored differential probes (all new, committed), each ours-vs-stock from the
boot anchor:
- **entry0100seq** — ours runs MSXDOS.SYS at $0100 (b0102=02) THEN COMMAND.COM (b0102=05), SAME
  structure as stock. The standing "ours skips MSXDOS.SYS init" hypothesis is **REFUTED**.
  COMMAND.COM entry (HIT2) is byte-identical to stock (BC=HL=1A00 IX=F195 IY=DC5B SP=DC00). Only
  MSXDOS.SYS-entry (HIT1) differs: IY (ours 0314 vs stock C0AB) + AF flags (0144 vs 0142).
- **conoutstream ($5454)** — ours prints the **full banner byte-identically** (53 chars
  "..MSX-DOS version 1.03..Copyright 1984 by Microsoft..", same ret=$0320/HL=DD0E/DE seq). The
  "blank screen / garbage CONOUT" reading was INCOMPLETE: banner is perfect; garbage ($00/$80,
  ret=$D88A) only starts AFTER COMMAND.COM launches.
- **bdosseq** — first BDOS divergence is call **n=3**: n=1 STROUT + n=2 FOPEN are byte-identical
  on both, then stock→STROUT(ret CBA6) vs ours→SELDSK(ret C30A). Ours then loops
  CONOUT/CURDRV/CONOUT/CONOUT/BUFIN forever (the $D858 loop = COMMAND.COM's prompt loop; BUFIN
  never blocks so it re-prompts endlessly).
- **fopenresult** — the FOPEN (fn $0F) is on **AUTOEXEC.BAT** (FCB at $D62F, identical entry).
  Result: **stock A=$FF (not-found), ours A=$21**. COMMAND.COM tests A==$FF ("no AUTOEXEC → go to
  prompt"); ours' $21 sends it down the wrong branch → spin. (Note: our disk-ROM bdos_open DOES
  return $FF correctly — but COMMAND.COM uses the KERNEL's BDOS via $0005, not our bdos_entry.)
- **fopenromcalls** — brackets that one FOPEN, logs every page-1 ($4000-$7FFF) disk-ROM entry the
  kernel invokes. **Divergence at the FIRST entry, $4462** (both enter with identical
  A=21/BC=0/DE=DA40/HL=C284): stock runs a **144-entry directory search** ($4462→$4411→$5604→
  $425D→$44DE→$4558→DSKCHG $4013→$607B→$434B dir-scan→DSKIO $4010→…) ending A=$FF; **ours bails
  after 1 entry** (A=$21 passes through). Our ROM at $4462 = `ld ($E299),a; ret` (unrelated FDC
  code), NOT a BDOS veneer.

**STRATEGIC FINDING (the reframe).** The MSX-DOS-1 **file-ops BDOS** (FOPEN, directory search,
file read) is implemented **inside the disk ROM** — the shared kernel (~2/3 of every MSX disk
ROM, [[msx-diskrom-shared-kernel]]). MSXDOS.SYS is the thin loader on top; for file ops its
relocated stub pages the disk ROM into page 1 and CALLs canonical addresses ($4462, $4411, $5604,
$425D, $44DE, $607B, $434B, $760E, $764D, …). Our 14 veneers cover only the **COMMAND.COM-LOAD**
subset; genuine DOS operation calls the **rest of the shared BDOS kernel**, which in our ROM is
unrelated FDC/DSKIO code, ds-padding, or bare-`ret` stubs (e.g. k_607B). So reaching `A>` is NOT
a one-veneer fix — it requires reproducing the shared disk-ROM BDOS contracts (dir/file/FAT) at
their canonical page-1 addresses. The 144-entry FOPEN chain is the first concrete map of it.

**HARD-STOP — FORK for the user (a scope surprise that changes the signed-off "fork-a" plan,
sized from the load path only):**
  (A) Continue faithful per-canonical-address reproduction — reproduce the shared BDOS kernel
      contracts ($4462 + its chain) at their fixed addresses (large but mechanical/harness-driven;
      most faithful to the layout-fixed Interface A).
  (B) Intercept higher — route whole BDOS functions (FOPEN…) to our existing bdos_entry/bdos_open
      (which already returns $FF correctly), instead of reproducing each fine-grained address.
      Smaller, but changes the interface model and must not break the kernel's internal BDOS use.
  (C) Characterise more first (e.g. map the full set of canonical BDOS addresses the kernel calls
      across FOPEN/dir/read) to size A precisely before committing.
· No code written (characterise-before-code held). Tier-1 untouched (probes only, no asm/build
change). New probes: entry0100seq, conoutstream, bdosseq, fopenresult, fopenromcalls. · undo: n/a.
  **>> USER CHOSE (C) map-scope-first. DONE 2026-06-26 → disk/docs/tier2-bdos-scope.md.** FOPEN
  (not-found) path = 23 distinct canonical disk-ROM addresses, only 2 covered (DSKIO $4010 /
  DSKCHG $4013), 21 to build (9 collide w/ our FDC-DSKIO code, 7 bare-ret stubs, 5 ds-pad); full
  DOS adds more. $0005=JP $D606 (kernel BDOS dispatch, identical ours/stock). **RECOMMENDATION:
  fork B** (re-point $0005→our bdos_entry at the documented BDOS ABI boundary): cleaner clean-room,
  bounded/finite vs A's open-ended per-address reproduction, reuses our existing disk BDOS (our
  bdos_open already returns the $FF this blocker needs). Next: A-vs-B decision, then (if B)
  tier2-bdos-spec.md before any asm. Risks for B catalogued in the doc §4.
  **>> USER CHOSE FORK B (2026-06-26). Viability gate PASSED** (disk_probe_dosboot_bdoscallers.py:
  every $0005 caller is COMMAND.COM, ZERO in the kernel $D606-$DDFF → redirecting $0005 is safe).
  **Spec drafted: disk/docs/tier2-bdos-spec.md (DRAFT, awaiting sign-off before asm).** Mechanism:
  k_47B2 overwrites $0005→our page-0 RAM trampoline → bdos_entry; extend bdos_entry with the
  startup console fns ($02/$06/$09/$0A/$0E/$19/$2A) on top of the disk fns we have. 5 open sign-off
  items in spec §5 (milestone scope, SDATE stub, BUFIN fidelity, trampoline location, clean-room
  confirm). No asm yet (spec-before-implementation).
  **>> PRE-IMPLEMENTATION VALIDATION OVERTURNED THE FORK-B PREMISE (2026-06-26, commit TBD) —
  HARD-STOP, fork re-opened.** Before writing any asm I cheaply tested the core fork-B assumption
  ("intercept FOPEN → our bdos_open returns $FF → COMMAND.COM unblocks") with register-override
  experiments (disk_probe_dosboot_fopenoverride.py): forced the kernel FOPEN return at $C24E to
  stock's EXACT state — A=$FF (expt2), then AF=$FF45 + HL=$00FF (all other regs already identical
  to stock: BC=0 DE=D64F IX=F195 IY=DC5B SP=D600). **Result: COMMAND.COM STILL mis-branches**
  (next call SELDSK ret=$C30A, not stock's STROUT ret=$CBA6) and still spins. ∴ **COMMAND.COM's
  post-FOPEN branch is NOT register-conveyed — it reads WORK-AREA MEMORY that stock's full 144-
  entry FOPEN populates and our bailed-at-$4462 FOPEN never writes.** A lightweight register-
  contract intercept is therefore INSUFFICIENT; the premise "our bdos_open already returns the $FF
  this blocker needs" was wrong (the value isn't the branch input). Implications: (i) the kernel's
  file machinery must ACTUALLY RUN to build the work area (favours fork A: reproduce the $4462
  chain), or (ii) a fork-B BDOS must additionally populate the exact work-area cells COMMAND.COM
  reads (converges toward A's effort). Recommend ONE more cheap characterisation — identify the
  specific work-area address COMMAND.COM reads between $C24E and its branch (read-watch /
  state-diff) — to decide A-vs-B on evidence before committing. No production asm written
  (validate-before-build held). New probe: fopenoverride. · undo: n/a.

**[$47B2 RETURN CONTRACT DONE / 2026-06-26, commit 9573a4c — COMMAND.COM now runs its real
startup (no longer spins at $050D). New blocker: a kernel loop $D858-$D87F after startup.]**
Implemented the M5.4-deferred fix. Clean same-program comparison (COMMAND.COM `$0100` entry,
ours vs stock) isolated it to 4 registers: stock `BC=HL=$1A00 IX=$F195 IY=$DC5B`, ours
`HL=0 BC=$0014 IX=$F1AA IY=$0314` → COMMAND.COM `jp $0500` then spun at `$050D` (a 5120-byte
LDIR with garbage params). The `$D824→$0100` transfer doesn't touch these regs, so they pass
through from `$47B2`'s return. `k_47B2` now sets, on EOF/success: `HL=BC=FAT_FILESIZE`,
`IX=DRVA_DPB ($F195)`, `IY = entry DE` (saved on the stack; the kernel work ptr `$DC5B`).
**Validated:** `$0100` entry now byte-identical to stock; COMMAND.COM reads `$0007` (TPA top
`$D6`), computes its high-mem target `$C200`, and LDIRs its transient up — genuine MSX-DOS
COMMAND.COM startup. A-3 intact (sp-rompage STUCK); Tier-1 green (unit 18/18,
DSKIO/BLOAD/FILES == CF-3300); net-zero 16384 B. · **NEW BLOCKER (next milestone):** after
startup the boot sits in a kernel loop `$D858-$D87F` ($D87F = the 130-byte LDIR `$D34E→$DA40`
+ a CONOUT call at `$D887`); screen still blank, CONOUT still fed `$00/$80`. Likely a BDOS
function COMMAND.COM calls during startup that our kernel/BDOS path mishandles. Drive it with
the same ours-vs-stock differential, anchored on a shared event. · undo: revert 9573a4c.

**[CHARACTERISATION (corrected) / 2026-06-26 — post-A-5. COMMAND.COM LOADS CORRECTLY; the
blocker is the DOS-env / boot-sequence handoff, NOT a wrong-sector load. RETRACTS the earlier
"+2 clusters" claim below.]**
- **RETRACTION:** I earlier wrote "ours reads COMMAND.COM 2 clusters too late (138 vs 134)".
  That was WRONG — an artifact of snapshotting the MIDDLE of the read. Ground truth from the
  disk: root dir [6] COMMAND.COM = cluster 62 → sectors **134-146** (chain 62-68, contiguous),
  and sector 134's bytes are **`C3 00 05`**. A full from-boot DSKIO capture shows ours reads
  exactly 134,135,…,146 — **CORRECT**. (Lesson, again: don't conclude from a mid-stream
  snapshot; capture from the anchor. [[harness-first-investigation-mo]].)
- **What actually differs:** ours' first `$0100` execution is **COMMAND.COM** (`C3 00 05` =
  sector 134) → `jp $0500` → spins at `$050D`. Stock's first `$0100` is **MSXDOS.SYS** (root
  dir [7] = cluster 69 → sector 148 = `C3 00 02`) → `jp $0200`, which runs the DOS init and
  prints the `MSX-DOS version 1.03 / Copyright 1984 by Microsoft` banner (CONOUT from `$0320`).
  So my "first-divergence at `$0100`" compared DIFFERENT PROGRAMS (ours=COMMAND.COM,
  stock=MSXDOS.SYS) — not a real divergence.
- **Open hypotheses (to verify next, fresh):** (a) ours enters COMMAND.COM at `$0100` with the
  wrong environment/entry-registers/SP (ours SP=$DC00, no proper DOS env) so it spins; and/or
  (b) ours' boot SKIPS or mishandles the MSXDOS.SYS-at-`$0100` init step that stock runs (banner
  + DOS setup) before launching COMMAND.COM; and/or (c) a possible off-by-1 in ours' MSXDOS.SYS
  read (ours read sectors 149-152, stock 148-151) — UNCONFIRMED, could be another mid-stream
  snapshot artifact, verify from the anchor before trusting it.
- **NEXT (fresh session, deliberate):** anchor a clean comparison on the SAME program. Either
  (i) compare ours-vs-stock at COMMAND.COM's `$0100` with matched entry state, or (ii) check
  whether ours runs MSXDOS.SYS at `$0100` at all. Understand how our Tier-2 veneer boot
  (k_47B2 et al.) sequences the MSXDOS.SYS-init vs COMMAND.COM-launch relative to stock.
  Connects to M5.4/§8.54 ($47B2 return-register state was explicitly deferred: "does NOT yet
  reproduce $47B2's return AF=0142/HL=1A00/IY=DC5B" — that deferred entry-state may be the env
  bug). · undo: n/a (analysis only).

**[RETRACTED — see correction above. The "+2 clusters" framing was wrong.]** After A-5 the boot
reaches the COMMAND.COM-load kernel phase but never shows `A>`. Harness findings:
- **Stock** prints the real banner via CONOUT `$5454`: `\r\n MSX-DOS version 1.03 \r\n
  Copyright 1984 by Microsoft \r\n`, called from `$0320` with `HL=$DD0E` (work area), `DE`=
  the banner chars.
- **Ours** feeds `$5454` a repeating `$00 $00 $80 …` garbage stream, called from **`$D88A`**
  (relocated kernel), with junk `DE`/`HL`. The kernel routine `$D87F` LDIRs 130 bytes from
  `$D34E` (garbage) → `$DA40`, maps the disk ROM into page 1 via `$F368`/WA_SEG (now WORKING),
  `ret`s to **`$50E0` — a bogus address inside our ROM's `$00` padding** (real code at `$50A9`
  ends `$50B7`; `$50B8-$520x` is `ds` fill), then NOP-slides. So the kernel is operating on
  corrupt state: garbage buffer, garbage return address, garbage output.
- **These are DOWNSTREAM symptoms** (cf. [[tier2-storms-are-downstream]]); chasing the `$50E0`
  NOP-slide or "missing veneer" would be fixing a symptom. The PRIMARY derail is upstream in
  the shared relocated kernel ($D606-$DD0E, same addresses on ours+stock since both use
  GETWRK=$DD0E) — likely a wrong value our disk ROM returns from one of the `$40xx`/`$50xx`
  kernel-callback contracts during COMMAND.COM load, sending the kernel down a wrong branch
  before it ever reaches the `$0320` banner path.
- **NEXT MILESTONE:** ours-vs-stock FIRST-DIVERGENCE hunt in the shared kernel — compare the
  kernel PC/branch sequences (not time-aligned; ours is slower) from COMMAND.COM entry to the
  first point ours branches away from stock, then identify the disk-ROM callback whose
  contract we get wrong there. Connects to the M5.5 "$544E spin from $D88A" thread (now with a
  clean post-A-5 signal). · undo: n/a (analysis only).

**[A-5 DONE / 2026-06-26 — WA_SEG corruption FIXED, boot now reaches COMMAND.COM]
The post-storm "kernel loop" was a CORRUPTED WA_SEG trampoline; root cause = our OWN
interrupt handler's A-2b private stack overflowing into it. Fix: run the $0038 handler on
the caller's stack (retire A-2b). Implemented + validated; see tier2-a5-spec.md.** After A-3
the real resting state was an infinite loop `$DC03 → call $F368 → jp WA_SEG($E795) → … →
$0000: jp $DC03`: the kernel's `$F368` segment-switch landed on a trampoline whose tail
(`$E7A8+`) was garbage (`ld (#00C0),a … call m,$0000` instead of `ld (SLTTBL3),a; ld
($FFFF),a; … ret`), so the page-1 swap never happened and COMMAND.COM never got control
(stock was already at `$0B9F` by the same time).
- **The corruptor is OUR int handler, not a disk-boot stack (corrected — see HONESTY note).**
  `INT_H_HIRAM` switched to the A-2b 48-byte private stack (`INT_STK_TOP`) before
  `call $0038`; the main-ROM KEYINT (`$0C82` loop + `dec ($F3F6)` JIFFY + the `pop ix/iy/af/
  bc/de/hl` epilogue at `$0D02`) needs ~60 B and overflowed DOWNWARD into `WA_SEG`, laid out
  just below the stack (`INT_STK_TOP = PG_SV_A8+1+48`). The corruption always landed at
  `WA_SEG+19`, regardless of where the band was placed.
- **HONESTY note (process):** I first misread the `$0C85 push` (KEYINT's pushes) as "the MSX
  disk-boot stack roaming `$E7xx`" and got sign-off for A-4 (relocate the band into `$DDxx`).
  A-4 was IMPLEMENTED, then the corruption *reproduced identically at the new address* — the
  stack and WA_SEG had relocated together — which exposed the real cause. A-4 was reverted
  (uncommitted) and `tier2-a4-spec.md` withdrawn. Lesson: I should have confirmed *what*
  `$0C85` is (trace it = KEYINT) before naming the corruptor; pattern-matching `push`+low-PC
  to "boot stack" skipped the black-box check. (cf. [[dont-prematurely-wall]], harness-MO.)
- **Fix (A-5, signed off):** delete the three stack-switch instructions from
  `int_h_hiram_tmpl`; run KEYINT on the caller's stack like stock/standard MSX. A-2b only
  guarded against a corrupt caller SP (the storm) which A-3 already fixed; every caller stack
  here is healthy + roomy. Removes the unbounded-depth guesswork a fixed private stack imposes.
- **Validated:** WA_SEG byte-identical at t=6 & t=14; boot breaks out of the loop and runs
  COMMAND.COM (`$0BA4`/`$0D0A`/`$120C`) + the working `$F36B→$E79B` switch + CONOUT; A-3
  intact (`sp-rompage` STUCK); Tier-1 green (unit 18/18, DSKIO/BLOAD/FILES == CF-3300);
  net-zero 16384 B. · **NEW downstream blocker (next milestone):** screen still blank at
  t=90, PC churning in the `$54xx` CONOUT band — likely a CONOUT/screen-output issue, looser
  than the loop. · undo: re-insert the 3 stack-switch instructions.

**[A-3 DONE / 2026-06-26, commit 71b1096] Relocated int_h to always-mapped high RAM
($DDAE) — THE COMMAND.COM STORM IS FIXED.** Implemented tier2-a3-spec.md approach B:
`int_h_hiram_tmpl` (the A-2/A-2b handler made relocatable — straight-line, only a
PC-relative `jr` + the fixed `call $0038`, `pg0_mainrom_in/out` inlined with `ret z`→
`jr z`, like `res_print_tmpl`) is LDIR'd into `$DDAE` by `lay_page0_env`, and the
`p0_env_tab` `$0038` entry now targets `INT_H_HIRAM` instead of the page-1 `int_h`.
**Validated with the harness + regression:** handler installed (`$DDAE = ED 73 E2 E7…`),
`$0038` chain → `jp $DDAE`, `int-vec hits=0`, SP stable `$DBFA-DC00`; `disk_derail_locate
--preset sp-rompage` = STUCK (no SP corruption — storm gone); Tier-1 green (unit 18/18,
DSKIO/FILES == CF-3300, BLOAD ok); net-zero (16384 B). · **New downstream blocker
revealed** (the storm was masking it): a bounded kernel loop, triage `loop-top $E7B1,
period 23`, healthy stack, in the `$D7xx`/wa_seg band — likely the M5.7/§8.60 "$DA23
wrong-path loop" / work-area thread, now visible with a CLEAN signal (no storm). This is
the next milestone; drive it with the harness (`bisect_locate` on a loop-specific
predicate, ours-vs-stock at the first divergence in the `$D7xx` kernel). · the old
page-1 `int_h`/`int_h_body` are dead-but-kept (net-zero); remove in a follow-up. · undo:
revert 71b1096.

**[FIX DIRECTION / 2026-06-26] Stock comparison (via the new harness) names the fix:
move our interrupt handler to ALWAYS-MAPPED high RAM, like stock's `$DDAE`.** Used the
new `omsx_session.py` `irq_chain` primitive on both machines (one call each) to dump the
`$0038` jp-chain + page-1 mapping at the COMMAND.COM phase:
- **Stock:** `$0038 → jp $DDAE`, and `$DDAE` is in **high RAM (page 3, always mapped)**
  (`push ix` = the real handler). The int entry is NOT in the swappable page-1 ROM.
- **Ours:** `$0038 → jp $4251 → jp $792B` — BOTH in **page-1 disk ROM** (`$792B` =
  int_h_body, the A-2b `ld ($e7e2),sp`). When `wa_seg_ram` swaps page 1 to RAM for
  COMMAND.COM, the whole vector path (`$4251` trampoline AND `$792B` body) is unmapped →
  the first IRQ storms on `$FF`. (This is also exactly why A-2b never ran — it lives in
  the wrong memory.)
- **The fix (Interface-B rework, fork (a)):** install `$0038 → jp <our high-RAM handler>`
  (our own address in the `$D7xx-$DFxx` kernel band, clean-room — mirror stock's structure,
  not its bytes), and relocate the int handler body there so it survives the page-1 swap.
  It can page the disk ROM back in via CALSLT if it needs disk-ROM routines, but the ENTRY
  must be always-mapped. This connects to §8.69 Interface-B / A-2..A-5 and supersedes the
  A-2b placement.
- **HARNESS NOTE:** the negative case validated too — `disk_derail_locate.py --preset
  sp-rompage --stock` = STUCK ("no failure in window"), i.e. stock never corrupts SP.
  · confidence: high (direct ours-vs-stock measurement) · this is a DESIGN sign-off point
  (the deferred Interface-B rework), not yet implemented · undo: n/a (analysis + new probe).

**[ROOT CAUSE FOUND / 2026-06-25] The primary derail is a SLOT-PAGING bug in the
COMMAND.COM handoff — NOT a control-flow slide. Located + confirmed end-to-end with
the new reverse/probe toolbox.** Method: `reverse` binary-search in emulated time for
the corruption instant (SP enters the ROM page is a clean predicate), then a forward
per-instruction trace from a `reverse goto` point. Findings, all from one boot:
- The "storm" is `rst 38h` recursion: RAM `$0038 = C3 51 42 = jp $4251`, but at the
  failure `$4251` reads **$FF** (`rst 38h`) — the **disk ROM is paged OUT of page 1**.
  So `$0038 → jp $4251 → $FF=rst38 → $0038 → …` loops forever, each `rst` pushing
  `$4252` (stack is all `4252`), marching SP down. Fully explains the SP march.
- **The unmap is deliberate, in our own RAM-resident handoff code.** Trace at the
  boundary (t≈8.186s): kernel `$D827 call $F36B → jp $E79B` (RAM trampoline). $E79B
  does `ld a,#00; di; ld a,(FCC8); and $F3; or b; ld (FCC8),a; ld ($FFFF),a`. SLTTBL[3]
  (`$FCC8`) was `$04` → page-1 subslot **1 = the disk ROM**; `and $F3` clears page-1's
  bits, `or b` (B=0) forces page-1 subslot to **0**; the `ld ($FFFF),a` write unmaps the
  disk ROM → page 1 = slot3-sub0 = **empty ($FF)**. Then `$D82A ei; jp $0100`.
- **COMMAND.COM then actually RUNS** (trace: $0100→$0500→ self-relocating `ldir`,
  bc=$1400). It dies at the **first interrupt**: confirmed via `z80.acceptIRQ` —
  ACCEPT#1 interrupts COMMAND.COM at $050D with `m4251=FF`, `$0038=jp $4251` → storm.
- **So:** the handoff unmaps the disk ROM from page 1 while the live interrupt vector
  `$0038 → $4251` still points there. Works only while the disk ROM is mapped; the
  moment COMMAND.COM is given control (page 1 = empty) the first IRQ storms. This is
  why "COMMAND.COM is not sustained" (M5.5).
- **This is the proximate trigger; relationship to the M5.7 "stale work-area" thread
  is unclear** (may be separate/earlier, or the wrong B/subslot value originates
  upstream). The slot bug is the confirmed storm cause regardless.
- **The fix is a DESIGN decision (clean-room, our own code) — HARD-STOP for sign-off,
  not yet implemented.** Candidate directions: (a) re-point the interrupt vector
  (RAM `$0038` / H.KEYI) to a handler that survives the disk-ROM unmap before the
  handoff; (b) keep page 1 mapped to a valid subslot so `$4251` stays a real `jp`;
  (c) follow whatever the real MSX-DOS / stock CF-3300 handoff does at this exact
  point (compare with stock = the obvious next experiment, same reverse method).
  · confidence: very high on the diagnosis (located + confirmed); the fix is open. ·
  undo: n/a (analysis only).

**[tooling / 2026-06-25] Built the dead-zone NOP tripwire — then a fast experiment
FALSIFIED its premise; pivoted to a full openMSX-probing-toolbox sweep instead.**
Added `probes/disk/disk_probe_dosboot_tripwire.py` (kept, per user) on the idea that
the derail is a NOP-slide into `$00` absorption pads, catchable by one watchpoint
(range + opcode==0). Mechanism validated and excellent. **But the decisive negative:
NO `$00` opcode executes anywhere in `$0000-$FFFF` across the entire 30-emulated-second
boot+derail** (ROM page, all RAM, page-0 storm ring — all zero; cross-checked by
trapping a known `$31` which fired instantly). So the triage oracle's **SLIDE** verdict
(`PC==prev+1`) means *consecutive single-byte instructions*, NOT a NOP-pad slide — the
absorption pads are never entered. The "dead zone = `$00` pad" frame (strategy ①) is
dead for this bug; the derail is control running forward through **real, valid-opcode
code at the wrong place**. · **Why this is progress, not a detour:** it cost one cheap
experiment (not a reframe spiral) and forced a systematic sweep of openMSX's debug
surface, which surfaced three capabilities we were not using — now validated and
documented in `disk/docs/openmsx-probing-toolbox.md`: (1) **`z80.acceptIRQ` hardware
probe** = direct interrupt-acceptance catcher, no per-instruction cost; (2) **`reverse`
rewind/replay** = `reverse goto <T>` before a caught failure then single-step forward
to recover the **faulty transfer** (this is the engine the derail hunt was missing);
(3) **`{CPU regs}` byte 27** = real IFF1/IFF2 + "can-accept-IRQ" bit (corrects the old
"reg IFF1 doesn't exist" dead-end). Also added `tools/sym_to_openmsx.py` (pasmo `.sym`
→ openMSX `generic` so traces show symbol names; 352 syms load). · **Recommended next
frame (strategy ③, the memory's "method that works"):** the disk-ROM PCs aren't
comparable to stock (relocated/own-design), but main BIOS (`$0000-$3FFF`) and the
DOS RAM image (MSXDOS.SYS/COMMAND.COM, fixed addresses) ARE byte-identical on both —
so find the first executed-PC divergence ours-vs-stock *restricted to those comparable
regions*, built on the validated `acceptIRQ`+`reverse` engine. This reconnects with the
M5.7 work-area-init diagnosis ($D7CE / $DC80-$DCB2 / $F1A8+ stale). · confidence: high
on the negative result + the toolbox; the next frame is a proposal, not yet greenlit. ·
undo: n/a (new probe + doc + tool, no ROM change).

**[A-2b / §8.76] Implemented the storm-proof int_h (private interrupt stack) — CORRECT
and green, but it does NOT change the boot outcome; the storm bypasses it. Kept as
defensive hardening (user call), then pivoting to the primary derail.** int_h_body now
saves the caller SP, runs on a private 48-byte page-3 stack ($E7B2-$E7E1, save at
$E7E2), and restores — proven by a first-interrupt pctrace (SP $8FEE→$E7E2, KEYINT
$0C3C runs on $E7xx, clean return). Net-zero ($4251=jp $792B unchanged), unit 18/18,
DSKIO/basic/tape regression green. · **The negative result:** the steady-state is
unchanged (triage still SLIDE, SP=$4250) and the storm ring is PURE $4251⇄$0038 with
int_h_body ($792B) NEVER appearing — the interrupt is accepted AT the $4251 trampoline
before the body runs, so A-2b's hardening is never reached during the storm. The SP
march is the hardware accept-push on an already-corrupt SP, not int_h_body. · **So the
"storm masks the bug" hypothesis was WRONG:** the storm is a pure downstream consequence
of the primary derail (IFF=1 while PC is already runaway → interrupts accepted at the
trampoline). No handler-level change can prevent that; fix the primary derail and there
is no runaway to storm. · **Disposition (user: "keep, commit, pivot"):** A-2b kept as a
standalone correctness fix (a handler that marches a corrupt caller stack is a real
latent bug; net-zero, green) but explicitly NOT the blocker. Next = hunt the primary
derail (first divergence from stock), reconnecting with the pre-compaction kernel/
COMMAND.COM-sustain track. · confidence: HIGH (storm ring + first-int trace are
unambiguous). · undo: revert init.asm INT_STK_TOP/INT_SP_SAVE equates + the 3 added
lines in runtime.asm int_h_body (net-zero, trivial).

**[M5.x / §8.72-8.74] RE-BASELINED the hang: the post-compaction "$4251/$0052
storm / SP=$0000 onset" was a RED HERRING; the real hang is an int_h→KEYINT
VDP-ACK FAILURE (interrupt storm).** After /compact I resumed the "find the SP=0
runaway onset" task from the summary and chased it to a tight page-0 loop at
$02E0-$0339 running with SP=$0000. **Judgment call:** I discarded that lead after
proving (PSP+prologue dump + a 30000-instr aligned pctrace, ours vs stock, both
from $02E0) it is **byte-and-register IDENTICAL on the stock CF-3300** — it is the
normal MSX-DOS RAM/slot-sizing scan, which legitimately abuses SP as scratch
(`ld sp,hl`) with interrupts off. Not a bug. · Then re-found the TRUE steady state
with `disk_probe_dosboot_hang.py --settle 24`: **ours** = a runaway sweeping
linearly through high RAM/ROM (`disk_probe_dosboot_derail.py`), **stock** = the A>
idle keyboard loop at $0D87 (SP=$DBE0, regs static). The derail ring pinned the
core: `$0038 (=C3 51 42 = jp $4251) ⇄ $4251 (int_h = C3 2B 79 = jp $792B =
int_h_body)`, **SP descending -2 per cycle**, int_h_body ($792B) NEVER executing →
the VDP interrupt is never acked → storm → SP marches from $8FEE down through our
ROM → derail/NOP-slide. · **Why it matters for you:** this moves the active front
OFF the kernel work-area / $D7xx grind (M5.6-5.9) and BACK onto Interface-B: A-2
(int_h chaining to KEYINT) is *present but not acking*. The fix locus is
`int_h_body` in disk/runtime.asm (the `call $0038` / EI-DI ordering, or KEYINT not
clearing the source under our paging). pg0_mainrom_in itself looks sound (CONOUT
uses it and works). · **My plan (PAUSING for sign-off — this is asm on the
interrupt path):** next milestone = observe whether int_h_body's `call $0038`
actually reaches main-ROM KEYINT ($0C3C) and acks S#0, then spec the fix before
touching asm. · confidence: HIGH on the re-baseline + storm mechanism; MEDIUM on
the precise ack-failure cause (one more probe needed). · undo: n/a (analysis +
6 new read-only probes, no production change).

**[M5.x / §8.75 — CORRECTION to the entry above] The int_h handler is NOT the
primary bug; the $4251 storm is a SECONDARY symptom masking a later control-flow
derail.** A pctrace armed on the first $4251 (the first interrupt) shows the
handler path works END-TO-END: $4251→$792B int_h_body→pg0_mainrom_in (paging
ok)→call $0038→$0C3C the real main-ROM KEYINT (H.KEYI $FD9A + H.TIMI $FD9F +
keyboard scan)→clean return through int_h_body cleanup→RET back to the interrupted
boot code at $0320 with SP recovering to $8FF8. ~700 steps stay healthy (multiple
interrupts + boot code, stack fine). So A-2 was a genuine improvement and the
handler acks correctly. · The collapse happens LATER: a primary derail (fingerprint
AF=C28C BC=C51C↓ DE=C5E4 HL=09E4 IX=F1AA IY=0314, SP frozen $4250) sends PC into a
runaway sweep; interrupts firing into int_h DURING the runaway are the "storm" we
kept catching. The triage oracle's SLIDE-with-SP-at-int_h-1 verdict is exactly this
aftermath. · **Why it matters for you:** the boot fix is NOT the interrupt handler —
it's the primary derail (reconnects with the pre-compaction M5.x kernel/COMMAND.COM-
sustain track). The storm-proof handler (Lever 2) is still worth doing but as
DIAGNOSTIC HARDENING (a non-destructive int_h makes a derail show as a clean SLIDE
pointing at the root, instead of a stack-marching storm that corrupts state and
hides it). · confidence: HIGH (the first-interrupt trace is unambiguous). · undo: n/a.

**[A-2 / LANDED — partial: advances the boot, downstream blocker remains] int_h now chains to the main-BIOS
KEYINT.** Greenlit + implemented per tier2-a2-spec.md. `int_h` ($4251) is now a net-zero trampoline
(`jp int_h_body` + `ds 3`; dskio unmoved); `int_h_body` (free tail) pages the main ROM into page 0 via the new
shared `pg0_mainrom_in/out` helper (factored out of CONOUT — `conout_set_sub` merged in, `CONOUT_A8`→shared
`PG_SV_A8`), `call $0038` (main-ROM KEYINT: VDP ack + H.KEYI/H.TIMI/keyboard/JIFFY), `di`, restore, ret.
Portable (EXPTBL[0]). **RESULT:** regression GREEN (unit 18/18); pctrace `--arm 0x0100` distinct PCs **199→283**,
interrupt path ($0038/$FDA4) now serviced, COMMAND.COM runs broader ($07xx/$0Bxx/$19xx) with stable SP in the
window — a real advance. **BUT** settle-24 still ends in the `$D7B0-DC00`/`SP=$4250` runaway; stackwatch shows
the same `$4251`/`$0052` storm = AFTERMATH, so a downstream blocker remains (the runaway's true onset is upstream
of the storm). · NEXT: find the new first-divergence / runaway ONSET (the `$4251` storm is the symptom, not the
cause) — but FIRST the disk.asm source split (user-approved). · undo: int_h/CONOUT revert is one tail block.

**[A-1 / DONE — A-2 spec ready, AWAITING SIGN-OFF] Architecture-rework analysis complete (10am span).**
Resolved O-1/O-2/O-3 from spec + CF-3300 oracle (§8.70); wrote `disk/docs/tier2-a2-spec.md`; **landed NO rework
asm** (held per the deferral). Results:
- **O-1:** the DISK ROM installs the whole page-0 vector band + `$0038` (write-watch: `$5A31`/`$5A89`/`$5A8C`/
  `$5A8E`/`$5AB9`/`$5ABC`, all disk-ROM) → `lay_page0_env` is correct to exist; the bug is the handler BODIES are
  mapped-memory shortcuts, not the install.
- **O-2:** stock's `$0038` handler inter-slot-CALSLTs to the main-ROM KEYINT (`$0038`→`$0C3C`), which runs H.KEYI
  (`$FD9A`) + H.TIMI (`$FD9F`) = the full service. Our `int_h` does only a partial VDP ack → starves COMMAND.COM's
  timer/keyboard loop → the runaway.
- **O-3:** Interface-B surface = CHPUT (done M8b), KEYINT (A-2), RDSLT/WRSLT/CALSLT/ENASLT (A-3), CALLF (real).
- **A-2 (proposed):** rework `int_h` to inter-slot-call the main-ROM KEYINT via `EXPTBL[0]` (CONOUT pattern),
  drop the partial ack. Expected to clear the residual runaway. BIOS-agnostic (MSX1 standard → ports to C-BIOS).
**DECISION NEEDED (sign-off):** greenlight implementing A-2 per the spec? It's a focused change (rework `int_h`
+ factor a shared `EXPTBL[0]` page-0-switch helper with CONOUT); A-3 (the other inter-slot handlers) stays
separate. · confidence: high that A-2 is the right + likely runaway-clearing fix · undo: trivial (int_h is small).

**[ARCH / §8.69] TARGET REFRAME + ARCHITECTURE AUDIT (user-directed, in-loop) — CF-3300 = oracle, C-BIOS =
prime target.** User clarified: we validate inside the CF-3300 *proprietary main BIOS*, but that is the oracle's
environment; the prime target for our disk ROM is **C-BIOS**, and the goal is any standards-compliant MSX. M9
debugging had begun over-fitting our ROM to the CF-3300 BIOS's instruction-level behaviour (wrong success
criterion). Per user: **reason from spec + oracle (no C-BIOS experiments yet), document the corrected
architecture, and DEFER the rework** to a separate signed-off effort. Wrote `disk/docs/tier2-architecture-audit.md`.
Core finding — **two interfaces**: (A) disk-ROM↔MSXDOS.SYS/COMMAND.COM is BIOS-INDEPENDENT and layout-fixed by
the loaded DOS (so all M1–M8 kernel-veneer/work-area work is correct, not BIOS-specific); (B) disk-ROM↔main-BIOS
must be BIOS-AGNOSTIC (EXPTBL/CHPUT/KEYINT/slot work area). **All current bugs are on Interface B** and only
"work" on CF-3300 by that BIOS's tolerance: `int_h` is ack-only (doesn't chain to KEYINT — likely the M9
runaway's real cause), and the lay_page0_env inter-slot handlers are "mapped-memory" shortcuts (CONOUT already
had to bypass `calslt_h`). CONOUT/EXPTBL[0] (M8b) is the correct Interface-B template. Migration plan A-1..A-5 +
open items O-1 (who owns the page-0 DOS env → fate of lay_page0_env) / O-2 (KEYINT chaining contract) / O-3
(enumerate Interface-B surface) in the audit doc. NO code changed; Tier-1 green; M1–M8 NOT invalidated.
· DECISION: documented + deferred per user. Awaiting greenlight to start the rework (A-1).

**[M8b / §8.68] PORTABILITY FIX (user-flagged, in-loop) — CONOUT now reads EXPTBL[0] instead of hardcoding
slot 0.** First cut switched page 0 with `and $FC` (= "main ROM is primary slot 0, unexpanded") — a CF-3300-
specific bake-in, not faithful. Rewrote `conout_body` to read `EXPTBL[0]` ($FCC1) at runtime for the main-ROM
slot id, set page-0 primary from it, and (if expanded) program the page-0 subslot via the standard $FFFF/SLTTBL
protocol (`conout_set_sub`). User chose "Full ENASLT." Re-validated on CF-3300: unit 18/18, pctrace 207 distinct
PCs (≈ M8's 199 — identical banner-escape, behaviour unchanged where primary=0). **CAVEAT TO REVIEW: the
expanded-main-ROM sub-path (`conout_set_sub`) is NOT exercisable on the CF-3300 (EXPTBL[0]=$00, unexpanded), so
it is spec-derived (MSX2 TH §2.4) and unvalidated by probe.** Pages 1 (our code) & 2 (stack) are provably
untouched by it (only page-0/page-3 $A8 fields move). · confidence: high on the primary path; the expanded path
is correct-by-construction but unproven · undo: one-block revert of conout_body.

**[M8 / §8.68] REAL CONOUT IMPLEMENTED — banner loop escaped (56→199 PCs), a new later blocker exposed.**
Implemented `conout_body`: emit `A` via main-ROM CHPUT (`$00A2`) through a genuine inter-slot call (slot 0
unexpanded per measured `EXPTBL`, so a plain `$A8` page-0 switch). `$5454` → `jp conout_body`, NET-ZERO (the +2
is absorbed by the `ds $5FE5 - $` pad; `$5FE5` still `jp k_5FE5`). Regression GREEN (unit 18/18). Ours now
escapes the banner loop and runs COMMAND.COM's code broadly with a stable `SP≈$8FE0` (the §8.60-8.66
stack-runaway was banner-spin aftermath, now gone in this phase). BUT it still eventually reaches the old
`$D7B0-DC00`/`SP=$4250` end-state — a NEW downstream blocker past the banner. · DECISION: committing M8 as a
validated incremental advance (strictly further than before) and proceeding to M9 = characterise the new
divergence under span mode. · spec `disk/docs/tier2-m8-spec.md`. · confidence: high that CONOUT is correct &
necessary; the new blocker is open. · undo: `$5454` back to `ret` + drop `conout_body` (one-block revert).

**[M7 / §8.67] ROOT CRACKED, MILESTONE UN-BANKED — the blocker is our own no-op CONOUT veneer at `$5454`.**
You said "continue; we're still making genuine progress," so I resumed on the §8.66 stack-write-watch angle and
it paid off decisively. New probe `disk_probe_dosboot_stackwatch.py` ruled out the interrupt-storm/bad-`LD SP`
theories (both machines set `SP≈$9000` by design — §8.66's "stack too low" was a red herring). A properly
aligned PC-trace from `$0100` (regs near-identical there) is byte-identical for 20 steps then diverges at ONE
instruction: stock's `$5454` runs the real disk-ROM CONOUT (inter-slot call to BIOS CHPUT `$00A2`), ours' is a
bare `ret` — our deliberately-stubbed `conout` "first cut" (disk.asm §8.38). COMMAND.COM's banner loop branches
on CONOUT's return flags, so ours spins forever (56 distinct PCs, never escapes) while stock proceeds (482).
**The entire §8.60-8.66 chase (`$DA23`/`$607B`/`int_h` storm) was downstream aftermath of this one stub.**
Alignment is rock-solid — far stronger than the superseded `$607B` reading. · DECISION: proceeding to implement
a real CONOUT (M8) under span mode — emit `A` via CHPUT through a genuine inter-slot call, preserving regs;
clean-room-legit (documented BIOS ABI, no oracle disassembly). It's the deepest Tier-2 code yet (our `calslt_h`
is a simplified `jp (ix)`, so CONOUT must do its own slot switch). · confidence: very high on the root;
implementation effort unknown · undo: n/a (analysis + new probe).

**[M6 / §8.66] TIME-BOXED ATTEMPT DONE → MILESTONE BANKED.** _(SUPERSEDED by §8.67 — the "unresolved late stack/
interrupt corruption" is now fully explained as aftermath of the `$5454` CONOUT no-op; milestone un-banked.)_ You chose "one
time-boxed cleaner attempt." It found the proximate failure (interrupt-storm stack
corruption — `SP` walks into the page-1 ROM) but that too is a late symptom: the
first interrupt is handled cleanly and COMMAND.COM runs 4000+ instructions normally
before the corruption appears. The true root receded under every method. Per the
agreement, I banked and stopped. **Banked milestone:** the clean-room disk ROM loads
real MSX-DOS 1 + COMMAND.COM byte-perfect and begins executing it (interrupts handled
correctly through COMMAND.COM startup). Best untried angle for a future restart: a
stack-write watch to find the first unbalanced push. No code regressions — Tier-1
Disk-BASIC stays fully green. · nothing to action; this is the wrap-up.

**[M6 / §8.65] COURSE CORRECTION — the M6 pre-build spec is INVALIDATED, and the
M5.8/M5.9 "stale work area = root" thesis was a mis-aligned-comparison artifact.**
Read-watch probes show ours reads none of the stale work-area cells before it loops,
and the loaded COMMAND.COM image is byte-identical to stock — both machines do the
same `$0500` self-relocation, so our loader is correct and the work area isn't what
the derail reads. The hang is a kernel BDOS-service loop, reached while COMMAND.COM
runs. **No code was written on the invalidated path** (characterise-before-code held
the line — twice this session: wa_seg-incomplete §8.60 and pre-build §8.65). **Net
positive banked: the clean-room disk ROM loads real MSX-DOS + COMMAND.COM byte-perfect
and starts executing it.** Re-synced with the user on direction (keep drilling with a
cleaner BDOS-level method / bank the milestone / reprioritise). · confidence: high on
the invalidation; the final-hang root is still open.

**[M5.9 / §8.62] ROOT PINNED — the upstream divergence is the stubbed canonical
entry `$607B`.** _(SUPERSEDED by §8.65 — see above; this was a mis-aligned-checkpoint
reading. `$607B` is real and stubbed, but it is not proven to be the hang's cause.)_ Binary-searched the first work-area memory divergence (it's already
stale at `$0100`/`$D824`, i.e. during MSXDOS.SYS-init) and named the responsible
canonical ABI entry: **`$607B`**, a multi-purpose disk-ROM service the kernel calls
15× during init to do inter-slot block copies AND build the `$F2B8` (filename+DPB)
and `$F1A8` work-area structures. **Our `k_607B` is a bare `ret`** — so the work area
is never built → the `$DA23` hang. **Scoped sub-track (M6): characterise + implement
`k_607B`.** Clean-room-feasible (the data it builds is derived from the disk/DPB,
like our GETDPB — no oracle disassembly). · confidence: high · this supersedes the
"build more of the work area" framing below with a concrete single entry point.

**[M5.8 / §8.61] SCOPE FLAG — the COMMAND.COM-load blocker is an upstream
work-area-init gap, not a single hook/veneer.** I disproved two of my own
hypotheses (the `$F368` hook and `$50A9` both rejoin register-identical with stock)
and traced the real divergence to STALE work-area memory at `$D7CE`: ours leaves
`$DC80-$DCB2` and `$F1A8+` uninitialised (`$FF`) and (before the fix below)
clobbered `$F2B8`. These regions are built upstream by MSXDOS.SYS page-0 code and
disk-ROM routines ours apparently skips. **Why it matters for you:** the remaining
fix is "build more of the DOS work area" — a sub-track of unknown size, a shift from
the M5.6-era "fill the `$F368` hooks" framing. **My plan (proceeding unless you
redirect):** M5.9 = binary-search the first upstream divergence (memsnap at earlier
landmarks) to name the exact init step ours skips, THEN scope/spec the build. ·
confidence: high on the diagnosis, unknown on remaining effort · undo: n/a (analysis).

**[M5.8 / commit 6ba6393] Narrowed the `RES_STUBS` `$C9`-fill `$F24E-$F2FD → $F24E-$F2B7`.**
Decided to commit this standalone even though it does NOT clear the hang. · why: it
removes a genuine clobber bug — our fill was destroying the kernel's `07 "MSXDOS  SYS"`
+ DPB block at `$F2B8` (proven by memsnap + write-watch: stock builds it via
`$4354/$5667`, ours' only writer there was our own fill LDIR). Correct regardless of
the hang. · alternative: hold it until the whole work-area fix is ready (rejected —
it's an independent correctness fix and removes a confound). · confidence: high ·
undo: revert `RES_STUBS_END` to `$F2FE` (one line). · regression: unit 18/18,
DSKIO/FILES==CF-3300, BLOAD ok.

**[workflow] Adopted the autonomous-span mode mid-session and ran this whole M5.7→M5.8
investigation under it** (multiple probes + one committed fix without bouncing). This
queue + §8.60/§8.61 are the batch to review. · undo: n/a.


---

## Archived 2026-07-01 — CONIN arc (M12–M12d, M13), resolved by M13 + reviewed

Batched-reviewed & approved by the user 2026-07-01. The CONIN journey that ended in
M13 (Option A implemented, garbage spin gone, Tier-1 green). Moved here to keep the
live board to just the Open M14 entry.

**[M12d / harness investment + CONIN ABIs PINNED black-box (no asm). Option A is now fully specified.]**
· **context:** user chose "harden trace + add key injection" at the M12c fork. · **tooling built &
validated (commit `49a5a29`, no disk-ROM change, tests 19/19):** (1) **clean-room disasm guard** in
`omsx_session` — `ctx` decodes a mnemonic only when `DISOK && PC>=0x4000`; `OmsxRun` auto-sets DISOK=0
for the STOCK machine. Suppresses the whole reference machine + main-BIOS (`$0000-$3FFF`) + COMMAND.COM
(`$0100`); still decodes our own artifact. Re-ran the M12c trace → stock mnemonics now `-`, leak gone,
flow (PCs/call-targets) intact; fork printers pull `dis` from the ours-aligned record. (2) **key
injection** — `--keys/--keys-at` (openMSX `type`) on every mode; validated on stock: `12-25-99` echoes
at the date prompt and `\r` drives to a visible `A>`. · **ABIs PINNED (M12d, guarded `callseq`, regs +
call-counts + RAM-pointer walks only — NO code decode):** **PIN A** `--log 0x50E0` → entry is the CALL
target `$50E0` (`ret=$D88A`, kernel `~$D887`), **`DE`=func-`$0A` buffer base**, regs byte-identical
ours==stock. **PIN B** `--log 0x009F --keys '12-99\r'` → CHGET fires **7×** (was 1); `HL` walks the fill
ptr `$DA42+`, `D`=count, `E=$0A`=max → the buffer is the **published func-`$0A` layout** (`[+0]`max
/`[+1]`count/`[+2..]`chars). · **resolves all spec open questions:** entry `$50E0` + `DE`→buffer; **no**
return register (result is the buffer); **bare CHGET per char**, no input-phase CHSNS; interrupts work
(keys received). Folded into [tier2-conin-spec.md](tier2-conin-spec.md) v3 §3 "Resolved answers";
supersedes the `$544E`/`$5107` per-char framing (we replace the LINE routine at `$50E0` and call
published CHGET directly, so stock's inner convention is irrelevant). · **judgment calls:** (1) added a
small printer improvement (fork lines show OUR `dis`, not the now-blank stock side) — strictly readability,
ours records already obey the gate. (2) Did NOT write any asm — stopped at the ABI-complete spec per
[[spec-before-implementation]] + the user's standing CONIN hold. · **confidence:** HIGH — every ABI fact
is a register/RAM/call-count observation matching the published func-`$0A` contract; the guard verifiably
emits no stock code. · **undo:** docs + probes only; ROM at committed baseline (16384 B, Tier-1 19/19); no
disk mutation. · **awaiting user:** go-ahead to implement Option A (the veneer at `$50E0`), then validate
(`callseq --log 0x009F` ours 0→≥1; `screen --machine ours --keys '\r'` → `A>`; tests 19/19; rom 16384 B).

**[M12c / CONIN ABI-pin (no asm) — audit PASSED; then a TOOL clean-room HAZARD forced a HARD-STOP.]**
· **context:** the user-gated M12-span paper-trail audit RAN and **PASSED ✅ CLEAN** (run log at
`e2a5d5d`); user then chose "pin ABIs black-box, then pause" (characterization only, no asm). · **clean
results pinned (black-box, observed myself):** (1) re-confirmed the baseline — CHGET `$009F` **stock 1 /
ours 0** (`callseq --log 0x009F`); at the stock CHGET call the caller returns to `$F392` (high-RAM
kernel). (2) CHSNS `$009C` fires 12× during the **banner** (each carries `C=09` STROUT + `B`=banner char)
= CP/M-style break-poll on the OUTPUT path; stock blocks at the first input CHGET, so the **input-phase**
CHSNS/echo question is NOT observable without a keystroke. (3) control-flow only: ours executes the
`$50E0`-region as a **NOP-slide** (OUR ROM is `$00` there — our artifact); where stock CALLs `$544E` at
`$5107` ours just continues (no call); the genuinely non-converging blocker sits further down at a
`$0D11 ret` → ours `$DDFD`. · **HARD-STOP reason (clean-room):** the `disk_probe_diff.py` **`trace` mode
prints the decoded Z80 mnemonic at every fork PC**. Run on the STOCK machine those PCs are reference disk-
ROM code, so it **surfaced stock's console-routine internals** — the SAME `$F237/8/9` / `IX=$F459` /
`CALL $F2AC` / CR-check material M12b quarantined. That is reference-ROM disassembly (✗). I did NOT record
or use any of it (quarantined-on-sight); only the call-target/PC/our-own-`$00` facts above are kept (and
`$5107→$544E` was already a pre-M12b-clean call-target). · **this REVISES the audit:** the 2026-06-30
paper-trail rated `trace` "black-box — disassembly-of-flow only, no code-byte surfacing." That is
**imprecise**: it DOES surface decoded stock code whenever a fork lands on stock ROM. The probe needs a
guard (print PC + call-target only; suppress mnemonic decode for reference-ROM code regions). · **judgment
calls:** (1) hard-stopped the probing the moment the trace surfaced stock code, per the clean-room
hard-stop rule + [[no-reference-rom-disasm]]; (2) did not propagate the decoded internals into any
doc/asm; (3) realized Option A does NOT need stock internals at all — it builds from published CHGET
`$009F` / CHPUT `$00A2` / BDOS func-`$0A` + our own artifact, and the entry-ABI (buffer ptr in DE? buf[0]
=max?) can be pinned CLEAN via `callseq --log <entry>` (call-target+regs, the allowed kind) instead of
trace-disasm. · **what still needs tooling before pinning completes:** (a) a clean-room **guard on the
trace mnemonic decode**; (b) **key injection** (openMSX `type`/`keymatrixdown`) — the harness has none, and
the input-phase questions (return register on a completed line, input CHSNS/echo, interrupt safety under a
real CHGET block, and the GOAL's drive-past-BUFIN-to-`A>`) all require a keystroke. · **confidence:** HIGH
that the trace surfaced disassembly (verified the mnemonics are stock's 3-byte ops vs ours' 1-byte `$00`
slide); HIGH that Option A is buildable from clean sources without those internals. · **undo:** docs only;
ROM at committed baseline (16384 B, Tier-1 19/19); no disk mutation (probe uses tmp copy). · **awaiting
user:** direction on tooling — (i) add the trace clean-room guard + key injection, then resume pinning the
entry ABI via `callseq` and drive past BUFIN; or (ii) proceed to Option A on published contracts + our
artifact and validate empirically after.

**[M12 / CONIN — UNIFY: the M11 "two-bug" model collapses into ONE missing veneer. ROOT CAUSE PINNED;
spec drafted; NO asm yet.]** · **what I decided:** ran a falsify-first differential span and concluded
the sole DOS-boot blocker is that the relocated kernel's **`$544E` CONIN entry has no veneer** — it is
`$00` padding (`kernel.asm:50 ds $5454-$,$00`) that falls through into `$5454` (`jp conout_body`,
CONOUT). So COMMAND.COM's BUFIN→`CALL $544E` emits one garbage char and returns without CHGET/blocking →
the infinite prompt spin + `D8 3E 40` garbage. · **decisive evidence:** CHGET (`$009F`) called **1× on
stock, 0× on ours** (`callseq --log 0x009F`). · **what this OVERTURNS (logged so the next sync re-levels
the archived M11 entries):** (a) "func-9 STROUT emits zero chars / `$F398` vector unset" — REFUTED
(func-9 entry regs+sysvars byte-identical; func-9 chars DO reach CHPUT, the ret=$7934-vs-$F392 diff is
benign relocation). (b) "two independent bugs A+B, fix A first" — WRONG; one root cause, and the old
"Bug A" is a phantom (garbage = CONOUT mis-invoked by the CONIN fall-through). (c) A-2/int_h is NOT the
blocker — A-3/A-5 already chains KEYINT (the `$0038` trace fork re-converges = benign). · **judgment
calls:** (1) declared the M11 model superseded and rewrote [tier2-STATE.md](tier2-STATE.md) to the M12
unified model — this CHANGES the ratified "Bug A first, then Bug B" plan, hence this queue entry rather
than silent continuation. (2) drafted [tier2-conin-spec.md](tier2-conin-spec.md) but STOPPED before any
ROM edit (spec-before-implementation): two CONIN ABI questions still open (return register; CHSNS
needed?). (3) used ONLY the one harness (`disk_probe_diff.py`), no 58th probe. · **alternative
considered:** that func-9 has a genuinely separate broken output route (the M11 thesis) — refuted by the
byte-identical func-9 entry + benign CHPUT re-convergence. · **confidence:** HIGH on the root cause
(CHGET 0-vs-1 is decisive + the source grep confirms no `$544E`/CONIN exists); MEDIUM on the exact CONIN
return-register ABI (to pin before coding). · **undo:** docs only; ROM at committed baseline (16384 B,
Tier-1 19/19). · **awaiting:** sign-off on the spec before I add the `$544E` veneer.

**[M12b / CONIN ABI-pin — SCOPE SURPRISE + PROVENANCE BREACH (self-caught), HARD-STOP. NO asm.]**
· **what I found:** the single-`$544E`-veneer plan is INSUFFICIENT — the kernel delegates the whole BDOS
func-`$0A` line read to a disk-ROM console routine (entered ~`$50E0`, black-box PC trace), and **our
`build/disk.rom` is `$00` across `$50B7–$5453`** (our artifact), so ours NOP-slides into the `$5454`
CONOUT veneer. The fix is a clean-room reimplementation of the console-input contract — a milestone, not
the one-liner. · **PROVENANCE BREACH (the important one):** I pinned the ABIs by **reading + decoding
stock CF-3300 disk-ROM CODE bytes** (`capture --mem` on `$50xx`/`$544E`/`$5454`/`$5100`) — that is
disassembly-class, a ✗ source ([`allowed-sources.md`](../../docs/allowed-sources.md) line 119/142). User
had pre-emptively chosen "Hold — provenance first"; the review confirmed the breach. **Containment:** NO
asm was written (held before implementation), so nothing shipped is tainted; the breach lived only in the
M12/M12b *docs*, now quarantined. **Conclusions survive on clean sources** (none depended on the
disassembly): CONOUT→E (M10 black-box), CONIN→A (published CHGET `$009F` contract), func-`$0A` buffer
layout (published BDOS), subsystem-unimplemented (our own ROM `$00` + black-box trace). Logged in the
clean-room-audit run log (2026-06-30). · **judgment calls:** (1) STOPPED before asm (bigger-than-authorized
+ clean-room hard-stops per [[confirm-before-large-execution]] + [[spec-before-implementation]]). (2)
self-reported the breach and re-grounded the docs rather than letting the disassembly-derived restatements
stand. (3) spec v2 keeps Option A (clean-room buffered-line veneer from the documented func-`$0A` contract,
entry pinned black-box) / Option B (faithful rebuild, contracts pinned black-box). · **confidence:** HIGH
on scope + the breach assessment. · **undo:** docs only; ROM at committed baseline. · **DECISION (user
2026-06-30):** run a **wider paper-trail audit of the M12 span FIRST**, deferred to next session; CONIN
Option A implementation is GATED behind that audit passing. Next-action board updated accordingly.

**[M13 — CONIN Option A implemented (user go-ahead 2026-07-01). Tier-1 green, garbage spin GONE.]**
· **what I did:** implemented `tier2-conin-spec.md` v3 Option A: a `jp conin_line_body` veneer at the
pinned CALL target `$50E0` ([kernel.asm](kernel.asm)), consuming our own `$00` dead region (net-zero,
`disk.rom` still 16384 B); the body (`conin_line_body`, [runtime.asm](../runtime.asm)) reimplements the
published BDOS func-`$0A` buffered-line read clean-room: per-char inter-slot CHGET (`$009F`) via the
existing `pg0_mainrom_in/out` bridge, CR ends the line, BS edits back one char, else echo via
`conout_body` (reused, not duplicated) + store; result lives in the buffer (`[DE+1]`=count) per the
pinned no-return-register contract. Added 4 bytes of page-3 scratch (`CONIN_BUF/MAX/COUNT`) in
[init.asm](../init.asm) after `INT_SP_SAVE`, clear of `DRV_TRAMP`. · **validated:** `make unit-test`
19/19; `disk.rom` == 16384 B; `callseq --log 0x009F` (no keys) → **1 call both sides** (was stock-1/ours-0
before this fix); `screen --machine both --settle 16` → **ours' infinite `D8 3E 40` spin is GONE** (static
screen, blocked at CHGET, matching the expected "block" behavior); with `--keys '12-25-99\r'` → **10 CHGET
calls both sides** (9 chars + CR, exact match), keystrokes echo correctly on ours via the CONOUT reuse.
· **new finding (NOT part of this milestone, logged for next sync):** even with keys injected, ours does
NOT reach a visible `A>` — after the typed date+CR, the screen just holds (no further output). Screen
inspection shows ours never rendered the `COMMAND version 1.08` / `Current date is Sun 84-01-01` /
`Enter new date: ` labels as separate lines at all — even in the NO-KEYS baseline (settle 16, before any
CHGET fires) ours shows a compressed `Sun 84-01-01` with the extra BASIC power-on banner (`MSX system
version 1.0` / `Copyright 1983`) still on screen above it, rows offset from stock. Since this renders
BEFORE any console-input call, it can't be caused by `conin_line_body`'s echo/edit logic — it's a
pre-existing CONOUT/newline/scroll gap that the old infinite spin was masking (nothing to compare against
before, since ours never held a stable frame). Likely the next milestone (M14): investigate why
COMMAND.COM's banner/prompt lines aren't rendering as stock does, falsify-first, `screen` as arbiter. ·
**judgment calls:** (1) reused `conout_body` for CONIN's echo (DE/E already the CONOUT ABI; less code,
same legitimacy) rather than a second CHPUT bridge. (2) buffer-full behavior = silently drop the char (no
bell/wrap) — undocumented in the func-`$0A` spec, own-design, matches the "smallest correct surface" v3
called for. (3) no flag-state contract established for the return (PIN said no return REGISTER; flags
unspecified) — if M14 finds COMMAND.COM cares about a flag on return from `$50E0`, revisit. ·
**confidence:** HIGH the CONIN fix itself is correct (CHGET counts + no-spin are decisive); the `A>` gap
is a SEPARATE, not-yet-characterised issue. · **undo:** `git revert` the CONIN commit; ROM stays
16384 B either way.

---

**[M15 / IMPLEMENTED + VALIDATED (2026-07-02) — user signed off on §9.3 option (ii); M15 CLOSED.]**
· User approved: "all approved, continue with (ii)". Moved `res_print_tmpl` to the free tail
(kernel.asm, next to `p1_blit_tmpl`/`wa_seg_*_tmpl`/`f365_iord_tmpl`), added the CONOUT-emit body
from spec §9.2 verbatim, added `install_res_print` (mirrors `install_f365`), and replaced
`build_resident`'s inline LDIR setup with a 3-byte `call install_res_print` (net shrink of the
cramped pre-`$41FD` region, avoiding the §7.3 overflow trap). · Verified per the §7.3 lesson:
`--bin ... out.rom out.sym` under pasmo's auto 3-pass mode → object file 16384 B (non-empty), all
new symbols resolve. · All §9.4 acceptance criteria met: `screen` renders the 3 COMMAND.COM lines;
`--log 0x00A2` 72/72 (was 12); `--log 0x009C` full per-char stream; `--log 0x009F` M13 regression
1/1 intact; `make unit-test` 19/19; `disk.rom` 16384 B. · **undo:** clean — Tier-1 green, net-zero,
no canonical-address shifts. · **next:** drive to visible `A>`; revisit deferred OI-3 (BASIC banner
not cleared).

---

**[M15 / ROOT CAUSE FOUND — `res_print_tmpl` is a no-emit stub; the whole wa_seg/$F365/page-1 thread
was a red herring. No asm; HARD-STOP for sign-off before the (now trivial) fix.]**
· **The reframe (deep-think first, per handover):** rather than mechanically widen the §7.2 `readwatch`
sweep (clean-room risk: might drift into stock code), I re-read [tier2-workarea-map.md] + M5.6 spec and
noticed `$F368`/`$F36B` are a page-1-flip PAIR (map disk ROM into page 1, run a resident routine there,
map RAM back). Hypothesis: the func-9 output worker is a page-1 disk-ROM routine ours stubbed. · **New
probe mode `callwatch`** (committed): enumerates which of OUR page-1 routines ($4000-$7FFF) the func-9
loop invokes — our own code, entry-PC counts only, clean-room-safe, decodes nothing on stock, defaults
`--machine ours`. · **Result 1 — hypothesis FALSIFIED but decisively:** `callwatch --machine ours`
gated to func-9 = **ZERO page-1 entries** (ungated shows normal $4462/$553C/$5454 activity, so the
mechanism works). ⇒ func-9's output path is entirely page-3/relocated-kernel; the `$F368`/`$F36B`
paging (§7.1) is CONCURRENT kernel work, NOT on the output path. The whole §§3–7 wa_seg/$F365 thread
is a red herring — this retroactively explains §7.3's negative build. · **Result 2 — root cause:**
`capture --at 0x0005 --nth 1` → DE=$C284 (STROUT string ptr), byte-identical both, reg-diffs NONE.
`readwatch --range 0xC284:0x40` gated func-9 → **ours reads ALL 27 bytes** of `\r\nCOMMAND version
1.08\r\n\r\n$` via reader PC **$F1C9 = RES_PRINT = our own `res_print_tmpl`** (stock reads via $F1CC,
its +3 equivalent, NOT decoded). Ours traverses the whole string and emits nothing — matching M14
(CHPUT gets 0 func-9 chars). · **Confirmed from OUR OWN SOURCE (no stock decode):** `res_print_tmpl`
([init.asm] :609) is straight-line `ld a,(de)/inc de/cp '$'/ret z/jr` with NO CHPUT/CONOUT call — and
its own comment says *"Our first cut CONSUMES the string … it does not yet emit the characters."* So
§7.2's "caller is NOT RES_PRINT" was wrong (reasoned from return addr $D88E; the actual consumer is
$F1C9). · **Fix (approach A, spec §9.2):** add `push de / ld e,a / call conout_body / pop de` before
the `jr` — emit each char via our proven CONOUT ($5454→CHPUT, char-in-E per M10), exactly as
`conin_line_body` echoes (runtime.asm:165). Preserves the DE-past-$/A=$24 return contract. Clean-room
(published func-9 + our own CONOUT). · **judgment call:** hard-stopped at the asm boundary
([[spec-before-implementation]]) — wrote spec §9 + updated STATE + committed the `callwatch` mode, did
NOT write the fix asm. · **the one build risk:** the pre-$41FD template budget (§7.3 silent-overflow
trap). Spec §9.3 gives two options; recommends (ii) moving `res_print_tmpl` to the free tail (net-zero)
so budget is a non-issue. **This is a design-ish fork (option i vs ii) → user steer wanted.**
· **confidence:** VERY HIGH on the root cause (our own source comment + string-read + zero-page-1 +
M14 CHPUT=0 all agree; and it's the same class as the M10 CONOUT / M13 CONIN gaps we already fixed the
same way). · **undo:** docs + one probe mode only; ROM at committed baseline (16384 B, 19/19). · **awaiting:**
(i) sign-off to implement §9.2; (ii) steer on build option (i grow-in-place vs ii move-to-tail).

**[M14 / banner blocker CHARACTERISED — it is a func-9 STROUT OUTPUT gap, and this CORRECTS the M12
"func-9 is fine" refutation. No asm; HARD-STOP for sign-off before any fix.]**
· **falsify-first (screen = arbiter):** `screen --machine ours --settle 16/35` are identical steady frames
(not slow) — ours renders only `Sun 84-01-01` (+ the un-cleared BASIC power-on banner), missing
`COMMAND version 1.08` / `Current date is ` / `Enter new date:`. · **decisive alignment:** `callseq --at
0x0100 --log 0x0005` → **ours == stock BYTE-IDENTICAL for all 18 BDOS calls** (STROUT×3, FOPEN, GDATE,
CONOUT×12, BUFIN — same C/A/B/DE/HL/ret). So COMMAND.COM's control flow is CORRECT; it *issues* every
STROUT. · **the gap is downstream in output servicing:** `callseq --log 0x00A2` (CHPUT, the shared
bottleneck) → stock emits all 72 chars (banner+prompt); **ours emits ONLY the 12 date chars**, which at
`$0005` are `C=02` CONOUT (n=5-16), reaching CHPUT via `ret=7934` = our `$5454` conout_body veneer.
Every `C=09` STROUT char is ABSENT from CHPUT on ours. `--log 0x5454` → ours 12 (date) / stock 0.
· **⇒ func-2 CONOUT works on ours (date renders via $5454); func-9 STROUT emits ZERO chars to CHPUT.**
· **CORRECTS M12 (archived-M11 re-level (a)):** M12 refuted "func-9 emits zero / `$F398` vector unset"
citing "func-9 chars DO reach CHPUT, ret=$7934-vs-$F392 benign." Those `ret=$7934` chars are the func-2
DATE (`C=02`), not func-9 STROUT (`C=09`) — a mislabel; the screen arbiter confirms func-9 literals never
render. The func-9-output-gap hypothesis is BACK, now with 18/18 dispatch alignment behind it.
· **routing note:** stock funnels ALL console output through the kernel `$F392` path; ours vectors func-2
to disk-ROM `$5454` and loses func-9. · **LOCALISED (black-box, no kernel decode, user chose this at the
M14 sync):** `--log 0xF392` ours **0** / stock **90**; `--log 0x009C` (CHSNS per-char break-poll on the
output loop, B=char) ours **0** / stock **72**. ⇒ ours' func-9 handler dispatches but NEVER enters the
char-output loop — the `$F392` resident routine (CHSNS-poll + CHPUT) is never reached; func-9 returns
having emitted nothing. func-2 works via a different wired path (`$5454`). Same SHAPE as the `$4462` FOPEN
gap: a shared-kernel routine that's live on stock, unreached/stubbed on ours. Deliberately did NOT `trace`
into `$F392`/`$F2AC`/`$F237` (M12c reference-disasm hazard). Fix target + approach in
[tier2-m15-spec.md](tier2-m15-spec.md) (DRAFT, no asm). · **§3 PIN (user chose "do it now", no asm):**
`capture --at 0x0005 --nth 1 --mem 0xF340:0x40` (aligned, reg-diffs NONE) → ours' DOS work-area page-3
substantially UNBUILT (FF at `$F345/$F347/$F358-$F367`; `$F368` JP-table half-stubbed →`$41AF`×5;
pointers `$F34D-$F356` diverge). ⇒ **NOT P-vector; leans P-resident** → the fix is approach (B)
work-area construction, HEAVIER than the recommended (A). **SCOPE SURPRISE flagged** (spec §7/OI-4).
Stayed clean-room: pointer-only region, did NOT capture the `$F38x` console-code bytes. **CAVEAT
([[tier2-investigation-guardrails]] / §8.65):** "unbuilt" proven, CAUSALITY not — func-9 not yet shown
to read a specific stubbed cell; gate the fix behind a read/call-through confirmation (needs a small
probe extension, no asm). · **CAUSAL CONFIRMATION DONE (user chose "confirm first, no asm"): built a
new `readwatch` mode** (per-byte `read_mem` watchpoints over a DATA range, gated to during-func-9,
records reader-PC+addr+value only — no code decode; committed with the probe). Gated reads of
`$F340:0x40`: STOCK func-9 output loop PAGES via the segment hooks — `$F368`→`JP $DF57` ×46,
`$F36B`→`JP $DF59` ×45, slot bytes `$F342`/`$F348` (PC `$DF5A`/`$DF60`), `$F365` `in a,($A8)` ×12;
OURS `$F368`→`JP $E795`/`$F36B`→`JP $E79B` (M5.6 `wa_seg`) only ×3 then ABORTS, `$F365` FF/unbuilt.
**⇒ passes §8.65 (func-9 demonstrably routes through the hooks on both); blocker = M5.6 `wa_seg` is an
INCOMPLETE `$DF57` (§8.57 thread, now tied to func-9 output). Scope BOUNDED: complete `wa_seg`+`$F365`,
NOT the broad work-area sub-track — feared bigger, measured smaller.** §8.61 once judged this hook
"rejoins register-identical," but that was the earlier blocker; func-9's 45× paging is a new
manifestation (not a blind re-walk). **HARD-STOP: the fix is ROM asm → sign-off before coding.**
· **judgment call:**
hard-stopped here rather than implementing — this re-opens a refuted item AND the fix (route func-9 output
to a working CONOUT / build the resident CONOUT dependency) is a new slice wanting a spec + sign-off
([[spec-before-implementation]]). · **confidence:** HIGH that func-9 STROUT output is the blocker
(screen arbiter + C=09-vs-C=02 char labelling at both $0005 and $00A2 + 18/18 alignment). MEDIUM on the
exact mechanism/fix (needs clean-room-safe localisation of func-9's output target). · **undo:** docs only;
ROM at committed baseline (16384 B, Tier-1 19/19); probe used tmp disk copy. · **awaiting:** (i) confirm
the M12 correction; (ii) steer on localising func-9's output path clean-room-safely (no kernel disasm);
(iii) sign-off on the fix approach once localised.

---
