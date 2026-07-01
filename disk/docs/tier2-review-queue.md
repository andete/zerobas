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

## Archived

Reviewed & re-levelled entries (M5–M10 history) have been split into
[tier2-review-archive.md](tier2-review-archive.md) to keep this live board lean.
Only **Open** (awaiting next sync) lives here.

