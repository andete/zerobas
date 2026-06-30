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
on scope + the breach assessment. · **undo:** docs only; ROM at committed baseline. · **awaiting:**
go-ahead to implement (Option A) AND, if wanted, whether to run a wider paper-trail audit of the M12 span.

---

## Archived

Reviewed & re-levelled entries (M5–M10 history) have been split into
[tier2-review-archive.md](tier2-review-archive.md) to keep this live board lean.
Only **Open** (awaiting next sync) lives here.

