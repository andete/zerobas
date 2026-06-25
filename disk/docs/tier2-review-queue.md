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
