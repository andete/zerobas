<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — unparenthesized `PRINT` string comparison (a Phase-3 string follow-on slice)

**Status: IMPLEMENTED & SHIPPED (S1–S3 all done, 2026-07-10/11).** All §4 decisions D-1…D-4
accepted as recommended; scope = all three string leads (§1 table). S2 implemented the
peek-then-reparse dispatch (`relop_peek` + the `exp_strvar`/`exp_maybe_strfn` gates + the
`str_lit_concat_q` generalization), Sonnet-5 on the signed spec, Opus-reviewed; the
PRINT-lead cases fold into `string-acceptance`'s **compare** half (no new half). S3
extended provenance ([`../basic/PROVENANCE.md`](../basic/PROVENANCE.md) → "Phase 3: string
comparison" → the PRINT-lead reroute subsection) and closed the docs/TODO/memory.
Repack-only, lean `basic.rom` byte-identical (pinned sha256 `e21f61fe…`); unit-test 43/43,
string-acceptance PASS (6 halves), diskbasic-acceptance-repack 34/34, audit-citations
clean. This document is the *how* + *decisions*, same shape as the engine / compare /
functions / inkey / mid-statement specs.
**Repack-only**, like the whole string engine — the lean `basic.rom` stays byte-for-byte
unchanged (every byte is gated `IF ROM_BASE < $4000`). User-selected 2026-07-10 as the next
Phase-3 session item, the last named entry on the standing string-engine deferral list
([`spec-basic-string-engine.md`](spec-basic-string-engine.md) §6 D-F residue;
[`spec-basic-string-compare.md`](spec-basic-string-compare.md) S2 deviation (3), and the
string-engine arc's "still deferred: the unparenthesized `PRINT A$<5` form").

The string-**comparison** engine already shipped ([`spec-basic-string-compare.md`](spec-basic-string-compare.md)):
`ev_rel` (`basic/expr.asm`) evaluates all six relational operators on two string operands →
`-1`/`0`, with the D-2 `type mismatch` abort when a string meets a non-string. It works
today wherever a *numeric* expression is evaluated — `IF A$="YES"`, `R=(A$<B$)`,
and crucially **`PRINT (A$="YES")`** (the leading `(` forces the item into the numeric
evaluator, where `ev_rel` runs). This slice removes the one place it does **not** work: the
**bare, unparenthesized** `PRINT` item `PRINT A$<5`, `PRINT A$="YES"`, `PRINT A$<B$`.

## 1. Goal & scope

Make an unparenthesized string comparison work as a top-level `PRINT` item, identical to its
already-working parenthesized form. `PRINT A$="YES"` prints `-1` or `0`; `PRINT A$<5` aborts
the line with `type mismatch` (D-2). No new evaluator behaviour — the comparison result and
the abort are exactly what `ev_rel` / `type_mismatch_error` already produce; this slice only
fixes **PRINT's item dispatch** (`exp_loop`, `basic/print.asm`) so a string operand that is
actually the *left* side of a comparison reaches `eval` instead of being printed.

**In scope — the unparenthesized comparison as a PRINT item, all three string leads:**

| Form | Lead | Result |
|---|---|---|
| `PRINT A$="YES"` , `PRINT A$<B$` , `PRINT A$<="Z"` | `$`-variable | prints `-1` / `0` |
| `PRINT "YES"=A$` , `PRINT "a"<"b"` | string literal | prints `-1` / `0` |
| `PRINT LEFT$(A$,1)="H"` , `PRINT INKEY$="" ` | string function | prints `-1` / `0` |
| `PRINT A$+B$="HELLO"` | concat chain | prints `-1` / `0` |
| `PRINT A$<5` , `PRINT 5>A$`(already ok) | string vs number | **`type mismatch`, line aborts** (D-2) |

The compound operators (`<=` `>=` `<>`) and boolean composition (`NOT`/`AND`/`OR`, e.g.
`PRINT A$="Y" OR A$="y"`) come for free — they are the numeric evaluator's, reached the
instant the item routes to `eval`.

**Out of scope (unchanged, deferred):** floats in `VAL`/`STR$`; the real heap/descriptor
model; string arrays / `DIM`; `STRMAX`→255. After this slice the string-engine deferral list
holds only those four architectural items — every *surface* form is landed.

## 2. Background — why the bare form mis-routes today

`exp_loop` (`basic/print.asm`) classifies each PRINT item by its **first** token and commits
to a whole-item action *before* any relational operator is seen:

- a `$`-suffixed variable → `exp_strvar`: `str_eval` reads `A$`, `print_strval` **prints it**,
  then loops. Back in the loop the cursor sits on `<5` / `="YES"` — `<` is not a PRINT
  separator and `is_letter` fails, so it falls to `exp_num` → `eval` on `<5`, a **syntax
  error** (or worse). Observed symptom: `PRINT A$<5` prints A$'s value *then* errors.
- a string **literal** → `exp_str`: the fast char-by-char path prints the quoted text; a
  trailing relop is left dangling exactly as above (`str_lit_concat_q` today only looks for a
  following `+`).
- a string **function** (`$FF …`, `STRING$`, `INKEY$`) → `exp_maybe_strfn`: `str_eval` +
  `print_strval`, same trailing-relop dangle.

The **parenthesized** form works because a leading `(` makes `is_letter` fail → `exp_num` →
`eval` → `ev_rel`, whose repack-gated string-LHS probe (`str_eval` → `ev_rel_str`) already
handles the whole `A$ = "YES"`. So the fix is *not* in the comparison engine — it is teaching
`exp_loop` to send a string operand that is the LHS of a comparison down the same `eval` path
the parentheses take.

## 3. Mechanism — "evaluate the string once, then peek for a relop"

The clean, low-byte fix reuses `str_eval` as the one true string-subexpression parser rather
than hand-rolling a second look-ahead scanner. All three string leads already call `str_eval`
on success (directly, or — for a plain literal — would need to). The insight: **`str_eval`
advances `HL` past the *entire* leading string sub-expression** (operand + any `+`-concat
chain) and returns its descriptor. So after it succeeds we can simply *peek the next token*:

```
    ; (repack) at a string-leading PRINT item, HL @ operand start
    push hl                 ; remember the operand start
    call str_eval           ; CF=ok; STRPTR->descriptor; HL past the whole string sub-expr
    ...                     ; (existing per-lead success handling)
    call skip_spaces
    ld   a,(hl)
    call relop_peek         ; ZF=1 iff (HL) is a relop token ($EE/$EF/$F0)
    jr   nz, <print it>     ; no relop -> plain PRINT, print_strval as today (NO re-parse)
    pop  hl                 ; relop follows -> restore cursor to the operand START
    jp   exp_num            ; re-drive via eval -> ev_rel -> -1/0 (or D-2 type mismatch)
```

Properties:

- **The comparison engine is untouched.** `exp_num` → `eval` → `ev_rel` re-parses the operand
  from the start and runs the *existing* string-LHS path (`ev_rel_str`, `str_cmp_bits`, the
  compound-form merge, the D-2 `TMISMATCH` set). The `exp_num` fall-through already checks
  `TMISMATCH` and jumps to `type_mismatch_error` (print.asm:130) — so `PRINT A$<5` aborts the
  line **with nothing printed**, because the abort happens *before* any print.
- **Plain `PRINT A$` / `PRINT "x"` / `PRINT CHR$(65)` are unchanged and pay no re-parse.**
  When no relop follows, we print the descriptor `str_eval` already produced — the exact
  bytes and control flow of today. Only the (rarer) comparison case re-parses, once.
- **One shared choke point.** `exp_strvar`, `exp_maybe_strfn` (both `str_eval`+`print_strval`)
  route through the same `relop_peek` gate. The plain-literal fast path needs the routing
  decision lifted one level: generalize `str_lit_concat_q` — which already scans to the
  closing quote + `skip_spaces` — to report "**`+` or a relop follows**", and on either route
  the literal through the `str_eval` path (so a literal LHS of a comparison gets the peek too).
  A plain literal (no `+`, no relop) keeps the fast un-clamped char path, so a literal longer
  than `STRMAX` still prints in full (the S5 property is preserved).

### 3a. `relop_peek` — the one new primitive

The relop tokens are contiguous: `GT_TOKEN $EE`, `EQ_TOKEN $EF`, `LT_TOKEN $F0`
(`basic/sysvars.inc`). `relop_peek` is a 6-byte range test (`A-$EE < 3` → ZF via a
`cp $EE / jr c / cp $F1 / ccf`-style test), living beside the comparator in
`basic/str-engine.asm` (low region, repack-only). It does **not** consume; the caller decides.
(`relop_bit` in expr.asm already maps a relop token → bit, but it is IX-based and consumes via
the ev_rel state machine; a tiny non-consuming HL-side peek is cleaner than bending it.)

### 3b. No new token, no tokeniser change

`A$="YES"`, `A$<5`, `"a"<"b"`, `LEFT$(A$,1)="H"` all already **crunch** correctly today (the
relop tokens and string keywords are established). This slice is entirely inside PRINT's
runtime dispatch — no kwtable / match_kw / detok change, so LIST round-trips are unaffected.

### 3c. Cursor discipline

`exp_loop` is HL-based; `eval` bridges HL→IX at entry and HL→out (`expr.asm` eval:35). The
`push hl` before `str_eval` / `pop hl` on the relop branch restores the *operand start* so
`eval` re-drives the full `A$ = "YES"`. On the print branch the `push`ed HL is dropped
(consumed by the normal `pop`/loop). Net stack effect balanced on both branches — to be
verified in S2 with the unit harness and a boot smoke.

## 4. Decisions (recommendations for sign-off)

- **D-1 — the peek-then-reparse mechanism (§3), not a look-ahead-only scanner.**
  *Recommend: accept.* Reuses `str_eval` as the parser (handles var/literal/function/concat
  uniformly), re-parses only in the comparison case, and leaves the plain-print path
  byte-for-byte in behaviour. The alternative (a standalone scanner that skips a whole string
  sub-expression to peek for a relop) would duplicate `str_eval`'s literal/function/paren
  handling — more bytes, a second thing to keep in sync.

- **D-2 — `PRINT A$<5` aborts the line with `type mismatch`, printing nothing.**
  *Recommend: accept (inherited).* This is the existing D-2 contract; because the comparison
  is the whole PRINT item and the abort fires in `exp_num` before `print_number`, nothing is
  emitted — matching MSX's observable behaviour (the item that errors prints nothing). The
  one documented D-2 divergence stands: items *after* a comparison on the same physical line
  do not run (the line aborts).

- **D-3 — scope = the top-level PRINT item lead only (§1 table).** *Recommend: accept.* A
  comparison nested *inside* another PRINT expression already reaches `eval` (e.g.
  `PRINT 1+(A$="Y")`); this slice only adds the case where the comparison **is** the item and
  its LHS is a string. `PRINT A$;B$<C$` — comparison after `;` — is a fresh item and gets the
  same treatment (each `;`/`,`-separated item re-enters `exp_loop`).

- **D-4 — oracle-lock the printed results and the abort black-box on the VG-8020**, not
  assumed. *Recommend: accept.* S2 captures `PRINT A$="YES"` → ` -1 `, `PRINT A$="no"` → ` 0 `,
  ordering, compound forms, and the `A$<5` abort (line aborts, nothing printed) on the
  reference machine and asserts zerobas == reference. Reuses `basic_probe_str_cmp.py`'s
  reference-lock discipline.

## 5. Files touched (all repack-gated)

| File | Change |
|---|---|
| `basic/print.asm` | `exp_strvar`: `push hl` before `str_eval`, `relop_peek` gate before `print_strval` → `pop hl`/`jp exp_num` on a relop. Generalize `str_lit_concat_q` → route a literal on `+` **or** relop. |
| `basic/str-engine.asm` | new `relop_peek` (non-consuming range test); `exp_maybe_strfn`: same `relop_peek` gate before its `print_strval`. |
| `probes/basic/basic_probe_str_cmp.py` | add unparenthesized `PRINT`-lead cases (var/literal/function) + the `A$<5` abort, reference-locked. |
| `tests/test_str_compare.py` | host cases for the new dispatch (where BIOS-independent). |
| `basic/PROVENANCE.md`, this spec, `TODO.md`, memory | S3 close-out. |

No `basic/sysvars.inc` change (relop equates exist). No new RAM (`TMISMATCH` already owns its
byte). Lean `basic.rom` unchanged by construction.

## 6. Test plan / acceptance

- **Standing gates unchanged & green:** lean `basic.rom` byte-identical (pinned sha256
  `e21f61fe…`); `unit-test`; `diskbasic-acceptance-repack` 34/34; `repack-boot` PASS;
  `audit-citations` clean; `$8000` overflow guard.
- **`make string-acceptance`** — the **COMPARE** half (`basic_probe_str_cmp.py`) grows the
  unparenthesized PRINT-lead cases. The gate already asserts reference-lock + zerobas ==
  reference; the new cases fold in without a new half.
- **Regression watch (from the S5 lesson):** re-run the full string-acceptance EXECUTE half —
  the change is in shared PRINT dispatch, so verify plain `PRINT A$`, `PRINT "lit"`,
  `PRINT CHR$(65)`, `PRINT A$+B$`, and a literal longer than `STRMAX` all still print
  unchanged. Diskbasic-acceptance-repack guards the shared parse for disk PRINT too.

## 7. Session plan

- **S1 — spec + sign-off (this document). No code.** ← *you are here.*
- **S2 — oracle + implement.** Reference-lock the PRINT-lead cases on the VG-8020; implement
  `relop_peek` + the two `exp_loop` gates + the `str_lit_concat_q` generalization; host tests;
  re-run all gates. (Sonnet-5 dispatch on the signed spec, Opus-reviewed — per the model-split
  working rule.)
- **S3 — acceptance + close-out.** Fold the new cases into `string-acceptance`; PROVENANCE
  "Phase 3: string comparison" note extended (the PRINT-lead dispatch reroute); spec → SHIPPED;
  TODO + memory updated; refresh `zerobas-main-eu.ips`/`.bps`.

## 8. Open questions for sign-off

1. **Accept the four decisions D-1…D-4 as recommended?**
2. **Scope check:** is the §1 table the right surface, or do you want any form explicitly
   excluded (e.g. leave string-function leads like `PRINT LEFT$(A$,1)="H"` out of this slice
   and cover only var/literal leads)?
3. **Model dispatch:** S2 implementation to Sonnet-5 on the signed spec (Opus review), same as
   the compare/mid-statement slices — confirm?
