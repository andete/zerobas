<!-- Provenance: original work (a how-to over zerobas's OWN sub-ROM architecture).
No reference-ROM content; the MSX2 sub-ROM ID/EXTROM/EXBRSA conventions it cites are
published (MSX2 Technical Handbook), same grade as elsewhere. See PROVENANCE.md. -->
# Playbook — moving a BASIC feature into the sub-ROM (zerobas-sub tenants)

**What this is.** A practical, reusable guide for the recurring task: *the repack
main ROM is full, and a new feature needs space.* zerobas-sub (slot 3-2, 32 KB) is
the overflow home, and this doc is the decision tree + recipe for putting a feature
there — distilled from the two arcs that have done it (math pack = leaf tenants;
arrays = a glue+resolver split). Read it **before** adding the next space-hungry
feature; there is much more BASIC to build and most of it will land here.

It consolidates knowledge that is otherwise scattered:
[spec-basic-subrom.md](spec-basic-subrom.md) §3b (paging), §3c (dispatch ABI), §3f
(leaf-audit); [spec-basic-subrom-mathpack.md](spec-basic-subrom-mathpack.md) (leaf
tenants); [spec-basic-subrom-trampoline.md](spec-basic-subrom-trampoline.md) (EI);
[spec-basic-arrays.md](spec-basic-arrays.md) §10 (the split); and the well-commented
[basic/subromcall.asm](../basic/subromcall.asm).

---

## 1. When you need this — measuring the wall

Symptom: `make` fails with a `*_OVERRAN_4000_*` / `*_OVERRAN_8000_*` guard symbol,
or you can see it coming. Measure exactly where you stand:

```
make build/basic-reloc.rom              # then read the two labels:
#   __MEAS_LOW_END   in build/basic-reloc.sym  -> low-region free  = $4000 - LOW_END
#   __MEAS_PAGE1_END in build/basic-reloc.sym  -> page-1  free     = $8000 - PAGE1_END
```
- **Low region** `$2812–$3FFF` (slot-0 **page 0**): reclaimed C-BIOS space; home of
  the repack-only tenants that main-BASIC calls directly (str-engine, input, float,
  float-arith, subromcall, …).
- **Page 1** `$4000–$7FFF` (slot-0 page 1): main BASIC. Usually near-full (tens of
  bytes), so new *statement/handler* code rarely fits here.

Sub-ROM headroom (the landing zone) — trailing-`$FF` run per 16 KB page of the
built ROM:
```
python3 -c "d=open('build/sub.rom','rb').read()
for i,(a,b) in enumerate([(0,0x4000),(0x4000,0x8000)]):
  p=d[a:b]; f=0
  for x in reversed(p):
    if x==0xFF: f+=1
    else: break
  print('sub page',i,'free tail ~',f)"
```
As of 2026-07-15 the sub-ROM is nearly empty (~13 KB page-0, ~10.6 KB page-1). *(Any
"29 B free / nearly full" note in old docs refers to the SUPERSEDED basic-window-in-
sub design — ignore it.)*

---

## 2. The one fact that decides everything — page visibility during a call

CALSLT switches only the *called* page, so a sub-ROM tenant runs with a specific,
asymmetric view of memory ([spec-basic-subrom.md](spec-basic-subrom.md) §3b):

| While this runs | slot-0 **page 0** (BIOS + low region + `$0038` ISR) | slot-0 **page 1** (main BASIC) | RAM pages 2/3 |
|---|---|---|---|
| **page-0 tenant** (`$0010+`) | **switched OUT** (invisible) | **visible** — callable | visible |
| **page-1 tenant** (`$4010+`) | visible (BIOS) | **switched OUT** (invisible) | visible |

Consequences that are hard rules:
- A **page-0 tenant** may call main-BASIC **page-1** routines directly (`pchar`,
  `eval`, the var store) — BUT **not the low region** (`float-arith`, str-engine,
  subromcall) which is paged out. This is the §3f leaf-audit obligation.
- A **page-1 tenant** may call the BIOS but **not main BASIC** at all.
- **RAM (pages 2/3) is always visible from both** — so `FAC`/`ARG`, sysvars, and a
  small `SUB_ARG`-style scratch block are the arg/result channel for every tenant.
- **Interrupts are OFF** while the sub-ROM is mapped (the ISR vector is paged out).
  A tenant that must run EI opts into the interrupt trampoline
  ([spec-basic-subrom-trampoline.md](spec-basic-subrom-trampoline.md)); short
  tenants just stay DI.

---

## 3. The decision tree — which tenant shape?

Classify the feature by **what it calls at runtime**, then pick a shape:

### A. Pure leaf — computes over `FAC`/RAM, calls nothing in main (or only page-1 / sub-local)
→ **Whole feature = one tenant.** This is the math pack: `SIN`/`COS`/`EXP`/`RND`/…
take `FAC`, compute, return `FAC` via RAM. Put it on **page 1** (the `$4010` island,
mirrors the disk DSKIO call the codebase runs 163×) if it needs the BIOS or nothing;
on **page 0** if it wants to call a main page-1 helper. The math pack lives page-1.
*Cost:* one entry-table append + a ~15 B main stub.

### B. Non-leaf, but its main-side needs are page-1 only, no low-region, no eval-of-arbitrary-expr mid-body
→ **page-0 tenant that calls main page-1 directly.** Legal because page 1 stays
visible. Watch the leaf-audit: if any callee (even transitively) dips into the low
region (`float-arith` is the usual trap — anything doing float math does), this
shape is **out** — go to C.

### C. Non-leaf that needs `eval` / `float-arith` / the low region mid-computation
→ **SPLIT: glue in main, a pure-RAM leaf resolver in the sub-ROM.** This is arrays
([spec-basic-arrays.md](spec-basic-arrays.md) §10). The trick: **do the
page-touching work in main *before/after* the call, and hand the tenant only a
pure-RAM job.**
- **Main glue (page 1, small):** parse the statement, `eval` the sub-expressions,
  coerce `FAC` ↔ storage. Everything that touches page-1/low-region services.
- **Sub-ROM tenant (the bulk, a pure-RAM leaf):** given already-computed values in
  a RAM param block, do the integer/pointer/memory work (table walks, offset math,
  allocation, bound checks) over RAM only. It calls **nothing** in either main page,
  so the page-0/page-1 split is *moot* and it drops straight onto the existing ABI.
This is how a feature far too entangled to be a leaf still spends the sub-ROM's
space: you carve a leaf *out of the middle* of it.

**Rule of thumb:** if `grep` of the feature's call graph reaches `float-arith`,
`eval`, or any low-region label, it is **not** a whole-tenant — either keep those
calls main-side (shape C) or move the callee too (rarely worth it).

---

## 4. The ABI recipe (all shapes)

From [spec-basic-subrom.md](spec-basic-subrom.md) §3c + [basic/subromcall.asm](../basic/subromcall.asm):

1. **Append** a `jp <tenant>` to the page's entry table — `SUBROM_ENTRY_BASE_P0
   = $0010` or `SUBROM_ENTRY_BASE_P1 = $4010`. Never move an existing entry; the
   main stub hard-codes only its page + index (`IX = base + 3*index`).
2. **Marshal args into RAM** (`FAC`/`ARG` + a small `SUB_*`/param-block scratch in
   page-2/3). Parsing/`eval` **always stays main-side.**
3. **Main stub:** guard the text cursor (HL) + any live page-1 pointers (CALSLT
   clobbers *all* registers), then `call subrom_call` with `IX` = entry. It returns
   `CF=1` **without calling** if the sub-ROM is absent (reduced builds) → jump to
   your absence-error path; `CF=0`, `A` = tenant result on success. The whole call
   is under DI.
4. **Read results from RAM**, restore the cursor, continue.
5. **EI tenant?** Only if it runs long enough to need interrupts — opt into the
   trampoline (§trampoline spec). Otherwise stay DI.

Error reporting: a leaf tenant can't print — return an **error code in `A`/RAM** and
let the main stub raise the disposition (`stmt_error`-class), as arrays' resolver
returns `ARY_ERR` → glue raises `Subscript out of range` / etc.

---

## 5. Gates every tenant must pass

- **`tools/check_tenant_closure.py`** — the tenant's entire callee set is co-resident
  (sub-ROM) or RAM; **nothing reaches the invisible page.** This is the mechanical
  enforcement of §2/§3f — run it, don't eyeball it.
- **`tools/check_resident_abi.py`** — the resident-ABI closure is intact.
- **Leaf-audit (§3f)** — for a page-0 tenant, confirm no low-region callee; for a
  page-1 tenant, no main-BASIC callee.
- **Lean byte-identity** — all main-side additions stay `IF ROM_BASE < $4000`; the
  lean 16 KB `build/basic.rom` SHA is unchanged (the sub-ROM is a separate artifact,
  so tenant bodies never threaten it). Verify with `shasum`, don't assume.
- Re-measure `__MEAS_LOW_END` / `__MEAS_PAGE1_END` after — prove the main ROM now
  fits, and by how much.

---

## 6. Worked examples

| Feature | Shape | Main-side | Sub-ROM tenant | Why |
|---|---|---|---|---|
| **Math pack** (`SIN…RND`) | A — whole leaf | tokenise + a thin FAC-marshal stub | the whole function, page-1 island | `FAC`→`FAC`, no main callbacks |
| **Arrays** (`DIM`/subscripts) | C — split | parse + `eval` subs + `FAC`↔element coerce | `ary_find`/offset/auto-dim/bounds, **pure-RAM**, page-0 | needs `eval`+`float-arith` (main) → carve a RAM leaf out |

---

## 7. Step-by-step for the next feature

1. **Measure** (§1): confirm the wall + the exact deficit, and the sub-ROM headroom.
2. **Classify** (§3): trace the feature's call graph. Leaf? → A. Non-leaf, page-1
   needs only? → B. Touches `eval`/`float-arith`/low-region? → C (split; find the
   pure-RAM leaf to carve out).
3. **If C, draw the cut:** what does the tenant need as *pre-computed* inputs (so it
   never calls back)? Define the RAM param/return block.
4. **Wire the ABI** (§4): append the entry, write the main stub, marshal through RAM.
5. **Gate** (§5): closure + resident-ABI + leaf-audit + lean byte-identity +
   re-measure. Then the feature's own functional/differential gate + Fable review.

**The meta-lesson (arrays, 2026-07-15):** don't attempt a monolithic implementation
when the main ROM is near-full — classify (§3) *first*. Arrays cost an 80-minute
build that overran by ~284 B before the split was chosen; measuring + classifying up
front would have gone straight to shape C.
