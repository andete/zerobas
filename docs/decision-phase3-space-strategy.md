<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Decision — Phase-3 ROM-space strategy

Status: **PROPOSED 2026-07-11, awaiting user sign-off.** Deliverable of the
deep-think session commissioned by
[`handover-phase3-space-strategy.md`](handover-phase3-space-strategy.md).
Every number below is **measured** on the post-F2 tree (commit `ba90d1d`,
fresh `make` + `make basic-reloc` + `make repack-main` artifacts) or on the
pinned C-BIOS checkout — sources noted per table. No implementation was done;
per the spec-before-implementation rule, nothing here is a green light until
signed off.

## 1. The question

After float F2 the repack BASIC window (`$2812–$7FFF`, ~21.5 KB) is FULL:
2 B of page-0 slack, 29 B of page-1 tail. F3 (typed variables) has no home —
but F3 is only the next ~0.9 KB of a **~14–21 KB** remaining Phase-3 roadmap
(§3). The decision is therefore not "where do 600 bytes for F3 come from" but
**which lever (or staged sequence) carries the rest of Phase 3**, priced
against the clean-room firewall, the shipped-artifact structure, and the
standing gates.

Headline: every in-ROM lever combined — gap fills, golf, deletion-only BIOS
cuts — tops out near **2 KB** (§4a/b/e). The roadmap needs an order of
magnitude more. Only the **extension-slot ROM** (§4d) has a roadmap-scale
ceiling, and it is the recommendation (§6), with the gap-fill machinery
demoted to an optional reserve.

## 2. Measured geometry (merged main ROM, post-F2)

Zero-run scan of `build/zerobas-main-eu.rom` vs the pristine/repacked C-BIOS
(EU MSX1), 2026-07-11:

| Region | Size | Status |
|---|---|---|
| `$0160–$01FF` | **160 B** | free fill. It is the MSX2 BIOS jump-table shadow: on MSX1 (`VDP = TMS99X8`) C-BIOS emits a fake-EXTROM `ret` at `$015F` and nothing more until `$0200` (`src/main.asm` line ~540). Caveat: a stray call to an MSX2-only entry (`$0162 CHKSLZ` … `$0177 NWRVRM`) today NOP-slides into `$0200`; with code here it would execute that code instead. Both behaviours are undefined on an MSX1, so the delta is marginal — but it is a *judgment call* and the region is best kept as reserve, not first-choice. |
| `$09D9–$09ED` | **21 B** | free on **MSX1 only** (MSX2 mains have content to `$09ED`). Usable in the EU-MSX1 merged ROM; not by the universal standalone tape IPS. |
| `$09EE–$0BBE` | 465 B | **zerobas-tape body** (D5 revision, `781348f`) — occupied, ours. |
| `$0BBF–$0D00` | **322 B** | free — gap-1 remainder above the tape body. |
| `$1ACA–$1BC6` | **253 B** | free — gap-2, below the pinned font. |
| `$2812–$3FFD` | — | BASIC low region, full (2 B slack to the `$4000` header). |
| `$4000–$7FE2` | — | BASIC page 1, full (**29 B** tail). |

Total reachable by a multi-region build: 322 + 253 = **575 B firm**, plus
160 + 21 = 181 B with the caveats above → **≤ 756 B**, one-shot, EU-MSX1
merged ROM only. (The lean 16 KB `basic.rom` stays byte-identical and is not
part of this problem; the standalone tape IPS keeps its own org build.)

Current low-region tenants (per-include spans from the pasmo symbol table;
±16 B):

| Module | Span | Size |
|---|---|---|
| kwtable.inc | `$2812–` | 626 B |
| str-engine.asm | `$2A84–` | 1 718 B |
| input.asm | `$313A–` | 449 B |
| float.asm (F1 tokeniser + formatter) | `$32FB–` | 1 294 B |
| float-arith.asm (F2 BCD core) | `$3809–$3FFD` | ~2 040 B |

## 3. The sized roadmap remainder

### 3a. Calibration — estimates run ~1.4× over

The two float slices give a measured estimate→actual factor (window shrink,
tape-move accounted):

| Slice | Estimated | Actual cost | Factor |
|---|---|---|---|
| F1 | ~1 331 B | 1 688 B (3 692→2 004 free) | ×1.27 |
| F2 | ~1 536 B | 2 438 B (2 004+465→31 free) | ×1.59 |
| blended | | | **×1.44** |

So **F3's "~0.6 KB" should be planned as ~0.85–0.9 KB** — by itself already
at the edge of what the gap fill (§4a) can supply.

### 3b. The blocks (calibrated ranges)

"Placement" anticipates §4d: **in-window** = interpreter-woven or hot
(dispatch loop, var store, parser, run loop) — must stay in the contiguous
`$2812–$7FFF` image; **ext-suitable** = function/statement-shaped, callable
through one CALSLT with args marshalled in page-3 RAM.

| Block | Est. | Placement |
|---|---|---|
| F3 typed variables | **0.9 KB** | in-window (var store, LET/eval hot paths) |
| `^` + math functions (SQR SIN COS TAN ATN EXP LOG RND FIX INT CINT CSNG CDBL; + coefficient tables) | **2.5–4 KB** | ext-suitable (leaf over the BCD core; anchor: F2's 4 ops + relationals = 2.4 KB) |
| DEFINT/DEFSNG/DEFDBL/DEFSTR | 0.2 KB | in-window (tokeniser + var key) |
| floats in VAL / STR$ | 0.3 KB | glue over the F1 converter/formatter (which are themselves evictable) |
| float INPUT / READ / DATA fields | 0.3 KB | in-window (parser) |
| float FOR/NEXT (D-D) | 0.4–0.6 KB | in-window (run loop) |
| float PRINT USING specs | 0.5–0.7 KB | ext-suitable (formatter-shaped; int printusing measured 668 B) |
| MKS$/MKD$/CVS/CVD | 0.15 KB | glue |
| **numeric-core subtotal** | **5.2–7.1 KB** | |
| heap + descriptors + STRMAX→255 (ROM side) | 1–1.5 KB | in-window (every string op) |
| arrays + DIM (numeric + string) | 0.8–1.2 KB | in-window (var store) |
| **data-structure subtotal** | **1.8–2.7 KB** | |
| error handling (ON ERROR/RESUME/ERR/ERL + messages) | 0.5–0.8 KB | in-window (dispatch) + text tables ext-suitable |
| interrupt traps (ON KEY/INTERVAL/STOP/SPRITE) | 0.5–0.7 KB | in-window (run loop) |
| input devices (STICK/STRIG/PAD/PDL, KEY(n)) | 0.3–0.5 KB | thin wrappers (+ possible tape-component BIOS completions) |
| editor / program mgmt (DELETE, RENUM, AUTO, TRON/TROFF, SWAP, WAIT, ERASE, FRE, LIST ranges, full CLEAR) | 0.8–1.2 KB | mostly ext-suitable (cold tools) |
| screen-editor REPL | 0.6–0.9 KB | in-window |
| **language-completion subtotal** | **2.7–4.1 KB** | |
| graphics (LINE/PSET/PRESET/CIRCLE/PAINT/DRAW/sprites/VDP) | 3–4.5 KB | ext-suitable bodies + small in-window dispatch |
| sound (PLAY MML/SOUND/BEEP) | 1.5–2.5 KB | ext-suitable (+ ~0.2 KB in-window queue hook) |
| **media subtotal** | **4.5–7 KB** | |
| **TOTAL remaining Phase 3** | **≈ 14–21 KB** | of which **in-window-bound ≈ 6.5–9 KB** |

Cross-check: zerobas's non-disk content is ~15 KB where the real VG-8020
fits its *entire* BASIC (math pack, graphics, PLAY, editor included) in
~22 KB — the ~14–21 KB remainder is consistent with that proportion, given
zerobas also carries ~7.3 KB of disk BASIC the real machine keeps in its
disk ROM.

## 4. The levers, measured

### 4a. Multi-region BASIC image (+ fold tape into the merged assembly)

**Yield: ≤ 756 B, one-shot** (575 B firm + 181 B caveated, §2).

Mechanism: restructure the merged-build assembly from the contiguous
`org $2812` image into a sparse `org $0000` 32 KB image using the same
`ds $xxxx-$` region-padding idiom C-BIOS itself uses, one `IF`-guarded
region per gap (each with its own overrun guard, like the existing `$4000`/
`$8000` guards). `tape/tape.asm` folds in as the `$09EE` region tenant
(merged build only — the standalone tape IPS keeps its own org build, per
the component-split decision). `build_mainrom.py` generalises from
fixed-constant splices to "overlay every non-zero byte, assert the repacked
base is free there" (its ref-safety check already exists); the tape vector
splices (`$00A5`, `$00E2–$00F5`) stay special-cased since they deliberately
overwrite stock bytes. `check_reloc.py` gains a free-region manifest;
lean-identity check unchanged.

- **Firewall:** unchanged — payload bytes are still ours-or-`$00`.
- **Artifacts:** merged ROM internal layout only; lean + tape IPS untouched.
- **Gates:** one full repack-side sweep after the rework (repack-boot,
  diskbasic-acceptance-repack 34, string 6, input 8, float 3 halves,
  tape battery for the fold-in, unit-test, lean hash). No new standing gate
  beyond the manifest check.
- **Cost:** ~1–2 sessions of build-machinery work.
- **Honest assessment:** the yield (≈0.76 KB) is consumed by F3 alone
  (≈0.85 KB calibrated) — this is exactly the "buys one slice" lever the
  handover warns about. Its durable value is as **infrastructure for
  fragments** (it is what makes 4b's deletion-only cuts and any future gap
  usable), not as the strategy.

### 4b. C-BIOS Tier-B tranche — the 2–3 KB figure does not survive the firewall

Two sub-cases with very different prices:

- **Deletion-only cuts** (zero dead content in place): keep the output
  firewall (a zeroed byte is `$00` in the IPS). Measured inventory: the
  "No cartridge found / …restart with a cartridge inserted" block
  `$2633–$26BD` ≈ 139 B (dead — the merged ROM's boot scan always finds our
  in-ROM `AB` header, proven by `make repack-boot`), "Cannot execute a BASIC
  ROM." ≈ 27 B, `debug.asm` helpers ≈ 60 B code, plus any BIOS routine
  proven unreachable (per-routine verify-on-execute, expensive). Realistic:
  **~0.2–0.5 KB, arriving as FRAGMENTS inside live BIOS** — they do not move
  the `$2812` boundary, so they are only usable if 4a's multi-region
  machinery exists.
- **Relocating/golfing cuts** (the escalation the space-analysis doc's
  "~2–3 KB" assumed): moving live C-BIOS code to new addresses makes the
  shipped IPS **carry C-BIOS code bytes** (target ≠ source at the new
  offsets). BSD-legal with attribution, but it kills the proven
  "**0 C-BIOS-leak bytes**" output-firewall property of
  [`cbios-repack-provenance.md`](cbios-repack-provenance.md) and the
  self-boot-by-construction argument (every reachable byte identical to
  stock). Verification burden becomes per-cut behavioural re-validation.
- **Recommendation: reject the relocation tranche outright**; keep
  deletion-only micro-cuts as an opportunistic follow-on *if* 4a ever lands.

### 4c. Heap-arc-first — not a space lever

Checked against the F3 spec: F3's ROM cost is typed-key parsing, coercion,
and typed LET/PRINT/eval paths — all store-model-independent. The heap arc
*adds* ROM (allocator, descriptors, GC) and competes for the same window;
the only saving is avoiding a later rewrite of the ~200–300 B store-layout
portion of vars.asm. **Rejected as a space lever.** The D-G ordering
recommendation stands: F3 first as specced (strong oracle surface), swap-out
contained behind `var_get_key`/`var_set_key`.

### 4d. Extension-slot ROM (`zerobas-basic-ext`) — the only roadmap-scale lever

A 16 KB "AB" cartridge ROM in its own slot — **exactly the zerobas-disk
model**, and almost everything it needs already exists:

- **Boot/dispatch:** `init_ext_roms` already scans every later slot for an
  `AB` header and CALSLTs its INIT (that is how disk.rom boots today); the
  generated machine configs already declare empty secondary slots 3-2/3-3.
  An ext ROM INIT sets a presence flag + slot id in RAM; main-ROM token
  handlers become thin stubs: evaluate args (parse stays in main ROM), stash
  in page-3 RAM (FAC/ARG/NUMTYP are visible from every slot), CALSLT a fixed
  entry-table offset (the `$4010`-style pattern), read results from RAM.
  Absent the ROM, stubs abort with a proper error (own-design wording).
- **Hot-path cost, measured from the C-BIOS CALSLT source:** ~300–500
  T-states round trip (expanded slot) ≈ 0.1 ms at 3.58 MHz. Precedent:
  **every disk sector op already makes this exact page-1→page-1 CALSLT**
  (`$4010` DSKIO). For function-shaped tenants (a BCD SIN is 10⁵-ish
  T-states) the overhead is <1 %; per-PRINT formatting ~one call — imperceptible.
- **Ceiling: 16 KB** (extensible later to 32 KB across the ext slot's
  pages 1+2 — CALSLT switches only the called page — but 16 KB is the sane
  first step and matches the disk.rom tooling wholesale).
- **Firewall: trivially clean.** Pure zerobas bytes, ships as a plain
  `.rom` like disk.rom — no C-BIOS interaction, no IPS, no provenance
  argument needed beyond the normal one.
- **Faithfulness:** the *mechanism* is canonical MSX — Disk BASIC,
  MSX-MUSIC FM-BASIC, and Kanji BASIC all extended BASIC from cartridge
  ROMs. (Real MSX kept SIN/COS in the main ROM; zerobas putting them in an
  extension cart is a documented own-design divergence, priced against the
  alternative of cutting into C-BIOS.)
- **Artifacts:** a **NEW shipped deliverable** — the product-shape change
  only the user can approve (§7 Q1). Lean cart + tape IPS + merged ROM all
  unchanged; the merged machine gains an optional companion ROM.
- **Gates:** new ext-present + ext-absent boot gate; existing standing gates
  unchanged; each evicted/added feature re-runs its own differential gate.
- **What it also unlocks — evictions.** Because in-window demand
  (~6.5–9 KB, §3b) exceeds every in-window supply, the ext ROM matters
  twice: new big blocks land there natively, AND already-landed
  *sink-decoupled* modules can move there to free window space. Measured
  candidate ladder, cheapest first:

  | Eviction wave | Modules | Frees in-window | Cost |
  |---|---|---|---|
  | 1 — already RAM-sink-decoupled | float.asm (tokeniser reads linebuf, formatter writes FOUTBUF) 1 294 B; screen.asm (thin BIOS wrappers) 251 B | **~1.5 KB** | low; float gates re-run |
  | 2 — buffered-sink refactor | list.asm/detok 765 B; printusing.asm 668 B (both emit per-char via pchar today → buffer in RAM, main prints) | ~1.4 KB | medium |
  | 3 — hot BCD core | float-arith.asm ~2.0 KB | ~2.0 KB | ~5–15 % tax on float-heavy arithmetic (one CALSLT per float operator) |
  | 4 — disk verbs | files+field ≈ 3.1 KB | ~3.1 KB | the cross-slot interpreter-services ABI the 2026-07-09 relocation study sized as a sub-project (163 call sites) — the known anti-pattern; only if ever truly needed |

  Waves 1–2 (+ gap/golf scraps) cover the in-window demand of the numeric
  core + heap + arrays; waves 3–4 exist as reserves if full parity
  (graphics-era in-window pieces, screen editor) exhausts them.

### 4e. Dedup/golf — complement only

Known candidates (float.asm ↔ float-arith.asm unpack/digit sharing, kwtable
compression) ≈ **0.2–0.4 KB**, one-shot, after F2 already took ~10 trim
rounds. Run opportunistically inside slices; never the plan.

## 5. Staged combinations considered

- **A. Gap-fill first:** (a)+(e) → F3 → ext ROM later for the math pack.
  Buys F3 with the smallest immediate arc, but builds ~756 B of machinery
  that F3 alone consumes, and hits the same in-window wall (heap/arrays)
  2–3 slices later with no answer — at which point the ext ROM + evictions
  are needed anyway. Total work ≥ B, strictly later payoff.
- **B. Ext-ROM first (recommended, §6):** stand up `zerobas-basic-ext`, do
  eviction wave 1 (float.asm 1.3 KB → window), land F3 in the freed window
  (~0.45 KB margin), then the math pack lands ext-natively. (a) is shelved
  as reserve; tape stays at `$09EE` (the fold-in was only ever natural *as
  part of* (a)'s rebuild). Deletion-only 4b cuts stay pocketed for later.
- **C. Tier-B once, then ext ROM:** rejected — the relocation tranche breaks
  the output firewall (4b) for at best one block's worth of bytes, and the
  ext ROM makes those bytes unnecessary.

## 6. Recommendation

**Adopt staging B — make the extension-slot ROM the durable Phase-3 space
strategy; do not spend a session on the gap-fill machinery first.**

Concrete sequence (each its own spec'd, gated session per the standing
cadence):

1. **S1 — `zerobas-basic-ext` arc spec** (naming, slot choice, entry-table
   ABI, presence/absence semantics, real-hardware stance) → sign-off.
2. **S2 — skeleton + tooling:** empty ext ROM builds, machine configs gain
   it, presence flag + stub-error path, new boot gate (present + absent).
   ~1 session; reuses the disk.rom patterns wholesale.
3. **S3 — eviction wave 1:** float.asm (tokeniser + formatter) moves ext;
   full float-acceptance + crunch re-run. Window regains ~1.3 KB.
4. **F3 lands in-window** (as specced, D-G unchanged), with margin; then
   the small numeric follow-ups (DEF*, VAL/STR$, MK*/CV*) in-window, and
   the **math pack** as the ext ROM's first native tenant.
5. Heap arc → arrays in-window, drawing on eviction wave 2 when needed;
   (e) golf opportunistically; 4b deletion-only cuts only if (a)'s
   machinery ever gets built for other reasons.

Why this over A: the roadmap's in-window-bound demand (~6.5–9 KB) can only
be met by evictions into an ext ROM — that conclusion is forced by the
measurements regardless of what happens first, so the strategy should build
the durable mechanism now rather than after one more stopgap. Why this over
Tier B: 16 KB of clean-provenance ceiling vs ≤2–3 KB that costs the
firewall property the repack arc just proved.

What it unblocks immediately: F3 two sessions from sign-off; the math pack
with no further space decisions; a placement rule ("hot/woven in-window,
function-shaped ext") that answers every future slice's "where does it go".

## 7. Open questions — the user's call

1. **Ship a third ROM deliverable?** `zerobas-basic-ext` changes the product
   shape (README/charter list, a second cartridge on real hardware next to
   the disk interface). Approve the deliverable in principle? Preferred slot
   (3-2 internal, like disk's 3-1, vs. a cartridge slot) and name?
   **→ ANSWERED 2026-07-11, see §8: built-in MSX2-style sub-ROM in slot 3-0
   of the virtual zerobas machine, not a cartridge.**
2. **Phase-3 ambition check.** The sizing assumes heap+arrays and
   (eventually) graphics/sound are real Phase-3 goals. If the charter stops
   at "numeric core complete", staging A (gap-fill, no evictions, math pack
   ext later) becomes defensible. Which is it?
3. **Divergence acceptance:** core math functions (SIN/COS/…) living in an
   extension cart rather than the main ROM is faithful in mechanism but not
   in placement — acceptable as a documented own-design divergence?
4. **Tier-B relocation formally rejected?** Confirm retiring the space-analysis
   doc's "~2–3 KB Tier B" as a strategy option on firewall grounds
   (deletion-only micro-cuts remain available under 4a).
5. **Gap-fill machinery (a) + tape fold-in:** shelve as reserve (recommended)
   even though the fold-in was your suggestion — or build it anyway in
   parallel because you want the gaps harvested and the merged build
   simplified regardless?
6. **F2 close-out riders:** the D5 tape move to `$09EE` (judgment call,
   flagged) — OK to ratify as part of this sign-off?

## 8. Addendum (2026-07-11) — user direction on Q1: a built-in sub-ROM in the virtual zerobas machine

The user reframed the deliverable: zerobas is ultimately **a virtual MSX1
machine whose built-in ROM complement we lay out ourselves, following the
example of real systems**. The Phase-3 spill-over ROM is therefore not a
cartridge but a **built-in MSX2-style sub-ROM**, with the machine's expanded
slot 3 laid out as: **3-0 = sub-ROM, 3-1 = disk ROM (unchanged), 3-3 = RAM
(moved from 3-0)**.

### 8a. Precedent check (real machines, openMSX hardware configs)

| Machine | Sub-ROM | Disk | RAM |
|---|---|---|---|
| Philips NMS 8250 | **3-0** | 3-3 | 3-2 (mapper) |
| Sony HB-F900 | **3-0** | 3-2 | 3-1 (mapper) |
| Sanyo PHC-23 | **3-0** | — | 3-2 |
| Sony HB-F700P/D | **3-0** (shares w/ disk) | 3-0 | **3-3** (mapper) |

Full-library survey (all 102 openMSX machine configs carrying a sub-ROM):
sub-ROM location is 3-0 in 53 machines (3-1 in 19 — 3-0 is decisively the
convention); main RAM sits in **3-2 in 50** machines (the plurality, e.g.
NMS 8250), 3-0 in 17 (FS-A1 family), **3-3 in 12** — among them the whole
Sony HB-F700 family, whose exact layout is `3-0 = sub-ROM (page 0) + disk
ROM (page 1), 3-3 = mapper RAM`. Since the sub-ROM takes 3-0, RAM must
move out of 3-0 either way, and the gate-churn cost of 3-2 (`$8B`) vs 3-3
(`$8F`) is identical — a pure precedent/taste call. **Chosen: RAM in 3-3,
after the user's own Sony HB-F700D.** Disk stays at 3-1 rather than
mimicking the F700's disk-in-3-0 stacking (no functional gain, extra
disk-gate re-baselining churn; the DRVTBL slot byte `$87` and all Tier-2
disk machinery assume 3-1). Each element of the resulting map is
individually precedented.

### 8b. Architectural consequence — the page-0 sub-ROM model supersedes §4d's cartridge model

A real MSX2 sub-ROM maps at **page 0** (`$0000–$3FFF`, `CD` signature) of
its slot; CALSLT switches only the *called* page. So during a sub-ROM call
**page 1 still maps slot 0 — the main BASIC ROM stays directly callable**,
and pages 2/3 (program RAM, sysvars, FAC/ARG) stay visible. This dissolves
§4d's biggest constraint: no cross-slot interpreter-services ABI, no
CALSLT-back per callback, and eviction wave 2's buffered-sink refactor
becomes unnecessary — cold page-1 modules can move to the sub-ROM and keep
calling `pchar`/`eval`/the var store directly. The eviction ladder
simplifies to: (1) anything cold in **page 1**, near-free; (2) the hot BCD
core only if ever needed, and even then the tax is one CALSLT at the
*entry* boundary, not per callback.

Two caveats replace it:

1. **The page-0 low region `$2812–$3FFF` is invisible during a sub-ROM
   call.** Shared cores the sub-ROM needs (float-arith, if the math pack
   calls back into it) must sit in page 1 — an include-order shuffle
   (move ~2 KB of cold page-1 code down, hot shared code up), free in
   bytes, one full gate sweep.
2. **Interrupts stay disabled while the sub-ROM is mapped** (the `$0038`
   vector is switched out with the BIOS — precedented MSX2 behaviour, known
   JIFFY-tick loss on long calls). Long tenants (LIST, later PLAY) need the
   DI-span budgeted in the arc spec; BREAKX-style direct PPI polling still
   works under DI.

Design details for the arc spec (S1): `init_ext_roms` gains a
`CD`-at-page-0 slot scan recording the sub-ROM slot (published MSX2
convention: EXBRSA `$FAF8`); dispatch = direct CALSLT with the MSX2
EXTROM register contract (IX = entry), so that actually implementing the
stubbed `$015C SUBROM`/`$015F EXTROM` BIOS vectors later is a drop-in —
and note those two are exactly the tape component's charter shape
("stubbed page-0 BIOS vectors C-BIOS leaves fake", cf. the `$015F`
fake-EXTROM `ret` in C-BIOS MSX1).

### 8c. Priced consequence — the RAM move 3-0 → 3-3

The RAM slot id changes `$83`→`$8F` everywhere it is derived
(`set_ramad`, `page0_ram_in/out` are host-adaptive by design — verify, not
assume). Machine configs regenerate (`install-openmsx-machine.py`
`expand_slot3`, the repack machine); the full disk gate suite re-runs, and
**`bdos-cbios-selfcheck` may need re-baselining** if any captured anchor
embeds the RAM slot id (the CF-3300 oracle machine keeps its real layout,
so a C-BIOS-side slot-id change can legitimately break byte-identity of
slot-derived anchor bytes). This is the one place the layout choice costs
verification work; budget it into the arc's S2.

### 8d. Placement discipline (user caution, 2026-07-11) — the four ROM regions are not interchangeable

With the sub-ROM in the map, WHERE a routine lives determines WHO can call
it. A CALSLT switches only the called page, so each executing context has
its own visibility set:

| Executing from | slot-0 pg0 (BIOS + low region `$2812–$3FFF` + tape + ISR) | slot-0 pg1 (main BASIC) | RAM pg2/3 | Ints |
|---|---|---|---|---|
| slot 0 (normal) | ✓ | ✓ | ✓ | ✓ |
| 3-0 pg0 (sub-ROM) | ✗ (switched out, incl. `$0038` ISR) | ✓ | ✓ | **DI** |
| 3-0 pg1 (if used) | ✓ (BIOS + ISR reachable) | ✗ | ✓ | may EI |
| 3-1 pg1 (disk ROM) | ✓ | ✗ (the measured 163-site wall) | ✓ | existing |

Note the symmetry: 3-0 pg0 sees main BASIC but not the BIOS; 3-0 pg1 sees
the BIOS but not main BASIC. Rules the arc spec must inherit:

- **Slot-0 page 1 is the premium region** — the only ROM visible to
  sub-ROM pg0 code. Shared services (float-arith core, `pchar`, FAC/eval
  helpers) must live there; evictions should preferentially move **leaf**
  code out of page 1 (to the low region or the sub-ROM) to keep page-1
  bytes for services, not the naive "cold code moves out".
- **Slot-0 page-0 low region is leaf-only**: nothing a sub-ROM tenant will
  ever call may sit in `$2812–$3FFF`, the gap fills, or the tape block.
  Existing tenants (kwtable, str-engine, input, float, float-arith) need a
  call-graph audit against each named sub-ROM tenant; float-arith is
  already flagged as a page-1 mover (§8b).
- **3-0 pg0 tenants**: may call main BASIC pg1 + RAM; must not need the
  BIOS mid-execution (or pay an explicit re-map trampoline); run under DI.
  RSTs there dispatch into the sub-ROM's own `$00xx` (cheap local
  dispatch; mind the `CD` header at `$0000`).
- **3-0 pg1 tenants** (optional second 16 KB, F700-style): BIOS-heavy
  bodies that don't need main BASIC (future graphics/VDP primitives);
  interrupts can stay enabled. In-slot pg0↔pg1 calls need explicit paging
  — treat the pages as separate islands.
- Every future slice's spec states, per new routine, its region and the
  contexts that may call it — placement is now part of the design, not an
  assembler accident.

### 8e. Remaining §7 questions unaffected

Q2 (ambition), Q3 (math-functions placement divergence — now "built-in
sub-ROM" rather than "extension cart", a strictly more faithful framing),
Q4 (Tier-B rejection), Q5 (shelve the gap-fill machinery), Q6 (ratify D5)
still stand as asked.
