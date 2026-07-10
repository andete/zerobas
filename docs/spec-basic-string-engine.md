<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — BASIC string engine (core) — the first Phase-3 feature

**Status: DRAFT — decisions RESOLVED, for final sign-off (2026-07-10). No code until
signed off.** All six decisions settled (§6): temp ring N=3; core verb set; **`STRMAX`=64**
(the 255-faithful option overflows page-3 RAM by ~2 KB — see §5a); repack-only + gated
repack machine; integer-only `VAL`; **string comparison deferred**.
First feature of Phase 3, consuming the ~5.5 KB reclaimed by the C-BIOS repack arc
([`spec-cbios-repack-tooling.md`](spec-cbios-repack-tooling.md)). This is the *how* +
*decisions*; it follows the same shape as the repack spec.

## 1. Goal & scope

Turn zerobas's **minimal string-VALUE layer** (`basic/strvar.asm`: literals + `$`-var
assign + PRINT) into a real **string expression engine**: string variables that
compose with `+` concatenation and the core string functions. Scoped to what
game-loader `.BAS` stubs and everyday one-liners actually use — not the full MSX
string library in one arc.

**In scope (the "core"):**
- **`+` concatenation** of string operands in an expression.
- **`LEN`** (string → number), **`ASC`** (string → number), **`VAL`** (string → number).
- **`CHR$`** (number → string), **`STR$`** (number → string).
- **`LEFT$` / `RIGHT$` / `MID$`** (3-arg function form) — substring extraction.

**Out of scope (deferred to a follow-on Phase-3 slice):**
**string comparison** (`A$=B$`, `<>`, `<`, `>`) — deferred per D-F; `INSTR`, `HEX$`,
`OCT$`, `STRING$`, `SPACE$`, `INKEY$`, `MID$` as an assignment *statement*, the
`MKS$`/`MKD$` float siblings, and anything requiring floating point. `INPUT$`/`MKI$`/`CVI`
already exist and are untouched.

**Non-goals:** a real MSX string heap with garbage collection (the fixed-slot store
stays — see §3); floating point; raising the game-loader charter beyond "run the
loader stubs + everyday string one-liners."

## 2. Background — what already exists (do not rebuild)

- **String value** = a `[len:1][bytes…]` descriptor. `STRPTR` → descriptor,
  `VALTYP` = 1 flags "current operand is a string" ([`basic/sysvars.inc`](../basic/sysvars.inc):300).
- **`STRSCR`** ($E360, 33 B = `[len][bytes:STRMAX]`) — the **single** scratch that
  currently holds one computed string value (a literal, `MKI$`, `INPUT$`).
- **Variable store** `STRTAB` ($E240) — a **fixed-slot** table, `STRSLOTS`=8 ×
  `STRENTSZ`=35, `STRMAX`=32 chars/var. `str_find`/`str_get_key`/`str_set_key`
  ([`basic/vars.asm`](../basic/vars.asm):207) look up / clamp-copy; no heap, no growth.
- **`str_eval`** ([`basic/strvar.asm`](../basic/strvar.asm):30) recognises a string
  operand (literal / `$`-var / `INPUT$` / `MKI$` / FIELDed) and sets `STRPTR`+`VALTYP`.
- **`print_strval`** emits a descriptor via `pchar`.
- **Evaluator** ([`basic/expr.asm`](../basic/expr.asm)) is recursive-descent
  (`expr := term {(+|-) term}`, numeric only today); operators are tokens
  (`+`=$F1). String operands appear only in narrow factor slots (e.g. the `CVI`
  argument bridges IX→`str_eval`→IX).
- **Tokeniser** crunches function keywords to `$FF <selector>` (`PEEK_PREFIX`=$FF),
  selector values **oracle-locked to the VG-8020** (`MKI$`=$FF$AE, `CVI`=$FF$A8;
  `basic/interp.asm` token table). Cross-checked vs MSX2 TH Table 2.20.

## 3. Design — the three pieces

### 3a. Temporary-string management (THE crux)

Concat and the `…$` functions each produce a **new** string value. A single `STRSCR`
cannot survive a nested expression (`LEFT$(A$+B$,3)` needs the `A$+B$` temp alive
while `LEFT$` runs). Real MSX BASIC solves this with a temp-descriptor pool + a heap
with GC. zerobas's fixed-slot world lets us do far less:

**Resolved (own-design): a small fixed temp-string ring, N=3, `STRMAX`=64.** A RAM area
holding **3** temp descriptors of `STRMAX`=64 bytes each, used round-robin. A routine
`str_alloc_temp` returns the next temp slot's descriptor address; string-producing ops
write their result there and set `STRPTR`. N=3 covers realistic game-loader expressions
(a binary concat has ≤2 live operands + 1 result). Depth beyond N reuses the oldest
slot — documented own-design truncation of expression depth, mirroring the existing
"truncate at `STRMAX`" philosophy. `STRSCR` folds into this pool (it becomes temp[0]).

*Rejected:* a real heap+GC — large, and unjustified for the charter. *Rejected:* one
temp — fails on any nested/chained string op.

### 3b. String-expression evaluation

Add a **string-expression** path invoked when the context wants a string (LET into a
`$`-var, PRINT operand, a string function argument). It mirrors the numeric descent but
its only operator is `+` (concat); its operands are: literal, `$`-var, string function
call, `(` string-expr `)`. Cleanest integration: a dedicated `str_expr` entry (extends
today's `str_eval`) so the numeric `ev_x`/`ev_t`/`ev_f` chain is untouched; callers pick
the string path via `VALTYP`/`var_str_type` exactly as they do now. Function arguments
that are numeric (the `n` in `LEFT$(a$,n)`) bridge back to `eval` (the `CVI`/`MKI$`
IX↔HL bridge is the established pattern).

### 3c. Function + operator set

| Verb | Form | Sig | Impl sketch |
|---|---|---|---|
| `+` | `a$ + b$` | (s,s)→s | copy a$ then b$ into a temp; length clamp per §6 D-C |
| `LEN` | `LEN(a$)` | s→n | read descriptor len byte |
| `ASC` | `ASC(a$)` | s→n | first byte (empty → error, MSX: Illegal function call) |
| `CHR$` | `CHR$(n)` | n→s | 1-byte temp descriptor |
| `LEFT$` | `LEFT$(a$,n)` | (s,n)→s | copy min(n,len) from head |
| `RIGHT$` | `RIGHT$(a$,n)` | (s,n)→s | copy min(n,len) from tail |
| `MID$` | `MID$(a$,p[,n])` | (s,n[,n])→s | substring from p (1-based), len n (or to end) |
| `STR$` | `STR$(n)` | n→s | reuse `print.asm` number formatter into a temp |
| `VAL` | `VAL(a$)` | s→n | parse leading signed integer (reuse the tokeniser/eval number path) |

`STR$` reuses the existing decimal formatter (currently emitting via `pchar`/`NUMBUF`);
factor it to also target a descriptor. `VAL` parses a leading optional-sign decimal,
integer-only (floats deferred; documented divergence, consistent with the whole engine
being integer-only).

## 4. Clean-room / provenance

- **Token selector values** for every new keyword (`LEN`/`LEFT$`/`RIGHT$`/`MID$`/`CHR$`/
  `ASC`/`STR$`/`VAL`) are **oracle-locked**: captured black-box from the VG-8020 crunch
  via `probes/basic/basic_probe_crunch.py` and cross-checked against MSX2 TH Table 2.20.
  Never read from a reference ROM disassembly ([[no-reference-rom-disasm]]).
- **Semantics** (1-based `MID$`, `LEFT$` clamps, `ASC ""` = error, `VAL` leading-parse)
  come from the **public MSX-BASIC language reference**.
- **Layout** (temp ring, descriptor, STRMAX clamp) is **own-design**, quarantined in
  `basic/PROVENANCE.md` like the existing string layer.
- Divergences (fixed STRMAX clamp, integer-only `VAL`, temp-depth N) are documented
  own-design descopes, not reference behaviour.

## 5. Space & build — repack-only, and it forces the repack gate

The lean 16 KB `basic.rom` is **byte-full** ($ = $8000): the string engine **cannot**
fit there. So every byte of it lands behind **`IF ROM_BASE < $4000`** (the repack-only
gate, enforced by the overflow guard added in commit 3fd1a2c). Consequences:

1. **The lean build stays exactly as today** — game-loader BASIC, no strings, universal,
   no external deps. Byte-identical `basic.rom` (regression-safe).
2. **The repack build gains the engine** — assembled into the reclaimed `$2812–$3FFF`
   low region (the string engine is a natural tenant; place as whole includes around the
   tape hole `$3A72–$3C42`, per D5).
3. **This is the first feature that requires the repack**, so it must **stand up a gated
   repack openMSX machine** (EU merged main ROM) and run the new string probes there —
   today's acceptance gates run only on the lean stack. That machine + a
   `string-acceptance` gate are part of this arc's deliverable, not a follow-on.

Rough size estimate: ~1.3–1.6 KB (evaluator + temp ring + 8 verbs + tokens) against a
~5.5 KB budget — comfortable, leaving room for the deferred functions later.

### 5a. RAM budget — the binding constraint on string length (why STRMAX=64)

ROM space is *not* the limiter for this feature; **page-3 RAM is.** The string store
`STRTAB` sits at $E240, and the first committed RAM above it is the cassette/file
512-byte buffers at $E560 (`CAS_WBUF`/`FSECTOR_BUF`), then `FCH_CTX` channel blocks to
~$EE64, then C-BIOS sysvars from ~$F380. So there is exactly **800 B of contiguous free
RAM** for `STRTAB` + the temp ring:

| `STRMAX` | 8 vars + 3 temps | Fit in 800 B |
|---|---|---|
| 32 (today) | 385 B | ✓ |
| **64 (chosen)** | **737 B** | **✓ (63 B spare)** |
| 128 | 1441 B | ✗ over by 641 B |
| 255 (MSX-faithful) | 2838 B | ✗ **over by ~2 KB** |

`STRMAX`=64 is the largest that fits without moving buffers. **255 is deferred** to an
optional future RAM re-architecture (relocate/shrink the file-channel + cassette buffers
to free ~2 KB contiguous — a sub-project that touches `fat.asm` + cassette code and
re-runs the disk + tape gates). Not worth bolting onto the first string feature.

## 6. Decisions — RESOLVED (2026-07-10)

- **D-A — temp model → small fixed temp ring, N=3.** (§3a.) Own-design; no heap/GC.
- **D-B — core verb set = the §3c table** (concat + LEN/ASC/CHR$/LEFT$/RIGHT$/MID$/STR$/
  VAL); INSTR/HEX$/OCT$/STRING$/SPACE$/INKEY$/`MID$`-statement deferred.
- **D-C — `STRMAX` = 64** (variables *and* temps). The MSX-faithful 255 overflows the 800 B
  of free page-3 RAM by ~2 KB (§5a); 64 is the largest clean fit (737 B). 255 is deferred
  to an optional RAM re-architecture sub-project. *(User-decided 2026-07-10 after the RAM
  check; the initial 255 pick was retracted once the map showed it doesn't fit.)*
- **D-D — repack-only + build the gated repack machine** (§5). The first Phase-3 feature
  carries the repack-becomes-shipping-target infrastructure.
- **D-E — `VAL` is integer-only** (leading signed decimal), consistent with the
  integer-only numeric core; float `VAL` waits for floating point.
- **D-F — string comparison DEFERRED.** `A$=B$`/`<>`/`<`/`>` join the deferred verbs in a
  later slice; this arc ships concat + the §3c functions only. *(User-decided 2026-07-10.)*

## 7. Risks & non-goals

- **Risk: temp-ring depth.** A pathological deep string expression silently reuses a temp
  and corrupts an operand. Mitigation: N=3 covers the grammar's real depth; document the
  limit; a probe asserts a 2-level nest (`LEFT$(A$+B$,n)`) is correct.
- **Risk: token-value drift.** A guessed selector byte would mis-crunch vs real MSX.
  Mitigation: the §4 oracle capture is a hard gate before any handler is written.
- **Risk: `STR$`/`VAL` coupling.** Factoring the number formatter/parser to hit a
  descriptor could perturb the existing PRINT/eval paths. Mitigation: keep the current
  entry points byte-identical (lean build unchanged proves it); add descriptor variants.
- **Non-goal:** heap/GC, floats, the deferred verbs, charter raise beyond game-loader +
  everyday string use.

## 8. Session plan (slices, each commits at its gate)

1. **S1 — this spec + sign-off.**
2. **S2 — token oracle + tokeniser.** Capture the 8 selector values (probe), add the
   crunch table entries, gate `basic_probe_crunch.py`. No handlers yet.
3. **S3 — temp ring + `str_expr` + `+` concat.** The evaluator spine; prove `A$+B$+C$`.
4. **S4 — the verbs.** LEN/ASC/CHR$/LEFT$/RIGHT$/MID$/STR$/VAL (+ D-F compare if taken).
5. **S5 — repack machine + `string-acceptance` gate** (D-D): install the EU repack
   machine, port the string probes onto it, wire the gate.
6. **S6 — close-out:** provenance (`basic/PROVENANCE.md` entries), docs harvest, memory +
   TODO update.

**Gates (must stay green):** lean `basic.rom` byte-identical (regression-safe by
construction); unit-test 38/38; bdos-acceptance 12/12; diskbasic-acceptance 34/34;
bdos-cbios-selfcheck 10/10; the `$8000` overflow guard stays green in the lean build;
+ new: `basic_probe_crunch.py` covers the 8 keywords, `string-acceptance` on the repack
machine.
