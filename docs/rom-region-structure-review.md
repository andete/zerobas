# ROM REGION STRUCTURE REVIEW

Filed 2026-07-30 against `19e8bfd` (lean-cart retirement S1+S2+S3 complete, tree
clean, all gates green). TODO item: "ROM REGION STRUCTURE REVIEW", deliberately
sequenced after S3 so the source reads with no `IF ROM_BASE` wrappers obscuring
which region anything sits in.

**No code changes in this document.** The action it recommends is specced
separately in [`spec-rom-region-rebalance-r1.md`](spec-rom-region-rebalance-r1.md).

---

## 0. The instrument, and its own control

pasmo emits no listing file, so per-file byte extents are not directly available.
Every size in this document comes from **zero-byte measurement labels injected
around every `include` site** (111 sites, recursively — bodies inside bodies), in
throwaway copies of the tree.

⚠️ **The instrument's control is byte-identity.** Both instrumented images were
assembled and compared against the shipped ROMs:

| image | result |
|---|---|
| `basic-reloc.rom` (22510 B) | **byte-identical** |
| `sub.rom` (32768 B) | **byte-identical** |

so the labels demonstrably emit nothing and the extents are the real ones. This is
the same discipline S3 used: a measurement whose apparatus is not itself gated is
not a measurement.

⚠️ **The sub-ROM pads with `$FF`, not `$00`** (`ds $4000-$,$FF` / `ds $8000-$,$FF`
in [`sub/sub.asm`](../sub/sub.asm)). A trailing-zero scan reports 0 B free and is
wrong. Its free space here is read from injected `__MEAS_SUB_P0_END` /
`__MEAS_SUB_P1_END` labels — the same mechanism `check_reloc.py` already uses for
the main ROM's two walls, not a byte scan.

### 0.1 Three apparatus errors found and fixed *during* the review

Recording these because two of them produced confident, wrong, citable rows, and
one of those rows would have steered a crashing change.

1. **A conditional branch read as a terminator.** My first dead-code triage used
   `^\s*(ret|reti|retn|jp|jr)\b` as the "nothing falls through here" test, which
   matches `jp nc,gfx_syntax` and `ret nz`. It reported `ei_set`
   ([`basic/program.asm:1619`](../basic/program.asm:1619)) and `spr_set`
   ([`basic/graphics.asm:690`](../basic/graphics.asm:690)) as **dead**. Both are
   fallthrough-entered and live. Fixed by reusing
   [`tools/check_tenant_closure.py`](../tools/check_tenant_closure.py)'s own
   `_is_terminator`, which handles the condition field.
2. **Lines before a file's first label belonged to no span**, so references made
   there were invisible. That reported `sp_done`
   ([`basic/sprtrap-body.inc:84`](../basic/sprtrap-body.inc:84)) as dead — it is
   the target of a `jr z,sp_done` twelve lines above it, in exactly that
   unscanned prologue. Fixed with a synthetic always-live prologue span per file.
3. 🔴 **A call-graph-only closure missed a DATA reference, and the row it produced
   was actively dangerous.** `zkey_hook` — the C-BIOS function-key hook, the one
   thing [`basic/keytrap.asm`](../basic/keytrap.asm) says "genuinely cannot leave"
   the low region — is installed by `ld hl,zkey_hook`
   ([`basic/subrom-boot.asm:118`](../basic/subrom-boot.asm:118)), not by a
   `call`/`jp`. Walking only call/jp/jr/djnz therefore never reached it, and
   `keytrap.asm` came out **"PRESSURE-PLACED (whole)"** — i.e. the review would
   have nominated the `$0038` keyboard hook for promotion into page 1, where a
   page-1 sub-ROM tenant pages it out and a keystroke arrives into whatever the
   tenant has mapped there. Fixed by closing over **every identifier a span
   mentions** (call, jump, `ld hl,label`, `dw label`) plus fallthrough plus
   `include` prologues, and by **asserting** `zkey_hook` and `sp_done` land in the
   forced set — the assert is what stops that row coming back.

4. 🔴 **"DEAD" IS PER-BUILD, AND THE SWEEP ONLY ASKED ONE BUILD.** Found by the
   assembler, not by me, when R1's implementation deleted C3 (§4) and
   `pasmo` stopped with `Symbol 'disk_putword' is undefined`. The sweep walks
   `basic/main.asm`'s include closure — 49 files. `disk_putword` is defined in
   [`basic/sv-diskwr.inc`](../basic/sv-diskwr.inc), which **both** ROMs assemble,
   and its only caller is in [`basic/sv-bsvdisk.inc`](../basic/sv-bsvdisk.inc),
   which **only `sub/save.asm` includes** (the whole BSAVE/SAVE write engine is a
   page-1 tenant). So the caller sat outside the walked closure and was invisible:
   the routine is genuinely dead in main and genuinely live in sub. Correct fix is
   `IF SUB_BUILD`, not deletion — same 16 B off main page 1, `sub.rom` byte-identical.
   **For any future sweep over a shared body `.inc`, "is this dead?" has two
   answers and you must ask both.**

**The lesson, in this file's terms:** the escape a placement contract needs to be
safe from is not always a `call`. Three of the four contract-forced files here are
reached by something other than a plain call edge — and a fourth error came from a
reference that was not in the file set at all.

⚠️ **Three of these four produced a confident wrong row, and the tree caught only
one of them.** Errors 1–3 were caught by my own controls and asserts; error 4 was
caught by `pasmo`. **Nothing in the review's own apparatus would have found error 4**
— it took building the change. That is the argument for R1 being an implemented
slice rather than a paper recommendation.

---

## 1. THE FRAMING MEASUREMENT — confirmed, and sharpened

Measured from clean (`rm -rf build && make basic-reloc`) at `19e8bfd`:

| region | span | used | free |
|---|---|---|---|
| main low | `$2812-$3FFF` | 6126 B | **0 B** (hard wall) |
| main page 1 | `$4000-$7FFF` | 16377 B | **7 B** |
| sub-ROM page 0 | `$0000-$3FFF` | 12330 B | **4054 B** |
| sub-ROM page 1 | `$4000-$7FFF` | 13027 B | **3357 B** |

The carried-forward figures hold: **7411 B unused in the sub image (22.6%) against
7 B in the whole main ROM.** The main ROM is not full-because-it-must-be, it is
**unbalanced** — and the sharpening is that *there is nothing to rebalance yet*:
main has 7 free bytes in total, so "relocate a small leaf between the two
co-mapped regions" cannot be the first move. **Something has to free bytes before
the rebalance has anything to spend.** §4 is that something.

---

## 2. SCOPE ITEM (1) — CONTRACT-FORCED vs PRESSURE-PLACED, separated

A main-ROM routine is **contract-forced low** (`< $4000`) if it can execute while
main page 1 is switched out. Two ways that happens, and they are the two the
closure gates already encode:

* **(a)** it is in the closure of the resident-ABI exports
  ([`sub/basic-resident-abi.inc`](../sub/basic-resident-abi.inc)) — a page-1
  sub-ROM tenant calls back into it;
* **(b)** it is on the `$0038` ISR path (`htimi_guard`, `zkey_hook`,
  `sub_int_template`) — an IRQ can land inside a page-1 tenant.

Closed over all reference kinds + fallthrough + include prologues: **165 forced-low
labels** of 424 in the region.

| file | forced | free | verdict |
|---|---|---|---|
| [`basic/keytrap.asm`](../basic/keytrap.asm) | 4 | 0 | **CONTRACT-FORCED (whole)** |
| [`basic/sprtrap-body.inc`](../basic/sprtrap-body.inc) | 1 | 0 | **CONTRACT-FORCED (whole)** |
| [`basic/float.asm`](../basic/float.asm) | 35 | 2 | MIXED (effectively forced) |
| [`basic/float-arith.asm`](../basic/float-arith.asm) | 116 | 75 | MIXED |
| [`basic/subromcall.asm`](../basic/subromcall.asm) | 4 | 2 | MIXED |
| [`basic/arrays.asm`](../basic/arrays.asm) (low half) | 2 | 37 | MIXED |
| [`basic/str-engine.asm`](../basic/str-engine.asm) | 3 | 99 | MIXED |
| [`basic/input.asm`](../basic/input.asm) | 0 | 33 | **PRESSURE-PLACED (whole)** |
| [`basic/main.asm`](../basic/main.asm) message pool | 0 | 9 | **PRESSURE-PLACED (whole)** |

### 2.1 🔴 THE STRUCTURAL FINDING: the contract is ONE-DIRECTIONAL

Running the mirror walk — which **main page-1** routines does a sub-ROM **page-0**
tenant call back into? (a page-0 tenant runs with main page 0 switched out, so
those would be forced to page 1) — the answer is measured, and it is:

> **ZERO.** All 13 page-0 tenants, 709 routines of closure, call **no main routine
> at all**. They are pure sub-local + RAM leaves.

Falsification control: re-seeding the identical script with the **page-1** tenant
table finds 20 main callees (9 BIOS entries + the 11 resident-ABI floats), so the
walk is live and the zero is a result, not a broken script.

**Consequence: nothing whatsoever in main page 1 has a placement contract.** All
16377 bytes of it are pressure-placed. The whole `$4000` contract surface points
one way — *low-region content that page-1 tenants and the ISR reach must stay
low* — and page-1 placement is purely a packing outcome. That is a much simpler
structure than `main.asm`'s scattered "lands in the reclaimed low region rather
than page 1 (page 1 is otherwise full to `$7FFF`)" comments suggest, and it means
**page-1 → low moves are always legal** (they are only ever blocked by the low
wall) while **low → page-1 moves need exactly one check: the §2 forced set.**

### 2.2 Promotion candidates, sized

Largest **contiguous** pressure-placed runs in the low region — i.e. what could be
promoted to page 1 if page 1 had room:

| bytes | span | file | head label |
|---|---|---|---|
| 1171 | `$2884-$2D17` | `str-engine.asm` | `pu_deref_body` |
| 586 | `$397C-$3BC6` | `float-arith.asm` | `abs16` |
| 549 | `$3D84-$3FA9` | `arrays.asm` | `ary_parse_call` |
| 446 | `$2ED9-$3097` | `input.asm` | `input_console` |
| 419 | `$2D32-$2ED5` | `str-engine.asm` | `sfi_nowrite` |
| **80** | **`$3FB0-$4000`** | **`main.asm`** | **`err_linebuf_overflow`** |

Candidate supply is ~3.3 KB. **Supply is not the constraint — page-1 room is.**

---

## 3. SCOPE ITEM (2) — DE-EVICTION: measured, and REFUTED

The TODO's hypothesis: a small tenant's resident footprint (trampoline +
dispatch-table entry + argument marshalling) can exceed the routine itself, so the
cost curve is not monotonic in size and some existing tenants may be on the wrong
side of it. De-evicting those would free main bytes *and* shrink the tenant count,
the ABI import list and the closure-gate surface.

**Measured, it does not happen anywhere in this tree.** Smallest tenant bodies
against their resident stubs:

| tenant | body (sub) | resident stub | margin | site |
|---|---|---|---|---|
| `beep_tenant` | 74 B | ~12 B marginal (16 B total) | +62 | [`basic/sound.asm:130`](../basic/sound.asm:130) |
| `dirverb_tenant` | 77 B | **~42 B across TWO call sites** | +35 | [`files.asm:1215`](../basic/files.asm:1215), [`:1283`](../basic/files.asm:1283) |
| `title_tenant` | 78 B | **7 B** (`ld ix` + `jp`) | +71 | [`basic/title.asm:30`](../basic/title.asm:30) |
| `fld_lookup_tenant` | 81 B | 22 B (body was 60 B → returns 38 B) | +38 | [`basic/field.asm:412`](../basic/field.asm:412) |
| `scan_stmt_end` | 93 B | ~18 B | +75 | [`basic/interp.asm:1342`](../basic/interp.asm:1342) |
| `deftype_tenant` | 181 B | ~26 B | +155 | [`basic/usr.asm:240`](../basic/usr.asm:240) |

The largest stub cost observed is **~42 B** (`dirverb`, the one tenant with two
resident call sites — the case most likely to cross) against the **smallest body in
the tree, 74 B**. The curve does not cross, and it is not close: every tenant is on
the right side by ≥35 B.

**Verdict: de-eviction frees no main-ROM bytes. Do not spend a slice on it.** The
simplification argument (fewer tenants, shorter import list, smaller gate surface)
survives on its own merits but must be costed as a *net main-ROM loss* of 35–155 B
per tenant, against a 0 B wall. That is the answer to "weigh de-eviction equally":
it was weighed, on the same scale, and it loses.

### 3.1 The duplication tax — measured, and contract-forced

Eight body `.inc` files are assembled into **both** ROMs. Main-ROM cost:

| bytes | file | in |
|---|---|---|
| 111 | `basic/fatio-body.inc` | `fat.asm` |
| 89 | `basic/tokskip-body.inc` | `interp.asm` |
| 79 | `basic/fatiow-body.inc` | `fat.asm` |
| 48 | `basic/pdfcb-body.inc` | `bload.asm` |
| 44 | `basic/sv-diskwr.inc` | `save.asm` |
| 37 | `basic/sv-tne.inc` | `save.asm` |
| 35 | `basic/fatiocreate-body.inc` | `fat.asm` |
| 30 | `basic/cal-refill-body.inc` | `cload.asm` |
| **473** | **total, all PAGE 1, all also present in `sub.rom`** | |

Tempting, and **not reclaimable**: a page-1 tenant cannot call main page 1, so each
sub-local twin is contract-forced. The transitive sweep in §4 confirms the main-side
copies still have live main-side callers — with **exactly one exception**, 16 B of
`sv-diskwr.inc`, which §4 takes. Recording the negative so the next reader does not
re-derive it: **457 of the 473 B are genuinely live on both sides.**

---

## 4. THE FREE CARVE — 122 B, and it is bigger than the TODO expected

The TODO carried forward one known carve (`vars.asm`'s dead int-only pool) with the
instruction "**measure the ROM saving before assuming it is large**". Measured, it
is 80 B — and a **transitive** sweep finds two more the per-symbol warnings cannot.

pasmo's "never used" is per-symbol, so it cannot see a routine that *is* referenced
but only from code that is itself dead — which is exactly `var_find`'s shape. The
sweep models each label's linear span, marks a span live if it is a seed, mentioned
by a live span, or fallthrough-entered from one, and iterates to a fixed point.

✅ **This sweep is no longer a scratchpad script.** It landed as
[`tools/check_dead_code.py`](../tools/check_dead_code.py), a hard gate inside
`make basic-reloc` over **both** builds, carrying all four §0.1 fixes
(`docs/spec-deadcode-gate.md`). Its first finding as a standing gate was 24 B in
`sub/graphics.asm` — `gfx_border_read`, orphaned when the VG-8020 PAINT bug fix
replaced it with `gfx_paint_read`.

⚠️ **Seeded on build consumers only** (`init` + `sub/` + `tools/`). A reference from
`tests/` or `probes/` is *not* a reason to keep ROM bytes — seeding on those too
hides the whole `vars.asm` block, because S3's ported tests still name it. That
seed choice is the difference between 16 dead spans and 4.

**Falsified both ways** (an injected dead routine is found; the same routine with
one live caller is not reported):

| # | block | region | bytes | evidence |
|---|---|---|---|---|
| C1 | `var_find` + `var_get_key` + `var_set_key` (12 labels) | PAGE 1 `$4760-$47B0` | **80** | the retired lean build's int-only fixed-pool store. [`basic/vars.asm:265`](../basic/vars.asm:265) **already calls it "the dead int-only `var_find` walk above"** |
| C2 | `div_de_bc` + `mod_de_bc` + `div_zero` | PAGE 1 `$523C-$5256` | **26** | the integer `/`/MOD helpers, superseded by the float pack. `udiv16` below them stays (live). **Not visible to pasmo for `div_zero`** — it is referenced, only from C2 |
| C3 | `disk_putword` | PAGE 1 `$6B63-$6B73` | **16** | [`basic/sv-diskwr.inc`](../basic/sv-diskwr.inc); **NOT dead code — see §4.1.** Dead in the MAIN build, live in the SUB build. Gated `IF SUB_BUILD`, not deleted. The one reclaimable byte of §3.1's 473 |
| | **total** | **all PAGE 1** | **122** | **0 B of it in the low region** |

⚠️ **RAM: ZERO bytes freed, and the TODO said 128.** `VARTAB`/`VARENTSZ`/`VARSLOTS`/
`VAREND` do describe C1's dead pool and are read by nothing — but the pool's
`$E1C0..$E240` **span was already spent**, by three later slices that each described
themselves as homing in "the freed VARTAB window": `ARYTAB` `$E1C0` (arrays 4b),
`DIRECTF` `$E1C2` (error-handling S1), `SAVSTK` `$E1C3` + `SAVTXT` (S2b), `ZTRAP`
`$E1D1..$E207` (interrupt traps). Only `$E226..$E23F` is free and it is accounted for
separately. All four equates were deleted as pure hygiene (they emit no bytes);
[`basic/sysvars.inc`](../basic/sysvars.inc)'s comment block, which still claimed the
span was freed RAM, was corrected in place.

⚠️ **"`VAREND` must stay — cells above it are placed relative to it" was also stale.**
Measured: nothing in any build references `VAREND` except C1's dead block, and
`STRTAB` — the constraint the comment named — is itself retired. It is vestigial, and
went with the rest.

🔴 **The carve is entirely in PAGE 1. It does not touch the 0 B hard wall.** Taken
alone it moves the walls to low 0 B / page 1 129 B — i.e. it makes the *roomy* wall
roomier and leaves the binding one exactly where it was. That is the finding that
decides what to do next.

---

## 5. THE RECOMMENDED ACTION — R1: carve, then spend it on the hard wall

§2.1 established that low → page-1 moves need only the §2 forced-set check, and
§2.2 that there is 3.3 KB of pressure-placed low-region content. §4 frees 122 B of
page 1. Together those compose into the rebalance the framing measurement asked
for, and the [[promotion-funds-low-region]] rule ("the walls are COUPLED") is
exactly this shape:

1. **carve** C1+C2+C3 → page 1 free `7 → 129 B`;
2. **promote** the 80 B low-region message pool
   ([`basic/main.asm`](../basic/main.asm) `err_linebuf_overflow` …
   `__MEAS_LOW_END`) into page 1 → low free `0 → 80 B`, page 1 free `129 → 49 B`.

**Projected walls: low 80 B free, page 1 49 B free** — both off zero for the first
time in the arc, from 0 B / 7 B.

Why that block is the right 80 B to move, in evidence order:

* it is **PRESSURE-PLACED (whole)** — 0 forced labels (§2), and
  [`main.asm`](../basic/main.asm)'s own comment says it was split across both
  regions only because "page 1 could not hold it";
* **all of its readers are already in main page 1** — `err_msgtab`
  ([`interp.asm:899`](../basic/interp.asm:899), [`:949`](../basic/interp.asm:949)),
  `dl_overflow` ([`program.asm:114`](../basic/program.asm:114)), and files.asm's six
  OPEN reject sites. The move puts the data *beside* its readers;
* **zero sub-ROM references** — verified for all 8 symbols in the block. No page-1
  tenant reads it, so promotion cannot page it out from under one;
* it is the **only** candidate run that fits in 122 B. The next smallest is 419 B.

Specced for sign-off in
[`spec-rom-region-rebalance-r1.md`](spec-rom-region-rebalance-r1.md).

---

## 6. SCOPE ITEM (3) — the split, the ABI and the three gates

Interrogated, and the recommendation is **leave them alone**. Measured reasons:

* The three closure walks are **not redundant** — they encode three different and
  genuinely opposite visibility facts, and §2.1's mirror result shows the page-0
  walk is currently proving a *vacuous* property (0 main callees). ⚠️ **That does
  not make it removable** — it is the gate that keeps it at zero, and a future
  page-0 tenant calling a main low-region routine is precisely the crash it exists
  to catch. It is a green-because-enforced row, not a green-because-untested one.
* The resident-ABI import is **11 symbols, closing over 122–172 routines** (122 by
  call edges, 172 including data refs). It is already minimal in the sense that
  matters: every one of the 11 is a shared FAC operation with multiple resident
  callers, so none could be evicted anyway.
* `SUBROM_ENTRY_BASE_P0`/`_P1` index space: **13 page-0 + 22 page-1 tenants**, and
  the sub image has room for far more. **Tenant count is not a constraint.**
* The one real asymmetry: sub page 0 has 4054 B free vs page 1's 3357 B, and page 0
  is the *cheaper* island to be a tenant on (a page-0 tenant may call main page 1,
  where main's bulk lives; a page-1 tenant may only call the low region, which is
  what forces the §3.1 duplication). **Future evictions should prefer page 0** —
  that is a costing rule, not a restructure.
  🔴 **AND THE RULE WAS UNUSABLE AS WRITTEN** ([D-EVLNO](spec-rom-region-evict-lineno.md),
  2026-08-05). Free *bytes* were the wrong measure: the page-0 **entry table** is
  full — 13 rows `$0010..$0036`, **one spare byte** before the fixed `$0038` IM1
  vector (`$0037` reads `FF`, `$0038` reads `C3 0A F1`; measured, and
  `sub/sub.asm` + `sub/equates.inc` both already said so). A 14th row would
  overwrite the vector. So a rank-4 candidate that genuinely needs to call main
  page 1 was **blocked** until `SUBROM_ENTRY_BASE_P0` was relocated past `$0038`,
  and nobody had connected that to the rule above. ✅ **Done —
  [D-P0BASE](spec-rom-region-p0base.md), base `$0040`, index 13 free, no cap.**
  ⚠️ With one correction it had to make: "every call site is symbolic" is true of
  `basic/*.asm` (18 sites) and **false of the harness** — three probes carried the
  entry address as a hardcoded *byte* inside injected machine code.
  🔴 **AND THE JUSTIFICATION ABOVE IS THE WRONG ONE** (D-P0BASE). The visibility
  argument — a page-0 tenant may call main page 1 — is worth **at most 95 B** across
  all **268** page-0-legal main page-1 entries, is claimed by **zero** of them, and
  lands on the wrong wall: the shared members a cluster leaves behind stay resident
  either way, so **the main-ROM saving is identical on both islands** and the clone
  is a *sub*-ROM cost, against 6237 B of sub headroom. §3.1's "Main-ROM cost" column
  answers a different question (can main's own copies be deleted — no), not the
  price of siting a tenant on page 1. It is also structurally unreachable: **777 of
  1045** page-1 labels are page-0-ILLEGAL and every one of the 268 legal ones is a
  leaf, because reaching into main page 1 transitively reaches `eval` (low region)
  or `pchar` → `CHPUT` (BIOS) and becomes illegal in the same step.
  **The rule is still right, for a CAPACITY reason measured as a trend rather than
  at one instant** ([[which-wall-binds-is-a-history-question]] applied to the sub
  walls): the table filled at `6c72931` (2026-07-29); sub page 0 has been **frozen
  at 3913 B free for the 9 commits since** — by construction, a new tenant needs a
  row — while page 1 absorbed **1015 B** over the same span. Page 0 held **63 %** of
  the sub-ROM's free space and could accept nothing. This section compared the two
  islands' free space **once**, and drew "page 0 is roomier, so prefer it"; the
  trend says **page 0 was roomier because it was closed.**

---

## 7. Candidate table — ranked, with the next tier costed

| rank | candidate | frees | in | cost | risk | status |
|---|---|---|---|---|---|---|
| 1 | **C1+C2+C3 dead-code carve** (§4) | **122 B** | page 1 | **0** | none — unreachable code, falsified sweep | ✅ **R1 LANDED** |
| 2 | **promote the 80 B message pool** (§5) | **80 B** | **low (the hard wall)** | 80 B of page 1 | low — pressure-placed, all readers page-1, 0 sub refs | ✅ **R1 LANDED** |
| 3 | promote `input.asm` (**458 B**, pressure-placed whole) | 458 B | low | 458 B of page 1 | low | 🔴 **DECLINED** — [D-PINDATA](spec-rom-region-promote-input.md). Short 157 B, and the premise is inverted: low moved 3× in 31 commits, page 1 moved 20+ |
| 4 | evict a page-1 file to a sub **page-0** tenant (§6) | body − stub | page 1 | 12–42 B stub | medium — needs a closure-clean seam | ✅ **OPENED + COSTED** — [D-EVLNO](spec-rom-region-evict-lineno.md). `parse_lineno`: **73 B body, 18 B stub, 55 B net**, page 1 **301 → 356 B**. The page-0 island was FULL; ✅ **REOPENED** by [D-P0BASE](spec-rom-region-p0base.md) — base `$0040`, index 13 free, no cap, 44 B of sub page 0 |
| 5 | de-evict any tenant (§3) | **nothing** | — | **35–155 B loss** | — | **REFUTED, closed** |
| 6 | reclaim the 473 B duplication tax (§3.1) | 16 B (taken as C3) | page 1 | — | — | **457 B contract-forced, closed** |
| 7 | merge the two main regions | — | — | — | — | **not on the table** — `$4000` is a hardware contract |

**What this review deliberately does not do:** rank rank-4 evictions per file.
Every eviction in the arc's history was costed one at a time and the cost was
dominated by **siting, not substance** (D-FCH S-FCH-1: 43 → 9 → 5 B for the same
fix), so a per-file eviction estimate made from reading code would be a hypothesis
presented as a measurement. Rank 4 should be opened only when ranks 1–2 are spent,
and then one candidate at a time, costed by **building** it.

🔴 **AND §0.1's ERROR 3 FIX NEVER REACHED THE SHIPPED TOOLS**
([D-PINDATA](spec-rom-region-promote-input.md), 2026-08-05). The data-reference
closure this review had to build to stop nominating `keytrap.asm` went into
`check_dead_code.py` and nowhere else: `tools/check_tenant_closure.py` — named
above as **the feasibility oracle for this review** — and `tools/promote_scout.py`
both matched only `call|jp|jr|djnz`. `basic/float.asm`'s three `tkf_ref*` bound
tables (15 B) sit in the resident-ABI closure via `ld de,tkf_ref32768` alone, so
the scout graded them `PROMOTABLE` and relocating them into page 1 left the gate
printing `OK`. **§2's own table had `float.asm` right** ("MIXED, effectively
forced") — the shipped tool disagreed with the review that commissioned it, and
the tool is what a later slice would run. Both now carry a data pass.

---

## 8. Answers to the TODO's own questions

| question | answer |
|---|---|
| Is the main ROM full or unbalanced? | **Unbalanced.** 7 B free against 7411 B of sub-ROM headroom. Confirmed from labels, not an `$FF` scan. |
| Which placements are contract-forced vs pressure-placed? | §2. **165 of 424** low-region labels forced; `keytrap.asm` + `sprtrap-body.inc` forced whole; `input.asm` + the message pool pressure-placed whole. |
| Is 7411 B of headroom 7411 B of relief? | **No**, and the reason is now measured: relief is bounded by what can legally leave, and the cheapest legal move available today is 122 B + an 80 B promotion. |
| Are some existing tenants on the wrong side of the cost curve? | **No.** §3 — measured margin ≥35 B on every one, largest stub 42 B vs smallest body 74 B. |
| Could the split / ABI / three gates be unified or simplified? | **No, and should not be.** §6 — the three walks encode three different facts, and the page-0 walk's vacuous pass is enforcement, not absence of coverage. |
| How large is the `vars.asm` carve? | **80 B ROM + 0 B RAM.** The instruction to measure it before assuming was right twice over: the sweep it prompted found **42 B more** in two blocks nobody was looking at, and the "128 B of freed RAM" the TODO carried forward turned out to be **already spent** by three later slices (§4). |

---

## 9. R1 outcome — ✅ LANDED 2026-07-30

Implemented per [`spec-rom-region-rebalance-r1.md`](spec-rom-region-rebalance-r1.md).
**Measured from clean:**

| | before | after | specced |
|---|---|---|---|
| main low `$2812-$3FFF` free | 0 B | **80 B** | 80 B ✅ |
| main page 1 `$4000-$7FFF` free | 7 B | **49 B** | 49 B ✅ |
| `build/sub.rom` | — | **byte-identical** (`1dbbfe2f…`) | required ✅ |

The `jr`-may-return byte (spec §1.2) **did not** come back: page 1 reads 49 B, not 50.

Two spec deviations, both forced by measurement: **A3 became a gate, not a deletion**
(§0.1 error 4), and **A4 freed no RAM** (§4). Both are recorded above rather than
quietly absorbed.

Gates: unit **54/54** · diskbasic **34/34** · bdos **12/12** · fat-error **7/7** ·
abort **31/31** · error-trap ALL PASS · chancost **39/1** · probe ALL PASS · machines
OK · linemax **60/60** (ERR 25 end-to-end — its string moved) · the three closure
walks + `check_resident_abi` + `check_kwtable_identity` OK.

Rows that specifically cover the moved content, named rather than folded into
"suite green" (spec §4.1): `tests/test_msgenc.py` decodes all 27 message strings from
the ROM including `err_linebuf_overflow`/`err_overflow` and ERR 52/59's
`err_bad_filenum`/`err_file_notopen`, plus a dedicated `overlap` row asserting
`err_overflow == err_linebuf_overflow + 12`; `chancost-characterize`'s `err_badchan`
(BFN == BFN) and `err_notopen` (59 == 59) exercise the two **moved raisers**
end-to-end against the reference machine.

**Falsification set, with its green control** (S3's lesson: a red row reads as
success): re-wording `err_overflow`'s tail alone broke **both** messages
(`err_linebuf_overflow` → 'Line buffer spilled'), proving the overlap is load-bearing
*and* gated; splitting the two strings apart tripped the dedicated overlap row
("the err_linebuf_overflow -> err_overflow overlap is broken"); and a comment-only
edit to the same block left all 27 messages passing. Two reds for two distinct
reasons, one green.
