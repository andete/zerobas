# Spec — C-BIOS repack tooling (reclaim page-0 space → grow the BASIC window)

**Status: SIGNED OFF (2026-07-09); WS-1 done + boundary corrected (2026-07-10).**
Decisions D1–D3 resolved (§6); **D2 boundary corrected `$23BF`→`$2812` after the S2
spike disproved the analysis's pre-font-gap estimate (§6, §8).** Next: S3 (WS-2 BASIC
relocation to `$2812`). Implementation spec for the arc
the user selected after zerobas reached its concluded state. Grounded in the sizing
analysis [`cbios-repack-space-analysis.md`](cbios-repack-space-analysis.md); this
doc is the *how* + *decisions*, that doc is the *why* + *budget*. No code until this
is signed off (per the project's spec-before-implementation discipline).

## 1. Goal

Break the standing wall: **the BASIC ROM page is byte-exactly full** (code ends at
`$8000`, page 1 = `$4000–$7FFF`, 16 KB). Reclaim ~6 KB of page-0 space *contiguous
with page 1* by repacking C-BIOS, so BASIC can become one ~21.5 KB image spanning
`$2812–$7FFF` — the real-MSX "BIOS-low + BASIC-high in one 32 KB slot-0 ROM" layout.
That single 32 KB slot-0 image (C-BIOS + tape page-0 completions + BASIC) *is* the
MSX **main ROM**, shipped as one IPS (D4).

This arc delivers **the space and the tooling to occupy it**, not a new BASIC
feature. It *unblocks* Phase-3 BASIC work (floats, strings, graphics…) that is
otherwise walled. Success = a rebuilt, validated **main-ROM IPS** on a pristine C-BIOS
where BASIC owns `$2812–$7FFF` and every standing gate stays green.

## 2. Chosen approach — Approach 1, Tier A (repack, no golfing)

The user picked *repack*, so **Approach 0 (overwrite-and-fill) is de-scoped** — its
~5.3 KB of holes are *fragmented* page-0 islands, usable only to evict individual
routines, and it does **not** grow the contiguous `$8000`-bounded image (the actual
constraint). Recorded as a fallback in the analysis; not built here.

**Tier A** (analysis §Approach 1): keep only the **jump table** (`$0000–$01B7`) and
the **font** (`$1BBF–$23BE`) pinned; relocate the ~1.4 KB of keep-content stranded
*above* the font (slot routines, message strings, scancodes, `vdp_bios`, `multiple`)
down into the ~1.4 KB empty gap *below* the font (core BIOS ends ~`$1734`); drop the
dead `rombas`/`rombas_niy` handlers + the stubbed-BASIC runloop dispatch table; drop
their `ds` pins. Frees **`$23BF–$3FFF` = 7 233 B contiguous with page 1**. Font stays
pinned at `$1BBF`, so `CGTABL`/font compat is untouched. **Tier B/C (cut genuine BIOS
content) are explicitly out of this arc** — Tier A alone reaches ~23 KB.

## 3. The three workstreams (all must land together)

The prize requires three coordinated changes; none is useful alone.

### WS-1 — C-BIOS source repack (produces the denser page-0 BIOS) — ✅ DONE
Edit the **C-BIOS source** at the pinned checkout (`~/projects/cbios`,
`v0.29-3-gb5ad9cb`, rebuilds `cbios_main_msx1_eu.rom` sha1 `baf2e9c6…` byte-exact).
**Outcome (S2, §8): a one-line edit.** The entire `src/statements.asm` — `multiple`,
`rombas`, `rombas_niy`, and the runloop/statement dispatch tables — is C-BIOS's
placeholder for a ROM BASIC it never ships, with **zero references** from anywhere else.
So the planned above-font relocation was **unnecessary**: comment out `include
"statements.asm"` in `src/main.asm`; the jump table (`$0000–$01B7`) and `B_Font`/`CGTABL`
stay untouched. Page-0 ceiling drops to `$2811`. Captured as the D1 tracked patch
[`../cbios-repack/eu-drop-statements.patch`](../cbios-repack/eu-drop-statements.patch)
(no C-BIOS bytes in-repo); reproducible pinned-tag + patch → sha1 `edb08440…`.

### WS-2 — BASIC org relocation (16 KB → ~21.5 KB)
`basic.rom` currently assembles to `org $4000`, exactly 16 KB. To span the freed
region it must assemble from the new low boundary (`$2812`) up to `$7FFF` (~21.5 KB).
- Audit `basic/*.asm` + `basic/*.inc` for **hardcoded absolute addresses** that assume
  the `$4000` base (the real risk — a label-clean reassemble is free, a hardcoded
  `$4xxx` is a silent corruption). This audit is the technical crux of the arc.
- The page-0 portion (`$2812–$3FFF`) and page-1 portion (`$4000–$7FFF`) are one
  contiguous slot-0 image; no cross-page paging is needed (both are slot-0 ROM).
- **Tape-block coordination (D5).** The zerobas-tape page-0 completions occupy
  `$3A72–$3C42` — *inside* the freed region. BASIC's layout must dovetail with it (fill
  around it, or relocate tape to the region edge). Layout settled at the top of WS-2
  with the real assembler constraints in hand (D5).
- **The `$8000` code-end wall is removed** as a side effect — that's the payoff.

### WS-3 — Tooling (build ONE main-ROM image, diff vs stock)
Per **D4**, tape + BASIC ship as a single **main ROM** (BIOS-low + BASIC-high, 32 KB
slot 0 — the MSX-spec model), not two IPS patches. WS-3 builds that combined image and
emits one patch:
- Build stages: (1) apply the WS-1 repack patch to the pinned C-BIOS checkout → denser
  base; (2) assemble the relocated BASIC (`$2812–$7FFF`, WS-2) + the tape page-0
  completions into the combined 32 KB image; (3) diff vs **pristine stock C-BIOS** →
  **one** `zerobas-msx1.ips`/`.bps`. The shipped diff spans the repack region, tape, and
  BASIC — still an overlay on the stock the user brings.
- [`overlay_page1.py`](../tools/overlay_page1.py) hardcodes `PAGE1=0x4000` /
  `len(basic)==0x4000` / a page-1-only splice → generalize to a **parameterized boundary
  + variable BASIC size** onto the *repacked* base.
- [`build_patches.py`](../tools/build_patches.py) gains the combined-main-ROM path; the
  separate `tape/zerobas-tape-msx1.ips` deliverable folds into an internal build stage
  (retain an **optional tape-only target** — D4).
- **Sources stay split (D4):** `basic/` and `tape/` remain distinct components with their
  own provenance; only the build *output* merges. `disk.rom` is unaffected (slot-3-1
  cartridge, not part of the main ROM).
- Per-variant: `main_msx1_eu` only (D3); the tape build already does per-variant work —
  reuse that machinery.

## 4. Validation gates (nothing ships red)

Reuse the standing harness — this arc must not regress it:
- `make bdos-cbios-selfcheck` (10/10) — re-captures BDOS anchors on the repacked
  C-BIOS target; asserts byte-identical behaviour.
- tape probes + `make diskbasic-acceptance` (34/34), `make bdos-acceptance` (12/12),
  `make unit-test` (38/38) — full standing-gate sweep after relocation.
- **New checks (per analysis verify-on-execute):**
  - Confirm `multiple`/`rombas`/`rombas_niy` are reached *only* via relocatable
    internal CALL/JP, with no fixed-address expectation, **before** moving/deleting.
  - Re-validate every `$00xx` jump-table entry + `CGTABL` after the repack (a peek at
    each published entry still lands on its handler; font still at `$1BBF`).
  - Boot the repacked+relocated stack in openMSX to `Ok` and round-trip a
    `.BAS`/binary loader (the charter scope) — the real end-to-end proof.

## 5. Session sequencing (one landing per session)

1. **S1: spec + sign-off.** ✅ DONE (commit b24ae7f).
2. **S2 — WS-1 spike.** ✅ DONE (2026-07-10). Repack = comment out `include
   "statements.asm"` (the whole file is dead — zero external refs); no live-content
   relocation needed. Rebuilt `main_msx1_eu` differs from stock in exactly 363 bytes
   (all `$3193–$3A70`, all zeroed); jump table / font / `CGTABL` / page-1 byte-identical.
   Captured as `cbios-repack/eu-drop-statements.patch` (reproducible: pinned tag + patch
   → sha1 `edb08440…`). Page-0 ceiling now `$2811`; **boundary corrected to `$2812`.**
3. **S3 (next) — WS-2 audit + relocation:** hardcoded-address audit, reassemble BASIC
   from `$2812`. Gate: BASIC boots to `Ok`, unit-tests green.
4. **S4 — WS-3 tooling:** parameterize overlay/build, emit the repacked IPS/BPS.
   Gate: full standing-gate sweep + end-to-end loader round-trip.
5. **S5 — close-out:** provenance write-up (patch-vs-merge firewall), docs harvest,
   memory + TODO update.

Each session commits at its gate (commit-after-TODO-point discipline). Judgment calls
that don't need a stop get logged; forks/irreversible steps hard-stop for sign-off.

## 6. Decisions — RESOLVED (signed off 2026-07-09)

**D1 — C-BIOS source-edit handling → TRACKED PATCH FILE.** Our own 0BSD patch against
the pinned C-BIOS tag (`v0.29-3-gb5ad9cb`), applied at build time to the user's
`~/projects/cbios` checkout. The zerobas repo stays **free of C-BIOS bytes**; the
patch is a description of edits to BSD source, so the firewall holds (a diff is not a
merge). *(Rejected: vendoring a fork — puts C-BIOS bytes in-repo; hand-edited branch —
not reproducible.)*

**D2 — relocation boundary → `$2812`** (corrected 2026-07-10 from `$23BF`). The S2
spike (§8) proved `$23BF` is **not cleanly achievable**: it assumed a ~1.4 KB pre-font
gap to relocate the above-font keep-content into, but the binary shows the pre-font gap
is only 253 B (core BIOS packs down to `$1AC9`, not `$1734`). The clean, surgical
boundary is `$2812` — reclaim **6126 B** (`$2812–$3FFF`), BASIC window `$2812–$7FFF` ≈
**21.5 KB** (+37 % over 16 KB). Clawing back the extra ~1.1 KB toward `$23BF` needs
fragmented deep-in-live-BIOS relocation (Tier B), which this arc excludes — user
accepted `$2812` (2026-07-10).

**D3 — variant scope → EU ONLY** (`main_msx1_eu`). Prove the mechanism on one target;
per-variant (br/jp) gap re-measurement is a documented later add, same pattern as the
tape build.

**D4 — tape + BASIC ship as ONE main-ROM deliverable** (added 2026-07-10). On the MSX
spec, BIOS + BASIC = one 32 KB slot-0 "main ROM"; the repack recreates that layout, and
it *forces the question* because the tape page-0 completions (`$3A72–$3C42`) sit inside
the region BASIC now grows into. So the two ship as **one** `zerobas-msx1.ips` (repacked
C-BIOS + tape + relocated BASIC, diffed vs pristine stock). **Merge only the build
output** — `basic/` and `tape/` stay separate source components with distinct provenance
(per the component-split rationale: tape = C-BIOS page-0 BIOS completions, not the
interpreter); keep an optional tape-only build target. *(Rejected: folding tape.asm into
the basic/ source tree — discards the component split.)*

**D5 — page-0 layout of grown-BASIC vs the tape block → decided at WS-2 start** (added
2026-07-10). Whether BASIC fills around the tape block (`$3A72–$3C42`) or tape relocates
to the region edge is settled at the top of S3/WS-2, with the real assembler constraints
in hand — not committed up front.

## 7. Risks & non-goals

- **Risk (highest): WS-2 hidden absolute addresses.** A `$4xxx` literal that assumed
  the old base corrupts silently. Mitigation: the S3 audit is a hard gate; grep +
  diff the relocated binary's cross-references before trusting it.
- **Risk: a "dead" handler isn't dead.** Mitigation: the verify-on-execute check in §4
  runs *before* deletion, not after.
- **Non-goal:** Tier B/C BIOS content-cutting, non-EU variants, Approach 0 fills, and
  any actual Phase-3 BASIC feature. This arc delivers *space + tooling* only.
- **Firewall unchanged:** ships as an IPS on a pristine C-BIOS, exactly like today's
  patches. A larger diff, still an overlay — no fork, no "own the BIOS" pivot.

## 8. S2 / WS-1 outcome (2026-07-10)

The spike both simplified WS-1 and corrected the budget:

- **WS-1 collapses to one line.** The entire `statements.asm` is C-BIOS's placeholder
  for a ROM BASIC it never ships (`multiple`, `rombas`, `rombas_niy`, the runloop +
  statement dispatch tables). Grep proved **zero references** from anywhere else in the
  source (verify-on-execute, done *before* removal), so the planned "relocate live
  content below the font" is unnecessary — just comment out the `include`. Captured as
  [`../cbios-repack/eu-drop-statements.patch`](../cbios-repack/eu-drop-statements.patch).
- **Proven surgical + reproducible.** Rebuilt `main_msx1_eu` vs pristine stock: exactly
  **363 differing bytes, all `$3193–$3A70`, all zeroed** (the dead code); jump table,
  font, `CGTABL`(→`$1BBF`), and the whole page-1 region byte-identical. Pinned tag +
  patch rebuilds to sha1 `edb0844053a3d428aaef95fcd9106972079bde34` deterministically.
- **Analysis error found → boundary corrected.** The sizing doc's Approach-1 narrative
  claimed core BIOS ends ~`$1734`, leaving a ~1.4 KB pre-font gap to relocate the
  above-font keep-content into. The binary refutes this: core BIOS packs down to
  `$1AC9`; the pre-font gap is only **253 B**, and gaps 1+2 together (~1061 B) can't even
  hold the 1107 B of above-font keep-content. So `$23BF` is unreachable without Tier-B
  moves; the clean boundary is `$2812` (see D2). The analysis doc's Approach-1 section
  was corrected to match.
- **Self-boot:** guaranteed by construction — every *reachable* byte is identical to
  stock; the only change is unreferenced dead code becoming `$00`. Full end-to-end boot
  is re-proven in S4 when the relocated stack runs the standing gates.
