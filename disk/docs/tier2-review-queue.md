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

## Archived

Reviewed & re-levelled entries (M5–M10 history) have been split into
[tier2-review-archive.md](tier2-review-archive.md) to keep this live board lean.
Only **Open** (awaiting next sync) lives here.

