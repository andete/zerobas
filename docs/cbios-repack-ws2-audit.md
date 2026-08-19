# WS-2 hardcoded-address audit (S3) — the relocation crux

**Status: audit COMPLETE 2026-07-10. Result: essentially clean.** This is the
arc's designated top risk ([spec §7](spec-cbios-repack-tooling.md)) — a `$4xxx`
absolute literal that assumed the old `$4000` base and would corrupt silently when
BASIC relocates to `$2812`. The audit finds **no such literal anywhere in the
zerobas-BASIC source.**

## Method

Swept `basic/*.asm` + `basic/sysvars.inc` for every numeric literal in the
`$2xxx–$7xxx` code-page range, plus high-byte/page-detection idioms (`cp $40`,
`and $c0`, ROM-range bounds), data-table pointers (`dw <label>`), and `$8000`
(TXTTAB / page-2) assumptions. Classified each hit.

## Findings — every `$2xxx–$7xxx` literal accounted for

| Category | Sites | Verdict |
|---|---|---|
| **`org $4000`** (`main.asm:23`) | 1 | **The only self-referential absolute address.** This is what changes. |
| External-cartridge `"AB"` header scan `$4000–$4003` (`initext.asm:106–102`) | 4 | **Stays `$4000`.** Scans *other* slots (e.g. zerobas-disk) whose headers are in their own page 1. Not a self-reference. |
| Cross-slot DSKIO ABI offset `DSKIO_ENTRY = $4010` (`sysvars.inc:2461`, used `fat.asm:66`) | 1 | **Stays `$4010`.** Fixed disk-cartridge interface offset (ROM base + `$10`), not zerobas's own address. |
| Cassette timing constants `CAS_LOW_1200 = $5C53`, `CAS_LOW_2400 = $2D25` (`sysvars.inc:143–90`, `save.asm:491`) | 3 | **Not addresses** — FSK low-signal-length words. |
| Comments citing `$4010`/`$4000`/`$8000` | ~18 | Prose, no code effect. |
| Char/ASCII arithmetic (`sub $20`, `cp $7F`, `or $80`) | 4 | **Not address math** — uppercasing, DEL key, expanded-slot flag. |
| `$8000` | 2 | Only the `ds $8000 - $` page pad + a comment. |

**Control-flow dispatch is 100 % label-based.** The statement executor
(`interp.asm:156+`) is a linear `cp TOKEN / jp z,<label>` chain — no `dw`-label
jump tables. The single `dw <label>` in the whole source is `dw init` (the
cartridge header's INIT pointer), which relocates automatically. Every internal
CALL/JP targets a label, so pasmo re-fixes all of them for free when `org` moves.

**Conclusion:** a label-clean reassemble at a new base is safe. The crux risk is
absent.

## The one real structural constraint the audit surfaced: the header must stay at `$4000`

C-BIOS boots zerobas by finding its `"AB"` cartridge header at **`$4000`** during
the slot cartridge scan (`main.asm:15`, `initext.asm:15`). The cartridge scan
checks pages 1 and 2 (`$4000`, `$8000`) of each slot — **not page 0.** So a naive
`org $2812` would move the header into page 0, where the scan never looks, and the
machine would not boot into BASIC.

**Therefore the relocation is not a simple `org` move.** The layout must keep the
`"AB"` header pinned at `$4000` and append the reclaimed `$2812–$3FFF` as a *low
region below the header*, reachable from page-1 code by ordinary in-slot CALL/JP
(it is all one slot-0 ROM). No C-BIOS boot-path change is needed — the header
mechanism is untouched.

## Reclaimed low-region map (post-repack, page-0 ceiling `$2811`)

```
$2812 ┌─────────────────────────────┐
      │  reclaimed low region       │  6126 B total ($2812–$3FFF)
      │  ...                        │
      │  tape page-0 completions    │  $3A72–$3C42 (465 B) — the D5 question
      │  ...                        │
$3FFF └─────────────────────────────┘
$4000 ┌─────────────────────────────┐
      │  "AB" header (pinned)       │  found by C-BIOS boot scan
      │  existing BASIC (unchanged) │  16384 B ($4000–$7FFF)
$7FFF └─────────────────────────────┘
```

- Below tape: `$2812–$3A71` = **4704 B** contiguous.
- Above tape: `$3C43–$3FFF` = **957 B** (contiguous with the `$4000` header).
- BASIC window total `$2812–$7FFF` minus the 465 B tape block ≈ **21.5 KB** (matches D2).
- The tape block org (`FREE_ORG = $3A72`) sits in free space on **both** the pristine
  C-BIOS (tape-only target) and the repacked base; note `$2812–$3192` is also free
  (gap 3) on pristine C-BIOS, so the tape block *could* relocate there too (D5-B).
</content>
