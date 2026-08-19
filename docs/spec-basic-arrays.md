<!-- Provenance: original work (own-design spec). Array *semantics* (DIM syntax,
subscript ranges, auto-dimensioning, OPTION BASE, error messages, ERASE) are
oracle-locked to the public MSX-BASIC language reference + black-box VG-8020
capture; token values to published tables (MSX2 TH Table 2.20 / MSX Assembly
Page) + the VG-8020 crunch. The array *descriptor byte layout* is zerobas's OWN
design (as VARTAB/STRTAB already are) — never ROM disassembly (see PROVENANCE.md,
[[no-reference-rom-disasm]]). -->
# Spec — BASIC arrays + `DIM` (dynamic-allocator arc)

**Status: 🟢 SCOPE SIGNED OFF (2026-07-14).** Direction ratified by the
user: **memory model = A, the real MSX dynamic allocator** (not a
fixed pool), built as a **multi-slice arc**; slice 1 = the allocator + **numeric
arrays only** (the smallest end-to-end proof). The §7 open questions are **all
signed off at the recommended defaults** (Q-A1 slice-1 cut = allocator + numeric,
base 0, no ERASE/OPTION; Q-A2 anchor `ARYTAB` at program-end, ceiling
`min(HIMEM,$BE00)`; Q-A3 slice-1 lvalues = `LET` + expression rvalue, FOR/READ/
INPUT fold in cheaply-or-slice-2; Q-A4 keep scalars/strings in fixed pools through
slices 1–3, unify in slice 4; Q-A5 include multi-dim in slice 1). This doc covers
the arc scope, the target memory model, the slice-1 cut, the reference-semantics
campaign, and (now-resolved) sign-off questions. **Oracle characterization DONE
(§4.1/§5, 2026-07-14)** — all semantics + token pins captured on the stock
VG-8020; headline finding: `OPTION BASE` is unsupported on MSX1 (dropped from the
arc; arrays are permanently base 0). Next = the slice-1 implementation contract;
each sub-slice still gets its own concrete contract + Fable review before its own
code, exactly as the float pack, string engine, and math pack slices did.

Builds on: the typed-variable store ([spec-basic-float-core.md](spec-basic-float-core.md)
§11, F3), the string engine ([spec-basic-string-engine.md](spec-basic-string-engine.md)),
and `CLEAR`/HIMEM ([basic/clear.asm](../basic/clear.asm)). Repack build only
(`IF ROM_BASE < $4000`); the lean 16 KB `basic.rom` stays byte-identical.

---

## 1. Scope

Arrays are the last foundational piece of the core interpreter and are **verified
greenfield** (2026-07-14): no `DIM`/`ERASE`/`OPTION` keyword, no array token, no
subscript parsing, and no array store exist. Referencing `A(1)` today is a syntax
error.

The arc delivers the full DOS1-class MSX-BASIC array surface:

- **`DIM`** — declare arrays, numeric (each type `%`/`!`/`#`) and string, single-
  and multi-dimensional.
- **Subscripting everywhere a variable can appear** — `A(i)` / `A(i,j)` as an
  lvalue (`LET`, `FOR`, `READ`, `INPUT`, `MID$`, `LSET`/`RSET`, file `INPUT#`)
  and as an rvalue (any expression factor).
- **Auto-dimensioning** — referencing an undeclared array auto-declares it with an
  upper bound of 10 per dimension (oracle-confirmed, §4.1).
- **`ERASE`** — free arrays (and permit re-`DIM`).
- ~~`OPTION BASE`~~ — **dropped**: MSX-BASIC 1.0 has no such statement (§4.1);
  arrays are permanently base 0.
- Reference error surface — `Subscript out of range`, `Redimensioned array`,
  `Out of memory`, plus the existing `Syntax error` for malformed forms.

### 1.1 Why this forces the memory-model decision (the ratified fork)

zerobas's variable store is **fixed pools** in the C-BIOS work area: scalars in a
pinned 128 B span (`VARTAB $E1C0..$E240`), strings in the `$E240..$E560` window
that ends *exactly* at the disk `WBUF` boundary — the sysvars comment records "no
spare byte left." The only sizable clean-RAM hole ($EA00..$EE63, ~1.1 KB) is the
file-channel buffers (`FCH_CTX`). And `$C000..$E000` is the **BLOAD target
region** — where the game-loader binaries this BASIC exists to load actually land
(sysvars.inc line 314). **There is no free window for an array pool.** A fixed
array pool (option B) is therefore both cramped and throwaway; the user chose the
dynamic allocator (option A) — the same re-architecture the string engine deferred
(STRMAX→255, string-engine §5a). Doing it now is the shared foundation that
arrays, string arrays, and the deferred string widening all sit on.

---

## 2. Target memory model — the real MSX bottom-up allocator

MSX-BASIC (and MS-BASIC generally) grows **program text → simple variables →
arrays → free space** upward from the text base, with the string space + stack
descending from the top; the boundary is **HIMEM**, which `CLEAR` sets. Pointer
chain (names/addresses from MSX2 TH work-area appendix / MSX Assembly Page —
allowed sources, the same provenance as `TXTTAB`; to be pinned in sysvars.inc,
not asserted here):

```
$8001  TXTTAB ─▶ [ program text .......... ] 0000
              VARTAB ─▶ [ simple variables ]
              ARYTAB ─▶ [ array area ...... ]
              STREND ─▶ [ === free RAM === ]
                              ...
                        [ string space ] (descends)   ← slice N
                        [ stack ]
       HIMEM  ─▶  ceiling (CLEAR sets it; default just below the work area)
```

**The load-bearing consequence for game loaders.** A loader stub does
`CLEAR 200,&HBFFF : BLOAD"GAME",R` — the `CLEAR` lowers HIMEM below the high
BLOAD blob so the variable/array area cannot grow into it. zerobas already parses
this and records HIMEM ([basic/clear.asm](../basic/clear.asm):70) **record-only**;
the comment there already anticipates "a future … variable mover would read it."
This arc makes HIMEM the **real allocator ceiling** — the mechanism that keeps
arrays from colliding with a loaded game. This is why the model is correct for the
charter, not just for completeness.

### 2.1 Own-design descriptor, oracle-locked semantics (clean-room line)

The **byte layout** of an array descriptor (how name/type/dimension-bounds/element
data are packed) is **zerobas's own choice**, exactly as VARTAB and STRTAB layouts
already are ([basic/vars.asm](../basic/vars.asm) header; PROVENANCE.md). Only the
**observable semantics** are oracle-locked to the CF-3300/VG-8020: element values,
subscript ranges, error messages/points, DIM/ERASE/OPTION syntax, multi-dimensional
element *ordering as observed through VARPTR* if in scope. The reference ROM's
internal array format is **never** read or disassembled ([[no-reference-rom-disasm]]).

Proposed own-design descriptor (slice 1, refined in the slice-1 contract):

```
[name0:1][name1:1][type:1][ndim:1][bound0:2]...[boundK:2][element data ...]
```

where `type` reuses the F3 type byte (2/4/8; string = a later slice), `ndim` is the
dimension count, each `boundK` is the inclusive upper subscript, and element data is
row-major, `elsize = type` bytes per element (`2/4/8`), count = Π(boundK − base + 1).

---

## 3. Slice-1 cut — allocator + numeric arrays

**Goal:** the smallest end-to-end path that proves the dynamic allocator with a
real, RAM-bounded array — deliberately mirroring how each prior arc shipped its
thinnest vertical slice first.

### 3.1 In scope (slice 1)

- A growing **array area** anchored at the top of the stored program
  (`ARYTAB = ` program-end pointer at RUN) and bounded above by the allocator
  ceiling (§3.3). Arrays bump-allocate here; capacity is RAM-bounded (tens of KB
  for a small program), **not** a fixed tiny pool — this is the "dynamic
  allocator" the fork chose.
- **`DIM A(n)`** and **`DIM A(n1,n2[,…])`** for numeric types (`%`/`!`/`#` +
  DEFtbl default), including several arrays in one `DIM` (comma-separated).
- **Subscripted rvalue + lvalue** for numeric arrays: `X=A(i)`, `A(i)=X`,
  `A(i,j)=…`, in `LET` and any expression factor. FOR/READ/INPUT lvalue targets
  and `VARPTR(A(i))` — scoped to confirm (§9 Q-A3).
- **Auto-dimensioning to bound 10** on first reference of an undeclared array
  (oracle-confirmed).
- Errors: **`Subscript out of range`** (index < base or > bound, or wrong
  dimension count), **`Redimensioned array`** (a second `DIM` of a live array),
  **`Out of memory`** (allocation would cross the ceiling). Exact messages +
  raise-points oracle-locked.

### 3.2 Deferred to later slices (arc roadmap)

- **Slice 2 — `ERASE`.** Array freeing (also enables clean re-DIM). Small,
  self-contained. (`OPTION BASE` was originally paired here but is **dropped** —
  §4.1: unsupported on MSX1; base 0 is hardcoded in slice 1 permanently.)
- **Slice 3 — string arrays.** `DIM A$(n)`; each element is a string value. Ties
  into the string store; may ride the STRMAX-widening decision.
- **Slice 4 — scalar/string relocation into the contiguous model + STRMAX→255.**
  Move simple variables and strings out of the fixed `$E1C0`/`$E240` pools into the
  `VARTAB→ARYTAB` chain so the whole variable space is one HIMEM-bounded region;
  unlocks STRMAX→255. The largest slice; the reason slice 1 keeps scalars/strings
  in their current fixed pools (decoupling arrays from scalar relocation).

### 3.3 Slice-1 RAM placement

Slice 1 keeps scalars (`VARTAB $E1C0`) and strings (`$E240`) in their current
fixed high-RAM pools **untouched**, and gives the array area the **low free
region**: `ARYTAB` = the stored program's end pointer (right after the `$0000`
line-link terminator), growing up toward the ceiling. Candidate ceiling =
`min(HIMEM, DETOKBUF $BE00)` — i.e. arrays share the `$8001..$BE00` span with the
program text exactly as the real model shares it, and a loader's `CLEAR ,&Hxxxx`
tightens it. This gives arrays real room while never touching the `$E1xx` work-area
pools or the `$C000` BLOAD region. (Confirm the ceiling interaction with DETOKBUF
and a high BLOAD in the slice-1 contract — §9 Q-A2.)

Because RUN/CLEAR already clears all variables, the array area is empty at program
start and the program-end anchor is stable for the RUN's duration (edits happen
only at the REPL, which re-clears) — so no mid-run array-block relocation is needed
in slice 1.

---

## 4. Reference-semantics campaign (to characterize, per sub-slice)

Black-box on the **VG-8020** (numeric arrays are diskless-testable) via the
KEYBUF-injection REPL driver, promoted into the slice's gate. Observed outputs
only; the ROM is a black box. Targets to pin (expected contract from the public
language reference, to be **confirmed**, not asserted):

1. **Default upper bound** on auto-dim — expected 10 (elements 0..10). Confirm the
   value and that it is per-dimension.
2. **`OPTION BASE`** — lower bound 0 (default) or 1; error if set after any DIM;
   `OPTION BASE 2`+ illegal. (Slice 2, but capture now.)
3. **Subscript-out-of-range** boundaries — is `A(n)` for the declared `n` legal
   (inclusive upper)? negative index? wrong dimension count vs declared?
4. **`Redimensioned array`** — second `DIM` of a live array; is it the DIM
   statement or the auto-dim that a later DIM collides with?
5. **Element ordering / multi-dim** — the arithmetic that maps `(i,j)` to a linear
   offset (row-major vs column-major), observed via values only (and VARPTR if in
   scope). MSX is column-major (left subscript varies fastest) — **confirm**.
6. **Auto-init** — fresh numeric array elements read as 0 (expected, matches scalar
   auto-init).
7. **Type independence** — do `A(10)` and `A%(10)` and `A$(10)` coexist as distinct
   arrays (as `A`/`A%`/`A$` scalars do)?
8. **`ERASE`** semantics + errors (`Illegal function call` on erasing an
   undeclared array?). (Slice 2.)
9. **`Out of memory`** onset — the raise point when an array would overflow the
   ceiling.

---

## 4.1 Characterization results — VG-8020 stock MSX-BASIC 1.0 (2026-07-14)

Black-box on the stock `Philips_VG_8020` (real MSX-BASIC 1.0) via the KEYBUF REPL
driver; observed outputs only, no ROM disassembly. All §4 targets **confirmed**:

| # | Behaviour | Observed (VG-8020) | Pin |
|---|---|---|---|
| 1 | Auto-dim default upper bound | `A(10)=9` ok; `A(11)` → error | **10** (elements 0..10), per dimension |
| — | Auto-dim onset | `A(5)=1 : A(10)` → 0 | first touch of any index auto-dims all dims to 10 |
| 2 | **`OPTION BASE`** | `OPTION BASE 1` → **`Syntax error`** | **NOT supported on MSX1** — arrays are permanently base 0. Drops the slice-2 OPTION item. |
| 3 | DIM upper bound | `DIM B(5):B(5)` ok; `B(6)` → error | **inclusive** upper |
| — | Lower bound | `DIM B(2):B(0)=7` → 7 | **base 0** always |
| 4 | Re-DIM | `DIM B(3):DIM B(3)` → | **`Redimensioned array`** |
| 5 | Multi-dim value | `DIM C(2,3):C(1,2)=5` → 5 | row/col mapping is internal (own-design); only value correctness observed |
| — | Multi-dim inclusive | `DIM C(2,3):C(2,3)` → 0 | valid up to `(2,3)` inclusive |
| — | Wrong dimension count | `DIM C(2,3):C(1)` → | **`Subscript out of range`** |
| 6 | Auto-init | `DIM B(3):B(2)` → 0 | fresh elements = 0 |
| 7 | Type independence | `A(1)=11 : A%(1)=22` → `11,22` | `A()`/`A%()`/`A$()` are **distinct arrays** (as scalars are) |
| — | Multiple arrays / DIM | `DIM P(2),Q(3)` → both live | comma-separated list in one `DIM` |
| — | Float/typed elements | `DIM D(3):D(1)=1.5` → 1.5 | element holds the resolved type's value |
| — | String array | `DIM S$(3):S$(1)="HI"` → `HI` | slice 3 |
| 8 | Over-bound at runtime | `A(11)` / `B(6)` → | **`Subscript out of range`** |
| 9 | **Negative subscript** | `DIM B(5):B(-1)` → | **`Illegal function call`** — NOT "Subscript out of range" |

**Consequences for the arc.**
- **`OPTION BASE` is dropped** (§1, §3.2): the reference has no such statement, so
  there is nothing to be reference-compatible *with*. Arrays are base 0, hardcoded.
  Slice 2 becomes **`ERASE` only**.
- **Two distinct error dispositions** the slice-1 evaluator must produce: an
  in-range-violation is `Subscript out of range`, but a **negative** index is
  `Illegal function call` (index < 0 is caught before the bound compare).
- **Wrong dimension count** (fewer/more subscripts than the array's `ndim`) is
  `Subscript out of range`, not a syntax error.

---

## 5. Token pinning — captured (2026-07-14)

Per the established discipline (math-pack §6, string-engine): every new keyword's
token is captured from the **VG-8020 crunch** and cross-checked against **MSX2 TH
Table 2.20 / MSX Assembly Page** — never asserted from memory, never from ROM
disassembly. Captured crunch bytes (stock VG-8020, stored-line dereference):

| Word | Crunch bytes | Token |
|---|---|---|
| `DIM A(5)` | `86 20 41 28 16 29 00` | **`DIM` = $86** |
| `ERASE A` | `a5 20 41 00` | **`ERASE` = $A5** |
| `X=A(3)` | `58 ef 41 28 14 29 00` | subscript ref = **no token** — `name ( subs )` verbatim (`(`=$28, `)`=$29, digit=`$11+n`) |
| `OPTION BASE 1` | `4f 50 54 49 95 20 c9 20 12 00` | "OPTI" literal + `ON`($95) + `BASE`($C9) — tokenises but **`OPTION BASE` is not an executable statement** (Syntax error), so no OPTION handling is built |

The `(`/`,`/`)` around subscripts are existing punctuation. The load-bearing parse
consequence: an array reference is lexically identical to a function call
(`NAME(args)`), so the factor layer + LET target must **dispatch on whether NAME is
a known function token vs a plain variable name** — a subscripted plain name is an
array element. Each value gets a crunch-byte-identity gate case.

---

## 6. Gates

A new **`array-acceptance`** gate (peer of `float-acceptance` / `string-acceptance`
/ `math-acceptance`), run on the VG-8020 via the KEYBUF-injection REPL driver +
`run_cases`/`run_differential` batching:

- Per sub-slice: functional cases for every semantic in §4 that the slice lands,
  each **differential vs the reference** where the reference can exercise it.
- Crunch-byte-identity for each new keyword.
- Host unit tests (`make unit-test`) for the RAM-only halves (offset arithmetic,
  bound checks, allocator pointer math) — the fast regression layer.
- Byte-identity gate (lean `basic.rom` unchanged) — every new routine is
  `IF ROM_BASE < $4000`.
- **Fable adversarial review of every sub-slice** (standing float-pack lesson:
  every slice hid ≥1 matrix-invisible bug).

---

## 7. Open questions for sign-off — ✅ ALL SIGNED OFF AT DEFAULTS (2026-07-14)

- **Q-A1 (slicing).** Is slice 1 = "allocator + numeric arrays, base 0, no
  ERASE/OPTION" the right smallest cut? (Recommended: yes — it proves the
  allocator, the hardest new piece, on the diskless-testable numeric path.)
- **Q-A2 (slice-1 array ceiling).** Anchor `ARYTAB` at program-end, ceiling =
  `min(HIMEM, $BE00)`? Confirm the DETOKBUF ($BE00) and high-BLOAD interactions
  are acceptable for slice 1, or set the default ceiling elsewhere.
- **Q-A3 (lvalue reach in slice 1).** Which lvalue contexts must slice 1 cover —
  just `LET`/expression, or also FOR/READ/INPUT/`VARPTR(A(i))`? (Recommended:
  `LET` + expression rvalue in slice 1; FOR/READ/INPUT lvalues fold in with their
  existing single-letter shims in a slice-1 follow-on if cheap, else slice 2.)
- **Q-A4 (relocation timing).** Keep scalars/strings in the fixed pools through
  slices 1–3 and unify only in slice 4 (recommended, decouples risk), or bite off
  the full contiguous relocation earlier?
- **Q-A5 (multi-dim in slice 1).** Include multi-dimensional numeric arrays in
  slice 1, or single-dimension first and multi-dim as slice 1b? (Recommended:
  include multi-dim — the offset arithmetic is the same code path and cheap to get
  right once, and games use 2-D arrays.)

---

## 8. Next step

§7 signed off + §4.1/§5 characterized. Next = the **slice-1 implementation
contract** (§9 below), then implement + gate + Fable-review, per
[[opus-vs-sonnet-model-split]] (Sonnet 5 on the signed-off contract).

---

## 9. Slice-1 implementation contract (DRAFT — awaiting sign-off)

**Status: 🟡 DRAFT 2026-07-14.** The concrete cut for slice 1: the dynamic
allocator + numeric arrays (base 0, multi-dim), grounded in §4.1/§5 and the current
code. New file `basic/arrays.asm`, all `IF ROM_BASE < $4000` (lean stays
byte-identical). No scalar/string relocation (that is slice 4).

### 9.1 RAM model + allocator pointers (new sysvars, repack-only)

The array area is the **low free region**: it begins at the stored program's end
and grows up, sharing the `$8001..TXTMAX` span with the program text exactly as the
real MSX model shares it. Two 2-byte pointers + a small index scratch:

| Sysvar | Size | Meaning |
|---|---|---|
| `ARYTAB` | 2 | base of the array area = program end (recomputed, §9.6) |
| `ARYEND` | 2 | bump pointer = first free byte (empty when `== ARYTAB`) |
| `ARY_NIDX` | 1 | subscript count parsed for the current reference |
| `ARY_IDX` | 2·`MAXDIM` | parsed subscript values (int16), one per dimension |
| `ARY_SCR` | ~8 | offset-arithmetic scratch (running offset, stride) |

Placement: `ARYTAB`/`ARYEND`/`ARY_*` go in the page-`$E0`/`$F0` own-choice free RAM
(pick a hole in the slice-1 contract review — e.g. near the other Phase-2/3 scratch;
they are 2+2+1+2·MAXDIM+8 ≈ 21 B for MAXDIM=4). **`MAXDIM` = 4** for slice 1
(documented cap; games use ≤3; a reference with >4 subscripts → `Subscript out of
range`, a documented divergence from the reference's larger internal cap).

**Ceiling** (the OOM bound) = `min(HIMEM, TXTMAX)`. `TXTMAX = $BE00` (repack) already
bounds program text and sits below every work-area pool (`VARTAB $E1C0`, strings,
disk buffers) and below DETOKBUF — so arrays can never trample them. `HIMEM`
(`$FC4A`, set by `CLEAR ,&Hxxxx`, [basic/clear.asm](../basic/clear.asm)) lowers the
ceiling further when a loader reserves high RAM; `min` picks the binding one. This
makes `CLEAR` load-bearing (the deferred item in clear.asm's comment).

### 9.2 Array descriptor (own design — clean-room)

Variable-width, bump-allocated, never moved or freed within slice 1 (ERASE = slice
2). One descriptor:

```
+0  name0 : 1     upcased first char (0 in no slot — but the area has no free slots,
+1  name1 : 1       it is a packed bump list; walk stops at ARYEND)
+2  type  : 1     2 / 4 / 8  (int / single / double), from suffix / DEFtbl (§9.4)
+3  ndim  : 1     dimension count (1..MAXDIM)
+4  bound0: 2     inclusive upper subscript of dim 0 (LE)   ] ndim of these
    ...             ...
    element data : elsize · Πk(boundk+1) bytes, zero-filled on alloc
```

`elsize = type` (2/4/8). Element order = **column-major** (first subscript varies
fastest): `off(i0,i1,…) = i0 + (b0+1)·(i1 + (b1+1)·(i2 + …))`, `elem_addr =
data + off·elsize`. Ordering is internal/own-choice (unobservable in slice 1 —
VARPTR of an element is deferred, Q-A3); column-major is chosen to match MSX
convention should VARPTR arrive later.

### 9.3 Routines (`basic/arrays.asm`)

- **`ary_find`** — in: BC=key, A=type. Walk `ARYTAB..ARYEND` by each descriptor's
  own stride (`4 + 2·ndim + elsize·Πk(boundk+1)`); match on (name0,name1,type).
  Out: CF=found + HL=descriptor base, else CF clear + HL=`ARYEND`. (Type is part of
  the key: `A`/`A%` are distinct arrays, §4.1 #7.)
- **`ary_parse_subs`** — in: HL at `(`. Eval each comma-separated subscript via
  `eval` into `ARY_IDX[]`, incrementing `ARY_NIDX`; require closing `)`. Each
  subscript is coerced to int16 (existing `fac_to_int_strict`/`flt_to_int16`). Saves
  the key (eval clobbers BC). `> MAXDIM` subscripts → `Subscript out of range`.
- **`ary_resolve`** — in: BC=key, A=type, `ARY_NIDX`/`ARY_IDX` filled. `ary_find`;
  if missing, **auto-dim**: create a descriptor with `ndim = ARY_NIDX`, every bound
  = **10** (§4.1 #1), zero-filled (OOM-checked, §9.5). Then validate: `ARY_NIDX ≠
  descriptor.ndim` → `Subscript out of range`; for each k, `ARY_IDX[k] < 0` →
  **`Illegal function call`** (§4.1 #9), `ARY_IDX[k] > boundk` → `Subscript out of
  range` (§4.1 #8). Compute `elem_addr` (§9.2). Out: HL=elem_addr, A=type.
- **`ary_load`** (rvalue) — `ary_resolve` → read the element into FAC/FACTYP + DE
  int16 fast path (mirrors `var_load_fac`'s value-field read: int16 for type 2,
  `LDIR` of `elsize` bytes into FAC for 4/8).
- **`ary_store`** (lvalue) — `ary_resolve` → coerce the live RHS (DE/FAC) into `type`
  and write the element (mirrors `var_store_fac`'s value-field write + coercion:
  `fac_to_int_strict` / `round_single_and_pack` / `round_and_finalize`; Overflow →
  FPERR, D-F2-1 abort). *(Mirror, not refactor, `var_*_fac` — keep the F3 typed
  scalar store untouched; factor a shared `elem` codec only if it falls out cleanly
  in review.)*
- **`ex_dim`** — DIM handler (§9.4).

### 9.4 `DIM` statement + parse integration

- **Token/dispatch:** add `DIM` (`$86`) to [kwtable.inc](../basic/kwtable.inc)
  (repack-only) and a `cp DIM_TOKEN : jp z,ex_dim` arm in `exec_stmt`
  ([interp.asm](../basic/interp.asm):~213, in the `IF ROM_BASE < $4000` block).
  `ERASE`/`$A5` token + handler are **slice 2** — not added now, so `ERASE` stays a
  `Syntax error` in slice 1 (out of scope).
- **`ex_dim`:** for each comma-separated `NAME(b0[,b1…])`: `var_str_type` (string →
  slice 3, so a `$` name in slice 1 → `Syntax error` or defer; **decide in review**,
  Q-9a) then `var_name_key` (BC=key, A/`VARTYPE`=type); parse the bound list (each
  bound `eval`'d to int16 ≥ 0); `ary_find` — if already present → **`Redimensioned
  array`** (§4.1 #4); else allocate + zero (OOM-checked). Loop on `,`.
- **lvalue `A(i)=x`:** in `ex_let` ([interp.asm](../basic/interp.asm):279), after
  `var_name_key` peek `(HL)`: if `'('` → `ary_parse_subs` + `ary_store` (RHS after
  `=` via `eval`), else the existing scalar path. The `$`-name string-array lvalue is
  slice 3.
- **rvalue `A(i)`:** in `ev_f_var` ([expr.asm](../basic/expr.asm):551), after
  `var_name_key` peek `(HL)`: if `'('` → `ary_parse_subs` + `ary_load` (auto-dim on
  read), else the existing `var_load_fac`. This is the array-vs-function
  disambiguation (§5): `ev_f` reaches `ev_f_var` only for a plain letter, never a
  function token, so a `(` after a plain name is unambiguously a subscript.

### 9.5 Errors (§4.1) + OOM

Reuse the existing disposition machinery: `Subscript out of range` / `Illegal
function call` / `Redimensioned array` / `Out of memory` are raised via the same
`stmt_error`-class path the other runtime errors use (exact message text + numbers
oracle-locked; capture each in the gate). OOM check before every allocation:
`ARYEND + descriptor_size > ceiling` → `Out of memory` (nothing written).

### 9.6 Allocator reset (edit/clear coupling)

`ARYTAB`/`ARYEND` are reset to the **program end** at:
- `clear_vars` ([vars.asm](../basic/vars.asm)) — already the NEW/CLEAR/RUN hook;
  add `ARYTAB = ARYEND = program_end`.
- **`store_line`** ([program.asm](../basic/program.asm)) — editing the program shifts
  its end, so any live array is invalidated; reset the allocator there too. This
  matches the reference "editing a line clears variables" semantics (for arrays;
  scalars/strings in fixed pools are a documented slice-1 divergence until slice 4).

`program_end` = the address just past the program's `$0000` terminator (derive from
the existing `PRGEND`/text-scan; pin the exact source in the contract review).

### 9.7 Gate (`array-acceptance`, slice-1 cases)

Differential vs the VG-8020 (numeric arrays are diskless-testable), driven by the
KEYBUF REPL harness — promote the §4.1 characterization cases: auto-dim/bound-10,
DIM inclusive/over, base-0, auto-init-0, redim, multi-dim value+init+wrong-count,
type independence, negative→ILL, float element, `DIM P(2),Q(3)`. Plus a `DIM`
crunch-byte-identity case (`86 20 41 28 16 29 00`). Host unit tests for the offset
arithmetic + bound checks + `ary_find` stride walk. Lean byte-identity + Fable
review.

### 9.8 Open contract questions (for sign-off before coding)

- **Q-9a.** In slice 1, a string-array `DIM A$(n)` or `A$(i)=…` → plain `Syntax
  error`, or a clearer deferral? (Recommended: `Syntax error` — it is genuinely
  unsupported until slice 3; the reference has no divergence to match since ours
  simply lacks the feature.)
- **Q-9b.** `MAXDIM = 4` acceptable (a `Subscript out of range` beyond it), or size
  the index buffer higher? (Recommended: 4.)
- **Q-9c.** Confirm `store_line` array-reset is acceptable (any current probe that
  DIMs then edits? — none exist yet; new behaviour).
- **Q-9d.** Exact free-RAM home for the ~21 B of `ARY*` sysvars — to be picked
  against sysvars.inc in the first implementation step (not a semantic choice).

---

## 10. Split design — glue in main, resolver in the sub-ROM (SIGNED OFF 2026-07-15)

**Why (space).** The monolithic slice-1 engine (WIP branch `arrays-slice1-wip`,
verified lean-byte-identical) is complete but overruns the repack ROM by ~284 B:
on clean `main` there are **730 B free in the low region** (`$3D26..$4000`) and
only **30 B free in page 1** (`$7FE2..$8000`); the engine needs ~812 B low + ~232 B
page-1 ≈ 1 KB. No redistribution closes a ~284 B *total* deficit. The **sub-ROM is
nearly empty** (~13 KB free page-0, ~10.6 KB page-1 — the "nearly full" note was a
stale reference to the superseded basic-window-in-sub design), so the ratified fix
(user, 2026-07-15) is to **move the array engine's leaf bulk into a sub-ROM
tenant**, freeing the low region.

**Why it fits the existing tenant ABI with no extension.** The math tenants are
page-0 tenants: while one runs, slot-0 page 0 (the low region) is switched out but
main **page 1 stays visible**; they are pure FAC-leaves. The array engine can't
run *whole* as a tenant (it needs `eval` for subscripts, which reaches into page-0
`float-arith` — switched out). But the split isolates a **pure-RAM leaf** that
needs *neither* main page: the resolver walks the array area, does offset
arithmetic, allocates, and bound-checks — all over **RAM (pages 2/3, always
mapped)**. So it marshals through the standard `subrom_call` (IX=entry, args/results
in RAM, `A`=result, `CF`=absent, under DI) exactly as the math tenants do.

### 10.1 Partition

**Main page-1 glue** (the small part that must see main's eval/var machinery):
- `ex_dim` — parse each `NAME(b0[,b1…])`: `var_name_key`→key+type; `eval` each
  bound into the param block; `subrom_call` op=`DIM`; on a nonzero result code
  raise the mapped error (`Redimensioned array`/`Out of memory`).
- `ex_let_arr` (from `ex_let`) / `ev_f_arr` (from `ev_f_var`) — parse + `eval` each
  subscript into the param block; `subrom_call` op=`RESOLVE` (auto-dim on read);
  the tenant returns the **element address**; glue then does the FAC↔element copy +
  the type coercion (reusing the `var_store_fac`/`var_load_fac` value-field codec —
  int16 for type 2, `LDIR` of `elsize` for 4/8), and raises on the result code
  (`Subscript out of range` / `Illegal function call`).
- The array-vs-function `(`-peek after `var_name_key` (interp.asm:586 / expr.asm:543)
  stays in main — it is 2–3 instructions per site.

**Sub-ROM page-0 tenant `ary_engine`** (the bulk, ~400–600 B, pure-RAM leaf):
`ary_find` (descriptor stride walk), auto-dim allocation + zero-fill, the
column-major offset arithmetic, the bound / negative / wrong-`ndim` checks, and the
`DIM` descriptor construction. **No `eval`, no float-arith, no main-ROM call** —
only RAM reads/writes over the array area (`ARYTAB..ARYEND`, derived from
`PRGEND`+ceiling) and the param block. One op-dispatched entry (op byte in the
param block) added to the sub-ROM page-0 entry table, per the math-pack tenant
pattern ([spec-basic-subrom-mathpack.md](spec-basic-subrom-mathpack.md)); subject to
`check_tenant_closure.py` (its whole callee set must be co-resident/RAM).

### 10.2 Param / return block (new RAM, ~24 B, page-2/3)

```
ARY_OP    : 1     0 = RESOLVE (read/write element), 1 = DIM
ARY_KEY   : 2     name0, name1
ARY_TYPE  : 1     2 / 4 / 8
ARY_NIDX  : 1     subscript / dimension count (1..MAXDIM=4)
ARY_IDX   : 2·4   the eval'd subscripts (RESOLVE) or bounds (DIM), int16 LE
ARY_ADDR  : 2     [return] element address (RESOLVE) — into the RAM array area
ARY_ERR   : 1     [return] 0 ok; 1 Subscript-oor; 2 Illegal-fn (neg); 3 Redimensioned; 4 OOM
```

Main fills `ARY_OP..ARY_IDX`, `subrom_call`s, then reads `ARY_ADDR`/`ARY_ERR`. This
replaces the WIP's `ARY_NIDX`/`ARY_IDX` scratch (which aliased tokeniser scratch —
keep that aliasing analysis) and needs **no new persistent allocator sysvars**
(`ARYTAB` stays derived as `PRGEND+2`, `ARYEND` is the descriptor-terminator
sentinel — the WIP's deviation #1, retained).

### 10.3 Reuse + build

The WIP engine's *logic* is correct (contract §9) — this is a **re-home + ABI-wire**,
not a rewrite: lift `ary_find`/offset/alloc/bounds/`ex_dim`-core bodies into a new
`sub/arrays.asm` tenant reading the param block; reduce `basic/arrays.asm` to the
main-side glue (parse/eval/copy/coerce + `subrom_call` + error raising). Gates
unchanged (§9.7) + the tenant-closure gate. Expected: low-region pressure drops by
the ~400–600 B moved to the sub-ROM, so both regions fit; re-measure
`__MEAS_LOW_END`/`__MEAS_PAGE1_END` to confirm. Lean `basic.rom` stays
byte-identical (all main-side additions `IF ROM_BASE < $4000`; the sub-ROM is a
separate artifact).
