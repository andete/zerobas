<!-- Provenance: original work (own-design implementation contract). String-array
*semantics* (DIM $-names, subscript ranges, auto-dim, error messages, element
string ops, value-copy semantics) are oracle-locked to the public MSX-BASIC
language reference + black-box VG-8020 capture (§2, 2026-07-15). The element
*byte layout* ([len][bytes:STRMAX] inline, reusing the STRTAB slot value format)
is zerobas's OWN design, continuous with the scalar string store — never ROM
disassembly (see PROVENANCE.md, [[no-reference-rom-disasm]]). -->
# Arrays slice 3 — string arrays implementation contract

**Status: 🟡 CONTRACT DRAFT — awaiting sign-off (2026-07-15).** Characterization
DONE (§2, VG-8020); design + split proposed (§4/§5); one open sign-off question
(§8, the element-format fork — recommended default given). No code until sign-off,
per [[spec-before-implementation]]. Builds on the slice-1 allocator + descriptor
([spec-basic-arrays.md](spec-basic-arrays.md) §9), slice-2 `ERASE`
([spec-basic-arrays-slice2-erase.md](spec-basic-arrays-slice2-erase.md)), and the
scalar string store ([basic/vars.asm](../basic/vars.asm) `str_find`/`str_set_key`,
[basic/strvar.asm](../basic/strvar.asm)). Repack build only; lean stays
byte-identical.

---

## 1. Surface & scope

Deliver the full string-array surface, everywhere the numeric slice delivered the
numeric one:

- **`DIM S$(n)` / `DIM S$(n,m,…)`** — declare string arrays, single- and multi-dim.
- **`S$(i…)` as lvalue** — `S$(i)=expr$` (LET path), assigned from a literal,
  another string variable, another string element, or a concatenation.
- **`S$(i…)` as rvalue** — a first-class string factor: usable in `PRINT`, concat,
  `LEN`/`ASC`/`VAL`/`MID$`/`LEFT$`/`RIGHT$`/`STR$`-args, comparisons, etc.
- **Auto-dimensioning** — referencing an undeclared `S$(i)` auto-declares it, upper
  bound 10 per dimension.
- **`ERASE S$`** — already reaches the tenant as type=1 (slice 2); once string
  arrays exist, `ERASE S$` frees a *real* string array instead of always raising
  IFC. This is a pure consequence of the type-1 key now matching — **no ERASE code
  changes** (slice-2 §4 already forces type=1 for `$` names).
- Error surface — identical messages to numeric (§3), all inherited.

**Out of scope (unchanged from the arc):** `MID$(S$(i),…)=` as a *statement*
lvalue (string-engine deferral, not array-specific); `VARPTR` of an element (Q-A3);
STRMAX→255 / a real string heap (slice 4).

---

## 2. Characterization (VG-8020 oracle, 2026-07-15 — do not re-run)

All black-box observable. Script: `scratchpad/strarr_char{,2}.py`. **Every semantic
mirrors the numeric slice** (base-0, DIM inclusive, auto-dim upper 10) with the
string-value additions:

| # | Probe | Result |
|---|-------|--------|
| 1 | `DIM S$(3):S$(1)="HI":?S$(1)` | `HI` — store/load |
| 2 | `S$(3)="X"` undeclared | auto-dims; `S$(10)` ok, `S$(11)` → **Subscript out of range** |
| 3 | `DIM S$(3):?S$(2)` / `?LEN(S$(2))` | `""` / `0` — fresh element = empty string |
| 4 | `DIM S$(5):S$(5)="E"` | ok (upper **inclusive**) |
| 5 | `DIM S$(5):S$(6)=…` | **Subscript out of range** |
| 6 | `DIM S$(2):S$(0)="Z"` | ok (**base 0**) |
| 7 | `DIM S$(3):DIM S$(3)` | **Redimensioned array** |
| 8 | `DIM S$(5):?S$(-1)` | **Illegal function call** (distinct from over-bound) |
| 9 | `DIM S$(2,3):S$(1,2)="HI"` | `HI`; wrong ndim `S$(1)` → **Subscript out of range**; init `""` |
| 10 | `S(1)=11:S$(1)="Q"` / `S%(1)=5:S$(1)="Q"` | `11 Q` / `5 Q` — **`S`/`S%`/`S!`/`S#`/`S$` independent** |
| 11 | concat / `LEN` / `MID$` / `LEFT$` on `S$(1)` | `ABC` / `3` / `BC` / `AB` — element is a first-class rvalue |
| 12 | scalar→elem, elem→elem, elem→scalar copy | all preserve the value |
| 13 | `S$(2)=S$(1):S$(1)="XY":?S$(2)` | `HI` — **value semantics** (elements hold copies, no aliasing) |
| 14 | `CLEAR` after `S$(1)="HI"` | element reads `""` — CLEAR frees array contents |
| 15 | `S$(1)=STRING$(40,…)` → `LEN`=40; `STRING$(255,…)` → **Out of string space** | reference has a heap (default 200 B); see §7 |

**Token crunch:** `DIM S$(5)` → `86 20 53 24 28 16 29 00` = `[DIM][sp]['S']['$']['(']['5' tok 0x16][')']`;
`X$=S$(3)` → subscript ref crunches as name+`$`+`(subs)` with **no array token**
(parser disambiguates by known-function-token, identical to numeric, §slice-1).
→ **No tokeniser/detokeniser change.** `$`=0x24 rides inside the crunched name; the
existing `var_str_type`/`var_name_key` pair already parses it.

---

## 3. Error surface — all inherited, zero new messages

Same four dispositions as numeric (slice-1 §4.1), keyed identically in the tenant:

| Condition | Message | Path |
|-----------|---------|------|
| index > declared/auto bound, or wrong ndim | `Subscript out of range` | ARY_ERR=1 → FPERR=… |
| re-`DIM` a live array | `Redimensioned array` | ARY_ERR=3 |
| negative index | `Illegal function call` | ARY_ERR=4 |
| (out of array RAM, HIMEM ceiling) | `Out of memory` | ARY_ERR=… |

Because type=1 is now a **live** array kind, the paths fire on `S$(…)` exactly as on
`A(…)`. No message wording, no new tier. (Contrast slice 2, which needed a bespoke
two-tier split; slice 3 needs none — the fork below is purely internal.)

---

## 4. The one internal change that matters: `elsize ≠ type`

Slice 1 baked the identity **`elsize = type`** (2/4/8 bytes) into the tenant
(`sub/arrays.asm:26`, and the literal use at `:435`/`:613`). A string element is
**not** `type` (=1) bytes. The element format decision (§8) sets a string element to
an **inline `[len][bytes:STRMAX]` value — 65 bytes (repack, STRMAX=64) / 33 (lean)**,
**byte-identical to the value portion of a STRTAB slot**. So:

```
elsize(type) = 2/4/8            for type 2/4/8   (numeric, unchanged)
elsize(type) = 1 + STRMAX       for type 1        (string, NEW)
```

This is the **durable gotcha flagged in slice 2**: "string type code = 1; a `$` name
parsed by var_name_key alone looks like a double." Now it becomes a one-line map
(`elsize_from_type`) consulted wherever the tenant currently reads `type` as a byte
count: `ary_alloc` (data-region sizing + zero-fill), `ary_resolve` (elem_addr =
data + off·elsize), the `stride` cache (`:331`). **No other descriptor field
changes** — `[name0][name1][type=1][ndim][bounds…]` is unchanged; only the
per-element byte count differs.

**Why inline (not classic `[len][ptr]`+heap):** zerobas has no string heap — the
scalar store is inline `[len][bytes:STRMAX]` in fixed STRTAB slots, and the heap is
explicitly a slice-4 concern (STRMAX→255, string-engine §5a). Inline elements are
(a) continuous with the scalar model, (b) preserve O(1) column-major indexing (fixed
elsize — a `[len][bytes…]`-packed variable-length scheme would force a walk), and (c)
give **value-copy semantics for free** (probe #13): copying an element is a byte copy,
so no aliasing, matching the oracle. Cost: memory-heavy (`DIM S$(10)` = 11·65 = 715 B
of array region); acceptable under the HIMEM-bounded dynamic allocator, revisited when
slice 4 introduces the real heap.

---

## 5. Implementation (glue-in-main + pure-RAM leaf — the slice-1 split)

### 5.1 Tenant leaf (`sub/arrays.asm`, page-0, pure-RAM) — the *only* leaf change
- Add `elsize_from_type`: `A=type → A/HL=elsize` (type 1 → `1+STRMAX`, else A).
  `STRMAX` is a build constant → baked into the tenant at assembly.
- Route `ary_alloc`, `ary_resolve`, and the `stride` computation through it instead
  of using `type` as the byte count. Zero-fill on alloc already yields `len=0` =
  `""` for every fresh string element (probe #3) — **no auto-init code**.
- `ary_find`/`ERASE`/redim/bound/neg/ndim checks: **unchanged** — they key on
  `(name,type)` and walk descriptors; type=1 already flows through since slice 2.

### 5.2 Main glue (`basic/arrays.asm` + LET/expr hooks) — string store/load
- **`ex_dim` (`:293-295`):** delete the `jp nz,stmt_error` that rejects `$` names.
  A `$` name now sets type=1 (via the existing `var_str_type`/`VARTYPE` path — note
  the slice-2 F1 lesson: force type=1, don't trust `var_name_key`'s VARTYPE=8) and
  dispatches op=DIM exactly like numeric. The tenant sizes it with the string elsize.
  **D1 (adversarial catch):** the old `$`-reject *doubled* as the "target must be a
  name" guard — deleting it let `DIM $(5)` and `DIM 1(5)` through (silently allocating
  a garbage-keyed array; reference: `Syntax error`). Fix: add `ex_erase`'s own
  `call is_letter / jp nc,stmt_error` right after `skip_spaces`, so a non-letter DIM
  target is rejected up front. Gate: `strarr.dim.bare.dollar` / `strarr.dim.digit.name`.
- **Store (`S$(i)=expr$`), the LET string path:** resolve `elem_addr` via the tenant
  (op=RESOLVE, type=1) → `HL=elem_addr`. Then **reuse `str_set_key`'s copy body**
  (the STRTAB `[len][bytes]` LDIR with the STRMAX clamp) writing to `elem_addr`
  instead of a STRTAB slot: `str_eval` the RHS → `STRPTR` = source `[len][bytes]`
  descriptor → clamp len to STRMAX → LDIR into `elem_addr`. Value semantics fall out
  of the byte copy. This mirrors `ary_store_write` (`:445`, the numeric FAC-copy) as
  its string sibling.
- **Load (`S$(i)` rvalue), the string-factor path:** resolve `elem_addr` (op=RESOLVE,
  type=1) → **set `STRPTR = elem_addr`, VALTYP=1, done.** The element *is* a valid
  `[len][bytes]` descriptor, so every existing string consumer (print_strval,
  concat, LEN/MID$/…) reads it in place — **zero-copy**, exactly how `str_get_key`
  returns an in-place STRTAB descriptor. Hook: wherever `str_eval`'s variable case
  currently calls `str_get_key`, a `$`-name-followed-by-`(` routes to the array
  resolve instead (the same known-function-token disambiguation the numeric factor
  path already does).

### 5.3 Space (the razor-thin page-1)
Slice 2 left **~1 B page-1 free**; the playbook mandates any new page-1 byte
**low-region-offload**. All slice-3 glue (string store body, the load hook, the
`ex_dim` change is a *deletion*) targets the **low region** (`$3Dxx`, the same span
slice 1 used), not page-1. Measurement gate before commit: `make build/basic-reloc.rom`,
read `__MEAS_LOW_END`/`__MEAS_PAGE1_END` from `build/basic-reloc.sym`; page-1 free
must stay ≥0.

---

## 6. Gate additions (`make array-acceptance`)

Fold the §2 probes into the existing gate (currently 52 numeric+ERASE cases). New
string cases, each direct-mode (per the stored-RUN landmine) or split ≤38-char lines
where needed: store/load, auto-dim + bound, auto-init `""`+LEN, inclusive/base0,
over-bound/redim/neg errors, multi-dim, type-independence (`S`/`S%`/`S$`),
element string-ops (concat/LEN/MID$/LEFT$), the three copy directions + the
**no-alias** case (#13), `ERASE S$` frees, `CLEAR` frees. Plus a crunch-identity
case for `DIM S$(5)` (§2 token pin) and the STRMAX-clamp deviation case (§7).

---

## 7. Documented deviations (own-design, not blockers)

1. **No `Out of string space`; STRMAX clamp instead (probe #15).** The reference has
   a heap (default 200 B) and errors when a single element exceeds free heap; zerobas
   stores inline and **clamps each element to STRMAX** (64 repack), consuming but not
   erroring. This is the *same* deviation the scalar string store already documents
   (string-engine §5a) — inherited, not new. Resolves in slice 4 (heap + STRMAX→255).
2. **`Out of memory` on a large string DIM where the reference succeeds (D-2).**
   The signed-off inline 65-byte element (Q-S1) makes `DIM S$(1000)` need 65 065 B
   of array region; the reference's 3-byte `[len][ptr]` descriptors need ~3 KB, so it
   succeeds while zerobas raises `Out of memory`. The observable cost of the inline
   format (§4 calls the memory cost "acceptable"); the OOM path itself is sound (the
   string elsize is threaded through the 16-bit alloc-overflow + HIMEM-ceiling guards,
   verified — no silent wrap, sysvars intact after the abort). Gate case
   `strarr.dim.huge.oom` (`zberr` kind). Resolves in slice 4 (real heap).
3. **Pre-existing shared deviations** (arc §8, not slice-3 bugs): stored-`RUN` doesn't
   abort on a runtime error (→ gate error cases must be direct-mode);
   whitespace-in-identifier parsing.

---

## 8. Open sign-off question

**Q-S1 — element format.** Recommended: **inline `[len][bytes:STRMAX]`, elsize =
1+STRMAX** (§4/§5), the STRTAB-continuous, heap-free, value-semantics-for-free
choice. The only alternative is pulling the slice-4 string heap forward to use classic
3-byte `[len][ptr]` descriptors — **rejected** for slice 3: it conflates the two
slices, and the arc explicitly ordered "string arrays (3)" before "relocation + heap
(4)." **Recommend: sign off the inline element format; heap deferred to slice 4.**

Everything else (semantics, errors, split, gate) is oracle-locked or mechanically
inherited — no other open questions.
