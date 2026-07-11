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
F3 widens the numeric store to `[name0][name1][type:1][value:8]` = 11 B/entry;
32 slots = 352 B (+224 B), which pushes STRTAB/STRSCR/temp-ring up — F3's S2
must re-verify the string-engine §5a RAM analysis before moving anything.

## 6. Decisions (recommendations for sign-off)

- **D-A — arc slicing** F1 literals+PRINT → F2 arithmetic → F3 typed vars,
  each slice its own S2/S3 + commit. Interim seams are documented divergences:
  after F1, floats print but don't compute; after F2, `LET` of a float value
  **rounds to int16** (resolved by F3).
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
3. F3 RAM growth (+224 B, moving the string region) — acceptable, or cap
   VARSLOTS lower?
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
  context rounds silently; real Overflow semantics are F2). FACTYP is STICKY through operators; every binary/unary op-combine
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
