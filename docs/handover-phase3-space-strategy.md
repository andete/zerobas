# Handover — Phase-3 ROM-space strategy deep-think

Status: **HANDOVER BRIEF, 2026-07-11** — input for a dedicated deep-think
session. Deliverable = a decision document (options, measured costs, risks,
verification plans, a recommendation) for user sign-off. **No implementation
in that session** (spec-before-implementation rule; the brief is not a green
light). Deliberate, Fable-level analysis — measure real numbers, don't
resume grinding.

## 1. The problem, framed properly

After float F2 (commit `dee70a9`), the repack BASIC window is **FULL**:
page-0 content reaches `$3FFD` (2 B slack to the `$4000` header), page-1
content reaches `$7FE2` (29 B tail). F3 (typed variables) is estimated at
~0.6 KB and has no home. But F3 is only the tip: the Phase-3 roadmap still
carries (TODO.md "Floating point" out-of-scope list + string-engine
deferrals + arc plans):

- `^` + the math functions (`SQR SIN COS TAN ATN EXP LOG RND FIX INT CINT
  CSNG CDBL`) — the largest single block, likely 1.5–3 KB of BCD code;
- `DEFINT/DEFSNG/DEFDBL/DEFSTR`;
- floats in `VAL`/`STR$`/`INPUT`/`READ`/`DATA`, float `FOR/NEXT` (D-D),
  float `PRINT USING` specs, `MKS$/MKD$/CVS/CVD`;
- the **heap arc** (string-engine deferrals: real heap + descriptors,
  arrays/`DIM`, STRMAX→255) — mostly RAM-side but with ROM code;
- graphics/sound statements further out.

So the question is NOT "find 600 bytes for F3" — it is **"what is the
durable space strategy for the rest of Phase 3?"** A lever that buys only
F3 postpones this same session by one slice. Size the remaining roadmap
(even coarsely, per block) and pick a lever (or staged sequence of levers)
that covers it.

## 2. Current geometry (measured 2026-07-11, post-F2)

Merged main ROM (`build/zerobas-main-eu.rom`, 32 KB, slot 0):

| Region | Contents | Free |
|---|---|---|
| `$0000–$015F` | C-BIOS jump table + entry code | — |
| `$0160–$01FF` | fill | 160 B (universal? re-verify) |
| `$0200–$09ED` | live C-BIOS (+ MSX2-variant content to `$09ED`) | — |
| `$09EE–$0BBE` | **zerobas-tape body** (moved here by the D5 revision, 781348f) | — |
| `$0BBF–$0D00` | gap-1 remainder | **~322 B** |
| `$0D01–$1AC9` | live C-BIOS | — |
| `$1ACA–$1BC6` | gap-2 | **253 B** |
| `$1BBF–$23BE` | font (PINNED — CGTABL compat) | — |
| `$23BF–$2811` | above-font keep-content (slot routines, strings, scancodes, vdp_bios) | — |
| `$2812–$3FFF` | relocated BASIC low region (one contiguous assembly) | **2 B** |
| `$4000–$7FFF` | BASIC page 1 (`AB` header pinned at `$4000`) | **29 B** |

Free-span facts: gap free-ness was measured across ALL 12 C-BIOS main
variants (MSX1/2/2+ × generic/EU/JP/BR) — the intersection matters for
anything the STANDALONE tape IPS touches; the merged ROM only needs the
EU repack. `$09D9–$09ED` is free on MSX1 only (MSX2 content ends `$09ED`).

The lean 16 KB `basic.rom` (stock C-BIOS + cart) is byte-full and must stay
byte-identical — it is not part of this problem.

## 3. Options on the table (D-G addendum, spec-basic-float-core.md §6 + the
user's suggestion)

**(a) Multi-region BASIC image.** Restructure `main-reloc.asm` into an
org-`$0000` 32 KB image (or equivalent) so BASIC code can also be placed
into gap-1's remainder and gap-2 (~575 B today). Build machinery:
`build_mainrom.py` overlays + `check_reloc.py` + lean-identity guards all
need rework. **Companion move (user suggestion, 2026-07-11): fold the tape
code into the main assembly** — once multi-region exists, the merged build
should simply compile `tape/tape.asm` in (dropping the tape-IPS layout
coupling for the MERGED artifact); the standalone tape IPS keeps its own
org build (it remains a first-class deliverable per the component-split
decision — do NOT drop it without asking). Note: folding tape in frees
its 465 B at `$09EE` only in the sense that tape code then competes inside
the same total budget — the real win of (a) is unlocking ALL gap space for
label-based placement, ~575 B + the 160 B `$0160` sliver if universal.
Ceiling: ~0.7 KB. Covers F3, NOT the roadmap.

**(b) Next C-BIOS repack tranche — Tier B (content cuts).** The Tier-A
"repack without cutting" ceiling is already reached (`$2812` boundary; the
WS-1 spike REFUTED the relocate-below-font plan — pre-font gaps can't hold
the 1107 B of above-font keep-content; see spec-cbios-repack-tooling.md
§8). Tier B = cutting genuine C-BIOS content a game-loader doesn't need
(debug helpers, boot-only strings, unused BIOS routines) and/or golfing —
the space-analysis doc estimates **~2–3 KB extra**, each cut needing
verify-on-execute + the standing gates. This breaks the "every reachable
byte identical to stock" self-boot-by-construction firewall property —
the verification burden per byte is much higher than Tier A's. Realistic
coverage: F3 + the math-function block, maybe.

**(c) Heap-arc-first ordering** (D-G): mostly re-sequencing, not space —
only if its RAM work genuinely shrinks F3's ROM need (doubtful; check).

**(d) Extension-slot ROM** (basic-rom-space-and-growth memory / TODO
"Beyond"): move Phase-3 growth into a second cartridge/slot ROM (the
zerobas-disk model — disk.rom lives in slot 3-1 with its own 16 KB). A
"zerobas-basic-ext" ROM could hold the math-function block etc., reached
via inter-slot calls (CALSLT overhead per call — measure whether that is
acceptable for expression-evaluator-hot paths, or whether a page-swap
scheme is needed). This is the only option with a ROADMAP-scale ceiling
(16 KB+). Big architectural questions: slot layout on real hardware,
C-BIOS slot expansion behaviour, how the lean-vs-repack split maps onto
it, gate/machinery cost.

**(e) Dedup/golf passes on our own code.** Known candidates: float.asm F1
tokeniser/formatter vs float-arith.asm share unpack/digit machinery;
kwtable compression; the F2 implement agent already did ~10 trim rounds on
float-arith. Ceiling maybe 200–400 B, one-shot, non-durable — at best a
complement, never the strategy.

Combinations are likely the answer (e.g. (a) now for F3 + (d) as the
Phase-3 endgame; or (b) once, then (d)).

## 4. Constraints the decision must honour

- **Clean-room firewall**: reference ROMs are oracles only; C-BIOS is BSD
  source we may read/patch. Tier-B cuts lose the "identical reachable
  bytes" boot-by-construction property — price that in.
- **Deliverable structure** (component-split decision, user-affirmed): the
  standalone tape IPS (stock C-BIOS, MSX1/2/2+ universal) and the lean
  16 KB cart remain shipped artifacts. The merged main ROM is the repack
  target. Any option must state its effect on each artifact.
- **Gates**: every option's verification plan must name which standing
  gates re-run (float-acceptance 3 halves, string 6, input, diskbasic-
  repack 34, bdos suite, tape battery, repack-boot, crunch, unit-test,
  lean byte-identity) and what NEW machinery it needs.
- **D-G interaction**: F3's variable-store re-layout vs the heap arc —
  the ordering decision rides on the same sign-off.
- Judgment calls get logged and flagged; anything irreversible or
  product-shape-changing (e.g. dropping a deliverable) is the user's call.

## 5. Required reading (in order)

1. This file; then `docs/spec-basic-float-core.md` §5, §6 (D-G + addendum),
   §10 (what F2 landed).
2. `docs/cbios-repack-space-analysis.md` (Approach 0/1, Tier A/B/C, the
   WS-1 correction) + `docs/spec-cbios-repack-tooling.md` §6 (D1–D5 incl.
   the D5 revision note) + §8 (WS-1 outcome).
3. `docs/cbios-repack-provenance.md` (what the merged ROM is, firewall).
4. `tools/build_mainrom.py`, `tools/build_patches.py`,
   `tools/build_repacked_cbios.py`, `basic/main.asm` (reloc layout),
   `Makefile` (targets: repack-main/-boot/-machine, patches).
5. TODO.md Phase-3 sections (size the remaining roadmap from these).
6. Memory topics: [[basic-rom-space-and-growth]], [[cbios-repack-arc]],
   [[component-split-rationale]], [[float-pack-arc]].

## 6. Deliverable of the deep-think session

`docs/decision-phase3-space-strategy.md`: the sized roadmap remainder, each
option with measured numbers (bytes gained, build/verification cost, firewall
impact, artifact impact), staged combinations, a clear recommendation +
what it unblocks (F3 now? math pack later?), and the open questions that
need the user — presented for sign-off BEFORE any implementation session.
