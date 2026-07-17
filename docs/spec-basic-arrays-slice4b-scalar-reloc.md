<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — Arrays slice 4b: numeric scalar relocation into the contiguous chain

Status: **DRAFT — AWAITING SIGN-OFF (2026-07-17).** Per the
[spec-before-implementation](../../.claude/projects/-Users-joost-projects-zerobas/memory/spec-before-implementation.md)
rule, nothing here is a green light until signed off. This contract is the
*implementation contract* the slice-4 space decision
([`decision-arrays-slice4-space.md`](decision-arrays-slice4-space.md) §7) calls
for, restricted to the **4b** half (scalar relocation); the 4a half (string heap)
shipped 2026-07-17.

Builds on: [`spec-basic-arrays.md`](spec-basic-arrays.md) (arc + memory model A),
[`spec-basic-arrays-slice4a-string-heap.md`](spec-basic-arrays-slice4a-string-heap.md)
(the heap 4b coexists with), [`decision-arrays-slice4-space.md`](decision-arrays-slice4-space.md)
(shape-C space plan), and the sub-ROM tenant playbook
([`subrom-tenant-playbook.md`](subrom-tenant-playbook.md)).

Every address / routine below is cited to the current tree (working-tree-clean,
11 commits ahead of origin, HEAD `cd8803c`). The whole slice is **repack-only**
(`IF ROM_BASE < $4000`); the lean 16 KB build keeps its int-only fixed-pool store
byte-identical.

---

## 0. TL;DR + the honest payoff question (read before signing)

Slice 4b moves numeric scalar variables out of the fixed high-RAM pool
`VARTAB $E1C0..$E240` and into the real-MSX contiguous bottom-up chain
(`program-text → scalars → arrays → free → string-heap → HIMEM`), the same chain
arrays and string bodies already live in. It is the arc's **"mechanically simpler,
lower payoff"** slice (arc spec §15).

**What it buys (be candid):**
1. **Architectural completeness of memory model A** — the last numeric fixed pool
   dissolves; the allocator chain becomes real, not half-real.
2. **Reclaims the 128-byte `$E1C0` RAM pool** and **removes the fixed scalar cap**
   (today ~11–25 scalars depending on type mix; after 4b, bounded only by
   `HIMEM`/the shared free region).
3. **`HIMEM` becomes a live scalar ceiling** — currently record-only
   ([`clear.asm:29-30`](../basic/clear.asm) "No allocator consults HIMEM yet").

**What it costs / risks:**
- The core mechanism is an **insert-and-shift** (creating a scalar moves the entire
  array region up), plus the same `FRETOP` collision / GC-retry arrays already do.
  This is genuinely more delicate than the current bump-into-fixed-pool store.
- The zerobas charter is **game-loader-scoped**; loader stubs use few scalars and
  essentially never exhaust the 128-byte pool. So the *user-facing* value is low —
  this is an internal-architecture slice.

**Decision the sign-off must make (Q0, §13):** proceed with 4b now, or **close the
arrays/DIM arc after 4a** and treat scalar relocation as a documented, deliberately-
deferred divergence (the fixed pool works; the only observable loss is the scalar
cap, which the charter never hits). This contract is written so that either answer
is defensible; if we proceed, §1–§12 are the plan.

---

## 1. Current state (measured, post-4a)

zerobas today runs **two disjoint storage regions**, not the classic single chain:

### 1a. The fixed high-RAM pool (page `$E1`) — what 4b relocates

| Store | Span | Entry | Managed by |
|---|---|---|---|
| **Numeric scalars** `VARTAB` | `$E1C0..$E240` (128 B) | `[name0][name1][type][value:2/4/8]`, stride `type+3` (5/7/11 B), key `(name0,name1,type)` | `vars.asm` |
| String scalars `STRTAB` | `$E240..$E268` (40 B) | `[name0][name1][len:1][ptr:2]` × 8 (already a heap descriptor, post-4a) | `strvar.asm`/`str-engine.asm` |

- The numeric pool is a **flat, packed, bump-allocated array**; entries are never
  deleted, so the first `name0==0` byte is the bump frontier
  ([`vars.asm:291-348`](../basic/vars.asm)).
- `VARTAB`/`VAREND` are **compile-time constants** loaded as immediates
  (`ld hl,VARTAB` at [`vars.asm:203,300,781`](../basic/vars.asm)); there is **no**
  `ld hl,(VARTAB)` anywhere. `VAREND==STRTAB==$E240` is a hard pin (STRTAB must not
  move) — [`sysvars.inc:405-418`](../basic/sysvars.inc).
- **4b touches the numeric pool only.** `STRTAB` (string scalars) stays a fixed pool
  — see the Q1 fork (§6).

### 1b. The contiguous chain — what 4b joins

```
$8001            PRGEND+2         (ARYEND=$0000)   FRETOP            C = min(HIMEM,TXTMAX)
  |  program text  |   array area   |   free gap    |   string heap    |
  +----------------+----------------+---------------+------------------+
   grows up  ->       grows up ->                     <- grows down     ^ceiling
```

| Symbol | Equate | Kind | Role |
|---|---|---|---|
| `PRGEND` | `$E026` | **live cell** (2 B) | addr of program's `$0000` end marker; array anchor = `PRGEND+2` |
| — | — | — | **no `ARYTAB`/`VARTAB` chain pointer exists**; array base is *derived* `(PRGEND)+2`, array end is a `$0000` sentinel found by stride-walk |
| `FRETOP` | `$E268` | **live cell** (2 B) | string-heap low frontier; heap occupies `[FRETOP,C)`, grows down |
| `HIMEM` | `$FC4A` | record-only for CLEAR, **read live** by heap ceiling | top of usable RAM |
| `TXTMAX` | `$BE00` (repack) | constant | ceiling input |

- Array base is computed **four times** as `(PRGEND)+2`:
  [`sub/arrays.asm:524-526`](../sub/arrays.asm) (`ary_alloc`), `:455-457` (`ary_find`),
  [`sub/strheap.asm:331-341`](../sub/strheap.asm) (`strheap_aryend`), and
  [`basic/arrays.asm:111-119`](../basic/arrays.asm) (`ary_reset`).
- Collision invariant `ARYEND ≤ FRETOP`; on a bump collision the allocator GCs the
  heap **once** and retries before OOM
  ([`sub/arrays.asm:582-610`](../sub/arrays.asm), [`sub/strheap.asm:284-311`](../sub/strheap.asm)).
- The heap treats everything below `FRETOP` as opaque array region; **GC never
  touches array data** — it only needs a correct "top of the region below me"
  (`ARYEND`), re-derived each alloc.

**The pivotal fact:** the first array descriptor is written at `PRGEND+2`,
**immediately after program text.** There is **no gap** reserved for scalars. To put
scalars into the chain, 4b must insert a scalar region between `PRGEND+2` and the
array base — which means **shifting the entire array region up**.

---

## 2. Target model

Adopt the real-MSX order, with **one new live pointer** `ARYTAB` (= scalar-region
end = array base):

```
$8001          PRGEND+2      (ARYTAB)         (ARYEND=$0000)  FRETOP        C
  | program text |  scalars  |    arrays      |   free gap    | string heap |
  +--------------+-----------+----------------+---------------+-------------+
     grows up ->   grows up->   grows up ->                     <- grows down
```

- **Scalar base** = `PRGEND+2` (derived, as arrays are today).
- **`ARYTAB`** = new live 2-byte cell = end of the scalar region = base of the array
  region. Every current `(PRGEND)+2` array-anchor site re-anchors on `(ARYTAB)`.
- **Scalar entry format unchanged**: `[name0][name1][type][value:2/4/8]`, key
  `(name0,name1,type)`. Only the *location* changes; the value codec, name parser,
  and type system carry over intact (they need only an entry base address —
  confirmed format-agnostic, §5).
- **Ceiling**: scalar growth shares the free region below `FRETOP`. Inserting a
  scalar shifts arrays up, raising `ARYEND` toward `FRETOP` → the *same* collision /
  GC-once-retry / OOM path arrays use, now reachable from scalar creation too.

---

## 3. The core mechanism (the delicate part)

### 3a. Create a scalar (the insert-and-shift)

`var_alloc_or_find` today: walk the fixed pool; if absent, bump-write into free
space with a `VAREND` room check ([`vars.asm:359-411`](../basic/vars.asm)). New:

1. Walk `[PRGEND+2, ARYTAB)` for `(key,type)`. Found → return entry addr (§3c: done).
2. Absent → need a new `stride = type+3` byte entry at the top of the scalar region
   (address `ARYTAB`). This requires opening a `stride`-byte hole at `ARYTAB` by
   **shifting the entire array region `[ARYTAB, ARYEND+2)` up by `stride`**.
3. **Collision check first** (before moving anything): `new ARYEND+2 = ARYEND+2 +
   stride`; if `≥ FRETOP`, GC the heap once and retry; still colliding → OOM (do not
   move, do not write — leave state consistent, like `var_store_fac`'s silent-drop
   contract today).
4. **Shift**: `LDDR` the array block up by `stride` (top-down to handle the growing
   overlap). Array descriptors relocate wholesale; **string-array element
   descriptors' `ptr` fields still point into the heap and are unaffected** (only the
   descriptor moves, not the body).
5. Write the new scalar entry `[name0][name1][type]` at the freed hole, **zero-fill**
   the value (reuse the existing `zero_fill`), bump `ARYTAB += stride`.
6. Return the entry address.

### 3b. Reset the scalar region (the `ARYTAB` re-anchor)

`clear_vars` today zero-fills the 128-byte pool ([`vars.asm:781-789`](../basic/vars.asm)).
New: set `ARYTAB = PRGEND+2` (empty scalar region), mirroring `ary_reset`'s sentinel
write. This is smaller than the 128-byte wipe.

**Correctness constraint (not optional):** the scalar region is anchored at
`PRGEND`, which the editor moves on **every** program edit
([`program.asm:169,513,549`](../basic/program.asm), `relink` tail-calls `ary_reset`
[`program.asm:552-565`](../basic/program.asm)). When `PRGEND` moves, the scalar
region's base moves under it — so **`relink` must reset the scalar region too**
(not just arrays). Today `relink` calls `ary_reset` but *not* `clear_vars`, so
scalars survive an edit; after 4b they cannot (their bytes are now under program
text or at the wrong address). This is:
- **required for correctness** (a moved base invalidates the old contents), and
- **more MSX-faithful** — stock MSX-BASIC clears *all* variables on a direct-mode
  program edit. It is a deliberate, documented behaviour change from current zerobas
  (which kept scalars across edits as an artifact of the off-to-the-side pool).

Concretely: `relink` / `new_prog` / `run_prog` / `ex_clear` must reset **scalars +
arrays** together. The clean move is a shared `vars_reset` (set `ARYTAB=PRGEND+2`)
that `ary_reset` chains into, so the four call sites stay single-call.

### 3c. Read / store a scalar (unchanged codec)

`var_load_fac` / `var_store_fac` ([`vars.asm:417-530`](../basic/vars.asm)) take an
entry base address and copy/coerce value bytes to/from `FAC`. They are
**location-independent** and carry over unchanged; only the *find/alloc* that hands
them the address changes. `ev_f_var` (read, [`expr.asm:569-594`](../basic/expr.asm))
and `ex_let` (write, [`interp.asm:290-334`](../basic/interp.asm)) are unchanged above
the find/alloc call.

---

## 4. Region / placement — the shape-C split

Per [`decision-arrays-slice4-space.md`](decision-arrays-slice4-space.md) §3–4 and the
playbook, 4b is a **shape-C** feature: pure-RAM pointer/memory bulk → a page-0
sub-ROM leaf; thin `FAC`-adjacent glue stays main-side. This is exactly how arrays
split.

| Piece | Home | Notes |
|---|---|---|
| Scalar walk (find by key,type), insert-and-shift, `FRETOP` collision + GC-once-retry, `vars_reset` | **page-0 sub-ROM leaf** — new `SUBROM_IDX_SCALAR=6` *or* folded into the existing ARY tenant (Q4, §12) | pure-RAM pointer work; calls in-page sibling `strheap_gc` (like `ary_alloc`) |
| `var_name_key`, `deftbl_lookup`, `var_str_type`, `ex_def_type` | **main** (unchanged) | pure key/type resolution, no pool address |
| `var_load_fac` / `var_store_fac` value codec + coercion | **main** (unchanged bodies) | needs `FAC` + float routines (`fac_to_int_strict`, `round_single_and_pack`) — must stay main-side |
| `var_alloc_or_find` / `var_find_typed` | **become thin main glue** → marshal `SCV_*` param block, `subrom_call`, read result addr | mirrors `ary_engine_call` ([`basic/arrays.asm:265-274`](../basic/arrays.asm)) |
| `ARYTAB` derivation at the 4 array-anchor sites | **in place** (`(PRGEND)+2` → `(ARYTAB)`) | 2 tenant sites + `strheap_aryend` + `ary_reset` |

**ABI** (reuse wholesale, [`basic/subromcall.asm:50-66`](../basic/subromcall.asm),
[`sub/equates.inc:33-61`](../sub/equates.inc)): `IX = SUBROM_ENTRY_BASE_P0 +
3*SUBROM_IDX_SCALAR`; a new `SCV_*` param block (op / key / type / return-addr /
err) aliased onto provably-dead scratch like `ARY_*`; `A`=result, `CF`=absent, DI.
`SUBROM_IDX_SCALAR = 6` is the next append-only enum slot (never renumber).

**Tenant closure:** the leaf touches only its param block, read-only sysvars
(`PRGEND`, `ARYTAB`, `FRETOP`, `HIMEM`), the scalar/array RAM regions, and the
in-page `strheap_gc`/`ary_stride` siblings — so it passes `check_tenant_closure.py`
by construction (no main-page call).

---

## 5. What changes, by file

- [`basic/vars.asm`](../basic/vars.asm) — `var_find_typed` (298-348) + `var_alloc_or_find`
  (359-411) lose their fixed-`VAREND` walk/room-check and become thin glue over the
  new leaf; `clear_vars` (754-798) swaps the 128-byte wipe for `vars_reset`
  (`ARYTAB=PRGEND+2`). `var_load_fac`/`var_store_fac`/`var_name_key`/`deftbl_lookup`
  unchanged.
- **new** `sub/scalar.asm` — the page-0 leaf (walk / insert-shift / collision-retry /
  reset). ~130–180 B est.
- [`sub/arrays.asm`](../sub/arrays.asm) — `ary_alloc` (524), `ary_find` (455): base
  `(PRGEND)+2` → `(ARYTAB)`.
- [`sub/strheap.asm`](../sub/strheap.asm) — `strheap_aryend` (331-341): base
  `(PRGEND)+2` → `(ARYTAB)`.
- [`basic/arrays.asm`](../basic/arrays.asm) — `ary_reset` (111-119) re-anchors on
  `ARYTAB`; add `vars_reset`/chain so scalar+array reset stay one call.
- [`basic/program.asm`](../basic/program.asm) — confirm `relink` (565) / `new_prog`
  (173) / `run_prog` (190) reset **scalars too**; [`basic/clear.asm`](../basic/clear.asm)
  `ex_clear` (74) likewise; make `HIMEM` a live ceiling input (it already is, for the
  heap — the scalar path just reuses `strheap_ceiling`/the `FRETOP` collision).
- [`basic/sysvars.inc`](../basic/sysvars.inc) — new `ARYTAB` live cell + `SCV_*`
  param block; retire/repurpose the `VARTAB`/`VAREND`/`VARSLOTS` fixed-pool equates
  (repack path); the 128 B `$E1C0..$E240` window is **freed** (RAM win).
- [`sub/equates.inc`](../sub/equates.inc) — `SUBROM_IDX_SCALAR = 6`.

---

## 6. The design fork — Q1: numeric-only vs. also unify string scalars

After 4a, **string scalars** live in a *separate* fixed pool `STRTAB $E240` as 5-B
`[name0][name1][len][ptr]` descriptors (already heap-pointer form). Two scopes:

- **(A) Numeric-only 4b (recommended).** Relocate the numeric pool; leave `STRTAB` a
  fixed pool. One fixed pool remains, retired later as an optional **4c**. Bounded
  risk: the insert-shift touches **no GC roots** (string-array element descriptors
  move with their array block but their heap `ptr` values are unchanged; string
  *scalar* descriptors don't move at all). Matches arc spec §15's literal scope.
- **(B) Unify string scalars into the same variable area too.** Fully faithful (one
  MSX simple-variable area; a string entry is `[name0][name1][type=1][len][ptr]`).
  But it makes **string-scalar descriptors chain-resident**, so **`strheap_gc`'s root
  enumeration must walk the variable area** instead of `STRTAB`, and edit/relink must
  reclaim orphaned bodies — i.e. it re-touches the GC root set that 4a stabilised.
  Higher risk, and it re-opens heap territory 4b is otherwise clean of.

**Recommendation: (A).** It respects the arc's hard-won "smaller slices" lesson
(every slice hid ≥1 matrix-invisible bug), keeps 4b a pure pointer-shift with no GC
interaction, and defers the GC-root-touching unification to its own signed-off slice
(4c) if ever wanted. The charter never needs it. **Your call at sign-off.**

---

## 7. Behaviour / faithfulness deltas (all deliberate, all documented)

1. **Edit clears all variables (incl. scalars).** New; required by §3b; MSX-faithful.
   Today scalars survive an edit. Gate + PROVENANCE note.
2. **`VARPTR(v)` addresses now move.** A scalar's chain address changes when a *later*
   scalar is created (the shift). This is exactly stock MSX semantics (VARPTR is only
   valid until the next variable is allocated); today's fixed pool made it
   accidentally stable. Document; no gate can pin a moving address, so the gate
   asserts the *value at the returned address* immediately after VARPTR.
3. **Scalar count is now dynamic**, bounded by the shared free region / `HIMEM`, not a
   fixed ~11–25. `Out of memory` replaces silent-drop when the *whole chain* is
   exhausted (matches the array OOM disposition).
4. **Lean build unchanged / byte-identical** (all 4b is `ROM_BASE < $4000`).

---

## 8. RAM + ROM space

- **RAM: net +128 B freed** — the `$E1C0..$E240` numeric pool dissolves; scalars now
  share the `$8001..HIMEM` chain (no fixed cost). New cost: `ARYTAB` (2 B) + `SCV_*`
  param block (~8–12 B, aliased onto dead scratch as `ARY_*` is). Net RAM ≈ +110 B.
- **ROM (main): predicted net-neutral-to-positive** (the shape-C thesis). Removed
  from main: the fixed-`VAREND` walk/room-check arithmetic in `var_find_typed` +
  `var_alloc_or_find` (~80 B) and the 128-byte `clear_vars` wipe loop. Added to main:
  thin `SCV_*` marshalling glue (~40–60 B) + the `(PRGEND)+2`→`(ARYTAB)` edits (net
  ~0). The insert-shift/collision bulk lands in the **sub-ROM** (12 KB free), not the
  full main regions. Target: **≥ 0 main-ROM delta**, measured via `__MEAS_LOW_END` /
  `__MEAS_PAGE1_END` (§9). If page-1 glue overflows its (currently 3 B) headroom, the
  reclamation ladder is the cold-page-1 eviction of
  [`decision-arrays-slice4-space.md`](decision-arrays-slice4-space.md) §5.2 — *not*
  expected to be needed.

---

## 9. Gate plan

**Differential** (VG-8020 reference vs repack, `probes/lib/omsx_repl.py`; extend
`array-acceptance`):
- Scalar round-trips across all types (`A%`/`A!`/`A#`/default-double), including
  many-scalar programs that formerly overflowed the 128-byte pool (now succeed).
- **Interleave scalar creation with array growth** — the insert-shift's core hazard.
  `DIM A(5): B=1: DIM C(5): D=2: PRINT A(0);B;C(0);D` and heavier churn; assert array
  *contents* survive scalar-triggered shifts (content, not just length — the standing
  4a lesson).
- **Scalar creation that forces a `FRETOP` collision → GC-retry → success**, and one
  that genuinely exhausts the chain → `Out of memory`.
- **String-array elements survive scalar shifts** (their heap `ptr` must stay valid):
  `DIM S$(3): S$(0)="hello": X=1: Y=2: Z=3: PRINT S$(0)` after several scalar allocs.
- **Edit-clears-scalars**: set a scalar in direct mode, edit a line, confirm the
  scalar is cleared (new faithful behaviour).
- **VARPTR-moves**: `A=5: PRINT VARPTR(A)` value-at-address check, then create `B` and
  re-read.
- **FOR/NEXT + READ** over typed loop vars (the shim path), post-relocation.

**Adversarial battery + Fable review** (the standing arc rule — *every* slice hid a
matrix-invisible bug; 4a took 4 Fable passes): LDDR shift direction/overlap, the
collision-before-move ordering (never move on OOM), `ARYTAB` consistency across all
4 anchor sites + the heap's `strheap_aryend`, the edit/relink reset of *both*
regions, register/`IX` clobber across the new `subrom_call`, and zero-fill width.

**Standing gates:** `check_tenant_closure` (new leaf), `subrom-abi-check`,
`__MEAS_LOW_END`/`__MEAS_PAGE1_END` re-measure (prove ≥0 main delta), lean
byte-identity SHA, full `make array-acceptance` (119) + `make string-acceptance` (6),
and the disk-interleaved heavy-churn case (a scalar-shift GC must not corrupt disk
work-area RAM — the 4a S6 lesson).

**Host unit tests** (`tests/`, emulator-free): the insert-shift and collision math as
a pure-Z80 unit test (like `test_arrays.py`), proven non-vacuous (revert → red).

---

## 10. Provenance

Clean-room. The `ARYTAB` two-pointer split, the insert-and-shift, and the shared
collision/GC-retry are zerobas's own realisation of the **documented** MSX memory
model (`TXTTAB→VARTAB→ARYTAB→…→FRETOP→HIMEM`), reusing our own arrays/heap
machinery. No disassembly; the model is a published contract (MSX2 TH / MSX Assembly
Page), the code is ours. Note in `basic/PROVENANCE.md` §variable area.

---

## 11. Slices boundary

4b = **numeric** scalar relocation (this doc). **4c** (optional, only if signed off)
= string-scalar unification into the same variable area (§6-B) — deferred because it
re-touches the heap GC root set. After 4b (A), the arrays/DIM arc's *numeric* memory
model is fully real; `STRTAB` remains the one intentional fixed pool.

---

## 12. Open questions for sign-off

- **Q0 — proceed at all?** 4b is low user-facing value (charter is game-loader-scoped;
  the fixed pool is never exhausted). Proceed now, or **close the arc after 4a** and
  log scalar relocation as a deliberate deferral? (§0)
- **Q1 — scope: numeric-only (A) vs. also unify string scalars (B)?** Recommend **A**
  (§6): bounded risk, no GC-root interaction, arc "smaller slices" lesson.
- **Q2 — edit-clears-scalars.** Confirm the new (MSX-faithful, correctness-required)
  behaviour that a program edit clears scalars is acceptable (§3b, §7.1).
- **Q3 — `ARYTAB` as a real stored pointer** vs. keeping the "derive by walk"
  minimalism arrays use today. Recommend a **stored `ARYTAB` cell** (the scalar region
  has no self-describing terminator the way the array `$0000` sentinel does; a stored
  end pointer is cleaner and the 2 B is trivial against the 128 B freed).
- **Q4 — tenant boundary.** Confirm the shape-C split (§4): find/insert-shift/collision
  in a new `SUBROM_IDX_SCALAR=6` page-0 leaf; codec + coercion stay main-side. Or fold
  into the existing `SUBROM_IDX_ARY` tenant (shared region, shared collision code) as
  a new op rather than a new leaf — arguably tighter, since scalars and arrays share
  the same span and the same `strheap_gc` retry. **Recommend folding into the ARY
  tenant as new ops** (one leaf owns the whole `[PRGEND+2, FRETOP)` region), unless you
  prefer a separate leaf for clarity.
