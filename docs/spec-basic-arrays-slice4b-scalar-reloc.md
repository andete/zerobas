<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — Arrays slice 4b: numeric scalar relocation into the contiguous chain

Status: **REVIEW COMPLETE — ALL FINDINGS RESOLVED, READY TO SHIP (2026-07-17).**
All five §12 sign-off decisions resolved (Q0 / Q1 / Q2 / Q3 / Q4) and implemented;
array-acceptance 130/130 / string-acceptance 6/6 / lean-byte-identity all
independently re-verified green. The Fable adversarial review (completed across two
passes) found **three** green-suite-invisible bugs, **all now fixed + verified**:
§13a (stale array-element address across a mid-eval scalar alloc — `A(0)=VARPTR(B)`
hung/corrupted; delta-correction fix), §13a-F1 (cold-boot wild write through an
uninitialised `PRGEND` — zeroed HIMEM on real hardware; fix = drop the `clear_vars`
`vars_reset` call; empirically re-verified by `probes/basic/basic_probe_prgend_init.py`),
and §13a-F2 (LOW — the "edit clears all vars" claim was over-stated; string scalars
persist to 4c — documented, not a code bug). This contract is the
*implementation contract* the slice-4 space decision
([`decision-arrays-slice4-space.md`](decision-arrays-slice4-space.md) §7) calls
for, restricted to the **4b** half (numeric scalar relocation); the 4a half (string
heap) shipped 2026-07-17, and **4c** (string-scalar unification) is the committed
follow-on (§11).

**Final gate record (2026-07-17, post-§13a-fix):** `make` clean, lean `basic.rom`
16384 B byte-identical (SHA-256 unchanged: `e21f61fe9ecb855ce69a29831a5990070
c215613479310da368c350bd4228005`); `make basic-reloc` clean (`__MEAS_LOW_END`
free 3→**12 B** (+9, NET SAVINGS — the relocated `ela_err`/`ela_abort_tm`/
`ela_abort_fp`/`elas_err`/`elas_abort_fp` tails freed more than the two new
`call`s + `jr`→`jp` conversions cost), `__MEAS_PAGE1_END` free 73→**13 B** (-60,
the delta-correction arithmetic + the five relocated error tails); `make
subrom-abi-check`/`subrom-closure-check` clean (118 routines, no page-1
escape); `make unit-test` — `tests/test_arrays.py` **ALL PASS**; the SAME 5
PRE-EXISTING unrelated host-test failures (`test_mid_stmt.py`/
`test_str_compare.py`/`test_str_engine.py`/`test_str_fn.py`/
`test_str_verbs.py`, string-engine internals, out of scope, untouched in
substance) as the pre-§13a-fix baseline; `make array-acceptance` **130/130 ALL
PASS** (127 pre-fix baseline + 3 new §13a gate cases: `scalar.varptr.elem`,
`scalar.varptr.neighbor`, `strarr.varptr.neighbor`); `make string-acceptance`
**6/6 PASS**; crunch probe byte-identical. The exact §13a repro (`DIM
A(1):A(0)=VARPTR(B):PRINT A(0)`) re-run standalone via
`probes/lib/omsx_repl.py` `run_case`: prints the VARPTR value cleanly, no hang
(was: hang, pre-fix).

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

## 0. TL;DR + scope under the faithful-full-BASIC charter

Slice 4b moves numeric scalar variables out of the fixed high-RAM pool
`VARTAB $E1C0..$E240` and into the real-MSX contiguous bottom-up chain
(`program-text → scalars → arrays → free → string-heap → HIMEM`), the same chain
arrays and string bodies already live in. It is arc spec §15's **"mechanically
simpler"** slice — but **not** a low-value one.

**Charter note (2026-07-17):** zerobas's BASIC is now on the **faithful full MSX1
BASIC** charter, no longer game-loader-scoped
([`charter-faithful-full-msx1-basic`](../../.claude/projects/-Users-joost-projects-zerobas/memory/charter-faithful-full-msx1-basic.md)).
Under that charter the real MSX contiguous variable model *is the deliverable*, so the
earlier "the loader never exhausts the pool, so maybe skip it" framing is **retired**.
Scalar relocation is in scope; the only open decisions are staging and mechanism, not
whether to do it.

**What it delivers:**
1. **Faithfulness** — the real MSX
   `TXTTAB→VARTAB→ARYTAB→STREND→free→FRETOP(strings)→MEMSIZ` model, of which zerobas
   already runs the array + string-heap half; 4b completes the numeric-scalar leg. The
   last numeric fixed pool dissolves.
2. **Removes the fixed scalar cap** (today ~11–25 scalars by type mix; after 4b,
   bounded only by `HIMEM`/the shared free region) and **reclaims the 128-byte
   `$E1C0` RAM pool**.
3. **`HIMEM` becomes a live scalar ceiling** — currently record-only
   ([`clear.asm:26-30`](../basic/clear.asm) "No allocator consults HIMEM yet").

**What it costs / risks:**
- The core mechanism is an **insert-and-shift** (creating a scalar moves the entire
  array region up), plus the same `FRETOP` collision / GC-retry arrays already do —
  genuinely more delicate than the current bump-into-fixed-pool store. Managed by the
  arc's standard discipline (small slice, differential + adversarial + Fable, §9).

**The faithful endpoint** is the *unified* variable area — real MSX keeps string and
numeric scalars in one table, a string entry's value being the 3-byte `[len][ptr]`
descriptor. So `STRTAB`-as-a-side-pool is a divergence to eliminate, not a resting
point. The live sign-off decision is therefore **staging** (§6 / Q1): reach the
unified model in one combined slice, or split **4b = numeric** (this contract) then
**4c = string-scalar unification** — the arc's "smaller slices" lesson favouring the
split, with 4c committed (not optional) toward the faithful endpoint.

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
  [`sub/arrays.asm:506-526`](../sub/arrays.asm) (`ary_alloc`), `:455-457` (`ary_find`),
  [`sub/strheap.asm:495-341`](../sub/strheap.asm) (`strheap_aryend`), and
  [`basic/arrays.asm:315-119`](../basic/arrays.asm) (`ary_reset`).
- Collision invariant `ARYEND ≤ FRETOP`; on a bump collision the allocator GCs the
  heap **once** and retries before OOM
  ([`sub/arrays.asm:1102-610`](../sub/arrays.asm), [`sub/strheap.asm:437-311`](../sub/strheap.asm)).
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
space with a `VAREND` room check ([`vars.asm:544-411`](../basic/vars.asm)). New:

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
([`program.asm:282,513,549`](../basic/program.asm), `relink` tail-calls `ary_reset`
[`program.asm:552-565`](../basic/program.asm)). When `PRGEND` moves, the scalar
region's base moves under it — so **`relink` must reset the scalar region too**
(not just arrays). Today `relink` calls `ary_reset` but *not* `clear_vars`, so
scalars survive an edit; after 4b they cannot (their bytes are now under program
text or at the wrong address). This is:
- **required for correctness** (a moved base invalidates the old contents), and
- **more MSX-faithful** — stock MSX-BASIC clears *all* variables on a direct-mode
  program edit. It is a deliberate, documented behaviour change from current zerobas
  (which kept scalars across edits as an artifact of the off-to-the-side pool). NOTE
  the interim caveat in §7.1: 4b clears the *numeric* scalar chain + arrays, but the
  still-fixed-pool *string* scalars (`STRTAB`) survive an edit until 4c unifies them.

Concretely: `relink` / `new_prog` / `run_prog` / `ex_clear` must reset **scalars +
arrays** together. The clean move is a shared `vars_reset` (set `ARYTAB=PRGEND+2`)
that `ary_reset` chains into, so the four call sites stay single-call.

### 3c. Read / store a scalar (unchanged codec)

`var_load_fac` / `var_store_fac` ([`vars.asm:566-530`](../basic/vars.asm)) take an
entry base address and copy/coerce value bytes to/from `FAC`. They are
**location-independent** and carry over unchanged; only the *find/alloc* that hands
them the address changes. `ev_f_var` (read, [`expr.asm:543-594`](../basic/expr.asm))
and `ex_let` (write, [`interp.asm:582-334`](../basic/interp.asm)) are unchanged above
the find/alloc call.

---

## 4. Region / placement — the shape-C split

Per [`decision-arrays-slice4-space.md`](decision-arrays-slice4-space.md) §3–4 and the
playbook, 4b is a **shape-C** feature: pure-RAM pointer/memory bulk → a page-0
sub-ROM tenant; thin `FAC`-adjacent glue stays main-side. This is exactly how arrays
split.

**Q4 locked — fold into the existing ARY tenant** (`SUBROM_IDX_ARY`,
[`sub/arrays.asm`](../sub/arrays.asm)) as **new `ARY_OP` op-codes**, not a new leaf.
Rationale: scalars and arrays share one region `[PRGEND+2, FRETOP)` and the same
`strheap_gc` collision retry; one tenant owning the whole region keeps the invariant
in a single place, and the scalar ops' args/results fit the **existing `ARY_*` param
block** (key + type in, addr + err out — identical to array resolve), so no new param
block and no new `SUBROM_IDX` are needed.

| Piece | Home | Notes |
|---|---|---|
| Scalar walk (find by key,type), insert-and-shift, `FRETOP` collision + GC-once-retry, `vars_reset` | **ARY tenant, new `ARY_OP` ops** ([`sub/arrays.asm`](../sub/arrays.asm)) | pure-RAM pointer work; calls in-page sibling `strheap_gc` (like `ary_alloc`) |
| `var_name_key`, `deftbl_lookup`, `var_str_type`, `ex_deftype` | **main** (unchanged) | pure key/type resolution, no pool address |
| `var_load_fac` / `var_store_fac` value codec + coercion | **main** (unchanged bodies) | needs `FAC` + float routines (`fac_to_int_strict`, `round_single_and_pack`) — must stay main-side |
| `var_alloc_or_find` / `var_find_typed` | **become thin main glue** → set `ARY_OP` = scalar-find/alloc, `ary_engine_call`, read `ARY_ADDR` | reuses `ary_engine_call` + `ary_errmap` ([`basic/arrays.asm:487-301`](../basic/arrays.asm)) verbatim |
| `ARYTAB` derivation at the 4 array-anchor sites | **in place** (`(PRGEND)+2` → `(ARYTAB)`) | 2 tenant sites + `strheap_aryend` + `ary_reset` |

**ABI** (reuse wholesale, [`basic/subromcall.asm:39-66`](../basic/subromcall.asm),
[`basic/arrays.asm:487-301`](../basic/arrays.asm)): `IX = SUBROM_ENTRY_BASE_P0 +
3*SUBROM_IDX_ARY`; the **existing `ARY_*` param block** ([`sysvars.inc:1953-709`](../basic/sysvars.inc))
carries op / `ARY_KEY` / `ARY_TYPE` in and `ARY_ADDR` / `ARY_ERR` out; new op-codes
appended to the `ARY_OP` dispatch (append-only, after the current resolve/alloc/erase/
copy-str set). `A`=result, `CF`=absent, DI. New tenant-err codes extend `ary_errmap`
(e.g. scalar OOM → `FPERR` `Out of memory`, matching the array disposition).

**Tenant closure:** the added ops touch only the `ARY_*` block, read-only sysvars
(`PRGEND`, `ARYTAB`, `FRETOP`, `HIMEM`), the scalar/array RAM regions, and the
in-page `strheap_gc`/`ary_stride` siblings — so the tenant still passes
`check_tenant_closure.py` by construction (no main-page call).

---

## 5. What changes, by file

- [`basic/vars.asm`](../basic/vars.asm) — `var_find_typed` (298-348) + `var_alloc_or_find`
  (359-411) lose their fixed-`VAREND` walk/room-check and become thin glue that sets
  `ARY_OP` = scalar-find/alloc and calls `ary_engine_call`; `clear_vars` (754-798)
  swaps the 128-byte wipe for `vars_reset` (`ARYTAB=PRGEND+2`).
  `var_load_fac`/`var_store_fac`/`var_name_key`/`deftbl_lookup` unchanged.
- [`sub/arrays.asm`](../sub/arrays.asm) — **gains the scalar ops** (walk / insert-shift /
  collision-retry / reset, ~130–180 B est., new `ARY_OP` dispatch entries); and
  `ary_alloc` (524), `ary_find` (455) re-anchor base `(PRGEND)+2` → `(ARYTAB)`.
- [`sub/strheap.asm`](../sub/strheap.asm) — `strheap_aryend` (331-341): base
  `(PRGEND)+2` → `(ARYTAB)`.
- [`basic/arrays.asm`](../basic/arrays.asm) — `ary_reset` (111-119) re-anchors on
  `ARYTAB`; add `vars_reset`/chain so scalar+array reset stay one call.
- [`basic/program.asm`](../basic/program.asm) — confirm `relink` (565) / `new_prog`
  (173) / `run_prog` (190) reset **scalars too**; [`basic/clear.asm`](../basic/clear.asm)
  `ex_clear` (74) likewise; make `HIMEM` a live ceiling input (it already is, for the
  heap — the scalar path just reuses `strheap_ceiling`/the `FRETOP` collision).
- [`basic/sysvars.inc`](../basic/sysvars.inc) — new `ARYTAB` live cell (Q3); retire/
  repurpose the `VARTAB`/`VAREND`/`VARSLOTS` fixed-pool equates (repack path); the
  128 B `$E1C0..$E240` window is **freed** (RAM win). `ARY_*` param block reused as-is
  (no new fields).

---

## 6. The design fork — Q1: numeric-only vs. also unify string scalars

After 4a, **string scalars** live in a *separate* fixed pool `STRTAB $E240` as 5-B
`[name0][name1][len][ptr]` descriptors (already heap-pointer form). Two scopes:

Under the faithful-full-BASIC charter the **endpoint is the unified variable area**
(real MSX stores string + numeric scalars together). So this is **not** a "whether"
question — `STRTAB` as a side pool is a divergence to eliminate — it is a **staging**
question:

- **(A) Split: 4b = numeric now, 4c = string-scalar unification next (recommended).**
  4b relocates the numeric pool and leaves `STRTAB` a fixed pool *temporarily*; 4c
  (committed, not optional) folds string scalars into the same variable area,
  reaching the faithful endpoint. Bounded per-slice risk: 4b's insert-shift touches
  **no GC roots** (string-array element descriptors move with their array block but
  their heap `ptr` values are unchanged; string *scalar* descriptors don't move at
  all). 4c then takes on the one hard interaction in isolation.
- **(B) Combined: one slice does numeric + string unification.** Reaches the endpoint
  in a single slice, but makes **string-scalar descriptors chain-resident**, so
  **`strheap_gc`'s root enumeration must walk the variable area** instead of `STRTAB`
  and edit/relink must reclaim orphaned bodies — re-touching the GC root set that 4a
  stabilised, in the *same* slice as the insert-shift. Higher blast radius.

**Recommendation: (A), with 4c committed.** The arc's hard-won "smaller slices"
lesson (every slice hid ≥1 matrix-invisible bug; 4a needed 4 Fable passes) argues
for isolating the GC-root-touching change from the insert-shift change. Same faithful
destination, lower per-slice risk. **Your call at sign-off** is A-split vs B-combined,
not whether to unify.

---

## 7. Behaviour / faithfulness deltas (all deliberate, all documented)

1. **Edit clears numeric scalars + arrays.** New; required by §3b; more MSX-faithful.
   Pre-4b, scalars survived an edit. **Interim-divergence caveat (Fable F2, 2026-07-17):**
   stock MSX-BASIC clears *all* variables on an edit, but 4b clears only the *numeric*
   scalar chain + arrays — **string scalars (the fixed `STRTAB` pool) still survive an
   edit**, because 4b does not relocate them (`relink`→`vars_reset` touches only the
   numeric/array region; `STRTAB` is untouched, deliberately, so heap bodies survive a
   bare relink). So after 4b, `A=5:A$="X"` + an edit → `A` clears, `A$` persists — a
   documented interim inconsistency, resolved by **4c** (string-scalar unification makes
   `A$` a chain-resident entry that clears with the rest). Gate `scalar.edit.clears`
   covers the numeric case only; do NOT add a differential `A$`-edit case (it would go
   red on this intentional interim state). Gate + PROVENANCE note.
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

**Standing gates:** `check_tenant_closure` (ARY tenant + its new ops), `subrom-abi-check`,
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

4b = **numeric** scalar relocation (this doc). **4c** (committed under the faithful
charter, its own signed-off contract) = string-scalar unification into the same
variable area (§6) — split out because it re-touches the heap GC root set. After 4b,
the *numeric* memory model is fully real and `STRTAB` remains a **temporary** fixed
pool; 4c retires it, reaching the faithful unified endpoint.

---

## 12. Sign-off decisions (all resolved 2026-07-17)

- **Q0 — proceed:** ✅ **YES.** Resolved by the faithful-full-BASIC charter (§0);
  "close the arc after 4a" is off the table.
- **Q1 — staging:** ✅ **SPLIT (A).** 4b = numeric now; **4c committed** =
  string-scalar unification (its own contract). Isolates the GC-root-touching change
  from the insert-shift change (§6).
- **Q2 — edit-clears-scalars:** ✅ **YES.** Authentic MSX behaviour + correctness-
  required (§3b, §7.1); documented behaviour change from current zerobas.
- **Q3 — `ARYTAB` pointer:** ✅ **STORED live cell.** The scalar region has no
  self-describing terminator; a stored end pointer is cleaner, 2 B trivial against the
  128 B freed.
- **Q4 — tenant boundary:** ✅ **FOLD into the ARY tenant** (`SUBROM_IDX_ARY`) as new
  `ARY_OP` ops reusing the `ARY_*` param block — no new leaf, no new `SUBROM_IDX`
  (§4). One tenant owns the whole `[PRGEND+2, FRETOP)` region and the shared
  `strheap_gc` retry.

**→ CONTRACT SIGNED OFF. Ready for implementation** ([[opus-vs-sonnet-model-split]]:
Sonnet implements + Fable adversarial review; the arc's Definition of Done includes
the openMSX acceptance suites actually *run*, [[gate-during-implementation]]).

---

## 13. Divergences / findings discovered during implementation (2026-07-17)

Recorded per the arc's standing discipline (every slice logs what the plan
didn't anticipate, not just what passed):

1. **A fifth `(PRGEND)+2` array-anchor site**, beyond the four §5 named
   (`ary_alloc`, `ary_find`, `strheap_aryend`, `ary_reset`): `sub/strheap.asm`
   `sg_walk_arrays` (the GC root-walker's own array-region traversal) derived
   `ARYBASE` the identical way and needed the SAME `(ARYTAB)` re-anchor. Found
   by `grep -rn "(PRGEND)"` across `sub/` + `basic/` before touching any code,
   not by a failing gate — logged here so a future re-audit doesn't need to
   re-derive it.
2. **A genuine IX-clobber regression, caught live by `array-acceptance`**
   (not anticipated in §4's ABI note). `var_find_typed`/`var_alloc_or_find`
   (vars.asm) becoming thin glue over `ary_engine_call` means they now clobber
   `IX` (the sub-ROM dispatch target) — but their PRE-4b contract never
   touched `IX`, and every real caller (`ev_f_var`, `var_get`/`var_set`,
   `ev_f_varptr`) holds the TEXT CURSOR in `IX` across the call. Symptom: 8
   `array-acceptance` cases FAILED with a phantom "syntax error" (every case
   touching a scalar variable as a subscript/loop var — `var.subscript`,
   `for.loop.fill`, the whole `strarr.*varsub/for.store` family, the S6
   GC-stress battery). Fixed with a `push ix`/`pop ix` guard around
   `ary_engine_call` in both routines (8 B page-1 cost, __MEAS_PAGE1_END
   81→73). This is exactly the class of bug
   [[gate-during-implementation]] warns about — invisible to a closure/
   byte-identity check, only caught by actually RUNNING the differential.
3. **A register-clobber bug in `scv_find` itself** (sub/arrays.asm), caught by
   the new `tests/test_arrays.py` Case 8 (host unit test, not the openMSX
   gate): the end-of-scalar-region test did `ld de,(ARYTAB)` every loop
   iteration, silently overwriting `D` (the target type, loaded once at
   entry and needed on every hit-check). Every re-find of a just-inserted
   scalar came back "not found". Fixed by testing `(ARYTAB)` byte-wise
   against H/L instead of via a 16-bit `DE` load, so `D` is never touched.
   Also fixed alongside: `scv_alloc`'s scratch frame was `dec sp`/`inc sp`'d
   13 times instead of 19 (its own documented field count) — the missing
   6 bytes let `SRC_LAST`/`DST_LAST`/`COUNT` overwrite the `CALL`-pushed
   return address on the stack, corrupting the return PC.
4. **Two pre-existing (not 4b-caused) host-unit-test gaps**, found while
   getting `tests/test_arrays.py` itself green:
   - `make_machine()` never seeded `TEMPTOP`, so any `ary_alloc` call (which
     always collides on a fresh `FRETOP=0` and forces a `strheap_gc`) made
     `sg_walk_temps` scan ~19000 bogus 3-byte strides from `TEMPTOP=0` up to
     `TEMPBASE`, occasionally exhausting the harness's step budget — this
     test was ALREADY failing on HEAD before this slice touched anything
     (confirmed via `git stash`). Fixed by seeding `TEMPTOP=TEMPBASE` (an
     empty temp-descriptor stack, the real cold-boot value).
   - Four OTHER pre-existing-broken host test files
     (`test_mid_stmt.py`/`test_str_compare.py`/`test_str_fn.py`/
     `test_str_verbs.py`) never seeded `PRGEND`, so their fresh `Machine()`
     had `ARYBASE` derived at address ~2 (pre-4b) or `ARYTAB` read as 0
     (post-4b) — the LATTER lands array-region derivation at the very START
     of the bridged sub-ROM binary, and a `strheap_gc` walking `$FF`-padded
     ROM tail as bogus descriptors can spin for the harness's whole step
     budget. These 4 files were ALREADY failing (unrelated STRTAB-format
     staleness, pre-dating 4b), but 4b's `ARYTAB` re-anchor turned their
     failure mode from a clean assertion list into an uncaught
     `RuntimeError`. Fixed (restoring the PRE-EXISTING, byte-identical
     failure output) by seeding `PRGEND`/`ARYTAB` to a safe placeholder
     address in each file, matching `tests/test_arrays.py`'s own convention.
     `test_str_engine.py` (the 5th pre-existing failure) is unaffected
     (fails identically before/after — a `KeyError` on a retired symbol,
     before any array/heap code runs). None of these 5 files' SUBSTANTIVE
     failures were touched or fixed — they are out of scope for this slice
     and flagged as a follow-up.
5. **No spec mis-statement found.** §7.2's "a scalar's chain address changes
   when a LATER scalar is created" reads more precisely as "an ARRAY's
   address moves when a scalar is created" (the actual §3a mechanism: a new
   scalar is appended at the current `ARYTAB` without touching any earlier
   scalar's own address — only the array region above it shifts). The
   ambiguity is harmless: §7.2's own gate design already anticipated it
   ("no gate can pin a moving address, so the gate asserts the value at the
   returned address immediately after VARPTR") — implemented exactly that
   way (`scalar.varptr.value`, `probes/basic/basic_probe_arrays.py`), so no
   gate depends on the imprecise phrasing.

## 13a. FIXED BUG (adversarial review 2026-07-17, fix landed 2026-07-17) — STALE ARRAY-ELEMENT ADDRESS

**Severity: HIGH (memory corruption + interpreter hang). Green-suite-invisible.
FIXED — see "Fix (landed)" below.** Found by the Fable adversarial pass;
empirically reproduced; fixed via a page-1-relocated delta correction (below),
gated (3 new `array-acceptance` cases, §9), and re-verified against the exact
repro standalone.

### Repro (confirmed on the repack build via `omsx_repl`)
```
DIM A(1) : A(0)=VARPTR(B) : PRINT A(0)
```
Output truncates at `[` — the interpreter **hangs / derails**. Also
`DIM A(3):A(0)=11:A(3)=22:A(0)=VARPTR(C)` then `PRINT A(3)` — same (a *neighbour*
element is corrupted). Controls (`A(0)=7`; `A(0)=9:B=5`) print correctly.

### Mechanism
`ex_let_arr` (`basic/arrays.asm`) resolves the array-element address
(`ary_op0_resolve`), **`push`es it**, then `call eval`s the RHS, then pops the
address and `ary_store_write`s. Slice-4b made **scalar creation shift the whole
array region UP** — and the RHS eval can create a scalar: `VARPTR(newvar)` calls
`var_alloc_or_find`, which allocates. (`VARPTR` is the *only* eval-time scalar
allocator — plain variable reads use `var_load_fac`, which is find-only and never
allocates. This is why the bug is narrow, and why it is a **4b regression**: pre-4b
scalar creation never moved arrays, so holding the address across eval was safe.)
The pushed address is now stale by one scalar entry's stride → the store writes to
the wrong location (corrupting a neighbour / the gap) and the element read after
hangs.

### Site audit (hazard #3 — completed in the main loop after the review was cut off)
The vulnerable pattern is: *hold a **relocatable** (array-region) address across an
operation that can allocate a scalar*. Exhaustive result — **exactly two sites**:
- **`ex_let_arr`** (numeric array-element LET) — VULNERABLE.
- **`ex_let_arr_str`** (string array-element LET; a numeric `VARPTR` sub-argument
  inside the string RHS, e.g. `S$(0)=MID$(A$,VARPTR(B))`) — VULNERABLE.

Everything else is SOUND: `ev_f_arr` / `str_eval_arr` (rvalue reads) resolve then
use atomically with no allocation between; scalar `var_load_fac`/`var_store_fac`
are atomic resolve-then-use; `ex_mid_stmt` targets a *scalar* string in the fixed
`STRTAB` pool (not relocated in 4b, so unaffected by numeric-scalar shifts);
`ex_read`/`ex_input` process targets sequentially and never eval `VARPTR`;
`VARPTR`-returned addresses are values, not interpreter-held pointers.

### Fix (landed 2026-07-17)
A scalar insertion shifts everything above `ARYTAB` up by exactly the amount
`ARYTAB` itself moves. So: **snapshot `ARYTAB` right after resolving the element
address (before the RHS eval); after eval, correct the saved address by
`+(ARYTAB_now − ARYTAB_before)`** before the store. (`corrected = ADDR +
(ARYTAB_now − ARYTAB_before)`.) This is provably correct — the element sits
above `ARYTAB`, auto-dim during eval appends at the tail and moves neither
`ARYTAB` nor the target element, and heap GC never moves the array region. The
same delta correction applies to both sites.

**Implementation collapses `[ADDR]` + the `ARYTAB` snapshot into ONE stack word**
(`OFFSET = ARYTAB_before − elem_addr`, so `corrected = ARYTAB_now − OFFSET`)
instead of two — this keeps each call site's stack frame the SAME SIZE as the
pre-fix `[ADDR]`-only frame, so `ela_err`/`ela_abort_tm`/`ela_abort_fp`/
`elas_err`/`elas_abort_fp`'s pop counts are UNCHANGED (only their location
moved, see below) — the design point that made the low-region budget close at
all (see "Space accounting" below).

**Relocation chosen:** the arithmetic (`ary_snapshot_offset` / `ary_apply_offset`
/ `ary_apply_offset_hl_sub`) lives in **`basic/vars.asm`, page-1** (right after
`deftbl_lookup`, inside the existing `IF ROM_BASE < $4000` block) — reached from
`basic/arrays.asm` (low region) by an ordinary same-bank `call`/`jp` (low region
and page 1 are the main ROM's co-mapped slot-0 pages, NOT a sub-ROM bank switch
— no `subrom_call`/CALSLT needed, unlike the `SUBROM_IDX_ARY` tenant). Two apply
variants because the two call sites have different live registers at the
correction point: `ex_let_arr` already has the cursor parked in IX (so
`ary_apply_offset` clobbers HL freely, returning the corrected address IN HL,
while DE — the RHS's live int-fast-path value — is untouched); `ex_let_arr_str`
still has the cursor live IN HL at that point (`str_eval`'s own return
contract), so `ary_apply_offset_hl_sub` preserves HL and returns the corrected
address in DE instead.

`ex_let_arr`'s/`ex_let_arr_str`'s own error tails (`ela_err`/`ela_abort_tm`/
`ela_abort_fp`/`elas_err`/`elas_abort_fp`) were ALSO relocated to `basic/
vars.asm` alongside the new arithmetic (their bodies are byte-identical to the
pre-fix ones, only moved + their call sites' `jr`→`jp` converted since the
targets are now out of branch range) — this is what makes the low-region delta
NET NEGATIVE despite the two new `call`s: relocating the five small tails frees
more low-region bytes than the two 3-byte `call`s + the `jr`→`jp` conversions
cost. `ela_parse_abort` (shared with `ex_dim`, a different stack frame) was
deliberately left untouched in the low region, per the task's own instruction.

### Space accounting (measured, `make basic-reloc`)
| | before fix | after fix | delta |
|---|---|---|---|
| `__MEAS_LOW_END` free | 3 B | **12 B** | **+9 B** (net low-region SAVINGS) |
| `__MEAS_PAGE1_END` free | 73 B | **13 B** | -60 B |

Both stay ≥ 0 — no overflow, no `STRING_ENGINE_OVERRAN_4000`/`BASIC_IMAGE_
OVERRAN_8000_CEILING` guard trip. Lean `basic.rom` SHA-256 unchanged
(`e21f61fe9ecb855ce69a29831a5990070c215613479310da368c350bd4228005` — all of
this is `IF ROM_BASE < $4000`, repack-only).

### Gate cases added (§9, `probes/basic/basic_probe_arrays.py`)
`scalar.varptr.elem`, `scalar.varptr.neighbor`, `strarr.varptr.neighbor` — all
**zb-only (`zbval`)**: triggering the shift needs a variable `VARPTR` has never
touched before (a find-only reference would skip the allocation and never
reproduce the hazard), and the VG-8020 reference's own `VARPTR` REQUIRES its
argument to already exist, raising `Illegal function call` on a fresh name
(confirmed empirically 2026-07-17: `PRINT VARPTR(ZZ)` on a never-referenced `ZZ`
errors; `ZZ=1:PRINT VARPTR(ZZ)` succeeds) — so the reference can never be an
oracle for this specific class; it is a genuinely zb-only mechanism (zerobas's
own auto-allocating `VARPTR`, an unrelated pre-existing slice-4b design choice,
§3a, not touched by this fix). Asserted portably (no hardcoded VARPTR address,
which would be fragile to any unrelated memory-layout change): compare the
stored value against a freshly re-evaluated `VARPTR` (the numeric case) or
assert a NEIGHBOUR element survived untouched (both cases). The task's own
suggested `MID$("XYZ",VARPTR(D),1)` string form does NOT work — a freshly
allocated scalar's address is a large-magnitude number that `MID$`'s position
argument rejects as out of `1..LEN(string$)` range (`Illegal function call`, an
unrelated argument-domain error) — `STRING$(3,VARPTR(D) AND 255)` sidesteps
that (any byte 0..255 is a valid charcode) while exercising the identical
hazard (a numeric `VARPTR` sub-argument nested inside the string RHS).

### Review coverage caveat
The first Fable pass was cut off by a session limit after confirming §13a. **A second
Fable pass (2026-07-17) completed hazards #4–#7 AND scrutinized the §13a fix code** —
result below. Coverage now closed.

## 13a-F1. FIXED — cold-boot wild write through an uninitialised PRGEND (SEVERE)

**Found by the second Fable pass; empirically proven; fixed + re-verified.** Slice-4b
added `call vars_reset` inside `clear_vars` (`basic/vars.asm`). `vars_reset` reads
`(PRGEND)` and — via its `ary_reset` fall-through — **writes a 2-byte `$0000` array
sentinel THROUGH `(ARYTAB)=(PRGEND)+2`**. At cold INIT (`interp.asm`) `clear_vars`
runs **before** `new_prog` sets `PRGEND`, so `PRGEND` still holds power-on RAM
garbage. Fable's debugger injection (`PRGEND=$FC48`, whose `+2` is HIMEM `$FC4A`)
showed the boot **zeroing HIMEM**. Also green-suite-invisible: openMSX zero-fills RAM
→ `PRGEND` reads `$0000`, the write lands at `$0002` (ROM, no-op) → every suite
passes; real hardware powers up with arbitrary RAM → sporadic boot corruption.

**Fix:** remove the `vars_reset` call from `clear_vars`. **Invariant (verified):**
every `clear_vars` caller resets the scalar+array regions itself AFTER establishing
`PRGEND` — init→`new_prog` (`jp vars_reset`), NEW→`jp new_prog`, `run_prog`/`ex_clear`
call `vars_reset` explicitly. So no reset is lost. Repack-only (lean keeps its own
128-byte `VARTAB` wipe → byte-identical). **Empirically re-verified FIXED:** the same
garbage-`PRGEND` injection now leaves HIMEM = the planted `$F380` sentinel (was
`$0000` pre-fix). Permanent non-vacuous regression guard:
`probes/basic/basic_probe_prgend_init.py` (re-adding the call turns it red).

## 13a-F2. DOCUMENTED — "edit clears all variables" was over-stated (LOW)

Q2/§7.1 claimed a program edit clears *all* variables (MSX-faithful). In 4b it clears
only the **numeric** scalar chain + arrays; **string scalars (the fixed `STRTAB`
pool) survive an edit** (`relink`→`vars_reset` touches only the numeric/array region).
So `A=5:A$="X"` + edit → `A` clears, `A$` persists — an interim divergence, resolved
by **4c** (string-scalar unification). Not a code bug; §7.1, §3b, and
`basic/PROVENANCE.md` corrected to state the interim behaviour precisely. The
`scalar.edit.clears` gate covers the numeric case only (a differential `A$`-edit case
would go red on this intentional interim state — deliberately not added).

## 13a — second-pass coverage (hazards #4–#7 + the §13a fix), all SOUND

The completed Fable pass traced the §13a fix helpers (`ary_snapshot_offset`/
`ary_apply_offset`/`ary_apply_offset_hl_sub`) instruction-by-instruction (stack
balanced every path; snapshot preserves HL/A/DE; both apply variants preserve A+DE;
OFFSET arithmetic wraparound-proof) and ran an 18-case empirical battery (two
`VARPTR`s in one RHS; GC-retry mid-RHS under heap churn; auto-dim before/after the
`VARPTR`; the string variant; int-typed element; genuine scalar OOM + OOM-during-RHS
at the gap boundary) — all clean. Confirmed SOUND: the anchor-site audit (all 5
array-base sites read `(ARYTAB)`; the 2 remaining `(PRGEND)+2` derivations are the
correct *scalar*-region base), register/flag clobber (IX **and** the newly-relevant
IY across `subrom_call` — no main-side IY holder spans a scalar-var call; FAC/ARGA/
`VS_INT_VAL` untouched by tenant+GC), `scv_alloc` (`dec sp`/`inc sp` 19/19/19, LDDR
high→low correct for the growing overlap, collision-checked before any move, zero-fill
width 2/4/8), reset completeness (every `PRGEND` writer funnels through `relink`/
`new_prog`), and boundaries (`CEND==FRETOP` rejected — consistent with `ary_alloc`).
