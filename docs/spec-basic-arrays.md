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
campaign, and (now-resolved) sign-off questions. Next = the oracle characterization
campaign (§4/§5), then the slice-1 implementation contract; each sub-slice still
gets its own concrete contract + Fable review before its own code, exactly as the
float pack, string engine, and math pack slices did.

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
  upper bound of 10 per dimension (to be oracle-confirmed, §5).
- **`OPTION BASE 0|1`** — the subscript lower bound.
- **`ERASE`** — free arrays (and permit re-`DIM`).
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

- **Slice 2 — `OPTION BASE` + `ERASE`.** Lower-bound selection and array freeing
  (ERASE also enables clean re-DIM). Small, self-contained; split out so slice 1
  can hardcode base 0.
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

## 5. Token pinning (to be captured, not asserted)

Per the established discipline (math-pack §6, string-engine): every new keyword's
token is captured from the **VG-8020 crunch** and cross-checked against **MSX2 TH
Table 2.20 / MSX Assembly Page** — never asserted from memory, never from ROM
disassembly. New reserved words this arc introduces: **`DIM`**, **`ERASE`**,
**`OPTION`** (+ `BASE` handling). The `(`/`,`/`)` around subscripts are existing
punctuation tokens. Each value is pinned in the sub-slice contract with its crunch
capture, plus a crunch-byte-identity gate case.

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

On sign-off of §7: write the **slice-1 implementation contract** (the concrete
descriptor layout, allocator pointer set + sysvars, DIM parser, subscript
evaluator, auto-dim, bound/OOM checks, and the token captures), then implement +
gate + Fable-review, per [[opus-vs-sonnet-model-split]] (Sonnet 5 on the signed-off
contract).
