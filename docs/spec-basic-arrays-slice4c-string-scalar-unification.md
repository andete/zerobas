<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — Arrays slice 4c: string-scalar unification into the variable area

Status: **SIGNED OFF 2026-07-17 — READY TO IMPLEMENT.** All four §12 decisions
resolved: **Q1** = temp-descriptor-stack snapshot of the source before the target
alloc (H1 fix); **Q2** = reuse `elsize_from_type` (type 1 → 3) for the scalar stride;
**Q3** = Sonnet implements against this contract, then mandatory Fable adversarial +
empirical-injection review with the openMSX acceptance suites in the Definition of Done
([[gate-during-implementation]]); **Q4** = fix the H3 `FRETOP`-reset-on-edit body
reclamation in this slice (intrinsic to chain-resident string scalars). This is the *implementation
contract* for the final slice of the arrays/DIM arc: dissolve the fixed `STRTAB`
string-scalar pool (`$E240..$E268`) and relocate string scalars into the same
real-MSX contiguous variable chain that numeric scalars (4b) and arrays (1–3) already
inhabit, reaching the **faithful unified variable area** the charter commits to. 4c
was split out of 4b on purpose (4b §6, Q1-A) because it is the one change that
**re-touches the string-heap GC root set** — so it takes that hazard in isolation, per
the arc's hard-won "smaller slices" discipline (every slice hid ≥1 matrix-invisible
bug; 4a needed 4 Fable passes).

Builds on: [`spec-basic-arrays.md`](spec-basic-arrays.md) (arc + memory model A),
[`spec-basic-arrays-slice4a-string-heap.md`](spec-basic-arrays-slice4a-string-heap.md)
(the compacting heap + `[len][ptr]` descriptors + GC),
[`spec-basic-arrays-slice4b-scalar-reloc.md`](spec-basic-arrays-slice4b-scalar-reloc.md)
(the numeric scalar chain, `ARYTAB`, insert-and-shift, the §13a delta-correction), and
the sub-ROM tenant playbook ([`subrom-tenant-playbook.md`](subrom-tenant-playbook.md)).

Every address / routine below is cited to the current working-tree-clean tree
(HEAD `5989409`). The whole slice is **repack-only** (`IF ROM_BASE < $4000`); the lean
16 KB build keeps its inline `[len][bytes:32]` `STRTAB` slots byte-identical.

---

## 0. TL;DR + scope

Slice 4c moves string scalar variables out of the fixed high-RAM pool
`STRTAB $E240..$E268` (8 slots of `[name0][name1][len:1][ptr:2]`) and into the unified
contiguous chain, interleaved with numeric scalars:

```
$8001        PRGEND+2       (ARYTAB)          (ARYEND=$0000)  FRETOP        C
  | program text | scalars: num + str |  arrays  |  free gap   | string heap |
  +--------------+-------------------+----------+-------------+-------------+
     grows up ->   grows up ->        grows up ->              <- grows down
```

A string scalar becomes an ordinary chain entry `[name0][name1][type=1][len:1][ptr:2]`
— identical framing to a numeric entry, differing only in the value field's *size*
(3-byte heap descriptor vs 2/4/8-byte number). The `[len][ptr]` value **is already the
post-4a descriptor form** (4a made every string descriptor a uniform 3-byte
`[len:1][ptr:2]` — [`sub/strheap.asm:13`](../sub/strheap.asm)), so no data reshaping is
needed; only the *location* and the *root enumeration* change.

**What it delivers (the faithful endpoint):**
1. **The last fixed variable pool dissolves.** After 4c the variable area is the real
   MSX `TXTTAB→VARTAB→ARYTAB→…→FRETOP→HIMEM` model in full — string + numeric scalars
   in one table, exactly as stock MSX-BASIC, a string entry's value being its 3-byte
   descriptor.
2. **Resolves 4b's documented interim caveat** (4b §7.1 / F2): 4b clears *numeric*
   scalars + arrays on an edit but string scalars survived (still in the untouched
   fixed `STRTAB`). 4c makes string scalars chain-resident → they clear with the rest
   → the "edit clears **all** variables" faithful behaviour is reached.
3. **Removes the fixed 8-string-scalar cap**; string-scalar count becomes dynamic,
   bounded only by the shared free region / `HIMEM`. Frees the 40-byte `$E240..$E268`
   RAM window.

**What it costs / risks — the one hard interaction:** string-scalar descriptors are
now **GC roots living inside the chain**, so `strheap_gc`'s root enumeration must walk
the scalar chain instead of `STRTAB`; and a string-scalar **store that allocates a new
entry** shifts the array region (like any scalar alloc) and can trigger a heap GC — so
the *source* descriptor of a var-to-var copy must survive both the shift and the GC.
That is the load-bearing new hazard (§6, H1). Managed by the arc's standard discipline
(small slice, differential + adversarial + Fable + **empirical injection**, §9).

---

## 1. Current state (measured, post-4b)

Two facts define the starting line:

### 1a. Numeric scalars are already chain-resident (4b); string scalars are not

| Store | Span / anchor | Entry | Managed by |
|---|---|---|---|
| **Numeric + string arrays, numeric scalars** | chain `[PRGEND+2 → ARYTAB → ARYEND)` | scalar `[name0][name1][type][value:2/4/8]` stride `type+3`; array descriptors above `ARYTAB` | `sub/arrays.asm` tenant (`scv_find`/`scv_alloc`, `ary_*`) + `basic/vars.asm` glue |
| **String scalars** `STRTAB` (4c relocates) | fixed `$E240..$E268` (40 B), stride `STRENTSZ=5` | `[name0][name1][len:1][ptr:2]` × 8, descriptor at slot+2 | `basic/vars.asm` (`str_find`/`str_get_key`/`str_set_key`) + `sub/strheap.asm` GC |

- `ARYTAB` ([`sysvars.inc:434-435`](../basic/sysvars.inc)) is the live cell = scalar-region
  end = array base. Scalar base is derived `(PRGEND)+2`.
- `STRTAB` ([`sysvars.inc:448`](../basic/sysvars.inc)), `STRENTSZ`/`STREND`
  ([`sysvars.inc:458-466`](../basic/sysvars.inc)), `FRETOP equ STREND == $E268`
  ([`sysvars.inc:544`](../basic/sysvars.inc)). Only three routines touch `STRTAB` as a
  live address: `str_find` ([`vars.asm:707-739`](../basic/vars.asm)), the `cv_str` wipe
  ([`vars.asm:903-910`](../basic/vars.asm)), and `sg_walk_strtab`
  ([`sub/strheap.asm:606-628`](../sub/strheap.asm)).

### 1b. The descriptor + GC machinery 4c reuses (all shipped by 4a)

- **Uniform 3-byte descriptor** `[len:1][ptr:2]` everywhere
  ([`sub/strheap.asm:13,19`](../sub/strheap.asm)); `len==0` ⇒ never a root
  ([`sub/strheap.asm:25`](../sub/strheap.asm), `sg_inrange`).
- **`elsize_from_type`** ([`sub/arrays.asm:761`](../sub/arrays.asm)) already maps
  **type 1 → 3** (the heap descriptor size), identity for numeric 2/4/8, and
  **preserves BC,D,E,H,L, clobbers A only** — the exact primitive 4c needs for a
  variable-stride scalar walk.
- **GC root set today** ([`sub/strheap.asm:584-591`](../sub/strheap.asm), `sg_walk`):
  `sg_walk_strtab` (STRTAB slots) → `sg_walk_arrays` (type==1 array elements, already
  `(ARYTAB)`-anchored) → `sg_walk_temps` (temp-descriptor stack `[TEMPTOP,TEMPBASE)`).
- **Temp-descriptor stack** ([`sysvars.inc:612-623`](../basic/sysvars.inc)): downward
  `[len][ptr]` entries, **enumerated as roots** (so GC updates their ptrs), reset each
  statement. `RVDESC` ([`sysvars.inc:554-568`](../basic/sysvars.inc)) is a fixed scratch
  descriptor that is **NOT** a root.

### 1c. Space (measured this session, `build/basic-reloc.sym`)

`__MEAS_LOW_END == $3FF4` → **12 B free** low region; `__MEAS_PAGE1_END == $7FF0` →
**16 B free** page-1. As with 4a/4b, dissolving `STRTAB` and its dedicated
find/store/wipe machinery is expected to **reclaim** main-ROM bytes to offset the new
glue (§8, the shape-C thesis). Sub-ROM page-0 has ~12 KB free — the GC-walk change and
stride substitution land there with room to spare.

---

## 2. Target model

Adopt the fully unified real-MSX variable area. **No new sysvar** — `ARYTAB` already
marks scalar-end/array-base; string scalars simply join the region below it.

- **String scalar entry** `[name0][name1][type=1][len:1][ptr:2]`, **stride 6** (header
  3 + descriptor 3). Key `(name0,name1,type)` — a `$` name resolves to type 1 via the
  existing `var_str_type` ([`vars.asm`], the slice-2 `$`≡type-1 unifier), so `A`, `A%`,
  `A!`, `A#`, `A$` are five distinct entries (arrays §4.1 #7, already how numeric types
  key). The value field (descriptor) sits at **entry+3** — one byte later than today's
  `STRTAB` slot+2, because the chain entry carries the explicit `type` byte a dedicated
  string pool omits.
- **Stride is per-entry** = `elsize_from_type(type) + 3`: numeric 2/4/8 → 5/7/11 (identity
  with today's `type+3`), string type 1 → **6**. This single substitution unifies the
  walk.
- **Find is find-only** (a *read* of an unset string var must NOT create it — real MSX
  and today's `str_get_key`→`STR_EMPTY` both do this); **alloc is find-or-insert** (a
  *store* creates on miss). Same split numeric scalars already use (`ARY_OP` 4 vs 5).

---

## 3. The core mechanism

### 3a. Unify the entry stride (the `elsize_from_type` substitution)

The 4b tenant's `scv_find` ([`sub/arrays.asm:376-432`](../sub/arrays.asm)) and
`scv_alloc` ([`sub/arrays.asm:451-605`](../sub/arrays.asm)) compute stride as raw
`type+3` ([`sub/arrays.asm:487`](../sub/arrays.asm) and the `scvf_lp` advance
`:414-429`). 4c routes both through **`elsize_from_type`** so a type-1 entry strides by
6 not 4. Because `elsize_from_type` is identity for numerics, **numeric behaviour is
byte-for-byte unchanged**; the map is already a co-resident in-page sibling
(`ary_stride`/`ary_alloc` already call it), preserves the registers the stride loop
needs, and clobbers only A. Net: `scv_find`/`scv_alloc` become **type-agnostic** — they
already take `(key, type)` in the `ARY_*` block, so with the stride fix they serve
string scalars with **no new op-code** (the same `ARY_OP` 4/5 the numeric glue uses,
now called with type=1).

### 3b. Replace `sg_walk_strtab` with a scalar-chain string walk (the GC crux)

`sg_walk` ([`sub/strheap.asm:588-591`](../sub/strheap.asm)) changes its first pass from
`sg_walk_strtab` (fixed `STRTAB`) to **`sg_walk_scalars`**, modelled directly on the
sibling `sg_walk_arrays` ([`sub/strheap.asm:633-684`](../sub/strheap.asm)) which already
walks a `(ARYTAB)`-anchored, type-filtered, `elsize_from_type`-strided region:

```
sg_walk_scalars:
    HL = (PRGEND)+2                 ; scalar-region base (derived, as scv_find does)
loop:
    HL == (ARYTAB)?  -> ret         ; reached array base -> every scalar scanned
    A = (HL+2)       ; type byte
    if A == 1:                      ; string scalar
        sg_visit(HL+3)              ; descriptor = entry+3 (NOT +2 as in STRTAB)
    HL += elsize_from_type(A) + 3   ; this entry's stride
    jr loop
```

- End-test is **byte-wise against `(ARYTAB)`**, mirroring `scv_find`'s deliberate
  no-`ld de,(ARYTAB)` to avoid clobbering the walk registers
  ([`sub/arrays.asm:382-396`](../sub/arrays.asm)).
- Descriptor offset is **entry+3** (past `[name0][name1][type]`), vs `sg_walk_strtab`'s
  slot+2 — the single most bug-prone byte in the slice (a stale +2 would visit the
  `type` byte as a `len`, corrupting compaction). Gate it directly (§9).
- `sg_visit`/`sg_inrange`/`sg_walk_arrays`/`sg_walk_temps` are **unchanged**. Numeric
  scalars are skipped by the `type==1` filter and never look like roots.
- This is invoked by `strheap_gc` under DI, from `heap_alloc` (string body store) and
  `ary_alloc`/`scv_alloc` (chain-full retry). At every such point the scalar chain is
  a consistent stride-walkable region — including mid-`scv_alloc`, where the collision
  GC runs **before** the new entry is written (§3d, the ordering that keeps the walk
  seeing only complete entries; a just-allocated entry's descriptor is zero-filled →
  `len==0` → inert, the 4a BUG-B invariant now structural via `scv_alloc`'s zero-fill).

### 3c. Retarget find/store from `STRTAB` to the chain (main-ROM glue shrinks)

The three `basic/vars.asm` string routines become thin glue over the existing
`ary_engine_call` + `ary_errmap` ([`basic/arrays.asm:285,311-321`](../basic/arrays.asm)),
exactly as 4b did for the numeric `var_find_typed`/`var_alloc_or_find`:

- **`str_find`** ([`vars.asm:707-739`](../basic/vars.asm)) — **deleted**; its callers use
  the tenant scalar-find. (~30 B main reclaim.)
- **`str_get_key`** ([`vars.asm:745-754`](../basic/vars.asm)) — set `ARY_KEY`=BC,
  `ARY_TYPE`=1, `ARY_OP`=4 (find), `ary_engine_call`; `ARY_ADDR`==0 (miss) → `HL=STR_EMPTY`;
  else `HL = ARY_ADDR + 3` (descriptor). Stays **find-only** (read never allocates).
- **`str_set_key`** ([`vars.asm:770-847`](../basic/vars.asm)) — `ARY_OP`=5 (alloc),
  type=1 → `ARY_ADDR` (new-or-existing entry); dest descriptor = `ARY_ADDR+3`; then the
  **unchanged** sub-side `sh_var_store` (op=12, [`sub/strheap.asm:1627-1653`](../sub/strheap.asm))
  heap-allocs the body copy and writes `[len][ptr]`. `ssk_new`'s manual name-write +
  the BUG-B len-zeroing ([`vars.asm:781-800`](../basic/vars.asm)) are **subsumed** by
  `scv_alloc` (it writes the name and zero-fills the value → `[len=0][ptr=0]`, an inert
  empty-string descriptor — BUG-B protection is now structural). **But** the source
  descriptor must be protected across `scv_alloc` — see §6 H1 (the one place this is not
  a mechanical port).
- `STR_EMPTY` ([`vars.asm:754`](../basic/vars.asm)) is retained (miss sentinel).

The lean build keeps its inline-slot `str_find`/`ssk_store` bodies unchanged (all 4c
edits are `IF ROM_BASE < $4000`).

### 3d. Reset — string scalars clear for free (resolves the 4b caveat)

String scalars now live in `[PRGEND+2, ARYTAB)`, so `vars_reset` (`ARYTAB=PRGEND+2`,
[`basic/arrays.asm:120-125`](../basic/arrays.asm)) — already chained from
`new_prog`/`run_prog`/`ex_clear`/`relink` — clears them with the numeric scalars and
arrays. The dedicated `cv_str` `STRTAB` wipe ([`vars.asm:903-910`](../basic/vars.asm))
is **deleted**. This is the change that reaches full faithfulness (edit clears **all**
vars). **Correctness rider (H3, §6):** the string *bodies* those scalars owned must be
reclaimed too — confirm `FRETOP` is reset to the ceiling (heap emptied) on the same
clear/edit paths, else bodies leak until the next GC (a leak, not corruption, but must
be characterised).

---

## 4. Region / placement — the shape-C split

4c is a **shape-C** feature like 4a/4b: pure-RAM pointer/memory bulk → the page-0
sub-ROM tenants; thin marshalling glue main-side.

| Piece | Home | Notes |
|---|---|---|
| `elsize_from_type` stride substitution in `scv_find`/`scv_alloc` | **ARY tenant** ([`sub/arrays.asm`](../sub/arrays.asm)) | in-page `call`, no ABI change; numeric identity preserved |
| `sg_walk_scalars` (replaces `sg_walk_strtab`) | **string-heap tenant** ([`sub/strheap.asm`](../sub/strheap.asm)) | in-page `call elsize_from_type` sibling (co-resident, like `sg_walk_arrays`→`ary_stride`) |
| `str_get_key`/`str_set_key` → `ARY_OP` 4/5 glue; source-protect (H1) | **main** ([`vars.asm`](../basic/vars.asm)) | reuses `ary_engine_call`/`ary_errmap` verbatim |
| `sh_var_store` body copy | **string-heap tenant** (unchanged) | op=12 already exists |
| `cv_str` deletion; `str_find` deletion | **main** | reclaim |

**No new `SUBROM_IDX`, no new `ARY_OP`, no new param block.** String-scalar find/alloc
*is* numeric-scalar find/alloc with type=1 once the stride is `elsize_from_type`-driven.
**Tenant closure** holds by construction: `sg_walk_scalars` touches only read-only
sysvars (`PRGEND`, `ARYTAB`), the scalar RAM region, and the in-page `elsize_from_type`
/`sg_visit` siblings — no main-page call (still passes `check_tenant_closure.py`).

---

## 5. What changes, by file

- [`basic/sysvars.inc`](../basic/sysvars.inc) — retire the `STRTAB`/`STRENTSZ`/`STRSLOTS`/
  `STREND`-as-pool equates on the repack path; the 40 B `$E240..$E268` window is freed
  RAM. Keep `FRETOP` as its own live cell at `$E268` (it no longer needs to alias
  `STREND`). Lean equates untouched.
- [`basic/vars.asm`](../basic/vars.asm) — delete `str_find` (707-739) and `cv_str`
  (903-910, repack); rewrite `str_get_key` (745-754) + `str_set_key` (770-825, repack
  body) as `ARY_OP` 4/5 glue + the H1 source-protect; `ssk_new`/BUG-B block removed
  (subsumed). Lean bodies unchanged.
- [`sub/arrays.asm`](../sub/arrays.asm) — `scv_find` (414-429 stride advance) + `scv_alloc`
  (487 `STRIDE=type+3`) route through `elsize_from_type`. No dispatch change.
- [`sub/strheap.asm`](../sub/strheap.asm) — replace `sg_walk_strtab` (606-628) with
  `sg_walk_scalars` (§3b); `sg_walk`'s first `call` retargeted. Verify `FRETOP` reset (H3).
- [`basic/arrays.asm`](../basic/arrays.asm) — no change expected (`vars_reset` already
  clears the whole scalar region); confirm only.
- [`basic/strvar.asm`](../basic/strvar.asm) / [`basic/str-engine.asm`](../basic/str-engine.asm)
  — callers of `str_get_key` (`str_eval_one` strvar.asm:89-91; MID$-stmt str-engine.asm:866-867)
  are **format-agnostic** (they consume the returned descriptor address) → unchanged, but
  re-audit the MID$-stmt dest-held-across-`str_eval` window under H1.

---

## 6. Hazards (the arc's load-bearing section — every prior slice hid a matrix-invisible bug here)

**H1 — stale SOURCE descriptor across the target alloc (the new, 4c-specific bug; SEVERE, silent).**
`str_set_key` today marshals `SH_SRC = DE` where `DE` "may point into `STRTAB` / an array
element / a temp entry / RVDESC" and is documented *STABLE* only because `STRTAB` slots
never move ([`vars.asm:759,804-806`](../basic/vars.asm)). After 4c, `ssk_new`→`scv_alloc`
**shifts the array region up** and, on a `FRETOP` collision, **runs `strheap_gc`
(compaction moves heap bodies)**. So for `A$ = <source>` where `A$` is *new*:
- source = **string-array element** (`A$=S$(0)`): the shift moves its descriptor address
  → `SH_SRC` stale (address).
- source = **RVDESC** (`A$=<concat/fn result>`): RVDESC is fixed-address (shift-safe) but
  **not a GC root** → a collision GC compacts the body it points at → `SH_SRC` stale
  (body ptr).
- source = **existing string scalar** (`A$=B$`): SAFE — existing scalars sit *below* the
  insertion point (`scv_alloc` inserts at `ARYTAB`), so their address is stable, and they
  *are* roots, so GC updates their ptr in place.
- source = **temp-stack entry**: SAFE — fixed address AND a root.

Both green-suite-invisible (need `A$` fresh **and** memory near `FRETOP` to force the GC).
**Recommended fix:** before `scv_alloc`, **snapshot the 3-byte source descriptor onto the
temp-descriptor stack** (fixed address ⇒ shift-immune; enumerated root ⇒ GC-immune — it is
exactly the mechanism 4a's concat already uses for operands), point `SH_SRC` at it, pop
after the store. Covers all source kinds uniformly with no address arithmetic. Alternative
(delta-correct `SH_SRC` by the `ARYTAB` shift + rely on in-place GC update) is more fragile
and rejected. **Must be Fable-reviewed + empirically injected** (fill RAM to force the
collision GC), not cleared by static reasoning — the standing arc rule.

**H2 — array-element LHS stale across a mid-eval STRING-scalar alloc (the §13a class, generalised).**
4b's §13a fix (snapshot `ARYTAB` pre-eval, correct the element addr by the `ARYTAB` delta
post-eval; [`vars.asm:552-593`](../basic/vars.asm), sites [`arrays.asm:608,629,795,817`](../basic/arrays.asm))
fires for `A(0)=…` / `S$(0)=…` when the RHS eval allocates a scalar. The only mid-eval
scalar allocator is `VARPTR`. **Audit + verify:** (a) does `VARPTR(A$)` on an unset string
var force-allocate a string scalar (⇒ a shift)? (b) if so, does the existing delta-correction
fire for a **string**-triggered shift (it keys on the `ARYTAB` delta regardless of cause, so
it *should*, but this is precisely the kind of "cleared by static reasoning" trap that bit
4b twice). Empirically inject `DIM S$(1):S$(0)=VARPTR(A$):PRINT S$(0)`-shaped cases.

**H3 — orphaned string bodies on edit/CLEAR (leak, not corruption).** §3d clears string
scalars via `vars_reset`; confirm the same paths reset `FRETOP` to the ceiling so their
heap bodies are reclaimed (real-MSX empties string space on CLEAR / program edit). Add a
gate that allocates strings, edits, and checks free string space recovers.

**H4 — lean byte-identity.** All 4c edits are `IF ROM_BASE < $4000`; the lean build's
inline-slot store path is untouched. Re-assert the lean SHA-256 (`e21f61fe…`) unchanged.

**H5 — standard register/`IX` clobber + zero-fill width + `ARYTAB` consistency** across
the new `sg_walk_scalars`, the `elsize_from_type` calls inside the stride loops, and the
retargeted `str_get_key`/`str_set_key` `subrom_call` (guard `IX`/the token cursor as the
callers require). The `sg_walk_scalars` **entry+3 descriptor offset** is the specific
byte to prove (a `+2` regression corrupts every GC).

---

## 7. Behaviour / faithfulness deltas (all deliberate, all documented)

1. **Edit / RUN / CLEAR now clears string scalars too** — resolves the 4b §7.1 interim
   inconsistency; the "edit clears **all** variables" endpoint is reached. **Now ADD**
   the differential `A$`-edit case 4b's spec explicitly told us to *withhold* (it would
   have gone red on the interim state; it goes green now).
2. **`VARPTR(A$)` addresses now move** (a later scalar's creation shifts nothing below
   `ARYTAB`, but string-array/element consumers and VARPTR are subject to the same
   "valid until the next variable is allocated" rule as numeric — stock MSX semantics;
   today's fixed pool made it accidentally stable). Gate asserts the value at the
   returned address immediately, not the address.
3. **String-scalar count is dynamic** (was fixed 8), bounded by the shared free region /
   `HIMEM`; table-full silent-drop → `Out of memory` (matches array/numeric-scalar OOM).
4. **Lean build byte-identical.**

---

## 8. RAM + ROM space

- **RAM: +40 B freed** (`$E240..$E268` `STRTAB` pool dissolves; string scalars share the
  `$8001..HIMEM` chain, no fixed cost). No new sysvar (reuses `ARYTAB`, the `ARY_*` block,
  the temp stack).
- **ROM (main): predicted net-neutral-to-positive** (shape-C). Removed: `str_find`
  (~30 B), `cv_str` (~8 B), `ssk_new`+BUG-B (~15 B), the fixed-`STREND` room-check.
  Added: `str_get_key`/`str_set_key` `ARY_OP` glue (~30–45 B) + the H1 temp-stack
  source-protect (~12–16 B). Target **≥ 0 main-ROM delta**, measured via
  `__MEAS_LOW_END`/`__MEAS_PAGE1_END` (start: **12 B low / 16 B page-1**). The
  `sg_walk_scalars` change and the `elsize_from_type` substitution land **sub-side**
  (page-0, ~12 KB free) — not in the tight main regions. If the H1 glue overflows page-1,
  the reclamation ladder is [`decision-arrays-slice4-space.md`](decision-arrays-slice4-space.md)
  §5.2 (cold-page-1 eviction) — not expected.

---

## 9. Gate plan

**Differential** (VG-8020 ref vs repack, `probes/lib/omsx_repl.py`; extend `array-acceptance`):
- String-scalar round-trips across create/reassign/grow/shrink; **many** string scalars
  (formerly capped at 8 → now succeed) interleaved with numeric scalars and arrays;
  assert *contents* survive scalar-triggered shifts (content, not length — the 4a lesson).
- **H1 battery:** `A$=S$(0)`, `A$=B$+C$`, `A$=A$` (self), each with `A$` **fresh** and RAM
  filled near `FRETOP` to force the collision GC during the target alloc; assert the copied
  value is correct (a stale source silently yields garbage).
- **H2 battery:** `VARPTR(A$)` in an RHS that stores to an array element; value-at-address
  check.
- **GC-root correctness:** build several string scalars + string arrays + temps, force a GC
  (large concat), assert *every* string variable's content survives (proves `sg_walk_scalars`
  enumerates the chain roots at the right `entry+3` offset). A revert of the `+3`→`+2` must
  turn this red (non-vacuous).
- **Edit-clears-all:** `A$="X":A=5` in direct mode, edit a line, confirm **both** cleared
  (the new faithful behaviour; the case 4b withheld).
- **H3:** allocate strings, edit/CLEAR, confirm free string space recovers.
- **OOM:** exhaust the chain with string scalars → `Out of memory` (not silent drop).
- **Disk-interleaved heavy churn** (the 4a S6 lesson): a scalar-shift GC must not corrupt
  disk work-area RAM.

**Adversarial + Fable review** (mandatory — *every* slice hid a matrix-invisible bug; run
**both** passes to completion): H1 source lifetime across shift+GC, H2 delta-correction
firing for string-triggered shifts, the `entry+3` offset, `sg_walk_scalars` stride/end-test,
register/`IX` clobber, `FRETOP` reset. **Empirical injection is load-bearing**, per the arc's
hardest lesson (4b's two severe bugs were both cleared by my flawed static reasoning and
caught only by live-debugger injection).

**Standing gates:** `check_tenant_closure` (both tenants), `subrom-abi-check`,
`__MEAS_LOW_END`/`__MEAS_PAGE1_END` (prove ≥0 main delta), lean SHA-256 byte-identity,
full `make array-acceptance` + `make string-acceptance`, `make unit-test`.

**Host unit tests** (`tests/`, emulator-free): `sg_walk_scalars` stride/offset walk and the
`elsize_from_type`-driven `scv` stride as pure-Z80 tests, proven non-vacuous (revert → red).

---

## 10. Provenance

Clean-room. The unified variable table (string + numeric scalars in one chain, a string
entry's value being its `[len][ptr]` descriptor) is zerobas's own realisation of the
**documented** MSX memory model (`TXTTAB→VARTAB→ARYTAB→…→FRETOP→HIMEM`), reusing our own
`scv_*`/`elsize_from_type`/`strheap_gc` machinery. No disassembly; the model is a published
contract (MSX2 Technical Handbook / MSX Assembly Page). Note in `basic/PROVENANCE.md`
§variable area (extend the 4b entry: the fixed `STRTAB` pool is retired).

---

## 11. Slices boundary — the arc ends here

4c is the **final** slice of the arrays/DIM arc. After it, the variable area is the
faithful unified real-MSX chain in full; no fixed variable pool remains. The arc's
remaining Phase-3 neighbours (graphics, sound, error handling, …) are separate tracks.

---

## 12. Sign-off decisions (please confirm before implementation)

- **Q1 — H1 source-protect mechanism:** temp-descriptor-stack snapshot of the source
  before the target alloc (**recommended** — structural, reuses 4a's concat machinery,
  no address arithmetic), vs `ARYTAB`-delta correction of `SH_SRC`. *Recommend: temp-stack.*
- **Q2 — stride unification:** reuse `elsize_from_type` (type 1 → 3) in `scv_find`/`scv_alloc`
  (**recommended** — one substitution, numeric identity preserved), vs a separate scalar
  valsize map. *Recommend: reuse.*
- **Q3 — implementation split:** Sonnet implements against this contract, then the mandatory
  Fable adversarial + empirical-injection review ([[opus-vs-sonnet-model-split]],
  [[spec-before-implementation]], [[gate-during-implementation]] — the acceptance suites
  are part of the Definition of Done, not a post-hoc check). *Recommend: yes.*
- **Q4 — H3 (`FRETOP` reset on edit/CLEAR):** confirm whether to characterise + fix any
  body-leak in this slice or split it (it is a leak, not corruption). *Recommend: fix here
  — it is intrinsic to making string scalars chain-resident.*
