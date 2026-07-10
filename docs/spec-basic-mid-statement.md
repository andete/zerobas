<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — BASIC `MID$` statement (a Phase-3 string follow-on slice)

**Status: PROPOSED — S1 (spec + sign-off), awaiting decision on §6.** User-selected
2026-07-10 as the next Phase-3 session item, from the standing string-engine deferral list
([`spec-basic-string-engine.md`](spec-basic-string-engine.md) §1 "Out of scope":
"`MID$` as an assignment *statement*"; [`spec-basic-string-functions.md`](spec-basic-string-functions.md)
§1: "the `MID$` *assignment statement* (needs an lvalue path into a string var)"). This
document is the *how* + *decisions*, same shape as the engine / compare / functions / inkey
specs. **Repack-only**, like the whole string engine — the lean `basic.rom` stays
byte-for-byte unchanged (every byte is gated `IF ROM_BASE < $4000`).

The `MID$` **function** `MID$(A$,n,m)` (read a substring) already shipped in the string
engine. This slice adds the `MID$` **statement** `MID$(A$,n,m)=B$` — the *assignment* form
that **overwrites a substring of A$ in place**. It is the first verb to need an
**lvalue path into the string store** (write back into a variable's slot), and the first
`$FF`-prefixed token to start a **statement** (not just an expression).

## 1. Goal & scope

Add the `MID$` statement so programs that patch a fixed-width string field in place
(`MID$(A$,3,2)="XY"`) work. It sits on the existing string store — the `STRTAB` inline
slots, `str_get_key` — plus the established numeric/string arg parsing; no new RAM
architecture, no floats, no heap.

**In scope (the one statement, both forms):**

| Form | Meaning |
|---|---|
| `MID$(A$,n)=B$` | overwrite A$ from 1-based position `n` with the bytes of B$, up to the end of A$ |
| `MID$(A$,n,m)=B$` | overwrite **at most `m`** bytes of A$ from position `n`, using the bytes of B$ |

- **The length of A$ never changes** — this is an in-place overwrite, not a splice. The
  replaced run is clipped to whatever room remains in A$ (`LEN(A$)-n+1`).
- The RHS `B$` may be any form `str_eval` already evaluates (a `"literal"`, a `$`-var, a
  string function, or a `+` concatenation).
- `n` and the optional `m` bridge back to `eval`, the established IX↔HL numeric pattern.

**Out of scope (deferred, consistent with the engine):**
- **`MID$` on a non-plain-variable lvalue** — a `FIELD`ed var (write into the field
  buffer) or a string **array** element (arrays don't exist yet). Target = a plain
  `$`-suffixed string variable only.
- Floats in `n`/`m`; the real heap+descriptor model; string arrays / `DIM`; `STRMAX`→255
  (all standing engine deferrals). *(Note: `MID$`-statement never grows A$, so `STRMAX`
  is not even in play here — the length is invariant.)*
- Any change to the **lean** build — every byte of this slice is gated `IF ROM_BASE < $4000`.

## 2. Behaviour (the contract)

Semantics come from the **public MSX-BASIC language reference**; the exact edge-case
results are **oracle-confirmed black-box on the Philips VG-8020** in S2/S3 — the values
below are the expected contract, to be *confirmed against the reference*, never assumed.

Let `La = LEN(A$)`, `Lb = LEN(B$)`, `n` = 1-based start.

- **Replaced count** `k = min( (m if given else Lb), Lb, La-n+1 )`. The first `k` bytes of
  B$ overwrite A$ at positions `n .. n+k-1`. A$'s length stays `La`; bytes outside
  `[n, n+k)` are untouched.
- **`MID$(A$,n)=B$`** (no `m`): `k = min(Lb, La-n+1)` — B$ overwrites from `n` up to the end
  of A$; a B$ longer than the remaining room is **truncated** (A$ never grows).
- **`MID$(A$,n,m)=B$`**: `k = min(m, Lb, La-n+1)` — at most `m` bytes, and only as many as B$
  supplies, and never past the end of A$.
- **`B$` empty** (`Lb=0`): `k=0`, A$ unchanged.
- **Range errors** (to oracle-confirm exactly, §5): `n < 1`, `n > La`, and `m < 0` are
  errors on the reference (MSX raises *Illegal function call*). zerobas has **no**
  "illegal function call" in its error vocabulary, so it reports these via the existing
  **`syntax error`** path (`stmt_error`) — a documented **error-wording divergence** (D-3),
  the same convention the string-compare slice used for `type mismatch` (own lowercase
  wording, not MSX's verbatim string).
- **Type errors**: the LHS not a `$`-var, or the RHS not a string, is a `type mismatch`
  (reusing the string engine's D-2 statement-level abort where it applies) or `syntax
  error` — the exact routing oracle-checked and documented in S2.

Example (the canonical case): `A$="HELLO" : MID$(A$,2,3)="XYZ" : PRINT A$` → `HXYZO`
(positions 2-4 overwritten, length still 5).

## 3. Mechanism (the implementation shape)

Two new hooks, both gated `IF ROM_BASE < $4000`:

**(a) Statement dispatch** (`exec_stmt`, [`interp.asm`](../basic/interp.asm)). The `MID$`
statement begins with the **`MID$` function token `$FF $83`** (`PEEK_PREFIX` +
`MIDD_TOKEN`) — the tokeniser crunches `MID$` to `$FF $83` wherever it appears, statement
position included (confirmed black-box in S2). `exec_stmt`'s dispatch chain is all
single-byte `cp TOKEN`; today a leading `$FF` falls through to the `is_letter` test →
`stmt_error`. Add, gated, right before that fallback:

```
    IF ROM_BASE < $4000
                cp      PEEK_PREFIX         ; $FF -> a function token at statement start
                jp      z,ex_mid_stmt       ; only MID$ ($FF $83) is a valid statement here
    ENDIF
```

`ex_mid_stmt` verifies the selector is `MIDD_TOKEN` ($83); any other `$FF xx` at statement
start is a `stmt_error` (no other `$FF` function starts a statement).

**(b) The handler** `ex_mid_stmt` ([`str-engine.asm`](../basic/str-engine.asm), the
reloc-only low region). It parses `MID$ ( A$ , n [, m] ) = B$` reusing the established
idioms — the `str_fn_mid` position/count parse for `( var , n [, m] )`, `var_name_key` /
`var_str_type` (strvar.asm) to resolve the LHS `$`-var, and `str_eval` for the RHS:

1. Past `$FF $83`; expect `(`.
2. Parse the target: `var_str_type` must report a `$`-suffixed string var (else type/syntax
   error); `var_name_key` → its key; `str_get_key` → `HL` = the var's in-place
   `[len][bytes]` descriptor **inside `STRTAB`** (an unset var yields the shared read-only
   `STR_EMPTY`, `La=0` → the `n>La` range error fires before any write, so we never write
   ROM).
3. Expect `,`; `eval` → `n`. Optional `,` + `eval` → `m` (else the "to end" sentinel).
4. Expect `)`, then `=`.
5. `str_eval` the RHS → source descriptor `B$`.
6. Compute `k` (§2), then overwrite `k` bytes of A$ at offset `n-1` from B$'s bytes — a
   short guarded copy, length byte untouched. Validate `1 ≤ n ≤ La` and `m ≥ 0` first.

No temp-ring slot is needed (the result *is* the variable, written in place); the only
subtlety is guarding the cursor/registers across `eval`/`str_eval`, per the existing
discipline.

## 4. Divergences (own-design, documented)

- **D-3 error wording.** Range/type errors report via `syntax error` / `type mismatch`
  (zerobas's existing vocabulary), not MSX's verbatim *Illegal function call* — the same
  own-wording convention as the string-compare slice.
- **Lvalue = plain string variable only.** `FIELD`ed and array targets are deferred (§1).
- **Lean build unchanged.** Every byte gated `IF ROM_BASE < $4000`; the shipping lean
  `basic.rom` stays byte-identical (verified in S3, as with every string slice).
- **No STRMAX interaction.** The statement never grows A$, so unlike SPACE$/STRING$ there is
  no length clamp to document here.

## 5. Oracle & acceptance

Differential vs the **real VG-8020** (reference-lock then zerobas==reference), the standard
string-slice method — plus a Python model of §2 to derive the expected result (never
assumed). Cases (final battery pinned in S2):

- **basic overwrite** — `A$="HELLO":MID$(A$,2,3)="XYZ"` → `HXYZO`.
- **no-m form** — `A$="HELLO":MID$(A$,3)="XY"` → `HEXYO` (overwrites 2 from pos 3).
- **B$ longer than room** — `A$="HELLO":MID$(A$,4)="WXYZ"` → `HELWX` (truncated, len still 5).
- **m shorter than B$** — `A$="HELLO":MID$(A$,1,2)="abcd"` → `abLLO`.
- **B$ empty** — `A$="HELLO":MID$(A$,2)=""` → `HELLO` (unchanged).
- **RHS is an expression** — `A$="HELLO":MID$(A$,2,2)=CHR$(88)+"Q"` → `HXQLO`.
- **range error** — `A$="HI":MID$(A$,5,1)="X"` → an error on both (reference *Illegal
  function call*; zerobas `syntax error`) — asserted as "errors + A$ unchanged", the
  documented D-3 wording divergence.
- **S2 crunch capture** — `mid$(a$,1,2)="xy"` tokenises with a leading `$FF $83` (the same
  MID$ token as the function), locked into the crunch corpus.

**Standing gate.** `make string-acceptance` gains a **sixth half — `MID$`-statement**
(crunch + execute + compare + functions + inkey + **mid-stmt**), regression-locking the
verb like the rest of the engine. The in-RAM overwrite logic (compute `k`, copy) is a clean
candidate for an emulator-free `unit-test` too (it touches no BIOS), complementing the live
oracle half.

## 6. Decisions to sign off (S1 gate)

Recommended answers in **bold**; nothing is coded until these are accepted.

- **D-1 — Scope = the `MID$` statement, both `MID$(A$,n)=B$` and `MID$(A$,n,m)=B$`.** The
  natural companion to the already-shipped MID$ function; atomic. Target = a plain string
  variable (FIELDed/array lvalues deferred).
- **D-2 — In-place overwrite, `LEN(A$)` invariant.** Replaced count
  `k = min(m|Lb, Lb, La-n+1)`; bytes outside the run untouched; empty B$ = no-op. The
  standard MSX MID$-statement contract, oracle-locked.
- **D-3 — Range/type errors via the existing `syntax error` / `type mismatch`** path
  (zerobas has no *Illegal function call*) — a documented own-wording divergence. `n<1`,
  `n>LEN(A$)`, `m<0` all error; A$ left unchanged.
- **D-4 — Statement dispatch via a repack-gated `cp PEEK_PREFIX` in `exec_stmt`**, then a
  `MIDD_TOKEN` ($83) check; other `$FF` at statement start → `syntax error`. Token
  reconfirmed black-box in S2.
- **D-5 — Reuse the existing idioms** — `str_fn_mid`'s position/count parse, `var_name_key`/
  `var_str_type` for the LHS, `str_get_key` for the in-place descriptor, `str_eval` for the
  RHS. No new RAM; no temp-ring slot (written in place).
- **D-6 — Repack-only, lean byte-identical.** Everything gated `IF ROM_BASE < $4000`; ships
  in the merged `zerobas-main-eu.ips`/`.bps`.
- **D-7 — Acceptance = a sixth `MID$`-statement half** of `make string-acceptance`
  (differential vs VG-8020), plus a host `unit-test` for the in-RAM overwrite math.

## 7. Plan (S1 → S3), one item per session

- **S1 (this doc)** — spec + scope + decisions → **sign-off**. No code.
- **S2** — oracle + implement: confirm the `MID$`-statement token black-box; add the
  `exec_stmt` dispatch + `ex_mid_stmt` handler; a host unit-test for the overwrite math;
  confirm the lean `basic.rom` stays byte-identical; first live run on the repack build.
- **S3** — acceptance + close-out: add the `MID$`-statement half to `string_acceptance.py`
  (differential vs VG-8020); provenance in [`../basic/PROVENANCE.md`](../basic/PROVENANCE.md)
  → "Phase 3: MID$ statement"; refresh the merged IPS/BPS; update `TODO.md` + memory; commit.
