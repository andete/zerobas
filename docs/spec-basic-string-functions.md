<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — BASIC string functions (INSTR / HEX$ / OCT$ / STRING$ / SPACE$) — a Phase-3 follow-on slice

**Status: SIGNED OFF (S1, 2026-07-10) — S2/S3 pending.** All six decisions accepted as
recommended (§6: five verbs; unsigned-16 HEX$/OCT$; clamp-to-STRMAX + negative→error;
probe-for-string-first for STRING$/INSTR arg typing; repack-only + reuse ring + S2 captures
token widths black-box first). The next batch of deferred string verbs from
the string-engine arc ([`spec-basic-string-engine.md`](spec-basic-string-engine.md) §1
"Out of scope" / §6 D-B, and [`spec-basic-string-compare.md`](spec-basic-string-compare.md)
§1 "Out of scope": "`INSTR`, `HEX$`, `OCT$`, `STRING$`, `SPACE$` … separate follow-on
verbs"). User-selected 2026-07-10 as the next Phase-3 session item. This is the *how* +
*decisions*; same shape as the engine + compare specs. **Repack-only**, like the whole
string engine — the lean `basic.rom` stays byte-for-byte unchanged (everything is gated
`IF ROM_BASE < $4000`).

## 1. Goal & scope

Add the five remaining *non-float, non-heap* string library functions so everyday
one-liners and loader stubs that format numbers (`HEX$`/`OCT$`), pad/fill fields
(`SPACE$`/`STRING$`), or search text (`INSTR`) work. All five sit squarely inside the
proven S4 machinery (the temp-string ring, the descriptor model, the IX↔HL bridge) — no
new RAM architecture, no floats, no heap.

**In scope (the five):**

| Verb | Form | Sig | Returns |
|---|---|---|---|
| `HEX$` | `HEX$(n)` | n→s | uppercase hex text of `n` viewed as unsigned 16-bit |
| `OCT$` | `OCT$(n)` | n→s | octal text of `n` viewed as unsigned 16-bit |
| `SPACE$` | `SPACE$(n)` | n→s | `n` spaces |
| `STRING$` | `STRING$(n,c)` / `STRING$(n,x$)` | (n,n\|s)→s | `n` copies of a fill char |
| `INSTR` | `INSTR([p,]a$,b$)` | ([n,]s,s)→n | 1-based position of `b$` in `a$` (0 = not found) |

- Every string operand (`a$`, `b$`, the `x$` of `STRING$`) may be any form the engine
  already evaluates via `str_eval`: a `"literal"`, a `$`-var, a string function, or a `+`
  concatenation — because the arguments bridge back through `str_eval` exactly as the S4
  substring verbs' source argument does.
- The numeric arguments (`n`, `p`, the `c` code of `STRING$`) bridge back to `eval`, the
  established IX↔HL pattern (`ev_str_arg` / the `CVI` bridge).
- Reached wherever an expression is evaluated (`PRINT`, LET into a `$`-var, an `IF`
  condition, a function argument), because the hooks live in the shared factor/`str_eval`
  layers — same reach the S4 verbs already have.

**Out of scope (deferred, consistent with the engine):**
- `INKEY$` (needs the keyboard/console read path — a different subsystem), the `MID$`
  *assignment statement* (needs an lvalue path into a string var), `BIN$`/`LPOS`.
- Floating-point operands and any float rendering; the real heap+descriptor model; string
  arrays / `DIM`; `STRMAX`→255 (all the standing engine deferrals).
- Any change to the **lean** build — no string engine there; every byte of this slice is
  gated `IF ROM_BASE < $4000`.

## 2. Behaviour (the contract)

Semantics come from the **public MSX-BASIC language reference**; the exact edge-case
results (empty needle, `n=0`, negative arg, `INSTR` past end) are **oracle-captured
black-box on the Philips VG-8020** in S2 (§5) — the values below are the expected contract,
to be *confirmed against the reference*, never assumed.

- **`HEX$(n)`** — render `n` **as an unsigned 16-bit value** in uppercase hexadecimal, no
  leading zeros, always ≥ 1 digit (`HEX$(0)="0"`, `HEX$(255)="FF"`, `HEX$(-1)="FFFF"` via
  the two's-complement 16-bit view). Integer-only, consistent with the whole engine.
- **`OCT$(n)`** — same, base 8 (`OCT$(8)="10"`, `OCT$(-1)="177777"`).
- **`SPACE$(n)`** — a string of `n` space (`$20`) characters. `SPACE$(0)` = empty. `n`
  beyond `STRMAX` clamps to `STRMAX` (own-design, per D-3); negative `n` is an error
  (D-3).
- **`STRING$(n,c)`** — `n` copies of a single fill character. Two argument shapes,
  distinguished by the second argument's *type* (D-4): a **numeric** `c` is a character
  **code** (`STRING$(3,65)="AAA"`), a **string** `x$` contributes its **first byte**
  (`STRING$(3,"*")="***"`, `STRING$(3,"abc")="aaa"`). `n` clamps to `STRMAX`; empty `x$` is
  an error (no first byte, mirrors `ASC ""`).
- **`INSTR([p,]a$,b$)`** — 1-based index of the first occurrence of `b$` within `a$`,
  searching from position `p` (default 1). Returns **0** when not found. The optional
  leading numeric `p` is distinguished from the two-argument form by probing the first
  argument's type (D-5). Reference edge cases to lock in S2: empty `b$` → returns `p`
  (clamped into range); `p` past `LEN(a$)` → 0; `p<1` → error.

All numeric results are the ordinary 16-bit integer values the numeric evaluator already
produces; all string results are `[len][bytes]` descriptors in a temp-ring slot, exactly
like the S4 verbs.

## 3. Architecture — three integration shapes (the organizing insight)

The five verbs are *not* uniform: the reference token map assigns three of them the
`$FF`-prefixed **function** encoding and two of them **single-byte reserved-word** tokens.
That token width dictates *where* each dispatch hook lives. This is the one structural
fact that shapes the slice, so it is called out up front (and the widths are an S2 oracle
gate — §4, D-6):

### 3a. Group A — `$FF`-prefixed, string-returning: `HEX$`, `OCT$`, `SPACE$`

A **pure mirror of S4's `CHR$`/`STR$`**. Each is a 2-byte `$FF <selector>` function
token; the crunch/LIST wiring is one `kwtable.inc` line each (repack-gated block), and the
dispatch is one `cp <TOKEN> / jp z,<handler>` case appended to **`str_func_ff`**
([`basic/str-engine.asm`](../basic/str-engine.asm):385) — the same entry that already
fields `CHR$`/`STR$`/`LEFT$`/`RIGHT$`/`MID$`. Zero new architecture.

- **`HEX$` / `OCT$`** reuse the **existing** `detok_hex16` / `detok_oct16` formatters
  ([`basic/list.asm`](../basic/list.asm):330,372) — today they emit an unsigned-16 value
  via the LIST `pchar` sink for `&H`/`&O` detokenising. Factor each to a small
  "emit into a descriptor" variant (the same move S4 did for `STR$` reusing `pu_fmt_int`):
  allocate a ring temp, evaluate the numeric arg, run the digit loop writing bytes into the
  temp and counting the length. Keeping the current `detok_*16` entry points **byte-identical**
  (the lean build proves it) protects LIST.
- **`SPACE$`** allocates a ring temp and fills `min(n,STRMAX)` `$20` bytes — a one-liner
  over the same temp allocator (`str_alloc_temp`).

### 3b. Group B — single-byte token, string-returning: `STRING$` (`$E3`)

`STRING$` is a **single-byte** reserved-word token, not `$FF`-prefixed, so it does **not**
arrive through the `$FF` factor path that routes to `str_func_ff`. It needs `str_eval`
itself to recognise the leading single-byte token. Add a repack-gated branch in the
`str_eval` entry dispatch ([`basic/strvar.asm`](../basic/strvar.asm), alongside the
existing literal/`$`-var/`$FF`-function cases): `cp STRING_TOKEN / jp z,str_fn_string`.
Because `IF`/LET/`PRINT`/concat all already funnel string context through `str_eval`, this
single hook lights up every context at once — exactly as the S4 `$FF` verbs did through
`str_eval_maybe_mki`.

`str_fn_string` reads `(`, evaluates the count `n` (numeric bridge), the comma, then the
**second argument by type** (D-4): probe for a string operand via `str_eval` (CF set ⇒
use its first byte); if not a string, evaluate it numerically as a char code. Allocate a
ring temp and fill `min(n,STRMAX)` copies of the resolved fill byte; read `)`.

### 3c. Group C — single-byte token, number-returning: `INSTR` (`$E5`)

`INSTR` returns a **number**, so it belongs in the numeric factor `ev_f`
([`basic/expr.asm`](../basic/expr.asm):350) — which already dispatches single-byte
function tokens `USR`/`VARPTR`/`BASE`. Add a repack-gated `cp INSTR_TOKEN / jp z,ev_f_instr`
branch right beside them (the lean `ev_f` stays byte-identical — the branch is behind the
gate). `ev_f_instr`:

1. read `(`, then probe the **first** argument's type (D-5): `str_eval` CF set ⇒ the
   two-argument form (`p` defaults to 1, this operand is `a$`); CF clear ⇒ evaluate it
   numerically as the start `p`, read the comma, then `str_eval` for `a$`.
2. **snapshot `a$`** into a ring temp (the dup-then-operate discipline the substring verbs
   and the compare LHS-snapshot use), so evaluating `b$` can't clobber it.
3. read the comma, `str_eval` for `b$`, snapshot it too (a second ring slot). N=3 covers
   `a$` + `b$` + headroom — no new RAM (D-6).
4. run a byte-wise search: for each start position from `p` to `LEN(a$)-LEN(b$)+1`, compare
   `LEN(b$)` bytes; first full match → return that 1-based index; none → 0. Empty-`b$` and
   out-of-range `p` per the S2-locked contract (§2).
5. return the result to `ev_f` as the ordinary numeric factor value (via the IX↔HL bridge).

### 3d. Placement & gating (all three groups)

- All five handlers + the two `detok_*16`→descriptor variants live in
  [`basic/str-engine.asm`](../basic/str-engine.asm) (repack low region), beside the ring /
  verb / comparator code, keeping page 1 lean.
- All dispatch hooks are near-zero-byte `IF ROM_BASE < $4000` branches: the lean
  `str_func_ff` is untouched (Group A appends *after* the existing cases, inside the file
  that is already whole-gated repack-only), and the lean `ev_f` / `str_eval` gain nothing
  (Group B/C branches are behind the gate). **Lean `basic.rom` byte-identical.**
- No new RAM: Group A/B use one ring temp each; `INSTR` uses two (D-6). The N=3 ring
  suffices; no `CMPBUF`-style dedicated buffer needed.

## 4. Tokens — oracle-locked widths *and* values (the hard S2 gate)

Unlike the compare slice (which added *no* token), this slice adds **five keyword
entries**, and — critically — their **encoding width is not uniform**. Per the sourced
**MSX2 Technical Handbook Table 2.20** (already the cited source for every zerobas token,
in `basic/sysvars.inc`), the cross-check target is:

| Verb | Expected token | Width | Dispatch hook |
|---|---|---|---|
| `SPACE$` | `$FF $99` | 2-byte `$FF`-prefixed | `str_func_ff` (Group A) |
| `OCT$` | `$FF $9A` | 2-byte `$FF`-prefixed | `str_func_ff` (Group A) |
| `HEX$` | `$FF $9B` | 2-byte `$FF`-prefixed | `str_func_ff` (Group A) |
| `STRING$` | `$E3` | 1-byte reserved word | `str_eval` (Group B) |
| `INSTR` | `$E5` | 1-byte reserved word | `ev_f` (Group C) |

These values/widths are **captured black-box** in S2 by crunching each keyword on the
VG-8020 (`basic_probe_crunch.py`, the established harness) and reading the emitted bytes —
*then* asserted equal to this table. **Never a reference-ROM disassembly**
([[no-reference-rom-disasm]]). The dispatch-hook location (§3) *depends on the captured
width*, so the S2 capture is a hard gate before any handler is written (D-6); if a capture
contradicts the width column, the handler moves to the group matching the real width. The
`'$'` is **part of the keyword** for `HEX$`/`OCT$`/`SPACE$`/`STRING$` (like `MKI$`); none
share a 2-char prefix with an existing keyword (`STR$` vs `STRING$`: `match_kw` is
full-keyword, not prefix — no shadow), and the new single-byte tokens must not collide with
an existing token equate (an S2 check).

## 5. Validation & oracle

- **Oracle (S2, black-box, no disassembly).** A new probe `basic_probe_str_fn.py` captures
  the VG-8020's result for a battery per verb — `HEX$`/`OCT$` over {0, small, `$FF`,
  `$FFFF`, negative}; `SPACE$`/`STRING$` over {0, mid, > `STRMAX`, numeric vs string fill};
  `INSTR` over {found, not-found, empty needle, `p` mid / past end, overlapping} — by
  evaluating each into a numeric var or `PRINT`ing the string and reading it back, asserting
  the §2 contract on the *reference* first, then asserting zerobas matches the reference.
- **Crunch (gate).** The five keywords crunch byte-identical to the VG-8020 (the §4 token
  bytes) — added to the `basic_probe_crunch.py --zb-machine` corpus as a standing regression
  guard, and they LIST-detokenise back (both directions scan `kwtable`).
- **Execute (gate).** Extend the `string-acceptance` EXECUTE half
  ([`basic_probe_string.py`](../probes/basic/basic_probe_string.py)) with live
  bracket-wrapped cases on the repack machine (`PRINT "[";HEX$(255);"]"`,
  `PRINT INSTR("HELLO","LL")`, `PRINT STRING$(3,"*")`, …) — screen-verified output.
- **Unit tests.** `tests/test_str_fn.py` (host Z80) covers each handler's raw output: the
  `detok_*16`→descriptor variants, the `STRING$` numeric-vs-string fill, `SPACE$`/`STRING$`
  `STRMAX` clamp, and the `INSTR` search (found / not-found / empty / start-offset).
- **Gates that must stay green:** lean `basic.rom` byte-identical; unit-test (current 41 +
  new); `string-acceptance` PASS (crunch + execute + compare, now incl. these five);
  `diskbasic-acceptance-repack` 34/34 (shared factor/`str_eval` path unregressed);
  `repack-boot` PASS; audit-citations clean. Refresh the shipping
  `zerobas-main-eu.ips`/`.bps` in S3.

## 6. Decisions — to settle at sign-off

- **D-1 — verb set = the five** (`INSTR HEX$ OCT$ STRING$ SPACE$`). *(User-selected
  2026-07-10.)* Deferred siblings `INKEY$` / `MID$`-statement / `BIN$` / `LPOS` stay out.
- **D-2 — `HEX$`/`OCT$` numeric view → unsigned 16-bit** (two's-complement for negatives:
  `HEX$(-1)="FFFF"`), reusing `detok_hex16`/`detok_oct16` which already render an unsigned
  16-bit word. Integer-only, consistent with the engine. *(Recommend: accept — it is the
  reference behaviour and reuses existing code.)*
- **D-3 — `SPACE$`/`STRING$` length handling → clamp to `STRMAX` (=64), negative → error.**
  A count > `STRMAX` clamps (own-design, identical to the concat/substring `STRMAX` clamp
  philosophy — the one documented divergence from the reference's 255 ceiling); a negative
  count sets `ERRMARK` (mirrors `ASC ""`). *(Recommend: accept — consistent with the whole
  engine; 255 waits for the RAM re-architecture.)*
- **D-4 — `STRING$` 2nd-arg type detection → probe-for-string-first.** Try `str_eval` (CF
  set ⇒ string, use first byte; empty ⇒ error); else evaluate numerically as a char code.
  *(Recommend: accept — reuses the established type probe; matches reference dual form.)*
- **D-5 — `INSTR` optional-`p` detection → probe-first-arg-type.** `str_eval` on the first
  argument: CF set ⇒ two-arg form (`p`=1); CF clear ⇒ that operand is the numeric `p`,
  then the two strings follow. *(Recommend: accept.)*
- **D-6 — placement/RAM + the token-width gate → repack-only, reuse the N=3 ring, S2
  captures widths first.** No new RAM (`INSTR` = 2 live snapshots + headroom); every hook
  is repack-gated; the S2 black-box width/value capture is a hard gate before handlers
  (the hook group follows the captured width). *(Recommend: accept.)*

## 7. Risks & non-goals

- **Risk: token-width surprise.** If a captured width differs from §4, a handler is in the
  wrong dispatch group. Mitigation: S2 oracle capture is a hard gate *before* any handler
  (D-6); the three group hooks are cheap to re-home.
- **Risk: `INSTR` arg-shape ambiguity.** The optional leading `p` plus two strings is the
  most complex parse in the slice. Mitigation: the probe-based detection (D-5) reuses the
  proven `str_eval`-CF pattern; the S2 oracle locks the empty-needle / out-of-range-`p`
  edges before coding.
- **Risk: `detok_*16` factoring perturbs LIST.** Sharing the hex/octal digit loop with
  `HEX$`/`OCT$` could disturb `&H`/`&O` detokenising. Mitigation: keep the existing
  `detok_hex16`/`detok_oct16` entry points byte-identical (lean build unchanged proves it);
  add a descriptor-target variant, don't rewrite the sink.
- **Risk: ring depth.** `INSTR(a$+b$, c$+d$)` needs both concatenations live. Mitigation:
  snapshot each argument into its own ring slot immediately (§3c); N=3 covers two snapshots
  + one transit; document the depth limit as the standing own-design ring bound (§3a of the
  engine spec).
- **Non-goal:** `INKEY$`, the `MID$` statement, floats, heap/GC, `STRMAX`→255, any lean-build
  change.

## 8. Session plan (slices, each commits at its gate)

1. **S1 — this spec + sign-off.** (No code.)
2. **S2 — oracle token-lock + implement.** Capture the five keywords' token bytes/widths
   black-box (`basic_probe_str_fn.py` token half + a `kwtable`/equate collision check), add
   the `kwtable.inc` entries + `sysvars.inc` equates, then the three dispatch hooks
   (`str_func_ff` cases for Group A; the `str_eval` branch for `STRING$`; the `ev_f` branch
   for `INSTR`) + the five handlers in `str-engine.asm` (Group A reusing the `detok_*16`→
   descriptor variants). Host unit tests (`tests/test_str_fn.py`). Gates: lean byte-identical,
   unit-test green, `make basic-reloc` OK, `repack-boot` PASS.
3. **S3 — acceptance + close-out.** Extend `string-acceptance` (crunch: five keywords
   byte-identical + suffix; execute: five verbs live on the repack machine; oracle:
   `basic_probe_str_fn.py` reference-lock + zerobas==reference across the §5 battery).
   Refresh the shipping `zerobas-main-eu.ips`/`.bps`; add the provenance section
   ([`../basic/PROVENANCE.md`](../basic/PROVENANCE.md) → "Phase 3: string functions", with
   the own-design divergences: `STRMAX` clamp on `SPACE$`/`STRING$`, unsigned-16 `HEX$`/
   `OCT$`, integer-only); update this spec to IMPLEMENTED & SHIPPED, TODO, memory. Full
   standing set green.

Small and self-contained like the compare slice, but with one genuinely new structural
element: two of the five verbs are **single-byte** tokens, so the slice adds `str_eval`
(Group B) and `ev_f` (Group C) hooks in addition to the S4-style `str_func_ff` mirror
(Group A) — all repack-gated, all reusing the existing ring/bridge/formatter machinery.
