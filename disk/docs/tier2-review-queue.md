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

## Archived

Reviewed & re-levelled entries (M5–M10 history) have been split into
[tier2-review-archive.md](tier2-review-archive.md) to keep this live board lean.
Only **Open** (awaiting next sync) lives here.

