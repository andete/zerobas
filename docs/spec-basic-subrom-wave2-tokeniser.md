<!-- Provenance: original work (own-design spec over our own tokeniser + the ratified sub-ROM ABI). -->
# Spec — sub-ROM eviction WAVE 2: the whole tokeniser

**Status: ✅ IMPLEMENTED + GATED 2026-07-11.** Signed off then shipped this
session. The whole tokeniser body (`tokenise`/`tk_*`/`tk_hex`/`match_kw`/
`branch_lineno`) was extracted to [`basic/tokenise.inc`](tokenise.inc) and evicted
to sub-ROM page 0 ([`sub/sub.asm`](../sub/sub.asm) index 1 = `SUBROM_IDX_TOKENISE`),
reunited with the wave-1 `tk_float` crunch ([`sub/tkfloat.asm`](../sub/tkfloat.asm),
now an in-slot callee). The repack main ROM keeps only a two-line `tokenise`
dispatch stub ([`basic/interp.asm`](../basic/interp.asm)); the lean 16 KB cart
assembles the body inline, byte-identical. Wave 1's per-literal CALSLT +
A-disposition protocol were reverted (§5). **Measured page-1 relief: ~23 B → 704 B
free (~681 B off the byte-full wall).** Worst-case DI span ~10 JIFFYs (~199 ms) for
a pathological 255-char line — cosmetic only (§6 R-W2-1(a)). All gates green (§7).

**Sign-off answers (retained):** **Q1 → (a)** ship with the whole-line DI span now
(cosmetic-only, post-Enter); **(b)** the `$0038` interrupt trampoline is DEFERRED
pending its own investigation (own slice when a tenant justifies it). **Q2 →
duplicate `kwtable`** sub-side (temporary — recovered by the wave-3 detok split,
§10). **Q3 → revert wave-1 dispatch**, folded into this wave (§5).

Slice spec for the sub-ROM arc
([spec-basic-subrom.md](spec-basic-subrom.md)); on sign-off it folds in as the
successor to §5's "S3 — eviction wave 1" (which shipped as the `tk_float` crunch,
not `float.asm` — see the arc memory). Cross-refs: wave-1 tenant
[`sub/tkfloat.asm`](../sub/tkfloat.asm), dispatch [`basic/subromcall.asm`](../basic/subromcall.asm),
the tokeniser [`basic/interp.asm:39`](../basic/interp.asm:39).

---

## 1. Proposal (the user's call, 2026-07-11)

> "D-5 was already approved — won't it make sense to put *all* tokenising in the
> sub-ROM?"

Evict the **entire repack-build tokeniser** to sub-ROM **page 0**, reuniting it
with the `tk_float` literal crunch that wave 1 already moved there. Today the
tokeniser is split three ways in the repack build:

| piece | today's home | page |
|---|---|---|
| outer loop + keyword/op/hex/name/string states (`tokenise`, `tk_loop`, `tk_*`, `match_kw`, `branch_lineno`, `tk_hex`) | main ROM, `interp.asm` after `$4000` | **page 1 (byte-full)** |
| float-literal crunch (`tk_float` …) | sub-ROM `tkfloat.asm` | sub page 0 |
| keyword table (`kwtable`) | main ROM low region | page 0 |

Wave 2 makes the tokeniser **one body in sub-ROM page 0** (+ a duplicated
keyword table), leaving only the two-site line-entry stub resident.

## 2. Why this is the right wave (not just possible)

1. **It relieves the *actual* wall.** The outer loop lives in **page 1**, the
   byte-full region (`interp.asm` is included after the `$4000` header,
   [`main.asm:87`](../basic/main.asm:87)). Wave 1's crunch eviction freed *page 0*;
   this frees *page 1*. Measured page-1 headroom today is **29 B** (`__MEAS_*`),
   so any page-1 body is worth evicting.
2. **The tokeniser is cold.** It runs only at line-entry and program-LOAD, never
   during RUN (the executor walks already-crunched tokens). So it fits the arc's
   standing rule exactly — *evict cold function-shaped bodies, keep runtime-hot
   paths resident* (the principle that swapped wave-1's tenant formatter→crunch).
3. **It reunites a split we already made.** Right now tokenising a numeric literal
   does `main → CALSLT → sub → return` **per literal**. With the whole tokeniser
   sub-side, `tk_loop`'s `jp tk_float` becomes an **ordinary in-slot jump** and the
   line pays **one** CALSLT total. Fewer slot switches, simpler code.
4. **It lets wave 1's contortions be reverted** (§5) — net simplification.
5. **Mechanism is proven.** D-5 dispatch, the absence path, and the
   separate-machine RAM-shuttle test bridge all shipped in wave 1; marginal cost
   is low.

## 3. The eviction surface (leaf-audit — DONE, verify at build)

The whole `tokenise` body was audited ([`interp.asm:39–593`](../basic/interp.asm:39)).
**No `RST`, `CALSLT`, `CHPUT`, `ISCNTC`, error-jump, `IN`/`OUT`, or any BIOS/
low-region touch anywhere in the path** — it is pure buffer computation over RAM.
That is the page-0-tenant purity precondition, and it holds.

**Moves sub-side (repack tokeniser body):** `tokenise`, `tk_loop` + every `tk_*`
state, `tk_hex`, `match_kw`, `branch_lineno`. In the repack build a digit/`.`
already routes to `tk_float` (sub), so **`tk_number` is not needed sub-side** —
integers exit through `tkfloat.asm`'s `tkf_emit_int_bc`. (`tk_number` stays in the
resident/lean source, still assembled for the lean cart.)

**Already sub-side:** the `tk_float` crunch ([`sub/tkfloat.asm`](../sub/tkfloat.asm)) —
becomes an in-slot callee of the co-located loop.

**Pure-leaf clones needed sub-side** (duplicate, byte-identical — resident copies
stay for the rest of the interpreter):
- `upcase` — **already cloned** in `tkfloat.asm`.
- `is_letter` → calls `upcase`. Clone.
- `is_ident_cont` ([`vars.asm:25`](../basic/vars.asm:25)) → calls `is_letter` →
  `upcase`. **Clone the whole chain.**
- `cmp16_bits`, `neg_de` — **already cloned** in `tkfloat.asm`.

**RAM cells:** `TKNAME`, `TKOVF`, `TKRADIX`, `TKRTOK` + all `tkfloat` `TK*` cells —
all in `sysvars.inc`, so **byte-address-identical** sub-side (sub.asm includes it).
No marshalling.

**Caller / stub sites — exactly two**, both in [`program.asm:50`](../basic/program.asm:50)
and [`program.asm:63`](../basic/program.asm:63) (direct-line + program-line entry;
ASCII LOAD/MERGE/CLOAD funnel through the same insert path). Each becomes:
`DI → set HL/DE → CALSLT sub tokenise entry → EI`, then act on the returned
cursors. Marshalling is nil — HL (source), DE (dest) pass through `CALSLT`
unchanged, exactly as the wave-1 crunch already relies on.

## 4. The keyword table — MUST duplicate, cannot move (the sharp trap)

`kwtable` is **shared**: read by `match_kw` (tokenise, evictable) **and** by
`detok_kw`/`detok_kw2` for **LIST** ([`list.asm:495`](../basic/list.asm:495),
[`list.asm:555`](../basic/list.asm:555)). LIST is I/O-bound (CHPUT) → **resident,
cannot go sub-side**. A page-0 sub tenant cannot see the main-ROM page-0 low
region either. Therefore:

> **The sub-ROM gets its OWN copy of `kwtable`; the resident copy stays put for
> LIST/detok.**

This is the exact shape of the `tkf_ref*`/`neg_de` precedent from wave 1 (a body
shared between an evictable and a resident consumer → duplicate, don't move).
Cost: one table copy in the sub-ROM's 32 KB (free); **page 1 is unaffected by the
table** (it already sits in page 0). It must be assembled from the *same*
`kwtable.inc` so the two copies can't drift — a build-time byte-identity assert on
the two `kwtable` images is a cheap guard and a named gate item.

## 5. Bonus: revert wave 1's dispatch contortions

Because `tk_loop`/`tk_end` are now co-resident with the crunch, `tk_float` can
`jp tk_loop` / `jp tk_end` **directly** again. Wave 2 therefore **removes**:
- the `crx_cont` disposition-byte protocol (A=0/1 return) in `tkfloat.asm`;
- the `subrom_call` dispatch stub in `basic/float.asm` (`tk_float` main-ROM stub);
- the per-literal CALSLT.

Net: the crunch reverts to its original, simpler jp-threaded form. Only the
**one** whole-tokeniser entry keeps a CALSLT stub (the two `program.asm` sites).

## 6. Risks

- **R-W2-1 — DI span (the material risk; a THREE-way choice, not two).** A page-0
  tenant is entered under `DI`: the inter-slot call transition is *always* done
  interrupts-off ([MSX2 TH Ch.5](https://konamiman.github.io/MSX2-Technical-Handbook/md/Chapter5b.html):
  "the interrupt is always inhibited when calling the object program"), because
  during the slot-register switch `$0038` momentarily points at the wrong bytes.
  Our `subrom_call` then holds `DI` for the tenant's *whole duration*. Wave 1 held
  it for one literal; wave 2 would hold it for a **whole line's** tokenise (a full
  keyword-table scan at every source position). Worst case (~255-char pathological
  line) is ~10⁵–10⁶ cycles — **multiple 50 Hz JIFFYs** (one JIFFY ≈ 71.6 k cycles).
  Options:
  - **(a) DI the whole tokenise** — current design. The dropped ticks are cosmetic:
    tokenise runs *after* Enter, no keystroke pending, no audio, so it only drifts
    `JIFFY`/`TIME` for a one-shot crunch — **no functional effect**. Simple. Ship
    wave 2 as-is. *(Sub-case: the ASCII tape-LOAD caller
    (`tape-realtime-read-buffering`) must keep tokenise between block reads — it
    buffers the whole line first; verify it still does.)*
  - **(b) The MSX2 "parallel interrupt" path** — faithful to how real MSX2 sub-ROMs
    avoid long DI spans. The standard call DIs the *transition*, but a long sub-ROM
    routine **re-enables interrupts itself**; that is only safe because the sub-ROM
    carries its **own valid `$0038` interrupt entry** in page-0 low memory. So we'd
    build an own-design sub-ROM interrupt **trampoline**: `$0038` handler saves the
    page-0 slot, switches page 0 back to the main/C-BIOS ROM, runs the real ISR
    (timer + keyboard + `H.TIMI`, which live in the paged-out BIOS), switches page 0
    back to the sub-ROM, `RETI` — the switch stub placed so it doesn't page out its
    own next instruction. Then the tokeniser `EI`s during its loop and the DI span
    collapses to the transition only. **This dissolves R-W2-1 entirely** and makes
    `zerobas-sub` a genuine MSX2-style sub-ROM — but it is **arc-level
    infrastructure, materially bigger than wave 2**, and it is the same subsystem
    that would unblock *every* future long page-0 tenant (see main-spec R3: the
    DI-span of a stream tenant). Best speccing as its own slice, seeded by this
    insight, *before or independent of* wave 2 — not folded into it.
  - **(c) Reject wave 2**, keep the current 3-way split; no new DI span at all.

  **Resolution (Q1) → (a).** Ship wave 2 under (a) now (measure + record the
  worst-case DI span); open (b) as a separate infrastructure slice when a tenant
  (math pack) justifies interrupt-live page-0 tenancy. Keeps wave 2 a clean
  eviction and gives the trampoline the design attention it deserves.
- **R-W2-2 — hidden resident dependency** (the recurring trap: `neg_de` bit twice).
  Mitigation: the leaf-audit above walked the *call chain* (`is_ident_cont` →
  `is_letter` → `upcase`), not just labels. Re-run the full chain audit at build;
  any callee that resolves in page 1/low-region and is also used resident → clone,
  don't link.
- **R-W2-3 — the two `kwtable` copies drift.** Mitigation: single source
  (`kwtable.inc`), build-time byte-identity assert (§4).
- **R-W2-4 — net page-1 relief is smaller than the body** because the two stub
  sites and any newly-resident glue cost page-1 bytes. Mitigation: **measurement is
  a pre-commit gate** (§7), not an assumption — wave 1 already showed dispatch
  bodies eat into freed space.

## 7. Gates (all must pass)

1. **Measurement pre-gate.** On the reloc build, record page-1 free before/after
   (`__MEAS_*`). Net relief = evicted body − (2 stub sites + glue). Must be
   **positive and reported**; if marginal, reconsider scope. Record the worst-case
   DI span (R-W2-1).
2. **`kwtable` byte-identity assert** (resident copy vs sub copy) passes.
3. **Tokenise correctness — the oracle gate is the arbiter** (wave-1 lesson: the
   ROM was right, the host bridge was wrong; trust openMSX over the harness).
   `make string-acceptance` (6 halves), float `float-acceptance` (3 halves,
   literals byte-identical), `make input-acceptance` (8) — all tokenise-path.
4. **`make subrom-acceptance`** — discovery + ABI round-trip still green with the
   new page-0 entry.
5. **`diskbasic-acceptance-repack` 34/34**, LIST/detok unaffected (proves the
   resident `kwtable`/detok path is untouched), ASCII LOAD/MERGE tokenise correct.
6. **Host `make unit-test`** — every tokenise-path test (~11+) rerouted through the
   separate-machine RAM-shuttle bridge (auto-installed when `subrom_call` present).
7. **Lean `basic.rom` byte-identical** — all sub-ROM code under `IF ROM_BASE <
   $4000`; the lean cart keeps its inline `tk_number`/`tk_hex`/`kwtable`/tokeniser
   unchanged.
8. **Reloc gate OK.**

## 8. Scope boundary

- **In:** the repack tokeniser body + `match_kw`/`branch_lineno`/`tk_hex`, its
  leaf clones, the duplicated `kwtable`, the two stub sites, the wave-1 revert (§5).
- **Out:** the lean-build tokeniser (unchanged by construction); LIST/detok
  (resident); any keyword-table *content* change; F3; the math pack.
- **Effort:** ~1 session, mechanism proven. The named pre-gates are the DI-span
  measurement (R-W2-1) and the full call-chain leaf-audit (R-W2-2).

## 9. Decisions — RESOLVED 2026-07-11

- **Q1 → (a).** Ship with the whole-line DI span now (cosmetic-only, post-Enter);
  *measure and record* the worst-case span. **(b)** the `$0038` interrupt trampoline
  is deferred to its own investigation slice (first tenant that might justify it =
  the math pack).
- **Q2 → duplicate `kwtable`** sub-side. Understood as **temporary**: the wave-3
  detok split (§10) makes both readers sub-side and drops the resident copy.
- **Q3 → revert** wave-1's `crx_cont`/float-stub dispatch, folded into this wave (§5).

## 10. Forward pointer — wave 3 (detok core split)

`kwtable`'s only two code readers are `match_kw` (tokenise, → sub here) and
`detok_kw`/`detok_kw2` (LIST, resident). This wave leaves **two** copies. A **wave 3**
that splits the LIST detokeniser into a **pure-compute core** (token→text into a RAM
buffer, sub-side, sharing *this* wave's `kwtable` copy) + a **thin resident drain**
(buffer→`pchar`/`PRDEST`) would make *both* readers sub-side → **drop the resident
`kwtable`** (recovering Q2's duplication + its low-region bytes) and free the
detok-core code from page 1. Not folded here — detok is a *streaming* body (~20
inline `pchar` sites) with multi-byte lookahead, so buffer-produce + a resumable
chunked-`CALSLT` ABI is a real refactor. Sketched in
[spec-basic-subrom-wave3-detok.md](spec-basic-subrom-wave3-detok.md).
