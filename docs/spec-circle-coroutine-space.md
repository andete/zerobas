# spec — CIRCLE → co-routine eviction (page-1 space reclamation for interrupt-traps)

Status: **✅ LANDED 2026-07-24.** Full re-host complete and gated: `ex_circle` is now a
thin eval-bounce servicer; the whole grammar walk + angle/aspect float math live in the
page-1 tenant `sub/circleparse.asm` (`SUBROM_IDX_CIRCLEPARSE=19`). **Build-confirmed reclaim
= 542 B** (page-1 free 80 → 622 B). Gates green: `basic-reloc` (lean byte-identity +
`--page1` closure with 20 tenants), `graphics-acceptance` **0 FAILs** (circ_r4..r20, arc_*,
ell_*, spoke_*, aspect_neg_err, and the whole PSET/LINE/PAINT/DRAW/sprite/VDP corpus),
`unit-test` **51/51** (incl. the moved `cpt_boundary_prep` + the 1.57-vs-1.58 teeth guard,
driven in the page-1-tenant memory map). One deviation from the plan: the reclaim was
**542 B** (not ~150–500 B) because essentially ALL of `ex_circle` moved — so the full
resident STOP-trap dispatch (364 B) now fits with ~258 B to spare; **no tenant-dispatch
traps needed** (supersedes D-CC-3).

**Measure-first result (sizing, baseline sym):** resident CIRCLE = **661 B** ($5C9F–$5F34);
essentially all of it (grammar walk `ex_circle`…`circ_draw` 341 B + angle/aspect float glue +
FPNUM constants 336 B) moves to a page-1 tenant, leaving only a ~150 B servicer + the resident
`GFX_OP=4` geometry call → **net page-1 reclaim ~350–500 B** (target was ~150 B). Sub-ROM
page-1 has **5441 B free** — ample. Space risk RETIRED.

**Finalized protocol (this build):** `GFX_OP=15` → page-1 tenant `gfx_circle_parse`
(`SUBROM_IDX_CIRCLEPARSE`, sub_p1_table). Shared cursor `GFX_DPTR` = the token cursor (RAM).
The tenant inlines `skip_spaces` + separator checks (it can't call main-page-1), walks the
grammar, and on each field sets `GFX_DREQ`: **1**=parse centre `(x,y)` (resident `parse_coord`
→ GFX_CXC/CYC), **2**=eval int16 (resident `gfx_eval_int16` → GFX_DVAL; tenant does the r-sign
/ colour-range checks), **3**=eval float→ARGA (resident `eval`+`widen_rhs_operand`; the tenant
then does the boundary/aspect float math writing GFX_SBRAD/EBRAD/ASPS…), **0**=done. Resident
services each request from `GFX_DPTR`, stores the value, advances `GFX_DPTR`, re-enters
`GFX_DRESUME=1`. On `GFX_DREQ=0`: check `GFX_RES` (tenant error → `raise_error`), else do the
resident `GFX_OP=4` geometry subrom_call (page-0). Two tenants (page-1 parse, page-0 geometry),
resident orchestrates both — the page-1 tenant reaches the low-region float pack (fp_mul/div/
cmp/add all confirmed <$4000), never main page-1.

Was: **DESIGN — sign-off pending.** A space-reclamation sub-arc: re-author `ex_circle`'s
resident grammar walk as a **page-1 sub-ROM tenant** driven by a DRAW-style eval-bounce
co-routine, to free ~page-1 room for interrupt-traps T1 (blocked-on-space,
`docs/spec-traps-t1-stop-reslice.md` §10). Repack-only (the whole graphics arc is).

Repository: all paths under `/Users/joost/projects/zerobas`.

---

## 1. Why — the trap byte wall

Interrupt-traps T1 (STOP) is written and correct but **overruns page-1 by 284 B** (measured);
page-1 has only **80 B** free and a scout found **no cheap carve** (the disk/file region is
100% eval/I/O-bound — `spec-traps-t1-stop-reslice.md` §10.0a). §10.3 opt 2 named the one
mechanism that reclaims eval-heavy parse bytes: the **DRAW-style co-routine**. This sub-arc
applies it to CIRCLE (the largest such resident parser), targeting ~150 B, enough to fund a
tenant-dispatch trap architecture across T1–T4.

## 2. The design decision that makes it pay off — a PAGE-1 tenant, not page-0

DRAW's tenant is **page-0** (`gfx_draw_op`): it can call main page-1 (`str_eval` via the
resident) but **not** the float pack (low region, which the sub-ROM overlays). That is fine
for DRAW — its language needs no float. **CIRCLE is different:** its resident bulk is *float
math* — `gfx_circ_boundary_prep` (3×`fp_cmp` + `fp_mul` + `gfx_round_arga_de`), `circ_aspect`
(`fp_div` + scale256), plus the FPNUM constants and helpers. A **page-0** CIRCLE tenant could
not host that math, so only the thin comma-hopping would move and the co-routine loop +
per-arg dispatch would nearly cancel the saving (**~20–50 B net — not worth it**).

A **page-1** tenant is the opposite visibility (per `tools/check_tenant_closure.py`): main
page-1 is switched out, but the **page-0 low region (float pack) stays reachable** — exactly
how `fp_sqrt` et al. call the shared FAC ops. So a page-1 CIRCLE tenant **can do all the float
math itself**, and the program token stream it parses lives in **RAM ($8000+, always mapped)**.
It bounces back to the resident only the handful of operations that are genuinely main-page-1:
`eval` / `parse_coord` / `gfx_eval_int16` (and the deferred-error check). This moves the
grammar walk **and** the float math off page-1 → the ~150 B reclaim.

**This is the load-bearing design call (D-CC-1): CIRCLE becomes a PAGE-1 tenant.**

## 3. The co-routine protocol (reuse the GFX_D* cells)

Model on `ex_draw`/`gdw_call` (`basic/graphics.asm:1124`), reusing `GFX_DREQ`/`GFX_DVAL`/
`GFX_DRESUME` and a shared cursor cell (`GFX_DPTR`-style). New `GFX_OP` value (15) → tenant
`gfx_circle_parse`.

- **Shared cursor** `GFX_DPTR` = the live token cursor (RAM). Seeded by the resident to the
  first byte past the CIRCLE token; advanced by the resident on each eval; read by the tenant
  to resume grammar parsing.
- **Tenant `gfx_circle_parse`** (page-1) walks the grammar state machine — the `(x,y)` /
  `,r` / `,c` / `,s` / `,e` / `,aspect` sequence, empty-field detection, STEP, the trailing
  separator checks — entirely in the tenant. When it reaches a field that needs a value, it
  sets `GFX_DREQ` to an **arg-type code** (1=coord-pair, 2=int16 (r/c), 3=angle-expr,
  4=aspect-expr) and returns. It does NOT try to delimit the expression itself (an arg
  expression can contain commas, e.g. `,POINT(3,4)`); it lets the resident's `eval` find the
  true end and reads the advanced `GFX_DPTR`, then inspects the *following* separator.
- **Resident servicer loop** (thin): on `GFX_DREQ`, eval from `GFX_DPTR` with the right
  resident routine (`parse_coord` / `gfx_eval_int16` / `eval`+`widen_rhs_operand`), store the
  raw result into a handoff cell (BC/DE→`GFX_*`, or `ARGA` for the float args), update
  `GFX_DPTR`, re-enter `GFX_DRESUME=1`. `GFX_DREQ=0` → the tenant is finished; then the
  resident does the final `circ_draw` marshal + the existing `GFX_OP=4` geometry call.
- **Float args** (angle, aspect): the resident evals to `ARGA` (RAM) and bounces back; the
  **tenant** does the `gfx_circ_boundary_prep` / `circ_aspect` float math on `ARGA` (float
  pack reachable) and writes the `GFX_SBRAD/…/GFX_ASPS` records the geometry op reads. So the
  ~200 B of angle/aspect float code **moves into the tenant**.

Round trips: one `subrom_call` per *present* arg (≤6). CIRCLE is never per-frame — fine
(same trade as DRAW/PAINT).

## 4. What moves vs stays

| Code | Now | After |
|---|---|---|
| Grammar walk (comma/empty/STEP/separator state machine, `ex_circle` 397–558) | resident ~120 B | **tenant** |
| Angle float math (`gfx_circ_boundary_prep`, `circ_parse_given_angle`, FPNUM consts, `gfx_round_arga_de`, `gfx_build_half`) | resident ~200 B | **tenant** (page-1 reaches float pack) |
| Aspect float math (`circ_asp_*`) | resident ~80 B | **tenant** |
| `eval`/`parse_coord`/`gfx_eval_int16` | resident | **resident** (bounced) |
| Geometry draw (`GFX_OP=4`) | tenant | tenant (unchanged) |
| **New:** resident servicer loop + arg-type dispatch | — | resident ~70 B |

**Projected reclaim ≈ (120+200+80 moved) − (70 new resident) ≈ ~330 B gross, ~150–260 B net**
after the tenant-side re-hosting overhead. **MEASURE-FIRST is impl step 1** (the recurring
lesson): build the tenant shell + resident servicer, measure the real page-1 delta before
declaring the trap wall funded. If the measured reclaim is < ~160 B, STOP-and-confirm.

## 5. Implementation plan

1. **Measure-first skeleton:** add `SUBROM_IDX_CIRCLEPARSE` (page-1 sub table), a
   `gfx_circle_parse` tenant shell in `sub/graphics.asm`, the resident servicer loop, and the
   `GFX_DREQ` arg-type protocol. Move the grammar walk + float math into the tenant. Build
   `basic-reloc`; **measure `__MEAS_PAGE1_END`** — confirm the reclaim ≥ what T1 needs.
2. **Green the differential:** `make graphics-acceptance` (the CIRCLE corpus — full ellipse,
   arcs, spokes, aspect, colour, STEP, the comma-in-expression case) must stay byte-identical
   to the pre-change behaviour AND to the VG-8020. Add a comma-in-expression case
   (`CIRCLE(x,y),POINT(3,4)`) if the corpus lacks one — the co-routine's boundary handling
   depends on it.
3. **Host tests:** extend `tests/test_graphics.py` for the tenant's grammar state machine +
   the resident servicer's arg-type dispatch (emulator-free).
4. **Standing sweep:** `basic-reloc` (lean byte-identity + `--page1` closure with the new
   tenant), `unit-test`, `graphics-floor-acceptance`; commit.
5. **Then** return to interrupt-traps T1 (the freed room funds the tenant-dispatch trap
   architecture — NOT the 364 B full-resident version; the traps also go tenant-dispatch).

## 6. Risks

- **Highest — a parser re-architecture must stay bug-for-bug identical.** CIRCLE's grammar has
  many subtle exits (empty fields, the shared "this comma also intros the next field" commas,
  ERR 2/5/6 raises, the aspect double-scale trap noted at `circ_asp_done`). The
  `graphics-acceptance` differential is the gate; every exit path needs a corpus case.
- **Page-1 tenant float-pack closure.** The tenant calling `fp_mul`/`fp_cmp`/`fp_div`/`fp_add`/
  `flt_to_int16` must pass `check_tenant_closure.py` (all its callees in the low region). The
  G4 slice already proved the CIRCLE math works in a sub-ROM context (it IS the geometry
  tenant's neighbour) — but the *page-1 tenant* calling the float pack is the fp_sqrt pattern,
  well-trodden.
- **Reclaim shortfall.** If step-1 measurement shows < ~160 B, this doesn't fully fund the
  traps and we reassess (PAINT next, or a leaner trap dispatch). Measure before the full push.

## 7. Decisions for sign-off

- **D-CC-1 — CIRCLE is a PAGE-1 tenant** (not page-0), so the float math moves too. The whole
  reclaim depends on this. *Recommend as written.*
- **D-CC-2 — measure-first (step 1)** before the full re-host + green push. *Recommend.*
- **D-CC-3 — the traps go tenant-dispatch** after this lands (the 364 B full-resident version
  is retired; CIRCLE's ~150 B funds a tenant-dispatch trap, not the resident generic).
  *Recommend.*
- **D-CC-4 — gate = `graphics-acceptance` byte-identity** + a comma-in-expression case.
  *Recommend.*
