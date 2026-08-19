<!-- Provenance: own-design over the ratified sub-ROM ABI ([[subrom-arc]], spec-basic-subrom-wave2-tokeniser.md §3) + our own float core. No reference-ROM disasm ([[no-reference-rom-disasm]]). -->
# Spec — sub-ROM PAGE-1 math tenant + `fp_sqrt` migration (DRAFT, awaiting sign-off)

**Status: ✅ IMPLEMENTED (2026-07-13) — all gates green.** `SQR` runs as the first sub-ROM
page-1 tenant; `math-acceptance` byte-identical (199/0), lean `basic.rom` byte-identical,
sub/float/unit gates green. Three real bugs surfaced + fixed en route (see §3, §4): the
`A`-across-CALSLT ABI, and TWO transitive page-1 escapes (`cmp16_bits`, `div10`). Migrating
`SQR` first — a known-good gated oracle — is exactly what made these loud and isolated.
§8 as resolved: new `gen_resident_abi.py`; **STRONG consistency gate** (`check_resident_abi.py`);
plus a **standing page-1-escape closure gate** (`check_tenant_closure.py`, §4) added after the
manual leaf-audit missed both escapes.

## 1. Motivation

Math-pack slice 1b shipped `SQR` **resident in main-ROM page-0 low** (repack-only),
where the correctly-rounded `fp_sqrt` grew to **709 B** and left only **27 B free** in
that region (+ it took the last RAM scratch byte below `DRVA_DPB`). `SQR` is no longer a
"thin wrapper" — it is exactly the heavy body the sub-ROM **page-1 tenant** was reserved
for (spec-basic-math-pack §2). Migrating it now — *before* any slice-2 transcendental —
(a) frees ~700 B of scarce page-0 low space, and (b) **proves the page-1 tenant mechanism
against a known-good oracle**: `SQR`'s outputs are already locked by `math-acceptance`, so
any tenant-mechanism bug (dispatch, paging, marshalling, resident-ABI import) surfaces as
a gate regression isolated from new-algorithm risk (the [[harness-first-investigation-mo]]
"reproduce a known result first"). This is the FIRST real page-1 tenant and the FIRST
non-leaf tenant (it calls back into resident code).

**Scope:** move the `fp_sqrt` body only. `evmc_sqr` (token dispatch + `( expr )` parse)
stays main-ROM. No behaviour change — `SQR`'s outputs must stay byte-identical.

## 2. Dispatch — reuse `subrom_call` unchanged (page-agnostic)

`subrom_call` ([basic/subromcall.asm:39](../basic/subromcall.asm:39)) already works for a
page-1 target with **no change**: it sets `IY`h=`SUBSLOT`, `DI`, `call CALSLT`, `EI`,
`or a`(preserves A) `ret`. CALSLT switches the page that the caller's `IX` addresses — so a
page-1 `IX` switches **page 1**, leaving **page 0 = slot-0 (C-BIOS + main-ROM low region +
BCD core)** mapped. That is the §2.1 tenant scenario: `fp_sqrt` in page 1 can call the
resident `fp_*` in page 0 by absolute address. (Only the routine header comment, which
describes the page-0 case, needs generalizing.)

- Add to [basic/sysvars.inc](../basic/sysvars.inc): `SUBROM_ENTRY_BASE_P1 equ $4010` and
  `SUBROM_IDX_SQR equ 1` (append after the page-1 ping = index 0; never renumber).
- Append `jp fp_sqrt` at index 1 of `sub_p1_table` ([sub/sub.asm:392](../sub/sub.asm:392)).
- `evmc_sqr` (main-ROM): `ld ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_SQR` / `call subrom_call`.

## 3. Marshalling — FAC + A, no register args

- **Input:** operand already in **FAC** (RAM, always mapped) after `ev_mc_arg`, exactly as
  today before `call fp_sqrt`. No HL/DE arg.
- **Output:** result in **FAC**. **CORRECTION (implementation): `A` is NOT preserved across
  CALSLT** — the tenant's status cannot ride back in `A` (existing tenants return via RAM
  buffers, never `A`; relying on `A` made every `SQR(x≥0)` spuriously error). Only **CF** is
  reliable (`subrom_call`'s own `or a` sets it deterministically). So the **`x<0` domain check
  is done MAIN-SIDE in `evmc_sqr`** (test `ARGA+FPNUM_SIGN` after `widen_rhs_operand`, before
  dispatch); the tenant is pure-compute for x≥0 and returns no status.
- **FACTYP/DE stay main-side:** `evmc_sqr` sets `FACTYP=8` + `DE` (`flt_to_int16`) after the
  call returns; the tenant's resident-ABI surface is compute-only (§4) — `flt_to_int16` is
  main-side.

## 4. THE new mechanism — resident-ABI import into the sub-ROM build

`fp_sqrt` is the first tenant that **calls back into resident main-ROM code**. Its direct
resident callees (enumerated from the body):

`fp_add · fp_sub · fp_mul · fp_div · fp_cmp · dig15_iszero · arga_pack_fac ·
widen_fac_to · widen_uint_to` — all page-0-resident (< `__MEAS_LOW_END`=$3FE5).

> **⚠️ IMPLEMENTATION CORRECTION (2026-07-13) — the leaf-audit must be TRANSITIVE.**
> The 9-routine list above is the set of *direct* callees. But `fp_mul`/`fp_cmp` (and the
> `fp_add`/`fp_sub`/`fp_div` exponent-compare paths) themselves call **`cmp16_bits`**, which
> lived in `basic/expr.asm` at **page 1** ($4A02). While the page-1 tenant runs, main-ROM
> page 1 is switched OUT, so `call cmp16_bits` executed sub-ROM garbage → **every `SQR(x≥0)`
> returned `FPERR=1` (Overflow)** with a garbage FAC. Caught only by driving the real gate +
> openMSX instrumentation (page 0 = main ROM ✓, ABI addresses ✓, tenant entered ✓ — but the
> resident core reached one page-1 helper). **Fix:** `cmp16_bits` is a pure leaf, relocated
> into the page-0 low region (`basic/float-arith.asm`, repack-only; lean keeps its `expr.asm`
> copy, byte-identical) so it is reachable from both the page-1 interpreter callers and the
> page-1 tenant's page-0 float core.
>
> **A SECOND escape (same class): `div10`.** After relocating `cmp16_bits`, `SQR` still hung
> (no output, no prompt). openMSX instrumentation (breakpoints + stack capture) traced it to
> `widen_uint_to` → **`div10`**, which lived in `basic/print.asm` at **page 1** ($5233); with
> page 1 out, $5233 is sub-ROM `$FF` padding = `rst $38` → an infinite ISR loop (PC pinned in
> C-BIOS `int_end`). Same fix: `div10` relocated to the page-0 low region (repack-only; lean
> keeps its `print.asm` copy). Both escapes were **out-of-file, fallthrough-reached** callees —
> exactly what the manual leaf-audit missed twice.
>
> **STANDING GATE (the real fix): `tools/check_tenant_closure.py`** (`make subrom-closure-check`,
> also a step of `basic-reloc`). It walks the FULL transitive closure of the resident-ABI seeds
> (read from `basic-resident-abi.inc`) across all `basic/*.asm` — following fallthrough into
> internal labels until an unconditional terminator, so it can't miss a `div10`-style escape —
> and FAILS on any reached symbol ≥ $4000. This makes the page-1-escape class impossible to
> reship and **directly de-risks the slice-2 transcendentals** (which add callees to the same
> `.inc`; the gate re-audits automatically). Any future page-1-resident helper a tenant needs
> must be relocated to page 0.

Their absolute addresses live in [build/basic-reloc.sym](../build/basic-reloc.sym) and
**shift whenever the page-0 low region changes**. So:

1. A tiny generator (extend `tools/sym_to_openmsx.py` or a new `tools/gen_resident_abi.py`)
   greps exactly these symbols from `basic-reloc.sym` → emits `sub/basic-resident-abi.inc`
   (`fp_div equ 03632H` …), included by `sub.asm` inside the page-1 island.
2. **Build order:** `basic-reloc` (produces the sym) → generate the `.inc` → `$(SUB_ROM)`.
   Add `sub/basic-resident-abi.inc` as a generated prerequisite of `$(SUB_ROM)` in the
   Makefile (mirrors the `$(MAIN_ROM)` fix — a real rule, not a phony).
3. **Consistency gate:** a check that the addresses baked into the built `sub.rom` match the
   current `basic-reloc.sym` (guards against a stale `sub.rom` calling wrong addresses — the
   same class of stale-artifact trap as the `$(MAIN_ROM)` bug). Simplest form: the generator
   is deterministic + the build-order dependency forces regen; add a probe/assert that the
   ABI `.inc` is not older than `basic-reloc.sym`.

This import is **reusable** — every slice-2 transcendental needs the same resident surface,
so building it now with SQR is the shared infrastructure, proven once.

## 5. Interrupts / DI

`subrom_call` wraps the call in `DI…EI`; the tenant runs under DI. `fp_sqrt` is bounded
(normalize + ≤~9 Heron steps + one correction) — no long-DI concern, no EI needed. (Page-1
tenants *may* EI per §2.2 since page 0 = BIOS/$0038, but `fp_sqrt` doesn't need to.)

## 6. Space

- **Frees ~700 B** of main-ROM page-0 low (27 B → ~730 B): removes `fp_sqrt` + its `fsq_*`
  helpers from `float-arith.asm`; `evmc_sqr` stub (small) stays.
- **sub.rom page-1 island** ($4000–$7FFF, currently ~empty) absorbs ~700 B — ample.
- **RAM scratch** (`SQRT_X/Y/K/ITER/POW10`) stays in RAM (always mapped) — unchanged; this
  migration does NOT free the exhausted RAM byte (separate concern), but does not worsen it.

## 7. Gates

- **`math-acceptance` byte-identical** — SQR's full battery (incl. the pinned floor case)
  must stay green with IDENTICAL outputs. This is the proof the tenant mechanism is correct.
- **`subrom-acceptance` / `subrom-inttest`** — page-1 ping + the new tenant dispatch path
  (this is the FIRST use of `subrom_call` against a page-1 target).
- **New ABI-consistency gate** (§4.3).
- **lean `basic.rom` byte-identical** — SQR/float engine is repack-only; the sub.rom change
  and the main-ROM stub edit are both `IF ROM_BASE < $4000` / sub-side, lean untouched.
- **`sub.rom` fits + boots** (existing sub boot gate); merged machine boots.
- Fable review of the migration (first non-leaf tenant — the resident-ABI surface + the
  page-1 dispatch are new failure modes).

## 8. Open questions for sign-off

1. **Home of the `.inc` generator + build wiring** — extend `sym_to_openmsx.py` vs a new
   `gen_resident_abi.py`? (Recommend: new small tool, single responsibility.) OK to add the
   generated `sub/basic-resident-abi.inc` + a Makefile rule + regen-freshness assert?
2. **A-status ABI** — confirm the tenant returns `A`=0/nonzero and `evmc_sqr` maps nonzero →
   "illegal function call" (the same disposition it uses today, just across the CALSLT). Any
   preference for a specific nonzero code vs just "nonzero"?
3. **Consistency-gate strictness** — freshness assert (mtime/regen) sufficient, or do you want
   a stronger build-time assert that re-reads the sub.rom's baked addresses and diffs them
   against `basic-reloc.sym`?
4. **Model split** — investigation/spec done (me); implementation = Sonnet on this signed-off
   spec, with a Fable review after ([[opus-vs-sonnet-model-split]]). OK?
