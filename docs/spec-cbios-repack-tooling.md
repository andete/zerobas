# Spec — C-BIOS repack tooling (reclaim page-0 space → grow the BASIC window)

**Status: SIGNED OFF (2026-07-09).** Decisions D1–D3 resolved (§6). Next: S2 (WS-1 C-BIOS repack spike). Implementation spec for the arc
the user selected after zerobas reached its concluded state. Grounded in the sizing
analysis [`cbios-repack-space-analysis.md`](cbios-repack-space-analysis.md); this
doc is the *how* + *decisions*, that doc is the *why* + *budget*. No code until this
is signed off (per the project's spec-before-implementation discipline).

## 1. Goal

Break the standing wall: **the BASIC ROM page is byte-exactly full** (code ends at
`$8000`, page 1 = `$4000–$7FFF`, 16 KB). Reclaim ~7 KB of page-0 space *contiguous
with page 1* by repacking C-BIOS, so BASIC can become one ~23 KB image spanning
`$23BF–$7FFF` — the real-MSX "BIOS-low + BASIC-high in one 32 KB slot-0 ROM" layout.

This arc delivers **the space and the tooling to occupy it**, not a new BASIC
feature. It *unblocks* Phase-3 BASIC work (floats, strings, graphics…) that is
otherwise walled. Success = a rebuilt, validated IPS on a pristine C-BIOS where
BASIC owns `$23BF–$7FFF` and every standing gate stays green.

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

### WS-1 — C-BIOS source repack (produces the denser page-0 BIOS)
Edit the **C-BIOS source** at the pinned checkout (`~/projects/cbios`,
`v0.29-3-gb5ad9cb`, rebuilds `cbios_main_msx1_eu.rom` sha1 `baf2e9c6…` byte-exact).
Confirmed source sites:
- `src/statements.asm`: `multiple:` (@`$3193`, a real helper — **relocate**),
  `rombas`/`rombas_text` + the `ds $392e - $` pin + the `rombas_niy` runloop table
  (all **dead** — zerobas *is* the BASIC, so C-BIOS's "can't run a ROM BASIC" path
  never executes → **delete**).
- `src/main.asm` / `src/main_msx1_eu.asm`: the `ds $XXXX - $` phantom pins that force
  the above-font content to fixed addresses — **remove the ones above the font** so
  the assembler repacks that content into the pre-font gap.
- Keep every `$0000–$01B7` jump-table pin and the `B_Font`/`CGTABL` pin **untouched**.

Edits are captured as **our own patch** against the pinned C-BIOS tag (see Decision D1),
never as vendored C-BIOS bytes. The assembler does all address fixups on rebuild.

### WS-2 — BASIC org relocation (16 KB → ~23 KB)
`basic.rom` currently assembles to `org $4000`, exactly 16 KB. To span the freed
region it must assemble from the new low boundary (`$23BF`) up to `$7FFF` (~23 KB).
- Audit `basic/*.asm` + `basic/*.inc` for **hardcoded absolute addresses** that assume
  the `$4000` base (the real risk — a label-clean reassemble is free, a hardcoded
  `$4xxx` is a silent corruption). This audit is the technical crux of the arc.
- The page-0 portion (`$23BF–$3FFF`) and page-1 portion (`$4000–$7FFF`) are one
  contiguous slot-0 image; no cross-page paging is needed (both are slot-0 ROM).
- **The `$8000` code-end wall is removed** as a side effect — that's the payoff.

### WS-3 — Tooling (combine + diff across the new boundary)
- [`overlay_page1.py`](../tools/overlay_page1.py) hardcodes `PAGE1=0x4000`,
  `len(basic)==0x4000`, and a page-1-only splice. Generalize to a **parameterized
  boundary + variable BASIC size**, splicing the ~23 KB image across `$23BF–$7FFF`
  onto the *repacked* C-BIOS base (not stock).
- [`build_patches.py`](../tools/build_patches.py) gains a repack path: build the
  repacked C-BIOS (WS-1), overlay the relocated BASIC (WS-2), diff vs **pristine
  stock C-BIOS** → IPS/BPS. The shipped diff spans both the repack region and BASIC.
- Per-variant: only `main_msx1_eu` is targeted first (analysis: re-measure gaps per
  variant before adding more). The tape build already does per-variant work — reuse
  that machinery, don't invent new.

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

1. **S1 (this session): spec + sign-off.** ← you are here.
2. **S2 — WS-1 spike:** make the C-BIOS source edits, rebuild `main_msx1_eu`, confirm
   it still boots C-BIOS standalone and page-0 content now ends ≤`$23BE`. No BASIC
   changes yet. Gate: C-BIOS self-boot + jump-table/CGTABL re-validation.
3. **S3 — WS-2 audit + relocation:** hardcoded-address audit, reassemble BASIC from
   `$23BF`. Gate: BASIC boots to `Ok`, unit-tests green.
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

**D2 — relocation boundary → `$23BF` (max reclaim).** Full ~23 KB window; analysis
shows C-BIOS content ends here cleanly, so no safety margin is left on the table — the
whole point is to break the wall.

**D3 — variant scope → EU ONLY** (`main_msx1_eu`). Prove the mechanism on one target;
per-variant (br/jp) gap re-measurement is a documented later add, same pattern as the
tape build.

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
