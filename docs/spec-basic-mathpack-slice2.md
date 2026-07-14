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
- `EXP(1000)` → **"Overflow"**; `EXP(-1000)` → 0 (underflow); `EXP(88)` ≈ 1.65E38 OK.
  > **CORRECTED (slice-2b characterization, 2026-07-13):** the original "overflow
  > threshold ≈ e^88 ≈ the FAC magnitude ceiling" note here was an unverified
  > inference (1E38 is a *binary*-Microsoft-BASIC ceiling). Measured on the
  > VG-8020: `EXP(145.062)`=`9.9913951180409E+62` (finite), `EXP(145.063)`→
  > `Overflow`; `EXP(-147.3)`=`1.0676350345268E-64` (finite), `EXP(-147.4)`→`0`.
  > I.e. the true thresholds are exactly the BCD FAC range ends
  > (`ln(9.99999999999999E62)`=145.06286…, `ln(1E-64)`=−147.36544…) — which our
  > float core SHARES, so zerobas's natural dispositions match the reference at
  > the range ends with no special-casing. Informational: the reference's own
  > `EXP(88)` is −45 ulp off truth and its `EXP(-147.3)` ~2.7e-8 relative off
  > (error grows with |x|); zerobas is exact at both (§12).
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

> **RELAXED for `ATN` (user sign-off 2026-07-13, §11.10).** Slice 2a found the strict
> per-input "never LESS accurate than the reference" invariant is **not achievable for `ATN`
> without an extended-precision arithmetic layer** — its 14-digit reduction+Horner+
> reconstruction chain accumulates ~2 ulp, and `ATN` is the *only* slice-2 function whose
> reference is accurate enough (~correctly-rounded) for that to lose. The user chose a
> **documented bounded deviation** (the div/SQR-floor precedent) over building the layer:
> the gate asserts `|zerobas − truth| ≤ 2 ulp` (the reference's *own* worst envelope) and
> catalogues the per-input deviations. The other five functions (references 4–20+ ulp off)
> keep the strict invariant trivially at 14 digits.

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
| `EXP(x)` | x ≤ 145.062 (FAC ceiling; §1.3 corrected) | **Overflow** above; underflow→0 below −147.36 | decimal-native reduce (×10^n exact), minimax; `EXP(0)`=1 exact — §12 |
| `LOG(x)` | x > 0 | **Illegal function call** for x≤0 (main-side pre-check) | `LOG(1)`=0 exact — §12 |
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

### 11.10 Implementation outcome + `ATN` accuracy resolution (2026-07-13)

Implemented (Sonnet on §11) + accuracy fork investigated (this session) + resolved (user).
`make math-acceptance` GREEN; all standing gates green (unit-test, basic-reloc lean
byte-identical + kwtable single-copy + resident-ABI + **tenant-closure 118 routines all
page-0, no page-1 escape**, subrom-acceptance/inttest, float/string/input-acceptance).

**The accuracy finding (a real §11.2 contract gap, surfaced by the implementer, not hidden).**
The faithful 14-digit `fp_atan` chain (reduction 1+2 → `g=a²` → 8-degree Horner →
reconstruction ≈ 15 chained `fp_*` ops) accumulates ~2 ulp of rounding with **no correction
stage** — §11.2 rejected argument-halving's `2^k` amplification but never addressed chain
*accumulation*. Verified NOT an asm bug: an independent 14-digit op-chain simulation
reproduces the exact wrong digits (`atn(1)=.78539816339746` bit-for-bit). Quantified
(scratchpad sim): the chain needs **3 internal guard digits (17-sig)** to be strictly
correctly-rounded; the resident BCD `fp_*` primitives carry effectively **0** usable guard
(canonical-operand discipline zeroes it). Reaching correctly-rounded therefore needs an
**extended-precision arithmetic layer** — the same clean-room wall as the division deviation
(§10.3.1) and the SQR floor (§10.4). Compensated-Horner alone does **not** fix it (the error
is spread across the reduction/reconstruction ops, not just Horner).

**Decisive reframing:** `ATN` is the **only** slice-2 function affected — its reference is the
sole ~correctly-rounded one (§1.1: worst 2 ulp). The other five (LOG/SIN/TAN/EXP/COS
references 4–20+ ulp off truth) are beaten trivially by our ~2-ulp chain, so they keep the
strict never-worse invariant at 14 digits without any extended precision.

**Resolution (user sign-off 2026-07-13): documented bounded deviation** (the div/SQR-floor
precedent) over building an extended-precision layer for the one function within the
reference's own envelope:
- Keep the faithful 14-digit `fp_atan`. Gate asserts **`|zerobas − truth| ≤ 2 ulp`** (the
  reference's own worst envelope), NOT `== truth` and NOT strict never-worse.
- Result: **43/60 correctly-rounded, worst 2 ulp**, oddness exact. The reference itself
  misses truth on 20/60 of the same inputs (informational report) — our accuracy is
  genuinely comparable, not inferior.
- The deviations are **catalogued** (probe `ATN_DEVIATION_TIE_OR_BETTER` /
  `ATN_DEVIATION_WORSE_THAN_REF`), not pinned/laundered — the ≤2-ulp bound decides pass/fail
  independently, so no specific value can silently drift.
- **Future option (not built):** an extended-precision (double-double / error-compensated)
  core would make `ATN` (and later slice-2 fns) uniformly correctly-rounded and restore the
  strict invariant. Deferred as disproportionate — only `ATN` needs it and it's already
  within envelope.

**Minor implementation notes (agent-flagged, accepted):** `fat_copy18` is a private duplicate
of `fsq_copy18` (file self-containment); `HORNER_CNT`/`HORNER_PTR` reuse 2 still-dead trailing
bytes of the `FOUTBUF` region (Horner's loop counter/table pointer must survive the `fp_*`
calls; no new RAM claimed) — a contained widening of §11.6's "reuse SQRT_X/SQRT_Y/FOUTBUF".

**Fable adversarial review (2026-07-13): SHIP after gate hardening.** Independently
re-derived all constants + 9 coeffs from the emitted bytes (byte-exact; poly max error
8.74e-17), simulated the exact op-chain over the full battery (worst 2 ulp, `atn(1)`
bit-for-bit), and traced reconstruction order, canonical-operand discipline, RAM live-ranges,
`evmc_atn`, clean-room, and the lean guard — **no functional defect in the asm.** Five
findings, all gate/doc hardening, all addressed: (1) added `atn(0)` to the battery (was
untested — the hand-rolled zero exit); (2) added a battery-wide correctly-rounded FLOOR
(`ATN_EXACT_FLOOR=40`) as a drift tripwire, since the ≤2-ulp bound alone would let a *uniform*
1–2-ulp degradation pass silently; (3) corrected the `fp_atan.asm` header (it still claimed
"correctly-rounded / never-worse" pre-§11.10); (4) header comment nits; (5) made
`gen_math_coeffs.py`'s Chebyshev nodes fully deterministic (Decimal `cos`, no host libm) —
regenerated `.inc` is byte-identical.

---

## 12. Slice 2b implementation contract — `EXP` + `LOG` (concrete, implementation-ready)

**Status: 🟢 CONTRACT 2026-07-13** — the ratified §5/§8 slicing's second cut. Written
against the live code (fp_atan.asm as the tenant template, expr.asm `evmc_sqr`/`evmc_atn`,
sub.asm `sub_p1_table`, basic-resident-abi.inc) and — the §11.10 lesson applied *forward* —
against a **pre-proven 14-digit chain simulation** ([tools/sim_math_chain.py](../tools/sim_math_chain.py),
committed 4e1a2a6): the fits AND the full op-chain accuracy were measured BEFORE this
contract was finalized. Implementation = Sonnet on this contract, Fable review after.

### 12.1 Proven accuracy envelope (sim, ~4000-input batteries, model = exact-then-
round-14-HALF_UP per op — the model that reproduced fp_atan bit-for-bit)

| Fn | worst | correctly-rounded | bound asserted | exact-floor | reference (for contrast, informational) |
|---|---|---|---|---|---|
| `EXP` | **1 ulp** | 92.0 % | ≤ 2 (margin +1) | ≥ 90 % | mean −3, worst −45 @x=88, ~15 % exact |
| `LOG` | **4 ulp** | 87.3 % | ≤ 4 | ≥ 85 % | mean −0.45, worst −5, ~30 % exact |

Anchors proven exact in-chain: `EXP(0)`=1, `EXP(1)`, `EXP(88)`, `EXP(145.062)`,
`EXP(-147.3)`, `LOG(1)`=0, `LOG(10)`, `LOG(9.9999999999999E62)`, `LOG(1E-64)`.
LOG's five >2-ulp cases are ALL in the j=8 fold path (x∈[0.866,1)): `den=m′+1`
inherently spans 15 digits and ∂r/∂s=2 doubles the division rounding — the same
extended-precision wall as §11.10/division; **documented bounded deviation** (the
ratified §2/§11.10 framework). **Per-input never-worse vs the reference is NOT
asserted** (the reference is exact on scattered inputs where a 14-digit chain can be
1–2 ulp off — the exact situation the user already resolved for ATN); the gate asserts
the truth-bound + exact-floor instead, with the reference captured informationally.
*Judgment call logged in the review queue: §11.10's "the other five keep the strict
invariant" claim was optimistic in per-input form; this contract extends the ATN
bounded-deviation shape to EXP/LOG. Aggregate superiority over the reference is
overwhelming (see table).*

### 12.2 Home + tokens + dispatch

- **Homes:** bodies `fp_exp` ([sub/fp_exp.asm](../sub/fp_exp.asm)) + `fp_log`
  ([sub/fp_log.asm](../sub/fp_log.asm)), page-1 tenants after `fp_atan`, both REUSING
  `fp_poly_horner` + `fat_copy18` (same assembly unit — direct call). Main-ROM stubs
  `evmc_exp`/`evmc_log` (repack-only, `IF ROM_BASE < $4000`). Lean 16 KB `basic.rom`
  **byte-identical**.
- **Tokens (§1.4 captured):** `EXP` = `$FF $8B`, `LOG` = `$FF $8A`. `EXP_TOKEN equ $8B` /
  `LOG_TOKEN equ $8A` in sysvars.inc (repack block, beside `ATN_TOKEN`) + two kwtable.inc
  crunch entries (`db 3,"EXP",2,PEEK_PREFIX,EXP_TOKEN`, same for LOG — no prefix
  collision: EXP/LOG diverge from every existing keyword by char 2 or 3; detok/LIST is
  free via the single-copy table). Gate confirms both bytes vs the real crunch.
- **Tenant indices:** `SUBROM_IDX_EXP equ 3`, `SUBROM_IDX_LOG equ 4` (append-only, both
  sysvars.inc IFNDEF block and sub/equates.inc); `jp fp_exp` / `jp fp_log` appended to
  `sub_p1_table`.
- **Dispatch:** two selectors in `ev_ff_mathconv` (`cp EXP_TOKEN / jp z,evmc_exp`, same
  for LOG), after the ATN selector.

### 12.3 Constants (already emitted + committed, 4e1a2a6 — sub/math-coeffs.inc)

All OWN decimal derivations (gen_math_coeffs.py §4 provenance; `check_2b_invariants`
asserts every exactness precondition below at generation time):

- `EXP_COEF` — **E(r) = (exp(r)−1)/r**, deg 9 (10 terms), fit 1.9e-19 on |r| ≤ ln10/16+pad.
  The leading 1 of exp(r) = 1 + r·E(r) is **implicit and exact** — reconstruction
  amplifies the poly's rounding by T·r ≈ 1.1×, not T ≤ 7.5× (the sim measured the direct
  exp-poly form 2 ulp worse from exactly that decade-crossing multiply).
- `LOG_COEF` — 2·atanh(√g)/√g, deg 5 (6 terms), fit 1.4e-18 on g ∈ [0, gmax] where gmax
  is computed FROM the emitted rounded `LOG_BP`/`POW8_TBL` records (closed intervals,
  both fp_cmp boundary outcomes covered).
- `EXP_RC` = 8/ln10 (n8 selector); `EXP_C1` (10 sig digits → **n8·C1 exact** for
  |n8| ≤ 3475, asserted) + `EXP_C2` (the remainder); `LN10_C1` (12 sig digits →
  **e′·C1 exact** for |e′| ≤ 64, asserted) + `LN10_C2`.
- `POW8_TBL[j]` = round14(10^(j/8)), j=0..7, record 0 exactly 1.0 — EXP's T̂ **and**
  LOG's K̂ (one shared table). `EXP_TCOR[m]` = round14(ln(T̂ₘ)−m·ln10/8), m=1..7 — the
  T̂ representation-error absorber. `LNK_TBL[j]` = round14(ln(K̂ⱼ)), j=1..7 — ln OF THE
  ROUNDED record (absorption). `LOG_BP[j]` = round14(10^((2j−1)/16)), j=1..8.
- `NEGLNK_TBL[j]` = round14(ln(K̂ⱼ)−ln10), j=0..7 — the **e′=−1 decade's merged
  additive**: without it the intermediate r+LNK sits a decade above the cancelled
  result and its rounding costs up to 10 result-ulps (sim measured worst 9 → 4).

### 12.4 `fp_exp` (tenant; input ARGA = widened x, |x| < 1000 guaranteed by the stub)

Persistent cells (all aliases, §12.6): `MATH_A` (FPNUM), `MATH_T`/`HORNER_G` (FPNUM,
sequential), `MATH_R`/`HORNER_ACC` (FPNUM), `MATH_N` (2B int16), `MATH_J` (1B).

1. `MATH_A := x` (copy). `q := x·EXP_RC` (fp_mul, widen).
2. **n8 := nearest-int(q)** — hand-extracted from the widened record: dexp ≤ 0 → int
   part 0 (round via d0 when dexp=0); 1 ≤ dexp ≤ 4 → int part = digits d0..d(dexp−1),
   round-half-away via digit d(dexp) ≥ 5; apply sign; defensive dexp > 4 → treat as
   step-3 bound breach by sign. Store `MATH_N`.
3. **Bounds:** n8 > 552 → `FPERR:=1`, `FAC:=0`, ret. n8 < −552 → `FAC:=0`, ret.
   (Keeps every later dexp within fp_mul's ±126 preExp envelope; borderline
   overflow/underflow inside the bound is disposed by round_and_finalize itself, which
   the sim proved lands EXACTLY on the reference's characterized thresholds.)
4. `m := n8 & 7` (low byte AND 7 — two's-complement floor semantics), `n := n8 >> 3`
   (arithmetic, sra h/rr l ×3). Store m in `MATH_J`; n stays in registers/`MATH_N` as
   convenient (n8 itself is dead after the two C1/C2 products).
5. **Reduce:** n8fp := widen |n8| (widen_uint_to) + sign poke → `MATH_T`.
   `r := x − n8fp·EXP_C1` (fp_mul EXACT by invariant, fp_sub EXACT by alignment —
   proven in-contract);  `r := r − n8fp·EXP_C2`;  if m ≠ 0: `r := r − EXP_TCOR[m−1]`.
   Result r canonical → `HORNER_G` (MATH_T retired: n8fp dead) and r survives there
   through the Horner call (fp_poly_horner never writes HORNER_G).
6. **Core:** `E := fp_poly_horner(HORNER_G, EXP_COEF)`; `w := r·E` (fp_mul, r re-read
   from HORNER_G).
7. **Reconstruct mantissa:** m ≠ 0 → `v := T̂[m]·w`; `res := T̂[m] + v` (table copy is
   canonical; addressing 18·m via HL×16+HL×2). m = 0 → `res := 1.0 + w`
   (widen_uint_to 1).
8. **Scale (exact):** build the 10^n record DIRECTLY in ARGB — sign 0, dexp = n+1
   (signed word), dig = 1,0×13, guard 0; `FAC := res·10^n` (fp_mul: mantissa ×1.0 is
   exact; round_and_finalize disposes borderline overflow → FPERR=1 / underflow → 0).
   Plain `ret` — COMPUTE-ONLY (FACTYP/DE are the stub's).

x = 0 needs **no special path** (n8=0 → r=x → E≈1 → res=1+0·… wait, res=1+w with
w=x·E=0 → exactly 1; ×10^0 exact): `EXP(0)=1` EXACT, proven in-sim.

### 12.5 `fp_log` (tenant; input ARGA = widened x, x > 0 guaranteed by the stub)

1. **Split (exact, free):** `e′ := dexp − 1` → `MATH_N` (int16); `MATH_A := x` with
   dexp forced to 1 (m ∈ [1,10)).
2. **j-scan:** j := #{j ∈ 1..8 : m > LOG_BP[j]} — fp_cmp loop, ascending, early-exit on
   first not-greater (A==4 ⟺ greater, the fp_atan idiom); loop counter/table pointer in
   `HORNER_CNT`/`HORNER_PTR` (free until Horner). **j = 8 fold:** m's dexp := 0 (m/10,
   exact), e′ := e′+1, j := 0. Store `MATH_J`.
3. **s:** `num := m − K̂[j]` (fp_sub — EXACT: same-dexp aligned 14-digit subtract; the
   fold case is dexp 0-vs-1 with the 14th digit landing in the guard slot, still exact)
   → `MATH_T`; `den := m + K̂[j]` (fp_add); `s := num/den` (fp_div) → `MATH_A`
   (m retired). K̂[j] = `POW8_TBL[j]` — record 0 is exactly 1.0, NO j=0 branch.
4. **Core:** `g := s·s` → `HORNER_G` (MATH_T retired); `Q := fp_poly_horner(g,
   LOG_COEF)`; `r := s·Q` (s from MATH_A; r replaces it there).
5. **Reconstruct (ascending magnitude; the sim-proven order):**
   - e′ = −1 → `FAC := r + NEGLNK_TBL[j]` (ONE scale-matched add), ret.
   - else: if e′ ≠ 0: e′fp := widen |e′| + sign → `MATH_T`; `r += e′fp·LN10_C2`.
     If j ≠ 0: `r += LNK_TBL[j−1]`. If e′ ≠ 0: `r += e′fp·LN10_C1` (product EXACT by
     invariant; the largest addend rounds last, at result scale). FAC := r, ret.

`LOG(1)`: j=0, num exact 0 → s=0 → r=0, no adds → **exactly 0** (proven in-sim); no
special path. COMPUTE-ONLY, plain `ret` everywhere (both functions are total over
their stub-guarded domains — every disposition inside the tenant is via FPERR/FAC,
never a status byte in A, per the CALSLT lesson).

### 12.6 Main-ROM stubs + RAM

- **`evmc_log`** = `evmc_sqr`'s shape with the domain check extended to sign-OR-zero:
  `ARGA+FPNUM_SIGN ≠ 0` → err; `dig15_iszero(ARGA+FPNUM_DIG)` Z → err; err tail =
  `FPERR:=3, DE:=0, ret` (verbatim evmc_sqr_err). Then push ix / dispatch
  `SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_LOG` / pop ix / `jp c,subrom_absent_error` /
  FACTYP:=8 / `jp flt_to_int16`.
- **`evmc_exp`** = same shape, domain check replaced by the **coarse magnitude
  disposition**: read ARGA+FPNUM_DEXP (signed word); dexp ≥ 4 (|x| ≥ 1000, SIGNED
  compare — tiny x has negative dexp) → sign clear: `FPERR:=1, DE:=0, ret`; sign set:
  `FAC:=0` (zero lead byte) then fall into the common FACTYP:=8 + flt_to_int16 tail
  (EXP(−huge) returns value 0, not an error). Otherwise dispatch
  `SUBROM_IDX_EXP`. This guarantees the tenant's |x| < 1000 / |n8| ≤ 3475 invariant.
- **RAM (§11.6 standing: NO new claims):** two new aliases in sysvars.inc —
  `MATH_N equ SQRT_K` (**2 bytes**, spans SQRT_K+SQRT_ITER $F192–$F193, both dead
  outside SQR; fp_atan's MATH_SIGN/MATH_RECIP alias the same bytes — SQR/ATN/EXP/LOG
  never run concurrently, one factor at a time) and `MATH_J equ SQRT_POW10` ($F194,
  = fp_atan's MATH_BREAK, same argument). FPNUM cells reuse MATH_A/MATH_T/HORNER_G/
  MATH_R/HORNER_ACC exactly as documented per-step above; `HORNER_CNT`/`HORNER_PTR`
  double as the LOG j-scan bookkeeping (dead until the Horner call).

### 12.7 Gate — extend `basic_probe_math_conv.py` (do NOT fork)

- **Tokens:** append `("EXP","a=exp(1)",0x8B)`, `("LOG","a=log(1)",0x8A)`.
- **Truth oracles** `truth_exp14`/`truth_log14` (Decimal, prec 50 → round14, the
  truth_atan14 shape) + pure-call matchers `_EXP_PURE_RE`/`_LOG_PURE_RE`.
- **Value batteries** (pure calls, asserted to the §12.1 bounds vs truth):
  - `EXP_BROAD_XS` (~35): 0, ±1e-13, ±1e-9, ±0.001, ±0.5, ±1, ±2, ±10, ±20, 88, 100,
    142.7, the r≈0 stress points (±2.3025850929940, 4.6051701859881, 23.025850929940),
    the n8-boundary straddle (±0.14391156831213/14), and the range straddles 145.062 /
    −147.3 (finite, value-asserted) — plus the characterization anchors.
  - `LOG_BROAD_XS` (~35): 1, 1±10^−k ladder (k=1,5,9,13), 0.99, 2, 3, 7,
    2.7182818284590, 0.5, 0.25, 0.1, 0.001, 1000, decades 1E±10/1E62/1E−64/
    9.9999999999999E62, fold-zone samples (0.87, 0.9245459892507, 0.95), breakpoint
    straddles (LOG_BP[1]/[4]/[8] values ±1 ulp as 14-sig literals), K̂-hits
    (1.3335214321633, 5.6234132519035 — s=0 rails).
  - Assert `|zb − truth| ≤ EXP_MAX_ULP(=2) / LOG_MAX_ULP(=4)` per input + battery-wide
    exact-count floors (`EXP_EXACT_FLOOR`/`LOG_EXACT_FLOOR`, set from the hardware run,
    cross-checked against the sim's per-input prediction — sim/hardware disagreement on
    any input is itself a finding for the review).
- **Domain/disposition rows (per-machine wording):** `LOG(0)`, `LOG(-1)` →
  `illegal function call`; **all three overflow paths**: `EXP(146)` (round_and_finalize
  FPERR=1), `EXP(200)` (tenant n8-bound), `EXP(1000)` (stub dexp≥4) → `overflow`; all
  three underflow paths: `EXP(-147.4)`, `EXP(-200)`, `EXP(-1000)` → `0`.
- **FACTYP-leak rows:** `PRINT EXP(1)+0.5`, `A%=EXP(1)`, `PRINT LOG(10)+0.5`,
  `A%=LOG(100)`, EXP/LOG over `PEEK` and over a single literal.
- **Reference-deviation report** (informational, ATN shape): capture the reference on
  both batteries, print the ulp summary — documents §1.1's envelope (and the newly
  found −45-ulp EXP(88) tail) without ever asserting against it.

### 12.8 Verification / standing gates

`make math-acceptance` (extended) green; `python3 tools/sim_math_chain.py` green
(committed proof stays a fast regression); `subrom-closure-check` green (both tenants'
resident surface ⊆ SQR's: fp_add/sub/mul/div/cmp, dig15_iszero, widen_fac_to/uint_to,
arga_pack_fac — NO new page-0 relocations); `subrom-acceptance`/`subrom-inttest` green
(indices 3+4); **lean basic.rom byte-identical**; sub.rom fits + boots; `unit-test`,
`float/string/input-acceptance`, reloc, kwtable single-copy green. **Fable review of
the whole slice** (standing float-pack lesson), including a per-input sim-vs-hardware
differential over the gate batteries.

### 12.9 Implementation outcome (2026-07-13) — SHIPPED

Implemented (Sonnet on §12, Fable adversarial review after — the §8.5 split). All
§12.8 gates GREEN, independently re-run by the reviewer: `math-acceptance` ALL PASS
(**EXP 24/32 correctly-rounded, worst 1 ulp; LOG 26/35, worst 2 ulp** — floors set
23/25), `unit-test` 45/45, tenant-closure 118 routines all page-0, subrom-acceptance/
inttest, float/string/input-acceptance, reloc + kwtable single-copy, **lean
`basic.rom` byte-identical to HEAD's** (SHA-256 verified twice, agent + reviewer).

**One real CONTRACT bug (mine, §12.4 step 8), found live by the implementer's gate
run:** the "FAC := res·10^n via fp_mul; round_and_finalize disposes borderline"
design missed that `fp_mul` runs `check_preexp_bounds` as a **pre-normalisation
gate** (`dexpA+dexpB > 63 → FPERR=1` even when the true product fits) — `EXP(145.062)`,
a sim-proven exact anchor, spuriously overflowed (p<1 → dexp(p)=0, scale-record
dexp=64, preExp=64>63). Verified from float-arith.asm source by the reviewer. Fix
(agent's, ratified): rescale by adjusting p's OWN dexp field directly (a pure decimal
shift — fp_sqrt's SQRT_K precedent) and dispose via `fp_add` with a **dexp-matched
zero** operand (fp_add has NO pre-check; round_and_finalize's post-check on the TRUE
dexp does the disposition). The first fix attempt used a canonical dexp=0 zero and hit
a second trap — fp_add's alignment adopts the LARGER dexp, corrupting any result with
negative true dexp (caught live via EXP(−10) etc.) — hence the dexp-matched zero. The
sim was NOT wrong (it models value semantics, which the fixed asm now matches); the
contract's step-8 mechanism was.

**Sim-vs-hardware per-input differential (§12.8):** LOG matched the sim
**bit-for-bit on all 35 battery inputs**. EXP had 6 inputs where hardware measured
1 ulp where the sim predicted exact — all within the sim's documented
no-sticky-digit modelling limit, which is precisely what EXP_MAX_ULP's +1 margin was
sized for. No unexplained disagreement.

**Accepted implementation deviations (agent-flagged):** (1) `sub/equates.inc` not
touched — the ATN precedent never declared tenant indices there (sub_p1_table is
positional); (2) the 8 FACTYP-leak compound rows route to a truth-based check
(±6 ulp) instead of ATN's raw reference-tail compare — the EXP/LOG reference is
imprecise enough (e.g. `exp(1)+0.5` prints …588 vs truth …590) that a reference
compare would fail on REFERENCE error, not ours; the rows still catch a real
FACTYP-narrowing bug (thousands of ulp); (3) the PEEK row is `exp(peek(0)\100)` — a
bare `exp(peek(0))` overflows (PEEK(0)=243, the BIOS DI opcode); LOG's is
`log(peek(0)+1)`.

**Informational finds:** the reference's own `EXP(-200)` throws `Overflow` (a full
disposition BUG in the reference — the true answer underflows to 0, which zerobas
returns); its `EXP(88)` is −45 ulp off truth; its LOG misses truth on 19/35 of our
battery. All captured in the gate's informational reports, never asserted against.

**Fable review verdict: SHIP.** Constants/tables independently re-derived from the
emitted bytes (all 41 records byte-exact vs closed forms; both polys re-validated on
a 2001-point dense grid: EXP 7.9e-17, LOG 1.9e-17); both tenant bodies traced
step-by-step against §12.4/§12.5 (cmp16 signed-compare, ×10 digit-extraction loop,
two's-complement m/n split, fold/e′ interaction hand-traced for x=0.99/0.5/0.05,
RAM live-ranges, canonical-operand discipline); both fp_mul-pre-check claims verified
from float-arith.asm source; stubs traced (the `sub 4 / jp p` signed dexp test is
correct over the full −64..63 range). One nit fixed (MATH_N byte-count comment).
**NEXT = 2c `^`** (integer exponent = exact repeated-multiply; fractional =
`EXP(y·LOG(x))`, unlocked by this slice).

---

## 13. Slice 2c implementation contract — `^` (POW operator, concrete, implementation-ready)

Grounded in a NEW five-round black-box characterization (VG-8020, 2026-07-14 —
scratchpad char_pow rounds 1–5, ~75 captures) and pre-proven by the committed
chain-sim (`tools/sim_math_chain.py`, 7f3f31f): **all 32 captured reference
anchors reproduce bit-for-bit** in the sim's model. The §12 process ("sim
before contract before asm") applied again.

### 13.1 Characterization result (pinned — do NOT re-run)

**Grammar** (all captured):
- `^` = single-byte token `$F5`, LEFT-associative: `2^3^2`=64, `2^2^3`=64,
  `(2^3)^2`=64.
- Binds ABOVE `*` `/` `\` (`2*3^2`=18, `7\2^2`=1) and above unary minus:
  `-2^2`=−4, `-2^-2`=−.25, `-2^.5`=−1.414… (a leading `-` NEVER makes the
  base negative; it negates the whole pow-chain).
- An exponent-side `-` wraps the ENTIRE following pow-chain (right-nested):
  `2^-3^2` = 2^−(3²) = 1.953125E−03, `2^-2^-2` = 2^−(2^−2) = .84089641525371.
  (This is exactly what falls out of `ev_f`'s unary-minus handler calling the
  pow layer — no special case needed, §13.3.)

**Semantics — the evaluation ladder** (each rule pinned by capture):
1. `y == 0` → result 1 (double). Includes `0^0`=1, `12345.678^0`=1.
2. `x == 0`: `y > 0` → 0 (incl. fractional y: `0^.5`=0 — the zero-base check
   PRECEDES the fractional path, no LOG(0) error); `y < 0` → **Division by
   zero** (`0^-1`, `0^-.5`, `0^-2`).
3. `y` integer-valued AND `−32768 ≤ y ≤ 32767` (asymmetric int16:
   `(-1)^32767`=−1 but `(-1)^32768`→IFC; `(-1)^-32768`=1) → **integer path**:
   - n := |y| as UNSIGNED 16-bit (32768 = $8000 representable).
   - **LSB-first square-and-multiply, acc initialised to a REAL 1.0**:
     ```
     acc := 1.0 ; s := x
     loop: if n&1: acc := fp_mul(acc, s)      ; overflow -> Overflow error
           n >>= 1 ; if n == 0: done
           s := fp_mul(s, s)                  ; overflow -> Overflow error
     ```
     Every fp_mul carries the `check_preexp_bounds` PRE-normalisation gate
     (`dexpA+dexpB > 63 → Overflow even when the true product fits`) — this is
     NOT a zerobas artifact: the reference's own `*` was probed to behave
     identically (`1D61*10`, `1D31*1D31`, `2D62*4` (product FITS) → Overflow;
     `9D61*9`=8.1E+62, `5D61*2`=1E+62 fine; zerobas repack differential 6/6
     IDENTICAL). The loop shape above makes the reference's whole odd
     overflow surface EMERGENT: `10^62`→Overflow (acc(10^30)·s5(10^32):
     E-sum 64) while `2^207`=2.0568806966517E+62 (worst sum 63) and
     `10^32`/`10^47`/`5^88`/`2^127` all fine; `1D62^1`→Overflow (acc=1·x:
     E-sum 1+63=64); `1D31^3`→Overflow (square chain 32+32); `1D12^5`=1E+60.
     Mul UNDERFLOW is silent → 0 (`.5^2000`=0).
   - `y < 0`: reciprocal AFTER the power (pinned: `.1^63`=1E-63 but
     `10^-63`→Overflow — reciprocal-FIRST would make them equal):
     p=Overflow → Overflow; **p==0 → Overflow error** (pinned `.5^-2000` →
     Overflow, NOT Division by zero — the reference's float div-by-zero
     including by a COMPUTED zero is "Division by zero", probed separately,
     so ^ must special-case p==0 BEFORE dividing); else result := fp_div(1, p)
     (our correctly-rounded div → ≤1-ulp documented deviation from the
     reference's low-biased div: ref `3^-5`=…4485, truth/us …4486).
4. else (fractional y, or integer-valued y outside int16): `x < 0` →
   **Illegal function call** (`(-2)^2.5`, `(-1)^32768`, `(-1)^3.0000001`);
   `x > 0` → **EXP(y·LOG(x))** (§5.1: bit-for-bit the reference's own
   derivation on all probes; ends follow OUR EXP's §12 dispositions — the
   reference's `10^-70.5`→Overflow is its own EXP(−162) disposition BUG
   (§12.9), ours correctly returns 0: documented deviation).

**Type**: result is ALWAYS double (`2!^3!`=8, `A%^B%`=8, `2!^.5!` prints the
full 14-digit 1.414213562373 — no single-width chain).

### 13.2 Accuracy contract (sim-proven 2026-07-14, commit 7f3f31f)

- **Positive-y integer path: REFERENCE-IDENTICAL BIT-FOR-BIT** (a composition
  of our reference-identical fp_mul in the reference's own pinned loop —
  clean-room: structure from black-box probes + published square-and-multiply;
  32/32 anchors incl. `3^33`=5.5590605665554E+15 (1 ulp BELOW truth — the
  reference's rounding, kept bug-for-bug per the §2 framework), `2^50`,
  `7^19`, `1.01^100`, `5^88`). The gate asserts BIT-IDENTITY differentially
  on this sub-surface — stronger than the ATN-shape truth gate.
- vs truth the int path inherits the structure's squaring amplification
  (each s:=s·s DOUBLES accumulated relative error → deviation ~2^bitlen(n)):
  sim battery 615 pairs, per-row structural cap `3·2^bitlen(n)` ulp HELD
  (worst measured 353 ulp @ 1.0392660791291^176 = 0.46 of cap). This is the
  reference's own error, not ours to fix.
- Negative-y (adds one correctly-rounded fp_div): same caps (measured within).
- **Fractional path**: deviation scales with |t| = |y·log x| (result rel err
  ≈ Δt): sim battery 2677 pairs, per-row cap `12·max(1,|t|)+10` ulp HELD
  (worst 91 ulp @ t≈11.3 = 0.62 of cap; ~7 ulp per unit t worst-case).
  ATN-shape gate: truth-bound caps + informational reference report; NO
  per-input never-worse claim (§2 relaxation, review-queue 2026-07-13).

### 13.3 Grammar implementation — new `ev_pw` layer (repack-only)

All under `IF ROM_BASE < $4000` (the lean build gets NO `^` — lean stays
byte-identical; `^` remains a plain uncrunched char there, an expression
error, unchanged behavior):

- `POW_TOKEN equ $F5` (basic/sysvars.inc, next to STAR_TOKEN/IDIV_TOKEN).
- **Tokeniser** (basic/tokenise.inc, SHARED lean+sub — guard the addition):
  `cp '^' → jp z,tk_op_pow` in the tk_notkw compare chain; `tk_op_pow: ld
  a,POW_TOKEN / jr tk_op_emit` beside tk_op_idiv.
- **Detokeniser** (basic/detok.inc detok_op, SHARED — guard): `cp POW_TOKEN →
  dop_pow: ld a,'^' / jr dop_emit`.
- **Evaluator** (basic/expr.asm): new layer between ev_t and ev_f —
  ```
  ev_pw:        call ev_f
  ev_pw_lp:     call ev_sp
                ld a,(ix+0) ; cp POW_TOKEN ; ret nz
                inc ix
                push de
                call push_lhs_frame
                call set_factyp_int_ret     ; FACTYP:=2 for the rhs eval
                call ev_f                   ; rhs (ev_f's unary-minus -> ev_pw
                call combine_pow            ;  gives the pinned -nesting free)
                jr ev_pw_lp                 ; loop = LEFT-assoc
  ```
  ev_t's THREE `call ev_f` operand sites (entry, after `*`, after `/`) become
  `call ev_pw` (IF-gated; lean keeps `call ev_f`). `ev_f_neg`'s operand call
  becomes `call ev_pw` (IF-gated) — this single change yields BOTH `-2^2`=−4
  AND `2^-3^2`=2^−9 (ev_f sees the exponent's `-`, recurses into ev_pw, and
  negates the whole chain).

### 13.4 `combine_pow` (basic/float-arith.asm, repack section) — dispositions MAIN-SIDE

Mirrors combine_div_float's frame protocol, then the §13.1 ladder before any
dispatch (per the CALSLT A-not-preserved rule, ALL classification/errors are
main-side):
```
combine_pow:
    call pop_lhs_and_probe        ; ZF ignored: ^ is always float
    call widen_both_operands      ; ARGA := x (lhs), ARGB := y (rhs), FPNUMs
    1) dig15_iszero(ARGB+FPNUM_DIG)  -> FAC := 1.0 double, DE via flt_to_int16, ret
    2) dig15_iszero(ARGA+FPNUM_DIG)  -> ARGB sign 0 ? (FAC := 0, done)
                                              : (FPERR := 2, DE := 0, ret)
    3) classify y from the ARGB RECORD (integer-valued iff every digit at
       index >= dexp is 0, for 1 <= dexp <= 5; dexp <= 0 -> fractional;
       dexp > 5 -> out of int16 -> fractional path):
       dexp==5 -> digit-string compare d0..d4 vs "32767" (ARGB sign 0) /
                  "32768" (sign $80); above -> fractional path.
       int: n := d0..d(dexp-1) accumulated *10 (fits uint16, pre-checked),
            MATH_N := n; MATH_J := bit0 = ARGB sign set (y negative), bit7=0.
       frac: ARGA sign nonzero -> FPERR := 3, DE := 0, ret (IFC)
             MATH_J := $80.
    4) push ix / ld ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_POW /
       call subrom_call / pop ix / jp c,subrom_absent_error
       FACTYP := 8 ; jp flt_to_int16       (evmc_log's exact tail shape)
```
Rationale for main-side classification: it reads only ARGB fields + does
16-bit arithmetic (no fp calls), and every error exit needs main-side FPERR
discipline anyway. The tenant receives x in ARGA, y in ARGB, n in MATH_N,
mode/sign in MATH_J.

### 13.5 `fp_pow` tenant (sub/fp_pow.asm, PAGE-1, `SUBROM_IDX_POW equ 5`)

Appended to sub_p1_table after fp_log (idx 4). COMPUTE-ONLY (FAC correct on
exit, FACTYP/DE untouched — stub's job), no A-returns, errors via FPERR only.

**RAM live-ranges** (all existing cells, no new allocation):
- int path: `SQRT_X` := s (the running square), `SQRT_Y` := acc stash across
  the squaring mul, `MATH_N` := n (consumed bit-by-bit), `MATH_J` bit0 read at
  the end (y-negative). fp_mul/fp_div touch none of these. acc lives in ARGA.
- frac path: y is copied to the **FOUTBUF FPNUM cell** (the §11.6 "3rd cell"
  precedent — SQRT_X/SQRT_Y are CLOBBERED by fp_log/fp_exp internals: MATH_A
  aliases SQRT_Y, HORNER_G aliases SQRT_X), MATH_J read ONCE at entry (fp_exp/
  fp_log clobber it: MATH_J aliases their m/j).

```
fp_pow:  MATH_J bit7 ? -> fp_pow_frac
 ; --- int path: LSB-first square-and-multiply (§13.1 rule 3, sim-proven) ---
         copy18 ARGA -> SQRT_X               ; s := x
         widen_uint_to(1) -> ARGA            ; acc := 1.0  (a REAL one: the
                                             ;  1D62^1 anchor NEEDS acc=1*x)
 fpw_lp: bit0(MATH_N)? : copy18 SQRT_X -> ARGB ; acc := acc*s
                         call fp_mul ; FPERR? -> ret
         srl (MATH_N) 16-bit ; zero? -> fpw_done
         copy18 ARGA -> SQRT_Y               ; stash acc
         copy18 SQRT_X -> ARGA ; copy18 SQRT_X -> ARGB
         call fp_mul ; FPERR? -> ret         ; s := s*s
         copy18 ARGA -> SQRT_X ; copy18 SQRT_Y -> ARGA
         jr fpw_lp
 fpw_done:
         MATH_J bit0 clear -> arga_pack_fac, ret
         dig15_iszero(ARGA)? -> FPERR := 1, ret   ; reciprocal of underflowed
                                             ; 0 = Overflow (pinned .5^-2000)
         copy18 ARGA -> ARGB ; widen_uint_to(1) -> ARGA
         call fp_div                          ; 1/p, correctly rounded
         arga_pack_fac, ret                   ; (fp_div's own bound check
                                              ;  handles 1/1E-63 -> Overflow)
 ; --- frac path: EXP(y*LOG(x)) (§13.1 rule 4) ------------------------------
 fp_pow_frac:
         copy18 ARGB -> FOUTBUF-cell          ; save y across fp_log
         call fp_log                          ; ARGA/FAC := ln(x)  (x>0
                                              ;  guaranteed by the stub)
         copy18 FOUTBUF-cell -> ARGB
         call fp_mul ; FPERR? -> ret          ; t := ln(x)*y  (pre-check on a
                                              ;  huge-E y IS the right
                                              ;  disposition: |t| overflows)
         ARGA dexp >= 4 ?                     ; |t| >= 1000: fp_exp's stub
             sign neg -> FAC := 0, ret        ;  precondition (§12.6) —
             else FPERR := 1, ret             ;  replicate evmc_exp's coarse
                                              ;  disposition TENANT-side
         call fp_exp                          ; FAC := e^t (packs FAC itself)
         ret
```
copy18 = the fat_copy18/fsq_copy18 idiom (in-page). fp_log/fp_exp are DIRECT
in-page calls (same assembly unit sub/sub.asm — the first tenant-to-tenant
composition; NO nested subrom_call). Verify fp_log's exit leaves ARGA = the
result FPNUM (it ends in round_and_finalize/arga_pack_fac — if it only
guarantees FAC, insert widen_fac_to ARGA after it).

Resident-ABI surface: fp_mul, fp_div, widen_uint_to, dig15_iszero,
arga_pack_fac (+ transitively whatever fp_log/fp_exp already import) — a
SUBSET of the existing imports, NO new page-0 relocations expected;
`make subrom-closure-check` re-audits mechanically.

### 13.6 Gate — extend `basic_probe_math_conv.py` (do NOT fork)

- **Token row**: crunch capture `2^3` → `… $F5 …` (check_tokens extension) +
  a LIST round-trip row (detok renders `^`).
- **Grammar battery (differential, EXACT-match both machines)**: the §13.1
  grammar pins — `2^3^2`, `2^2^3`, `-2^2`, `2^-3`, `-2^-2`, `2^-3^2`,
  `2^-2^-2`, `2*3^2`, `7\2^2`, `-2^.5`, `(2^3)^2`, `2^-3*4`.
- **Int-path battery (differential, BIT-IDENTITY — the §13.2 claim)**: the 18
  value anchors + the 8 disposition anchors from POW_REF_ANCHORS (sim table,
  same rows) + ~15 random in-envelope (x,n) pairs frozen by seed. Error rows
  use the probe's per-machine wording mechanism (`Overflow`/`overflow` etc.).
- **Neg-y battery (truth-bound, ATN shape)**: `3^-5`, `2^-40`, `2^-10`,
  `10^-31`, `.1^-63`(→Overflow both sides expected — informational
  differential), caps per §13.2 + informational reference-deviation report.
- **Frac battery (truth-bound, ATN shape)**: ~20 (x,y) pairs across |t| ∈
  [0.1, 140] with per-row `12·max(1,|t|)+10` caps vs truth_pow (new
  `truth_pow14` helper mirroring the sim's pow_truth) + the §13.1 rule-4
  domain rows ((-2)^2.5 → IFC; 10^62.5 value; 10^63.5 → Overflow both;
  10^-70.5 → 0 OURS vs Overflow REFERENCE — the documented §12.9-bug
  deviation row, asserted OURS=0 + reference captured informationally).
- **Zero/one/type rows**: 0^0, 0^2, 0^.5, 0^-1, 0^-.5, x^0, 1^123456789,
  2!^3!, A%=2:B%=3:A%^B%, and FACTYP-leak `a%=2^3`, `a#=2^.5:a#*a#`.
- **Sim-vs-hardware per-input differential** on the int + frac batteries
  (the §12.8/§12.9 practice: LOG matched 35/35; expect the int path to match
  bit-for-bit, frac within the no-sticky modelling margin).

### 13.7 Verification / standing gates

Same §12.8 list: `math-acceptance` extended + green; `sim_math_chain.py`
green; `subrom-closure-check` (fp_pow's closure ⊆ existing); lean basic.rom
**byte-identical**; sub.rom fits (fp_pow ≈ 250–350 B page-1 island, ~13 KB
free); `unit-test`, float/string/input-acceptance, reloc, kwtable
single-copy; IPS rebuild + reinstall before machine probes
([[ips-rebuild-after-basic-change]]). Fable review after implementation
(§8.5 model split).

### 13.8 Implementation outcome (2026-07-14) — SHIPPED

Implemented (Sonnet on §13, Fable adversarial review after — the §8.5 split).
All §13.7 gates GREEN, independently re-run by the reviewer: `math-acceptance`
470 PASS / 0 FAIL (grammar 12/12 differential-exact; **int-path anchors 32/32
BIT-IDENTICAL to the reference** + 10 frozen random pairs; neg-y/frac rows
inside their per-row caps), `unit-test` 45/45, tenant-closure 118 routines all
page-0 (no new relocation; the resident-ABI inc regenerated for the
combine_pow-shifted page-0 addresses), subrom-acceptance/inttest, float/
string/input-acceptance, basic-reloc, **lean basic.rom byte-identical to
HEAD's** (SHA-256 verified from both trees by the reviewer). Sim-vs-hardware:
int anchors 32/32 bit-for-bit; frac battery 4/20 rows 1 ulp from the sim —
inside the documented no-sticky-digit modelling margin (the §12.9 EXP
precedent).

**Three real fp-core interaction bugs found live by the implementer** (all
§13.5-contract gaps, fixed in sub/fp_pow.asm with in-place mechanism notes):
(1) fp_mul's silent UNDERFLOW abort sets FAC:=0 but leaves ARGA completely
untouched → the loop's raw copy18-from-ARGA froze a stale partial product
(`0.5^2000` printed 2.43…E-63) — fixed with `widen_fac_to` after every loop
fp_mul; (2) fp_mul's zero-PRODUCT path leaves a stale nonzero dexp in ARGA →
the frac path's coarse |t|≥1000 test misread `ln(1)*bigY` as huge
(`1^123456789` → spurious Overflow) — same fix at the t site; (3)
arga_pack_fac's documented not-all-zero precondition is violated by a
genuinely-zero acc (`0.5^2000` then printed `.`) — fixed by NOT re-packing at
the positive exit (the loop guarantees the last fp_mul was the acc-multiply,
so FAC is already authoritative), and by tail-jumping fp_div on the
reciprocal (its own tail is the sole authority — an explicit re-pack would
resurrect the stale pre-div ARGA=1.0 over a correct Overflow disposition).

**Contract corrections (ratified in review):** §13.5's FOUTBUF y-stash is
infeasible — FOUTBUF aliases HORNER_ACC, clobbered by fp_log/fp_exp's own
Horner; y is stashed on the machine stack instead (18 bytes, zero new RAM).
§13.6 mis-listed `-2^.5` as an exact-match grammar row — `2^.5` rides the
frac path where we deviate from the reference by design (the reference's own
EXP·LOG 2^.5 is 1 ulp low, printing 13 digits); routed through the
truth-bound cap instead. §13.2's bit-identity claim is positive-y only —
live runs confirm random negative-y pairs deviate ≤1 ulp via our
correctly-rounded div (expected, documented).

**Also fixed (latent, pre-existing):** basic/tokenise.inc + basic/detok.inc
were never build prerequisites (main OR sub ROM) — the ba652b7 staleness
class; `^` is the first change to touch them since.

**Reviewer verdict: SHIP.** combine_pow's classification ladder traced
against §13.1 (dexp word read, digit-scan, asymmetric dexp==5 bound via the
established tkf_ref32767/32768 + dig15_cmp idiom, dig_to_word accumulate);
ev_pw's frame protocol matched against ev_t_mul's; both tenant paths traced
including the three fix mechanisms verified against round_and_finalize/
check_preexp_bounds headers; the stack-stash's byte-exact save/restore order
hand-verified; live edge probes on BOTH machines (8/8 match: `1^9.5D62`=1 —
the stale-dexp-zero × huge-dexp-y pre-check compound the reviewer flagged —
plus 0^0/0^.5/0^-1/2^-3^2/1D62^1/(0.5)^-2000 dispositions).
**NEXT = 2d SIN/COS/TAN** (shared kernel: TAN=SIN/COS bit-for-bit,
COS=SIN(x+π/2), §1.2), then 2e RND (LCG capture campaign).

---

## 14. Slice 2d implementation contract — `SIN` + `COS` + `TAN` (concrete, implementation-ready)

**Status: 🟢 CONTRACT 2026-07-14** — the ratified §5/§8 slicing's fourth cut, the
trig cluster. Written against the live code (fp_exp.asm as the reduction template,
fp_pow.asm for the tenant-to-tenant / stashing precedent, expr.asm `evmc_atn` for the
no-domain-check stub, sub.asm `sub_p1_table`) and — the §12/§13 process — against a
**pre-proven 14-digit chain simulation** ([tools/sim_math_chain.py](../tools/sim_math_chain.py),
committed 24cb6f2): the fits AND the full reduce+poly chain accuracy were measured
BEFORE this contract was finalized. Implementation = Sonnet on this contract, Fable
review after (§8.5 split).

### 14.1 Characterization result (pinned 2026-07-14 — do NOT re-run)

Fresh VG-8020 black-box capture ([scratchpad/char_trig.py](../scratchpad/char_trig.py),
cached char_trig.json), extending §1.1/§1.2 with the quantitative reduction floor:

- **Exact anchors (confirmed):** `SIN(0)`=0, `COS(0)`=1, `TAN(0)`=0.
- **`TAN(x)` = `SIN(x)/COS(x)`** bit-for-bit (§1.2); `COS(x)` = `SIN(x+π/2)` (shares the
  SIN kernel; the near-π/2 catastrophic COS error is the reduction signature).
- **The reference's reduction is WEAK** (limited-precision ~13-digit stored π): signed
  ulp-vs-truth grows ≈ linearly with |x| — `SIN(1000)` **1649 ulp**, `SIN(1E5)` **2.9M
  ulp**, `SIN(1E8)` **1.1E8 ulp** off truth. Its first few digits stay right (7 at 1E5),
  the rest are garbage.
- **Reduction floor: the reference RETURNS 0 for |x| ≥ 1E13** (both SIN and COS by 1E14;
  SIN already 0 at 1E13). This is exactly where x's OWN 14-sig ULP reaches ≥ 1 rad, so the
  argument is meaningless and *no* implementation can do better. Our design's natural floor
  (§14.5 step 3, dexp′≥15) sits even further out (~1.57E14). In [0, 1E13) we are
  dramatically better; in the meaningless band **[1E13, 1.57E14) we return bounded values in
  [−1,1] while the reference returns 0** — *both* are garbage (x's ULP ≥ 10 rad there;
  e.g. `sin(1E14)` ours −0.948 vs truth −0.209, reference 0), so "never worse" is not a
  meaningful per-input claim in that band (nothing asserts it — the gate pins our floor
  outputs 0/1/0 for |x|≥1.57E14 by capture, §14.8). Above 1.57E14 we too return 0/1/0.
- **Near π/2:** `TAN` → large finite (no error); `TAN(1.5707963267949)` = −15915494309189
  (reference), a large finite our fp_div reproduces in kind (not bit).
- **Tokens (§1.4):** `SIN`=`$FF $89`, `COS`=`$FF $8C`, `TAN`=`$FF $8D` (gate re-confirms
  vs the real crunch; capture wins on any disagreement).

### 14.2 Proven accuracy envelope (sim, ~6000-input moderate battery + 4000 large-|x|)

SIN/COS ∈ [−1,1], so **ABSOLUTE error is the uniform metric** (relative ulp inherently
blows up at the result-zeros — the reference too, §1.1); TAN uses relative-ulp in the
well-conditioned band away from both its zeros (k·π) and poles (π/2+k·π).

| Fn | metric | measured worst | bound asserted | reference (informational) |
|---|---|---|---|---|
| `SIN` | abs error | **1.0E-14** (~1 ulp), **100 %** correctly-rounded (\|val\|≥0.1) | abs ≤ `3E-14`, CR ≥ 85 % | 1649 ulp @1000, 2.9M @1E5 |
| `COS` | abs error | **1.0E-14**, **100 %** correctly-rounded | abs ≤ `3E-14`, CR ≥ 85 % | catastrophic near π/2 |
| `TAN` | rel ulp (0.1≤\|tan\|≤10) | **11 ulp** @ x≈950 (band edge: \|sin\| or \|cos\|≈0.1 amplifies) | ≤ `16` (~1.5× margin) | 44577 ulp @12345 |
| SIN/COS large-\|x\| | abs error | grows ~\|x\|·1E-14 (n·C2 rounding) | ≤ \|x\|·1E-13 (structural tripwire) | 0 (gives up) @≥1E13 |

Anchors proven exact in-chain: `SIN(0)`=0, `COS(0)`=1, `TAN(0)`=0; oddness
`SIN(−x)`=−`SIN(x)` / evenness `COS(−x)`=`COS(x)` bit-exact. **Documented bounded
deviation, ATN/EXP/LOG-shape gate** (truth-bound + informational reference report; no
per-input never-worse claim — but here it's academic, the reference is 3–6 orders worse
everywhere it matters).

### 14.3 Constants (already emitted + committed, 24cb6f2 — sub/math-coeffs.inc)

OWN decimal minimax (gen_math_coeffs.py §4 provenance; `check_2d_invariants` asserts every
precondition at generation time):

- `SIN_COEF` — **S(u) = sin(√u)/√u**, deg 6 (7 terms), fit 3.1E-18 on u∈[0,(π/4)²]; the
  odd sine is `sin(r) = r·S(r²)`, so S carries only even powers of r. `S(0)`=c0 rounds to
  **exactly 1** (⇒ `SIN(0)`=r·S=0 exact).
- `COS_COEF` — **C(u) = cos(√u)**, deg 6 (7 terms), fit 4.7E-17 on the same domain;
  `cos(r) = C(r²)`. `C(0)`=c0 rounds to **exactly 1** (⇒ `COS(0)`=1 exact).
- `TWO_OVER_PI` = round14(2/π) — the reduction selector (n := round(x·2/π)).
- `SIN_C1` = π/2 to **5 significant digits (exactly 1.5708, trailing zeros)** so **n·C1 is
  EXACT in 14 digits for |n| ≤ 10⁹** (5 sig + 9-digit n = 14), asserted; `SIN_C2` =
  round14(π/2 − C1) (≈ −3.673E-6) carries the next 14 digits, so C1+C2 ≈ π/2 to ~19 digits.
  The ONLY reduction error is n·C2's rounding (~|x|·1E-14) — see §14.2's floor row.

### 14.4 Home + tokens + dispatch

- **Home:** one body file [sub/fp_sin.asm](../sub/fp_sin.asm) holding the **shared
  `sincos_kernel`** plus three thin tenant entries `fp_sin`/`fp_cos`/`fp_tan`, page-1
  tenants after `fp_pow`. REUSES `fp_poly_horner` + `fat_copy18` directly (same assembly
  unit; sub.asm includes fp_atan.asm…fp_pow.asm before this file). Main-ROM stubs
  `evmc_sin`/`evmc_cos`/`evmc_tan` (repack-only, `IF ROM_BASE < $4000`). Lean 16 KB
  `basic.rom` **byte-identical** (all new code is sub-side).
- **Tokens (§1.4):** `SIN_TOKEN equ $89` / `COS_TOKEN equ $8C` / `TAN_TOKEN equ $8D` in
  sysvars.inc (repack block, beside `ATN_TOKEN`) + three kwtable.inc crunch entries
  (`db 3,"SIN",2,PEEK_PREFIX,SIN_TOKEN`, same for COS/TAN). Gate confirms all three bytes
  vs the real crunch; detok/LIST free via the single-copy table.
- **Tenant indices:** `SUBROM_IDX_SIN equ 6`, `SUBROM_IDX_COS equ 7`, `SUBROM_IDX_TAN
  equ 8` (append-only, sysvars.inc IFNDEF block); `jp fp_sin` / `jp fp_cos` / `jp fp_tan`
  appended to `sub_p1_table` (positional — sub/equates.inc NOT touched, the ATN/EXP/LOG
  precedent).
- **Dispatch:** three selectors in `ev_ff_mathconv` (`cp SIN_TOKEN / jp z,evmc_sin`, same
  for COS/TAN), after the LOG selector.

### 14.5 `sincos_kernel` (shared; input ARGA = widened x → sets sv, cv, quad)

The heart of the slice: **ONE reduction produces BOTH sv=sin(r) and cv=cos(r)**, so SIN,
COS, and TAN differ only in a final quadrant-select (no second reduction, no re-run, no
stack stash — the fp_pow y-stash problem is sidestepped entirely). COMPUTE-ONLY, plain
`ret`; leaves `sv`→`MATH_A`, `cv`→`MATH_R`, `quad` (0..3)→`MATH_J`. Works on **a = |x|**
(the wrappers own the x-sign). Persistent cells (all §14.7 aliases): `MATH_A` (a→r→sv),
`MATH_T`/`HORNER_G` (nf→u), `MATH_R`/`HORNER_ACC` (r1-temp→cv), `MATH_J` (quad byte);
`MATH_N` is UNUSED by the kernel (free for the wrappers' x-sign stash).

1. **a := |x|:** `fat_copy18` ARGA→`MATH_A`, force `MATH_A+FPNUM_SIGN`:=0.
2. **q := a·TWO_OVER_PI** (fp_mul, widen → ARGA).
3. **n := round(q), quad := n&3, via add-half-then-truncate** (avoids a digit-carry loop):
   - `q′ := q + 0.5` (fp_add; build ARGB=0.5 inline: sign 0, dexp 0, dig[0]=5 rest 0 —
     value 5·10⁻¹; widen result). round(q)=floor(q+0.5) for q≥0.
   - Read `dexp′` (signed low byte, safe per widen_fac_to's ±64 guarantee — same idiom as
     fexp step 2). **dexp′ ≤ 0** → q′∈[0.5,1) → n=0: `quad:=0`, `nf:=0.0` (skip the
     reduction; r=a). **dexp′ ≥ 15** → the units digit (index dexp′−1) falls off the
     14-digit array → **FLOOR** (x meaningless, |x|≥~1.57E14): set `sv:=0.0`, `cv:=1.0`
     (so SIN=0, COS=1, TAN=0 — closest to the reference's own 0-return, finite, no 0/0),
     `quad:=0`, `ret`.
   - **1 ≤ dexp′ ≤ 14:** `nf := q′` with digits `d[dexp′..13]` and guard zeroed (a pure
     suffix-zero truncation — NO round-up, the +0.5 already rounded). `quad`: dexp′==1 →
     `d[0] & 3`; else `(2·d[dexp′−2] + d[dexp′−1]) & 3` (10≡2 mod 4). Store `quad`→`MATH_J`.
     Copy `nf`→`MATH_T`.
4. **Reduce (nf·C1 EXACT by the §14.3 invariant; fp_sub EXACT by alignment — the fexp
   step-5 pattern verbatim):** `r := a − nf·SIN_C1` (fp_mul nf·C1, widen, ARGB; ARGA:=a
   from MATH_A; fp_sub, widen → `MATH_R` temp); `r := r − nf·SIN_C2` (fp_mul nf·C2, widen,
   ARGB; ARGA:=r from MATH_R; fp_sub, widen → ARGA). nf now dead (MATH_T free).
5. **u := r·r:** copy r→`MATH_A` (a retired), copy→ARGB, fp_mul (ARGA still r) → u, widen →
   `HORNER_G` (=MATH_T). [MATH_A=r, HORNER_G=u]
6. **sv := r·S(u):** `S := fp_poly_horner(HORNER_G, SIN_COEF)` (FAC; HORNER_G=u preserved),
   widen, ARGB:=S; ARGA:=`MATH_A`(r); fp_mul → sv=r·S, widen; store sv→`MATH_A` (r retired).
7. **cv := C(u):** `C := fp_poly_horner(HORNER_G, COS_COEF)` (FAC=cv; HORNER_ACC=MATH_R is
   the horner's own transient, done on return), widen; store cv→`MATH_R`. `ret`.
   [MATH_A=sv, MATH_R=cv, MATH_J=quad]

x=0 needs no special path: n=0, r=a=0, u=0, sv=0·S=0, cv=C(0)=1 (proven in-sim).

### 14.6 `fp_sin` / `fp_cos` / `fp_tan` (tenant entries; quadrant-select over sv/cv)

A shared `sc_select(q)`: `q&1==0` → source `MATH_A`(sv) else `MATH_R`(cv); `fat_copy18`
source→the target FPNUM (ARGA or ARGB per caller); `q&2` → flip the target's sign byte
(fp negate is exact). `qq := (quad + off) & 3`:

- **`fp_sin`** (off=0): save x-sign (`MATH_N` := `ARGA+FPNUM_SIGN`, before the kernel);
  `call sincos_kernel`; `sc_select(quad+0)`→ARGA/FAC; if `MATH_N`≠0 flip `FAC` sign; `ret`.
- **`fp_cos`** (off=1): `call sincos_kernel`; `sc_select((quad+1)&3)`→FAC; `ret` (COS even —
  no x-sign; COS(|x|)=COS(x)).
- **`fp_tan`** (off=0, odd): save x-sign→`MATH_N`; `call sincos_kernel`;
  `sc_select(quad+0)`→**ARGA** (=sinv); `sc_select((quad+1)&3)`→**ARGB** (=cosv);
  `fp_div` (FAC := sinv/cosv); if `MATH_N`≠0 flip `FAC` sign; `ret`. cosv→0 (x at π/2) is
  disposed by fp_div's own tail (reference returns a large finite; captured, not asserted).

All three COMPUTE-ONLY (plain `ret`; the stubs own FACTYP/DE). `sincos_kernel` is a local
`call` (registers survive per normal call/ret; the wrappers keep the x-sign in `MATH_N`,
which the kernel never touches, NOT a register).

### 14.7 Main-ROM stubs + RAM

- **`evmc_sin`/`evmc_cos`/`evmc_tan`** = **`evmc_atn`'s shape verbatim** (SIN/COS/TAN are
  total over all x, §6 — NO domain check, no error tail): `ev_mc_arg`; `widen_rhs_operand`
  into ARGA; `push ix`; `ld ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_{SIN,COS,TAN}`;
  `subrom_call`; `pop ix`; `jp c,subrom_absent_error`; `FACTYP:=8`; `jp flt_to_int16`.
- **RAM (§12.6 standing: NO new claims):** the kernel reuses `MATH_A`/`MATH_T`/`HORNER_G`/
  `MATH_R`/`HORNER_ACC` exactly as EXP/LOG do; `MATH_J` (=`SQRT_POW10`) holds `quad`;
  `MATH_N` (=`SQRT_K`+`SQRT_ITER`, 2 B) holds the wrapper's x-sign byte (the kernel leaves
  it untouched — the whole point of NOT keeping it in a register). SIN/COS/TAN never run
  concurrently with SQR/ATN/EXP/LOG/POW (one factor at a time — every prior slice's
  argument).

### 14.8 Gate — extend `basic_probe_math_conv.py` (do NOT fork)

- **Tokens:** append `("SIN","a=sin(1)",0x89)`, `("COS","a=cos(1)",0x8C)`,
  `("TAN","a=tan(1)",0x8D)`.
- **Truth oracles** `truth_sin14`/`truth_cos14`/`truth_tan14` (Decimal prec 50 → the
  high-precision quadrant reduction of char_trig.py, promoted) + pure-call matchers.
- **Value batteries** (asserted vs truth):
  - `SIN_BROAD_XS`/`COS_BROAD_XS` (~40 each): 0, small angles, the quadrant boundaries
    (π/4, π/2, π, 3π/2, 2π as 14-sig literals) and ±1 ulp straddles, negatives (oddness/
    evenness rows), 100, 628.318…, 1000, plus the §14.1 anchors. **Assert
    `|zb − truth| ≤ SIN_ABS_TOL (3E-14)` per input** (absolute — sin/cos are bounded) +
    a correctly-rounded floor (`SIN_CR_FLOOR`/`COS_CR_FLOOR` on |val|≥0.1 inputs, set from
    the hardware run, cross-checked vs the sim's per-input prediction — any disagreement is
    itself a review finding).
  - `TAN_BAND_XS` (~25): x giving 0.1≤|tan|≤10; assert relative ulp ≤ `TAN_MAX_ULP (16)`.
  - **`TAN_NEARPI2_XS` / large-|x| rows** (1.5707, 1.57079, 1000, 1E5, 1E8, 1E13): **pin to
    captured-zerobas** (SPAN_ONLY / a `TAN_KNOWN` map), NOT truth — the near-π/2 poles and
    the reduction floor are documented deviations (the SQR-floor precedent).
- **Reference-deviation report** (informational, ATN/EXP shape): capture the reference on
  the batteries, print the ulp summary (documents §14.1's weak-reduction envelope + the
  1E13 zero-floor) without ever asserting against it.

### 14.9 Verification / standing gates

`make math-acceptance` (extended) green; `python3 tools/sim_math_chain.py` green (the
committed proof stays a fast regression); `subrom-closure-check` green (the three tenants'
resident surface ⊆ the existing set: fp_add/sub/mul/div/cmp, dig15_iszero, widen_fac_to/
uint_to, arga_pack_fac, fp_poly_horner — **NO new page-0 relocation**); `subrom-acceptance`/
`subrom-inttest` green (indices 6/7/8); **lean basic.rom byte-identical**; sub.rom fits +
boots; `unit-test`, `float/string/input-acceptance`, reloc, kwtable single-copy green.
IPS rebuild + reinstall before machine probes ([[ips-rebuild-after-basic-change]]).
**Fable review of the whole slice** (standing float-pack lesson), including a per-input
sim-vs-hardware differential over the gate batteries.

### 14.10 Open watch-items for implementation (flagged by the contract author)

1. **`sincos_kernel` round-half (step 3) modelling boundary + sim is NOT a bit-exact
   oracle (RESOLVED by the 2026-07-14 adversarial review):** the sim models `n` as the
   exact round of the 14-digit q; the asm does `fp_add(q,0.5)` then truncate. These agree
   except when the fp_add rounds (q ≳ 1E13 — floor regime, unasserted). MORE IMPORTANTLY,
   the review's mandated sim-vs-hardware differential found the sim's exact-then-round op
   model differs from the real core (no-sticky-digit alignment) by 1 ulp on **~23 % of the
   moderate battery** (small-u Horner adds), so the original "matches the sim bit-for-bit"
   expectation is UNACHIEVABLE and was wrong to state. The correct check is **"hardware
   matches a FAITHFUL digit-level core model"**, which the review verified (all 111 live
   gate values bit-for-bit) — and it re-measured the whole §14.2 envelope under real-core
   semantics with every bound holding. The gate's truth-bound tolerances (3E-14 abs / 16
   ulp) carry that 1-ulp margin, so the shipped values + bounds are correct; the sim stays
   a valid **bounds/envelope** regression proof (its docstring now says so). Promoting the
   faithful-core model into `sim_math_chain.py` is a **slice-2e follow-up** (RND's black-box
   capture will want a bit-exact model).
2. **`fp_tan` cosv→0:** exactly-zero cosv (x landing on a 14-sig π/2 where the selected cos
   rounds to 0) would hit fp_div's Division-by-zero rather than the reference's large-finite.
   The characterized `TAN(1.5707963267949)` is a *tiny-nonzero* cos → large finite (fp_div
   fine); an exactly-0 case is not known to occur, but the implementer should confirm
   fp_div's disposition there and add a guard only if a live probe surfaces one.
3. **Token bytes** are asserted from §1.4's prior capture; the gate's token check is the
   arbiter (capture wins on disagreement).

### 14.11 Implementation outcome (2026-07-14) — SHIPPED

Implemented (Sonnet on §14, independent Fable adversarial review after — the §8.5 split;
commit 5ec4935, review follow-ups d082fd7). All §14.9 gates GREEN, independently re-run:
`math-acceptance` **ALL PASS** (tokens `$89`/`$8C`/`$8D` confirmed vs the fresh VG-8020
crunch; **SIN 28/28, COS 31/31 correctly-rounded** on the moderate battery, worst abs
1.0E-14 — matching the sim exactly; TAN worst 4 ulp in-band vs bound 16; the 9 floor rows
and the near-π/2/large-|x| pins all hold), `unit-test` 45/45, `subrom-closure-check` 118
routines all page-0 (**no new relocation**), `subrom-acceptance`/`inttest`, float/string/
input-acceptance, reloc + kwtable single-copy, **lean `basic.rom` byte-identical to HEAD**
(worktree sha match, independently reverified), sub.rom fits + boots, `sim_math_chain`
green.

**One real CONTRACT gap, self-caught live by the implementer** (the fp_pow §13.8 class):
§14.6's `sc_select`-then-`arga_pack_fac` missed that `arga_pack_fac` has a **not-all-zero
ARGA precondition** — `SIN(0)`=0 (kernel's dexp′≤0 path → exact-zero sv) packs a
non-canonical `$40` lead byte instead of `FAC:=0`. Fixed with `fsc_pack_arga`, a
`dig15_iszero`-guarded pack tail on fp_sin/fp_cos (fp_tan is safe — fp_div's own
round_and_finalize carries the guard). The shared-kernel design (one reduction → sv+cv,
select for SIN/COS/TAN) worked as specified — TAN needed no stack-stash, unlike fp_pow.

**Adversarial review verdict: SHIP** (no value-level bug survived a hostile pass; the
reviewer built an independent faithful digit-level core model that reproduced all 111 live
gate values bit-for-bit and re-measured the entire §14.2 envelope under real-core
semantics — every bound held). Three follow-ups landed (d082fd7): (1) the `sck_floor` path
was gated by nothing → 9 pinned floor rows + sim anchors added; (2) the sim's "measure-zero"
no-sticky-digit claim was false for trig (~23 % differ by 1 ulp, within bounds) → docstring
+ §14.10 + header corrected, sim reframed as a bounds/envelope proof not a bit-exact oracle
(a faithful-core model is a **2e follow-up**); (3) §14.1's "never worse" softened for the
meaningless [1E13, 1.57E14) band. **NEXT = 2e `RND`** (black-box LCG capture campaign;
§5 — will want the faithful-core sim model).

---

## 15. Slice 2e — `RND` (implementation contract)

`RND` is the LAST slice-2 function and is **categorically different** from the six
transcendentals + `^`: it is not an approximation with a bounded-deviation envelope, it is a
**pseudo-random generator whose entire contract is sequence reproducibility**. So the target
is **bit-for-bit reference-IDENTITY** (the strongest form, like the 2c `^` positive-int
path), *not* documented deviation — and reference-identity is both **achievable** (the
recurrence is exact integer arithmetic mod 10¹⁴; there is no coefficients-in-ROM wall) and
**required** (a program that reseeds with `RND(-k)` and reads the sequence must get the same
numbers as the reference). `A`/`C`/`S₀` below are three constants **recovered purely
black-box** (observe output, fit the recurrence — admissible per §4.2, the same footing as
the division characterization; no ROM disassembly).

### 15.1 Characterization (black-box, Philips VG-8020, 2026-07-14 — don't re-probe)

Harness `scratchpad/char_rnd*.py` (KEYBUF REPL, ~15 consecutive transitions + a reseed
battery + edge probes, **every value exact**). The complete model:

| | |
|---|---|
| State `S` | a 14-digit decimal integer ∈ [0, 10¹⁴) |
| Multiplier `A` | `21132486540519` |
| Increment `C` | `14389820420821` |
| Power-on / reset seed `S₀` | `40649651372358` |
| Modulus `M` | `10¹⁴` |
| **advance(S)** | **`(A·S + C) mod 10¹⁴`** |

- `RND(x>0)`: `S := advance(S)`; return `S·10⁻¹⁴`. **The argument VALUE is ignored** — any
  positive x advances exactly once (confirmed: `RND(7)`, `RND(.3)`, `RND(12345)`, `RND(99)`,
  `RND(2)` all step identically to `RND(1)`).
- `RND(0)`: return `S·10⁻¹⁴` (**no advance** — repeats the last value).
- `RND(x<0)`: `S := advance(mant14)`; return `S·10⁻¹⁴`, where **`mant14` = the 14 mantissa
  digit slots of the argument as an integer** (sign & exponent ignored). This is literally
  the widened-ARGA digit array `d[0..13]` read as a 14-digit integer (`d[0]` = the 10¹³
  place). A *double* fills all 14 slots; a *single* fills 6 + trailing zeros (hence
  `RND(-A!)` with `A!=1/3` ⇒ mant14 `33333300000000`, different from `RND(-1/3)`'s
  `33333333333333`). Exponent-independence explains the observed collision
  `RND(-1)`=`RND(-0.001)`=`RND(-1E9)` (all have mantissa `1.000…`).
- **Return type is DOUBLE** (FACTYP=8; `PRINT RND(1)` with no `DEFDBL` shows 14 digits).
  Value ∈ [0,1). **No domain errors** (all args valid).
- **Reset**: `S := S₀` happens in **`clear_vars`** — confirmed reference-identical:
  `NEW`, `CLEAR`, `RUN` all reset the seed to S₀ (first `RND(1)` after each =
  `advance(S₀)`=`.59521943994623`); `CLS` does **not** (screen-only, no var wipe). This is
  exactly DEFTBL's reset site, and cold boot runs `clear_vars` too — so one hook covers
  power-on + all three clears, no separate cold-boot path.
- **`RANDOMIZE` is OUT OF SCOPE**: the reference MSX1 BASIC 1.0 answers `RANDOMIZE 1` /
  `RANDOMIZE 42` with **`Syntax error`** — it is not a supported keyword here. Noted as a
  potential separate follow-up (a statement, not the `RND` function); not a 2e deliverable.

Proven in `tools/sim_math_chain.py` (`rnd_validate`, commit bc6417b): the exact recurrence
AND a **model of the intended asm algorithm** reproduce all 19 captured anchors bit-for-bit.

### 15.2 The arithmetic — why `fp_mul` is the WRONG tool

`advance` needs the **LOW 14 digits** of `A·S + C`. `A·S ≈ 2·10²⁷`; `fp_mul` produces the
**HIGH 14 significant digits** of a product (that is what a *float* multiply is) and would
discard exactly the digits `RND` keeps. So `RND` does **not** use the resident fp ops at
all. It needs a dedicated **14-digit BCD modular multiply-add**:

```
unpack S -> 14 digit bytes (MSD-first d[0..13])
acc := 0 (14 digit bytes)
for each digit A[j] of the constant A (weight 10^(13-j)):
    multiply the 14-digit S by A[j] with a running BCD carry, add into acc
    SHIFTED by A[j]'s weight; DROP every partial-product digit at a place >= 10^14
    (they cannot affect the result mod 1e14 -- this is the "keep low digits" rule)
acc := acc + C  (14-digit BCD ripple-carry add, carry out of the top dropped)
```

This is `rnd_advance_bcd` in the sim (little-endian there; the asm is MSD-first — same math),
asserted equal to `(A·S+C) mod 1e14` over the 19 anchors **and 20 000 swept states**. `A`
(`21132486540519`) and `C` (`14389820420821`) are page-1 constants living beside the tenant;
`S₀` (`40649651372358`) is a main-side constant in `clear.asm`. A mis-transcribed digit is
caught **immediately** by the differential gate (the sequence diverges on step 1).

### 15.3 Placement, RAM, dispatch

- **Page-1 tenant** `fp_rnd` (`sub/fp_rnd.asm`), the 9th, appended to `sub_p1_table` after
  `fp_tan`: `jp fp_rnd` at **`SUBROM_IDX_RND = 9`**. Self-contained: needs only RAM
  (RND_SEED/FAC/ARGA + transient scratch) + its own page-1 `A`/`C` constants; the resident-ABI
  surface it touches is a **subset** (`dig15_iszero`, `arga_pack_fac`) — **no new page-0
  relocation**, closure-check clean.
- **Token** `RND = $88` ($FF-prefixed, §1.4 / memory).
- **`RND_SEED`** — the persistent 14-digit state. RAM below `DRVA_DPB $F195` is **exhausted**
  (§11.6), and the seed must survive arbitrary statements between calls (so it cannot reuse
  transient math scratch). It is stored **packed BCD, 7 bytes** (two digits/byte, MSD-first)
  in the **tail slack of the `SUB_INT_RAM` trampoline reservation**: the trampoline template
  is a fixed ~47-byte position-independent stub but its reservation runs to `$F149` (64 B),
  so `RND_SEED equ $F142` (7 B, → `$F148`) sits in the unused tail. **Safe-by-construction:**
  `fp_rnd.asm`/`subromcall.asm` carries a build-time
  `ASSERT sub_int_template_end - sub_int_template <= RND_SEED - SUB_INT_RAM`
  (currently 47 ≤ 56) so any future trampoline growth that would collide **fails the build**
  loudly rather than silently overlapping. (The disk-area `$F2B8–$F33F` gap was rejected — it
  is MSX-DOS work-area, semantically reserved even where un-`equ`'d, and cross-component.)
  `IF ROM_BASE < $4000` — repack-only, like every math sysvar; the lean build has no RND.
- **`clear_vars`** (basic/clear.asm) gains a 7-byte copy `RND_SEED := packed(S₀)` at the same
  point it resets DEFTBL to all-8 (`IF ROM_BASE < $4000`).

### 15.4 `evmc_rnd` stub + `fp_rnd` tenant

- **`evmc_rnd`** (basic/expr.asm) = the **`evmc_atn` shape** (total function, NO domain
  check): `ev_mc_arg` → `widen_rhs_operand` into ARGA → `push ix` / dispatch
  `SUBROM_ENTRY_BASE_P1 + 3·SUBROM_IDX_RND` / `pop ix` → `jp c,subrom_absent_error` →
  `ld a,8 / ld (FACTYP),a` → `jp flt_to_int16` tail. Selector added to `ev_ff_mathconv`.
- **`fp_rnd`** (page-1, COMPUTE-ONLY — leaves FAC correct, does NOT touch FACTYP/DE, exactly
  like fp_atan/fp_sin) receives **ARGA = the widened argument**:
  1. `dig15_iszero(ARGA+FPNUM_DIG)` → **zero** ⇒ `RND(0)` path: skip the advance, go to
     step 3 with the *current* RND_SEED.
  2. else `ld a,(ARGA+FPNUM_SIGN)`: **negative** ($80) ⇒ reseed — the advance input `S`
     is `mant14` = ARGA's 14 digit slots read as a 14-digit integer (`dexp`/sign ignored);
     **positive** ⇒ the advance input `S` is the current RND_SEED (unpacked). Run
     `rnd_advance` (§15.2), store the result back to RND_SEED (packed).
  3. **Output**: normalize the 14-digit state to a FAC double = `S·10⁻¹⁴`. Left-shift out
     leading zeros: if the state has `k` leading zeros, mantissa = digits `d[k..13]`
     left-justified (pad low with 0), `dexp := -k`, sign := 0, guard := 0 → `arga_pack_fac`
     → FAC (value `= d[k].d[k+1]…×10^(−1−k)`). Guard S=0 (all-zero) with `dig15_iszero` →
     `FAC:=0` directly (the `arga_pack_fac` not-all-zero precondition, the recurring 2c/2d
     class); S=0 is astronomically rare but valid.

### 15.5 Gate (extend `basic_probe_math_conv.py` / `math-acceptance`)

- **Token capture** row for `RND $88` (§1.4 pattern).
- **Reference-IDENTITY differential** (not a truth-bound — the whole point of RND): assert
  zerobas reproduces the reference sequence **bit-for-bit** on: (a) the cold sequence from
  power-on (`NEW`-reset), (b) `RND(-k)` reseed for the characterization battery (incl. the
  `-1`/`-0.001`/`-1E9` collision and the single-vs-double `1/3` pair), (c) a long
  `RND(1)` run, (d) `RND(0)` repeat, (e) positive-arg-ignored (`RND(7)`≡`RND(1)` from a
  common seed), (f) `NEW`/`CLEAR`/`RUN` reset to S₀ and `CLS` non-reset. The captured
  anchors already live in the sim (`RND_COLD`/`RND_AFTER_M1`/`RND_RESEED`); the gate captures
  the same on both machines and asserts equality.
- **FACTYP discipline** (standing trap, bit twice): `RND` over a typed store, `RND` of a
  `PEEK`, `A#=RND(1)` then re-read — assert double, no FACTYP leak.
- Standing gates stay green: `unit-test`, `subrom-closure-check`, `subrom-inttest` (the
  trampoline still fits below RND_SEED — the new build ASSERT guards it), `float`/`string`/
  `input`-acceptance, **lean byte-identical**, reloc, kwtable single-copy.
- **Fable adversarial review** after (every slice hid ≥1 matrix-invisible bug).

### 15.6 Notes / deferrals

- `RANDOMIZE` — out of scope (reference rejects it, §15.1); a potential separate statement
  follow-up.
- The reset-on-`RUN`/`NEW`/`CLEAR` (to a *fixed* S₀) means the default sequence is
  deterministic per program run unless the program itself reseeds with `RND(-x)` — a
  reproducibility feature, reference-identical.
- `RND` is the **faithful-core-model win** flagged in §14.10: its sim model (`rnd_advance_bcd`)
  is an EXACT bit-for-bit oracle, not a bounds envelope — the first slice-2 function where the
  sim proves reference-identity outright.
