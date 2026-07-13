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
