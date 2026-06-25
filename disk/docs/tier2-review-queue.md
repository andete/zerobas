<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 review queue — decisions taken without per-step sign-off

Running log for the **autonomous-span** working mode (2026-06-25). During a span I
chain `characterise → spec → implement → validate → commit` across milestones
without bouncing back; every judgment call I'd normally have asked about lands here.
When the user is back we do **one batched review** of the open entries, then I
archive them (move the resolved block under "Archived").

**Hard-stops (I pause the span and wait):** a design fork that hinges on user taste;
a clean-room legitimacy call I'm unsure of; anything irreversible/outward-facing;
a regression I can't get green or a blocker I can't crack; a scope surprise that
changes a signed-off plan.

Entry format: **[Mx.y / §8.zz]** what I decided · why · alternative · confidence ·
undo. Newest first.

---

## Open (awaiting next sync)

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

## Archived (reviewed & re-levelled)

_(empty)_
