<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — BASIC string engine (core) — the first Phase-3 feature

**Status: SIGNED OFF — IN PROGRESS. S1–S3 done (2026-07-10); S4 (verbs) next.** All six
decisions settled (§6): temp ring N=3; core verb set; **`STRMAX`=64** (the 255-faithful
option overflows page-3 RAM by ~2 KB — see §5a); repack-only + gated repack machine;
integer-only `VAL`; **string comparison deferred**. S3 delivered the re-layout + `+` concat
spine (see §8); the 8 verb tokens are already crunched/detokenised, only the handlers remain.
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
"truncate at `STRMAX`" philosophy.

**S3 implementation deviation (2026-07-10):** `STRSCR` was kept **separate** from the
ring rather than folded into temp[0]. Folding would require `str_eval`'s literal/MKI$/
INPUT$ scratch to participate in ring allocation (so a literal operand can't share
temp[0] with a live concat accumulator) — that means gating `str_eval`'s body per
build and re-introduces the aliasing hazard the ring exists to remove. Keeping `STRSCR`
its own 65 B cell (above the widened store) leaves `str_eval` **byte-identical** for the
lean build and makes a `+` chain use exactly **one** ring slot (the accumulator; each
operand transits `STRSCR`/its var slot, never the ring). Cost: +65 B RAM (see §5a) —
still inside the 800 B wall. The ring's 3 slots are headroom for S4's nested function
temps (`LEFT$(A$+B$,n)`), which is where multiple simultaneously-live temps actually arise.

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

- **Token selector values** for every new keyword are **oracle-locked** (captured 2026-07-10,
  black-box VG-8020 crunch, [`probes/basic/basic_probe_str_tokens.py`](../probes/basic/basic_probe_str_tokens.py)
  reusing the crunch-probe harness) **and** cross-checked against the sourced MSX2 TH Table 2.20 contiguous function
  table (`…LEN $92, STR$ $93, VAL $94…`, already in `basic/sysvars.inc`). Never a reference
  ROM disassembly ([[no-reference-rom-disasm]]). Observed `$FF`-suffixes:

  | `LEN` | `LEFT$` | `RIGHT$` | `MID$` | `STR$` | `VAL` | `ASC` | `CHR$` |
  |---|---|---|---|---|---|---|---|
  | `92` | `81` | `82` | `83` | `93` | `94` | `95` | `96` |

  Note: zerobas today emits these keywords as **verbatim ASCII** (it never tokenised them;
  `LEN=` relied on the host test injecting `FF 92`), so adding the entries is purely
  additive — the lean build is unaffected (entries gated out), and nothing regresses.
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

**As built (S3, separate `STRSCR` — §3a deviation):** `STRTAB` 536 + `STRSCR` 65 + ring
3×65=195 + `STRTMP_IDX` 1 + `STRCAT_R` 2 = **799 B** ($E240–$E55E, 1 B under the $E560
wall). The +65 B over the folded 737 estimate is the cost of keeping `STRSCR` separate;
it still fits. `STRMAX`=64 is the largest that fits without moving buffers. **255 is deferred** to an
optional future RAM re-architecture (relocate/shrink the file-channel + cassette buffers
to free ~2 KB contiguous — a sub-project that touches `fat.asm` + cassette code and
re-runs the disk + tape gates). Not worth bolting onto the first string feature.

### 5b. ROM layout — the reloc build must re-distribute includes (verified 2026-07-10)

The S3/S4 reloc build put **all** code at $4000+ (page 1, byte-identical to lean) and left
the reclaimed low region $2812–$3FFF as `$00` pad — it proved *relocation* without yet
*using* the space. Measured now: reloc **page 1 is full to $7FFF**, low region is 5661 B of
`$00`. So the string engine cannot be added inline in page-1 structures (`kwtable`, the
`expr.asm` factor) — any inline growth pushes page 1 past $7FFF. **The engine, its keyword
table, and its evaluator handlers go in the low region**, and enough existing page-1
includes are **moved down** into the low region to free the page-1 room the tokeniser /
evaluator hooks need. Cross-slot reach is a non-issue (all in-slot; S3-audit proved the
interpreter is 100 % label-based). Consequence: the reloc build's page-1 body **no longer
equals lean's** — `tools/check_reloc.py`'s "page-1 identical" assertion was a pure-relocation
(no-features) property and is **superseded** here by the durable regression guarantee:
**the lean `basic.rom` (default `ROM_BASE=$4000`) stays byte-identical**, enforced by the
$8000 overflow guard. `check_reloc.py` is updated in S3 to check the low region + lean
byte-identity instead of page-1 equality.

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

1. **S1 — this spec + sign-off.** ✅
2. **S2 — clean-room token lock.** ✅ Capture the 8 selector values black-box (done) +
   add the token equates + provenance. The `kwtable` entries + tokeniser wiring move to S3
   (they can't be placed until the re-layout frees page-1 room — §5b). No differential on
   the byte-full lean build; the zerobas-side crunch check runs on the repack build in S5.
3. **S3 — low-region re-layout + temp ring + `str_expr` + `+` concat + tokeniser wiring.** ✅
   (2026-07-10.) Done: `STRMAX` gated 64 (repack) / 32 (lean); the temp ring + concat
   accumulator RAM laid out inside the 800 B window (`STRSCR` kept separate — §3a deviation).
   `kwtable` extracted to [`basic/kwtable.inc`](../basic/kwtable.inc) with **gated placement**
   (inline page-1 for lean, low region for repack) — the cleanest way to "move page-1 code
   down": the table is pure data reached only via `ld ix,kwtable`, so relocating it frees
   ~500 B of page-1 room (page 1 was full to $7FFF) and its 8 new string-keyword entries
   crunch **and** LIST-detokenise for free (both scan the table). Engine core (temp ring
   allocator + `+` concat spine) in [`basic/str-engine.asm`](../basic/str-engine.asm)
   (repack-only, low region); the concat-aware `str_eval` wrapper in
   [`basic/strvar.asm`](../basic/strvar.asm) folds `+` for every string context at once.
   `check_reloc.py` rewritten per §5b (low-region-occupied + pinned lean byte-identity).
   Proof: [`tests/test_str_engine.py`](../tests/test_str_engine.py) — 10 cases incl. the
   spec case `A$+B$+C$`, the 64-char clamp, empty operands, and a 6-operand chain using one
   ring slot. Gates: lean byte-identical, unit-test 39/39, `make basic-reloc` OK. **The S4
   verbs' keyword tokens are already wired (crunch + LIST); only their handlers remain.**
4. **S4 — the verbs.** LEN/ASC/CHR$/LEFT$/RIGHT$/MID$/STR$/VAL.
5. **S5 — repack machine + `string-acceptance` gate** (D-D). **Machine + acceptance
   corpus PULLED FORWARD (2026-07-10, commits 24ff24e + 4f90b53):** the gated repack disk
   machine `C-BIOS_MSX1_EU_REPACK_DISK` (merged main ROM + zerobas-disk) is installed by
   [`tools/install-repack-machine.py`](../tools/install-repack-machine.py), and the FULL
   Disk-BASIC acceptance corpus now runs on the relocated BASIC build via
   [`tools/run_repack_acceptance.py`](../tools/run_repack_acceptance.py) — `make
   diskbasic-acceptance-repack` → **34/34 verbs converge vs CF-3300**, trustworthy (a
   binary-level `openmsx` shim remaps every probe's machine to repack regardless of how it
   launches openMSX, with a STRICT guard that hard-fails any lean fallback). This closes the
   behavioural-divergence gap S3 opened (STRMAX=64 / concat `str_eval` / relocated kwtable /
   tokenised keywords all flow through the disk verbs). **Still remaining for S5:** the
   repack-build crunch differential for the 8 keywords (assert the repack build crunches
   `LEN`→`$FF$92` … against the §4 captured bytes) + a functional string-concat openMSX
   probe (`string-acceptance`) + wiring it as a standing gate. (No `bdos-acceptance-repack`:
   the BDOS gate exercises the disk ROM, which the string arc does not touch.)
6. **S6 — close-out:** provenance (`basic/PROVENANCE.md` entries), docs harvest, memory +
   TODO update.

**Gates (must stay green):** lean `basic.rom` byte-identical (regression-safe by
construction); unit-test 38/38; bdos-acceptance 12/12; diskbasic-acceptance 34/34;
bdos-cbios-selfcheck 10/10; the `$8000` overflow guard stays green in the lean build;
+ new: `basic_probe_crunch.py` covers the 8 keywords, `string-acceptance` on the repack
machine.
