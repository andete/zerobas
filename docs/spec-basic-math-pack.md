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

## 8. Sequencing

F3 typed vars concluded (2026-07-12) → this. Slice 1 = §4.1 (+ Q-M2 decision on RND),
with Q-M1 resolving whether `SQR`/`^` join slice 1 or fall to slice 2. Slice 2 =
`SIN COS TAN ATN EXP LOG` (+ `SQR`/`^` if Q-M1→(a)), coefficient sets from admissible
published sources (Cody & Waite, Hart, Abramowitz & Stegun) or own derivation,
re-fitted for the decimal DOUBLE FAC — never the MSX ROM.
