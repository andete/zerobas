<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — BASIC string comparison — a Phase-3 follow-on slice

**Status: SIGNED OFF — ready to implement (S2).** The D-F item deferred from the
string-engine arc ([`spec-basic-string-engine.md`](spec-basic-string-engine.md) §6 D-F:
"string comparison DEFERRED … join the deferred verbs in a follow-on Phase-3 slice").
This is the *how* + *decisions*; same shape as the engine spec. **Repack-only**, like the
whole string engine. All four decisions settled (§6): all six operators; **a real
`type mismatch` error that aborts the line, raised at the statement boundary** (D-2);
oracle-locked unsigned-byte semantics; LHS snapshot reuses the ring.

## 1. Goal & scope

Make string operands comparable with the relational operators so conditions like
`IF A$="YES" THEN …` and `IF LEFT$(N$,1)<"M" THEN …` work. Today the relational layer
(`ev_rel`, [`basic/expr.asm`](../basic/expr.asm)) compares only **numeric** operands; a
relational applied to a string operand is unhandled.

**In scope:**
- The six relational operators on two string operands: `=`, `<>`, `<`, `>`, `<=`, `>=`.
- Both operands may be any string form the engine already evaluates via `str_eval`:
  a `"literal"`, a `$`-suffixed variable, a string function (`LEFT$`/`RIGHT$`/`MID$`/
  `CHR$`/`STR$`), or a `+` concatenation of those (`A$+B$ = C$`).
- The result is numeric **-1 (true) / 0 (false)** — identical to the numeric relational
  result — so it composes with `NOT`/`AND`/`OR`/`XOR` above it (`IF A$="Y" AND B=1`) and
  can be assigned (`R=(A$=B$)`), exactly like a numeric comparison.
- Reached wherever an expression is evaluated: `IF … THEN/GOTO`, a numeric RHS, `PRINT`
  of a comparison, etc. — because the hook lives in the shared relational layer.

**Out of scope (deferred, consistent with the engine):**
- `INSTR`, `HEX$`, `OCT$`, `STRING$`, `SPACE$`, `INKEY$` (separate follow-on verbs).
- Floating-point operands, the `MID$` statement, string arrays / `DIM`.
- Any change to the **lean** build — it has no string engine, and its `ev_rel` stays
  byte-for-byte unchanged (the whole feature is gated `IF ROM_BASE < $4000`).

## 2. Behaviour (the contract)

String comparison is a **byte-by-byte unsigned** compare, left to right:

1. Compare corresponding bytes by unsigned value (raw byte, ASCII). At the first
   differing position, the string with the smaller byte is **less**.
2. If one string is a prefix of the other (all shared bytes equal), the **shorter**
   string is less.
3. Strings are **equal** iff they have the same length and all bytes match.
4. Comparison is **case-sensitive** (`"A"` < `"a"`, since `$41 < $61`).

This is the standard MSX-BASIC string-ordering contract (public language reference). It
must be **oracle-captured black-box** on the Philips VG-8020 before ship (§5, the S2
probe) — the values above are the expected result, not an assumed encoding.

Note the distinction from the numeric path: `cmp16_bits` is a **signed 16-bit** compare;
string comparison is **unsigned byte** compare. The reused piece is the *relation-bit
model* (below), not `cmp16_bits` itself.

## 3. Architecture — reuse the relation-bit spine

`ev_rel` already factors a comparison into three clean steps that the string path
reuses verbatim:

- `relop_bit` maps a relop token to a **requested-relation bit**: `<`→1, `=`→2, `>`→4;
  a compound form (`<=`/`>=`/`<>`) arrives as two relop tokens and **merges** to the OR
  of their bits (`<=` → 1|2 = 3, `<>` → 1|4 = 5, `>=` → 4|2 = 6).
- an **actual-relation bit** (1/2/4) is produced from the two operands (today by
  `cmp16_bits`).
- the result is `actual AND requested` → non-zero ⇒ **-1**, zero ⇒ **0**.

So string comparison needs to change exactly **one** thing: substitute a string
comparator that yields the actual 1/2/4 bit. Everything else — the six operators, the
compound-form merge, the -1/0 convention, the boolean composition above — is inherited.

### 3a. The hook (repack-gated, in `ev_rel`)

`ev_rel` is `IX`-based; `str_eval` is `HL`-based (returning a `[len][bytes]` descriptor,
`VALTYP=1`, `CF`=set on a recognised string operand, HL advanced). The bridge is the
**existing** IX↔HL pattern used by `ev_ff_cvi`/`ev_str_arg` ([`basic/expr.asm`](../basic/expr.asm)).

At the top of `ev_rel` (repack build only), before committing to the numeric `ev_e`:

1. **Probe the LHS** for a string operand — bridge IX→HL and try `str_eval`, saving the
   cursor so a non-string LHS can be re-parsed numerically. `CF` set ⇒ LHS is a string:
   enter the string-compare path. `CF` clear ⇒ restore the cursor and fall through to the
   unchanged numeric `ev_rel` body.
2. **Snapshot the LHS** into a stable compare temp (dup its descriptor — the same
   "dup-then-operate" discipline the substring verbs use — so evaluating the RHS can't
   clobber it via STRSCR / the ring).
3. Read the relop token(s) with `relop_bit` (+ the compound merge) exactly as the numeric
   path does — reused unchanged.
4. **Evaluate the RHS** via `str_eval`. If the RHS is **not** a string, that is a
   type-mismatch (see D-2).
5. **Compare** the two descriptors bytewise-unsigned → actual bit 1/2/4, then join the
   numeric path at `and c` → return DE = -1/0.

The numeric-vs-string case `5 < A$` (numeric LHS, string RHS) is caught symmetrically:
the LHS probe finds no string, the numeric body runs `ev_e` on the RHS, which is not a
number — handled by D-2.

### 3c. Type-mismatch reporting (D-2 realized — statement-level abort)

zerobas has **no mid-expression abort**: every existing evaluator error (bad factor
`ev_f_err`, division-by-zero, function error) sets `ERRMARK` and yields 0, letting the
line continue — there is no longjmp to the prompt from inside `ev_rel`. Rather than add a
saved-SP unwind to the **shared** run/REPL driver (which the lean build uses, so it would
threaten the lean-byte-identical invariant), the type mismatch is reported at the
**statement boundary**, entirely repack-gated:

1. When the comparator sees a string on one side and a non-string on the other, it sets
   `ERRMARK` **plus a distinct type-mismatch marker** (a new sentinel byte / RAM flag,
   `TMISMATCH`, own free page-3 RAM) and yields 0 (false), returning normally.
2. Repack-gated, the expression-*statement* drivers that own a condition — first `ex_if`
   (both `THEN` and `GOTO` forms), and the numeric-assignment / `PRINT`-item paths — check
   the marker immediately after their `eval`/`ev_rel` call and, if set, `jp` to a new
   `type_mismatch_error` printer.
3. `type_mismatch_error` mirrors `stmt_error` (zero `PRDEST`, set `ERRMARK`, print the
   message, `ret` to the prompt — a clean line abort at statement level). The message
   follows zerobas's own lowercase convention (`"type mismatch"`, like `"syntax error"` /
   `"load error"` — **not** MSX's `?Type mismatch Error` verbatim string, which is
   reference wording we don't copy).

For the realistic uses (`IF A$<5 THEN…`, `R=(A$<5)`) the comparison is the first thing
evaluated, so the line aborts with the message before any clause runs — observably
identical to MSX. The only difference from a true mid-expression unwind is that a
comparison buried after other side-effecting items on the same physical line would let
those items run first; loader stubs never write that, and it is documented as the one
own-design divergence.

### 3b. Placement & gating

- New comparator + the LHS-snapshot helper live in
  [`basic/str-engine.asm`](../basic/str-engine.asm) (repack low region), alongside the
  ring/verb code, keeping page 1 lean.
- The `ev_rel` hook is a near-zero-byte `IF ROM_BASE < $4000` branch — the lean `ev_rel`
  is byte-identical.
- Snapshot storage: **reuse a temp-ring slot** for the LHS and STRSCR/another slot for
  the RHS (N=3 covers LHS + RHS + headroom); no new RAM if the ring suffices, else a
  dedicated `CMPBUF` (STRMAX+1 B) — decided at implementation, low stakes (D-4).

## 4. Tokens — nothing new

The relop tokens are already sourced and crunched: `=`→`$EF` (`EQ_TOKEN`), `<`→`$F0`
(`LT_TOKEN`), `>`→`$EE` (`GT_TOKEN`); compound forms are two tokens (existing behaviour,
already byte-identical to the VG-8020 via `basic_probe_crunch.py`). **No new token byte,
no `kwtable` change, no tokeniser change** — `A$="YES"` already crunches correctly today;
only the *evaluation* of the crunched relational is added. This keeps the whole feature
inside the evaluator.

## 5. Validation & oracle

- **Oracle (S2, black-box, no disassembly).** A new probe `basic_probe_str_cmp.py`
  captures the reference VG-8020's string-ordering result for a battery of pairs (equal,
  prefix-shorter, case, first-diff-byte, empty string, all six operators) by evaluating
  `A$=B$` etc. into a numeric variable and reading it back — asserting -1/0 matches the
  §2 contract on the reference, then asserting zerobas matches the reference.
- **Execute (gate).** Extend the `string-acceptance` EXECUTE half
  ([`basic_probe_string.py`](../probes/basic/basic_probe_string.py)) with comparison
  cases printed live on the repack machine (`PRINT (A$="YES")`, `IF`-driven branch
  outcomes).
- **Crunch (gate).** `A$="YES"`, `A$<>B$`, `A$<=B$`, etc. already crunch byte-identical
  (relop tokens unchanged) — add them to the `--zb-machine` corpus as a regression guard.
- **Unit tests.** Add `tests/test_str_compare.py` (host Z80) covering the comparator's
  1/2/4 output for the §2 cases + the compound-form merge + type-mismatch.
- **Gates that must stay green:** lean `basic.rom` byte-identical; unit-test (current 40
  + new); `string-acceptance` PASS (crunch + execute, now incl. comparison);
  `diskbasic-acceptance-repack` 34/34 (shared `ev_rel`/`eval` path unregressed);
  `repack-boot` PASS; audit-citations clean.

## 6. Decisions (all SETTLED at sign-off)

- **D-1 — operator set. ✅ All six** (`=` `<>` `<` `>` `<=` `>=`). They fall out of the
  relation-bit merge at ~zero extra cost.
- **D-2 — type mismatch (`A$ < 5`, `5 < A$`, string-vs-number). ✅ A real `type mismatch`
  error that aborts the line**, realized at the **statement boundary** (not a
  mid-expression unwind) — see §3c. Chosen over the cheaper ERRMARK-and-continue for
  MSX faithfulness, and over a true saved-SP longjmp because that would touch the shared
  lean run driver and risk the byte-identical invariant for no observable gain in
  loader-stub code. Message is zerobas's own lowercase `"type mismatch"`.
- **D-3 — comparison semantics. ✅ Unsigned byte-wise, shorter-is-less, case-sensitive,
  -1/0** (§2) — the reference contract, oracle-locked black-box in S2 (not assumed).
- **D-4 — LHS snapshot storage. ✅ Reuse a temp-ring slot** (no new RAM); fall back to a
  dedicated `CMPBUF` only if an aliasing hazard forces it (implementation-time call).

## 7. Session plan (slices, each commits at its gate)

1. **S1 — this spec + sign-off.** (No code.)
2. **S2 — oracle + implement.** Capture the ordering contract black-box
   (`basic_probe_str_cmp.py`), then add the `ev_rel` hook + the unsigned-byte comparator +
   LHS snapshot in `str-engine.asm`; wire the D-2 statement-level type-mismatch (the
   `TMISMATCH` marker set by the comparator + the repack-gated post-`eval` check in `ex_if`
   / the numeric-assignment / `PRINT`-item drivers + the `type_mismatch_error` printer).
   Host unit tests. Gates: lean byte-identical, unit-test green, `basic-reloc` OK,
   `repack-boot` PASS.
3. **S3 — acceptance + close-out.** Extend `string-acceptance` (execute + crunch) with
   comparison cases; refresh the shipping `zerobas-main-eu.ips`/`.bps`; provenance section
   in [`../basic/PROVENANCE.md`](../basic/PROVENANCE.md); update the engine spec's D-F
   pointer, TODO, memory. Gates: full standing set green.

Small, self-contained: it adds no token and no new architecture — it substitutes one
comparator into an existing three-step relational spine, entirely inside the repack
evaluator.
