# Spec — BASIC math float pack (Phase-3 numeric core arc)

Status: **SIGNED OFF 2026-07-11** (decisions D-A…D-G as recommended).
Companion of the string-engine arc: the same S1 (spec + sign-off) → S2 (oracle +
implement) → S3 (acceptance + close-out) cadence, but this is an **arc of three
slices** (F1/F2/F3 below), each with its own S2/S3 and its own commit-at-gate.

## 1. Goal & scope

Give zerobas real MSX-BASIC numbers: BCD floating point (single + double
precision) alongside the existing 16-bit integers — the "math pack" TODO item
([TODO.md](../TODO.md) "Floating point").

The arc covers, in three slices:

- **F1 — literals + PRINT** (representation, tokeniser, output formatter):
  crunch decimal float literals to the real `$1D` (single, 4 value bytes) /
  `$1F` (double, 8 value bytes) tokens with the reference's classification
  rules — this also finally makes **decimal ≥ 32768** correct (today's
  cruncher wraps it into `$1C`, a documented divergence, `interp.asm
  tk_number`); decimal→BCD conversion; and the full MSX number **output
  formatter** (sign space, trailing space, 6/14 significant digits, trailing
  zero suppression, leading `.`, `E±nn`/`D±nn` scientific forms) so
  `PRINT 1.5`, `PRINT 40000`, `PRINT 1E10`, `PRINT 1.23456789#` print
  reference-identically. No arithmetic yet: a float is parsed, stored, printed.
- **F2 — arithmetic + relationals + type promotion**: `+ - * /` and the six
  relationals over int/single/double operands with MSX promotion rules
  (int op int → int; `/` always float; mixed → wider; int overflow promotes,
  e.g. `32767+1` → single `32768`); unary minus; parenthesised sub-exprs.
  Includes the **signed-integer migration** (D-C below): the existing unsigned
  `/ \ MOD` divergences become MSX-signed in the repack build.
- **F3 — typed numeric variables**: `%` `!` `#` suffixes select distinct typed
  variables; unsuffixed defaults to **double** (MSX default); LET/PRINT/
  expression paths read+write the typed store; assignment coerces per MSX
  (float→int rounds; "Overflow" outside int range).

**Out of scope for the arc** (stay on the TODO, unblocked by this work):
`^`, the transcendental/math functions (`SQR SIN COS … RND FIX CINT CSNG
CDBL`), `DEFINT/DEFSNG/DEFDBL/DEFSTR`, float `PRINT USING` specs, `MKS$ MKD$
CVS CVD`, floats in `VAL`/`STR$`, float `INPUT`/`READ`/`DATA` fields, float
`FOR/NEXT` control variables (D-D), arrays. Each becomes a cheap fast-follow
once the pack exists (they compose over the same conversion/arith routines).

## 2. Existing infrastructure this builds on (verified 2026-07-11)

- **Evaluator** ([expr.asm](../basic/expr.asm)): recursive, cursor in IX,
  value in DE, int16-only. Precedence ladder `ev_xor … ev_f` is complete and
  gate-locked; the string engine already grafted a typed (string) probe onto
  `ev_rel`, so a second type-dispatch point is precedented.
- **Tokeniser** ([interp.asm](../basic/interp.asm) `tk_number`): int forms
  `$11+n / $0F / $1C` are byte-identical vs the VG-8020 (standing crunch
  probe). `.`-led and E/D-suffixed literals are currently NOT number-crunched
  at all; ≥ 32768 wraps (both changed by F1).
- **Output** ([print.asm](../basic/print.asm) `print_number`): signed-16 →
  NUMBUF with the MSX sign-space + trailing-space shape already right; F1
  generalises this into the float formatter (int path stays as the fast case).
- **Store** ([vars.asm](../basic/vars.asm)): 4-byte `[name0][name1][value:2]`
  entries; suffix chars are parsed and *ignored* today (`vnk_suffix`). F3
  makes the suffix part of the key and widens the value cell.
- **Gates**: crunch probe (byte-identical), string-acceptance (6),
  input-acceptance (8), diskbasic-acceptance-repack (34), unit-test (44),
  lean-`basic.rom`-byte-identical. All must stay green after every slice.

## 3. Design

### 3a. Representation — MSX BCD, per the published format

MSX2 Technical Handbook (allowed source, grade B) publishes the Math-Pack
number formats: **int** 2-byte two's complement −32768..32767; **single**
4 bytes = 1 sign/exponent byte (sign bit 7, excess-64 exponent bits 6..0,
whole byte 0 ⇒ value 0) + 6 BCD mantissa digits (3 bytes), mantissa
normalised 0.1 ≤ m < 1; **double** 8 bytes = the same lead byte + 14 BCD
digits (7 bytes). S2 of F1 pins every detail against the oracle (crunched
token bytes ARE the stored representation, so the crunch probe verifies the
encoder for free). All *algorithms* (conversion, arithmetic, formatting) are
own-design — BCD digit loops parameterised by mantissa length, so single and
double share one routine set (D-F).

### 3b. Value model — typed accumulator, int16 fast path (D-B)

The evaluator keeps its `DE = int16` convention as the **fast path**; a new
one-byte type flag (`NUMTYP`, own scratch cell: 2/4/8 like the published
VALTYP convention) plus an 8-byte accumulator **FAC** (own RAM) carry float
values. `ev_f` factors that decode a float token load FAC and set NUMTYP;
binary operators check NUMTYP on each side — int⊗int runs the existing code
untouched, anything wider pushes FAC (8 bytes) on the Z80 stack, evaluates the
other side, promotes the narrower operand, and calls the BCD routine.
Statement consumers (PRINT first, LET in F3) dispatch on NUMTYP exactly like
they already dispatch on the string/number split. The whole pack is
**repack-only** (`IF ROM_BASE < $4000`), same firewall as the string engine;
the lean 16 KB ROM stays byte-identical.

### 3c. Literal classification (F1) — PINNED, see §9

Oracle-pinned 2026-07-11 by `basic_probe_floatlit.py` (VG-8020). Full rule
set + captures in §9.1–§9.2.

### 3d. Output formatter (F1) — PINNED, see §9

Oracle-pinned 2026-07-11 by `basic_probe_float_fmt.py` (VG-8020). Notable:
the reference prints `E` notation for BOTH precisions (no `D` output form),
and the fixed↔E wall is decimal exponent ∈ [-1, 14] for both. Full rules +
captures in §9.3.

## 4. Clean-room / provenance

Formats + workarea *conventions* from MSX2 TH (cited inline at the format
constants); token bytes `$1D`/`$1F` from MSX2 TH Table 2.20 + the crunch
oracle; classification/formatting *behaviour* pinned by our own black-box
probes (notebook finding → distilled into this spec per the doc-deliverable
rule); every algorithm own-design. No ROM disassembly anywhere. New
`PROVENANCE.md` section "Phase 3: math float pack" per slice.

## 5. Space & RAM budget — the binding constraint

Measured 2026-07-11 on the current build: repack window free = **3354 B in
page 0** (`$32E6–$3FFF`) **+ 338 B tail** (`$7EAE–$7FFF`) ≈ **3.7 KB**; the
lean ROM has 0 B (stays untouched). Estimate: F1 ≈ 1.3 KB (conversion +
formatter), F2 ≈ 1.5 KB (BCD add/sub/mul/div + promotion + signed-int
migration), F3 ≈ 0.6 KB → ≈ 3.4 KB total. **Inside the window but tight**;
each slice's S3 re-measures, and the fallback lever is the next repack tranche
(see [cbios-repack-space-analysis.md](cbios-repack-space-analysis.md)) —
NOT squeezing correctness.

RAM: FAC+ARG+NUMTYP ≈ 20 B in the `$E0xx` scratch page (free cells exist).
F3 widens the numeric store to carry a type + full value. **SUPERSEDED by §11
(2026-07-12): the store is VARIABLE-WIDTH** (`[name0][name1][type][value:
2/4/8]`, sized to the resolved type), not the fixed 11 B slot floated here —
user pick, the D-G heap-aligned option; VARSLOTS stays 32 and the string region
need not move as far. See §11 intro + §11.4.

## 6. Decisions (recommendations for sign-off)

- **D-A — arc slicing** F1 literals+PRINT → F2 arithmetic → F3 typed vars,
  each slice its own S2/S3 + commit. Interim seams are documented divergences:
  after F1, floats print but don't compute; after F2, `LET` of a float value
  **TRUNCATES to int16** (resolved by F3; F1's sign-off said "rounds" — the
  §10.3 oracle correction made the interim conversion truncating too).
- **D-B — typed accumulator with int16 fast path** (§3b), not all-through-FAC:
  zero risk to the locked integer surface (addresses, disk verbs, FOR/NEXT).
- **D-C — signed-int migration rides in F2** (repack build only): `/ \ MOD`
  become MSX-signed, int overflow promotes to single, div-by-zero becomes the
  reference behaviour (oracle question) instead of today's `0 + ERRMARK`.
  Retires three long-standing documented divergences.
- **D-D — float `FOR/NEXT` deferred** out of the arc (loop state + NEXT
  arithmetic ride the int16 path unchanged); `FOR I=0 TO 1 STEP .1` stays a
  documented divergence until a fast-follow slice.
- **D-E — unsuffixed numeric variables default to double** in F3 (MSX rule);
  until F3 lands, variables stay int16.
- **D-F — one BCD routine set, length-parameterised** (6 vs 14 digits): true
  per-precision arithmetic (matches the reference's single results) without
  two code copies.
- **D-G addendum — RESOLVED 2026-07-12: the space lever was the sub-ROM arc.**
  The blocker below is dissolved — evicting the tokeniser + detokeniser to the
  built-in sub-ROM (waves 1-3) freed **1260 B page-0 + 1351 B page-1** on the
  repack build, so F3 now lands in-window. (Original blocker text kept for
  history:) the F2 build leaves the
  repack window ESSENTIALLY FULL (page-0 slack 2 B, page-1 tail 29 B), so F3's
  ~0.6 KB has no home in the contiguous image. Remaining space = C-BIOS gap-1
  remainder (~322 B at `$0BBF`) + gap-2 (253 B at `$1ACA`), both usable only by
  fixed-position overlay code today. The D-G re-decide must therefore also pick
  the space lever: (a) a multi-region BASIC image (assemble around the gaps —
  at which point folding the tape body into the main assembly becomes natural
  and the tape-IPS layout coupling should be dropped, per the user's 2026-07-11
  suggestion; the standalone tape IPS build then needs its own org variant),
  (b) the next C-BIOS repack tranche (Tier-B content cuts,
  cbios-repack-space-analysis.md), or (c) heap-arc-first if its RAM work
  shrinks F3's ROM need.
- **D-G — F3 ordering vs the heap arc is re-decided at F2 close-out.** The
  real heap+descriptor model (string-engine deferral: heap, arrays/`DIM`,
  STRMAX→255) is orthogonal to F1/F2 — only F3's variable-store re-layout
  overlaps it. F1+F2 proceed now; when F2 closes, decide whether F3 grows the
  fixed typed table (as specced, swap-out contained behind the
  `var_get_key`/`var_set_key` API) or is specced directly against the heap
  arc's real-MSX variable-area model. Heap-first for the whole arc was
  considered and rejected: no dependency, weak oracle surface of its own,
  and it competes for the same ROM window.

## 7. Test plan / acceptance

- **Crunch probe** (standing, byte-identical): F1's encoder is verified
  literally byte-for-byte; boundary matrix per §3c.
- **New standing gate `make float-acceptance`** (modeled on
  string-acceptance): reference-lock + zerobas==reference screen compares;
  grows a half per slice — *literals* (F1), *arith* (F2), *vars* (F3).
- **Host unit tests** `tests/test_float.py` (emulator-free): dec↔BCD
  conversion, normalisation, rounding, formatter edge matrix — the cheap
  regression layer under the oracle gate.
- **All existing gates green per slice** + lean `basic.rom` byte-identical.

## 8. Open questions for sign-off

1. Approve the D-A slicing (or fold F1+F2 into one bigger slice)?
2. Approve D-C (signed migration inside F2) — it changes behaviour the
   existing acceptance corpus may silently rely on; the corpus runs decide.
3. F3 RAM growth — **RESOLVED 2026-07-12: variable-width entries** (int 2 /
   single 4 / double 8 B), VARSLOTS stays 32; see §11. (Was: +224 B fixed 11 B
   table moving the string region — user chose the heap-aligned variable-width
   model instead.)
4. Gate name `float-acceptance` OK?

## 9. F1 S2 — oracle-pinned contracts (VG-8020, 2026-07-11)

Black-box captures by `probes/basic/basic_probe_floatlit.py` (crunch bytes;
BLOAD-leads freeze at TAPION, KBUF read) and
`probes/basic/basic_probe_float_fmt.py` (PRINT output; bracketed VRAM span).
Re-runnable; the same probes in `--zb-machine` mode are the F1 differential
gates. "dec_exp" below = (lead byte & $7F) − 64.

### 9.1 Representation (confirms the MSX2 TH format)

- Token `$1D` + 4 bytes (single) / `$1F` + 8 bytes (double). Byte 0 = sign
  (bit 7) + excess-64 exponent (bits 6..0); byte 0 = `$00` ⇒ value 0. Then
  packed BCD mantissa digits (2/byte, left-justified, zero-padded): 6 digits
  (single) / 14 (double), normalised 0.1 ≤ m < 1.
  Captures: `32768` → `1D 45 32 76 80`; `.000001` → `1D 3B 10 00 00`;
  `9999999` → `1F 47 99 99 99 90 00 00 00`.
- The crunch never sets the sign bit (`-` is the operator token `$F2`).
- Zero encodes as token + ALL-ZERO value bytes (`0!` → `1D 00 00 00 00`).

### 9.2 Literal classification + conversion (tokeniser contract)

Let D = typed digit count, excluding leading zeros, INCLUDING trailing
zeros and post-`.` digits (`1e6` is D=1 → single, but `1000000` is D=7 →
double, same value — the rule counts CHARS, not numeric significance).

1. `%` suffix → int forms; the `%` is consumed, NO extra byte (`1%` → `$12`,
   `100%` → `0F 64`, `30000%` → `1C 30 75`); value > 32767 → crunch-time
   error (`65535%`: BLOAD leading the line never ran).
2. No `.`, no exponent, no suffix: D ≤ 5 and value ≤ 32767 → int forms
   (unchanged); D ≤ 6 with value > 32767 → single; D ≥ 7 → double
   (`999999` → single, `1000000` → double).
3. `.` and/or `E` exponent: D ≤ 6 → single, D ≥ 7 → double
   (`3.14159` → single, `3.141592`/`123456.7` → double).
4. `D` exponent or `#` suffix → double, always. `!` suffix → single, always.
5. Rounding to the precision's digit count is HALF-UP at both precisions
   (`1234565!`/`1234575!` → `123457`/`123458`; `…345`+`5` tail → `…35`).
   **Carry-out-of-all-digits quirk:** the single path does NOT renormalise —
   `9999995!` → `1D 47 10 00 00` = 1000000 (a 10× value change, faithfully
   reproduced); the double path DOES — 16 nines → `1F 51 10 00 …` = 1E16.
6. dec_exp = int-digit count (post-leading-zero-skip; negative for leading
   post-`.` zeros) + explicit exponent. Range: +63 max (`1e62` → `$7F`;
   `1e63` → crunch-time error, line never runs); −63 min encodable
   (`1e-64` → `$01`); BELOW that, byte 0 with mantissa RETAINED
   (`1e-65` → `1D 00 10 00 00` — reads as value 0, no error).
7. Crunch-time error surface: on the reference the whole line is rejected
   before any statement runs. zerobas: tokeniser sets an overflow flag;
   dispatch_line prints its own lowercase `overflow` and skips
   execute/store (message wording = D-2-style divergence, D-F1-1).
8. (Found during F1 implement, extra targeted capture — see
   `basic/float.asm` `tkf_try_exponent`:) a type suffix (`!`/`#`/`%`) is
   recognised only when NO `E`/`D` exponent was parsed; after an exponent
   the suffix char is left UNCONSUMED in the stream (`1e10#` leaves a raw
   `#` that derails the evaluator identically on both sides).

### 9.3 PRINT output format (formatter contract)

Shape: sign position (space or `-`) + digits + ONE trailing space. Both
precisions, same rules; `E` notation for both (never `D` on this reference).

- Value 0 (lead byte 0, mantissa ignored) → `0`.
- FIXED form iff −1 ≤ dec_exp ≤ 14 (`.01` fixed, `.001` → `1E-03`;
  `1e13`/`1d13` fixed 14-digit, `1e14`/`1d14` → `1E+14`).
  Layout: significant digits s = mantissa with trailing zeros stripped;
  dec_exp ≤ 0 → `.` + (−dec_exp) zeros + digits;
  s ≤ dec_exp → digits + (dec_exp − s) zeros, NO point (`1234567!` →
  `1234570`, `1.0` → `1`, `100000!` → `100000`);
  else digits[0..dec_exp) + `.` + rest (`3.14159`, `.0123`).
- E form: first digit, then (if s > 1) `.` + remaining significant digits;
  `E`; explicit sign; TWO-digit zero-padded |dec_exp − 1|
  (`6.023E+23`, `1.23E-03`, `2.5E-10`, `1E-64`, `1.2345678901235E+17`).
- Doubles display all 14 stored digits (trailing zeros stripped); singles 6.

### 9.4 F1 implementation protocol (repack-only)

- RAM (all free `$E0xx`, own choice): `FACTYP $E0BB` (2=int / 4=sng /
  8=dbl), `TKOVF $E0BC` (crunch overflow flag), `FAC $E0C8` (8 B, holds the
  value bytes exactly as tokenised), `FOUTBUF $E0D0` (24 B formatter out),
  `TKDIG $E0E8` (24 B tokeniser digit scratch). NUMBUF/print_number int
  path untouched.
- Evaluator: `eval` sets FACTYP=2 on entry. A `$1D`/`$1F` factor in `ev_f`
  copies the value bytes to FAC, sets FACTYP, and returns DE = the value
  rounded (half-up) into the 16-bit ADDRESS domain: positives to 65535 as
  their unsigned bit pattern, negatives to −32768 — matching the published
  POKE/HEX$ −32768..65535 argument range and the pre-F1 unsigned `$1C`
  cruncher (a strict-int16 cap would regress `POKE 40000,n`). Outside that
  → DE=0, NO error mark (interim divergence D-F1-2: float into an int
  context rounds silently; real Overflow semantics are F2). **F2
  correction (§10.3): the reference conversion TRUNCATES (wrap-then-
  truncate in the address domain) and errors out of domain — F1's half-up
  was reasoned, not oracle-pinned, and is superseded.** FACTYP is STICKY through operators; every binary/unary op-combine
  site calls a guard: FACTYP≠2 → ERRMARK `$DD`, FACTYP:=2, operands as the
  already-rounded ints (interim divergence D-F1-3: no float arithmetic
  until F2). Unary minus on a float flips the FAC sign bit (zero exempt)
  AND negates DE.
- PRINT: `exp_num` dispatches on FACTYP after eval — 2 → `print_number`,
  else the new formatter (FAC → FOUTBUF → `print_string`).
- Tokeniser: repack build replaces `tk_number` with the float-aware scanner
  (single pass into TKDIG + flags, then §9.2 classify/emit; int results
  emit the EXACT existing forms). `tk_loop` additionally routes `.`+digit
  (outside a name) into it. Lean build: byte-identical, all hooks
  `IF ROM_BASE < $4000`-gated.

## 10. F2 S2 — oracle-pinned contracts (VG-8020, 2026-07-11)

Black-box captures by `probes/basic/basic_probe_float_arith.py` (PRINT-bracket
span for values + screen-tail for the error surface; bare-statement lines for
statement-argument conversion). Three capture rounds; round 2/3 disambiguated
round-1 cases that crunch-time literal rounding had confounded. Re-runnable;
the same probe in `--zb-machine` mode is the F2 differential gate (the ARITH
half of `make float-acceptance`). "e(x)" below = a value's excess-64 decimal
exponent as stored, i.e. dec_exp.

### 10.1 Value model — all float arithmetic is DOUBLE

- **Single precision is a STORAGE format only.** Every `+ - * /` with any
  non-int operand widens both operands to double (BCD zero-pad — exact) and
  yields a DOUBLE result. Pins: `2!/3!` → `.66666666666667` (14 digits);
  `123456!+.5` → `123456.5` and `1000000!+1!` → `1000001` (sums exact only
  beyond single's 6 digits); `123456!*654321!` → `80779853376` (exact
  11-digit product); `2!/3!=2#/3#` → −1 (identical double computations).
  This SUPERSEDES §3b's per-precision promotion sketch and simplifies D-F:
  only one 14-digit routine set exists at runtime.
- `/` is always real division, always double: `7/2` → `3.5`, `1/3` →
  `.33333333333333`, `-7/2` → `-3.5` — retires the integer-quotient
  divergence (D-C).
- int⊗int `+ - *` stays int16 (fast path); on 16-bit overflow the operation
  promotes and the result is EXACT (`32767*32767` → `1073676289`,
  `-32768-32768` → `-65536`, `3125*625` → `1953125`). Whether the reference
  types these single or double is black-box-invisible for `+`/`-` (results
  ≤ 6 digits) but `*` products print > 6 exact digits ⇒ double; zerobas
  promotes to double uniformly (own-design where unobservable).
- Relationals over any float operand compare AS floats after widening —
  never int-converted (`40000=40000!` → −1, `1e10>5` → −1 — no Overflow;
  `.1!=.1#` → −1). Result is int −1/0 (`(1.5>1)+5` → `4`). All six forms
  pinned incl. compounds (`>=`, `<=`, `<>`).
- Multi-item PRINT: the accumulator type resets per item
  (`print 1.5;2` → ` 1.5  2 `).

### 10.2 Double arithmetic semantics

- **Rounding: guard-digit HALF-UP on the magnitude** (away from zero) for
  add / mul / div: `1+5e-14` → `1.0000000000001` (tie up) vs `1+4e-14` → `1`;
  `1-1e-15` → `1` (carry through all 14 nines); `2.5#*1.0000000000001#` →
  `2.5000000000003` (mul tie up); `1.0000000000003#/4` → `.25000000000008`
  (div tie up); `-2/3` → `-.66666666666667` (magnitude, not toward +∞).
  **EXCEPTION — effective subtraction ties round TOWARD ZERO** (opposite-sign
  combine, incl. every `-`): `2-5e-14` → `1.9999999999999` (not `2`). This is
  bug-for-bug reference behaviour (the reference keys the tie on the effective
  op, not the surface token); implemented 2026-07-13 (commit `fe0d99c`,
  `fpa_sub_finalize`), see [spec-float-subtract-tie-compat.md](spec-float-subtract-tie-compat.md).

> **⚠️ Reference-divergence addendum (2026-07-13) — the F1–F3 "reference-identical"
> claim has TWO known exceptions, both in DIVISION-driven rounding, both
> characterized black-box:**
> 1. **`fp_div` is correctly-rounded; the reference's is LOW-BIASED** (0 to −5 ulp,
>    growing with divisor significant-length). Live example: `2/1.4142135623731` →
>    zerobas `1.4142135623731` (correct) vs reference `1.4142135623729`. Identical
>    for divisors ≤10 significant digits; diverges (we're *more* accurate) beyond.
>    The reference's exact per-digit rule lives in the hidden 15th digit and is
>    **not clean-room black-box recoverable** (RE campaign plateaued ~80%/±1 ulp;
>    reading it needs disasm, barred) — so this is a **documented deviation, kept**,
>    not a bug to fix. See [[bug-for-bug-compat-over-accuracy]] + spec-basic-math-pack §10.3.1.
> 2. **`SQR`** (math pack) inherits this: correctly-rounded Heron over our div,
>    diverges from the reference exactly where the reference's div-driven Heron is
>    1 ulp off truth (~40% of near-boundary inputs); zerobas is always ≥ as accurate.
>
> The original `float-acceptance` matrix (349/349) never included near-unity
> 14-digit divisions, so it reported "reference-identical" with this blind spot;
> the exposing cases are now pinned in `basic_probe_float_arith.py` as
> characterized known-deviations.
- Add/sub are exact through the 14-digit window (`1/3*3-1` → `-1E-14`;
  `99999999999999#+1` → `1E+14` — mantissa carry renormalises).
- **Overflow checks are PRE-normalisation on the operand exponents:**
  - mul: e(a)+e(b) > 63 → "Overflow" even when the normalised result fits:
    `2e62*4` → Overflow (63+1=64) though 8e62 is representable; `1e62*9` →
    Overflow; `9e61*9` → `8.1E+62` (62+1=63 passes).
  - div: e(a)−e(b)+1 > 63 → "Overflow" even when the quotient fits:
    `2e62/.4` → Overflow (63−0+1) though 5e62 is representable;
    `1e40/1e-40` → Overflow.
  - add/sub: only genuine result overflow observed (`9e62+9e62` → Overflow;
    `1e62+0#` → `1E+62`).
- Underflow → 0, silently, both ops (`1e-40*1e-32` → `0`, `1e-40/1e30` →
  `0`); boundary exact: `1e-32*1e-32` → `1E-64` (representable, lead $01),
  `1e-33*1e-32` → `0`.
- Division by zero: `x/0`, `x\0`, `x mod 0` → "Division by zero", ALL
  precisions including int (`1/0`, `1!/0`, `1#/0`, `0/0`).
- **Error model: runtime numeric errors ABORT the statement** — in
  `print "[";1/0;"]"` the `[` prints, then the message, never the value or
  `]`. zerobas prints its own lowercase wording, same abort shape
  (divergence D-F2-1, the D-2 pattern).

### 10.3 Float→int16 conversion contexts — two domains, both TRUNCATE

Both conversions share one shape: an EXCLUSIVE-bounds domain check on the
un-truncated value, then truncate toward zero (after a wrap, in the address
domain's high half). Fractional values just inside a bound are legal;
truncation can then land ON the bound.

- **Strict int16 domain** — operands of `\`, `MOD`, `AND`, `OR`, `XOR`,
  `NOT`: domain −32769 < x < 32768, truncate toward zero (`2.9\1` → `2`,
  `-2.9\1` → `-2`, `7.5 mod 4` → `3`, `7\1.5` → `7`, `not 2.5` → `-3`
  = NOT 2; boundaries: `32767.5\1` → `32767`, `-32768.5\1` → `-32768`);
  outside → "Overflow" abort (`40000!\2`, `40000 mod 7`,
  `40000! and 65535`, `100000! and 1` — note the LOGICAL ops are strict
  too, not address-domain).
- **Address domain** (the published POKE/HEX$ −32768..65535 range) —
  statement/function int arguments: domain −32769 < x < 65536; a value
  ≥ 32768 is wrapped by −65536 into the signed domain FIRST, then
  truncated toward zero (⇔ ceiling mod 65536 for the high half):
  `hex$(2.9)` → `2`, `hex$(-2.5)` → `FFFE` (−2), `hex$(32767.5)` → `7FFF`
  (below the wrap threshold — plain truncation), but `hex$(40000.5)` AND
  `hex$(40000.1)` → `9C41` = 40001 (40000.x → −25535.9̄ → −25535: any
  fraction rounds UP in the high half), `hex$(65535.5)` → `0` (→ −0.5 →
  0), `hex$(-32768.9)` → `8000`. Outside the domain → "Overflow" abort
  (`hex$(65536.)`, `poke 100000,0` → Overflow; `poke 40000.5,1` → legal,
  silent, address 40001). This RETIRES interim divergence D-F1-2 (silent
  round, DE=0 out of range) and CORRECTS F1's `flt_to_int16` (its half-up
  mode was reasoned from the published range, not oracle-pinned; the
  reference truncates).
- F1's crunch-time HALF-UP literal rounding (§9.2 rule 5) is unaffected —
  that is tokenise-time mantissa rounding, byte-pinned separately.

### 10.4 Signed integer `\` and `MOD` (the D-C migration)

- `\` truncates toward zero: `7\2` → `3`, `-7\2` → `-3`, `7\-2` → `-3`,
  `-7\-2` → `3`; `32767\-1` → `-32767`.
- Quirk: `-32768\-1` → `32768` printed — the result ESCAPES int16 without
  error (promoted; the int16 bit pattern $8000 would have printed −32768).
- `MOD` takes the DIVIDEND's sign: `7 mod 2` → `1`, `-7 mod 2` → `-1`,
  `7 mod -2` → `1`, `-7 mod -2` → `-1` (identity a = (a\b)*b + (a mod b)
  holds with truncation).
- Division by zero for both → "Division by zero" abort (replaces zerobas's
  0 + ERRMARK divergence, D-C).

### 10.4a IF truthiness over a float condition

`IF x THEN` takes the TRUE branch iff x ≠ 0 for FLOAT x too — `IF .5 THEN`
is TRUE on the reference (companion capture, F2 review live-check
2026-07-11), so the truncated int view of a float condition must never be
the truthiness judge (a truncate-to-DE model would make every |x|<1 float
falsely FALSE). `IF 1.5-1.5 THEN` → false. Note the OPERANDS of the logical
operators stay §10.3 strict-int (`.5 AND 1` → 0 AND 1 = 0 — consistent on
both sides); only the bare condition value is float-aware.

### 10.5 Formatter interaction (F1 unchanged)

Results print through the F1 §9.3 formatter as-is: `12345678#*87654321#` →
`1.0821520223746E+15`, `1!/512!` → `1.953125E-03` (dec_exp −2 → E form),
`1e-32*1e-32` → `1E-64`. No new output shapes were observed in ~140 arith
captures.

## 11. F3 S2 — oracle-pinned contracts (Philips VG-8020, 2026-07-12)

**S3a SHIPPED 2026-07-12** (typed variable-width store + `%`/`!`/`#` suffixes +
coercion; NO DEF statements yet — that is S3b). Gate = the vars half of
`make float-acceptance` (`basic_probe_float_vars.py`, 40 cases). The Fable
review caught three matrix-invisible bugs, each now pinned by a regression case:
(A) fresh-entry zero-init wiped 256 B (wrong `zero_fill` count register) →
corrupted STRTAB; (B) cross-type LET read the LHS type from a global clobbered by
the RHS's `var_name_key` (now latched in `LHS_VARTYPE` before eval); (C) —
PRE-EXISTING F1 — `tok_skip` lacked the `$1D`/`$1F` float-literal strides, so any
STORED program with a float literal broke (fixed with gated +4/+8 strides). RAM
cells `VARTYPE`/`VS_TARGET_TYPE`/`VS_INT_VAL`/`LHS_VARTYPE` at $F14E–$F152 (free
window below DRVA_DPB $F195). Lean `basic.rom` byte-identical.

**S3b SHIPPED 2026-07-12** (`DEFINT`/`DEFSNG`/`DEFDBL`/`DEFSTR` — the last F3
half). The mnemonics are NOT keyword tokens (only `DEF` is), so after the `DEF`
token they arrive as plain upcased ASCII; `ex_def_type` (basic/usr.asm) parses
`INT`/`SNG`/`DBL`/`STR` + a comma-list of `letter`/`letter-letter` range items
into a 26-byte `DEFTBL` ($F153, sysvars.inc), reset to all-double by
`clear_vars` at INIT/RUN. `var_name_key` (numeric default) and `var_str_type`
(DEFSTR → the unsuffixed name selects STRTAB) consult it at every reference; an
explicit `%`/`!`/`#`/`$` suffix always wins. All 14 spec §11.1 cases pinned in
the vars probe (now 58 cases), incl. the orphan-on-redeclare and DEFSTR-numeric
Type-mismatch contracts. Gate: `make float-acceptance` (vars half). Lean
`basic.rom` byte-identical.

The DEFtbl "unsuffixed name → default type" rule lives in ONE place,
`deftbl_lookup` (vars.asm), shared by `var_name_key`'s no-suffix path,
`var_str_type`, and the single-letter `var_get`/`var_set` shims.

Three bugs were fixed before ship; the matrix passed each time until the case
that exposed them was added — the F1/F2/S3a "differential + review beats the
happy-path matrix" lesson again:
- **The range-fill** loaded its count from `D` (range-end) AFTER `ld de,DEFTBL`
  had already clobbered `D` → a garbage ~177-byte fill corrupting the $F1xx
  sysvar area. Caught by the differential (`def.int.range.out`: D outside `A-C`
  must stay double). Now the count is computed before the address.
- **The FOR/NEXT + READ shims** (`var_get`/`var_set`) hardcoded type-8, correct
  under S3a's "unsuffixed ≡ double" invariant but WRONG once S3b made unsuffixed
  references resolve via the DEFtbl: a `DEFINT` loop/READ variable was stored as
  double yet read back as an int (a never-written `var_find_typed` (name,type)
  entry) = 0 — silent because the loop iterates self-consistently. Caught by the
  Fable review (no probe combined DEF with FOR/READ); fixed by routing the shims
  through `deftbl_lookup`. Pinned by `reg.S3b.fornext_defint{,_sum}` and
  `reg.S3b.read_defint`.
- **`var_str_type`** became letter-keyed for the DEFtbl default, but
  `ex_mid_stmt` calls it on the RAW target, so a non-letter (a `MID$` string
  LITERAL target) indexed the DEFtbl out of range. Fixed with an `is_letter`
  guard (restores the pre-S3b totality). Pinned by `reg.S3b.mid_literal_target`.

Two DIVERGENCES the review surfaced are left as-is because they are the SAME
pre-existing behaviour as an explicit `$` string variable in the same context,
not new to S3b (verified live: `A$="HI":B=A$+1` already prints ` 1 `, and
`VARPTR(A$)` already allocates a phantom numeric entry): a DEFSTR-defaulted name
used in a NUMERIC expression evaluates as 0 instead of `Type mismatch`, and
`VARPTR` of one allocates a phantom entry. Both are the "string variable in a
numeric/VARPTR context" limitation; closing it (a real Type-mismatch in
expression context) is a separate cross-cutting change, out of F3 scope.

The probe also grew a length-scaled Enter gap: openMSX types a ~45-char line
over ~8 emulated seconds, so the VARPTR-compare cases need the Enter fired later
than the 3 s default or it is swallowed mid-type (a latent flake that only
surfaced when this rebuild shifted timing).

Typed numeric variables. Captured via `A…=<expr>:PRINT"[";A…;"]"` on the
reference; span = the printed value, tail = the error surface. Storage model =
**variable-width entries** (user pick 2026-07-12, the D-G heap-aligned option):
each entry `[name0][name1][type][value: 2 int / 4 single / 8 double]`, sized to
the resolved type — VARSLOTS stays 32, no fixed 11 B slot, and it pre-aligns
with the future heap arc's real-MSX variable area. The `$` suffix still selects
the separate STRTAB store.

### 11.1 Type resolution — variable identity is (name, resolved type)

- **Unsuffixed numeric default = DOUBLE** (confirms D-E; MSX-BASIC really does
  default to double — `A=1/3` → ` .33333333333333`, identical to `A#`, not the
  6-digit `A!`). This corrects the arc's earlier "MSX default is single" doubt.
- Suffix forces the type: `%` int, `!` single, `#` double, `$` string. `A%`,
  `A!`, `A#` are up to **three distinct entries**; `A` ≡ `A#` while the default
  is double (`A=1:A!=2:A#=3:PRINT A;A!;A#` → ` 3  2  3` — `A#=3` overwrote `A`).
- `DEFINT/DEFSNG/DEFDBL/DEFSTR <letter-range>` set the default type for name
  **first letters** in the range. `DEFINT A-C:B=1.9` → `1` (B in range → int);
  `…:D=1.9` → `1.9` (D outside → default double). `DEFSTR S:S="HI"` → `HI` (an
  unsuffixed name becomes a **string** variable — selects STRTAB).
- The type table is consulted at **each variable reference**, so re-declaring a
  letter's type **orphans** any value stored under the old type:
  `A=7:DEFINT A:PRINT A` → ` 0` (the double `A=7` is now unreachable as
  unsuffixed `A`, which resolves to the unset int slot).

### 11.2 Store coercion — RHS value → the variable's declared type

- **→ int: TRUNCATE toward zero** — `A%=1.7` → `1`, `A%=-1.7` → `-1`,
  `DEFINT A:A=1.7` → `1`. Same rule as F2's §10.3 float→int contract (not a new
  rounding domain).
- **→ single: ROUND to 6 significant digits**, half-up with carry
  renormalisation — `A!=1234567` → `1234570`, `A!=123456.7` → `123457`,
  `A!=2/3` → `.666667`, `A!=1.9999999` → `2`. **Asymmetry to preserve:** int
  store truncates, single store rounds.
- **→ double: exact** (14 significant digits retained).
- **Cross-type numeric↔string assignment → `Type mismatch`, statement aborts**
  (no value stored): `A%="X"` and `A$=5` both print `Type mismatch`.

### 11.3 PRINT precision + interactions

- PRINT of a typed variable formats per the stored FACTYP through the F1 §9.3
  formatter unchanged: int / 6-digit single / 14-digit double.
- **Deferred (D-D):** a **typed/float FOR/NEXT loop variable** — the reference
  drives the loop in the variable's own type; zerobas keeps the int16 loop path
  in F3 (documented divergence, fast-follow slice). Note the interaction that
  unsuffixed loop vars now default to double on the reference.

### 11.4 F3 implementation protocol (repack-only)

- All F3 code is `IF ROM_BASE < $4000` (lean `basic.rom` stays byte-identical),
  landing in the sub-ROM-arc-freed window (1260 B page-0 / 1351 B page-1 as of
  2026-07-12 — the D-G "no home" blocker is dissolved).
- Rework `var_find`/`var_get_key`/`var_set_key` (`basic/vars.asm`) from the
  fixed 4 B int-only walk to a **variable-stride** walk keyed on (name, type),
  reading the type byte to advance. Preserve the single-letter `var_get`/
  `var_set` shims (FOR/NEXT, READ) on the int16 path (D-D).
- Add a DEFtbl (26-entry letter→type map) consulted by `var_name_key` /
  `var_str_type` to resolve unsuffixed names; `DEFINT/SNG/DBL/STR` statements
  write ranges into it. Retire the `vnk_suffix` "consume and ignore" path.
- Store coercion: int = the §10.3 truncate; single = a 14→6 digit BCD round
  (reuse F1's `round_and_finalize`); double = copy.
- Gate: `basic_probe_float_vars.py` becomes the **vars half** of
  `make float-acceptance` (characterise + `--zb-machine` differential), plus the
  full standing battery + lean byte-identical. Per the model split, S3 is a
  Sonnet implement drop + Fable review — both F1 and F2 reviews caught
  matrix-invisible bugs, so give the vars matrix false-EXPECTED and
  function-over-typed cases and always run the whole differential.
