<!-- Provenance: own-design spec over our own decimal float core + the ratified sub-ROM page-1 tenant ABI ([[subrom-arc]], spec-basic-subrom-mathpack.md). Per-function behaviour is characterized black-box from the Philips VG-8020 oracle (PRINT output only) and coefficient sets are OWN decimal-minimax derivations or published approximation tables (Cody & Waite, Hart, Abramowitz & Stegun) — NEVER MSX ROM disassembly (see PROVENANCE.md, [[no-reference-rom-disasm]]). -->
# Spec — BASIC math pack **slice 2: transcendentals** (DRAFT, awaiting sign-off)

**Status: 🟢 SCOPE + APPROACH SIGNED OFF 2026-07-13** (§8 forks resolved by user: the
**documented-deviation** accuracy framework and **ATN-first** slicing are ratified; the
per-sub-slice *implementation* contract still gets written + reviewed before its own code,
per [[spec-before-implementation]]). Slice 1 concluded (1a `ABS/SGN/INT/FIX/CINT/CSNG/CDBL`,
1b `SQR`, + the `SQR` sub-ROM page-1 tenant migration — all green, `make math-acceptance`
199/0). This spec opens **slice 2**: the transcendental functions `SIN COS TAN ATN EXP
LOG`, the `^` operator, and `RND`. It is grounded in a **black-box characterization
campaign** (§1, run this session, the same method [spec-basic-math-pack.md](spec-basic-math-pack.md)
§5.1 used for `SQR`/`^`).

Builds on the float core ([spec-basic-float-core.md](spec-basic-float-core.md), F1+F2+F3
concluded) and the **proven** sub-ROM page-1 tenant mechanism
([spec-basic-subrom-mathpack.md](spec-basic-subrom-mathpack.md) — `fp_sqrt` is the first
tenant; resident-ABI import + `check_tenant_closure.py` closure gate already exist).

---

## 1. Characterization result (black-box VG-8020, 2026-07-13)

Full-precision `PRINT` capture over designed batteries, compared against host `Decimal`
mathematical truth (14-sig correctly-rounded). Raw harness: `scratchpad/char_trans.py`
(to be promoted into the slice's probe). **Observed outputs only; the ROM is a black box.**

### 1.1 Accuracy — the reference transcendentals are LOW-accuracy polynomial approximations

Signed last-digit error of the oracle vs 14-sig truth (ulp = unit of the 14th significant
digit), per function over ~20 in-domain inputs:

| Fn | mean | worst | exact/20 | character |
|---|---|---|---|---|
| **ATN** | +0.00 | +2 | **15** | ~correctly-rounded; self-contained |
| **LOG** | −0.45 | −5 | 6 | mild low bias |
| **TAN** | +0.85 | ±12 | 4 | = `SIN/COS` (error inherited, grows near π/2) |
| **SIN** | +0.90 | +4 | 0 | ~1–2 ulp high in magnitude |
| **EXP** | −3.0 | **−20** | 3 | low bias **grows with x** (`EXP(8.8)` −20, `EXP(6.28)` −19) |
| **COS** | — | **−62807** | 3 | catastrophic near π/2 (`COS(1.5707)`): relative precision collapses at the zero |

Key points:
- **None of `EXP/LOG/SIN/COS/TAN` is correctly-rounded.** They are genuine ~1980s
  polynomial approximations with multi-ulp error; `EXP` reaches −20 ulp, and `COS` loses
  almost all relative precision near its zeros (argument cancellation).
- **`ATN` is the exception** — effectively correctly-rounded already (15/20 exact, worst
  2 ulp). It is the most self-contained and the lowest-risk target.

### 1.2 Structure / derivation (bit-compare)

- **`TAN(x)` = `SIN(x)/COS(x)` bit-for-bit** — CONFIRMED (`TAN(.7)`=`SIN(.7)/COS(.7)`=
  `.84228838046312`; `TAN(1.2)` likewise). TAN is a trivial derived function.
- **`COS` almost certainly = `SIN(x+π/2)`** (shares the SIN kernel): its catastrophic
  near-π/2 error is the signature of a `π/2 − x` reduction feeding the SIN core (not a
  dedicated COS polynomial). Not bit-provable from outside (the internal π/2 constant
  isn't a typeable literal), but the error shape is decisive.
- **`^` fractional = `EXP(y·LOG(x))` bit-for-bit** (already established, math-pack §5.1);
  integer-valued exponent = exact repeated-multiply. `^` = single-byte operator `$F5`.
- **Weak large-argument reduction:** `SIN(1000)` = `.82687954054849` vs truth
  `.82687954053200` — wrong at the 11th digit; `SIN(1E38)`=0 (argument beyond reducible
  range). A limited-precision stored π, classic for the lineage.

### 1.3 Domain / error / exactness

- `LOG(0)`, `LOG(-1)` → **"Illegal function call"** (same disposition path as `SQR(<0)`).
- `EXP(1000)` → **"Overflow"**; `EXP(-1000)` → 0 (underflow); `EXP(88)` ≈ 1.65E38 OK
  (overflow threshold ≈ e^88, the FAC magnitude ceiling).
- `TAN` near π/2 → very large finite (no error; `SIN/COS` with tiny COS).
- `ATN` saturates to ±π/2 for huge \|x\| (`ATN(1E38)` = 1.5707963267949).
- **Exact & guarded:** `EXP(0)`=1, `LOG(1)`=0, `SIN(0)`=0, `COS(0)`=1, `TAN(0)`=0,
  `ATN(0)`=0.

### 1.4 Tokens (captured, all match the §6 targets — clean interleave)

`SIN $89 · LOG $8A · EXP $8B · COS $8C · TAN $8D · ATN $8E · RND $88` (all `$FF`-prefixed);
operator `^` = `$F5`. Confirmed by crunch capture this session.

---

## 2. THE central decision — bit-exact is BARRED → faithfully-rounded + documented deviation

This is the slice-2 analogue of the `SQR`/division fork (math-pack §10.3.1), and the
characterization makes it **more clear-cut**, not less:

- **Bit-exact reference-identity is not clean-room achievable.** Reproducing the oracle's
  exact last digits requires its **polynomial coefficients + evaluation order + reduction
  constants**, which exist only in the ROM code → barred by [[no-reference-rom-disasm]].
  (§1.1's up-to-20-ulp / near-zero-catastrophic errors are properties of *specific hidden
  coefficients*, not of any clean model we could fit from 14-digit PRINT output.)
- **Matching the error envelope is both impossible and undesirable** — we cannot hit a
  20-ulp-in-a-hidden-pattern target, and it would make zerobas *less* accurate on purpose.

**Recommended position (mirrors `SQR` §10.3.1):** ship **own faithfully-rounded**
implementations, **gate against mathematical truth** (host `Decimal`), and **document the
deviation** (a per-function envelope table: reference error vs truth). zerobas is then
**always ≥ as accurate as the reference** — dramatically so here. This is *not*
reference-identical and the spec says so honestly.

**Accuracy target:** **correctly-rounded to 14 sig digits where the 14+guard-digit method
resolves it, with a pinned near-tie floor set** (exactly the `SQR` outcome: correctly-rounded
except `SQR(99.99998)`). True correctly-rounded transcendentals hit the Table-Maker's-Dilemma
precision floor (§10.4's `SQR` floor, same *kind* of limit); the gate pins the floor cases as
known-deviations so they can't silently drift. Invariant asserted by the gate: **zerobas is
never LESS accurate than the reference on any input.**

**Compatibility note (honest, per [[bug-for-bug-compat-over-accuracy]]):** the principle is
"bug-for-bug where **clean-room-achievable**." For transcendentals it is provably *not*
achievable, so accuracy wins by necessity. A program doing `IF SIN(x)=k` could branch
differently — but (a) the pack is game-loader-scoped (loaders use these for
positioning/graphics, not exact-equality branching), and (b) no clean-room path to the
reference's bits exists. **This is the same documented-deviation boundary as division.**

---

## 3. Placement — sub-ROM slot 3-2, **PAGE 1 tenant** (mechanism already proven)

Each function is a page-1 tenant of `zerobas-sub`, exactly like the migrated `fp_sqrt`
(spec-basic-subrom-mathpack §2–§4). Rationale is settled there: a page-1 tenant keeps
slot-0 **page 0 = BIOS + BCD float core** mapped (so the body calls resident `fp_*`
directly) and **may EI** for long iteration.

- **Bodies + coefficient tables** live in the sub-ROM **page-1 island** ($4000–$7FFF, 16 KB
  headroom). This is precisely the "coefficient-heavy transcendentals" home the page-1
  tenant was reserved for (math-pack §2.3).
- **Main-side stubs** (`evmc_*` token dispatch + `( expr )` parse + domain pre-check +
  result FACTYP/DE) stay in main BASIC, `IF ROM_BASE < $4000` (repack-only) — lean 16 KB
  cart stays byte-identical.
- **Dispatch:** append each to `sub_p1_table` after `SUBROM_IDX_SQR`=1 (never renumber);
  `subrom_call` is page-agnostic and unchanged.
- **Resident-ABI + closure gate:** every new resident callee is added to
  `basic-resident-abi.inc`; `check_tenant_closure.py` (`make subrom-closure-check`)
  re-audits the full transitive closure automatically and FAILS on any reached symbol
  ≥ $4000 (the `cmp16_bits`/`div10` page-1-escape class is already fenced). Any new page-1
  helper a body needs must be relocated to page 0 first.
- **Marshalling (per the SQR lesson): `A` is NOT preserved across CALSLT.** Domain checks
  (`LOG(≤0)`) are done **main-side** before dispatch (test FAC sign/zero), like `SQR(<0)`;
  the tenant is pure-compute; `FACTYP`/`DE` set main-side after return.

---

## 4. Coefficient provenance — OWN decimal-minimax, never the ROM

Our FAC is a **decimal** BCD mantissa (not the reference's binary format), so the
reference's coefficients would not even apply — we derive our own:

- **Primary:** own **minimax (Remez) polynomials** fitted for the 14-digit decimal FAC over
  each reduced domain, generated by a committed host tool (`tools/gen_math_coeffs.py`,
  deterministic; the fit inputs + method are the provenance trail).
- **Cross-check / seed:** published approximation literature — **Cody & Waite** *Software
  Manual for the Elementary Functions*, **Hart** *Computer Approximations*, **Abramowitz &
  Stegun**. All are admissible published sources (same tier as the string-engine tables).
- **Never** the MSX ROM's coefficients (barred; and format-incompatible anyway). This
  sidesteps any coefficient-provenance question entirely — there is no relationship to the
  reference to launder.

Range reduction: our own (reduce to the primary interval with a **high-precision** stored
constant — we can afford more guard digits than the reference, hence our better large-arg
behaviour; §8 gate pins large-arg cases).

---

## 5. Recommended sub-slicing (algebraic/risk-ascending — proves machinery early)

Dependency graph: `SIN`→`COS`(=shift)→`TAN`(=quotient); `EXP`,`LOG` independent; `^` needs
`EXP`+`LOG`; `ATN` independent; `RND` independent (LCG). Recommended order:

| Sub-slice | Functions | Why here |
|---|---|---|
| **2a** | **`ATN`** | Lowest risk: self-contained, already ~correctly-rounded (§1.1), simplest reduction (`atan(1/x)` + halving). **First page-1 transcendental tenant** — proves the polynomial-eval + reduction + coeff-table + tenant machinery against the easiest function (the [[harness-first-investigation-mo]] "reproduce a known result first"). |
| **2b** | **`EXP` + `LOG`** | Foundational independent pair; each = one reduction (`EXP` mod ln2 · `LOG` mantissa/exponent split) + one minimax poly. Unlocks `^`. |
| **2c** | **`^`** | Integer exponent = exact repeated-multiply (**algebraic**, no approximation); fractional = `EXP(y·LOG(x))` (reuses 2b). Precedence `$F5` above unary minus (`-2^2`=−4). |
| **2d** | **`SIN` + `COS` + `TAN`** | The trig cluster, highest reduction risk (quadrant reduction to [−π/4,π/4]): one `SIN` kernel, `COS`=`SIN(x+π/2)`, `TAN`=`SIN/COS` (§1.2). Landed together since they share the kernel. |
| **2e** | **`RND`** | Separate **black-box LCG capture** campaign (capture the sequence, fit the recurrence — admissible, no disasm; math-pack §4.2). May prove its own effort; sequenced last / independently. |

Rationale for **ATN-first** over EXP/LOG-first: ATN's near-correctly-rounded reference
means the accuracy target is provably reachable, so slice 2a isolates *tenant/machinery*
risk from *approximation* risk. (EXP/LOG-first is a defensible alternative if unlocking `^`
sooner is preferred — a §10 sign-off question.)

---

## 6. Per-function contract (oracle-locked by the gate, not asserted from memory)

All `$FF`-prefixed function tokens (§1.4); all compute **DOUBLE** per float-core §10; result
FACTYP=8 (double) unless the oracle narrows for single input (capture & match). Domain
errors return a **disposition** (never `jp`), raised main-side (§3).

| Fn | Domain | Error | Notes |
|---|---|---|---|
| `EXP(x)` | x ≤ ~88 | **Overflow** above; underflow→0 | reduce mod ln2, minimax; `EXP(0)`=1 exact |
| `LOG(x)` | x > 0 | **Illegal function call** for x≤0 (main-side pre-check) | `LOG(1)`=0 exact |
| `SIN(x)`/`COS(x)` | all x | none (huge-x → reduction floor, capture) | shared kernel; `SIN(0)`=0/`COS(0)`=1 exact |
| `TAN(x)` | all x | none (near π/2 → large finite) | = `SIN/COS`; `TAN(0)`=0 exact |
| `ATN(x)` | all x | none | saturates ±π/2; `ATN(0)`=0 exact |
| `^` (`x^y`) | per EXP/LOG (frac); base<0 frac → error as `LOG(neg)` | integer path exact; fractional = `EXP(y·LOG(x))` | operator `$F5` |
| `RND(x)` | x>0 next, x=0 repeat, x<0 reseed | none | LCG over RAM seed; sequence fit black-box |

FACTYP discipline (float-pack standing trap, bit twice): every returning tail leaves
FAC+FACTYP consistent; the battery must cover function-over-float, store-into-typed-var,
and function-of-`PEEK`.

---

## 7. Gates (per sub-slice) — extend `math-acceptance`

- Extend `probes/basic/basic_probe_math_conv.py` (do **not** fork): append token-capture
  rows (§1.4) + a **truth-oracle value differential** per function — assert `fn(x)` == host
  `Decimal` correctly-rounded 14-sig √-analogue over a **broad** battery (the ~120
  characterization inputs + random draws), NOT == reference. Pin near-tie floor cases in a
  `<FN>_KNOWN_FLOOR` set (SQR precedent).
- **Documented reference-deviation report:** separately capture the reference on the same
  inputs, print the per-function ulp-error summary (§1.1) as informational — documents the
  ROM's inaccuracy, never asserted against.
- **Invariant assert:** for every battery input, zerobas's \|error vs truth\| ≤ reference's
  (zerobas never worse).
- Domain-error cases per-machine (`LOG(0)`/`LOG(-1)`/`EXP(1000)` → exact wording).
- Standing gates stay green: `unit-test`, `float-acceptance`, `string-acceptance`,
  `input-acceptance`, `subrom-acceptance`, `subrom-inttest`, `subrom-closure-check`,
  `diskbasic-repack`, kwtable single-copy, **lean byte-identical**, reloc.
- **Fable review of every sub-slice** (float-pack standing lesson: every slice hid ≥1
  matrix-invisible bug — the differential + review together, never the passing matrix).

---

## 8. Sign-off — RESOLVED (user, 2026-07-13)

1. **§2 accuracy position** → ✅ **Documented deviation.** Own faithfully/correctly-rounded
   functions; gate vs mathematical truth (`Decimal`); pin near-tie floor cases; assert
   **"never less accurate than the reference"**; document the envelope. The `SQR` §10.3.1
   framework. **NOT reference-identical** — bit-exact is barred ([[no-reference-rom-disasm]]).
2. **§5 slicing + order** → ✅ **ATN-first.** Sub-slices 2a `ATN` → 2b `EXP`+`LOG` → 2c `^`
   → 2d `SIN`+`COS`+`TAN` → 2e `RND`. One sub-slice per session (dev workflow).
3. **§4 coefficient provenance** → ✅ (default accepted) own decimal-minimax via a committed
   `gen_math_coeffs.py`, cross-checked vs Cody & Waite / Hart / A&S, never the ROM.
4. **`RND` (2e)** → ✅ distinct sub-slice, sequenced last (black-box LCG-fit campaign).
5. **Model split** → ✅ characterization Fable-solo (done); implementation = Sonnet on the
   signed sub-slice contract, Fable review after ([[opus-vs-sonnet-model-split]]).
6. **Deferred `unclosed-paren` residue** (math-pack §9.5 F3) → ✅ stays evaluator-wide-deferred,
   not fixed in slice 2.

Next: write the concrete **slice 2a (`ATN`) implementation contract** (seed/reduction,
minimax degree, RAM scratch, `evmc_atn` evaluator stub, page-1 tenant index, gate battery)
— then Sonnet implements it, Fable reviews.

---

## 11. Slice 2a implementation contract — `ATN` (concrete, implementation-ready)

**Status: 🟢 CONTRACT 2026-07-13** — the concrete cut for the ratified ATN-first slice.
Written against the live code (expr.asm `evmc_sqr` / `ev_ff_mathconv`, sub.asm
`sub_p1_table`, float-arith.asm `fp_*`, basic-resident-abi.inc). Implementation = Sonnet
on this contract, Fable review after.

### 11.1 Home + token + dispatch

- **Home:** body `fp_atan` in the sub-ROM **page-1 island** (sub/, appended after
  `fp_sqrt`); main-ROM stub `evmc_atn` (repack-only, `IF ROM_BASE < $4000`). Lean 16 KB
  `basic.rom` **byte-identical**.
- **Token:** `ATN` = `$FF $8E` (§1.4, captured). Add `ATN_TOKEN equ $8E` to
  [basic/sysvars.inc](../basic/sysvars.inc) (repack block, beside `SQR_TOKEN`) + a crunch
  entry to [basic/kwtable.inc](../basic/kwtable.inc) (repack-only, the "math pack slice 2a"
  block). Gate confirms the byte vs the real crunch.
- **Tenant index:** `SUBROM_IDX_ATN equ 2` (append after `SUBROM_IDX_SQR`=1; never renumber).
  Append `jp fp_atan` at index 2 of `sub_p1_table` ([sub/sub.asm](../sub/sub.asm)).

### 11.2 Algorithm — Cody-Waite ATAN (decimal, OWN minimax), NOT halving+series

**Design decision (resolved here):** ATN uses a **two-stage argument reduction + a single
minimax polynomial** (the Cody & Waite ATAN structure), *not* the argument-halving +
Taylor scheme. Rationale:
1. **Accuracy invariant.** The reference ATN is already ~correctly-rounded (§1.1: 15/20
   exact). Argument-halving reduces `x` k times and multiplies the result by `2^k`, which
   **amplifies accumulated 14-digit rounding by up to ~8×** → real risk of landing *worse*
   than the reference on some inputs, violating the "never less accurate than the
   reference" invariant. Direct Horner evaluation of a minimax polynomial has **no such
   amplification** — the tightest accuracy control.
2. **Builds the reusable machinery.** The coeff-table + Horner evaluator this needs is
   exactly what 2b/2c/2d (EXP/LOG/SIN) all reuse — the stated ATN-first rationale (§5).
3. Faster (no `fp_sqrt`/halving loop under the `subrom_call` DI span).

**Steps** (`fp_atan`, input operand in **ARGA** already widened by `widen_rhs_operand`,
`dig[14]`=0 fresh; total function — no domain error):

0. **Trivial:** `x==0` → FAC:=0 (packed), return. (`dig15_iszero` on `ARGA+FPNUM_DIG`.)
1. **Sign fold:** atan is odd. Record `s = ARGA sign`, clear it (work with `a=|x|`),
   restore `s` onto the final result's `FPNUM_SIGN`.
2. **Reduction 1 — |x|>1:** if `a > 1` (`fp_cmp` vs a `widen_uint_to` 1.0), set
   `a := 1/a` (`fp_div`: ARGA=1.0, ARGB=|x|) and remember `flag_recip`. Now `a ∈ [0,1]`.
3. **Reduction 2 — breakpoint `a > 2−√3` (≈0.267949):** if `a > BREAK`, set
   `a := (a·√3 − 1)/(a + √3)` (constants `SQRT3`, using `fp_mul`/`fp_sub`/`fp_add`/`fp_div`)
   and remember `flag_break`. Now `|a| ≤ 2−√3 ≈ 0.268`.
4. **Core minimax:** `g := a·a` (`fp_mul`); `P := horner(g, ATAN_COEF)` (§11.3);
   `r := a·P` (`fp_mul`). `P` is a minimax polynomial in `g` for `atan(a)/a` on
   `g ∈ [0, (2−√3)²] ≈ [0, 0.0718]`, degree chosen so the fit error ≤ 0.5 ulp of the
   14-digit result (§11.3; gen tool reports it; est. degree ~7–8).
5. **Reconstruct:** if `flag_break`: `r := r + PI_6` (`fp_add`, `PI_6`=π/6). If
   `flag_recip`: `r := PI_2 − r` (`fp_sub`: ARGA=`PI_2`, ARGB=r; `PI_2`=π/2). Apply `s`
   (sign byte). Pack FAC (result already in FAC/ARGA from the last op; `arga_pack_fac` if a
   trivial path left it in ARGA only). Return status implicit-ok (no `A` reliance).

**Canonical-operand discipline** (fp_sqrt's hard-won lesson, §fp_sqrt header): between every
`fp_*` op, re-`widen_fac_to` the result into a clean record before feeding it as the next
operand — never the raw post-op ARGA guard bytes.

### 11.3 New infrastructure (first transcendental → reused by 2b–2d)

1. **FPNUM constant-table format.** An assembler macro `FPCONST sign,dexp,d0,…,d13`
   emitting an 18-byte record (`db sign` / `dw dexp` / 14 digit bytes / `db 0` guard),
   placed in the page-1 island. Named constants for 2a: `PI_2`, `PI_6`, `SQRT3`, `BREAK`
   (=2−√3), and the coeff table `ATAN_COEF`.
2. **Horner evaluator `fp_poly_horner`** (tenant-local, page-1 — NOT a resident-ABI add):
   inputs `g` in a scratch FPNUM cell + `HL`→a count-prefixed coeff table
   (`db n` then n×18-byte `FPCONST` records, `c[n-1]…c[0]`); returns FAC = `Σ c[i]·g^i`.
   Loop: `acc := c[top]`; for each lower coeff `acc := acc·g + c[i]` (`fp_mul` acc×g,
   re-widen, `fp_add` +c[i], re-widen). Reused verbatim by EXP/LOG/SIN.
3. **`tools/gen_math_coeffs.py`** — host tool (deterministic, `Decimal`/Remez), emits
   `sub/math-coeffs.inc` (the `FPCONST` records) + prints each fit's max error. Committed
   generated file + a Makefile rule (mirrors `gen_resident_abi.py`). **Provenance:** OWN
   Remez minimax for `atan(a)/a` on the reduced domain, ≥16 sig digits; the fit spec
   (function, domain, degree, target) is the trail; **cross-checked vs published Cody &
   Waite ATAN coefficients**, never the MSX ROM (which is binary-format anyway — no relation
   to launder). This turn PROVES the fit (degree + error bound) before any asm.

### 11.4 Resident-ABI surface — a SUBSET of SQR's (no new relocations)

`fp_atan`'s direct resident callees: `fp_add · fp_sub · fp_mul · fp_div · fp_cmp ·
dig15_iszero · widen_fac_to · widen_uint_to · arga_pack_fac` — **all already in**
[sub/basic-resident-abi.inc](../sub/basic-resident-abi.inc) (the SQR import set). No new
page-0 relocation needed. `fp_poly_horner` + the constants are tenant-local (page-1).
`check_tenant_closure.py` re-audits the full transitive closure automatically and must stay
green (the `cmp16_bits`/`div10` escape class is already fenced).

### 11.5 `evmc_atn` (main-ROM stub) — mirror `evmc_sqr` minus the domain check

Add the `ATN_TOKEN` selector to `ev_ff_mathconv` ([basic/expr.asm:817](../basic/expr.asm:817)).
`evmc_atn` = `evmc_sqr` ([expr.asm:1059](../basic/expr.asm:1059)) **without** the
`ARGA+FPNUM_SIGN` domain branch (atan is total): `ev_mc_arg` → `widen_rhs_operand` (ARGA) →
`push ix` → `ld ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_ATN` → `call subrom_call` → `pop ix`
→ `jp c,subrom_absent_error` → `ld a,8 / ld (FACTYP),a` → `jp flt_to_int16` (DE := int16,
FACTYP untouched). Result FACTYP=8 (double) per §6. `A` is NOT read after the call (CALSLT
doesn't preserve it; SQR lesson).

### 11.6 RAM scratch — REUSE `SQRT_X`/`SQRT_Y` (RAM below `DRVA_DPB` is exhausted)

Slice-1b took the last free byte below `DRVA_DPB`=$F195. `fp_atan` MUST NOT allocate new
RAM. It reuses the SQR scratch cells as generic math scratch — SQR and ATN never run
concurrently (one factor evaluated at a time): `SQRT_X`=$F16E and `SQRT_Y`=$F180 are two
18-byte FPNUM cells; plus `ARGA`/`ARGB`/`FAC`. If a 3rd persistent FPNUM cell is needed,
reuse `FOUTBUF` (as `SQRT_R` already does — idle outside PRINT/LIST). The implementer
confirms the working-set fits ≤ these cells; if not, flag before adding RAM (there is none).
Add sysvars.inc comments noting the shared SQR/ATN use (rename intent: generic `MATH_*`
aliases over the same addresses, optional).

### 11.7 Gate — extend `basic_probe_math_conv.py` (do NOT fork)

- **Token:** append `("ATN", "a=atn(1)", 0x8E)` to `TOKENS`.
- **Value differential (oracle = mathematical truth, §2):** assert `atn(x)` == host
  `Decimal` correctly-rounded 14-sig `atan(x)` over a BROAD battery — the 20 characterization
  inputs + fresh draws spanning: near-breakpoint `a≈0.268` (both sides), near 1 (both
  reduction paths meet), huge saturating to ±π/2 (`ATN(1E38)`), tiny (`ATN(1E-9)`),
  oddness (`ATN(-x)==-ATN(x)`), and mid-range. Pin any near-tie floor cases in
  `ATN_KNOWN_FLOOR` (SQR precedent).
- **Never-worse invariant:** for each input, `|zb−truth| ≤ |reference−truth|` (assert).
- **Documented reference-deviation:** capture the reference on the same inputs, print the
  ulp summary (informational; the reference is ~correctly-rounded so this table is small).
- **FACTYP-leak:** `PRINT ATN(1)+0.5`, `A%=ATN(1)`, `ATN` over a single/double literal and
  over `PEEK`.
- No domain-error case (atan total). `make math-acceptance` green.

### 11.8 Verification / standing gates

`math-acceptance` (extended) green; `gen_math_coeffs.py` deterministic + Makefile rule +
`sub/math-coeffs.inc` committed; `subrom-closure-check` green (surface ⊆ SQR's);
`subrom-acceptance`/`subrom-inttest` green (new page-1 index 2); **lean `basic.rom`
byte-identical** (evmc_atn is repack-only); `sub.rom` fits + boots; `unit-test`,
`float-acceptance`, `string-acceptance`, `input-acceptance`, reloc, kwtable single-copy all
green. **Fable review of the whole slice** (float-pack standing lesson).

### 11.9 First implementation step (this session) — prove the minimax fit

Before any asm: build `tools/gen_math_coeffs.py` and PROVE the ATN minimax degree + error
bound (≤0.5 ulp on `[0, (2−√3)²]`) so the asm is written against real, feasibility-verified
coefficients. Then Sonnet implements §11.1–§11.6 and the gate §11.7.
