<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Decision — Arrays slice-4 ROM-space strategy

Status: **SIGNED OFF 2026-07-16** — space plan ratified; the four §6 questions
answered by the user (folded into §6): **(a)** split slice 4 → **4a** = string heap
+ STRMAX→255 + STRCAT_R absorption, **4b** = scalar relocation; **(b)** heap policy
= **GC-compaction (MSX-faithful)** — sub-ROM has the room, take the better approach;
**(c)** STRMAX→255 scratch RAM budget = **deferred to the 4a spec**; **(d)** shape-C
reframe **confirmed** (net-neutral-to-positive main ROM, no speculative eviction).
Next step: the **slice-4a implementation contract**. The space-reclamation plan that
must precede that contract. No functional design here (heap
algorithm, descriptor format, GC policy belong in the slice-4 spec); this doc
answers only **"both main-ROM regions are full — what gets offloaded to the
sub-ROM to make room for slice 4, and does slice 4 net cost or free main-ROM
space?"** Per the spec-before-implementation rule, nothing here is a green light
until signed off.

Builds on [`decision-phase3-space-strategy.md`](decision-phase3-space-strategy.md)
(the ext-/sub-ROM strategy of record) and
[`subrom-tenant-playbook.md`](subrom-tenant-playbook.md) (the tenant recipe).
Every number is **measured** on the current tree (commit `8b4f2ee`,
`build/basic-reloc.sym` + `build/sub.rom`, 2026-07-16).

## 1. The question

Slice 4 (scalar/string relocation into the contiguous `VARTAB→ARYTAB→free` model +
STRMAX 64→255 + a real string heap; it also absorbs the deferred STRCAT_R
nested-concat fix) is the last and largest slice of the arrays/DIM arc. The blocker
recorded post-slice-3: **both main-ROM regions are full** — 0 B low, 8 B page-1 —
and even the +6 B STRCAT_R fix cannot land. So before designing slice 4 we must
settle where its code lives.

The old Phase-3 space doc (§3b) sized "heap + descriptors + STRMAX→255 (ROM side)"
at **1–1.5 KB** and tagged it **in-window** ("every string op"), and "arrays + DIM"
at 0.8–1.2 KB, also in-window. **The arrays arc (slices 1–3) has since disproved
that in-window tag** — see §3.

## 2. Measured geometry (2026-07-16)

| Region | Free | Source |
|---|---|---|
| Main **low** (slot-0 pg0, `$2812–$3FFF`) | **0 B** (`__MEAS_LOW_END = $4000`) | `basic-reloc.sym` |
| Main **page-1** (slot-0 pg1, `$4000–$7FFF`) | **8 B** (`__MEAS_PAGE1_END = $7FF8`) | `basic-reloc.sym` |
| Sub-ROM **page-0** (slot 3-2, `$0000–$3FFF`) | **~12.1 KB** (12 407 B tail) | `sub.rom` zero-run |
| Sub-ROM **page-1** (slot 3-2, `$4000–$7FFF`) | **~10.4 KB** (10 676 B tail) | `sub.rom` zero-run |

The landing zone is wide open; the main ROM is the entire constraint. This is the
exact situation the tenant playbook exists for.

### 2a. The string store slice 4 reworks (RAM + the code that manages it)

- **Fixed pools, high RAM (RAM-side, no ROM cost):** scalars `VARTAB $E1C0`;
  strings `STRTAB $E240` — 8 slots × 67 B = 536 B store, `STRSCR $E458` 65-B
  scratch, `STRMAX = 64`. Slice 4 dissolves both into the contiguous
  `$8001..HIMEM` chain and widens `STRMAX→255`.
- **The fixed-pool management code slice 4 REPLACES (ROM-side, low region):**
  `str_alloc_temp`…`str_temp_slice` = **`$2812–$28D8` ≈ 200 B** — the concat spine
  (`str_concat_tail`/`sct_loop`), temp-descriptor copy/append, and the temp-slice
  ring. A real heap subsumes all of it. **The deferred STRCAT_R bug lives here**
  (`sct_loop` re-reads the global accumulator, [spec](spec-basic-string-concat-nesting-fix.md)).
- **String value codec (ROM-side, page-1):** `str_get_key`/`str_set_key`
  (`$4767`/`$4774`) — the clamped copy into a slot. Slice 4 repoints these at heap
  descriptors.

## 3. The reframe — slice 4 is shape-C, not in-window (arrays proved it)

The old doc's "in-window" tag assumed the heap/relocation logic is interpreter-woven
and must sit in the contiguous main image. **Slices 1–3 falsified that for the
sibling feature.** Arrays is every bit as "woven" (the var store, called from
eval/LET), yet it shipped as playbook **shape C** ([`subrom-tenant-playbook.md`](subrom-tenant-playbook.md) §3C):

- **Main glue (page-1, small):** parse, `eval` subscripts, coerce `FAC`↔element.
- **Pure-RAM leaf resolver (the bulk, sub-ROM pg0 tenant):** descriptor walk,
  column-major offset, auto-dim alloc, bound/neg/ndim checks — **pointer/memory work
  over RAM only, calls neither main page** → drops straight onto the `subrom_call`
  ABI (`ary_engine_call $3E17`, `SUBROM_IDX_ARY`, `ARY_*` param block `$E028`).

**Slice 4 is the same shape, more so.** Its new work — heap alloc, GC compaction
(walk descriptors, mark live, compact, fix back-pointers), var-table growth/shift,
column of offset math — is **entirely pure-RAM pointer manipulation**. It is the
textbook pure-RAM leaf. The eval-called glue (request-alloc, coerce `FAC`↔descriptor)
stays main-side and is *thinner than today's fixed-pool codec* because the mechanism
leaves the main ROM.

Consequence: the planning figure is **not** "1–1.5 KB in-window" (impossible at 0 B
free). It is "≈1–1.5 KB into the sub-ROM (12 KB free) + a small, possibly *negative*,
net main-ROM delta."

## 4. The cut — what lands where

| Piece | Home | Notes |
|---|---|---|
| String heap allocator + GC/compaction | **sub-ROM pg0 tenant** (new leaf; new `SUBROM_IDX_*`) | pure-RAM; the bulk of slice 4 |
| Scalar/string table relocation + growth/shift | **sub-ROM pg0 tenant** (same or sibling leaf) | pure-RAM pointer walk |
| Offset/keyed-slot math for the contiguous model | **sub-ROM pg0 tenant** | pure-RAM |
| Alloc-request glue, `FAC`↔descriptor coerce | **main, page-1** | thin; eval-adjacent |
| `str_get_key`/`str_set_key` repointed at heap | **main, page-1** (in place) | shrinks vs fixed-pool codec |
| STRMAX→255 constant + clamp widening | **main** (constant) + RAM | ROM cost ≈ nil; see §6 Q-c |

Every sub-ROM piece is a §3C pure-RAM leaf → reuses the arrays ABI wholesale (append
an entry, marshal a `SUB_*` param block, `subrom_call`, read result from RAM), and
passes `check_tenant_closure.py` by construction (touches no main page).

## 5. Reclamation — the direct answer to "what gets offloaded"

Two independent supplies, cheapest first. **We expect only the first is needed.**

1. **Slice 4 reclaims its own room (net-positive main ROM).** The ~200 B of
   low-region fixed-pool machinery in §2a (`str_alloc_temp`…`str_temp_slice`) is
   *replaced*, not kept — a heap subsumes the temp ring and concat spine. That
   reclamation:
   - pays for the (smaller) main-side glue,
   - **absorbs the +6 B STRCAT_R fix that is blocked today** — the re-entrancy root
     cause (a global `STRCAT_R` accumulator in fixed scratch) *disappears* when
     concat results go to heap descriptors, so the fix is likely free, not +6 B
     (confirm during the slice-4 spec; chip stays open until then),
   - and plausibly leaves the low region with headroom it hasn't had since slice 3.

2. **If glue still overflows page-1's 8 B** (the premium region — the only main ROM
   visible to sub-ROM pg0 tenants, §8d of the phase-3 doc): evict a **cold page-1
   leaf** to the sub-ROM per the playbook eviction ladder. Because a sub-ROM pg0
   tenant keeps main page-1 visible, cold page-1 code can move to the sub-ROM and
   keep calling `pchar`/`eval`. Candidates already inventoried (phase-3 doc §4d wave
   table): `list.asm`/detok, `printusing.asm`, `screen.asm` — none touched by slice 4,
   each ≥250 B. **Do NOT** evict low-region code to make room: the low region is
   invisible to sub-ROM tenants and is where slice-4's own glue may want to sit.

**Net main-ROM delta prediction: ≈ 0 to positive.** Slice 4, built as shape C, is
the first arc slice that should *give back* main-ROM bytes rather than consume them —
inverting the "0 free bytes crisis" framing. The crisis is real only if slice 4 is
built monolithically in-window, which is precisely the mistake the arrays 80-minute
overrun already taught us not to repeat (playbook §7 meta-lesson).

## 6. Open questions — the user's call

- **Q-a — split slice 4?** The arc doc bundles "scalars + strings" into one slice.
  The arrays lesson (smaller slices; every slice hid ≥1 bug) argues for splitting:
  **4a = string heap + STRMAX→255 + STRCAT_R absorption** (the hard, high-value
  half), **4b = numeric scalar relocation into the chain** (mechanically simpler,
  lower payoff). Recommend the split. Your call.
- **Q-b — heap policy.** MSX-faithful is **GC-on-OOM compaction** (the classic
  string-GC pause), the largest sub-ROM cost. Alternative: bump-allocator +
  free-list (simpler, no pause, less faithful, fragments). This is a faithfulness↔
  size↔behaviour call that belongs to you before the spec sizes the tenant.
- **Q-c — STRMAX→255 scratch.** `STRSCR` (literal/scratch buffer) widens 64→255 =
  **+191 B of high-RAM sysvars**; the 800-B `$E240..$E560` window is already tight
  (spec §5a "no spare byte"). Does the scratch move onto the heap/stack too, or do
  we buy the RAM elsewhere? Real design question, but it's a **RAM**-budget question,
  not a ROM one — flag it for the spec, doesn't change this space plan.
- **Q-d — confirm the reframe.** Sign off that slice 4 is planned as **shape C**
  (bulk → sub-ROM pure-RAM leaf, thin main glue), targeting a **net-neutral-to-
  positive** main-ROM footprint — i.e. we do **not** pre-build any reclamation
  machinery (§5.2 eviction) speculatively; we build the shape-C split and only reach
  for an eviction if the measured glue overflows page-1's 8 B.

## 7. Recommendation

Adopt the shape-C plan (§4) with **self-reclamation as the primary supply** (§5.1)
and a **cold-page-1 eviction held in reserve** (§5.2). Concretely, the next session
after this sign-off writes the **slice-4 implementation contract**, which:

1. classifies each new routine's region + callers per phase-3 §8d placement
   discipline (part of the design, not an assembler accident);
2. defines the sub-ROM heap/relocation tenant(s), their `SUB_*` param block, and
   `SUBROM_IDX_*` entries (arrays ABI as the template);
3. specifies the STRMAX→255 clamp/scratch changes and the heap policy chosen in Q-b;
4. folds in the STRCAT_R fix as a heap consequence (retiring
   [`spec-basic-string-concat-nesting-fix.md`](spec-basic-string-concat-nesting-fix.md)),
   or, if the root cause does not dissolve, budgets its +6 B against the §5.1
   reclamation;
5. carries the standing gates (closure + resident-ABI + leaf-audit + lean
   byte-identity + `__MEAS_*` re-measure) and slice 4's own differential gate +
   Fable adversarial review.

**Bottom line for the space question:** nothing needs to be pre-offloaded. Slice 4
built as shape C reclaims ~200 B of the low-region fixed-pool code it obsoletes,
which is expected to cover its own thin glue *and* the blocked STRCAT_R fix — turning
the "both regions full" wall into a wash or a small win. The sub-ROM's 12 KB absorbs
the heap/relocation bulk. A cold-page-1 eviction is the only fallback and is unlikely
to be needed.
