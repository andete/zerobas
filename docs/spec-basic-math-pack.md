<!-- Provenance: original work (own-design spec over our own float core + the ratified sub-ROM ABI). Function-token values and per-function numeric behaviour are oracle-locked to published tables (MSX2 TH Table 2.20 / MSX Assembly Page) + black-box VG-8020 capture — never ROM disassembly (see PROVENANCE.md, [[no-reference-rom-disasm]]). -->
# Spec — BASIC math pack (transcendental + algebraic functions)

**Status: 🟢 SCOPE SIGNED OFF + CHARACTERIZED (2026-07-12).** Placement settled +
grounded (§2–§3); slice-1 home = **main BASIC in-window** (user-ratified — the
functions are thin wrappers over resident page-0 primitives, no heavy body to evict;
~1022 B free in page 1; the sub-ROM page-1 tenant is built when slice-2's
transcendentals need it). **`SQR`/`^` black-box characterization DONE** (§5.1):
`SQR` is **standalone algebraic** (Newton-style, exact on perfect squares, NOT
exp/log) → **moves INTO slice 1**; `^` is **dual-path** (integer exponent =
repeated-multiply; fractional exponent = bit-exact `EXP(y·LOG(x))`) → **stays slice
2** (needs EXP/LOG). RND → slice 2. Refined slice-1 (§4):
- **Slice 1a** (this cut): `ABS SGN INT FIX CINT CSNG CDBL` — trivial wrappers.
- **Slice 1b**: `SQR` — algebraic, but needs bit-exact fitting to the oracle's
  rounding (a distinct effort); its own sub-slice after 1a.

Slice spec for the sub-ROM arc ([spec-basic-subrom.md](spec-basic-subrom.md)); the
first **page-1** tenant of `zerobas-sub`. Builds on the float core
([spec-basic-float-core.md](spec-basic-float-core.md), F1+F2+F3 concluded) and the
sub-ROM ABI ([spec-basic-subrom-wave2-tokeniser.md](spec-basic-subrom-wave2-tokeniser.md)).

---

## 1. Scope

The math pack is the set of BASIC intrinsic math functions not yet implemented
(verified greenfield 2026-07-12 — no keywords, tokens, or bodies exist):

`SQR SIN COS TAN ATN EXP LOG` (transcendental) · `^` (exponentiation operator) ·
`ABS SGN INT FIX` · `CINT CSNG CDBL` (type conversion) · `RND` (pseudo-random).

Estimated 2.5–4 KB total ([decision-phase3-space-strategy.md](decision-phase3-space-strategy.md) §94).
This doc covers **placement (final)** + the **slice-1 cut**. Slice 2 (the
coefficient-heavy transcendentals) gets its own spec once slice 1 lands.

---

## 2. Placement — final: **slot 3-2 (zerobas-sub), PAGE 1**

The slot map is fixed (`3-0 RAM / 3-1 disk / 3-2 sub / 3-3 empty`), so "which slot"
is not open: the pack is a tenant of the existing sub-ROM in **3-2**. The decision is
**which page of the sub-ROM**, and it is forced by one hard constraint.

### 2.1 Decisive constraint — the FAC arithmetic surface is slot-0 page 0

A CALSLT switches **only the called page** into 3-2; the other page stays slot-0.

| Tenant page | Page 0 during the call | Page 1 during the call |
|---|---|---|
| **page-0 tenant** | sub-ROM — BIOS + BCD core **paged OUT** | main BASIC (visible) |
| **page-1 tenant** | slot-0 — BIOS + BCD core **visible** | sub-ROM — main BASIC paged out |

Every routine the pack computes on lives in slot-0 **page 0** (all below
`__MEAS_LOW_END`=$3BA8, verified in [build/basic-reloc.sym](../build/basic-reloc.sym)):

- BCD core: `fp_add`=$3469 · `fp_mul`=$3547 · `fp_div`=$3632 · `fp_cmp`=$36D7
- F2 operator/convert/widen layer: `combine_add`=$3979 · `domain_convert_core`=$3766 ·
  `fac_to_int_addr`=$37DE · `widen_fac_to`=$3808 · `mul16x16_32`=$3925

A **page-0** tenant would page all of that out and have nothing to compute with. A
**page-1** tenant keeps it mapped. → **page 1.** (This corrects an earlier
"page-0 native tenant" note in the arc memory; the interrupt trampoline made page-0
EI-capable, but EI-capability was never the blocker — BCD-core visibility is.)

### 2.2 Independent second reason — long compute wants EI natively

Transcendentals iterate many BCD mul/add steps. A page-1 tenant sees the BIOS and
`$0038` natively and **may EI** (S1 spec reserved page 1 for exactly "BIOS-heavy
bodies that may EI") — no long DI span, and no dependence on the page-0 interrupt
trampoline. The page-1 island is currently empty ([sub/sub.asm](../sub/sub.asm)
`$4010` table holds only the ping), so the pack is the **first real page-1 tenant**,
appended at index 1+.

### 2.3 Physical home

The pack's bodies live in the sub-ROM **page-1 island** ($4000–$7FFF of `sub.rom`),
which is empty within the 32 KB image — 16 KB of headroom for a 2.5–4 KB pack.
Main-side keyword-dispatch stubs live in main BASIC and are `IF ROM_BASE < $4000`
(repack-only), so the lean 16 KB cart stays byte-identical.

---

## 3. ABI — page-1 tenant contract

Inherits the sub-ROM dispatch mechanism (append-only `$4010` jp-table, `subrom_call`
in page-0-resident [basic/subromcall.asm](../basic/subromcall.asm) — issuing a page-1
CALSLT is self-paging-safe because the caller is in page 0).

1. **Entry.** Each function = one `$4010`-table index (append after the ping). The
   main-side stub parses its argument(s), leaves the operand in **FAC** (RAM,
   always mapped through any page switch), sets up any int/aux arg, then `subrom_call`.
2. **Compute.** The tenant runs with page 0 = BIOS + BCD core, page 1 = itself. It may
   `EI`. It calls the page-0 `fp_*` / widen / convert routines directly (same absolute
   addresses — page 0 is mapped).
3. **Result.** Returned in FAC (double, per §10 of the float core: all float arith is
   DOUBLE; single is storage-only). `FACTYP` set per the function's result type.
4. **Errors return a disposition — never `jp`.** `err_fp_divzero`=$425A and the
   "Illegal function call" path live in main-BASIC **page 1**, switched out during the
   call. The tenant returns a status code in `A` (0=ok, nonzero=error class); the
   main-side stub maps it to the real error raise. Domain errors (§4) use this path:
   `SQR` of a negative, `LOG` of ≤0, etc.
5. **No main-BASIC-page-1 dependency.** A leaf-audit (per-slice pre-gate, per the
   wave-1 lesson) must confirm every tenant body touches only page-0-resident routines
   + RAM. Anything page-1-resident must be page-0-relocated, duplicated sub-side, or
   avoided. (The §2.1 audit shows the arithmetic surface is already page-0; the audit
   re-runs per function to catch hidden reverse-deps — the recurring `neg_de`-class trap.)

---

## 4. Slice-1 candidate set + oracle contract

All are `$FF`-prefixed two-byte function tokens (like PEEK/VAL), **except `^`** which is
a single-byte binary **operator** token. Token values are oracle targets to be pinned
(§6). Behaviour below is the *intended* contract, to be confirmed byte/reference-exact
against the VG-8020 oracle before/at implementation.

### 4.1 Type-conversion + sign + integer functions (coefficient-free, oracle-direct)

These the oracle computes directly (no polynomial/exp-log dependence), so a clean-room
algebraic implementation can be reference-identical. **This is the safe slice-1 core.**

| Fn | Token (target) | Contract |
|---|---|---|
| `ABS(x)` | `$FF $86` | \|x\|; preserves precision/type of x; `ABS(-32768%)` → int-domain per §10 float core |
| `SGN(x)` | `$FF $84` | −1 / 0 / +1 as **integer** (`FACTYP`=int) |
| `INT(x)` | `$FF $85` | floor toward −∞ (`INT(-1.5)`=−2); returns float type of x |
| `FIX(x)` | `$FF $A1` | truncate toward 0 (`FIX(-1.5)`=−1); returns float type of x |
| `CINT(x)` | `$FF $9E` | → integer, **rounds** (half-up per float core §10); domain −32768..32767, else Overflow (disposition) |
| `CSNG(x)` | `$FF $9F` | → single (narrowing round of a double) |
| `CDBL(x)` | `$FF $A0` | → double (widen) |

`INT`/`FIX`/`CINT` reuse the F2 `domain_convert_core` / `fac_to_int_*` layer (page 0);
`CSNG`/`CDBL` reuse the F3 widen/narrow layer. Low implementation risk — mostly thin
wrappers over existing page-0 primitives, which is why they anchor slice 1.

### 4.2 `RND` — pseudo-random (own sub-slice)

`RND(x)` — `$FF $88`. MSX semantics: `x>0` next in sequence, `x=0` repeat last, `x<0`
reseed. The generator is a fixed LCG over a RAM seed cell. **Reproducing the exact
sequence needs the LCG constants**, which are black-box observable (capture the
sequence from the VG-8020, fit the recurrence) — admissible, no disasm. Bit-exact
fitting is nontrivial → treat as its own sub-slice (1c) gated on a capture campaign.
May slip to slice 2 if the fit is not clean.

### 4.3 `SQR` — slice **1b** (own sub-slice, after 1a)

`SQR(x)` `$FF $87`. Characterization (§5.1) proved it is **standalone algebraic**, NOT
exp/log — exact on perfect squares, near-correctly-rounded (Newton-style). So it is
reference-identical-able without EXP/LOG and belongs in slice 1. But matching the
oracle's exact rounding (it is 1 ulp low on `SQR(2)`/`SQR(3)`, correctly rounded on
5/7/10) is a real fitting task distinct from the trivial 1a wrappers — hence its own
sub-slice. Domain error `SQR(<0)` → "Illegal function call" via the §3.4 disposition.

### 4.4 `^` — slice **2** (dual-path, fractional = EXP·LOG)

`^` operator `$F5` (highest binary precedence, above unary minus: `-2^2` = −4).
Characterization (§5.1): integer-valued exponent → exact repeated-multiply (no
exp/log, verified to `2^40`); **non-integer exponent → bit-for-bit `EXP(y·LOG(x))`**.
Because the fractional path *is* the oracle's exp/log, full reference-identity requires
slice-2's EXP/LOG → `^` is slice 2 (avoids an interim integer-only path that slice 2
would replace).

---

## 5. Open questions for sign-off

**RESOLUTION (user, 2026-07-12):** Q-M1 → characterize first (§5.1 DONE) — outcome
**revised the assumption**: `SQR` is algebraic → slice 1 (as 1b); `^` fractional path
is exp/log → slice 2. Q-M2 → **defer RND** to slice 2. Q-M3 → default accepted
(published-table + black-box capture, no disasm — same method as the string engine).

### 5.1 `SQR`/`^` characterization result (black-box VG-8020, 2026-07-12)

Battery captured full-precision PRINT output and compared against constructed
`EXP(y·LOG(x))`:
- **`SQR` = standalone algebraic.** Exact on every perfect square (`SQR(16)`=4,
  `SQR(100)`=10) while `EXP(.5·LOG(16))`=3.9999999999995; bit-differs from the exp/log
  construction on 5/5 non-square samples; more accurate than exp/log (5/7/10 correctly
  rounded, 2/3 one ulp low) → a Newton-style iteration, no exp/log dependency.
- **`^` = dual-path.** Integer-valued exponent (any literal type, incl. negative base
  `(-2)^3`=−8 and negative exponent `2^-3`=.125, exact to `2^40`/`3^20`) → dedicated
  repeated-multiply. Non-integer exponent → **bit-for-bit `EXP(y·LOG(x))`** in all 5
  tested cases (incl. `^.5`, which is NOT routed through `SQR`: `16^.5`=3.9999999999995
  vs `SQR(16)`=4); negative-base-fractional errors exactly as `LOG(neg)` would.

**Q-M1 (original, now resolved by §5.1).** Characterize black-box how

**Q-M1 (the slicing fork — must resolve before coding).** Characterize black-box how
the VG-8020 oracle computes `SQR` and `^`:
- Capture `SQR(2)`, `SQR(2)*SQR(2)`, `2^0.5`, `2^3`, `2^3-8`, `10^2-100`, etc.,
  full-precision, and compare last-digit behaviour against an exp/log-derived model vs
  a standalone-algebraic model.
- **(a)** If oracle = exp/log-derived → **move `SQR` + `^` to slice 2** (with EXP/LOG).
  Slice 1 = §4.1 (+ §4.2 RND). *(leaning — matches MS-BASIC lineage; keeps slice 1
  purely reference-identical with zero interim seams.)*
- **(b)** If oracle has a standalone algebraic `SQR`/integer-`^` → keep them in slice 1,
  reimplement clean-room to match.
- **(c)** Ship slice-1 `SQR`/`^` now via Newton/repeated-multiply as a **documented
  interim divergence** (last-digit only), unified onto the oracle path in slice 2.
  *(only if the user wants `^`/`SQR` usable earlier and accepts a temporary non-identity,
  like F1's interim seams — but this spends effort on a path slice 2 replaces.)*

**Q-M2.** RND (§4.2): commit to the black-box LCG-fit sub-slice now (1c), or defer RND
to slice 2 and ship slice 1 as pure conversion/sign/int functions only?

**Q-M3.** Token pinning provenance (§6): confirm the "MSX2 TH Table 2.20 + black-box
VG-8020 capture, no disasm" method is the ratified source for the new function tokens
(same as the string-engine slice did).

---

## 6. Token pinning (to be captured, not asserted)

New function tokens to add to [basic/sysvars.inc](../basic/sysvars.inc) and
[basic/kwtable.inc](../basic/kwtable.inc), sourced from published tables (MSX2 TH
Table 2.20 / MSX Assembly Page) **and** black-box VG-8020 crunch capture (new probe,
mirroring `basic_probe_str_tokens.py`) — cross-checked, never disassembled. Expected
values (published-table targets, to confirm by capture): `SGN $84`, `INT $85`,
`ABS $86`, `SQR $87`, `RND $88`, `SIN $89`, `LOG $8A`, `EXP $8B`, `COS $8C`, `TAN $8D`,
`ATN $8E`, `CINT $9E`, `CSNG $9F`, `CDBL $A0`, `FIX $A1` (all `$FF`-prefixed);
operator `^` = `$F5`. These interleave cleanly with the already-pinned block
(LEN $92 … PEEK $97, HEX$ $9B …) confirming the contiguous-table assumption.

---

## 7. Gates (per slice)

- New `basic_probe_math_*` differential(s) vs VG-8020 oracle (batched via `omsx_repl`,
  per the acceptance-harness rework) → a `make math-acceptance` gate.
- Token capture probe (crunch byte-identity for each new keyword).
- Leaf-audit (§3.5) as a named pre-gate each slice.
- Standing gates stay green: `unit-test`, `float-acceptance`, `string-acceptance`,
  `input-acceptance`, `subrom-acceptance`, `subrom-inttest`, `diskbasic-repack`,
  kwtable single-copy, lean byte-identical, reloc.
- Fable review of every slice (the float pack's standing lesson: every slice hid ≥1
  matrix-invisible bug; the differential + review together, not the passing matrix).

---

## 9. Slice-1a implementation contract (the target for this cut)

Home: **main BASIC, repack-only** (`IF ROM_BASE < $4000`); lean 16 KB ROM stays
byte-identical. Function bodies in page 1; the one new numeric primitive in the page-0
low region alongside the other `fp_*` (it is a shared leaf).

### 9.1 Functions, exact semantics, result type

| Fn | Token (capture, target) | Semantics | Result |
|---|---|---|---|
| `ABS(x)` | `$FF $86` | clear FAC sign | same FACTYP as x |
| `SGN(x)` | `$FF $84` | −1 / 0 / +1 from FAC sign+zero | **int** (FACTYP=2, DE) |
| `INT(x)` | `$FF $85` | **floor toward −∞** (`INT(-1.5)`=−2), **float→float full range** (`INT(1E9)`=1E9) | same FACTYP as x |
| `FIX(x)` | `$FF $A1` | **truncate toward 0** (`FIX(-1.5)`=−1), float→float full range | same FACTYP as x |
| `CINT(x)` | `$FF $9E` | **truncate toward 0** to int16 (oracle-CONFIRMED 2026-07-12: CINT does NOT round — `cint(2.9)`=2, `cint(3.7)`=3, `cint(32767.6)`=32767 in range; identical to the strict `\`/MOD int16 domain, float-core §10.3); Overflow only when the **integer part** exceeds ±domain | **int** (FACTYP=2, DE) |
| `CSNG(x)` | `$FF $9F` | narrow to single (round) | **single** (FACTYP=4) |
| `CDBL(x)` | `$FF $A0` | widen to double | **double** (FACTYP=8) |

`INT`/`FIX` differ **only** for negative non-integers (`INT`=`FIX`−1 there; identical for
x≥0 or integral x). Exact per-case behaviour is oracle-locked by the gate (§9.4), not
asserted from memory — capture and match.

### 9.2 New primitive

`fp_trunc` (float→float integer part, truncate toward 0): zero the BCD fractional digits
of FAC below the decimal point, preserving lead byte / exponent / full range; built on the
existing `dig15_*` helpers. Page-0 low region with the other `fp_*`. `INT` = `fp_trunc`
then, if x<0 and a fraction was dropped, subtract 1 (via `fp_sub` of a 1); `FIX` = `fp_trunc`.
`CINT` = the F2 strict int16 domain conversion directly (`fac_to_int_strict_reset`) —
truncating, NOT rounding (oracle-confirmed; the earlier "half-up" text was an unverified
assumption, corrected 2026-07-12); Overflow via that path's disposition. `CSNG`/`CDBL` reuse the F3 narrow/`widen_fac_to`
layer. Audit each for hidden page-1 reverse-deps before finalizing.

### 9.3 Dispatch integration

- **Tokens:** add the seven `$FF`-suffix equates to [basic/sysvars.inc](../basic/sysvars.inc)
  (repack block), crunch entries to [basic/kwtable.inc](../basic/kwtable.inc) (repack-only,
  like the string-engine tokens). Values **captured** by a new crunch probe (targets above),
  cross-checked vs MSX2 TH Table 2.20 — no disasm.
- **Evaluator:** extend `ev_f_ff` ([basic/expr.asm:601](../basic/expr.asm:601)) with a new
  **numeric-math group**: recognize the seven selectors, parse `( <numeric expr> )`
  leaving the arg in FAC/FACTYP (as a float factor is evaluated in the repack build), apply
  the function, set the result FACTYP + DE. This is a new arg path distinct from `ev_ff_arg`
  (RAM/port→int) and `ev_ff_strnum` (string→number).
- **FACTYP discipline (float-pack standing trap):** every int-returning tail (`SGN`, `CINT`)
  must set FACTYP=2 + DE correctly; every float-returning tail must leave FAC+FACTYP
  consistent. The sticky-FACTYP leak (F1/F2) bit twice — cover function-over-float cases.

### 9.4 Gate

New `probes/basic/basic_probe_math_conv.py` differential vs VG-8020, batched via
`omsx_repl` → `make math-acceptance`. Battery MUST include the traps that hid bugs in the
float pack (matrix-invisible unless explicitly cased), with false-EXPECTED entries:
- `INT` vs `FIX` on negatives (`INT(-1.5)`=−2, `FIX(-1.5)`=−1, `INT(-1)`=`FIX(-1)`=−1,
  `INT(1.9)`=1), full-range (`INT(1E9)`, `FIX(-1E9)`, `INT(123456.789)`).
- `CINT` rounding + domain edges (`CINT(2.5)`, `CINT(-2.5)`, `CINT(32767.4)`,
  `CINT(32767.6)`→Overflow, `CINT(-32768.4)`, `CINT(-32768.6)`→Overflow) — capture the
  half-up direction, don't assume.
- Type preservation / FACTYP-leak: `PRINT SGN(2.5)`, `PRINT SGN(2.5)+0.5`, `PRINT INT(2.5)`,
  `PRINT CSNG(1.2345678#)`, `PRINT CDBL(1.5!)`, `A%=CINT(3.7)`, function-over-`PEEK`.
- `ABS(-1.5)`, `ABS` of a double, `ABS(-32768%)` (int-overflow edge — capture the oracle).
Plus a crunch-byte-identity check for each new keyword. Fable review of the whole slice.

### 9.5 Review outcome (2026-07-12) — slice 1a SHIPPED

Implemented (Sonnet) + adversarially reviewed (Fable) + triaged. `make math-acceptance`
green (7/7 tokens + 89/89 values incl. the added type-preservation cases); all standing
gates green; lean `basic.rom` byte-identical. Three review findings, all resolved
**without a ROM change** (implementation was correct):
- **F1 — spaced `DEF INT A-C` now errors.** NOT a regression: the VG-8020 oracle
  rejects the spaced form ("Syntax error"); pre-slice zerobas wrongly *accepted* it, so
  slice-1a **converged to the oracle**. (Only contiguous `DEFINT A-C` is valid, as before.)
- **F2 — gate blindness to INT/FIX result type.** The double `sub1` branch and single
  re-narrow were untested by the battery. Verified our build matches the oracle on
  type-revealing doubles (`int(12345678.9#)`=12345678, `int(-9999999.5#)`=−10000000, …)
  and **added those cases** — the logic is now proven, not trusted.
- **F3 — unclosed-paren leniency** (`CINT(2` prints `0`; `CINT(40000` reports "overflow")
  where the oracle says "Syntax error". This is the **pre-existing evaluator-wide
  lenient-unbalanced-paren residue** ([[float-pack-arc]]): `PRINT PEEK(40000` (existing)
  likewise prints `40000`, not a syntax error. The math functions inherit it consistently.
  A real fix is evaluator-wide (all `$FF` functions + parens), NOT math-only — **deferred**
  as its own decision; fixing math-only would make it inconsistent with PEEK.

## 10. Slice-1b implementation contract — `SQR` (DRAFT, awaiting sign-off)

**Status: 🟠 DRAFT 2026-07-13 — spec input, NOT a green light** (per
[[spec-before-implementation]]). Slice 1a shipped `ABS/SGN/INT/FIX/CINT/CSNG/CDBL`
(§9.5). This cut adds the one remaining slice-1 algebraic function, `SQR`. It is
*not* a trivial wrapper — §5.1 proved the oracle's `SQR` is a **standalone
Newton-style algebraic** routine (not `EXP(.5·LOG(x))`), so it is
reference-identical-able in slice 1, but matching its **exact last-ulp behaviour**
is a distinct fitting task, hence its own sub-slice.

### 10.1 Home + token

- **Home: main BASIC, repack-only** (`IF ROM_BASE < $4000`), exactly like 1a — the
  body is a short algebraic loop over resident page-0 `fp_*` primitives, no heavy
  coefficient tables, so it stays in-window; lean 16 KB `basic.rom` **byte-identical**
  (SHA1-proven). No sub-ROM page-1 tenant yet (that is slice 2's transcendentals).
- **Token: `SQR` = `$FF $87`** (§6 target, MSX2 TH Table 2.20). **Captured, not
  asserted** — add `SQR_TOKEN` to [basic/sysvars.inc](../basic/sysvars.inc) (repack
  block) + crunch entry to [basic/kwtable.inc](../basic/kwtable.inc), confirmed by the
  gate's token-capture check against the real VG-8020 crunch (interleaves cleanly:
  `ABS $86 · SQR $87 · RND $88`).

### 10.2 Result contract (oracle-locked by the gate, not asserted from memory)

| Fn | Token | Semantics | Result |
|---|---|---|---|
| `SQR(x)` | `$FF $87` | non-negative square root; **DOUBLE** compute per float-core §10 (all float arith is double); exact on perfect squares | **double** (FACTYP=8) unless the oracle narrows for single input — capture and match |
| `SQR(x<0)` | — | domain error → **"Illegal function call"** via the §3.4 disposition path (never `jp`; return status, main-side stub raises) |

Edge inputs the battery must pin: `SQR(0)`=0, `SQR(1)`=1, perfect squares
(`SQR(4)`/`SQR(16)`/`SQR(100)`/`SQR(10000)` all exact), the known one-ulp-low cases
(`SQR(2)`, `SQR(3)`), correctly-rounded cases (`SQR(5)`, `SQR(7)`, `SQR(10)`),
sub-1 (`SQR(.25)`=.5, `SQR(.01)`=.1), large (`SQR(1E10)`, `SQR(1E30)`), FACTYP-leak
(`PRINT SQR(4)+0.5`, `A%=SQR(9)`, `SQR` of a single vs a double literal), and the
negative-domain error (`SQR(-1)`, `SQR(-1E-9)`).

### 10.3 RESOLVED (user, 2026-07-13) — full bug-for-bug compatibility, no accuracy flag

The characterization campaign (this session, continuing §5.1) found the oracle's
`SQR` anomaly does **not** originate in the sqrt algorithm: `SQR` is exactly
**Heron fixed-point under the oracle's own arithmetic** (verified 72/72), and the
one-ulp-low pattern comes from the **reference's DIVISION** being biased low by
0–3+ ulp in an operand-dependent way. Our `fp_div` is correctly-rounded
(mathematically *more* accurate) → Heron lands a different last ulp on ~15/72 inputs,
so bit-exact `SQR` is **impossible over our current div**. This is a **live divergence
today, independent of SQR** (`PRINT 2/1.4142135623731` → oracle `…729`, zerobas
`…731`), which means the float pack's "reference-identical" claim was silently
**falsified for division** — `float-acceptance` (349/349) has a blind spot: its matrix
never included near-unity 14-digit divisions.

**Decision:** **compatibility is the product's ultimate goal** — a divergent result can
make real programs branch differently — so **`fp_div` is reworked to reproduce the
reference's low-biased rounding exactly** (a float-core change). **No compile-time
accuracy option:** a `strict-vs-accurate` flag was considered and **rejected** — a
reference-identity project has no consumer for an "accuracy" build, and a live second
branch would double the affected gate surface and cost scarce lean-cart bytes. Once the
div is compat, **`SQR` = plain Heron over it → reference-identical automatically** (no
per-function divergence table). §10.4's `fp_sqrt` therefore simplifies to the iterate
loop with no special rounding of its own.

**Blocking prerequisite:** reverse-engineer the reference division micro-rule *exactly*
(campaign at 76/104 → close via active disagreement-probing). The `fp_div` bug-compat
rework then gets **its own spec + sign-off** before any [float-arith.asm](../basic/float-arith.asm)
edit (it reopens the concluded float pack), and **closes the `float-acceptance` blind
spot** by adding the near-unity 14-digit-division cases.

### 10.3.1 FINAL (user, 2026-07-13, post-campaign) — documented deviation; ship SQR correctly-rounded

The "rework fp_div bug-compatible" plan in §10.3 was **attempted and abandoned**. A
time-boxed reverse-engineering campaign (two spans, error-map fitting vs
adversarial + fresh held-out sets, full family sweep: Knuth Alg-D estimate ×
trial-subtraction × divisor-rounding × remainder-width × guard-count) **plateaued at
~80% (fresh) / ±1 ulp** and could not reach bit-exact. The reference division's
distinguishing per-digit rule lives in the **15th digit of intermediate remainders**,
which its 14-digit `PRINT` structurally hides; recovering it requires reading the ROM's
internal state or code — both barred by [[no-reference-rom-disasm]]. **Conclusion: the
reference's division rounding is not clean-room black-box reproducible.** This is the
honest boundary of black-box reproduction, not an unexplored-model gap.

**Decision (documented deviation):**
- **Keep zerobas's correctly-rounded `fp_div`** (it is *more* accurate). Do **not** rework
  it. The div deviation envelope is **narrow**: identical to the reference for divisors
  with ≤10 significant digits; ≤~5 ulp more accurate (in the 14th digit) beyond.
- **`SQR` ships correctly-rounded** — Heron over our `fp_div` + a final correction step
  (§10.4) so the result is the **true correctly-rounded 14-digit √x** (except a rare,
  fundamental near-tie **precision floor**, §10.4 — only observed `SQR(99.99998)`, where
  the reference ties us), and it is **always ≥ as accurate as the reference** (verified
  ~1180 adversarial near-ties, 0 where zerobas is worse). It is **not** reference-identical; the gate's oracle is
  **mathematical truth** (host `Decimal`), and it carries a **documented table** of the
  ~15/72 inputs where the **reference ROM** is 1 ulp off truth (zerobas is correct there —
  see [[bug-for-bug-compat-over-accuracy]]). *(A plain Heron fixed-point was tried first
  and rejected: it is ±1 ulp off truth, sometimes LESS accurate than the reference —
  `SQR(14)` 1 ulp high — which defeats the "at least as accurate" rationale.)*
- **Document the division + SQR deviation envelope** in the float-pack record and add the
  exposing near-unity 14-digit-division cases to `float-acceptance` **as characterized
  known-deviations** (closes the blind spot without asserting a false identity).
- **Principle intact:** bug-for-bug is still the goal *where clean-room-achievable*. The
  **subtraction** guard-tie divergence IS achievable and is fixed bug-compat
  ([spec-float-subtract-tie-compat.md](spec-float-subtract-tie-compat.md)); division is
  the one place clean-room reproduction is provably capped.

The original fork framing is retained below for provenance.

### 10.3-orig THE open decision — bit-exact fit vs documented divergence (superseded by 10.3)

§5.1 characterized *what* the oracle computes (standalone algebraic, exact on
squares, 5/7/10 correctly rounded, 2/3 one ulp low) but **not the exact iteration**
(seed form + iteration count + final rounding/truncation) that reproduces that
specific ulp pattern. Reproducing it clean-room, **without ROM disasm**
([[no-reference-rom-disasm]]), forces a fork — this is slice 1b's Q-M1-analogue:

- **(a) Characterize-then-fit → bit-exact reference-identity** *(recommended, matches
  the float-pack bar).* Run a **black-box campaign first** (mirrors §5.1's method):
  capture `SQR` at full precision over a designed input battery, then fit a decimal
  Newton/Heron recurrence — `y₀` seed (likely exponent-halving + a short mantissa
  approximation), fixed iteration count, and the **final-step rounding mode** — that
  reproduces the exact last digit on *every* sample incl. the 2/3-low anomaly.
  Clean-room reimplement that fitted recurrence. Highest confidence of `float-acceptance`-
  grade identity; cost = the fit campaign may take a few capture/model rounds.
- **(b) Correctly-rounded interim divergence** — ship a clean correctly-rounded Newton
  now, **document** the last-ulp divergence on `SQR(2)`/`SQR(3)` (like F1's interim
  seams), unify later. Cheaper, but spends effort on a path a later fit replaces and
  breaks the "reference-identical slice 1" property.
- **(c) Defer `SQR` to slice 2** — fold it in alongside EXP/LOG if the fit proves
  intractable. Least attractive (§5.1 already proved it is *not* exp/log, so it gains
  nothing from slice 2's machinery).

**Recommendation: (a).** The whole slice-1 thesis is reference-identity; a
characterize-first campaign is the same discipline that produced §5.1 and every clean
float-pack slice. Do the campaign as an explicit **pre-gate** and only commit the
recurrence once the fit is clean across the full battery.

### 10.4 New primitive — `fp_sqrt`

A single page-0-low leaf beside the other `fp_*` (where `fp_trunc`=$3AF5 landed in 1a),
`IF ROM_BASE < $4000`. **Correctly-rounded Heron over our `fp_div`** (§10.3.1 — NOT a
bit-exact fit of the reference; the reference's div-driven ~15/72 1-ulp-low anomaly is a
documented deviation, §10.6):

1. **Domain/trivial guard:** x<0 → return error status (A≠0). x=0 → FAC:=0, done.
   x=1 → FAC:=1 (avoid iterating).
2. **Seed y₀:** `y₀ = x` is correct but slow at exponent extremes; for efficiency
   normalize x to `x'∈[1,100)` by an even-decade shift (rescale the root by `10^k` —
   BCD ops make the map exactly `100^k`-covariant, agent-verified scale-covariant) so
   the iterate needs ≤~9 steps, seed `y₀` from the leading digits of `x'`.
3. **Heron iterate:** `y ← (y + x/y)/2` via resident `fp_div`=$3632, `fp_add`=$3469,
   and a halving (exponent-decrement or `fp_mul`=$3547 by .5). **Stop rule (agent-locked,
   reproduces the reference's own iteration shape): iterate while `y` decreases; return
   the first non-decreasing `y'` (suppress the check on iteration 1, since for x<1 the
   first step rises).** AM-GM guarantees `y₁≥√x`, so the sequence is monotone-decreasing
   to the fixed point.
4. **Final correction → correctly-rounded (REVISED 2026-07-13).** A plain Heron
   fixed-point is NOT correctly-rounded — it carries a ±1-ulp double-rounding error
   (verified: `SQR(14)`/`21`/`22`/`3.7` land 1 ulp HIGH, i.e. *less* accurate than the
   reference). Since the whole point of the documented deviation is "zerobas is at least
   as accurate as the reference," `fp_sqrt` MUST return the **true correctly-rounded
   14-digit √x**. After the Heron loop yields a candidate `y` (within 1 ulp), apply a
   final correction — either one Newton step `y ← y + (x − y·y)/(2y)` then round once
   (simplest; `fp_mul`/`fp_sub`/`fp_div`/halve/`fp_add`, all resident), or an explicit
   neighbour-test (`y` vs `y±1ulp`, pick the candidate whose square brackets x). The
   **gate is the arbiter** (§10.6): SQR must equal the host-computed correctly-rounded
   √x across a broad battery; whichever method the implementer picks, if any case is
   off, escalate to the neighbour-test.

   **Precision floor (verified 2026-07-13, IMPLEMENTED via a Dekker 7/7-digit split +
   single decide-step).** A 14+guard-digit method cannot resolve every case: for
   razor-thin near-ties (the true √x within ≈1e-7 ulp of a 14-digit rounding boundary)
   the correction's own rounding floor can't tell which way to round, so SQR lands 1 ulp
   off truth. This is **rare** (adversarial sweep: 1 in ~446 constructed near-ties, 0 in
   737 broad; only observed instance `SQR(99.99998)`→`9.9999990000000`, truth
   `9.9999989999999`) and **fundamental** — closing it needs genuine multi-limb
   extended precision (a much larger effort, same *kind* of clean-room limit as §10.3.1's
   division wall). **Crucially the design goal still holds:** on every floor case the
   reference ROM shares the identical limitation and returns the **same** value, so
   zerobas is **never LESS accurate than the reference** (verified across ~1180
   near-tie-biased inputs, 0 violations). The floor cases are pinned in the gate
   (`SQR_KNOWN_FLOOR`) as known-deviations so they can't silently drift.
5. Leave result in FAC, FACTYP per §10.2. **Never `jp` an error** — return disposition
   in A (§3.4).

Per-function **leaf-audit** (§3.5) still required even though the body is main-side:
confirm `fp_sqrt` touches only page-0-resident `fp_*`/`dig15_*` + RAM (no page-1
reverse-dep — the recurring `neg_de`-class trap).

### 10.5 Dispatch integration

- **Evaluator:** extend the slice-1a **`evmc_` numeric-math group** (`ev_ff_mathconv`,
  [expr.asm:619](basic/expr.asm:619)) with an `SQR_TOKEN` selector → new `evmc_sqr`:
  parse `( <numeric expr> )` leaving the arg in FAC/FACTYP (the existing math-group arg
  path), `call fp_sqrt`, on CF/status≠0 raise "Illegal function call" via the disposition
  map, else set result FACTYP per §10.2. Same shape as `evmc_abs`/`evmc_int`.
- **FACTYP discipline** (float-pack standing trap, bit twice): the returning tail must
  leave FAC + FACTYP consistent for the double/promoted result; cover
  `SQR`-over-float and store-into-typed-var cases in the battery (§10.6).

### 10.6 Gate — extend `math-acceptance`

Extend [basic_probe_math_conv.py](../probes/basic/basic_probe_math_conv.py) (do **not**
fork a new probe — same `omsx_repl` batched differential vs VG-8020, `reset=("NEW","CLS")`):

- **Token capture:** append `("SQR", "a=sqr(1)", 0x87)` to the `TOKENS` table (crunch
  byte-identity vs Table 2.20).
- **Value differential:** the full §10.2 battery — perfect-square exactness (assert
  ==reference), sub-1, large-magnitude, FACTYP-leak `PRINT SQR(4)+0.5` / `A%=SQR(9)`,
  single-vs-double input type (all assert ==reference).
- **Oracle = mathematical truth (REVISED):** SQR is intentionally correctly-rounded, so
  the value battery asserts `SQR(x)` == host-computed **correctly-rounded 14-digit √x**
  (`Decimal`, ≥16 guard digits) over a BROAD battery (the 72 characterization inputs +
  more random draws), NOT == the reference. This is what guarantees "correctly-rounded";
  a narrow battery could miss a Newton-correction boundary miss.
- **DOCUMENTED reference-deviation table (§10.3.1):** separately capture the reference
  ROM's `SQR` on the same inputs and list the ~15/72 where the **reference** ≠ truth
  (it is 1 ulp off; zerobas is correct). This documents the ROM's inaccuracy, not ours;
  the probe prints the summary. Mirrors the `float-acceptance` div blind-spot cases.
- **Domain error:** `SQR(-1)` / `SQR(-1E-9)` assert "Illegal function call" per-machine.
- Standing gates stay green (§7 list); **Fable review of the whole slice** (the float-pack
  standing lesson — every slice hid ≥1 matrix-invisible bug; the differential + review
  together, never the passing matrix alone).

### 10.7 Sign-off — ✅ ALL RESOLVED (2026-07-13)

1. **§10.3 fork** → **§10.3.1 documented deviation** (bit-exact div not black-box
   recoverable; keep our accurate div; ship SQR correctly-rounded Heron + divergence
   table). ✅
2. **Scope** → `SQR` only this cut; `RND`/`^`/transcendentals stay slice 2; the
   evaluator-wide unbalanced-paren fix (§9.5 F3) stays deferred. ✅
3. **Model split** → characterization done Fable-solo; implementation = Sonnet on this
   signed-off spec. ✅
4. **Subtraction** guard-tie bug-compat fix approved separately
   ([spec-float-subtract-tie-compat.md](spec-float-subtract-tie-compat.md)) — lands
   before/independent of SQR.

---

## 8. Sequencing

F3 typed vars concluded (2026-07-12) → this. Slice 1 = §4.1 (+ Q-M2 decision on RND),
with Q-M1 resolving whether `SQR`/`^` join slice 1 or fall to slice 2. Slice 2 =
`SIN COS TAN ATN EXP LOG` (+ `SQR`/`^` if Q-M1→(a)), coefficient sets from admissible
published sources (Cody & Waite, Hart, Abramowitz & Stegun) or own derivation,
re-fitted for the decimal DOUBLE FAC — never the MSX ROM.
